"""Continue the existing master after the reviewed P10 stop-scope correction."""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import (
    read, save, ref, require, verify, process_identity, process_alive,
)
from scripts.legal_integration_master import BASE, PROGRAM, STATE

WORK = Path(__file__).resolve().parent
OUTPUT = WORK / 'evidence-continuation'
LIVE_COMMAND = ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'live']


def checked_command(name, command, outcomes):
    started = time.monotonic()
    with (OUTPUT / (name + '.stdout')).open('x') as output, \
            (OUTPUT / (name + '.stderr')).open('x') as errors:
        try:
            completed = subprocess.run(command, cwd=ROOT, stdout=output,
                stderr=errors, timeout=900)
            row = dict(action=name, command=command, exit_code=completed.returncode)
        except subprocess.TimeoutExpired:
            row = dict(action=name, command=command, timeout_seconds=900)
    row.update(wall_seconds=time.monotonic()-started,
        at_utc=datetime.now(timezone.utc).isoformat())
    outcomes.append(row)
    save(OUTPUT / 'checks.json', outcomes)
    save(OUTPUT / 'progress.json', dict(action=name, result=row,
        process=process_identity(os.getpid()), at_utc=row['at_utc']))


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        for path in (WORK / 'detached-worker.lock', OUTPUT / 'worker.lock'):
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (OUTPUT / 'worker-start.json').exists(),
            'Inspect retained continuation identity/result; do not duplicate it')
        prior = read(WORK / 'worker-result.json')
        require(prior['live_exit_code'] == 0
            and all(r.get('exit_code') == 0 for r in prior['checks']),
            'Original worker did not settle')
        for name in ('worker-start.json', 'worker-live-process.json'):
            require(not process_alive(read(WORK / name)['process']), 'Original worker survives')
        correction = read(WORK / 'veto-scope-applied.json')
        require(correction['verdict'] == 'PASS', 'Scope correction did not pass')
        for name in ('before', 'after', 'review', 'evidence'):
            verify(ROOT, correction[name])
        require(read(WORK / 'scope-history-recorded.json')['verdict'] == 'PASS',
            'Scope correction has no mission history')
        state = read(ROOT / STATE)
        require(not any(t['status'] == 'RUNNING' for t in state['tasks'].values()),
            'Another master owner is running')
        require(state['tasks']['acquire-evidence']['status'] == 'PENDING'
            and len(state['tasks']['acquire-evidence']['attempts']) == 5,
            'Evidence attempt frontier changed')
        grant = read(ROOT / BASE / 'live-grant.json')
        require(datetime.now(timezone.utc) < datetime.fromisoformat(grant['deadline_utc']),
            'Original live deadline expired')
        started = dict(profile='legal-independent-continuation.v1', command=LIVE_COMMAND,
            process=process_identity(os.getpid()),
            at_utc=datetime.now(timezone.utc).isoformat(),
            git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            program=ref(ROOT, PROGRAM), binding=ref(ROOT, BASE / 'current-binding.json'),
            grant=ref(ROOT, BASE / 'live-grant.json'), ledger_before=ref(ROOT, BASE / 'live-calls.json'),
            correction=ref(ROOT, WORK / 'veto-scope-applied.json'),
            review=ref(ROOT, WORK / 'independent-continuation-review.md'),
            source=ref(ROOT, Path(__file__)),
            environment=str(ROOT / '.venv-context/bin/python'),
            devices='CPU only; CUDA_VISIBLE_DEVICES=-1; GPUs intentionally hidden',
            seeds='N/A: production execution; no stochastic ranking',
            output_directory=str(OUTPUT.relative_to(ROOT)), new_phase=False,
            calls_added=0, attempts_added=0, repair_allowance_added=0)
        save(OUTPUT / 'worker-start.json', started)
        checks = []
        for name, command in (
                ('pre-refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
                ('pre-verify', ['.venv/bin/python', 'scripts/legal_integration_master.py', 'verify']),
                ('pre-check', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'check']),
                ('pre-status', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'status']),
                ('pre-admit', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'admit'])):
            checked_command(name, command, checks)
        ready = all(r.get('exit_code') == 0 for r in checks)
        live_code = None
        if ready:
            save(OUTPUT / 'progress.json', dict(action='live',
                process=process_identity(os.getpid()),
                at_utc=datetime.now(timezone.utc).isoformat()))
            with (OUTPUT / 'worker.log').open('x') as output:
                child = subprocess.Popen(LIVE_COMMAND, cwd=ROOT, stdout=output,
                    stderr=subprocess.STDOUT)
                save(OUTPUT / 'worker-live-process.json',
                    dict(process=process_identity(child.pid), command=LIVE_COMMAND))
                live_code = child.wait()
            for name, command in (
                    ('post-refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
                    ('post-verify', ['.venv/bin/python', 'scripts/legal_integration_master.py', 'verify'])):
                checked_command(name, command, checks)
        calls = len(read(ROOT / BASE / 'live-calls.json')['calls'])
        save(OUTPUT / 'worker-result.json', dict(preflight_passed=ready,
            live_exit_code=live_code, checks=checks, calls=calls,
            finished_at_utc=datetime.now(timezone.utc).isoformat(),
            start=ref(ROOT, OUTPUT / 'worker-start.json'), integration_complete=False,
            legal_acceptance=False,
            meaning='Runner settlement only; assess original substantive results separately.'))


if __name__ == '__main__':
    main()
