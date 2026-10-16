#!/usr/bin/env python3
"""Fixed offline successor receipts and focused verification; no provider calls."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import Execution, ref, save, read, require
from scripts import legal_mission_answer_tools as trial

BASE = ROOT / 'artifacts/legal-mission-control/2026-10-12/answer-tools-execution'
OFFLINE = BASE / 'offline-verification.json'
TESTS = BASE / 'offline-tests.log'


def verify():
    BASE.mkdir(parents=True, exist_ok=True)
    prior = ref(ROOT, trial.PRIOR)
    preflight = trial.offline()
    command = ['.venv/bin/python', '-m', 'pytest', '-q',
               'tests/tooling/test_legal_mission_answer_tools.py',
               'tests/tooling/test_legal_mission_execution.py',
               'tests/tooling/test_legal_mission_control.py']
    test = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
    TESTS.write_text(test.stdout + test.stderr)
    require(test.returncode == 0 and ref(ROOT, trial.PRIOR) == prior,
            'Focused tests failed or predecessor ledger changed')
    rule_checks = {}
    for action in ('offline', 'prepare', 'verify', 'status', 'install-rules', 'execute'):
        result = subprocess.run(['codex', 'execpolicy', 'check', '--rules', str(trial.RULES),
            '.venv/bin/python', 'scripts/legal_mission_answer_tools.py', action],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
        require(json.loads(result.stdout).get('decision') == 'allow',
                'Reviewed rules lack exact action ' + action)
        rule_checks[action] = 'allow'
    for command_tail in (['.venv/bin/python', '-c', 'print'],
                         ['.venv/bin/python', 'scripts/legal_mission_answer_tools.py', 'launch']):
        result = subprocess.run(['codex', 'execpolicy', 'check', '--rules', str(trial.RULES),
            *command_tail], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
        require(not json.loads(result.stdout).get('matchedRules'),
                'Reviewed rules allow an unreviewed command')
    value = {'profile': 'answer-tools-offline-verification.v1',
             'at_utc': datetime.now(timezone.utc).isoformat(),
             'status': 'PASS', 'preflight': preflight,
             'tests': ref(ROOT, TESTS), 'test_command': command,
             'rules': ref(ROOT, trial.RULES), 'rule_checks': rule_checks,
             'negative_rules': ['inline Python', 'combined launch'],
             'predecessor_ledger_before_after': prior,
             'new_provider_calls': 0,
             'nonclaims': ['No actual answer or tool contribution established']}
    save(OFFLINE, value)
    print({'verification': 'PASS', 'tests': TESTS.read_text().strip().splitlines()[-1],
           'new_provider_calls': 0})


def record(task):
    require(OFFLINE.exists() and read(OFFLINE)['status'] == 'PASS',
            'Offline verification missing')
    execution = Execution()
    require(execution.summary()['tasks'][task]['status'] == 'RUNNING',
            'Task must be reserved before retaining its result')
    mapping = {
        'answer-tools-source': (
            'Exact questions, seven cross-question obligations and five typed cases retained; P11 is not assumed.',
            'Use the common source/case contract in the focused pilot; original duties remain open.',
            [trial.CONTRACT, trial.P14, trial.PLAN, trial.REVIEW, OFFLINE]),
        'answer-tools-route': (
            'Focused route and six installed backend checks pass local controls; failures isolate independent arms.',
            'Proceed only through separately reviewed live admission; do not infer legal warrant.',
            [Path(trial.__file__), trial.RULES, trial.POST_REVIEW, OFFLINE, TESTS]),
        'answer-tools-scope': (
            'P14, Gatecoin and full-matrix gaps remain independently explicit.',
            'Retain their separate question populations and the old whole-route refusal.',
            [ROOT / 'docs/implementation/legal-mission-control/answer-tools-scope-review.md']),
        'answer-tools-resource': (
            'Twenty enumerated proposed calls fit the original ceiling and clock arithmetically; no stage transfer or retry.',
            'Bind exact method and register live task before preparing any successor allowance.',
            [trial.RESOURCE_REVIEW, trial.PLAN, OFFLINE]),
        'answer-tools-post-review': (
            'Skeptical post-review passes a bounded focused diagnostic, subject to exact mission/allowance admission.',
            'Create and validate the separate admission record; preserve all original legal questions.',
            [trial.POST_REVIEW, trial.PLAN, trial.RESOURCE_REVIEW, OFFLINE]),
    }
    require(task in mapping, 'Unregistered offline result')
    conclusion, next_action, paths = mapping[task]
    output = BASE / (task + '-result.json')
    require(not output.exists(), 'Offline result already retained')
    save(output, {'task_id': task, 'status': 'SUCCEEDED',
        'conclusion': conclusion, 'next_action': next_action,
        'evidence': [ref(ROOT, p) for p in paths],
        'nonclaims': ['No original obligation closed', 'No live answer or tool benefit measured']})
    print({'task': task, 'result': ref(ROOT, output)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('verify', 'record'))
    parser.add_argument('task', nargs='?', choices=('answer-tools-source',
        'answer-tools-route', 'answer-tools-scope', 'answer-tools-resource',
        'answer-tools-post-review'))
    args = parser.parse_args()
    if args.action == 'verify':
        require(args.task is None, 'Verification takes no task')
        verify()
    else:
        require(args.task is not None, 'Record needs a fixed task')
        record(args.task)


if __name__ == '__main__':
    main()
