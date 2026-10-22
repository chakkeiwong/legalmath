"""Bounded actual H1 scope-consumer unit-conflict integration."""
import argparse
from copy import deepcopy
import gzip
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)];sys.dont_write_bytecode=True
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as authority_digest
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus import h1_incorporation_scope as scope, h1_unit_conflict as unit
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_h1_unit_oracle import verify, require

SOURCE=REL+'/attempts/source-bes-dep-05';NORMAL=SOURCE+'/attempt-007';PRIOR=SOURCE+'/attempt-016'
REVIEW=REL+'/reviews/h1-unit-212';PLAN='docs/plans/prospectus-h1-unit-integration-2026-10-17.md'
FIXTURE='tests/prospectus_successor/fixtures/h1_unit_conflict.json.gz'
TESTS=('tests/prospectus/test_h1_unit_conflict.py','tests/prospectus/test_h1_incorporation_scope.py',
       'tests/prospectus/test_build_contract.py')
METHODS=('scripts/prospectus_h1_unit_integration.py','scripts/prospectus_h1_unit_oracle.py',
    'src/legalmath/prospectus/h1_unit_conflict.py','src/legalmath/prospectus/h1_incorporation_scope.py',
    'src/legalmath/prospectus/build_contract.py',*TESTS,FIXTURE)
ADDED=('h1_individual_unit_review','h1_individual_unit_explanation')
SELECTOR={'version':'h1-unit-conflict.v1','preparation_seconds':60,'candidate_seconds':180,
    'validation_seconds':180,'cumulative_seconds':2220,'new_bytes':32*1024**2,'cumulative_bytes':732*1024**2,
    'reserve_bytes':262144,'extraction_OCR_network_render_GPU_install':0,'candidate_copies':0}

def load(path):
    with gzip.open(path,'rt') as f:return json.load(f)

