"""Stage, verify, and register the finite retry continuation without live calls."""
from pathlib import Path
from contextlib import ExitStack
from copy import deepcopy
import argparse
import hashlib
import importlib
import json
import os
import shutil
import sys
import time

ROOT=Path('/home/chakwong/python/legalmath')
WORK=Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
TREE=Path('/tmp/legalmath-repaired-retry-continuation')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,save,ref,verify,require,digest
from scripts.legal_integration_master import BASE,DOC,PROGRAM,STATE,PLAN
from scripts import legal_baseline_corpus_deployment as deployment

def candidate_imports():
    for name in list(sys.modules):
        if name=='scripts' or name.startswith('scripts.') or name=='legalmath' or name.startswith('legalmath.'):
            del sys.modules[name]
    sys.path[:0]=[str(TREE/'src'),str(TREE)]
    import scripts
    scripts.__path__=[str(TREE/'scripts')]
    for name in ('legal_mission_execution','legal_integration_master','legal_mission_control','legal_repaired_retry_continuation'):
        module=importlib.import_module('scripts.'+name);module.ROOT=ROOT

def prepare():
    require(not (ROOT/WORK/'baseline.json').exists(),'Baseline already retained')
    commands=read(ROOT/WORK/'admission-command-results.json')['commands']
    require(len(commands)==3 and all(r['exit_code']==0 for r in commands),'Admission incomplete')
    outputs={p.relative_to(ROOT/WORK/'source').as_posix():p for p in (ROOT/WORK/'source').rglob('*.py')}
    for p,source in outputs.items():compile(source.read_text(),p,'exec')
    binding=read(ROOT/BASE/'current-binding.json');service=Path(binding['phase_service_scope']['path']).parent
    old_live=ROOT/deployment.OLD_WORK/'live'
    journals=[p.relative_to(ROOT).as_posix() for p in sorted(old_live.glob('arms/*/*/calls/dispatch.json'))]
    watched=[PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',
        BASE/'live-grant.json',BASE/'current-stage.json',service/'service-circuit.json',service/'service-recovery.json',
        PLAN,*map(Path,outputs),*map(Path,journals)]
    with ExitStack() as stack:
        deployment.acquire_locks(ROOT,stack,deployment.lock_paths(ROOT,binding,journals))
        deployment.stopped(ROOT)
        state=read(ROOT/STATE)
        for tid,row in state['tasks'].items():
            if row['status']=='RUNNING':
                from scripts.legal_review_service_checkpoint import checked
                checked(ROOT,tid,row)
                require(not deployment.process_alive(row.get('live_supervisor')),'Active owner '+tid)
        archived,absent=[],[]
        for path in dict.fromkeys(watched):
            if (ROOT/path).exists():
                target=WORK/'before'/path;(ROOT/target).parent.mkdir(parents=True,exist_ok=True)
                (ROOT/target).write_bytes((ROOT/path).read_bytes())
                archived.append(dict(previous=ref(ROOT,path),archive=ref(ROOT,target)))
            else:absent.append(str(path))
        ledger=read(ROOT/BASE/'live-calls.json');recovery=read(ROOT/service/'service-recovery.json')
        require(len(ledger['calls'])==6471 and ledger['maximum']==8100 and len(recovery['charges'])==288,
            'Allowance baseline changed')
        save(ROOT/WORK/'baseline.json',dict(archived=archived,absent_paths=absent,changed_paths=sorted(outputs),
            calls=6471,service_replacements=288,journals=journals,at_utc=deployment.now()))
    save(ROOT/WORK/'authorization.json',dict(user_instruction='you have 500 retries more. continue. What are the problems we have to fix?',
        additional_service_recoveries=500,cumulative_service_recoveries=788,global_calls_added=0,
        deadline_extended=False,deadline_utc='2026-10-27T05:15:09+00:00',
        original_call_ceiling=8100,attempt_additions={'baseline-p14':1,'baseline-gatecoin':1},
        protected_question_reserves_unchanged=True,review=ref(ROOT,'docs/plans/legal-repaired-baselines-retry-continuation-2026-10-26.md')))
    plan=(ROOT/PLAN).read_text()+'''
## October 26 repaired continuation and 500 additional retries

The user grants 500 additional service retries. The reviewed continuation in
docs/plans/legal-repaired-baselines-retry-continuation-2026-10-26.md increases
only the replacement ceiling, from 288 to 788, within the unchanged 8,100 calls
and October 27 05:15:09 UTC deadline. It preserves all prior charges and the
protected original-question budgets. P14 and Gatecoin receive one repaired
continuation each; the paused BM25 owner retains its current attempt. Successful
answers and corrections are fixed. Failed reviews retry only under authenticated
checkpoints; genuine unresolved legal findings remain open. Corpus qualification
requires actual evidence, and unrelated original questions continue independently.
'''
    target=ROOT/WORK/'source'/PLAN;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(plan)
    require(not TREE.exists(),'Candidate tree already exists')
    for folder in ('scripts','src','tests'):
        shutil.copytree(ROOT/folder,TREE/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for path,source in outputs.items():
        target=TREE/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
    save(ROOT/WORK/'preparation.json',dict(sources={p:ref(ROOT,f) for p,f in outputs.items()},
        plan=ref(ROOT,WORK/'source'/PLAN),provider_calls=0))
    return dict(prepared=True,source_files=len(outputs),provider_calls=0)

def seed():
    from types import SimpleNamespace
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    from legalmath.interpretation.assurance.phased.evidence_store import load_exact
    from scripts.legal_integration_campaign import provider
    require(not (ROOT/WORK/'seed.json').exists(),'Seed already retained')
    p=read(ROOT/PROGRAM);baseline=read(ROOT/WORK/'baseline.json');deployment.assert_unchanged(ROOT,baseline)
    service=provider();checkpoints=deepcopy(p['window_continuation']['arm_checkpoints']);census=[]
    for journal_name in baseline['journals']:
        journal=ROOT/journal_name;directory=journal.parent.parent;qid,arm=directory.parent.name,directory.name
        checkpoint=deepcopy(read(ROOT/checkpoints[qid][arm]['path']))
        saved=read(journal);identity=read(directory/'identity.json')
        require(checkpoint['input_hash']==saved['input_hash'],'Changed checkpoint input')
        checker=BoundDispatch(service,directory/'calls',SimpleNamespace(limits=Limits(**identity['limits'])))
        checker.capacity_manager=True
        checkpoint.update(retry_profile='repaired-review-checkpoint.v1',
            retry_review=ref(ROOT,'docs/plans/legal-repaired-baselines-retry-continuation-2026-10-26.md'),
            reviewed_failed_results=[])
        tasks={'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT','ASSESS_REVIEW_WARRANT',
            'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS','AUDIT_ANSWER_AND_DETAILED_ACCOUNT'}
        counts={}
        for key,row in saved['calls'].items():
            require(Path(key).name==key and row['status'] in ('FAILED','VALIDATED'),'Uncertain dispatch')
            folder=journal.parent/key
            refs={n:ref(ROOT,folder/(n+'.json')) for n in ('request','schema','result')}
            refs['dispatch']=ref(ROOT,journal)
            request,schema,result=[read(ROOT/refs[n]['path']) for n in ('request','schema','result')]
            require(row['identity']==checker.request_identity(request,schema) and row['result_hash']==digest(result)
                and row['status']==result['status'] and not result.get('continuation_veto'),'Changed retained call '+key)
            if key in checkpoint['calls']:
                old=checkpoint['calls'][key]
                same=(read(ROOT/old['request']['path'])==request and read(ROOT/old['schema']['path'])==schema
                    and read(ROOT/old['result']['path'])==result)
                if not same:
                    require(request['task'] not in ('ANSWER_ORIGINAL_QUESTION','CORRECT_REVIEWED_ANSWER'),
                        'Different successful answer checkpoint '+key)
                    checkpoint['calls'][key+'-historical-'+old['result']['sha256'][:12]]={**old,'dispatch_key':key}
            mode='VALIDATED' if result['status']=='VALIDATED' else 'RETAINED_FAILURE'
            if result['status']=='FAILED' and request['task'] in tasks:
                mode='REVIEWED_FAILURE_RETRY';checkpoint['reviewed_failed_results'].append(refs['result'])
            if (result['status']=='FAILED' and request['task']=='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS'
                    and 'audit-group-' in key and (folder/'raw.json').exists()):
                # Reuse valid siblings from malformed groups; only individual failures retry.
                mode='RETAINED_FAILURE'
                refs['raw']=ref(ROOT,folder/'raw.json')
                checkpoint['reviewed_failed_results'].remove(refs['result'])
            checkpoint['calls'][key]={**refs,'mode':mode}
            category=request['task']+' / '+mode;counts[category]=counts.get(category,0)+1
        if qid=='p14' and arm=='baseline':
            answers=load_exact(directory/'answers.json');fixed=answers[qid]['correction']
            require(fixed['candidate']['status']=='VALIDATED' and 'correction-p14' in checkpoint['calls'],
                'Fixed successful correction missing')
            request=read(directory/'calls/correction-p14/request.json')
            fixed_path=WORK/'checkpoints'/qid/'fixed-correction.json'
            save(ROOT/fixed_path,dict(profile='fixed-corrected-answer-continuation.v1',question_id=qid,
                question=request['question'],answers=ref(ROOT,directory/'answers.json'),
                original_hash=digest(fixed['original_answer']['value']),candidate_hash=digest(fixed['candidate']['value']),
                new_answer_calls=0,legal_acceptance=False))
            checkpoint['fixed_correction']=ref(ROOT,fixed_path)
        path=WORK/'checkpoints'/qid/(arm+'.json');save(ROOT/path,checkpoint);checkpoints[qid][arm]=ref(ROOT,path)
        census.append(dict(question=qid,arm=arm,calls=len(saved['calls']),counts=counts,
            retryable=len(checkpoint['reviewed_failed_results'])))
    save(ROOT/WORK/'seed.json',dict(arm_checkpoints=checkpoints,census=census,reserved=0,
        provider_calls=0,retained_invalid_responses=True,successful_answers_fixed=True))
    return dict(census=census,provider_calls=0)

def tests():
    candidate_imports();os.chdir(TREE)
    import pytest
    names=['tests/assurance/test_repaired_retry_continuation.py','tests/tooling/test_repaired_retry_continuation.py',
        'tests/assurance/test_review_deployment_service.py','tests/assurance/test_review_repair_budget_service.py',
        'tests/assurance/test_baseline_corpus_repairs.py','tests/assurance/test_corpus_passage_attribution.py',
        'tests/assurance/test_context_exact_references.py','tests/assurance/test_context_need_disposition.py',
        'tests/assurance/test_downstream_capacity.py','tests/assurance/test_requirement_correction.py',
        'tests/assurance/test_source_review_repair.py','tests/tooling/test_baseline_corpus_deployment.py']
    raise SystemExit(pytest.main([*names,'-q','--junitxml='+str(ROOT/WORK/'tests-staged.xml')]))

def stage():
    from xml.etree import ElementTree as ET
    from scripts.legal_integration_acceptance_revision import historical_projection
    suite=ET.parse(ROOT/WORK/'tests-staged.xml').getroot();cases=list(suite.iter('testcase'))
    require(cases and not list(suite.iter('failure')) and not list(suite.iter('error')),'Staged tests failed')
    baseline=read(ROOT/WORK/'baseline.json');deployment.assert_unchanged(ROOT,baseline)
    preparation=read(ROOT/WORK/'preparation.json')
    for p in preparation['sources'].values():verify(ROOT,p)
    save(ROOT/WORK/'local-result.json',dict(verdict='PASS',provider_calls=0,legal_acceptance=False,
        tests=len(cases),evidence=[ref(ROOT,WORK/'tests-staged.xml'),ref(ROOT,WORK/'seed.json')]))
    candidate_imports()
    from scripts import legal_repaired_retry_continuation as module
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_REPAIRED_RETRY_POLICY
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    implementation={p:dict(path=p,sha256=v['sha256']) for p,v in preparation['sources'].items()}
    revision=dict(profile=module.PROFILE,work=str(WORK),runtime=str(WORK/'live'),prior_detours=67,
        additional_consolidated_revision=1,calls_added=0,replacements_added=500,
        attempt_additions={k:1 for k in module.ATTEMPTS},attempts_reset=False,
        review=ref(ROOT,module.REVIEW),result=ref(ROOT,WORK/'local-result.json'),baseline=ref(ROOT,WORK/'baseline.json'),
        authorization=ref(ROOT,WORK/'authorization.json'),seed=ref(ROOT,WORK/'seed.json'),
        prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
        implementation=implementation,service_policy=SERVICE_REPAIRED_RETRY_POLICY,
        arm_checkpoints=read(ROOT/WORK/'seed.json')['arm_checkpoints'])
    plan= dict(path=str(PLAN),sha256=preparation['plan']['sha256'])
    old=read(ROOT/PROGRAM);program=module.expected_program(old,revision,ROOT,plan)
    state=module.project_state(read(ROOT/STATE),program,module.now());target=WORK/'registration-stage'
    save(ROOT/target/'program.json',program);save(ROOT/target/'state.json',state)
    pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,target/'program.json')['sha256'])
    binding=read(ROOT/BASE/'current-binding.json');folder=Path(binding['phase_service_scope']['path']).parent
    binding['bindings']=historical_projection(binding['bindings'],module.mapping(baseline,True))
    binding.update(program=pointer,**{module.KEY:revision},baseline_corpus_repair_hold=False,
        predecessor=revision['prior_binding'],phase_service_predecessor=revision['prior_binding'],
        service_recovery_policy=SERVICE_REPAIRED_RETRY_POLICY,
        repaired_retry_service_predecessor=held[str(folder/'service-recovery.json')],
        repaired_retry_authority=revision['authorization'],user_instruction=read(ROOT/WORK/'authorization.json')['user_instruction'])
    binding['bindings'] += [pointer,plan,revision['review'],revision['result'],revision['baseline'],revision['authorization'],revision['seed'],*implementation.values()]
    known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
    binding['historical_archives'] += [r for r in baseline['archived'] if (r['previous']['path'],r['previous']['sha256']) not in known]
    save(ROOT/target/'binding.json',binding)
    recovery=read(ROOT/folder/'service-recovery.json')
    save(ROOT/target/'service-recovery.json',{**recovery,'profile':SERVICE_REPAIRED_RETRY_POLICY['profile'],'maximum':788})
    mission=historical_projection(read(ROOT/DOC/'mission.json'),module.mapping(baseline,True));master=mission['integration_master']
    for k in master:
        if k in program and isinstance(program[k],dict) and program[k].get('profile'):master[k]=deepcopy(program[k])
    master.update(program=pointer,plan=plan,**{module.KEY:revision})
    reason='Continue repaired failed reviews with 500 additional service replacements; preserve fixed answers, all charges, original-question reserves, and independent branches. Corpus legal evidence remains open.'
    mission['next_task_reason']=reason
    mission['history'].append(dict(id='repaired-retry-continuation-2026-10-26',task_id='product-contribution',kind='product_evaluation',
        outcome='no_advance',decision=reason,next_task='product-contribution',next_task_reason=reason,recorded_at_utc=module.now(),
        result_evidence=[pointer,revision['review'],revision['result'],revision['authorization']]))
    save(ROOT/target/'mission.json',mission)
    return dict(staged=True,provider_calls=0,tests=len(cases))

