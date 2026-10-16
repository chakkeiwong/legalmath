"""Record the existing remaining-work package without resetting its execution."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import subprocess
import sys

from scripts.legal_integration_master import ROOT, DOC, BASE, PROGRAM, PLAN, STATE, QUESTIONS, TOOLS, MasterExecution
from scripts.legal_integration_remaining import WORK, RESULT, retain
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_acceptance import validate_applicability, validate_inventory
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program

RECORDS = WORK / 'final-records'


def registers(program):
    """Current scope evidence does not change a tool's observed-effect status."""
    targets_ref = ref(ROOT, BASE / 'sources/attempt-4/original-targets.json')
    target_review = ref(ROOT, BASE / 'sources/attempt-4/target-review.json')
    source_review = ref(ROOT, DOC / 'remaining-work-source-review-2026-10-13.md')
    targets = read(ROOT / targets_ref['path'])
    old = read(ROOT / program['acceptance_revision']['applicability']['path'])
    matrix = deepcopy(old)
    for row in matrix['pairs']:
        qid, tool = row['question'], row['tool']
        native = ref(ROOT, BASE / ('native-' + tool) / 'attempt-4/native.json')
        exists = tool in ('bm25', 'legalruleml', 'logical-english') or bool(targets[qid]['proposals'])
        row.update(decision='applicable' if exists else 'target_required',
            reason=('A reviewed restricted original-source target executed in the native adapter; '
                    'its effect on the complete answer remains unmeasured.' if exists else
                    'No reviewed argument graph for this original question; this is unfinished target work.'),
            question_impact=targets[qid]['warrant_limit'],
            reopen_when='Reassess when the generated original-answer target or its source warrant differs; preserve unsupported semantics.',
            evidence=[source_review, targets_ref, native], reviewed=True,
            prepared_target_scope=targets[qid]['warrant_limit'],
            actual_answer_effect='NOT_EVALUATED')
        if exists:
            row.update(target_evidence=[targets_ref, native], warrant_review=[target_review, source_review])
    validate_applicability(matrix, ROOT)
    retain(RECORDS / 'applicability.json', matrix)
    owners = {t['id']: Path(t['deliverable']).parent for t in program['tasks']}
    inventories = [read(ROOT / owners['legal-' + q] / 'inventory-dispositions.json') for q in QUESTIONS]
    require(all(value == inventories[0] for value in inventories), 'Per-question inventory dispositions disagree')
    source = read(ROOT / WORK / 'quotation-repair-envelope.json')
    acceptance = source['answer_acceptance']
    validate_inventory(inventories[0], [r['id'] for r in acceptance['acceptance_obligations']],
                       [r['id'] for r in acceptance['original_readings']], ROOT)
    retain(RECORDS / 'inventory-dispositions.json', inventories[0])
    return {'applicability': ref(ROOT, RECORDS / 'applicability.json'),
            'inventory': ref(ROOT, RECORDS / 'inventory-dispositions.json')}


