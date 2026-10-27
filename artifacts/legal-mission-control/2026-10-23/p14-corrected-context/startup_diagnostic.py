"""Read-only startup diagnosis; no provider, scheduler mutation or acceptance."""
import argparse
import cProfile
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import pstats
import signal
import sys
import time
import traceback

ROOT = Path('/home/chakwong/python/legalmath')
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
HERE = ROOT / 'artifacts/legal-mission-control/2026-10-23/p14-corrected-context'
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'

def read(path):
    return json.loads(path.read_text())

def status():
    state = read(BASE / 'execution-state.json')
    ledger = read(BASE / 'live-calls.json')
    binding = read(BASE / 'current-binding.json')
    service = (ROOT / binding['phase_service_scope']['path']).parent
    recovery = read(service / 'service-recovery.json')
    directory = HERE/'requested-owner' if (HERE/'requested-owner/worker.json').exists() else HERE
    worker = read(directory / 'worker.json')
    pid = worker['process']['pid']
    process = {}
    try:
        proc = Path(f'/proc/{pid}')
        fields = (proc / 'stat').read_text().rsplit(') ', 1)[1].split()
        process = dict(state=fields[0], start=fields[19],
                       recorded_identity_matches=fields[19] == worker['process']['start'],
                       io=(proc / 'io').read_text(),
                       children=(proc / f'task/{pid}/children').read_text(),
                       fds=[str(p.readlink()) for p in (proc / 'fd').iterdir()])
    except OSError as exc:
        process['inspection_error'] = str(exc)
    circuit=read(service/'service-circuit.json')
    runtime=ROOT/'artifacts/legal-mission-control/2026-10-23/p14-deployment/context-isolated-live'
    from collections import Counter
    dispatches=[]
    for path in runtime.rglob('calls/dispatch.json'):
        rows=read(path)['calls']
        dispatches.append(dict(path=str(path.relative_to(runtime)),counts=dict(Counter(
            r['status'] for r in rows.values())),latest=[dict(key=k,status=r['status'],at=r.get('at'))
            for k,r in sorted(rows.items(),key=lambda pair:pair[1].get('at',''))[-3:]]))
    result = dict(at_utc=datetime.now(timezone.utc).isoformat(), worker=worker, process=process,
                  calls=len(ledger['calls']), ceiling=ledger['maximum'],
                  recovery_charges=len(recovery['charges']), recovery_ceiling=recovery['maximum'],
                  circuit={k:circuit.get(k) for k in ('open','consecutive_failures','half_open_reserved',
                      'half_open_request_hash','resumed_at_utc')},dispatches=dispatches,
                  tasks={k: {x:v.get(x) for x in ('status','live_supervisor','reason')} |
                         {'attempts':len(v['attempts'])} for k,v in state['tasks'].items()
                         if v['status']=='RUNNING'},
                  recent_events=[{k:e.get(k) for k in ('action','task_id','at_utc')}
                                 for e in state['events'][-5:]],
                  receipts={p.name:read(p) for p in directory.iterdir()
                            if p.name in {'worker-error.json','finished.json','live-result.json'}})
    print(json.dumps(result, indent=2))

def history_profile(action='history'):
    # Debug only: validate an immutable read snapshot; no lock or scheduler entry.
    from scripts.legal_review_repair import validate_state_history
    from scripts.legal_mission_execution import validate_program
    program = read(ROOT / 'docs/implementation/legal-mission-control/integration-master.json')
    state = read(BASE / 'execution-state.json')
    profile = cProfile.Profile()
    outcome = {'purpose':'debug-only, no engineering or legal promotion', 'provider_calls':0}
    def expired(signum, frame):
        outcome['timeout_stack'] = traceback.format_stack(frame)
        raise TimeoutError('60-second read-only diagnosis bound')
    signal.signal(signal.SIGALRM, expired)
    started=time.monotonic()
    signal.alarm(60)
    try:
        profile.enable()
        if action=='history':
            validate_state_history(program, state, ROOT)
        else:
            validate_program(program, ROOT)
        outcome['status']='VALIDATED_SNAPSHOT'
    except BaseException as exc:
        outcome.update(status=type(exc).__name__,reason=str(exc))
    finally:
        profile.disable()
        signal.alarm(0)
    outcome['wall_seconds']=time.monotonic()-started
    stream=io.StringIO()
    pstats.Stats(profile,stream=stream).sort_stats('cumulative').print_stats(30)
    outcome['profile']=stream.getvalue()
    target=HERE/('startup-'+action+'-diagnostic.json')
    with target.open('x') as out:
        json.dump(outcome,out,indent=2)
    print(json.dumps(outcome,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['status','history','program'])
    args=parser.parse_args()
    if args.action=='status': status()
    else: history_profile(args.action)
