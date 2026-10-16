#!/usr/bin/env python3
"""One-time reviewed graph registration; preserves every predecessor attempt."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
from pathlib import Path
import sys

ROOT_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_PATH))

from scripts.legal_mission_execution import ROOT, BASE, PROGRAM, STATE, Execution, digest, read, ref, save, require, validate_program
from scripts import legal_mission_control as control

OLD = ROOT / BASE / 'execution-v3.json'
NEW = ROOT / BASE / 'execution-v4.json'
MISSION = ROOT / BASE / 'mission.json'
PARENT = ROOT / 'docs/plans/legal-mission-answer-tool-successor.md'
REVIEW = ROOT / BASE / 'answer-tools-review.md'
POST = ROOT / BASE / 'answer-tools-post-review.md'
SCOPE = ROOT / BASE / 'answer-tools-scope-review.md'
RESOURCE = ROOT / BASE / 'answer-tools-resource-review.md'
SCRIPT = ROOT / 'scripts/legal_mission_answer_tools.py'
RULES = ROOT / BASE / 'answer-tools.rules'


def node(key, kind, *, needs=(), after=(), deliverable, acceptance, inputs=(), priority=2):
    return {'id': key, 'kind': kind, 'executor': 'agent',
            'deliverable': deliverable, 'acceptance': acceptance,
            'question_ids': ['p10', 'evidence'], 'requires': list(needs),
            'after': list(after), 'any_success': [], 'priority': priority,
            'maximum_attempts': 1, 'write_resources': [key],
            'inputs': [ref(ROOT, p) for p in inputs]}


def program():
    old = read(OLD)
    require(old['profile'] == 'legal-mission-execution.v1' and
            old['deadline_utc'] == '2026-10-12T04:28:01+00:00' and
            old['global_call_ceiling'] == 400 and old['prior_detours'] == 9,
            'Historical resource identity changed')
    extra = [
        node('answer-tools-source', 'source_analysis',
             deliverable='Exact P10/evidence source obligations and typed case facts',
             acceptance='P11 applicability, two P14 axes and incorporation preserved without source mutation.',
             inputs=(PARENT, REVIEW), priority=1),
        node('answer-tools-route', 'engineering',
             deliverable='Focused answer and installed-tool route with failed-branch isolation',
             acceptance='Source/transport/ledger tests and actual six-tool offline product delivery pass.',
             inputs=(SCRIPT, RULES, REVIEW)),
        node('answer-tools-scope', 'source_analysis',
             deliverable='Independent P14/Gatecoin and full-route scope review',
             acceptance='Unassessed questions, populations and prior whole-route guard remain explicit.',
             inputs=(SCOPE,), priority=1),
        node('answer-tools-resource', 'resource_review',
             deliverable='Finite 20-call successor and exact command review',
             acceptance='Original 17-call prefix, 400 ceiling, deadline, stage IDs and no automatic retries retained.',
             inputs=(RESOURCE, PARENT)),
        node('answer-tools-post-review', 'review',
             needs=('answer-tools-source', 'answer-tools-route', 'answer-tools-resource'),
             deliverable='Post-implementation skeptical audit and live diagnostic decision',
             acceptance='Wrong baseline, scope, limits, branch independence and tool/warrant boundaries reviewed.',
             inputs=(POST,)),
        node('answer-tools-live', 'product_evaluation', needs=('answer-tools-post-review',),
             deliverable='Actual source-bound baseline and independently attempted tool answer arms',
             acceptance='Exact selected questions, source/cases, stage receipts, 20-call ceiling and clock preserved.',
             inputs=(SCRIPT, RULES, PARENT, POST, RESOURCE)),
        node('answer-tools-assessment', 'product_evaluation',
             after=('answer-tools-live', 'answer-tools-scope'),
             deliverable='Source-reviewed answer and matched per-tool effect or exact blockers',
             acceptance='Separate legal quality, downstream consideration, explanatory results and nonclaims.'),
        node('answer-tools-closeout', 'reporting',
             after=('answer-tools-assessment', 'answer-tools-source',
                    'answer-tools-route', 'answer-tools-resource', 'answer-tools-scope'),
             deliverable='Mission history and refreshed next substantive task',
             acceptance='Every independent branch has a result or concrete blocker; no false completion.'),
    ]
    require(not set(t['id'] for t in extra) & set(t['id'] for t in old['tasks']),
            'Successor task ID collides with predecessor')
    result = deepcopy(old)
    result['id'] = 'continuous-legal-mission-2026-10-12-answer-tools'
    result['artifact_directory'] = 'artifacts/legal-mission-control/2026-10-12/answer-tools-execution'
    result['protected_evidence'] = old['protected_evidence'] + [
        ref(ROOT, p) for p in (OLD, PARENT, REVIEW, POST, SCOPE, RESOURCE, SCRIPT, RULES)]
    result['tasks'] += extra
    validate_program(result, ROOT)
    return result


def register():
    expected = program()
    with (ROOT / BASE / 'answer-tools-registration.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(MISSION)
        state = read(ROOT / STATE)
        previous = ref(ROOT, OLD)
        target = ref(ROOT, NEW) if NEW.exists() else None
        if NEW.exists():
            require(read(NEW) == expected, 'Existing v4 graph differs from reviewed candidate')
        else:
            require(mission.get('execution_program') == previous and
                    state['program_hash'] == digest(read(OLD)),
                    'Current graph or state differs from preserved predecessor')
            save(NEW, expected)
            target = ref(ROOT, NEW)
        if state['program_hash'] == digest(read(OLD)):
            require(set(state['tasks']) == {t['id'] for t in read(OLD)['tasks']},
                    'Predecessor task state changed')
            for task in expected['tasks'][len(read(OLD)['tasks']):]:
                state['tasks'][task['id']] = {'status': 'PENDING', 'attempts': []}
            state['events'].append({'task_id': None, 'action': 'REVIEWED_SUCCESSOR_REGISTERED',
                'at_utc': datetime.now(timezone.utc).isoformat(),
                'predecessor': previous, 'successor': target,
                'reason': 'Independent answer/tool successor under original grant and deadline; no provider call.'})
            state['program_hash'] = digest(expected)
            save(ROOT / STATE, state)
        require(state['program_hash'] == digest(expected) and
                set(state['tasks']) == {t['id'] for t in expected['tasks']},
                'Successor state migration incomplete')
        if mission.get('execution_program') == previous:
            mission['execution_program'] = target
            mission['next_task_reason'] = (
                'Execute independent reviewed answer-tool source, route, scope and resource branches; '
                'only the registered live branch may seek finite provider admission.')
            control.validate(mission, read(ROOT / BASE / 'tools.json'), ROOT)
            save(MISSION, mission)
        require(mission.get('execution_program') == target,
                'Mission graph registration incomplete')
    print({'registration': 'PASS', 'predecessor_tasks': len(read(OLD)['tasks']),
           'successor_tasks': len(expected['tasks']), 'program': target,
           'execution': Execution().summary()['execution']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('register',))
    parser.parse_args()
    register()


if __name__ == '__main__':
    main()
