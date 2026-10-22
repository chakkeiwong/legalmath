"""Reviewed voting-threshold integration through complete source-bound answers."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import ast,hashlib,json,os,shutil,signal,subprocess,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from scripts import prospectus_rating_application as prior
from scripts import prospectus_votes_application as failed
from scripts import prospectus_votes_oracle as oracle
from scripts.prospectus_typed_delta import changes,apply
from legalmath.prospectus.execution_authority import Authority,CODE,digest as adigest
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;PREP=AUTH/'reviews/control-votes-verification-310';HERE=AUTH/'attempts/basf-references/attempt-051'
PLAN='docs/plans/prospectus-control-votes-verification-2026-10-19.md';METHOD='scripts/prospectus_votes_continuation.py'
WORKER='scripts/prospectus_votes_continuation_installed.py';ORACLE='scripts/prospectus_votes_oracle.py'
TEST='tests/prospectus_successor/test_control_votes.py';FILES=(PLAN,METHOD,WORKER,ORACLE,TEST)
TARGETS=('src/legalmath/prospectus/control_votes.py',
         'src/legalmath/prospectus/successor/service.py')
STAGES=('tests','consume','controls','package','installed','seal')
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel


def costs(extra=0):
    start=read(PREP/'accounting-start.json');seconds=start['prior']['cumulative026_050_measured_seconds']+extra
    for folder in (PREP,HERE):
        for pattern in ('stages/*/result.json','stages/*/failure.json'):
            seconds+=sum(read(p)['wall_seconds'] for p in folder.glob(pattern))
    paths={p for folder in (PREP,HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in FILES);paths.add(AUTH/'revisions/0310.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size=start['prior']['cumulative026_050_bytes']+sum(p.stat().st_size for p in paths if p.exists())
    size+=max(0,(AUTH/'program.json').stat().st_size-start['program_bytes'])
    size+=sum(max(0,(ROOT/n).stat().st_size-v) for n,v in start['production_bytes'].items() if (ROOT/n).exists())
    assert seconds<9600 and size<1148*1024**2,'Rating cumulative026 resource bound'
    return {'cumulative026_051_measured_seconds':seconds,'cumulative026_051_bytes':size,
        'prior_costs_reset':False,'seconds_bound':9600,'bytes_bound_with_4MiB_reserve':1152*1024**2,
        'manual_controller_seconds':'UNKNOWN','prior_unmeasured_preparation':'UNKNOWN;never treated as zero'}


def prepare():
    program=read(AUTH/'program.json');assert program['revision']==309
    events=Authority(ROOT).events();attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts)==50 and any(e['kind']=='REJECT' and e.get('attempt')==rel(failed.HERE) for e in events)
    for n,v in read(failed.HERE/'outputs.json').items():assert sha(failed.HERE/n)==v,n
    assert read(failed.HERE/'stages/tests/failure.json')['message']=="'events'"
    save(PREP/'accounting-start.json',{'prior':failed.costs(),'program_bytes':(AUTH/'program.json').stat().st_size,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'production_bytes':{n:(ROOT/n).stat().st_size for n in TARGETS}})
    for name in ('profile.json','expected.json','reconciliation.json','installation.json'):
        shutil.copyfile(failed.PREP/name,PREP/name)
    for row in read(PREP/'installation.json'):assert sha(ROOT/row['target'])==row['after']
    (PREP/'METHOD-REVIEW.md').write_text("""# Bounded verification repair

