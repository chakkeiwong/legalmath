"""Fixed, lock-serialized handover of the authenticated old live child.

No model calls, master state changes, or synthetic completion records. The
existing wrapper retains the actual signal exit and runs its remaining commands.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import argparse
import fcntl
import json
import os
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'
OLD = ROOT / 'artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry'
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
MISSION = ROOT / 'docs/implementation/legal-mission-control/mission.json'
CHILD = {'pid': 229996, 'start': '2968697'}
WRAPPER = {'pid': 229995, 'start': '2968683'}
COMMAND = ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'live']


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temp = path.with_name(path.name + '.writing')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def identity(pid):
    try:
        fields = Path('/proc', str(pid), 'stat').read_text().rsplit(') ', 1)[1].split()
        return None if fields[0] == 'Z' else {'pid': pid, 'start': fields[19]}
    except (OSError, IndexError):
        return None


def guards(state, journals, native):
    running = [k for k, v in state['tasks'].items() if v['status'] == 'RUNNING']
    reserved = [key for journal in journals for key, row in journal['calls'].items()
                if row['status'] == 'RESERVED']
    native_reserved = [row for row in native if row['status'] == 'RESERVED']
    return not (running or reserved or native_reserved), {
        'running': running, 'reserved_calls': reserved,
        'reserved_native_count': len(native_reserved)}


def run():
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    from legal_common_capacity_deploy import checked_manifest, ref
    manifest = checked_manifest()
    if manifest['predecessor_worker'] != WRAPPER:
        raise ValueError('Predecessor wrapper identity changed')
    result_path = WORK / 'handover-result.json'
    if result_path.exists():
        return read(result_path)
    began = time.monotonic()
    with (WORK / 'handover.lock').open('a') as single:
        fcntl.flock(single, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while time.monotonic() - began < 1800:
            active = read(OLD / 'execution/active-command.json')
            if active['command'] != COMMAND:
                result = {'status': 'ALREADY_SETTLING', 'active': active}
                save(result_path, result)
                return result
            if active['process'] != CHILD or identity(CHILD['pid']) != CHILD:
                raise ValueError('Original live child is absent or changed; no signal sent')
            if identity(WRAPPER['pid']) != WRAPPER:
                raise ValueError('Original wrapper is absent or changed; no signal sent')
            try:
                with ExitStack() as stack:
                    for path in (MISSION.with_name('mission.execution.lock'),
                                 BASE / 'execution-state.lock'):
                        handle = stack.enter_context(path.open('a'))
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    state = read(BASE / 'execution-state.json')
                    allowed, observation = guards(state,
                        [read(p) for p in (OLD / 'live').rglob('dispatch.json')],
                        [read(p) for p in (OLD / 'live').rglob('product-binding.json')])
                    save(WORK / 'handover-state.json', {
                        'at_utc': datetime.now(timezone.utc).isoformat(), **observation})
                    if allowed:
                        # Freeze this exact process while inspecting descendants;
                        # otherwise it could spawn refresh after the read. A pidfd
                        # binds signals to the process rather than a recycled PID.
                        descriptor = os.pidfd_open(CHILD['pid'])
                        stack.callback(os.close, descriptor)
                        if identity(CHILD['pid']) != CHILD:
                            raise ValueError('Child identity changed before quiescence')
                        signal.pidfd_send_signal(descriptor, signal.SIGSTOP)
                        def resume_if_alive():
                            try:
                                signal.pidfd_send_signal(descriptor, signal.SIGCONT)
                            except ProcessLookupError:
                                pass
                        stack.callback(resume_if_alive)
                        proc = Path('/proc', str(CHILD['pid']))
                        for _ in range(50):
                            stopped = proc.joinpath('stat').read_text().rsplit(') ', 1)[1].split()[0]
                            if stopped in ('T', 't'):
                                break
                            time.sleep(0.01)
                        else:
                            raise ValueError('Child did not enter stopped state; handover refused')
                        actual = proc.joinpath('cmdline').read_bytes().decode().rstrip('\0').split('\0')
                        fields = proc.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
                        children = proc.joinpath('task', str(CHILD['pid']), 'children').read_text().strip()
                        observation['process'] = {'command': actual, 'parent': int(fields[1]),
                            'children': children, 'identity': identity(CHILD['pid'])}
                        save(WORK / 'handover-state.json', {
                            'at_utc': datetime.now(timezone.utc).isoformat(), **observation})
                        if (actual != COMMAND or int(fields[1]) != WRAPPER['pid']
                                or identity(CHILD['pid']) != CHILD):
                            raise ValueError('Child command, parent or identity changed')
                        if children:
                            raise BlockingIOError('Wait for existing child subprocess settlement')
                        if ref(ROOT / manifest['predecessor_program']['path']) != manifest['predecessor_program']:
                            raise ValueError('Master revision changed')
                        result = {'status': 'QUIESCENT_SIGNAL_AUTHORIZED',
                            'at_utc': datetime.now(timezone.utc).isoformat(),
                            'child': CHILD, 'wrapper': WRAPPER, 'signal': 'SIGTERM',
                            'command': actual, 'observations': observation,
                            'state_before': ref(BASE / 'execution-state.json'),
                            'provider_calls': len(read(BASE / 'live-calls.json')['calls']),
                            'reason': 'Reviewed common capacity handover between tasks',
                            'state_mutations': 0, 'provider_calls_added': 0,
                            'wrapper_completion_fabricated': False}
                        save(WORK / 'handover-authorization.json', result)
                        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                        signal.pidfd_send_signal(descriptor, signal.SIGCONT)
                        for _ in range(50):
                            if identity(CHILD['pid']) != CHILD:
                                result['status'] = 'CHILD_SETTLED_WRAPPER_CONTINUES'
                                result['ended_at_utc'] = datetime.now(timezone.utc).isoformat()
                                save(result_path, result)
                                return result
                            time.sleep(0.1)
                        raise ValueError('Child did not settle; no stronger signal or retry permitted')
            except BlockingIOError:
                pass
            time.sleep(2)
    result = {'status': 'BLOCKED', 'reason': 'No safe handover point in 1800 seconds',
              'provider_calls_added': 0, 'state_mutations': 0}
    save(result_path, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run'])
    parser.parse_args()
    if not hasattr(os, 'pidfd_open'):
        # Fixed same-script compatibility path; no user-supplied command or args.
        os.execv('/usr/bin/python3', ['/usr/bin/python3',
            str(ROOT / 'scripts/legal_common_capacity_handover.py'), 'run'])
    print(json.dumps(run(), indent=2))