def validate_stage():
    from unittest.mock import patch
    baseline=read(ROOT/WORK/'baseline.json');deployment.assert_unchanged(ROOT,baseline)
    prep=read(ROOT/WORK/'preparation.json');stage_path=WORK/'registration-stage'
    overrides={ROOT/p:ROOT/v['path'] for p,v in prep['sources'].items()}
    overrides[ROOT/PLAN]=ROOT/prep['plan']['path']
    service=Path(read(ROOT/BASE/'current-binding.json')['phase_service_scope']['path']).parent
    overrides.update({ROOT/p:ROOT/stage_path/n for p,n in ((PROGRAM,'program.json'),(STATE,'state.json'),
        (BASE/'current-binding.json','binding.json'),(service/'service-recovery.json','service-recovery.json'))})
    originals={n:getattr(Path,n) for n in ('read_text','read_bytes','is_file','exists')}
    candidate_imports();started=time.monotonic()
    with ExitStack() as stack:
        for name,method in originals.items():
            stack.enter_context(patch.object(Path,name,lambda p,*a,_method=method,**k:_method(overrides.get(p,p),*a,**k)))
        from scripts.legal_integration_repair_execution import validate_staged_mission
        from scripts.legal_integration_campaign import provider
        from scripts import legal_mission_control
        mission=read(ROOT/stage_path/'mission.json');legal_mission_control.verify_refs(ROOT,mission)
        print(json.dumps(dict(checkpoint='staged_references',status='PASS')),flush=True)
        checked=validate_staged_mission(ROOT,stage_path,mission,68)
        print(json.dumps(dict(checkpoint='staged_mission',status='PASS')),flush=True)
        service_object=provider();ledger=service_object.check();binding=read(ROOT/BASE/'current-binding.json')
        require(len(ledger['calls'])==6471 and ledger['maximum']==8100,'Provider preflight changed allowance')
        require(service_object.allowance.service_scope()[0]==binding['phase_service_scope'],'Changed service scope')
        from legalmath.interpretation.assurance.time_authority import effective_deadline
        require(effective_deadline(ROOT,ROOT/BASE)=='2026-10-27T05:15:09+00:00','Changed deadline')
    result=dict(verdict='PASS',provider_calls=0,elapsed_seconds=time.monotonic()-started,mission=checked,
        files={str(p.relative_to(ROOT)):ref(ROOT,v) for p,v in overrides.items()},mission_candidate=ref(ROOT,stage_path/'mission.json'))
    save(ROOT/WORK/'staged-verification.json',result);return result

