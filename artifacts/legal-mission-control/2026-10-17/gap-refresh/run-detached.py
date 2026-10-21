"""Run the registered master once; retain identity through editor reloads."""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import read, save, ref, require, process_identity
from scripts.legal_integration_gap_refresh import WORK, KEY, BASE, PROGRAM, PLAN, REVIEW


def main():
    directory = ROOT / WORK
    with ExitStack() as stack:
        handle = stack.enter_context((directory / 'detached-worker.lock').open('a'))
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        program = read(ROOT / PROGRAM)
        require(program.get(KEY, {}).get('work') == str(WORK),
                'Current frontier amendment is not registered')
        require(not (directory / 'worker-start.json').exists(),
                'Inspect retained worker identity and result; do not launch a duplicate')
        command = ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'live']
        start = dict(profile='legal-frontier-worker.v1', command=command,
            process=process_identity(os.getpid()),
            started_at_utc=datetime.now(timezone.utc).isoformat(),
            commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            binding=ref(ROOT, BASE / 'current-binding.json'), program=ref(ROOT, PROGRAM),
            plan=ref(ROOT, PLAN), review=ref(ROOT, REVIEW),
            grant=ref(ROOT, BASE / 'live-grant.json'),
            ledger_before=program[KEY]['prior_ledger'],
            launcher=ref(ROOT, Path(__file__).resolve()),
            environment='.venv-context; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
            data_version=program['prerequisite_repair']['source'],
            seeds='N/A: production continuation; no stochastic method ranking',
            output_log=str(WORK / 'worker.log'), result=str(WORK / 'worker-result.json'))
        save(directory / 'worker-start.json', start)
        with (directory / 'worker.log').open('w') as output:
            child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            save(directory / 'worker-live-process.json',
                 dict(process=process_identity(child.pid), command=command))
            returncode = child.wait()
        outcomes = []
        for name, command in (
                ('refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
                ('verify', ['.venv/bin/python', 'scripts/legal_integration_master.py', 'verify'])):
            with (directory / (name + '.stdout')).open('w') as output, \
                    (directory / (name + '.stderr')).open('w') as errors:
                try:
                    result = subprocess.run(command, cwd=ROOT, stdout=output,
                                            stderr=errors, timeout=900)
                    outcomes.append(dict(action=name, command=command, exit_code=result.returncode))
                except subprocess.TimeoutExpired:
                    outcomes.append(dict(action=name, command=command, timeout_seconds=900))
        save(directory / 'worker-result.json', dict(live_exit_code=returncode, checks=outcomes,
            finished_at_utc=datetime.now(timezone.utc).isoformat(),
            start=ref(ROOT, WORK / 'worker-start.json'),
            calls=len(read(ROOT / BASE / 'live-calls.json')['calls']), integration_complete=False,
            log=ref(ROOT, WORK / 'worker.log')))


if __name__ == '__main__':
    main()
