"""Interrupt only a proved idle, fully checkpointed supervisor for local deployment."""
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime,timezone
import fcntl,hashlib,json,os,signal,sys,time
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-27/git-handoff'
LIVE=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/live'
BASE=ROOT/'artifacts/legal-mission-control/2026-10-13/master'
def read(p):return json.loads(p.read_text())
def pointer(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def identity(pid):
    path=Path('/proc')/str(pid)/'stat'
    if not path.exists():return None
    text=path.read_text();parts=text[text.rindex(')')+2:].split()
    return dict(pid=pid,start=parts[19])
def snapshot():
    worker=read(ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure/followthrough/runtime-deployment/armed.json')['process']
    assert identity(worker['pid'])==worker,'Supervisor identity changed'
    binding=read(BASE/'current-binding.json')
    service=ROOT/Path(binding['phase_service_scope']['path']).parent
    journals=sorted(LIVE.rglob('dispatch.json'))
    locks=[service/'service-worker.lock',service/'service-circuit.lock',
        BASE/'live-calls.lock',BASE/'execution-state.lock',
        ROOT/'docs/implementation/legal-mission-control/mission.execution.lock',
        *[p.with_name('dispatch.lock') for p in journals]]
    with ExitStack() as stack:
        for path in locks:
            stream=stack.enter_context(path.open('a'));fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert identity(worker['pid'])==worker
        children=Path('/proc')/str(worker['pid'])/'task'/str(worker['pid'])/'children'
        assert not children.read_text().strip(),'Supervisor still owns a subprocess'
        os.kill(worker['pid'],signal.SIGSTOP)
        try:
            for _ in range(100):
                stat=(Path('/proc')/str(worker['pid'])/'stat').read_text()
                if stat[stat.rindex(')')+2:].split()[0]=='T':break
                time.sleep(.01)
            else:raise RuntimeError('Supervisor did not quiesce')
            assert not children.read_text().strip(),'Supervisor started a subprocess'
            assert sorted(LIVE.rglob('dispatch.json'))==journals,'Journal population changed'
            reserved=[(str(p),k) for p in journals for k,v in read(p)['calls'].items() if v['status']=='RESERVED']
            assert not reserved, 'Provider dispatch is reserved'
            phases=sorted(LIVE.rglob('phase.json'))
            assert all(read(p)['status'] in ('COMPLETE','INCOMPLETE','RESOURCE_BLOCKED') for p in phases), 'A phase still needs its old admission'
            circuit=read(service/'service-circuit.json')
            assert not circuit['open'] and not circuit.get('half_open_reserved'),'Service recovery unsettled'
            record=dict(at_utc=datetime.now(timezone.utc).isoformat(),supervisor=worker,
                calls=len(read(BASE/'live-calls.json')['calls']),reserved_dispatches=0,
                phases=[pointer(p) for p in phases],journals=[pointer(p) for p in journals],
                binding=pointer(BASE/'current-binding.json'),state=pointer(BASE/'execution-state.json'),
                reason='User-authorized coherent Git checkpoint and main integration; preserve all calls, attempts, reservations and historical source bindings')
            target=WORK/'handover-request.json'
            with target.open('x') as f:json.dump(record,f,indent=2)
            os.kill(worker['pid'],signal.SIGINT)
        finally:
            os.kill(worker['pid'],signal.SIGCONT)
    print(json.dumps(dict(interrupt_sent=True,calls=record['calls'],pid=worker['pid'])))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--watch-seconds',type=int,default=0)
    seconds=parser.parse_args().watch_seconds
    assert 0<=seconds<=3600,'Bounded checkpoint watch only'
    until=time.monotonic()+seconds
    attempts=0
    while True:
        try:
            snapshot()
            break
        except (BlockingIOError,AssertionError) as exc:
            attempts+=1
            if (WORK/'handover-request.json').exists():raise
            if time.monotonic()>=until:raise
            if attempts==1 or attempts%120==0:
                print(json.dumps(dict(waiting_for_safe_boundary=True,attempts=attempts,
                    reason=str(exc) or type(exc).__name__)),flush=True)
            time.sleep(.5)