def finalize():
    final_path = ROOT / RECORDS / 'settlement.json'
    if final_path.exists():
        result = read(final_path)
        verify(ROOT, result['program'])
        verify(ROOT, result['result'])
        return result
    baseline = read(ROOT / RECORDS / 'baseline.json')
    archives = {(r['previous']['path'], r['previous']['sha256']): r['archive'] for r in baseline['archived']}
    prior = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    for item in archives.values(): verify(ROOT, item)
    old_program = read(ROOT / prior[str(PROGRAM)]['path'])
    old_state = read(ROOT / prior[str(STATE)]['path'])
    require(read(ROOT / PROGRAM) == old_program and read(ROOT / STATE) == old_state,
            'Execution changed during final review; preserve it before recording')
    require(not any(r['status'] == 'RUNNING' for r in old_state['tasks'].values()), 'Worker still running')
    checks_ref = ref(ROOT, WORK / 'final-review/verification.json')
    checks = read(ROOT / checks_ref['path'])
    for item in checks['implementation']: verify(ROOT, item)
    require(read(ROOT / checks['tests']['path'])['exit_code'] == 0, 'Final controls failed')
    capacities = {}
    for q, row in checks['questions'].items():
        verify(ROOT, row['capacity'])
        capacity = read(ROOT / row['capacity']['path'])
        capacities[q] = {'requests': len(capacity['measurements']),
            'construction_blocks': capacity['construction_blocks'], 'request_failures': capacity['request_failures'],
            'maximum_local_tokens': max(r['local_tokens'] for r in capacity['measurements'])}
    program = historical_projection(deepcopy(old_program), archives)
    current = registers(program)
    revision = program['remaining_work_revision']
    revision.update(**current, source_revision=checks['source'], final_verification=checks_ref,
                    execution_result=ref(ROOT, RESULT), final_review=ref(ROOT, RECORDS / 'review.md'))
    updates = {
        'R06': ('PARTIALLY_REPAIRED', 'Document/index/prose-field quotation binding repaired; source entailment remains open.'),
        'R08': ('PARTIALLY_REPAIRED', 'One dependency retrieval round and fresh interaction review implemented; actual remote-exception semantics unqualified.'),
        'R10': ('LOCALLY_REPAIRED; LIVE_USE_UNQUALIFIED', 'One opt-in source-backed correction preserves original/fresh review; not yet exercised on a live original answer.'),
        'R11': ('PARTIALLY_REPAIRED', '18 restricted target pairs have native execution; 6 argument pairs and all complete matched effects remain open.'),
        'R13': ('LOCALLY_REPAIRED_WITH_DECLARED_SCOPE', 'Relevant selected packages, schemas and native/parser trees have content identity; whole-host attestation is outside scope.'),
        'R14': ('PARTIALLY_REPAIRED', 'Wire/decoded bounds and complete request planning repaired; service framing and actual final-answer review remain unqualified.'),
        'S01': ('SOURCE_INCLUDED; PRODUCT_USE_UNQUALIFIED', '80-unit packet constructs; both legal indexes and 164 quotation locations rebuilt against exact packet.'),
        'S02': ('PARTIALLY_REVIEWED', '566 judgment components and 137 footnotes retained; displayed numbering, heading/annexure boundaries and Handbook locators remain unqualified.'),
        'L01': ('PARTIALLY_REVIEWED', 'Conditional original-source targets and 81 retained individual dispositions reviewed; governing-standard and later-treatment limits remain.'),
    }
    for item in program['remaining_work']:
        item['phase_plan'] = ref(ROOT, PLAN)
        if item['id'] in updates:
            item['status'], item['finding'] = updates[item['id']]
            item['verification'] = checks_ref
            item['current_result'] = ref(ROOT, RESULT)
    program['protected_evidence'] += [ref(ROOT, PLAN), ref(ROOT, RESULT), checks_ref,
        *current.values(), checks['source'], ref(ROOT, RECORDS / 'review.md')]
    validate_program(program, ROOT)
    state = deepcopy(old_state)
    state['program_hash'] = digest(program)
    state['events'].append({'task_id': None, 'action': 'REMAINING_WORK_FINAL_VERIFICATION',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'verification': checks_ref,
        'attempts_added': 0, 'calls_added': 0})
    mission = historical_projection(read(ROOT / DOC / 'mission.json'), archives)
    tools = historical_projection(read(ROOT / DOC / 'tools.json'), archives)
    for tool in tools:
        if tool['id'] not in TOOLS: continue
        tool['evaluation_completion']['applicability'] = current['applicability']
        tool['remaining_work_result'] = {'review': ref(ROOT, RESULT), 'effect': 'INCOMPLETE',
            'native_targets': ref(ROOT, BASE / ('native-' + tool['id']) / 'attempt-4/native.json'),
            'applicability': current['applicability'], 'actual_answer_effect_established': False}
    reason = ('Complete source locator qualification and original-question argument targets independently; '
        'then bind current code/source and finite service controls before original answers and matched effects. '
        'Local repairs and scope reviews are retained, not legal or tool-effect acceptance. '
        'All prior attempts, 232 current/41 historical calls and both deadlines are unchanged.')
    with (ROOT / DOC / 'mission.json').with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (ROOT / STATE).with_suffix('.lock').open('a') as state_lock:
            fcntl.flock(state_lock, fcntl.LOCK_EX)
            require(read(ROOT / PROGRAM) == old_program and read(ROOT / STATE) == old_state, 'Finalization race')
            save(ROOT / PROGRAM, program); save(ROOT / STATE, state)
            mission['integration_master'].update(program=ref(ROOT, PROGRAM), plan=ref(ROOT, PLAN),
                remaining_work_revision=revision, acceptance_revision=program['acceptance_revision'],
                latest_remaining_work_review=ref(ROOT, RESULT))
            mission['next_task_reason'] = reason
            mission['history'].append({'id': 'integration-master-remaining-work-executed-2026-10-13',
                'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
                'decision': 'Local product/source/native repairs executed and reviewed; complete original effects remain open.',
                'next_task': 'product-contribution', 'next_task_reason': reason,
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'result_evidence': [ref(ROOT, RESULT), checks_ref, ref(ROOT, PLAN), ref(ROOT, PROGRAM),
                                    ref(ROOT, RECORDS / 'review.md')]})
            target = next(row for row in mission['tasks'] if row['id'] == 'product-contribution')
            target.update(status='blocked', blocker_kind='remaining_source_semantic_and_answer_qualification',
                blocker_scope='Question/source-specific qualifications and current live binding; local repairs do not close legal answers.',
                blocker_evidence=[ref(ROOT, RESULT), checks_ref], remaining_work_review=str(RESULT),
                execution_limit_note='232/8100 current-master calls; 41 historical calls; detour 22; no new live attempt or deadline.')
            save(ROOT / DOC / 'tools.json', tools); save(ROOT / DOC / 'mission.json', mission)
    from scripts import legal_mission_control as control
    validated = control.validate(mission, tools, ROOT)
    require(validated['detours_since_advance'] == 22 and validated['original_inventory_dispositions_complete'],
            'Final records lost accounting or reviewed inventory')
    execution = MasterExecution(ROOT, PROGRAM, STATE).summary()
    require(not execution['ready'] and not execution['running'], 'Independent admitted work remains')
    require(read(ROOT / STATE)['tasks'] == old_state['tasks'], 'Final records altered attempts or outcomes')
    for item in read(ROOT / WORK / 'baseline.json')['sealed']: verify(ROOT, item)
    result = {'profile': 'remaining-work-final-records.v1', 'program': ref(ROOT, PROGRAM),
        'plan': ref(ROOT, PLAN), 'result': ref(ROOT, RESULT), 'verification': checks_ref,
        'registers': current, 'capacity': capacities, 'ready': [], 'running': [],
        'task_counts': dict(Counter(r['status'] for r in execution['tasks'].values())),
        'calls': 232, 'historical_calls': 41, 'detours': 22, 'live_calls_added': 0,
        'attempts_unchanged': True, 'sealed_unchanged': True, 'integration_complete': False,
        'implementation': [ref(ROOT, p) for p in ('scripts/legal_integration_remaining_records.py',
            'scripts/legal_integration_acceptance.py', 'scripts/legal_integration_campaign.py',
            'scripts/legal_mission_control.py')],
        'environment': sys.executable, 'device': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'command': '.venv-context/bin/python -m scripts.legal_integration_remaining_records',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'seeds': 'N/A: deterministic local checks; no stochastic comparison',
        'wall_seconds': read(ROOT / checks['tests']['path'])['wall_seconds'],
        'wall_time_scope': 'Final regression command; per-node runtimes remain in original result manifests.',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat()}
    save(final_path, result)
    return result


if __name__ == '__main__':
    print(json.dumps(finalize(), indent=2))
