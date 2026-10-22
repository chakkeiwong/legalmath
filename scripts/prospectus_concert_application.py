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
from scripts import prospectus_conditional_cli as prior
from scripts import prospectus_concert_oracle as oracle
from scripts.prospectus_typed_delta import changes,apply
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/concert-312';HERE=AUTH/'attempts/basf-references/attempt-053'
PLAN='docs/plans/prospectus-concert-application-2026-10-19.md';METHOD='scripts/prospectus_concert_application.py'
WORKER='scripts/prospectus_concert_installed.py';ORACLE='scripts/prospectus_concert_oracle.py';TEST='tests/prospectus_successor/test_concert_application.py'
FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/concert_application.py','src/legalmath/prospectus/successor/service.py','src/legalmath/prospectus/successor/conditional_profiles.py')
STAGES=('install','tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_052_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0312.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_052_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<10800 and size<1532*1024**2,'Cumulative026 CLI resource bound'
    return {'cumulative026_053_measured_seconds':seconds,'cumulative026_053_bytes':size,
        'prior_costs_reset':False,'seconds_bound':10800,'bytes_bound_with_4MiB_reserve':1536*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def compact(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'))


def testfiles():
    return [TEST,*prior.testfiles()]


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==311
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==52 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    text=(ROOT/TARGETS[1]).read_text();old='            votes_profile=None, expected_votes_profile_sha256=None):'
    new='            votes_profile=None, expected_votes_profile_sha256=None,\n            concert_profile=None, expected_concert_profile_sha256=None):'
    assert text.count(old)==1;text=text.replace(old,new)
    old='    return {**result, "report_sha256": digest(result)}\n\n\ndef assess('
    new="""    if concert_profile is not None:
        from ..concert_application import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['concert_necessary_review'] = evaluate(products, baseline, concert_profile, root,
            expected_profile_sha256=expected_concert_profile_sha256)
    elif expected_concert_profile_sha256 is not None:
        raise ValueError('Concert profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess("""
    assert text.count(old)==1;text=text.replace(old,new);(PREP/'candidate/service.py').write_text(text)
    text=(ROOT/TARGETS[2]).read_text();old="'payment', 'rating', 'votes')";new="'payment', 'rating', 'votes', 'concert')"
    assert text.count(old)==1;text=text.replace(old,new);(PREP/'candidate/conditional_profiles.py').write_text(text)
    (PREP/'baseline').mkdir(exist_ok=True);installation=[]
    for target in TARGETS:
        candidate=PREP/'candidate'/Path(target).name;ast.parse(candidate.read_text());exists=(ROOT/target).exists()
        if exists:shutil.copyfile(ROOT/target,PREP/'baseline'/Path(target).name)
        installation.append({'target':target,'before':sha(ROOT/target) if exists else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    p,_,ordinary=prior.prior.retained();report=p['P3']['payload']['statutory_references']
    assert ordinary['statutory_references']==report
    record=next(r for r in report['records'] if r['id']=='H16');source=record['legal_sources'][0]
    excerpt=next(e for e in source['excerpts'] if '(2) Dem Bieter werden auch Stimmrechte' in e['quote'])
    a=excerpt['quote'].index('(2) Dem Bieter');b=excerpt['quote'].index('(3)',a)
    context={'statutory_profile_sha256':report['profile_sha256'],'H16':record,
        'necessary_source':{'path':source['text_path'],'sha256':source['text_sha256'],
            'start':excerpt['start']+a,'end':excerpt['start']+b,'quote':excerpt['quote'][a:b]},
        'meaning':'Explicitly modeled necessary conditions only;legal sufficiency and group attribution not established'}
    assert context['necessary_source']['start']==51520 and context['necessary_source']['end']==52229
    instrument=p['P1']['payload']['request']['bundle']['instrument_id'];rows=oracle.scenarios(instrument)
    profile={'version':'basf-concert-necessary.v1','products_sha256':digest(p),'ordinary_answer_sha256':digest(ordinary),
        'context':context,'scenarios':rows,'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}
    save(PREP/'profile.json',profile);save(PREP/'expected.json',{'scenarios':{r['id']:oracle.classify(r) for r in rows},'candidate_invoked':False})
    manifest=read(prior.PREP/'profiles.json');manifest['profiles'].append({'name':'concert','path':rel(PREP/'profile.json'),
        'file_sha256':sha(PREP/'profile.json'),'profile_sha256':digest(profile)})
    save(PREP/'profiles.json',manifest)
    save(PREP/'coverage.json',{'prior':rel(prior.HERE),'new_application':'H16 necessary coordination conditions for one identified pair',
        'additional_original_gap':{'id':'H43','citation':'WpHG50(1)','original_inventory_preserved':True,
            'current_dependency':'historical-WpHG-50-1-publication','status':'SOURCE_EDITION_AND_APPLICATION_OPEN'},
        'remaining':['Group aggregation and30(1) voting attribution','Historical editions','Wider source and implicit reference completeness',
            'Fresh request profile preparation','Original margin,office,incorporation and remaining task acceptance'],
        'original_task_complete':False,'external_adviser_required':False})
    (PREP/'METHOD-REVIEW.md').write_text("""# H16 necessary-condition audit

PASS after reading exact primary paragraph offsets51520:52229 and full contract
context. Voting understanding and other cooperation with lasting/substantial
aim are alternative branches. Individual-case exception remains explicit.
The source says sets prerequisites: a YES reports only necessary-condition
satisfaction,never sufficient legal concert,group-wide attribution,eligible
ownership or actual control. Readings apply only conditionally;historical truth
remains unknown. One identified pair,instrument and event prevent silent joins.
Independent128Boolean checks and unknown/conflict cases precede candidate.
Complete previous answer and actual installed CLI comparison remain mandatory.
H43 outside the12statutory records is preserved as an original unresolved source.
""")
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD,prior.WORKER,prior.prior.METHOD)}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.prior.HERE/'answer-delta.json.gz',prior.PREP/'profiles.json',prior.PREP/'products.json'):
        bindings[rel(p)]=sha(p)
    for row in read(prior.PREP/'products.json')['products'].values():bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=312
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Apply H16 necessary coordination conditions without promoting eligibility;retain original H43 source gap',
        concert_application={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':10800,'cumulative026_bytes':1536*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=53
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=312
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Validate H16 necessary conditions via installed CLI;continue statutory eligibility and complete original source reconciliation',
            stop_condition='53 admissions;210s stages;10800s cumulative026;1536MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_053_measured_seconds']+750,'bytes':costs()['cumulative026_053_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<10800 and forecast['bytes']<1532*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Source-specific H16 necessary-condition application','Explicit original H43 residual','Admission52 to53;retain cumulative bounds and costs'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Independent source truth table,complete baseline preservation,actual ordinary and installed CLI equality',
            'promotion_veto':['Alternative conflation','Lost exception','Necessary promoted sufficient','Eligibility inferred','Source or baseline drift'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Counts','Runtime'],
            'not_concluded':['Actual concert','Group aggregation','Eligible voting ownership','Historical validity','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':52,'new_maximum':53,'retained_attempts':attempts,
            'reason':'Control ratio does not derive source-specific coordinated-action conditions',
            'next_discriminating_check':'Voting branch does not require lasting-change aim;exception preserved;no actual or sufficient legal conclusion',
            'stop_condition':'210s stages;10800s cumulative026;1536MiB reserve;no GETs',
            'same_scope_authorization':'User requested continued conditional internal source analysis'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':312,'scenarios':len(rows),'forecast':forecast,'original_H43_preserved':True}


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
    from legalmath.prospectus import concert_application as module
    profile=read(PREP/'profile.json');instrument=profile['scenarios'][0]['pair']['instrument_id']
    for row in profile['scenarios']:assert oracle.projection(module.analyze(row,instrument))==oracle.classify(row)
    return {'status':'PASS','formula_cases':128,'source_scenarios':len(profile['scenarios'])}


def cli_arguments(output):
    return ['prospectus','consume','--products',str(prior.PREP/'products.json'),'--repository',str(ROOT),
        '--output',str(HERE/output),'--mode','frozen','--conditional-profiles',rel(PREP/'profiles.json'),
        '--conditional-profiles-sha256',sha(PREP/'profiles.json')]


def compress_output(filename):
    path=HERE/filename;body=path.read_bytes();raw_sha=sha(path)
    with gzip.open(str(path)+'.gz','wb') as stream:stream.write(body)
    assert gzip.open(str(path)+'.gz','rb').read()==body;path.unlink()
    return {'raw_output_sha256':raw_sha,'lossless_output':filename+'.gz'}


def consume():
    from legalmath.prospectus import concert_application as module
    execute('ordinary-cli',[str(ROOT/'.venv/bin/python'),'-m','legalmath.cli',*cli_arguments('ordinary-answer.json')],195)
    p,_,ordinary=prior.prior.retained();actual=json.loads((HERE/'ordinary-answer.json').read_text());profile=read(PREP/'profile.json')
    verification=module.verify_answer(actual,ordinary,profile,p,ROOT,expected_profile_sha256=digest(profile))
    outcomes={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']}
    assert outcomes==read(PREP/'expected.json')['scenarios']
    save(HERE/'answer-delta.json.gz',{'delta':changes(ordinary,actual),'sha256':digest(actual)})
    save(HERE/'verification.json',verification);save(HERE/'outcomes.json',outcomes)
    return {'status':'PASS','actual_cli':True,'baseline_unchanged':True,'scenarios':len(outcomes),'answer_sha256':digest(actual),**compress_output('ordinary-answer.json')}


def retained():
    p,_,ordinary=prior.prior.retained();delta=read(HERE/'answer-delta.json.gz');answer=apply(ordinary,delta['delta'])
    assert digest(answer)==delta['sha256'];return p,ordinary,answer


def controls():
    from legalmath.prospectus import concert_application as module
    p,ordinary,answer=retained();profile=read(PREP/'profile.json');refused={}
    for kind in ('context','products','baseline','actual','historical','sufficiency','pair','forged','lost-baseline'):
        bad=deepcopy(profile);actual=deepcopy(answer)
        if kind=='context':bad['context']['necessary_source']['quote']+='changed'
        elif kind=='products':bad['products_sha256']='0'*64
        elif kind=='baseline':bad['ordinary_answer_sha256']='0'*64
        elif kind=='actual':bad['actual_event_established']=True
        elif kind=='historical':bad['historical_application_proved']=True
        elif kind=='sufficiency':bad['complete_legal_test']=True
        elif kind=='pair':bad['scenarios'][1]['pair']['right_person']=bad['scenarios'][1]['pair']['left_person']
        elif kind=='forged':actual[module.KEY]['scenarios'][1]['sufficient_legal_test']=True
        else:actual['questions']['Q1']['status']='YES'
        actual['report_sha256']=digest({k:v for k,v in actual.items() if k!='report_sha256'})
        try:
            if kind in ('forged','lost-baseline'):module.verify_answer(actual,ordinary,bad,p,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(p,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    filemap=prior.prior.prior.prior.prior.prior.prior.base.prior.prior.base.package_files
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
    result=read(HERE/'installed-result.json');result.update(compress_output('installed-answer.json'));return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'H16_NECESSARY_COORDINATION_CONDITIONS',
        'scenarios':len(read(PREP/'profile.json')['scenarios']),'formula_cases':128,'baseline_unchanged':True,'installed_cli_equal':True,
        'resources':costs(),'actual_concert':'NOT_ESTABLISHED','sufficient_legal_test':False,
        'next_action':'Continue original statutory/source reconciliation including H43;retain ownership/group/historical/fresh-profile gaps'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(prior.PREP/'products.json'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text("""# Necessary coordinated-action conditions reach the actual command

The retained H16 source has separate voting-understanding and lasting/substantial
business-change cooperation alternatives,plus the individual-case exception.
The adapter computes only their necessary-condition satisfaction for one
identified hypothetical pair. It never fills actual concert,group aggregation,
eligible ownership or control. Prior complete fields stay identical and actual
ordinary/installed CLI outputs agree. The original H43 WpHG publication source
gap is explicitly preserved outside the12-record statutory profile.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain conditional necessary-condition application|Independent source formulas and ordinary/installed CLI|Promotion,pair,source and forged controls refused|Sufficiency,group attribution,historical application|Original source reconciliation and eligibility|Actual concert or whole build|

This is local source-specific implementation,not evidence against an external
package. The strongest alternative explanation for a real positive result is
incorrect legal classification of supplied premises. A verified Boolean formula
does not prove those premises or legal sufficiency. That limitation remains
visible in every scenario and prevents promotion to an actual control finding.
""");return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_concert_application',stage],
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
