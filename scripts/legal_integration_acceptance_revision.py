"""One reviewed local migration of the existing master; no live grant or reset."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import subprocess
import sys

from scripts.legal_integration_master import (
    ROOT, DOC, BASE, PLAN, PROGRAM, STATE, QUESTIONS, TOOLS, MasterExecution, run_tests,
)
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance import validate_applicability, validate_inventory, evaluation_summary

WORK = BASE / 'acceptance-revision'
REVIEW = DOC / 'acceptance-revision-review-2026-10-13.md'
SOURCE_REVIEW = DOC / 'acceptance-scope-source-review-2026-10-13.md'
RESULT = DOC / 'results/acceptance-revision-execution-2026-10-13.md'
USER_INSTRUCTION = ('repair the master program for the acceptance criteria as you suggested.  '
    'refresh the master program with plans for closing the remaining gaps.  review the program.  execute.')
TESTS = [
    'tests/tooling/test_integration_acceptance.py', 'tests/tooling/test_integration_master.py',
    'tests/tooling/test_legal_mission_execution.py', 'tests/tooling/test_legal_mission_control.py',
    'tests/tooling/test_integration_campaign.py', 'tests/assurance/test_master_reopening.py',
    'tests/assurance/test_bounded_context.py', 'tests/assurance/test_bounded_product.py',
    'tests/assurance/test_bounded_references.py', 'tests/assurance/test_bounded_resume_identity.py',
]


def retain(path, value):
    path = ROOT / path
    if path.exists():
        require(read(path) == value, 'Refuse to overwrite retained revision evidence: ' + str(path))
    else:
        save(path, value)


def build_sources():
    from legalmath.canonical import digest as source_digest
    from legalmath.interpretation.assurance.answer_acceptance import validate_manifest
    before = BASE / 'reviewed-reopening/combined-envelope.json'
    envelope = deepcopy(read(ROOT / before))
    extracted = BASE / 'corpus-work/ut-handbook-current.txt'
    pages = (ROOT / extracted).read_text().split('\f')
    supplement = read(ROOT / BASE / 'corpus-work/source-supplement.json')
    verify(ROOT, supplement['handbook']['current_pdf'])
    for page in (16, 17, 18):
        require(pages[page - 1].strip(), 'Missing retained Handbook page')
        uid = f'handbook.oct2024.page{page}'
        require(all(u['unit_id'] != uid for u in envelope['source_packet']['units']), 'Duplicate source')
        envelope['source_packet']['units'].append({'unit_id': uid, 'text': pages[page - 1],
            'locator': f'SFC Handbook October 2024 fifth edition, PDF page {page}',
            'normative': True, 'span': {}})
        envelope['source_question_ids'][uid] = list(QUESTIONS)
    packet_hash = source_digest(envelope['source_packet'])
    envelope['source_qualification']['source_packet_hash'] = packet_hash
    envelope['source_qualification']['evidence'] += [ref(ROOT, SOURCE_REVIEW), ref(ROOT, extracted)]
    envelope['source_qualification']['limitations'].append(
        'Chapters 6-7 are supplied for conditional disclosure/monitoring analysis. '
        'Their applicability, rendered extraction and current-law status are not certified; '
        'they are not premises of the historical Gatecoin holdings.')
    envelope['binding'] = {'profile': 'bounded-combined-corpus.v3',
        'predecessors': [ref(ROOT, before), ref(ROOT, SOURCE_REVIEW)], 'source_packet_hash': packet_hash}
    envelope['binding_hash'] = source_digest(envelope['binding'])
    validate_manifest(envelope['answer_acceptance'], envelope['original_questions'], ROOT)
    require(all(envelope['answer_acceptance'][key] == read(ROOT / before)['answer_acceptance'][key]
                for key in ('acceptance_obligations', 'original_readings', 'cases')),
            'Source supplement changed original acceptance populations')
    retain(WORK / 'combined-envelope.json', envelope)
    return envelope


def build_registers(envelope, mission):
    from scripts.legal_mission_control import ANCHORS
    source = ref(ROOT, WORK / 'combined-envelope.json')
    review = ref(ROOT, SOURCE_REVIEW)
    original = ref(ROOT, ANCHORS['inventory'][0])
    target = {'source': source, 'questions': {r['question_id']: r['text']
              for r in envelope['original_questions']},
              'retrieval_scope': 'Exact original question over retained source units; no legal entailment claim'}
    retain(WORK / 'retrieval-targets.json', target)
    rows = []
    descriptions = {
        'bm25': ('rank source passages for the exact question', 'Exact question and immutable source units'),
        'legalruleml': ('preserve a supplied Boolean conditional in the installed representation',
                       'Source-warranted Boolean candidate with declared facts and counterexample'),
        'logical-english': ('check the retained parser translation on explicit true/false cases',
                            'Source-warranted Boolean candidate within eight facts and 128 expression nodes'),
        'pyarg': ('evaluate effective support/attack consequences', 'Warranted graph of at most 12 nodes'),
        'carneades': ('evaluate the installed argument adapter on explicit warrants', 'Warranted graph of at most 12 nodes'),
        'clingo': ('enumerate stable argument consequences and uncertainty', 'Warranted graph of at most 12 nodes'),
    }
    for q in QUESTIONS:
        question = next(r for r in mission['questions'] if r['id'] == q)
        for tool in TOOLS:
            mechanism, required = descriptions[tool]
            row = {'question': q, 'tool': tool,
                'decision': 'applicable' if tool == 'bm25' else 'target_required',
                'mechanism': mechanism, 'required_target': required,
                'reason': ('Exact source/question retrieval target exists; answer effect is still unmeasured.'
                    if tool == 'bm25' else 'Complete original-answer candidate/graph and its source-to-rule warrant are absent.'),
                'question_impact': question['current_gap'],
                'reopen_when': ('Reassess after corpus/question changes or an observed retrieval failure.'
                    if tool == 'bm25' else 'Review the exact original-answer target, warrant and supported/adverse boundary cases.'),
                'evidence': [review, source, *question['result_evidence']], 'reviewed': True}
            if tool == 'bm25':
                row.update(target_evidence=[ref(ROOT, WORK / 'retrieval-targets.json')], warrant_review=[review])
            rows.append(row)
    applicability = {'profile': 'legal-tool-applicability.v1', 'pairs': rows}
    validate_applicability(applicability, ROOT)
    retain(WORK / 'applicability.json', applicability)
    inventory = {'profile': 'legal-original-inventory-review.v1', 'records': [
        {'kind': kind, 'id': identifier, 'disposition': 'unreviewed',
         'reason': 'Inherited research record retained pending individual source/duplication/applicability review.',
         'evidence': [original], 'reviewed': False}
        for kind, ids in (('obligation', mission['original_obligation_ids']),
                          ('reading', mission['original_reading_ids'])) for identifier in ids]}
    validate_inventory(inventory, mission['original_obligation_ids'], mission['original_reading_ids'], ROOT)
    retain(WORK / 'inventory-dispositions.json', inventory)


def historical_projection(value, archives):
    if isinstance(value, dict):
        replacement = archives.get((value.get('path'), value.get('sha256')))
        if replacement: return {**value, **replacement}
        return {key: historical_projection(child, archives) for key, child in value.items()}
    if isinstance(value, list): return [historical_projection(child, archives) for child in value]
    return value


def register():
    existing = read(ROOT / PROGRAM)
    if existing.get('acceptance_revision'):
        return MasterExecution(ROOT, PROGRAM, STATE).summary()
    baseline = read(ROOT / WORK / 'baseline.json')
    archives = {(r['previous']['path'], r['previous']['sha256']): r['archive'] for r in baseline['archived']}
    prior = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    for row in baseline['archived']: verify(ROOT, row['archive'])
    for sealed in baseline['sealed']: verify(ROOT, sealed)
    old_program = read(ROOT / prior[str(PROGRAM)]['path'])
    old_state = read(ROOT / prior[str(STATE)]['path'])
    require(existing == old_program and read(ROOT / STATE) == old_state, 'Unexpected pre-migration state')
    require(not any(r['status'] == 'RUNNING' for r in old_state['tasks'].values()), 'Running owner cannot migrate')
    mission = read(ROOT / DOC / 'mission.json')
    envelope = build_sources()
    build_registers(envelope, mission)
    verification = ROOT / WORK / 'verification'
    verification.mkdir(parents=True, exist_ok=True)
    run_tests(TESTS + ['--tb=short'], verification)
    revision = {'profile': 'legal-acceptance-revision.v1', 'user_instruction': USER_INSTRUCTION,
        'prior_detours': 20, 'additional_consolidated_revision': 1, 'prior_charged_calls': 232,
        'live_calls_added': 0, 'attempts_reset': False, 'review': ref(ROOT, REVIEW),
        'prior_program': prior[str(PROGRAM)], 'prior_state': prior[str(STATE)],
        'applicability': ref(ROOT, WORK / 'applicability.json'),
        'inventory': ref(ROOT, WORK / 'inventory-dispositions.json'),
        'source_revision': ref(ROOT, WORK / 'combined-envelope.json'),
        'verification': ref(ROOT, verification / 'test-result.json'),
        'live_dispatch': 'BLOCKED_UNTIL_CURRENT_CODE_AND_SOURCE_QUALIFY; NO_ACQUISITION_ATTEMPT_ADDED'}
    program = historical_projection(deepcopy(old_program), archives)
    state = deepcopy(old_state)
    reopened = [t['id'] for t in program['tasks'] if t['executor'] == 'command'] + ['corpus-qualification', 'release-review']
    revision.update(reopened_nodes=reopened,
        attempt_ceilings={t: len(state['tasks'][t]['attempts']) + 1 for t in reopened})
    program['acceptance_revision'] = revision
    program['protected_evidence'] += [ref(ROOT, PLAN), ref(ROOT, REVIEW), ref(ROOT, SOURCE_REVIEW),
                                      revision['applicability'], revision['inventory']]
    for task in program['tasks']:
        tid = task['id']
        if tid not in reopened: continue
        task.update(executor='command', maximum_attempts=revision['attempt_ceilings'][tid],
            command=['.venv/bin/python', 'scripts/legal_integration_master.py', 'worker', tid], timeout_seconds=3600)
        task['inputs'] += [ref(ROOT, REVIEW)]
        task['acceptance_before_revision'] = task['acceptance']
        task['acceptance'] = ('Execute the acceptance revision work for this owner; retain actual scope, '
            'local results and unresolved prerequisites. A blocked qualification must remain BLOCKED. '
            'Original substantive acceptance remains required for integration; see acceptance_before_revision.')
        task['deliverable'] = str(BASE / tid / ('attempt-' + str(task['maximum_attempts'])) / 'result.json')
        state['tasks'][tid] = {'status': 'PENDING', 'attempts': state['tasks'][tid]['attempts'],
                              'prior_outcome': deepcopy(old_state['tasks'][tid])}
    # Local acceptance changes invalidate the former campaign qualification;
    # preserve its result and attempts without authorizing a new live attempt.
    live = state['tasks']['live-approval']
    live['prior_outcome'] = deepcopy(live)
    live.pop('result', None)
    live.update(status='BLOCKED', reason=revision['live_dispatch'], dispatch_status='NOT_DISPATCHED',
                prerequisite_evidence=[ref(ROOT, REVIEW)])
    for item in program['remaining_work']:
        item['execution_authorization'] = 'SAME_MASTER_REVIEWED_LOCAL_PACKAGE; NO_LIVE_ATTEMPT_RESET'
        item['phase_plan'] = ref(ROOT, PLAN)
        if item['id'] in {'R09', 'R12', 'R15'}:
            item['status'] = 'LOCALLY_REPAIRED'
            item['verification'] = revision['verification']
        if item['id'] == 'S01':
            item['status'] = 'SOURCE_INCLUDED; PRODUCT_USE_UNQUALIFIED'
            item['source_revision'] = revision['source_revision']
    validate_program(program, ROOT)
    state['program_hash'] = digest(program)
    state['events'].append({'task_id': None, 'action': 'REVIEWED_ACCEPTANCE_REVISION',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'review': ref(ROOT, REVIEW),
        'attempts_reset': False, 'live_calls_added': 0, 'reopened_nodes': reopened})
    mission = historical_projection(mission, archives)
    tools = historical_projection(read(ROOT / DOC / 'tools.json'), archives)
    for tool in tools:
        if tool['id'] not in TOOLS: continue
        tool['evaluation_completion'] = {'status': 'incomplete', 'scope': 'Complete original four-question product',
            'reason': 'Original complete matched answers are absent; applicability and adoption are separate decisions.',
            'reopen_when': 'Qualify original answers and supported native targets; retain a valid matched effect or reviewed scope rejection.',
            'applicability': revision['applicability']}
    with (ROOT / DOC / 'mission.json').with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (ROOT / STATE).with_suffix('.lock').open('a') as state_lock:
            fcntl.flock(state_lock, fcntl.LOCK_EX)
            require(read(ROOT / PROGRAM) == old_program and read(ROOT / STATE) == old_state,
                    'State changed during migration review')
            save(ROOT / PROGRAM, program)
            save(ROOT / STATE, state)
            mission['integration_master'].update(program=ref(ROOT, PROGRAM), plan=ref(ROOT, PLAN),
                acceptance_revision=revision, latest_acceptance_review=ref(ROOT, REVIEW))
            reason = 'Execute all ready local acceptance-revision owners; preserve consumed acquisition attempts and current-binding prerequisites.'
            mission['next_task_reason'] = reason
            mission['history'].append({'id': 'integration-master-acceptance-revision-2026-10-13',
                'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
                'decision': 'Reviewed acceptance repair registered in the same graph; one consolidated local revision, no historical reset.',
                'next_task': 'product-contribution', 'next_task_reason': reason,
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'result_evidence': [ref(ROOT, PROGRAM), ref(ROOT, PLAN), ref(ROOT, REVIEW), revision['verification']]})
            save(ROOT / DOC / 'tools.json', tools)
            save(ROOT / DOC / 'mission.json', mission)
    from scripts import legal_mission_control as control
    require(control.validate(mission, tools, ROOT)['detours_since_advance'] == 21, 'Lost detour accounting')
    for tid, row in old_state['tasks'].items():
        require(read(ROOT / STATE)['tasks'][tid]['attempts'] == row['attempts'], 'Migration altered attempts')
    for sealed in baseline['sealed']: verify(ROOT, sealed)
    retain(WORK / 'migration.json', {'prior_program': prior[str(PROGRAM)], 'current_program': ref(ROOT, PROGRAM),
        'prior_state': prior[str(STATE)], 'preserved_attempts': True, 'sealed_unchanged': baseline['sealed'],
        'reopened_nodes': reopened, 'detours': 21, 'live_calls_added': 0,
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'environment': sys.executable, 'device': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'command': '.venv-context/bin/python scripts/legal_integration_master.py prepare',
        'plan': ref(ROOT, PLAN), 'data': revision['source_revision'], 'seeds': 'N/A: deterministic records'})
    return MasterExecution(ROOT, PROGRAM, STATE).summary()


def worker(tid, directory):
    program = read(ROOT / PROGRAM)
    revision = program['acceptance_revision']
    require(tid in revision['reopened_nodes'], 'Task outside reviewed local revision')
    for key in ('review', 'source_revision', 'verification', 'applicability', 'inventory'):
        verify(ROOT, revision[key])
    require(read(ROOT / revision['verification']['path'])['exit_code'] == 0, 'Local repair tests failed')
    common = {'acceptance_revision': ref(ROOT, REVIEW), 'verification': revision['verification'],
              'engineering_qualified': False, 'legal_acceptance': False, 'tool_effect_established': False}
    if tid == 'scope':
        from scripts.legal_mission_control import ANCHORS
        for path, sha in ANCHORS.values(): verify(ROOT, {'path': path, 'sha256': sha})
        matrix = validate_applicability(read(ROOT / revision['applicability']['path']), ROOT)
        return {**common, 'pairs': len(matrix), 'pair_decisions': dict(Counter(r['decision'] for r in matrix.values())),
            'obligations': 46, 'readings': 35, 'cases': 12, 'premises': 224, 'subparts': 407,
            'inventory': revision['inventory'], 'source': revision['source_revision']}
    if tid == 'sources':
        envelope = read(ROOT / revision['source_revision']['path'])
        for evidence in envelope['source_qualification']['evidence']: verify(ROOT, evidence)
        return {**common, 'source': revision['source_revision'], 'added_pdf_pages': [16, 17, 18],
            'units': len(envelope['source_packet']['units']), 'S01': 'Omission repaired in candidate source revision',
            'remaining': ['Rendered fidelity and complete locator ownership', 'Dated applicability and later treatment']}
    if tid in {'runtime', 'product'}:
        issues = ['R13', 'R14'] if tid == 'runtime' else ['R06', 'R08', 'R14']
        return {**common, 'locally_repaired': ['R09'] if tid == 'runtime' else ['R12'],
            'remaining_issues': [r for r in program['remaining_work'] if r['id'] in issues],
            '_node_status': 'BLOCKED', '_conclusion': ('Acceptance and failure controls pass; '
                + ('package content identity and complete decoded/provider capacity remain unqualified.'
                   if tid == 'runtime' else 'document/proposition binding and cross-source semantic handling remain unqualified.'))}
    if tid.startswith('native-'):
        tool = tid[7:]
        if tool == 'bm25':
            from scripts.legal_independent_tools import IndependentProductToolBackend
            envelope = read(ROOT / revision['source_revision']['path'])
            backend = IndependentProductToolBackend([tool])
            outputs = {q['question_id']: backend.retrieval(envelope['source_packet'], {'question': q['text']},
                directory / q['question_id']) for q in envelope['original_questions']}
            require(all(r['status'] == 'PASS' and r['passages'] for r in outputs.values()), 'Original retrieval failed')
            save(directory / 'native.json', {'output': outputs, 'identity': backend.identity(),
                'source': revision['source_revision'], 'downstream_effect': 'NOT_EVALUATED'})
            return {**common, 'original_question_retrieval': ref(ROOT, directory / 'native.json')}
        from scripts.legal_integration_master import native
        return {**common, **native(tool, directory), 'applicability': 'TARGET_REQUIRED_FOR_ORIGINAL_ANSWERS'}
    if tid.startswith('legal-'):
        q = tid[6:]
        mission = read(ROOT / DOC / 'mission.json')
        question = next(r for r in mission['questions'] if r['id'] == q)
        return {**common, 'question': question['question'], 'retained_conditional_analysis': question['result_evidence'],
            'source_supplement_review': ref(ROOT, SOURCE_REVIEW), 'unresolved': question['current_gap'],
            'fact_policy': 'Only affected conclusions require client facts; conditional analysis retained.',
            '_node_status': 'BLOCKED', '_conclusion': q + ': conditional analysis retained; individual inventory dispositions, exact source warrants and dated authority research remain open.'}
    if tid == 'corpus-qualification':
        prior = BASE / 'reviewed-reopening/corpus-audit/result.json'
        verify(ROOT, ref(ROOT, prior))
        return {**common, 'prior_actual_locator_audit': ref(ROOT, prior),
            'new_source': revision['source_revision'], 'source_review': ref(ROOT, SOURCE_REVIEW),
            '_node_status': 'BLOCKED', '_conclusion': 'Chapters 6-7 now included; full judgment/Handbook paragraph, footnote and annexure ownership remains unqualified (S02).'}
    if tid.startswith('qualify-'):
        return {**common, '_node_status': 'BLOCKED',
                '_conclusion': 'Actual source semantics and complete provider/output capacity must qualify before acquisition.'}
    if tid == 'campaign':
        matrix = validate_applicability(read(ROOT / revision['applicability']['path']), ROOT)
        return {**common, 'applicability': revision['applicability'],
            'applicable_arms': {q: ['baseline'] + [t for t in TOOLS if matrix[q, t]['decision'] == 'applicable'] for q in QUESTIONS},
            'budget_formula': '(1 + applicable_tool_count) * measured_answer_bound + 6 * applicable_tool_count per question',
            'unresolved_pair_count': sum(r['decision'] in {'target_required', 'unresolved'} for r in matrix.values()),
            'R15': 'Dormant helper import repaired and tested', 'dispatch_ready': False,
            '_node_status': 'BLOCKED', '_conclusion': 'Concrete applicable-arm plan retained; source/product/runtime qualification and current binding prevent live dispatch. All acquisition attempts remain 3/3.'}
    if tid == 'release-review':
        return {**common, 'assessment_complete': True, 'frontier': MasterExecution(ROOT, PROGRAM, STATE).summary(),
            'tool_decisions': evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT),
            'remaining_work': program['remaining_work'], 'charged_calls': 232,
            '_conclusion': 'Acceptance repair assessment complete; original answers and selected-tool effects remain incomplete. Independent local work executed; no live allowance or attempt was reset.'}
    raise ValueError('No acceptance-revision worker for ' + tid)


def settle():
    execution = MasterExecution(ROOT, PROGRAM, STATE)
    view = execution.summary()
    require(not view['ready'] and not view['running'], 'Independent authorized work remains')
    baseline = read(ROOT / WORK / 'baseline.json')
    for item in baseline['sealed']: verify(ROOT, item)
    old = read(ROOT / next(r['archive']['path'] for r in baseline['archived'] if r['previous']['path'] == str(STATE)))
    current = read(ROOT / STATE)
    for tid, row in old['tasks'].items():
        require(current['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost historical attempts')
    manifest = {'profile': 'legal-acceptance-revision-result.v1', 'program': ref(ROOT, PROGRAM),
        'plan': ref(ROOT, PLAN), 'execution': view['execution'], 'ready': view['ready'], 'running': view['running'],
        'task_counts': dict(Counter(r['status'] for r in view['tasks'].values())), 'frontier': view,
        'charged_calls': 232, 'live_calls_added': 0, 'detours': 21, 'historical_attempts_preserved': True,
        'sealed_evidence_unchanged': baseline['sealed'], 'fully_evaluated_tools': 0, 'integration_complete': False,
        'verification': ref(ROOT, WORK / 'verification/test-result.json'),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': '.venv-context/bin/python scripts/legal_integration_master.py run',
        'environment': sys.executable, 'device': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat()}
    path = ROOT / WORK / 'execution-result.json'
    if not path.exists(): save(path, manifest)
    return manifest


def finalize_records():
    """Bind the final review to mission history without changing executed results."""
    from scripts import legal_mission_control as control
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    require(not view['ready'] and not view['running'], 'Ready work cannot be replaced by a report')
    result = ref(ROOT, RESULT)
    final_check = ref(ROOT, WORK / 'post-review/test-result.json')
    require(read(ROOT / final_check['path'])['exit_code'] == 0, 'Post-review controls failed')
    dispatch_check = ref(ROOT, WORK / 'dispatch-boundary-review/test-result.json')
    require(read(ROOT / dispatch_check['path'])['exit_code'] == 0, 'Live-binding boundary check failed')
    reason = ('Acceptance revision executed: evaluation, scope and adoption are separate; '
        'R09/R12/R15 repaired locally and Handbook Chapters 6-7 included. Integration remains incomplete. '
        'Remaining work is original inventory/warrant review, S02/R06 source/assertion binding, '
        'R08 cross-source semantics, R13 package identity, R14 full decoded/provider capacity, '
        'R01 live semantic qualification and R02/R10/R11 original answers/targets/effects. '
        'No ready local work remains under this package; 232 calls, original live deadline and all prior attempts remain.')
    with (ROOT / DOC / 'mission.json').with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(ROOT / DOC / 'mission.json')
        tools = read(ROOT / DOC / 'tools.json')
        identifier = 'integration-master-acceptance-revision-executed-2026-10-13'
        if not any(row['id'] == identifier for row in mission['history']):
            mission['history'].append({'id': identifier, 'task_id': 'product-contribution',
                'kind': 'product_evaluation', 'outcome': 'no_advance',
                'decision': 'Executed the reviewed acceptance repair and independent local branches; retained all substantive blockers.',
                'next_task': 'product-contribution', 'next_task_reason': reason,
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'result_evidence': [result, ref(ROOT, WORK / 'execution-result.json'), final_check]})
        boundary_id = 'integration-master-acceptance-dispatch-boundary-review-2026-10-13'
        if not any(row['id'] == boundary_id for row in mission['history']):
            implementation = [ref(ROOT, p) for p in (
                'scripts/legal_integration_acceptance.py', 'scripts/legal_integration_acceptance_revision.py',
                'scripts/legal_mission_control.py', 'scripts/legal_mission_execution.py',
                'scripts/legal_integration_master.py', 'scripts/legal_integration_campaign.py',
                'scripts/legal_integration_reopening.py', 'tests/tooling/test_integration_acceptance.py')]
            manifest = ROOT / WORK / 'final-implementation.json'
            save(manifest, {'implementation': implementation, 'verification': [final_check, dispatch_check],
                'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'result': result, 'plan': ref(ROOT, PLAN), 'data': mission['integration_master']['acceptance_revision']['source_revision'],
                'command': 'finalize_records via .venv-context/bin/python', 'environment': sys.executable,
                'device': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A: deterministic controls',
                'wall_seconds': sum(read(ROOT / p['path'])['wall_seconds'] for p in (final_check, dispatch_check)),
                'verification_scope': 'Post-review scheduler/acceptance controls and dispatch-free binding veto',
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'live_calls_added': 0})
            mission['history'].append({'id': boundary_id, 'task_id': 'product-contribution',
                'kind': 'product_evaluation', 'outcome': 'no_advance',
                'decision': 'Final review validates preserved attempts, retry markers and refusal to reuse the consumed live binding.',
                'next_task': 'product-contribution', 'next_task_reason': reason,
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'result_evidence': [result, ref(ROOT, manifest), dispatch_check]})
        mission['integration_master']['latest_acceptance_review'] = result
        mission['next_task_reason'] = reason
        target = next(row for row in mission['tasks'] if row['id'] == 'product-contribution')
        target.update(status='blocked', blocker_kind='substantive_qualification_and_consumed_live_attempts',
            blocker_scope='Only each relevant dependency blocks its consumers; all admitted independent local branches were assessed.',
            blocker_evidence=[result, ref(ROOT, WORK / 'execution-result.json')],
            remaining_work_review=str(RESULT), execution_limit_note=
                '232/8100 current-master calls, historical 41 calls, detour 21. '
                'Original live deadline 2026-10-18T19:03:39.626294+00:00; acquisition remains 3/3. '
                'Current code/source has no inherited live qualification.')
        for tool in tools:
            if tool['id'] not in TOOLS: continue
            if result not in tool['evidence']: tool['evidence'].append(result)
            tool['acceptance_revision_result'] = {'review': result, 'effect': 'INCOMPLETE',
                'applicability': 'applicable' if tool['id'] == 'bm25' else 'target_required',
                'native_control': ref(ROOT, BASE / ('native-' + tool['id']) / 'attempt-3/native.json')}
        require(control.validate(mission, tools, ROOT)['detours_since_advance'] == 21, 'Changed detour accounting')
        save(ROOT / DOC / 'tools.json', tools)
        save(ROOT / DOC / 'mission.json', mission)
    return view
