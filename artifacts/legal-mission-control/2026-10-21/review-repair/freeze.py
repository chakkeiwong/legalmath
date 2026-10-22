"""Freeze an idle predecessor under its state and provider locks."""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import os
import signal
import time

ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parent
BASE = ROOT/'artifacts/legal-mission-control/2026-10-13/master'
DOC = ROOT/'docs/implementation/legal-mission-control'

def read(path):
    return json.loads(path.read_text())

def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def identity(pid):
    path = Path('/proc')/str(pid)/'stat'
    if not path.exists():
        return None
    fields = path.read_text().rsplit(') ', 1)[1].split()
    return dict(pid=pid, start=fields[19], state=fields[0], parent=int(fields[1]))

def main():
    assert not (WORK/'baseline.json').exists(), 'Never replace a frozen baseline'
    binding = read(BASE/'current-binding.json')
    service = (ROOT/binding['phase_service_scope']['path']).parent
    worker_path = ROOT/'artifacts/legal-mission-control/2026-10-21/retained-acquisition-repair/worker.json'
    expected = read(worker_path)['process']
    with ExitStack() as stack:
        for path in (BASE/'execution-state.run.lock', DOC/'mission.execution.lock',
                     BASE/'execution-state.lock', service/'service-worker.lock',
                     service/'service-circuit.lock', service/'service-recovery.lock'):
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(BASE/'execution-state.json')
        assert not any(r['status'] == 'RUNNING' for r in state['tasks'].values())
        current = identity(expected['pid'])
        if current is not None and current['state'] != 'Z':
            assert current['start'] == expected['start'], 'PID reused'
            assert b'legal_retained_acquisition_repair.py\x00worker' in (Path('/proc')/str(expected['pid'])/'cmdline').read_bytes()
            children = [p for p in Path('/proc').iterdir() if p.name.isdigit()
                        and (v := identity(int(p.name))) and v['parent'] == expected['pid'] and v['state'] != 'Z']
            assert not children, 'Worker has a child; wait for a safe boundary'
            circuit = read(service/'service-circuit.json')
            assert circuit['open'] and not circuit.get('half_open_reserved'), 'Provider request may be live'
            os.kill(expected['pid'], signal.SIGTERM)
            for _ in range(50):
                alive = identity(expected['pid'])
                if alive is None or alive['state'] == 'Z':
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('Bookkeeping worker did not terminate')
        interruption = dict(process=expected, at_utc=datetime.now(timezone.utc).isoformat(),
            reason='Reviewed repair handover: no running owner, provider lock held, no worker child; shared circuit open.',
            charges=len(read(BASE/'live-calls.json')['calls']), attempts_reset=False)
        (WORK/'handover.json').write_text(json.dumps(interruption, indent=2)+'\n')
        paths = [DOC/'integration-master.json', DOC/'mission.json', BASE/'execution-state.json',
            BASE/'live-calls.json', BASE/'live-grant.json', BASE/'current-binding.json',
            BASE/'current-stage.json', ROOT/'docs/plans/legal-integration-master-2026-10-13.md',
            service/'scope.json', service/'service-recovery.json', service/'service-circuit.json']
        paths += sorted((ROOT/'src/legalmath').rglob('*.py'))
        paths += sorted((ROOT/'scripts').glob('legal_*.py'))
        rows = []
        for old in paths:
            if not old.exists():
                continue
            copy = WORK/'before'/old.relative_to(ROOT)
            copy.parent.mkdir(parents=True, exist_ok=True)
            with copy.open('xb') as stream:
                stream.write(old.read_bytes())
            rows.append(dict(previous=ref(old), archive=ref(copy)))
        baseline = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), prior_detours=61,
            calls=interruption['charges'], running_owners=0, archived=rows, handover=ref(WORK/'handover.json'))
        with (WORK/'baseline.json').open('x') as stream:
            json.dump(baseline, stream, indent=2)
        print(json.dumps(dict(calls=baseline['calls'], archived=len(rows), running=0)))

if __name__ == '__main__':
    main()
