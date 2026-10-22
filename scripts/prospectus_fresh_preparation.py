"""Reviewed staged regeneration of original prospectus products through the CLI."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import ast,gzip,hashlib,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_residual_coverage as prior
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/fresh-preparation-314';HERE=AUTH/'attempts/basf-references/attempt-055'
PLAN='docs/plans/prospectus-fresh-preparation-2026-10-19.md';METHOD='scripts/prospectus_fresh_preparation.py'
WORKER='scripts/prospectus_fresh_installed.py';FIXTURE='scripts/prospectus_preparation_fixture.py'
TEST='tests/prospectus_successor/test_preparation.py';FILES=(PLAN,METHOD,WORKER,FIXTURE,TEST)
TARGETS=('src/legalmath/prospectus/successor/preparation.py','src/legalmath/prospectus/successor/service.py')
STAGES=('install','tests','package','small-installed','source','construction','interpretation','law','financial','consume-installed','seal')
PHASES={'source':'P1','construction':'P2','interpretation':'P3','law':'P4','financial':'P5'}
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def testfiles():return [TEST,'tests/prospectus_successor/test_successor.py',*prior.testfiles()]


def costs(extra=0):
    start=read(PREP/'accounting-start.json');base=start['prior'];seconds=base['cumulative026_054_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0314.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=base['cumulative026_054_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<12600 and size<2044*1024**2,'Fresh cumulative026 bound'
    return {'cumulative026_055_measured_seconds':seconds,'cumulative026_055_bytes':size,
        'prior_costs_reset':False,'seconds_bound':12600,'bytes_bound_with_4MiB_reserve':2048*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==313
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==54 and any(e['kind']=='RECORD' and e.get('attempt')==rel(prior.HERE) for e in events)
    for n,v in read(prior.HERE/'outputs.json').items():assert sha(prior.HERE/n)==v,n
    save(PREP/'accounting-start.json',{'prior':prior.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size if (ROOT/n).exists() else 0 for n in TARGETS}})
    text=(ROOT/TARGETS[1]).read_text()
    old='    commands = parser.add_subparsers(dest="prospectus_command", required=True)'
    assert text.count(old)==1;text=text.replace(old,old+'\n    from .preparation import configure as configure_preparation\n    configure_preparation(commands)')
    old='def dispatch(args):\n    root = Path(args.repository)'
    assert text.count(old)==1;text=text.replace(old,'def dispatch(args):\n    if args.prospectus_command == "prepare":\n        from .preparation import dispatch as prepare_dispatch\n        return prepare_dispatch(args)\n    root = Path(args.repository)')
    (PREP/'candidate/service.py').write_text(text);(PREP/'baseline').mkdir();installation=[]
    for target in TARGETS:
        path=ROOT/target;candidate=PREP/'candidate'/path.name;ast.parse(candidate.read_text())
        if path.exists():shutil.copyfile(path,PREP/'baseline'/path.name)
        installation.append({'target':target,'before':sha(path) if path.exists() else None,'candidate':rel(candidate),'after':sha(candidate)})
    save(PREP/'installation.json',installation)
    products,_=prior.baseline()
    inputs={'request':products['P1']['payload']['request'],'interpretation':products['P3']['payload']['interpretation_input'],
        'law':{k:products['P4']['payload'][k] for k in ('law_input','cases')},
        'financial':{k:products['P5']['payload'][k] for k in ('scenario_input','cases')}}
    refs={}
    for name,value in inputs.items():
        path=PREP/'inputs'/(name+'.json');path.parent.mkdir(exist_ok=True)
        with path.open('x') as stream:json.dump(value,stream,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        refs[name]={'path':rel(path),'sha256':sha(path)}
    save(PREP/'recipe.json',{'version':'prospectus-preparation.v1','inputs':refs})
    save(PREP/'expected-products.json',{k:{'sha256':p['sha256'],'semantic_sha256':digest(p)} for k,p in products.items()})
    save(PREP/'source-files.json',[{'path':d['path'],'sha256':d['sha256']} for d in inputs['request']['bundle']['documents']])
    (PREP/'METHOD-REVIEW.md').write_text('''# Fresh preparation audit

PASS after correcting missing phase-input forwarding and monolithic runtime.
One public command builds exactly one phase from explicit pinned inputs.
P1 must really extract the four original PDFs;P2-P5 use the existing production
functions and exact phase inputs. Parent request,recipe,seals and links are
checked. Small controls compare actual commands with direct functions.
Installed BASF products must be completely equal to CLI311 before unchanged
conditional profiles can be reused. No baseline rehashing or legacy runner
selects work. This is finite source regeneration,not general legal correctness.
Input/product caps follow measured17.8MBrequest and65.8MBmaximum product.
New output directories preserve failed evidence. All previous costs remain;
explicit resource expansion pays for retained153MBregenerated products.
''')
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,'pyproject.toml',prior.METHOD)}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and rel(p) not in TARGETS})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (prior.HERE/'outputs.json',prior.HERE/'ordinary-answer.json.gz',prior.PREP/'profiles.json',prior.prior.prior.PREP/'products.json'):
        bindings[rel(p)]=sha(p)
    for row in read(prior.prior.prior.PREP/'products.json')['products'].values():bindings[row['path']]=row['sha256']
    for row in read(PREP/'source-files.json'):bindings[row['path']]=row['sha256']
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings});proposal=deepcopy(program);proposal['revision']=314
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Rebuild source and interpretation phases through public bounded CLI;verify unchanged profile reuse',
        fresh_preparation={'review':rel(PREP),'original_task_complete':False,'cumulative026_seconds':12600,'cumulative026_bytes':2048*1024**2})
    task['inputs']=list(dict.fromkeys([n for n in task['inputs'] if n not in TARGETS]+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=55
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=314
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Reextract original PDFs and rebuild P1-P5 through installed CLI;then continue original source and legal gaps',
            stop_condition='55 admissions;210s stages;12600s cumulative026;2048MiB reserve;no GETs')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    for n in TARGETS:proposal['continuation_review']['bindings'].pop(n,None)
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_055_measured_seconds']+1100,'bytes':costs()['cumulative026_055_bytes']+350*1024**2,'estimate_only':True}
    assert forecast['seconds']<12600 and forecast['bytes']<2044*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Public staged preparation with exact separate inputs','Actual installed source regeneration and profile reuse',
                   'Admission54 to55;retain costs;10800 to12600seconds and1536 to2048MiB for real regeneration'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Complete direct-function and installed phase equality;realPDFreextraction;unchanged profile pins and answer',
            'promotion_veto':['Lost phase input','Silent rebinding','Copied P1','Parent/source drift','Overwrite','Installed mismatch'],
            'continuation_veto':['Corruption','Method drift','Resource exhaustion'],'explanatory_only':['Runtime','File sizes','Test counts'],
            'not_concluded':['Automatic new-source profiles','Legal completeness','Historical truth','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':54,'new_maximum':55,'retained_attempts':attempts,
            'reason':'Frozen consumer verification does not demonstrate source regeneration;retain full products and phase inputs',
            'next_discriminating_check':'Complete installed P1equality after realPDFextraction before downstream replay',
            'stop_condition':'210s stages;12600s cumulative026;2048MiB reserve;no GETs',
            'same_scope_authorization':'User requests complete general build with internal proof and continued bounded execution'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':314,'forecast':forecast,'input_bytes':{k:(ROOT/r['path']).stat().st_size for k,r in refs.items()}}


def frozen(installed=True):
    a=read(HERE/'admission.json');assert adigest(read(AUTH/'program.json'))==a['program_sha256']
    assert Authority(ROOT).binding(a['task_spec'])==a['binding']
    for n,v in read(PREP/'freeze.json')['bindings'].items():assert sha(ROOT/n)==v,n
    for r in read(PREP/'installation.json'):
        p=ROOT/r['target'];assert (sha(p) if p.exists() else None)==r['after' if installed else 'before'],r['target']


def install():
    for row in read(PREP/'installation.json'):
        p=ROOT/row['target'];assert (sha(p) if p.exists() else None)==row['before'];shutil.copyfile(ROOT/row['candidate'],p)
    return {'status':'PASS','production_files':2}


def execute(name,command,seconds):
    save(HERE/('commands/'+name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (HERE/'commands'/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},
            stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def tests():
    execute('pytest',[str(ROOT/'.venv/bin/python'),'-m','pytest',*[str(ROOT/n) for n in testfiles()],'-q','--junitxml='+str(HERE/'pytest.xml')],150)
    return {'status':'PASS','phase_inputs_and_adverse_controls':True}


def filemap(folder):return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    expected=filemap(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert filemap(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])})
    return {'status':'PASS','package_files':len(expected)}


def cli_arguments(stage):
    output=rel(HERE/'fresh'/stage)
    args=['prospectus','prepare','--stage',stage,'--recipe',rel(PREP/'recipe.json'),
        '--recipe-sha256',sha(PREP/'recipe.json'),'--repository',str(ROOT),'--output',output]
    if stage!='P1':
        previous='P'+str(int(stage[1:])-1);path=HERE/'fresh'/previous/'products.json'
        args+=['--parents',rel(path),'--parents-sha256',sha(path)]
    return args


def worker(name):
    execute(name,[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),name],195)
    return read(HERE/(name+'-result.json'))


def small_installed():return worker('small-installed')
def source():return worker('source')
def construction():return worker('construction')
def interpretation():return worker('interpretation')
def law():return worker('law')
def financial():return worker('financial')


def consume_installed():
    result=worker('consume-installed');path=HERE/'installed-answer.json';body=path.read_bytes()
    with gzip.open(str(path)+'.gz','wb') as stream:stream.write(body)
    assert gzip.open(str(path)+'.gz','rb').read()==body;path.unlink()
    result.update(raw_output_sha256=hashlib.sha256(body).hexdigest(),lossless_output='installed-answer.json.gz');return result


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'INSTALLED_FRESH_PHASE_PREPARATION',
        'actual_original_pdf_extraction':True,'complete_products_equal':True,'unchanged_profile_pins':True,
        'installed_answer_equal':True,'resources':costs(),
        'next_action':'Continue statutory/historical source gaps and new-source profile preparation;exact regeneration is not general source recall'}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic',
        'data_version':sha(PREP/'recipe.json'),'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    (HERE/'RESULT.md').write_text('''# Original products rebuilt through the installed command

The public prepare command extracts sourceP1and separately buildsP2-P5from a
pinned recipe with explicit phase inputs. Real retained BASFPDFs are reextracted;
every complete product equals its earlierCLI311product. The installed consumer
uses those regenerated products and unchanged conditional profiles and equals
the complete coverage054answer. Small-source commands also equal direct functions.

|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain staged preparation|Complete source and installed phase/answer equality|Phase input,recipe,parent,source and overwrite checks pass|New-source readings and historical editions|Original substantive source closure|Automatic interpretation,source recall or whole build|

The integration gap was ours: fresh assess omitted later separate inputs and
offered no bounded phase preparation. No package incapability follows. Exact
regeneration preserves supplied readings;it does not independently prove them.
The strongest remaining alternative explanation is a shared error in those
readings. A changed extraction graph or lost phase input would invalidate reuse.
''')
    return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_fresh_preparation',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Fresh preparation stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage.replace('-','_')]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:
        save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
