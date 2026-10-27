"""Execute the admitted P14 item before draining independent retained owners."""
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/home/chakwong/python/legalmath')
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive
from scripts import legal_review_context_isolation as isolation
HERE = isolation.HERE / 'requested-owner'
NOTE = Path('docs/implementation/legal-mission-control/results/p14-deployment-continuation-2026-10-23.md')
SELF = isolation.HERE / 'requested_owner.py'
SELECTED = ('baseline-p14', 'baseline-gatecoin', 'tool-gatecoin-bm25')

def now():
    return datetime.now(timezone.utc).isoformat()

def authenticate():
    manifest = read(ROOT/HERE/'operation.json')
    require(manifest['selected'] == list(SELECTED) and manifest['calls_added'] == 0
            and manifest['attempts_added'] == 0, 'Unreviewed selected work')
    for pointer in manifest['evidence']:
        verify(ROOT,pointer)
    require(manifest['program'] == ref(ROOT,PROGRAM)
            and manifest['binding'] == ref(ROOT,BASE/'current-binding.json'),
            'Bound deployment changed before handover')
    return manifest

def children(owner):
    return Path(f'/proc/{owner["pid"]}/task/{owner["pid"]}/children').read_text().strip()

def state_of(owner):
    return Path(f'/proc/{owner["pid"]}/stat').read_text().rsplit(') ',1)[1].split()[0]

def settle_once():
    manifest=authenticate()
    receipt=ROOT/HERE/'handover.json'
    if receipt.exists():
        value=read(receipt)
        require(value.get('supervisor_ended') and not process_alive(value['process']),
                'Incomplete existing handover')
        return value
    owner=read(ROOT/isolation.HERE/'worker.json')['process']
    require(owner == manifest['old_owner']
            and read(ROOT/isolation.HERE/'armed.json')['process'] == owner
            and process_identity(owner['pid']) == owner, 'Supervisor identity changed')
    binding=read(ROOT/BASE/'current-binding.json')
    service=ROOT/Path(binding['phase_service_scope']['path']).parent
    runtime=ROOT/isolation.RUNTIME
    with ExitStack() as stack:
        journals=sorted(runtime.rglob('calls/dispatch.json'))
        locks=[ROOT/STATE.with_suffix('.lock'),ROOT/DOC/'mission.execution.lock',
               service/'service-worker.lock',service/'service-circuit.lock',
               (ROOT/BASE/'live-calls.json').with_suffix('.lock')]
        locks += [p.with_name('dispatch.lock') for p in journals]
        try:
            for path in locks:
                path.parent.mkdir(parents=True,exist_ok=True)
                handle=stack.enter_context(path.open('a'))
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(settled=False,reason='Shared state or provider is busy; no signal')
        state=read(ROOT/STATE)
        require(state['tasks']['baseline-p14']['status']=='RUNNING'
                and len(state['tasks']['baseline-p14']['attempts'])==5,
                'P14 no longer has the retained attempt')
        active=[r for r in state['tasks'].values() if r['status']=='RUNNING']
        require(all(r.get('master_live') and r.get('live_supervisor') and
                    (r['live_supervisor']==owner or not process_alive(r['live_supervisor']))
                    for r in active), 'Another active or unknown owner')
        if any(r['status']=='RESERVED' for p in journals for r in read(p)['calls'].values()):
            return dict(settled=False,reason='Unsettled dispatch; no signal')
        circuit=read(service/'service-circuit.json')
        if circuit.get('open',True) or any(circuit.get(k) for k in
                ('half_open_reserved','half_open_request_hash','half_open_schema_hash')):
            return dict(settled=False,reason='Service recovery unsettled; no signal')
        if children(owner):
            return dict(settled=False,reason='Provider child present; no signal')
        ledger=ref(ROOT,BASE/'live-calls.json')
        stopped=False
        try:
            os.kill(owner['pid'],signal.SIGSTOP)
            stopped=True
            for _ in range(100):
                if state_of(owner) in ('T','t'): break
                time.sleep(.01)
            require(state_of(owner) in ('T','t') and process_identity(owner['pid'])==owner
                    and not children(owner) and ref(ROOT,BASE/'live-calls.json')==ledger
                    and read(service/'service-circuit.json')==circuit
                    and sorted(runtime.rglob('calls/dispatch.json'))==journals,
                    'Idle boundary changed after stop')
            authenticate()
            retained=[]
            for name in ('armed.json','worker.json','worker.log'):
                source=ROOT/isolation.HERE/name
                target=ROOT/HERE/'before'/name
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as output: output.write(source.read_bytes())
                retained.append(ref(ROOT,target))
            value=dict(settled=True,process=owner,at_utc=now(),ledger=ledger,
                       state_before=ref(ROOT,STATE),preserved_receipts=retained,
                       dispatches=[ref(ROOT,p) for p in journals],reserved_dispatches=0,
                       provider_children=[],service_settled=True,
                       operation=ref(ROOT,HERE/'operation.json'))
            save(receipt,value)
            os.kill(owner['pid'],signal.SIGTERM)
            os.kill(owner['pid'],signal.SIGCONT)
            stopped=False
            for _ in range(100):
                if not process_alive(owner): break
                time.sleep(.05)
            require(not process_alive(owner),'Supervisor has not ended')
            value['supervisor_ended']=True
            save(receipt,value)
            return value
        finally:
            if stopped: os.kill(owner['pid'],signal.SIGCONT)

