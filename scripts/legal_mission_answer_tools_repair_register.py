#!/usr/bin/env python3
"""Register one reviewed recovery, preserving every v4 task and charged call."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import argparse
import fcntl
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import BASE, STATE, ref, read, save, require, digest, validate_program, Execution
from scripts.legal_mission_answer_tools_register import node
from scripts import legal_mission_control as control

OLD = ROOT / BASE / 'execution-v4.json'
NEW = ROOT / BASE / 'execution-v5.json'
PLAN = ROOT / 'docs/plans/legal-mission-answer-tools-interface-repair.md'
REVIEW = ROOT / BASE / 'answer-tools-interface-repair-review.md'
SCRIPT = ROOT / 'scripts/legal_mission_answer_tools_recovery.py'
INTERFACE = ROOT / 'src/legalmath/interpretation/assurance/answer_interface.py'
RULES = ROOT / BASE / 'answer-tools-repair.rules'
RESULT = ROOT / BASE / 'results/answer-tools.md'
LEDGER = ROOT / 'artifacts/legal-mission-control/2026-10-12/answer-tools/allowance.json'


def register():
    with (ROOT / BASE / 'answer-tools-repair-registration.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = read(OLD)
        program = deepcopy(old)
        program['id'] = 'continuous-legal-mission-2026-10-12-answer-tools-recovery'
        program['predecessor_program'] = ref(ROOT, OLD)
        program['artifact_directory'] = 'artifacts/legal-mission-control/2026-10-12/answer-tools-repair-execution'
        files = (OLD, PLAN, REVIEW, SCRIPT, INTERFACE, RULES, RESULT, LEDGER, Path(__file__))
        program['protected_evidence'] += [ref(ROOT, p) for p in files]
        program['tasks'] += [
            node('answer-tools-interface-repair', 'engineering',
                 after=('answer-tools-closeout',),
                 deliverable='Expose exact answer identities and retain complete graph-repair diagnostics',
                 acceptance='Actual failure controls pass; historical sources and outputs unchanged; post-review recorded.',
                 inputs=(PLAN, REVIEW, SCRIPT, INTERFACE, RULES)),
            node('answer-tools-repair-live', 'product_evaluation',
                 needs=('answer-tools-interface-repair',),
                 deliverable='One repaired graph and independently attempted fresh matched answer arms',
                 acceptance='At most 17 new calls; source review and exact ledger retained; branch failures isolated.',
                 inputs=(PLAN, REVIEW, SCRIPT, INTERFACE, RULES, LEDGER)),
            node('answer-tools-repair-assessment', 'product_evaluation',
                 after=('answer-tools-repair-live',),
                 deliverable='Source-reviewed comparison or exact failures, refreshed mission and remaining gaps',
                 acceptance='Actual answer/source/tool receipts inspected; no statistical ranking or false closure.',
                 inputs=(PLAN, REVIEW)),
        ]
        validate_program(program, ROOT)
        mission_path = ROOT / BASE / 'mission.json'
        mission = read(mission_path)
        state = read(ROOT / STATE)
        if NEW.exists():
            require(read(NEW) == program, 'Registered recovery differs from reviewed program')
        else:
            require(mission['execution_program'] == ref(ROOT, OLD)
                    and state['program_hash'] == digest(old), 'Wrong predecessor')
            require(not any(r['status'] == 'RUNNING' for r in state['tasks'].values()), 'Prior task is running')
            require(state['tasks']['answer-tools-closeout']['status'] == 'SUCCEEDED', 'Prior trial not closed')
            require(len(read(LEDGER)['calls']) == 25, 'Reviewed final prefix differs')
            save(NEW, program)
        if state['program_hash'] == digest(old):
            for task in program['tasks'][len(old['tasks']):]:
                require(task['id'] not in state['tasks'], 'Recovery collision')
                state['tasks'][task['id']] = {'status': 'PENDING', 'attempts': []}
            state['events'].append({'task_id': None, 'action': 'REVIEWED_RECOVERY_REGISTERED',
                'at_utc': datetime.now(timezone.utc).isoformat(), 'predecessor': ref(ROOT, OLD),
                'successor': ref(ROOT, NEW), 'reason': 'One observed interface/graph recovery; no limit reset.'})
            state['program_hash'] = digest(program)
            save(ROOT / STATE, state)
        require(state['program_hash'] == digest(program), 'Recovery state differs')
        if mission['execution_program'] == ref(ROOT, OLD):
            mission['execution_program'] = ref(ROOT, NEW)
            mission['next_task_reason'] = 'Execute the one bounded answer-interface/graph recovery, then assess all independent answer arms under the original clock.'
            control.validate(mission, read(ROOT / BASE / 'tools.json'), ROOT)
            save(mission_path, mission)
        require(mission['execution_program'] == ref(ROOT, NEW), 'Recovery mission registration incomplete')
    print({'registered': str(NEW.relative_to(ROOT)), 'ready': Execution().summary()['ready'], 'predecessor_calls': 25})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register'])
    parser.parse_args()
    register()