PASS: retained failure is a driver lookup of events where the immutable scenario
declares votes. All668 tests passed. Candidate,source,expected scenarios and
baseline049 stay unchanged. The changed runner reads votes; prior test XML/log
and failure remain bound. Complete ordinary,negative,package and installed
verification remain mandatory. No weakened assertions or production changes.
""")
    bindings={n:sha(ROOT/n) for n in (*CODE,*FILES,failed.METHOD,failed.WORKER,failed.PLAN,
        prior.METHOD,prior.WORKER,prior.ORACLE,'pyproject.toml','scripts/prospectus_typed_delta.py')}
    bindings.update({rel(p):sha(p) for p in (ROOT/'src/legalmath').rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix!='.pyc'})
    bindings.update({rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    for p in (failed.PREP/'freeze.json',failed.HERE/'outputs.json',failed.HERE/'pytest.xml',
        failed.HERE/'commands/pytest.log',failed.HERE/'stages/tests/failure.json',prior.HERE/'outputs.json',
        prior.HERE/'answer-delta.json.gz',prior.PREP/'profile.json'):
        bindings[rel(p)]=sha(p)
    for n in testfiles():bindings[n]=sha(ROOT/n)
    save(PREP/'freeze.json',{'bindings':bindings})
    proposal=deepcopy(program);proposal['revision']=310
    task=next(t for t in proposal['tasks'] if t['id']=='basf-references')
    task.update(dossier=PLAN,pre_admission_review=rel(PREP/'METHOD-REVIEW.md'),
        reason='Repair actual-source verification lookup without changing tested voting candidate;finish full consumer and installed checks',
        control_votes_verification={'failed_attempt':rel(failed.HERE),'review':rel(PREP),'production_changes':False,
            'original_task_complete':False,'cumulative026_seconds':9600,'cumulative026_bytes':1152*1024**2})
    task['inputs']=list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    proposal['budgets']['basf-references']['maximum_new_attempts']=51
    routes=read(ROOT/program['continuation_review']['routes']);routes['baseline_revision']=310
    for row in routes['tasks']:
        if row['task']=='basf-references':row.update(dossier=PLAN,task_sha256=adigest(task),
            next_action='Complete unchanged control candidate verification then return to retained statutory eligibility/source work',
            stop_condition='51 admissions;210s stages;9600s cumulative026;1152MiB with reserve;no GETs;no unchanged retry')
    save(PREP/'routes.json',routes);proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    forecast={'seconds':costs()['cumulative026_051_measured_seconds']+750,'bytes':costs()['cumulative026_051_bytes']+120*1024**2,'estimate_only':True}
    assert forecast['seconds']<9600 and forecast['bytes']<1148*1024**2
    review={'baseline':adigest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Bounded changed verification lookup events to votes','No production or oracle changes','Admission50 to51;all cumulative costs retained'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'METHOD-REVIEW.md'),'forecast':forecast},
        'evidence_contract':{'primary':'Original source oracle,complete baseline equality,ordinary and installed agreement',
            'promotion_veto':['Candidate drift','Expected result drift','Missing adverse control','Answer mismatch'],
            'continuation_veto':['Corruption','Resource exhaustion','Another driver failure'],
            'explanatory_only':['Tests','Runtime'],'not_concluded':['Actual control','Ownership eligibility','Whole build']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':50,'new_maximum':51,'retained_attempts':attempts,
            'reason':'One reproduced verification-driver schema mismatch after668passing tests',
            'next_discriminating_check':'Corrected lookup evaluates all34actual-source scenarios before full consumer replay',
            'stop_condition':'One changed verification;210s stages;9600s cumulative026;1152MiB reserve;no GETs',
            'same_scope_authorization':'User authorized continued repairs and internal build verification'}}
    save(PREP/'proposal.json',proposal);save(PREP/'review.json',review)
    return {'status':'PASS','revision':310,'production_unchanged':True,'forecast':forecast}


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


def execute(name,command,seconds):
    folder=HERE/'commands';folder.mkdir(exist_ok=True);save(folder/(name+'.json'),{'command':command,'timeout_seconds':seconds})
    with (folder/(name+'.log')).open('x') as stream:
        result=subprocess.run(command,cwd=HERE,env={**os.environ,'PYTHONPATH':str(ROOT/'src')+os.pathsep+str(ROOT)},stdout=stream,stderr=subprocess.STDOUT,timeout=seconds)
    assert result.returncode==0,'Inspect '+name+'.log'


def testfiles():
    return [TEST,*prior.testfiles()]


def tests():
    import xml.etree.ElementTree as ET
    suite=ET.parse(failed.HERE/'pytest.xml').getroot().find('testsuite')
    assert suite.attrib['tests']=='668' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
    save(HERE/'retained-tests.json',{'tests':668,'xml':rel(failed.HERE/'pytest.xml'),'sha256':sha(failed.HERE/'pytest.xml'),'candidate_unchanged':True})
    from legalmath.prospectus import control_votes as module
    profile=read(PREP/'profile.json');instrument=profile['scenarios'][0]['votes']['instrument_id']
    for row in profile['scenarios']:assert oracle.projection(module.analyze(row,profile['context'],instrument))==oracle.classify(row)
    return {'status':'PASS','independent_formula_cases':560,'actual_source_node_cases':len(profile['scenarios'])}


def profiles():
    options=prior.profiles();profile=read(PREP/'profile.json')
    return {**options,'votes_profile':profile,'expected_votes_profile_sha256':digest(profile)}


def consume():
    from legalmath.prospectus.successor import service
    from legalmath.prospectus import control_votes as module
    p,_,ordinary=prior.retained();profile=read(PREP/'profile.json')
    actual=service.consume(p,ROOT,mode='frozen',**profiles())
    verification=module.verify_answer(actual,ordinary,profile,p,ROOT,expected_profile_sha256=digest(profile))
    outcomes={r['scenario']['id']:oracle.projection(r) for r in actual[module.KEY]['scenarios']}
    assert outcomes==read(PREP/'expected.json')['scenarios']
    save(HERE/'answer-delta.json.gz',{'delta':changes(ordinary,actual),'sha256':digest(actual)})
    save(HERE/'outcomes.json',outcomes);save(HERE/'verification.json',verification)
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(outcomes),'answer_sha256':digest(actual)}


def retained():
    p,_,ordinary=prior.retained();delta=read(HERE/'answer-delta.json.gz');answer=apply(ordinary,delta['delta'])
    assert digest(answer)==delta['sha256'];return p,ordinary,answer


def controls():
    from legalmath.prospectus import control_votes as module
    p,ordinary,actual=retained();profile=read(PREP/'profile.json');refused={}
    for kind in ('source','products','baseline','promotion','computed-override','denominator','operand-event','composition-event','forged-answer','lost-baseline'):
        bad=deepcopy(profile);answer=deepcopy(actual)
        if kind=='source':bad['context']['quote']+=' changed'
        elif kind=='products':bad['products_sha256']='0'*64
        elif kind=='baseline':bad['ordinary_answer_sha256']='0'*64
        elif kind=='promotion':bad['actual_event_established']=True
        elif kind=='computed-override':bad['scenarios'][1]['other_facts']['control_put.control']=True
        elif kind=='denominator':bad['scenarios'][1]['votes']['total']['basis']='PARTICIPATING_VOTING_RIGHTS'
        elif kind=='operand-event':bad['scenarios'][1]['votes']['eligible']['control_event_id']='other'
        elif kind=='composition-event':next(r for r in bad['scenarios'] if r['id']=='composed-timely')['rating_scenario']['events']['control_event_id']='other'
        elif kind=='forged-answer':answer[module.KEY]['scenarios'][1]['voting_rights_above_half']=True
        else:answer['questions']['Q1']['status']='YES'
        answer['report_sha256']=digest({k:v for k,v in answer.items() if k!='report_sha256'})
        try:
            if kind in ('forged-answer','lost-baseline'):module.verify_answer(answer,ordinary,bad,p,ROOT,expected_profile_sha256=digest(bad))
            else:module.evaluate(p,ordinary,bad,ROOT,expected_profile_sha256=digest(bad))
        except ValueError as error:refused[kind]=str(error)
        else:raise AssertionError('Accepted '+kind)
    save(HERE/'controls.json',{'status':'PASS','refused':refused});return {'status':'PASS','refused':len(refused)}


def package():
    folder=HERE/'package-source';folder.mkdir();shutil.copyfile(ROOT/'pyproject.toml',folder/'pyproject.toml')
    shutil.copytree(ROOT/'src',folder/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    filemap=prior.prior.prior.prior.prior.base.prior.prior.base.package_files;expected=filemap(ROOT/'src/legalmath');python=read(prior.HERE/'package.json')['python']
    execute('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index','--wheel-dir',str(HERE/'wheel'),str(folder)],60)
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual==expected
    execute('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed'),str(wheels[0])],60)
    assert filemap(HERE/'installed/legalmath')==expected
    save(HERE/'package.json',{'python':python,'files':expected,'wheel_sha256':sha(wheels[0])});return {'status':'PASS','package_files':len(expected)}


def installed():
    execute('installed',[read(HERE/'package.json')['python'],'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE)],195)
    return read(HERE/'installed-result.json')


def seal():
    result={'status':'PASS','task':'basf-references','original_task_complete':False,'result_kind':'CONDITIONAL_CONTROL_VOTING_RIGHTS',
        'scenarios':len(read(PREP/'profile.json')['scenarios']),'formula_cases':560,'baseline_unchanged':True,'installed_complete_equal':True,'prior_failure_preserved':rel(failed.HERE),
        'resources':costs(),'actual_control':'NOT_ESTABLISHED','eligible_ownership_and_concert':'NOT_DERIVED',
        'next_action':'Continue retained statutory eligibility and source-specific applications;preserve wider original coverage'}
    save(HERE/'result.json',result);save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(HERE/'stages'/s/'started.json')['command'] for s in STAGES],'environment':str(ROOT/'.venv/bin/python'),
        'cpu_gpu':'CPU;GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(prior.HERE/'answer-delta.json.gz'),
        'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json')})
    shutil.copyfile(PREP/'reconciliation.json',HERE/'reconciliation.json')
    (HERE/'RESULT.md').write_text("""# Strict contract voting threshold reaches the full answer

