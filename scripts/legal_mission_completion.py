#!/usr/bin/env python3
"""Fixed local completion checks; no live provider or arbitrary shell action."""
import argparse
import fcntl
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-12/completion'
RULES = ROOT / 'docs/implementation/legal-mission-control/completion.rules'
ACTIONS = ('check', 'status', 'verify', 'native', 'install-rules')
TESTS = (
    'tests/assurance/test_completion_contract.py',
    'tests/assurance/test_route_admission.py',
    'tests/assurance/test_dossier_answer.py',
    'tests/assurance/test_integration_repair_product.py',
    'tests/assurance/test_investigation_answer.py',
    'tests/tooling/test_legal_answer_evidence.py',
    'tests/tooling/test_legal_independent_tools.py',
    'tests/tooling/test_legal_mission_control.py',
    'tests/tooling/test_legal_mission_completion.py',
)


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temp = path.with_suffix(path.suffix + '.writing')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    temp.replace(path)


def check(active=False):
    record = load(BASE / 'authorization.json')
    assert record['live_calls'] == 0 and record['additional_attempts'] == 1
    assert record['reconciled_prior_attempts'] == 1 and record['prior_registered_detours'] == 14
    for ref in record['protected_evidence']:
        assert hashlib.sha256((ROOT / ref['path']).read_bytes()).hexdigest() == ref['sha256'], ref['path']
    if active:
        now = datetime.now(timezone.utc)
        assert datetime.fromisoformat(record['started_utc']) <= now < datetime.fromisoformat(record['deadline_utc']), 'Local window expired or not started'
        state = load(BASE / 'state.json')
        mission = load(ROOT / 'docs/implementation/legal-mission-control/mission.json')
        assert state['assessment']['status'] not in ('PASS', 'FAILED', 'BLOCKED'), 'Local completion package settled'
        assert not any(row['id'] == 'integration-completion-assessment-2026-10-12'
                       for row in mission['history']), 'Local completion package settled in mission history'
    return record


def install_rules():
    # Installation cannot alter existing settings, hooks, historical rules or grants.
    target = Path('/home/chakwong/.codex/rules/legalmath-completion.rules')
    text = RULES.read_text()
    for action in ACTIONS[:-1]:
        result = subprocess.run(['codex', 'execpolicy', 'check', '--rules', str(RULES),
            '.venv/bin/python', 'scripts/legal_mission_completion.py', action],
            cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
        assert json.loads(result.stdout).get('decision') == 'allow', result.stdout
    probe = subprocess.run(['codex', 'execpolicy', 'check', '--rules', str(RULES),
        '.venv/bin/python', '-c', 'print(1)'], cwd=ROOT, capture_output=True,
        text=True, timeout=20, check=True)
    assert json.loads(probe.stdout).get('decision') != 'allow'
    if target.exists():
        assert target.read_text() == text, 'Refusing to overwrite a different rule file'
    else:
        target.write_text(text)
    assert target.read_text() == text
    return {'rules': str(target), 'exact_commands_checked': 4, 'unrelated_command_allowed': False}


def run(action):
    with (BASE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(action)


def run_locked(action):
    authority = check(active=True)
    history = BASE / ('runs-' + action + '.json')
    rows = load(history) if history.exists() else []
    assert not any(r['status'] == 'RUNNING' for r in rows), 'Reconcile prior process before another run'
    index = len(rows) + 1
    command = ([str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', *TESTS,
                '--junitxml=' + str(BASE / f'verify-{index}.xml')]
               if action == 'verify' else
               [str(ROOT / '.venv/bin/python'), 'scripts/legal_mission_completion_native.py'])
    output = BASE / f'{action}-{index}.log'
    row = {'command': command, 'status': 'RUNNING', 'pid': os.getpid(),
           'started_utc': datetime.now(timezone.utc).isoformat(), 'output': str(output.relative_to(ROOT)),
           'cpu_only': True, 'provider_calls': 0}
    rows.append(row); save(history, rows)
    start = time.monotonic()
    try:
        with output.open('w') as stream:
            result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
                'LEGAL_COMPLETION_PRODUCT_EVIDENCE': str(BASE / f'verify-{index}-product'),
                'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT)},
                stdout=stream, stderr=subprocess.STDOUT, timeout=min(600,
                    (datetime.fromisoformat(authority['deadline_utc']) - datetime.now(timezone.utc)).total_seconds()))
        row.update(status='PASS' if result.returncode == 0 else 'FAILED', exit_code=result.returncode)
    except Exception as exc:
        row.update(status='FAILED', error=type(exc).__name__)
        raise
    finally:
        row['seconds'] = time.monotonic() - start
        save(history, rows)
    print(output.read_text()[-14000:])
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    action = parser.parse_args().action
    if action == 'install-rules':
        value = install_rules()
    elif action in ('verify', 'native'):
        value = run(action)
    else:
        record = check()
        value = {'check': 'PASS', 'live_calls': 0, 'authority': record,
                 'branches': load(BASE / 'state.json')}
    print(json.dumps(value, indent=2))
    return 1 if value.get('status') == 'FAILED' else 0


if __name__ == '__main__':
    sys.exit(main())
