"""Finite reviewed retry successor; historical evidence and answers stay immutable."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
from scripts.legal_integration_master import BASE,DOC,PROGRAM,STATE,PLAN,MasterExecution
from scripts.legal_mission_execution import read,save,ref,verify,require,digest,historical_evidence,process_alive,process_identity
from scripts.legal_integration_acceptance_revision import historical_projection

KEY = 'repaired_retry_continuation'
PROFILE = 'reviewed-repaired-retry-continuation.v1'
WORK = Path('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation')
REVIEW = Path('docs/plans/legal-repaired-baselines-retry-continuation-2026-10-26.md')
SELF = 'scripts/legal_repaired_retry_continuation.py'
ATTEMPTS = {'baseline-p14':7,'baseline-gatecoin':5}
PROBE_FIX_PATHS = {'scripts/legal_review_repair_service.py', SELF,
    'tests/assurance/test_repaired_retry_continuation.py'}

def now(): return datetime.now(timezone.utc).isoformat()

def mapping(baseline, mission=False):
    allowed = set(baseline['changed_paths']) | {str(PLAN)}
    if mission: allowed.add(str(PROGRAM))
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in baseline['archived'] if r['previous']['path'] in allowed}

def expected_program(old,revision,root,plan_reference):
    baseline = read(Path(root)/revision['baseline']['path'])
    value = historical_projection(old,mapping(baseline))
    value[KEY] = deepcopy(revision)
    for tid,count in ATTEMPTS.items():
        task = next(t for t in value['tasks'] if t['id']==tid)
        require(task['maximum_attempts']==count,'Changed attempt baseline')
        task.update(maximum_attempts=count+1,deliverable=str(BASE/tid/f'attempt-{count+1}'/'result.json'))
        task['inputs'] += [revision['review'],revision['result']]
    value['protected_evidence'] += [revision[k] for k in ('review','result','baseline','authorization','seed')]
    value['protected_evidence'] += list(revision['implementation'].values())
    if revision.get('probe_capacity_repair'):
        fix=revision['probe_capacity_repair']
        value['protected_evidence'] += [fix[k] for k in ('review','result','prior_program','prior_binding',
            'prior_state','prior_calls','prior_recovery','prior_circuit','prior_stage','prior_error','prior_finished')]
    value['protected_evidence'].append(plan_reference)
    return value

def validate_probe_fix(revision,root):
    fix=revision.get('probe_capacity_repair')
    if fix is None:return
    root=Path(root)
    require(fix['profile']=='reviewed-undispatched-probe-capacity.v1'
        and fix['calls_added']==fix['attempts_added']==fix['replacements_added']==fix['detours_added']==0
        and fix['failed_slot']==6471 and fix['replacement_index']==289
        and fix['successor_stage_path']==str(WORK/'probe-capacity-fix'/'stage.json'),
        'Unreviewed probe capacity correction')
    for k in ('review','result','prior_program','prior_binding','prior_state','prior_calls',
            'prior_recovery','prior_circuit','prior_stage','prior_error','prior_finished'):
        verify(root,fix[k])
    before=read(root/fix['prior_program']['path'])[KEY]
    require(not before.get('probe_capacity_repair'),'Repeated bounded probe correction')
    changed={p for p in before['implementation'] if before['implementation'][p]!=revision['implementation'][p]}
    require(changed==PROBE_FIX_PATHS and set(fix['sources'])==changed,'Unreviewed probe source population')
    expected=deepcopy(before);expected['probe_capacity_repair']=deepcopy(fix)
    for name,row in fix['sources'].items():
        require(row['prior_sha256']==before['implementation'][name]['sha256']
            and row['prior_sha256']==row['archive']['sha256']
            and row['current']==revision['implementation'][name],'Changed probe source history')
        verify(root,row['archive']);verify(root,row['current'])
        expected['implementation'][name]=row['current']
    require(expected==revision,'Probe correction changed authority, attempts or checkpoint selection')
    calls=read(root/fix['prior_calls']['path']);recovery=read(root/fix['prior_recovery']['path'])
    circuit=read(root/fix['prior_circuit']['path']);charge=recovery['charges'][-1]
    require(len(calls['calls'])==6471 and calls['maximum']==8100
        and len(recovery['charges'])==289 and recovery['maximum']==788
        and charge['failed_slot']==6471 and charge['stage']==fix['prior_stage']
        and not circuit['open'] and circuit['half_open_reserved'] is False
        and circuit['half_open_request_hash']==charge['request_hash']
        and circuit['half_open_schema_hash']==charge['schema_hash'], 'Uncertain probe dispatch baseline')
    result=read(root/fix['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['legal_acceptance'] is False,
        'Probe correction local checks failed')
    for pointer in result['evidence']:verify(root,pointer)

def project_state(before,program,timestamp):
    state = deepcopy(before)
    for tid,count in ATTEMPTS.items():
        row=state['tasks'][tid]
        require(row['status']=='FAILED' and len(row['attempts'])==count,'Different continuation owner')
        row.update(status='PENDING',reason='One reviewed repaired continuation; all old attempts retained')
        row.pop('result',None)
    state['program_hash']=digest(program)
    state['events'].append(dict(task_id=None,action='REPAIRED_RETRY_CONTINUATION',at_utc=timestamp,
        review=program[KEY]['review'],calls_added=0,replacements_added=500,attempt_additions={k:1 for k in ATTEMPTS}))
    return state

def validate(program,root,plan_reference):
    from scripts.legal_mission_execution import validate_program
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_REPAIRED_RETRY_POLICY
    root=Path(root);r=program[KEY]
    require(r['profile']==PROFILE and r['work']==str(WORK) and r['runtime']==str(WORK/'live')
        and r['prior_detours']==67 and r['additional_consolidated_revision']==1
        and r['calls_added']==0 and r['replacements_added']==500
        and r['attempt_additions']=={k:1 for k in ATTEMPTS}
        and r['attempts_reset'] is False and r['service_policy']==SERVICE_REPAIRED_RETRY_POLICY,
        'Unreviewed retry continuation scope')
    for k in ('review','result','baseline','authorization','seed','prior_program','prior_state','prior_binding'):
        verify(root,r[k])
    baseline=read(root/r['baseline']['path'])
    require(baseline['calls']==6471 and baseline['service_replacements']==288,'Wrong retry baseline')
    held={row['previous']['path']:row['archive'] for row in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed historical bytes')
        verify(root,row['archive'])
    for k,p in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')):
        require(r[k]==held[str(p)],'Wrong retry predecessor')
    require(set(r['implementation'])==set(baseline['changed_paths']),'Different implementation population')
    for p in r['implementation'].values(): verify(root,p)
    validate_probe_fix(r,root)
    authority=read(root/r['authorization']['path'])
    require(authority['additional_service_recoveries']==500 and authority['cumulative_service_recoveries']==788
        and authority['global_calls_added']==0 and authority['deadline_extended'] is False
        and authority['deadline_utc']=='2026-10-27T05:15:09+00:00','Unreviewed retry authority')
    old=read(root/r['prior_program']['path'])
    require(KEY not in old,'Repeated retry revision')
    with historical_evidence(root,mapping(baseline)): validate_program(old,root)
    result=read(root/r['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and not result['legal_acceptance'],
        'Retry candidate did not pass local checks')
    for p in result['evidence']: verify(root,p)
    seed=read(root/r['seed']['path'])
    require(seed['arm_checkpoints']==r['arm_checkpoints'] and seed['reserved']==0,'Changed retry checkpoints')
    for arms in r['arm_checkpoints'].values():
        for p in arms.values(): verify(root,p)
    require(program==expected_program(old,r,root,plan_reference),'Changed unrelated graph or authority')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def validate_history(program,state,root):
    from scripts.legal_baseline_corpus_deployment import validate_history as predecessor_history
    root=Path(root);r=program[KEY];before=read(root/r['prior_state']['path'])
    old=read(root/r['prior_program']['path']);baseline=read(root/r['baseline']['path'])
    with historical_evidence(root,mapping(baseline)): predecessor_history(old,before,root)
    require(set(before['tasks'])==set(state['tasks'])
        and state['events'][:len(before['events'])]==before['events'],'Lost predecessor state')
    for tid,prior in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(prior['attempts']),'Lost attempts: '+tid)
        for a,b in zip(prior['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed old attempt: '+tid)
        if prior['status']=='SUCCEEDED' or (tid not in ATTEMPTS and prior['status'] not in ('PENDING','RUNNING')):
            require(current==prior,'Reopened settled unrelated owner: '+tid)
        if prior.get('service_checkpoint'):
            verify(root,prior['service_checkpoint'])
            if current!=prior:
                events=[e for e in state['events'][len(before['events']):]
                    if e.get('task_id')==tid and e.get('action')=='SERVICE_CHECKPOINT_READY']
                require(events,'Paused owner changed without authenticated service response')
                for event in events:
                    for pointer in event['evidence']:
                        verify(root,pointer);proof=read(root/pointer['path'])
                        require(proof.get('substituted_into_product') is False and proof.get('legal_acceptance') is False
                            and proof['provenance']['response_hash']==digest(proof['value']),
                            'Invalid service resumption evidence')
    for key in ('continuation_vetoes','resolved_continuation_vetoes'):
        require(state.get(key,[])[:len(before.get(key,[]))]==before.get(key,[]),'Lost '+key)

def worker():
    from scripts import legal_integration_phased_live as live,legal_integration_campaign as campaign
    from scripts.legal_review_repair_service import recover
    with (ROOT/WORK/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        runtime=WORK/'probe-capacity-fix' if read(ROOT/PROGRAM)[KEY].get('probe_capacity_repair') else WORK
        save(ROOT/runtime/'worker.json',dict(process=process_identity(os.getpid()),at_utc=now()))
        try:
            # Registration already validated the complete master. Probe the exact
            # ended transport first, under current provider authority and locks.
            save(ROOT/runtime/'service-recovery-result.json',recover())
            # Existing scheduler preserves all independent owners; no failed arm is a global stop.
            from scripts.legal_review_repair import live as drain
            save(ROOT/runtime/'live-result.json',drain())
        except BaseException as exc:
            import traceback
            save(ROOT/runtime/'worker-error.json',dict(error=type(exc).__name__,reason=str(getattr(exc,'details',None) or exc),
                traceback=traceback.format_exc(),at_utc=now()))
            raise
        finally:
            with (ROOT/runtime/'refresh.stdout').open('w') as out,(ROOT/runtime/'refresh.stderr').open('w') as err:
                code=subprocess.call([str(ROOT/'.venv/bin/python'),'scripts/legal_mission_control.py','refresh'],
                    cwd=ROOT,stdout=out,stderr=err)
            save(ROOT/runtime/'finished.json',dict(at_utc=now(),refresh_exit=code,integration_complete=False))

def arm():
    from scripts.legal_integration_campaign import provider
    require(read(ROOT/WORK/'registration.json')['status']=='COMMITTED','Retry registration incomplete')
    require(read(ROOT/WORK/'installed-verification.json')['verdict']=='PASS','Installed preflight incomplete')
    with (ROOT/WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/WORK/'armed.json'
        if path.exists():
            saved=read(path)
            if process_alive(saved['process']):return saved
            revision=read(ROOT/PROGRAM)[KEY]
            require(revision.get('probe_capacity_repair'),'Ended retry worker requires reviewed recovery')
            require(read(ROOT/WORK/'probe-capacity-fix'/'registration.json')['status']=='COMMITTED'
                and read(ROOT/WORK/'probe-capacity-fix'/'installed-verification.json')['verdict']=='PASS',
                'Probe capacity correction is not verified and installed')
            path=ROOT/WORK/'probe-capacity-fix'/'armed.json'
            if path.exists():
                saved=read(path);require(process_alive(saved['process']),'Bounded probe repair already ended')
                return saved
        provider().check()
        with path.with_name('worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(ROOT/SELF),'worker'],cwd=ROOT,
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        result=dict(process=process_identity(process.pid),at_utc=now())
        require(result['process'],'Worker ended at startup');save(path,result);return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['arm','worker'])
    print(json.dumps(globals()[parser.parse_args().action](),indent=2))