def commit():
    prep=read(ROOT/WORK/'preparation.json');baseline=read(ROOT/WORK/'baseline.json')
    checked=read(ROOT/WORK/'staged-verification.json');require(checked['verdict']=='PASS','No staged verification')
    for pointer in [*checked['files'].values(),checked['mission_candidate']]:verify(ROOT,pointer)
    binding=read(ROOT/BASE/'current-binding.json');folder=Path(binding['phase_service_scope']['path']).parent
    with ExitStack() as stack:
        deployment.acquire_locks(ROOT,stack,deployment.lock_paths(ROOT,binding,baseline['journals']))
        deployment.assert_unchanged(ROOT,baseline);deployment.stopped(ROOT)
        targets={p:Path(v['path']) for p,v in prep['sources'].items()}
        targets[str(PLAN)]=Path(prep['plan']['path'])
        stage=WORK/'registration-stage'
        targets.update({str(p):stage/n for p,n in ((PROGRAM,'program.json'),(STATE,'state.json'),
            (DOC/'mission.json','mission.json'),(BASE/'current-binding.json','binding.json'),(folder/'service-recovery.json','service-recovery.json'))})
        writes=[dict(path=p,before=ref(ROOT,p) if (ROOT/p).exists() else None,replacement=ref(ROOT,v)) for p,v in targets.items()]
        save(ROOT/WORK/'registration.json',dict(profile='baseline-corpus-deployment-transaction.v1',status='PREPARED',writes=writes))
        deployment.finish_transaction(ROOT,WORK/'registration.json')
    return dict(registered=True,replacements_added=500,provider_calls=0)

def verify_installed():
    from scripts.legal_integration_campaign import provider
    p=read(ROOT/PROGRAM);r=p['repaired_retry_continuation']
    for pointer in r['implementation'].values():verify(ROOT,pointer)
    service=provider();ledger=service.check();binding=read(ROOT/BASE/'current-binding.json')
    require(len(ledger['calls'])==6471 and not binding['baseline_corpus_repair_hold'],'Unexpected installed allowance')
    prior=read(ROOT/r['prior_binding']['path'])
    require(binding['review']==prior['review'] and binding['execution_budget']==prior['execution_budget'],
        'Changed time review or protected budget')
    result=dict(verdict='PASS',provider_calls=0,installed_files=len(r['implementation']),
        calls=len(ledger['calls']),maximum_calls=ledger['maximum'],service_ceiling=788,
        binding=ref(ROOT,BASE/'current-binding.json'),at_utc=deployment.now())
    save(ROOT/WORK/'installed-verification.json',result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','seed','tests','stage','validate_stage','commit','verify_installed'])
    print(json.dumps(globals()[parser.parse_args().action](),indent=2))