def settle():
    end=time.monotonic()+50
    while True:
        value=settle_once()
        if value.get('settled') or time.monotonic()>=end: return value
        time.sleep(.25)

def run_selected(execution,tid):
    from scripts import legal_integration_phased_live as live
    from scripts import legal_integration_campaign as campaign
    from scripts.legal_review_repair_service import recover
    while True:
        state=read(ROOT/STATE)
        if state['tasks'][tid].get('service_checkpoint') and not state['tasks'][tid].get('service_resume'):
            recover()
            continue
        view=execution.summary()
        if tid not in view['running'] and tid not in view['ready']:
            return dict(task_id=tid,disposition='NOT_READY_OR_ALREADY_COMPLETED',
                        current=view['tasks'][tid])
        state=read(ROOT/STATE)
        require(not any(tid in v['scope'] for v in state.get('continuation_vetoes',[])),
                'Selected owner retains a continuation veto')
        if tid=='baseline-p14':
            require(state['tasks'][tid]['status']=='RUNNING'
                    and len(state['tasks'][tid]['attempts'])==5,
                    'Selected P14 would start a different attempt')
        binding=read(ROOT/BASE/'current-binding.json')
        circuit=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-circuit.json')
        if circuit['open']:
            recover()
            continue
        service=campaign.provider()
        service.check()
        if tid.startswith('baseline-'): q,tool=tid[9:],None
        else: q,tool=tid[5:].split('-',1)
        with (ROOT/live.LIVE/'supervisor.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            value=campaign.complete_node(execution,tid,lambda:live.answer(q,tool,service))
        if isinstance(value,dict) and value.get('service_deferred'):
            recover()
            continue
        return dict(task_id=tid,disposition='EXECUTED_EXISTING_NODE',value=value,at_utc=now())

def worker():
    from scripts.legal_review_timeout_correction import verify_orphans
    from scripts.legal_review_repair import live as drain
    authenticate()
    with ExitStack() as stack:
        for path in (ROOT/isolation.HERE/'worker.lock',ROOT/HERE/'worker.lock'):
            handle=stack.enter_context(path.open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(ROOT/HERE/'worker.json',dict(process=process_identity(os.getpid()),
             at_utc=now(),operation=ref(ROOT,HERE/'operation.json')))
        try:
            verify_orphans(ROOT,read(ROOT/STATE),ROOT/isolation.RUNTIME)
            execution=MasterExecution(ROOT,PROGRAM,STATE)
            for tid in SELECTED:
                save(ROOT/HERE/(tid+'.started.json'),dict(at_utc=now(),task_id=tid))
                save(ROOT/HERE/(tid+'.result.json'),run_selected(execution,tid))
                # complete_node.finish already persists its result and refreshes
                # mission control. Failed product conclusions do not end this loop.
            save(ROOT/HERE/'live-result.json',drain())
        except BaseException as exc:
            import traceback
            save(ROOT/HERE/'worker-error.json',dict(error=type(exc).__name__,
                 reason=str(getattr(exc,'details',None) or exc),traceback=traceback.format_exc(),at_utc=now()))
            raise
        finally:
            steps=[]
            for action in ('refresh','status'):
                command=([str(ROOT/'.venv/bin/python'),'scripts/legal_mission_control.py',action]
                         if action=='refresh' else
                         [str(ROOT/'.venv-context/bin/python'),'scripts/legal_integration_master.py',action])
                with ((ROOT/HERE/(action+'.stdout')).open('w') as out,
                        (ROOT/HERE/(action+'.stderr')).open('w') as err):
                    code=subprocess.call(command,cwd=ROOT,stdout=out,stderr=err)
                steps.append(dict(command=command,exit_code=code))
            save(ROOT/HERE/'finished.json',dict(steps=steps,at_utc=now(),integration_complete=False))

def arm():
    authenticate()
    with (ROOT/HERE/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/HERE/'armed.json'
        if path.exists():
            prior=read(path)
            require(process_alive(prior['process']),'Prior selected worker ended; inspect before restart')
            return dict(already_running=True,**prior)
        ended=read(ROOT/HERE/'handover.json')
        require(ended.get('supervisor_ended') and not process_alive(ended['process']),
                'Previous worker remains active')
        for pointer in ended['dispatches']: verify(ROOT,pointer)
        require(ref(ROOT,BASE/'live-calls.json')==ended['ledger'],
                'Call ledger changed after handover')
        from scripts.legal_review_timeout_correction import verify_orphans
        verify_orphans(ROOT,read(ROOT/STATE),ROOT/isolation.RUNTIME)
        from scripts.legal_integration_campaign import provider
        provider().check()
        with (ROOT/HERE/'worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(ROOT/SELF),'worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        identity=process_identity(process.pid)
        require(identity is not None,'Selected worker exited during startup')
        value=dict(process=identity,at_utc=now(),operation=ref(ROOT,HERE/'operation.json'))
        save(path,value)
        return value

if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['settle','arm','worker'])
    args=parser.parse_args()
    print(json.dumps(globals()[args.action](),indent=2))
