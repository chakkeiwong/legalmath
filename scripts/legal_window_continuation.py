"""Resume deadline-interrupted work under the explicit October 24 time grant."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence, process_alive, process_identity
from scripts.legal_integration_acceptance_revision import historical_projection

KEY = 'window_continuation'
WORK = Path('artifacts/legal-mission-control/2026-10-24/window-continuation')
REVIEW = Path('docs/plans/legal-integration-window-continuation-2026-10-24.md')
SOURCE = Path('artifacts/legal-mission-control/2026-10-23/p14-optional-quote/live')
RUNTIME = WORK/'live'
USER = 'you have 72 hours more.  continue'
APPROVED = '2026-10-24T05:15:09+00:00'
DEADLINE = '2026-10-27T05:15:09+00:00'
CHANGED = ('scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_phased_live.py', 'src/legalmath/interpretation/assurance/time_authority.py')
SELF = 'scripts/legal_window_continuation.py'
TEST = 'tests/tooling/test_window_continuation.py'
IMPLEMENTATION = (*CHANGED, SELF, TEST)

def now():
    return datetime.now(timezone.utc).isoformat()

def projection(rows, mission=False):
    allowed = set(CHANGED) | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
            for r in rows if r['previous']['path'] in allowed}

def expected_program(old, revision, root, plan_reference):
    rows = read(Path(root)/revision['baseline']['path'])['archived']
    value = historical_projection(old, projection(rows))
    value['deadline_utc'] = DEADLINE
    value[KEY] = revision
    for task in value['tasks']:
        if task['id'] == 'baseline-p14':
            require(task['maximum_attempts'] == 5, 'Changed P14 continuation baseline')
            task['maximum_attempts'] = 6
            task['deliverable'] = str(BASE/'baseline-p14/attempt-6/result.json')
            task['inputs'] += [revision['review'],revision['result']]
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result','seed','time_extension','authorization')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference)
    return value

def validate_revision(program, root, plan_reference=None):
    if program['window_continuation'].get('service_inheritance'):
        from scripts.legal_window_service_correction import validate
        return validate(program, root, plan_reference)
    from scripts.legal_mission_execution import validate_program
    root = Path(root); revision = program[KEY]
    require(revision['profile']=='deadline-window-continuation.v1' and revision['user_instruction']==USER
        and revision['runtime']==str(RUNTIME) and revision['prior_detours']==65
        and revision['additional_consolidated_revision']==1 and revision['additional_task_attempts']==1
        and revision['reopened_nodes']==['baseline-p14']
        and revision['calls_added']==revision['service_replacements_added']==0
        and revision['attempts_reset'] is False, 'Changed continuation scope')
    for key in ('baseline','review','result','seed','authorization','time_extension','prior_program','prior_state','prior_binding','prior_grant','prior_ledger'):
        verify(root,revision[key])
    require(set(revision['implementation'])==set(IMPLEMENTATION),'Changed implementation scope')
    for pointer in revision['implementation'].values(): verify(root,pointer)
    baseline=read(root/revision['baseline']['path'])
    require(baseline['settled'] and baseline['calls']==4872 and baseline['service_charges']==195
        and baseline['prior_detours']==65,'Wrong settled baseline')
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed historical bytes')
        verify(root,row['archive'])
    for key,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
                     ('prior_grant',BASE/'live-grant.json'),('prior_ledger',BASE/'live-calls.json')):
        require(revision[key]==held[str(path)],'Changed predecessor '+key)
    old=read(root/revision['prior_program']['path'])
    before=read(root/revision['prior_state']['path'])
    require(KEY not in old and before['program_hash']==digest(old)
        and before['tasks']['baseline-p14']['status']=='FAILED'
        and len(before['tasks']['baseline-p14']['attempts'])==5,'Wrong owner checkpoint')
    authorization=read(root/revision['authorization']['path'])
    require(authorization==dict(user_instruction=USER,approved_at_utc=APPROVED,duration_seconds=259200,
        deadline_utc=DEADLINE,calls_added=0,replacements_added=0),'Changed explicit time authority')
    extension=read(root/revision['time_extension']['path'])
    prior_binding=read(root/revision['prior_binding']['path'])
    grant=read(root/revision['prior_grant']['path'])
    require(extension==dict(profile='integration-time-extension.v3',approved=True,user_instruction=USER,
        approved_at_utc=APPROVED,duration_seconds=259200,deadline_utc=DEADLINE,maximum_calls=8100,prior_calls=4872,
        original_grant=revision['prior_grant'],original_grant_hash=digest(grant),ledger_before=revision['prior_ledger'],
        review=revision['review'],previous_extension=prior_binding['time_extension'],
        previous_deadline_utc=old['deadline_utc'],prior_binding=revision['prior_binding'],
        prior_program=revision['prior_program'],authorization=revision['authorization']),'Changed extension')
    result=read(root/revision['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and not result['legal_acceptance'], 'Tests did not pass')
    for pointer in result['evidence']: verify(root,pointer)
    seed=read(root/revision['seed']['path'])
    require(seed['provider_calls']==0 and seed['arm_checkpoints']==revision['arm_checkpoints']
        and seed['retained_invalid_responses'] and seed['deadline_refusals_not_dispatched']==50,'Wrong checkpoint census')
    for arms in seed['arm_checkpoints'].values():
        for pointer in arms.values(): verify(root,pointer)
    for row in seed['imported']:
        for name in ('request','schema','result','dispatch'): verify(root,row[name])
        outcome=read(root/row['result']['path']); journal=read(root/row['dispatch']['path'])
        require(journal['calls'][row['key']]['result_hash']==digest(outcome)
            and journal['calls'][row['key']]['status']==outcome['status']==row['status'],'Changed imported receipt')
    with historical_evidence(root,projection(baseline['archived'])):
        validate_program(old,root)
    require(program==expected_program(old,revision,root,plan_reference),'Unreviewed graph or budget changes')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def project_state(before, program):
    value=deepcopy(before)
    row=value['tasks']['baseline-p14']
    require(row['status']=='FAILED' and len(row['attempts'])==5,'Wrong P14 state')
    row.update(status='PENDING', reason='Continue deadline-interrupted work once; preserve five attempts and every invalid response.')
    value['program_hash']=digest(program)
    value['events'].append(dict(action='REVIEWED_WINDOW_CONTINUATION',task_id='baseline-p14',at_utc=now(),
        review=program[KEY]['review'],attempts_reset=False,calls_added=0))
    return value

def validate_state_history(program,state,root):
    if program['window_continuation'].get('service_inheritance'):
        from scripts.legal_window_service_correction import validate_history
        return validate_history(program, state, root)
    from scripts.legal_review_repair import validate_state_history as prior_history
    prior_history(program,state,root)
    before=read(Path(root)/program[KEY]['prior_state']['path'])
    require(set(state['tasks'])==set(before['tasks']),'Changed owners')
    for tid, row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']),'Lost attempts')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed prior attempt '+tid)
        if row['status']=='SUCCEEDED': require(row==current,'Changed successful owner')
        elif tid!='baseline-p14' and row['status'] not in ('PENDING','RUNNING'):
            require(row==current,'Reopened unrelated settled owner')
    require(state['events'][:len(before['events'])]==before['events'],'Lost event history')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),'Lost veto')

def seed():
    from types import SimpleNamespace
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    from scripts.legal_integration_campaign import provider
    service = provider()  # Identity only; no check, reservation or request.
    old=read(ROOT/PROGRAM)
    checkpoints=deepcopy(old['review_repair']['optional_quote_validation']['arm_checkpoints'])
    imported=[]
    for journal in sorted((ROOT/SOURCE/'arms').glob('*/*/calls/dispatch.json')):
        directory=journal.parent.parent; qid,arm=directory.parent.name,directory.name
        require(qid in checkpoints and arm in checkpoints[qid],'Unknown arm')
        checkpoint=read(ROOT/checkpoints[qid][arm]['path'])
        checkpoint=deepcopy(checkpoint); identity,saved=read(directory/'identity.json'),read(journal)
        require(checkpoint['input_hash']==saved['input_hash'],'Changed checkpoint input')
        checker=BoundDispatch(service,directory/'calls',SimpleNamespace(limits=Limits(**identity['limits'])))
        checker.capacity_manager=True
        for key,row in saved['calls'].items():
            require(Path(key).name==key and row['status'] in ('VALIDATED','FAILED'),'Uncertain dispatch')
            folder=directory/'calls'/key
            pointers={n:ref(ROOT,folder/(n+'.json')) for n in ('request','schema','result')}
            pointers['dispatch']=ref(ROOT,journal)
            request,schema,result=[read(ROOT/pointers[n]['path']) for n in ('request','schema','result')]
            require(row['identity']==checker.request_identity(request,schema) and row['result_hash']==digest(result)
                and row['status']==result['status'] and not result.get('continuation_veto'),'Changed call receipt')
            if key in checkpoint['calls']:
                previous=read(ROOT/checkpoint['calls'][key]['result']['path'])
                require(previous==result,'Unexpected checkpoint collision')
            checkpoint['calls'][key]={**pointers,'mode':'VALIDATED' if result['status']=='VALIDATED' else 'RETAINED_FAILURE'}
            imported.append(dict(question=qid,arm=arm,key=key,status=result['status'],**pointers))
        path=WORK/'checkpoints'/qid/(arm+'.json'); save(ROOT/path,checkpoint)
        checkpoints[qid][arm]=ref(ROOT,path)
    progress=read(ROOT/'artifacts/legal-mission-control/2026-10-23/p14-optional-quote/progress/20261024T050855505149Z.json')
    pending=[r for r in progress['rows'] if (r.get('failure') or {}).get('reason')=='Phase exceeds original global window']
    require(len(pending)==50,'Changed unfinished population')
    require(len(imported)==608,'Changed settled dispatch census')
    value=dict(provider_calls=0,arm_checkpoints=checkpoints,imported=imported,
        retained_invalid_responses=True,deadline_refusals_not_dispatched=len(pending),unfinished=pending)
    save(ROOT/WORK/'seed.json',value)
    return dict(imported=len(imported),unfinished=len(pending),provider_calls=0)

def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_integration_campaign import provider
    from unittest.mock import patch
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        for path in (SOURCE.parent/'worker.lock',WORK/'worker.lock',STATE.with_suffix('.run.lock'),
                     DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            finish_transaction(ROOT,journal); return dict(registered=True,resumed=True)
        baseline=read(ROOT/WORK/'baseline.json'); rows=baseline['archived']
        held={r['previous']['path']:r['archive'] for r in rows}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'],'Predecessor changed '+str(path))
        old,before,binding=read(ROOT/PROGRAM),read(ROOT/STATE),read(ROOT/BASE/'current-binding.json')
        require(not process_alive(read(ROOT/SOURCE.parent/'worker.json')['process']),'Old supervisor active')
        require(all(not process_alive(t.get('live_supervisor')) for t in before['tasks'].values() if t['status']=='RUNNING'), 'Live owner remains')
        require(datetime.now(timezone.utc)<datetime.fromisoformat(DEADLINE),'Renewed window expired')
        for p in (ROOT/SOURCE).rglob('calls/dispatch.json'):
            require(not any(r['status']=='RESERVED' for r in read(p)['calls'].values()),'Uncertain dispatch remains')
        extension=dict(profile='integration-time-extension.v3',approved=True,user_instruction=USER,approved_at_utc=APPROVED,
            duration_seconds=259200,deadline_utc=DEADLINE,maximum_calls=8100,prior_calls=4872,
            original_grant=held[str(BASE/'live-grant.json')],original_grant_hash=digest(read(ROOT/BASE/'live-grant.json')),
            ledger_before=held[str(BASE/'live-calls.json')],review=ref(ROOT,REVIEW),previous_extension=binding['time_extension'],
            previous_deadline_utc=old['deadline_utc'],prior_binding=held[str(BASE/'current-binding.json')],
            prior_program=held[str(PROGRAM)],authorization=ref(ROOT,WORK/'authorization.json'))
        save(ROOT/WORK/'time-extension.json',extension)
        revision=dict(profile='deadline-window-continuation.v1',user_instruction=USER,work=str(WORK),runtime=str(RUNTIME),
            prior_detours=65,additional_consolidated_revision=1,additional_task_attempts=1,reopened_nodes=['baseline-p14'],
            calls_added=0,service_replacements_added=0,attempts_reset=False,baseline=ref(ROOT,WORK/'baseline.json'),
            review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),seed=ref(ROOT,WORK/'seed.json'),
            authorization=ref(ROOT,WORK/'authorization.json'),time_extension=ref(ROOT,WORK/'time-extension.json'),
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            prior_grant=held[str(BASE/'live-grant.json')],prior_ledger=held[str(BASE/'live-calls.json')],
            implementation={p:ref(ROOT,p) for p in IMPLEMENTATION},arm_checkpoints=read(ROOT/WORK/'seed.json')['arm_checkpoints'])
        program=expected_program(old,revision,ROOT,ref(ROOT,PLAN)); state=project_state(before,program)
        stage=WORK/'registration-stage'
        save(ROOT/stage/'program.json',program);save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding['bindings']=historical_projection(binding['bindings'],projection(rows,True))
        binding.update(program=pointer,review=revision['review'],user_instruction=USER,predecessor=revision['prior_binding'],
            phase_service_predecessor=revision['prior_binding'],
            time_extension=revision['time_extension'],effective_deadline_utc=DEADLINE,window_continuation=revision)
        binding['bindings'] += [pointer,ref(ROOT,PLAN),*[revision[k] for k in ('review','result','seed','time_extension','authorization')],*revision['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in rows if (r['previous']['path'],r['previous']['sha256']) not in known]
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),projection(rows,True))
        master=mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'): master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),**{KEY:revision})
        reason='Continue deadline-interrupted P14 once with every prior result preserved, then Gatecoin and independent original-tool owners under the renewed 72-hour window and unchanged spending ceilings.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='integration-window-continuation-2026-10-24',task_id='product-contribution',kind='product_evaluation',
            outcome='no_advance',decision=reason,next_task='product-contribution',next_task_reason=reason,recorded_at_utc=now(),
            result_evidence=[pointer,revision['review'],revision['result'],revision['time_extension']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,66))
        targets={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text,original_bytes=Path.read_text,Path.read_bytes
        with patch.object(Path,'read_text',lambda path,*a,**k:original_text(targets.get(path,path),*a,**k)), \
             patch.object(Path,'read_bytes',lambda path,*a,**k:original_bytes(targets.get(path,path),*a,**k)):
            require(len(provider().check()['calls'])==4872,'Staged authority changed charges')
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,deadline_utc=DEADLINE,calls_added=0,replacements_added=0)

def worker():
    work=Path(read(ROOT/PROGRAM)['window_continuation'].get('service_inheritance',{}).get('work',str(WORK)))
    from scripts import legal_integration_phased_live as live, legal_integration_campaign as campaign
    from scripts.legal_review_repair import live as drain
    from scripts.legal_review_repair_service import recover
    with (ROOT/work/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(ROOT/work/'worker.json',dict(process=process_identity(os.getpid()),at_utc=now()))
        try:
            execution=MasterExecution(ROOT,PROGRAM,STATE)
            for tid in ('baseline-p14','baseline-gatecoin','tool-gatecoin-bm25'):
                while True:
                    view=execution.summary()
                    if tid not in view['ready'] and tid not in view['running']: break
                    state=read(ROOT/STATE)
                    if state['tasks'][tid].get('service_checkpoint') and not state['tasks'][tid].get('service_resume'):
                        recover(); continue
                    binding=read(ROOT/BASE/'current-binding.json')
                    circuit=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-circuit.json')
                    if circuit['open']: recover(); continue
                    service=campaign.provider(); service.check()
                    q,tool=(tid[9:],None) if tid.startswith('baseline-') else tid[5:].split('-',1)
                    with (ROOT/live.LIVE/'supervisor.lock').open('a') as shared:
                        fcntl.flock(shared,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        value=campaign.complete_node(execution,tid,lambda:live.answer(q,tool,service))
                    if isinstance(value,dict) and value.get('service_deferred'): recover(); continue
                    save(ROOT/work/(tid+'.result.json'),dict(value=value,at_utc=now()))
                    require(not isinstance(value,dict) or not value.get('continuation_veto'),
                        'Shared authority veto; no further live owners')
                    break
            save(ROOT/work/'live-result.json',drain())
        except BaseException as exc:
            import traceback
            save(ROOT/work/'worker-error.json',dict(reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc(),at_utc=now()))
            raise
        finally:
            for name,command in (('refresh',[str(ROOT/'.venv/bin/python'),'scripts/legal_mission_control.py','refresh']),
                                 ('status',[str(ROOT/'.venv-context/bin/python'),'scripts/legal_integration_master.py','status'])):
                with (ROOT/work/(name+'.stdout')).open('w') as out,(ROOT/work/(name+'.stderr')).open('w') as err:
                    code=subprocess.call(command,cwd=ROOT,stdout=out,stderr=err)
                save(ROOT/work/(name+'.exit.json'),dict(exit_code=code,at_utc=now()))
            save(ROOT/work/'finished.json',dict(at_utc=now(),integration_complete=False))

def arm():
    if read(ROOT/PROGRAM)['window_continuation'].get('service_inheritance'):
        from scripts.legal_window_service_correction import arm as corrected_arm
        return corrected_arm()
    from scripts.legal_integration_campaign import provider
    require(read(ROOT/WORK/'registration.json')['status']=='COMMITTED','Registration incomplete')
    with (ROOT/WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/WORK/'armed.json'
        if path.exists():
            saved=read(path);require(process_alive(saved['process']),'Ended successor requires review')
            return saved
        provider().check()
        with (ROOT/WORK/'worker.log').open('a') as log:
            p=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(ROOT/SELF),'worker'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        value=dict(process=process_identity(p.pid),at_utc=now())
        require(value['process'] is not None,'Worker ended at startup');save(path,value);return value

def status():
    receipts={n:read(ROOT/WORK/n) for n in ('armed.json','worker.json','worker-error.json','finished.json','registration-check.json') if (ROOT/WORK/n).exists()}
    return dict(at_utc=now(),receipts=receipts,alive=process_alive(receipts.get('worker.json',{}).get('process')),
        calls=len(read(ROOT/BASE/'live-calls.json')['calls']),deadline_utc=DEADLINE)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['seed','register','arm','worker','status'])
    args=parser.parse_args();print(json.dumps(globals()[args.action](),indent=2))