The adapter derives >50% from exact eligible/all voting rights and composes the
same control event with rating and Frankfurt exercise conditions. Exactly50%
and statutory30% do not trigger this contract threshold. Numeric majority does
not establish eligible ownership,coordinated persons,nonoverlap or snapshot truth.
Unknown qualifications stay visible. All prior complete-answer fields and the
isolated installed answer are preserved.

|Decision|Primary criterion|Veto status|Main uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Retain conditional ratio and composition|Integer oracle,complete formula,ordinary/installed equality|Wrong basis,event,override,source and forged controls refused|Eligible ownership,concert,historical application|Source-specific statutory applications|Actual control or whole build|

This was a local missing source-specific derivation,not evidence of a package
defect. The strongest alternative explanation for an actual positive result is
an incorrect supplied eligible total; explicit qualification premises expose
that dependence. Independent ownership attribution remains unevaluated. The
coverage reconciliation retains original denominators and each historical or
broader source gap; finite test counts do not establish complete reference recall.
""");return result


def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES;folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not (folder/'started.json').exists(),'Unchanged retry refused'
    if stage!='prepare':
        for before in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/before/'result.json')['status']=='PASS'
        costs()
    save(folder/'started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_votes_continuation',stage],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':210})
    start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Rating stage bound')));signal.alarm(210)
    try:
        if stage!='prepare':frozen(stage!='install')
        result=globals()[stage]()
        if stage!='prepare':frozen()
        costs(time.monotonic()-start);result['wall_seconds']=time.monotonic()-start;save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except BaseException as error:save(folder/'failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
