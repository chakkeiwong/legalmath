"""Retain exact full validation and acknowledge only its wrapper timeout."""
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
DOC = ROOT / 'docs/implementation/legal-mission-control'
read = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
save = lambda path, value: path.write_text(json.dumps(value, indent=2) + '\n')
paths = [DOC / 'mission.json', DOC / 'integration-master.json',
    BASE / 'current-binding.json', BASE / 'execution-state.json', BASE / 'live-calls.json']
action, label = sys.argv[1:]
assert action in ('finish', 'snapshot', 'refresh', 'verify', 'settle')
assert label in ('pre-adoption', 'registration', 'binding', 'terminal')
prefix = WORK / label

def locks(stack):
    program = read(DOC / 'integration-master.json')
    names = {ROOT / value / 'supervisor.lock' for value in program['repair_execution']['live_directories'].values()}
    names |= {BASE / 'execution-state.run.lock', DOC / 'mission.execution.lock', BASE / 'execution-state.lock'}
    for name in sorted(names):
        name.parent.mkdir(parents=True, exist_ok=True)
        handle = stack.enter_context(name.open('a'))
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

if action == 'snapshot':
    with ExitStack() as stack:
        locks(stack)
        state = read(BASE / 'execution-state.json')
        assert not any(r['status'] == 'RUNNING' for r in state['tasks'].values())
        target = prefix.with_name(label + '-inputs.json')
        assert not target.exists(), 'Do not overwrite recorded refresh inputs'
        save(target, {str(path.relative_to(ROOT)): sha(path) for path in paths})
    print('Settled input hashes retained.', flush=True)
elif action in ('finish', 'refresh', 'verify'):
    command = (['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']
        if action == 'refresh' else ['.venv-context/bin/python', 'scripts/legal_integration_master.py',
            'run' if action == 'finish' else 'verify'])
    target = prefix.with_name(label + '-' + action + '.json')
    error = target.with_suffix('.stderr')
    assert not target.exists(), 'Do not overwrite command evidence'
    began = time.monotonic()
    with target.open('w') as output, error.open('w') as stderr:
        result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=stderr)
    manifest = {'command': command, 'returncode': result.returncode,
        'wall_seconds': time.monotonic() - began, 'at_utc': datetime.now(timezone.utc).isoformat(),
        'stdout': {'path': str(target.relative_to(ROOT)), 'sha256': sha(target)},
        'stderr': {'path': str(error.relative_to(ROOT)), 'sha256': sha(error)}}
    save(target.with_suffix('.manifest.json'), manifest)
    print(json.dumps(manifest), flush=True)
    raise SystemExit(result.returncode)
else:
    expected = read(prefix.with_name(label + '-inputs.json'))
    reference = prefix.with_name(label + '-refresh.json')
    checkpath = prefix.with_name(label + '-verify.json')
    result, check = read(reference), read(checkpath)
    for filename in (reference, checkpath):
        manifest = read(filename.with_suffix('.manifest.json'))
        assert manifest['returncode'] == 0 and manifest['stdout']['sha256'] == sha(filename)
    assert result['admission']['admission'] == 'ADMITTED_MASTER_WORK'
    assert result['status']['integration_master']['running'] == []
    assert check['prior_calls_preserved'] and check['prior_attempts_preserved']
    with ExitStack() as stack:
        locks(stack)
        for name, checksum in expected.items():
            assert sha(ROOT / name) == checksum, 'Changed validated input: ' + name
        state = read(BASE / 'execution-state.json')
        program = read(DOC / 'integration-master.json')
        revision = program['repair_execution']
        assert check['calls'] == len(read(BASE / 'live-calls.json')['calls'])
        assert check['repairs_allocated'] == len(revision['repair_ids'])
        assert check['additional_attempts_allocated'] == revision['cumulative_additional_attempts']
        assert not any(r['status'] == 'RUNNING' for r in state['tasks'].values())
        assert state['tasks']['current-binding']['status'] == 'SUCCEEDED'
        if label != 'binding':
            assert state['tasks']['continuation-review']['status'] == 'SUCCEEDED'
        failure = state.get('mission_sync_error')
        assert failure == "Command '['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']' timed out after 300 seconds"
        state.pop('mission_sync_error')
        event = {'action': 'MISSION_SYNC_RECOVERED', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(),
            'basis': 'Exact direct refresh and verification passed on unchanged settled inputs after wrapper timeout.',
            'review': {'path': str((WORK / 'refresh-review.md').relative_to(ROOT)),
                'sha256': sha(WORK / 'refresh-review.md')},
            'evidence': {'path': str(reference.relative_to(ROOT)), 'sha256': sha(reference)},
            'verification': {'path': str(checkpath.relative_to(ROOT)), 'sha256': sha(checkpath)},
            'previous_error': failure, 'provider_calls': 0, 'task_attempts_added': 0}
        state['events'].append(event)
        temporary = BASE / 'execution-state.refresh-complete.json'
        save(temporary, state)
        temporary.replace(BASE / 'execution-state.json')
        save(prefix.with_name(label + '-recovered.json'), event)
    print('Successful exact refresh acknowledged; original attempts and results retained.', flush=True)