def compressed(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=gzip.compress(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode(),mtime=0)
    with path.open('xb') as f:f.write(data)

def products(root):
    ps=load(root/NORMAL/'products.json.gz');req=ps['P1']['payload']['request']
    service.verify(ps['P1'],'P1',req['bundle'],{'request':digest(req)})
    for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
        service.verify(ps[phase],phase,req['bundle'],{k:ps[k]['sha256'] for k in parents})
    return ps

def consume(root,ps,profile=None):
    cash,risk,spec=[read(root/NORMAL/n) for n in ['cash-flow-profile.json','risk-profile.json','profile.json']]
    return scope.consume(ps,cash,risk,spec,root,expected_cash_profile_sha256=digest(cash),
        expected_risk_profile_sha256=digest(risk),expected_profile_sha256=digest(spec),
        unit_profile=profile,expected_unit_profile_sha256=digest(profile) if profile is not None else None)

def original(root):
    return {**read(root/PRIOR/'profile.json'),'full_units':read(root/PRIOR/'source-units.json')}

def finite_fixture(root):
    old=original(root);ids=set()
    for page in (53,54):ids.update(f'{unit.DOCUMENT}:p{page}:l{n}' for n in [*unit.HEADERS[page],*unit.CELLS[page]])
    graph={'units':[u for u in old['full_units'] if u['id'] in ids]}
    prior={'h1_scope_review':{'candidates':[{'id':'overall-range','pages':[53,54]},
                                         {'id':'enumerated-information','pages':[53,54]}]}}
    return {'graph':graph,'prior':prior,'profile':unit.make_profile(graph,prior,old['images']),'original':old}

def control_helpers(root):
    spec=importlib.util.spec_from_file_location('h1_unit_adverse_cases',root/TESTS[0]);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

def refuse_outputs(value,explanation,verifier,cases):
    rows=[]
    for name in cases.OUTPUT_CASES:
        a,e=cases.output_change(value,explanation,name)
        try:verifier(a,e)
        except ValueError:rows.append({'case':'output:'+name,'rejected':True})
        else:raise ValueError('Incorrect output accepted: '+name)
    return rows

def controls(root):
    f=load(root/FIXTURE);cases=control_helpers(root);p=f['profile']
    value=unit.evaluate(f['graph'],f['prior'],p,root,expected_profile_sha256=digest(p));explanation=unit.explain(value)
    verifier=lambda a,e:verify(a,e,p,f['graph'],f['prior'],f['original'],root)
    rows=[]
    for name in cases.PROFILE_CASES:
        changed=cases.profile_change(p,name)
        try:unit.evaluate(f['graph'],f['prior'],changed,root,expected_profile_sha256=digest(changed))
        except ValueError:rows.append({'case':'repinned-profile:'+name,'rejected':True})
        else:raise ValueError('Incorrect source profile accepted: '+name)
    rows.extend(refuse_outputs(value,explanation,verifier,cases))
    detected=False
    try:refuse_outputs(value,explanation,lambda _a,_e:True,cases)
    except ValueError as exc:detected=str(exc).startswith('Incorrect output accepted:')
    require(detected,'Permissive checker undetected')
    return {'cases':rows,'permissive_checker_detected':detected}

def historical():
    from scripts.prospectus_h1_management import storage as previous_storage
    value=previous_storage()
    value['seconds']=value['previous_seconds']+read(ROOT/PRIOR/'result.json')['cumulative_seconds']
    return value

def storage(root,attempt,enforce=True):
    old=historical()
    files={root/n for n in (*METHODS,PLAN)}
    files|={p for folder in (root/REVIEW,attempt,root/REL/'continuation-reviews/h1-unit-212-record')
            for p in folder.rglob('*') if p.is_file()}
    files|={root/REL/'proposals'/('h1-unit-212'+suffix) for suffix in ('.json','-review.json')}
    added=sum(p.stat().st_size for p in files if p.is_file())
    if enforce:require(added<SELECTOR['new_bytes']-262144 and old['combined_bytes']+added<SELECTOR['cumulative_bytes']-262144,
                       'H1 cumulative storage/reserve ceiling')
    return {'historical_seconds':old['seconds'],'historical_bytes':old['combined_bytes'],
        'new_bytes':added,'combined_bytes':old['combined_bytes']+added,'failure_reserve':262144}

def frozen(root):
    f=read(root/REVIEW/'frozen.json')
    require(f['methods']=={n:file_hash(root/n) for n in METHODS},'Frozen H1 methods changed')
    require(f['inputs']=={n:file_hash(root/n) for n in f['inputs']},'Frozen H1 source/answer changed')
    fixture=load(root/FIXTURE)
    require(digest(fixture['original'])==digest(original(root)),'Independent original016 map changed')
    return f

def evaluate_result(root):
    ps=products(root);baseline=load(root/NORMAL/'scope-consumer.json.gz');p=read(root/REVIEW/'profile.json')
    require(digest(p)==digest(unit.make_profile(ps['P1']['payload']['graph'],baseline,original(root)['images'])),
        'Original H1 finite profile changed')
    actual=consume(root,ps,p)
    require(set(actual)==set(baseline)|set(ADDED) and digest({k:actual[k] for k in baseline})==digest(baseline),
        'Entire original H1 answer changed')
    proof=verify(actual[ADDED[0]],actual[ADDED[1]],p,ps['P1']['payload']['graph'],baseline,original(root),root)
    delta={k:actual[k] for k in ADDED};normal_hash=digest(actual);baseline_hash=digest(baseline)
    del ps,baseline,actual
    later=load(root/PRIOR/'answer-supplement.json.gz')
    require(not set(ADDED)&set(later),'New result collides with016 evidence')
    prior_hash=digest(later);combined={**later,**delta}
    require(digest({k:combined[k] for k in later})==prior_hash,'Whole016 evidence changed')
    composition={'normal_baseline':NORMAL+'/scope-consumer.json.gz','normal_baseline_sha256':baseline_hash,
        'normal_baseline_file_sha256':file_hash(root/NORMAL/'scope-consumer.json.gz'),'normal_answer_sha256':normal_hash,
        'previous_complete_answer':PRIOR+'/answer-supplement.json.gz','previous_content_sha256':prior_hash,
        'previous_file_sha256':file_hash(root/PRIOR/'answer-supplement.json.gz'),
        'complete_composed_sha256':digest(combined),'hash_convention':'product default-spaced sorted JSON',
        'large_answer_copies':0,'all_prior_fields_preserved':True}
    return delta,proof,composition

def validate_submission(root,attempt,task):
    root,attempt=Path(root),Path(attempt);start=time.monotonic();passed=False
    old_handler=signal.getsignal(signal.SIGALRM)
    def expired(_s,_f):raise ValueError('H1 acceptance180second ceiling')
    signal.signal(signal.SIGALRM,expired);signal.alarm(180)
    try:
        require(task['id']=='source-bes-dep-05' and task.get('unit_integration')==SELECTOR,'Wrong H1 reviewed task')
        f=frozen(root);require(set(METHODS)|set(f['inputs'])|{REVIEW+'/frozen.json'}<=set(task['inputs']),'Unbound H1 sources')
        result=read(attempt/'result.json');manifest=read(attempt/'run-manifest.json')
        require(result['status']=='PASS' and result['task_complete'] is False and result['whole_program_complete'] is False
            and manifest['methods']==f['methods'] and manifest['data_version']==f['inputs'],'Invalid retained H1 result')
        checked_tests(root/REVIEW/'tests.xml',f['focused_tests'])
        delta,proof,composition=evaluate_result(root)
        require(digest(load(attempt/'answer-delta.json.gz'))==digest(delta)
            and read(attempt/'verification.json')==proof and read(attempt/'composition.json')==composition
            and read(attempt/'controls.json')==controls(root),'Actual H1 result differs from retained evidence')
        elapsed=time.monotonic()-start;state=storage(root,attempt);prep=read(root/REVIEW/'preparation.json')['seconds']
        charged=state['historical_seconds']+prep+manifest['wall_seconds']+elapsed
        print(json.dumps({'stage':'h1-validation','seconds':elapsed,'cumulative_seconds':charged,'comparisons':2}),flush=True)
        require(elapsed<=180 and manifest['wall_seconds']<=180 and prep<=60 and charged<=2220,'H1 cumulative time ceiling')
        passed=True;return True
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,old_handler)
        print(json.dumps({'stage':'h1-validation-clock','seconds':time.monotonic()-start,'passed':passed}),flush=True)

