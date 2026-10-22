"""Bounded source-preserving CLI route for pinned conditional analysis profiles."""
from argparse import ArgumentParser
from contextlib import redirect_stderr
from copy import deepcopy
from datetime import datetime,timezone
from io import StringIO
from pathlib import Path
import ast,gzip,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_votes_continuation as prior
from scripts import prospectus_bgb_timing as plain_baseline
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/conditional-cli-311';HERE=AUTH/'attempts/basf-references/attempt-052'
PLAN='docs/plans/prospectus-conditional-cli-2026-10-19.md';METHOD='scripts/prospectus_conditional_cli.py'
WORKER='scripts/prospectus_conditional_cli_worker.py';TEST='tests/prospectus_successor/test_conditional_profiles_cli.py'
FILES=(PLAN,METHOD,WORKER,TEST)
TARGETS=('src/legalmath/prospectus/successor/conditional_profiles.py','src/legalmath/prospectus/successor/service.py')
STAGES=('install','tests','consume','plain','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_051_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0311.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_051_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<10800 and size<1532*1024**2,'Cumulative026 CLI resource bound'
    return {'cumulative026_052_measured_seconds':seconds,'cumulative026_052_bytes':size,
        'prior_costs_reset':False,'seconds_bound':10800,'bytes_bound_with_4MiB_reserve':1536*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def compact(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'))


def testfiles():
    return [TEST,*prior.testfiles()]


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==310
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==51 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    from legalmath.prospectus.successor import service
    parser=ArgumentParser();service.configure(parser);errors=StringIO()
    with redirect_stderr(errors):
        try:parser.parse_args(['consume','--products','products.json','--output','answer.json',
            '--conditional-profiles','profiles.json','--conditional-profiles-sha256','a'*64])
        except SystemExit as error:assert error.code==2
        else:raise AssertionError('Expected current CLI to lack conditional profile options')
    save(PREP/'reproduction.json',{'classification':'MISSING_CLI_ARGUMENTS','exit_code':2,'stderr':errors.getvalue(),
        'direct_python_support':True,'actual_cli_support':False,'candidate_run':False})
    text=(ROOT/TARGETS[1]).read_text()
    old='            p.add_argument("--mode", choices=("frozen", "current"), default="frozen")'
    new=old+'\n            p.add_argument("--conditional-profiles", help="Repository-relative pinned profile manifest")\n            p.add_argument("--conditional-profiles-sha256", help="SHA256 of the conditional manifest bytes")'
    assert text.count(old)==1;text=text.replace(old,new)
    old='        manifest = read(args.products)'
    new='''        from .conditional_profiles import load
        profile_options = load(root, getattr(args, "conditional_profiles", None),
                               getattr(args, "conditional_profiles_sha256", None))
        manifest = read(args.products)'''
    assert text.count(old)==1;text=text.replace(old,new)
    old='        result = consume(products, root, bank, mode=getattr(args, "mode", "frozen"))'
    new='        result = consume(products, root, bank, mode=getattr(args, "mode", "frozen"), **profile_options)'
    assert text.count(old)==1;text=text.replace(old,new)
    (PREP/'candidate/service.py').write_text(text);(PREP/'baseline').mkdir(exist_ok=True);installation=[]
    for target in TARGETS:
        candidate=PREP/'candidate'/Path(target).name;ast.parse(candidate.read_text());exists=(ROOT/target).exists()
        if exists:shutil.copyfile(ROOT/target,PREP/'baseline'/Path(target).name)
        installation.append({'target':target,'before':sha(ROOT/target) if exists else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    p,_,answer=prior.retained();pp,ordinary=plain_baseline.retained('ordinary');assert digest(p)==digest(pp)
    manifest={'products':{}}
    for stage,value in p.items():
        path=PREP/'products'/(stage+'.json');compact(path,value)
        manifest['products'][stage]={'path':rel(path),'sha256':sha(path)}
    save(PREP/'products.json',manifest)
    profiles=prior.profiles();rows=[]
    for name in ('comparative','default_f','majority','amount','duration','cutoff','payment','rating','votes'):
        key=name+'_profile'
        if key not in profiles:continue
        path=PREP/'profiles'/(name+'.json');compact(path,profiles[key]);semantic=digest(profiles[key])
        assert profiles['expected_'+name+'_profile_sha256']==semantic
        rows.append({'name':name,'path':rel(path),'file_sha256':sha(path),'profile_sha256':semantic})
    save(PREP/'profiles.json',{'version':'prospectus-conditional-profiles.v1','profiles':rows})
    save(PREP/'expected.json',{'profile_answer_sha256':digest(answer),'plain_answer_sha256':digest(ordinary),
        'product_sha256':digest(p),'profile_manifest_sha256':sha(PREP/'profiles.json'),'candidate_invoked':False})
    save(PREP/'coverage.json',{'predecessor':rel(prior.HERE),'verified':'Voting numeric adapter and same-event rating/cutoff compose through Python consume',
        'reproduced_gap':'CLI does not forward profile inputs','repair':'Explicit hash-bound consume CLI manifest',
        'remaining':['Fresh request profile preparation','Source-specific eligibility and historical application',
            'Original implicit reference,definition,margin,office,incorporation and wider corpus acceptance'],
        'actual_facts':'AFTER_BUILD','external_adviser_required':False,'original_task_complete':False})
    (PREP/'METHOD-REVIEW.md').write_text('''# Conditional CLI skeptical audit

PASS after reproducing missing consume CLI options with exit2. Direct Python
verification is not CLI coverage. Candidate forwards explicit file/semantic pins
without rewriting source or baseline identities. All product and prior-answer
checks remain. No-profile behavior remains unchanged. Fresh assess is excluded
because its profile preparation protocol is not yet established. Actual installed
CLI output must equal complete051; mocks/parser tests alone are insufficient.
Manifest/profile size bounds,strict JSON,known names and existing bound_path are
input validation,not host-security or legal-truth guarantees. No extra permission.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.WORKER,prior.ORACLE,plain_baseline.METHOD)}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'answer-delta.json.gz',prior.PREP/'profile.json'):
        bindings[rel(p)]=sha(p)
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=311
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Close reproduced installed CLI profile-routing gap while preserving verified conditional answers',
        conditional_cli={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':10800,'cumulative026_bytes':1536*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=52
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=311
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Verify actual installed consume CLI with pinned profiles;then return to source-specific statutory work',
            stop_condition='52 admissions;210s stages;10800s cumulative026;1536MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_052_measured_seconds']+850,
        'bytes':read(PREP/'accounting-start.json')['prior']['cumulative026_051_bytes']+400*1024**2,'estimate_only':True}
    assert forecast['seconds']<10800 and forecast['bytes']<1532*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Reproduced real CLI integration repair','Admission51 to52;time9600 to10800;storage1152 to1536MiB;retain all costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Actual ordinary/installed CLI full equality with complete051 and no-profile baseline',
            'promotion_veto':['Unpinned profile','Unexpected answer delta','Lost no-profile route','Noninstalled imports'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],
            'explanatory_only':['Counts','Runtime'],'not_concluded':['Actual facts','Fresh request integration','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':51,'new_maximum':52,'retained_attempts':attempts,
            'reason':'Actual CLI cannot accept the verified optional profiles;product JSON/output retention needs measured storage extension',
            'next_discriminating_check':'Actual installed CLI produces the same full conditional answer as Python consume',
            'stop_condition':'210s stages;10800s cumulative026;1536MiB reserve;no GETs',
            'same_scope_authorization':'User requested continued internally verified complete build and integration repair'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':311,'profiles':len(rows),'reproduced_missing_cli':True,'forecast':forecast}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['after' if installed else 'before'],row['target']


def install():
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['before'];shutil.copyfile(ROOT/row['candidate'],p)
    return {'status':'PASS','production_files':len(TARGETS)}


def execute(name,command,seconds,expected=0):
    folder=HERE/'commands';folder.mkdir(exist_ok=True);save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},
            stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==expected,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],90)
    return {'status':'PASS','prior_candidate_tests_included':True}


def cli_arguments(output,profiles=True):
    args=['prospectus','consume','--products',str(PREP/'products.json'),'--repository',str(ROOT),
        '--output',str(HERE/output),'--mode','frozen']
    if profiles:args+=['--conditional-profiles',rel(PREP/'profiles.json'),'--conditional-profiles-sha256',sha(PREP/'profiles.json')]
    return args


def retain_cli_answer(filename,expected):
    path=HERE/filename;actual=json.loads(path.read_text());assert actual==expected
    body=path.read_bytes();raw_sha=sha(path)
    with gzip.open(str(path)+'.gz','wb') as stream:stream.write(body)
    assert gzip.open(str(path)+'.gz','rb').read()==body
    path.unlink() # Lossless compressed evidence retained; remove only this generated raw duplicate.
    return {'status':'PASS','actual_cli':True,'complete_answer_equal':True,'answer_sha256':digest(actual),
        'raw_output_sha256':raw_sha,'lossless_output':filename+'.gz'}


def consume():
    execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    _,_,expected=prior.retained();result=retain_cli_answer('ordinary-answer.json',expected)
    assert result['answer_sha256']==read(PREP/'expected.json')['profile_answer_sha256'];return result


def plain():
    execute('plain-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('plain-answer.json',False)],195)
    _,expected=plain_baseline.retained('ordinary')
    result=retain_cli_answer('plain-answer.json',expected)
    assert result['answer_sha256']==read(PREP/'expected.json')['plain_answer_sha256'];return result


def controls():
    refused={};original=read(PREP/'profiles.json')
    for kind in ('manifest-hash','file-hash','semantic-hash','unknown-name','escape-path','missing-pin'):
        bad=deepcopy(original)
        if kind=='file-hash':bad['profiles'][0]['file_sha256']='0'*64
        elif kind=='semantic-hash':bad['profiles'][0]['profile_sha256']='0'*64
        elif kind=='unknown-name':bad['profiles'][0]['name']='unsupported'
        elif kind=='escape-path':bad['profiles'][0]['path']='../outside.json'
        path=HERE/'control-inputs'/(kind+'.json');save(path,bad)
        output=HERE/(kind+'-answer.json');args=cli_arguments(output.name,False)
        args+=['--conditional-profiles',rel(path)]
        if kind!='missing-pin':args+=['--conditional-profiles-sha256','0'*64 if kind=='manifest-hash' else sha(path)]
        execute('refuse-'+kind,[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*args],15,expected=1)
        log=(HERE/'commands'/('refuse-'+kind+'.log')).read_text()
        assert 'ValueError:' in log and not output.exists();refused[kind]=log.split('ValueError:')[-1].strip()
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','actual_cli_refusals':len(refused)}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    filemap=prior.prior.prior.prior.prior.prior.base.prior.prior.base.package_files
    expected=filemap(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):__import__('hashlib').sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert filemap(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed-cli',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    result=read(HERE/'installed-result.json');_,_,expected=prior.retained()
    result.update(retain_cli_answer('installed-answer.json',expected));return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'PINNED_CONDITIONAL_CONSUME_CLI',
        'ordinary_cli_equal':True,'plain_cli_equal':True,'installed_cli_equal':True,'actual_cli_refusals':6,
        'resources':costs(),'fresh_assess_profile_support':'NOT_IMPLEMENTED','actual_facts':'NOT_ESTABLISHED',
        'next_action':'Return to source-specific statutory eligibility and original source completeness;retain fresh profile preparation gap'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PREP/'products.json'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Conditional analysis profiles reach the installed command

The consume CLI accepts an explicit manifest with pinned file and semantic hashes.
It forwards the existing profiles without rebinding source or prior-answer
identities. Ordinary and isolated installed CLI answers equal complete051;the
no-profile answer equals its original baseline. Six malformed/unbound CLI inputs
refuse before answer creation. Prior candidate tests remain included.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain explicit consume CLI profiles|Actual complete ordinary/installed and no-profile equality|Hash,name,path and missing-pin controls refuse|Fresh profile preparation and substantive legal premises|Return to source-specific applications|Actual legal facts or general build completion|

This fixes a local CLI integration omission. It does not establish a package
defect. Fresh assess still has no profile preparation protocol because profiles
bind exact products and preceding answers. The weakest remaining product link
is preparation for a new source bundle;the successful frozen-product route does
not prove that capability. Original source and acceptance gaps remain recorded.
''');return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_conditional_cli',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('CLI stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