def prepare():
    import xml.etree.ElementTree as ET
    start=time.monotonic();folder=ROOT/REVIEW;folder.mkdir(parents=True,exist_ok=True)
    ledger=folder/'preparation.json';prep=read(ledger) if ledger.exists() else {'seconds':0,'stages':[]}
    index=len(prep['stages']);error=None
    try:
        ps=products(ROOT);baseline=load(ROOT/NORMAL/'scope-consumer.json.gz')
        p=unit.make_profile(ps['P1']['payload']['graph'],baseline,original(ROOT)['images'])
        inputs={NORMAL+'/'+n for n in ('products.json.gz','scope-consumer.json.gz','cash-flow-profile.json','risk-profile.json','profile.json')}
        inputs|={PRIOR+'/'+n for n in ('profile.json','source-units.json','answer-supplement.json.gz','result.json')}
        inputs|={PLAN,REVIEW+'/preparation.json',REVIEW+'/profile.json'}
        inputs|={d['path'] for d in ps['P1']['payload']['request']['bundle']['documents']}
        inputs|={i['path'] for i in original(ROOT)['images'] if i['page'] in (53,54)}
        for source in read(ROOT/NORMAL/'profile.json')['source'].values():
            inputs.add(source['path']);inputs.update(i['path'] for i in source['images'])
        if not (ROOT/FIXTURE).exists():compressed(ROOT/FIXTURE,finite_fixture(ROOT))
        require(digest(load(ROOT/FIXTURE))==digest(finite_fixture(ROOT)),'Prepared fixture changed')
        write(folder/'profile.json',p)
        log=folder/f'tests-{index:02d}.log';xml=folder/f'tests-{index:02d}.xml'
        with log.open('x') as stream:
            subprocess.run([sys.executable,'-m','pytest',*TESTS,'-q','--junitxml='+str(xml)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1'},
                stdout=stream,stderr=subprocess.STDOUT,timeout=max(1,60-prep['seconds']-(time.monotonic()-start)),check=True)
        tree=ET.parse(xml).getroot();tests=sum(int(s.attrib.get('tests',0)) for s in tree.iter('testsuite'))
        (folder/'tests.xml').write_bytes(xml.read_bytes())
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    elapsed=time.monotonic()-start;prep['seconds']+=elapsed
    prep['stages'].append({'seconds':elapsed,'status':'FAIL' if error else 'PASS','error':error})
    prep.update(command=[sys.executable,'-m','scripts.prospectus_h1_unit_integration','prepare'],
        cpu_gpu='CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',exclusions='Agent authoring/reading, later proposal hashing excluded; preparation commands/tests charged')
    write(ledger,prep)
    if error:print(json.dumps({'stage':'preparation','error':error,'seconds':prep['seconds']}));return 1
    require(prep['seconds']<=60,'Preparation60second ceiling')
    f={'methods':{n:file_hash(ROOT/n) for n in METHODS},'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},
        'selector':SELECTOR,'focused_tests':tests,'parent_bindings_verified':True}
    write(folder/'frozen.json',f,exclusive=True)
    state=storage(ROOT,ROOT/SOURCE/'attempt-017')
    require(state['new_bytes']+12*1024**2+262144<SELECTOR['new_bytes']
        and state['combined_bytes']+12*1024**2+262144<SELECTOR['cumulative_bytes'],'H1 proposal/admission retention forecast')
    write(folder/'preflight.json',{**state,'additional_forecast_bytes':12*1024**2,'preparation_seconds':prep['seconds']},exclusive=True)
    auth=Authority(ROOT);program,tasks,_=auth.spec();require(program['revision']==211,'Expected211 baseline')
    proposal=deepcopy(program);proposal['revision']=212
    task=next(t for t in proposal['tasks'] if t['id']=='source-bes-dep-05')
    previous_dossier=task['dossier'];task.update(dossier=PLAN,timeout_seconds=210,unit_integration=SELECTOR,
        reason='Integrate original H1 individual unit conflict through normal scope consumer with full007/016 preservation; retain unit ambiguity, dash and original obligations.')
    task['inputs']=sorted(set(task['inputs'])|set(METHODS)|inputs|{previous_dossier,REVIEW+'/frozen.json',REVIEW+'/preflight.json'})
    proposal['budgets'][task['budget_key']]['maximum_new_attempts']=17
    proposal['build_contract']['criteria'][task['id']]=[
        {'id':'individual-unit-conflict','basis':'NAMED_CONDITIONAL_CHECK','validator':'h1-unit-conflict.v1',
         'description':'Original H1 unit conflict and unknown cells through normal consumer, with independent dimensional source checks'},
        {'id':'remaining-source-coverage','basis':'ORIGINAL_TASK_ACCEPTANCE','validator':None,
         'description':'All original source05 obligations remain; finite unit-conflict analysis cannot complete them'}]
    review={'baseline':authority_digest(program),'changes':['Normal optional H1 unit review with whole baseline preservation',
        'Independent original016 map and dimensional comparison; no unit correction or financial equality',
        'Separate finite criterion preserves original source05 acceptance and all earlier history'],
        'skeptical_audit':{'verdict':'PASS_AFTER_ORIGINAL_SOURCE_AND_PARENT_REVIEW','plan':PLAN,
            'findings':['Original53/54images visually reconfirm literal EUR million versus thousands',
                'Full007P1-P5parent bindings checked; same actual007consumer, full016supplement retained',
                'Finite unit comparison uses original positions; complete prior answers are primary, test totals explanatory',
                'No extraction or external opinion; unknown adjustment dash and incorporation alternatives preserved',
                'Measured preflight and bounded candidate/acceptance phases; no duplicate large answers',
                'Shared router changes require later current revalidation of earlier components; historical results survive']},
        'evidence_contract':{'question':'Can the normal H1 consumer preserve the printed dimensional conflict without changing prior answers?',
            'baseline':NORMAL+'/scope-consumer.json.gz','primary':'Whole007normal consumer and016supplement preservation; independent original-source map and scale check',
            'promotion_veto':'Hidden unit conflict, unit correction, financial equality, invented zero, dropped evidence or accepted adverse case',
            'continuation_veto':'Corrupt original source, frozen-method drift or declared cumulative time/storage ceilings',
            'explanatory':['test totals','runtime','size'],'not_concluded':['intended unit','official correction','source truth','automatic discovery','original task or build complete'],
            'artifacts':SOURCE+'/attempt-017'},'scope_unchanged':True,'budget_unchanged':False,
        'delivery_scope_changed':True,'delivery_authorization':proposal['build_contract']['authorization'],
        'original_obligations_preserved':True,
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':16,'new_maximum':17,
            'retained_attempts':[e['attempt'] for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']],
            'reason':'First normal-consumer integration of previously detached original unit conflict',
            'next_discriminating_check':'Actual normal consumer output and separate source/dimensional verifier with fresh adverse cases',
            'stop_condition':'60seconds prep,180candidate,180acceptance,2220cumulative;32MiB new/732MiB cumulative; no unchanged retry',
            'same_scope_authorization':'User requests refreshed general build and continued execution without external opinion'}}
    write(ROOT/REL/'proposals/h1-unit-212.json',proposal,exclusive=True)
    write(ROOT/REL/'proposals/h1-unit-212-review.json',review,exclusive=True)
    print(json.dumps({'stage':'prepared212','tests':tests,'seconds':prep['seconds'],'historical_seconds':state['historical_seconds'],
        'historical_bytes':state['historical_bytes'],'parent_bindings_verified':True}));return 0

def run(attempt_name):
    auth=Authority(ROOT);attempt=auth.path(attempt_name);admission=read(attempt/'admission.json')
    program,tasks,_=auth.spec();task=tasks['source-bes-dep-05']
    require(admission['binding']==auth.binding(task) and admission['task_spec']==task
        and admission['program_sha256']==authority_digest(program) and task['unit_integration']==SELECTOR,'Current H1 admission required')
    latest=next(e for e in reversed(auth.events()) if e.get('task')==task['id'])
    require(latest['kind']=='ADMIT' and latest['attempt']==attempt_name,'H1 attempt is not newly admitted')
    start=time.monotonic();f=frozen(ROOT)
    manifest={'command':[sys.executable,'-m','scripts.prospectus_h1_unit_integration','run','--attempt',attempt_name],
        'git_commit':admission['git_commit'],'environment':{'python':sys.version,'executable':sys.executable,'scope_module':scope.__file__},
        'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'N/A; deterministic dimensional checks',
        'methods':f['methods'],'data_version':f['inputs'],'plan':PLAN,'result':attempt_name+'/RESULT.md',
        'accounting':SELECTOR,'preparation_seconds':read(ROOT/REVIEW/'preparation.json')['seconds']}
    write(attempt/'started.json',manifest,exclusive=True)
    def expired(_s,_f):raise TimeoutError('H1 candidate180second ceiling')
    signal.signal(signal.SIGALRM,expired);signal.alarm(180)
    status,error,proof='PASS',None,{}
    try:
        storage(ROOT,attempt)
        ps=products(ROOT);off=consume(ROOT,ps);baseline=load(ROOT/NORMAL/'scope-consumer.json.gz')
        require(digest(off)==digest(baseline),'Unconfigured complete original H1 consumer differs')
        del ps,off,baseline
        print(json.dumps({'stage':'normal-consumer-off','status':'PASS'}),flush=True)
        delta,proof,composition=evaluate_result(ROOT);adverse=controls(ROOT)
        compressed(attempt/'answer-delta.json.gz',delta)
        write(attempt/'verification.json',proof,exclusive=True);write(attempt/'composition.json',composition,exclusive=True)
        write(attempt/'controls.json',adverse,exclusive=True)
        require(f['methods']=={n:file_hash(ROOT/n) for n in METHODS},'Methods changed during H1 candidate')
    except Exception as exc:
        status,error='FAIL',type(exc).__name__+': '+str(exc)
        (attempt/'failure-trace.txt').write_text(traceback.format_exc(limit=10)[-8192:])
    signal.alarm(0);manifest.update(status=status,error=error,wall_seconds=time.monotonic()-start)
    try:manifest['storage']=storage(ROOT,attempt)
    except Exception as exc:
        status,error='FAIL',str(exc);manifest.update(status=status,error=error,storage=storage(ROOT,attempt,False))
    write(attempt/'run-manifest.json',manifest,exclusive=True)
    write(attempt/'result.json',{'task':task['id'],'status':status,'error':error,'summary':proof,
        'task_complete':False,'whole_program_complete':False},exclusive=True)
    (attempt/'RESULT.md').write_text('# H1 individual unit conflict integration\n\nStatus: '+status+'.\n\n'
        +('The actual normal H1 consumer preserves every previous007field and the entire016supplement. The original labels are EUR million and thousands; the two matching net-profit numerals cannot establish financial equality. The adjustment dash remains unknown.\n\n' if status=='PASS' else str(error)+'\n\n')
        +'| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n'
        +('| Retain finite integration pending acceptance | Actual consumer and separate source dimensional check pass | Declared adverse cases refused | Intended unit and official correction unknown | Record, refresh, continue comparative accounting issue | Original task and whole build incomplete |\n' if status=='PASS' else '| Reject candidate | Failed | See trace | Local source or implementation failure | Changed discriminating repair | No package-direction rejection |\n')
        +'\nPost-run red team: the finite row mapping is supplied; agreement with a separate parser does not prove authenticity or intended units. Both editions or readings may share errors. An official correction could change the source conclusion. No source is rescaled, no legal interpretation is selected, and no financial authorization follows.\n')
    write(attempt/'outputs.json',{p.name:file_hash(p) for p in attempt.iterdir() if p.is_file() and p.name!='outputs.json'},exclusive=True)
    print(json.dumps({'stage':'h1-candidate','status':status,'error':error,'seconds':manifest['wall_seconds']}),flush=True)
    return 0 if status=='PASS' else 1

def record(attempt_name):
    folder=ROOT/REL/'continuation-reviews/h1-unit-212-record';folder.mkdir(parents=True,exist_ok=True)
    start=time.monotonic();error=None;result=None
    try:
        with (folder/'command.log').open('x') as log:
            result=subprocess.run([sys.executable,'-m','scripts.prospectus_control','record','--attempt',attempt_name],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=210,check=False)
    except Exception as exc:error=type(exc).__name__+': '+str(exc)
    event=next(e for e in reversed(Authority(ROOT).events()) if e.get('attempt')==attempt_name)
    receipt={'wall_seconds':time.monotonic()-start,'error':error,'exit_code':result.returncode if result else None,
        'kind':event['kind'],'reason':event.get('reason'),'build_acceptances':event.get('build_acceptances',[]),
        'event_sha256':event['sha256'],'command_log_sha256':file_hash(folder/'command.log')}
    write(folder/'receipt.json',receipt,exclusive=True);print(json.dumps(receipt))
    return 0 if 'individual-unit-conflict' in receipt['build_acceptances'] else 1

def main():
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','run','record']);parser.add_argument('--attempt');a=parser.parse_args()
    if a.action=='prepare':return prepare()
    if not a.attempt:parser.error('--attempt required')
    return run(a.attempt) if a.action=='run' else record(a.attempt)

if __name__=='__main__':raise SystemExit(main())
