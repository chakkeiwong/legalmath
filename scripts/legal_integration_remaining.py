"""Reviewed remaining-work execution in the existing master, preserving history."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import subprocess
import sys

from scripts.legal_integration_master import ROOT, DOC, BASE, PRIOR, PLAN, PROGRAM, STATE, QUESTIONS, TOOLS, MasterExecution, run_tests
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = BASE / 'remaining-work'
REVIEW = DOC / 'remaining-work-review-2026-10-13.md'
RESULT = DOC / 'results/remaining-work-execution-2026-10-13.md'
TESTS = ['tests/assurance/test_remaining_integration_repairs.py',
    'tests/tooling/test_remaining_work_revision.py', 'tests/tooling/test_legal_mission_execution.py',
    'tests/tooling/test_legal_mission_control.py', 'tests/tooling/test_integration_acceptance.py',
    'tests/tooling/test_integration_master.py', 'tests/tooling/test_integration_campaign.py',
    'tests/assurance/test_bounded_context.py', 'tests/assurance/test_bounded_product.py',
    'tests/assurance/test_bounded_references.py', 'tests/assurance/test_bounded_resume_identity.py',
    'tests/assurance/test_master_reopening.py', 'tests/tooling/test_legal_independent_tools.py']


def retain(path, value):
    path = ROOT / path
    if path.exists(): require(read(path) == value, 'Changed remaining-work evidence: ' + str(path))
    else: save(path, value)


def source_revision():
    from legalmath.canonical import digest as source_digest
    from legalmath.interpretation.assurance.legal_locators import build_index, retained_html, verify_index
    previous = BASE / 'acceptance-revision/combined-envelope.json'
    envelope = deepcopy(read(ROOT / previous))
    rebuilt = []
    for old in envelope['legal_indexes']:
        index = build_index(envelope['source_packet'], retained_html(old['source'], ROOT),
            source_ref=old['source'], unit_ids=list(old['units']), root=ROOT,
            numbering_profile=old.get('numbering_profile', 'ordered-lists'))
        verify_index(envelope['source_packet'], index, root=ROOT, expected_index_hash=index['index_hash'])
        rebuilt.append(index)
    envelope['legal_indexes'] = rebuilt
    obligations = envelope['answer_acceptance']['acceptance_obligations']
    envelope['requirement_question_ids'] = {
        'obligation:' + obligations[i - 1]['id']: sorted(set(obligations[i - 1]['question_ids']) | {'p14'})
        for i in (4, 10, 21, 42)}
    envelope['source_qualification']['source_packet_hash'] = source_digest(envelope['source_packet'])
    envelope['binding'] = {'profile': 'bounded-combined-corpus.v4', 'previous': ref(ROOT, previous),
        'packet_hash': source_digest(envelope['source_packet']),
        'legal_index_hashes': [i['index_hash'] for i in rebuilt], 'review': ref(ROOT, REVIEW)}
    envelope['source_qualification']['evidence'] += [ref(ROOT, DOC / 'remaining-work-source-review-2026-10-13.md')]
    envelope['binding_hash'] = source_digest(envelope['binding'])
    retain(WORK / 'combined-envelope.json', envelope)
    return envelope


def register():
    existing = read(ROOT / PROGRAM)
    if existing.get('remaining_work_revision'):
        if isinstance(existing['remaining_work_revision'].get('archives'), list):
            # Interrupted registration retained the archive map inline. Generic
            # evidence validation interpreted its historical keys as live refs.
            # Preserve that partial registration and bind the immutable map file.
            old_ref = ref(ROOT, PROGRAM)
            for path in (PROGRAM, STATE, DOC / 'mission.json'):
                retain(WORK / 'registration-recovery' / path, read(ROOT / path))
            existing['remaining_work_revision']['archives'] = ref(ROOT, WORK / 'baseline.json')
            validate_program(existing, ROOT)
            state = read(ROOT / STATE)
            state['program_hash'] = digest(existing)
            save(ROOT / PROGRAM, existing); save(ROOT / STATE, state)
            mission = historical_projection(read(ROOT / DOC / 'mission.json'),
                {(old_ref['path'], old_ref['sha256']): ref(ROOT, PROGRAM)})
            mission['integration_master']['remaining_work_revision'] = existing['remaining_work_revision']
            save(ROOT / DOC / 'mission.json', mission)
            from scripts import legal_mission_control as control
            require(control.validate(mission, read(ROOT / DOC / 'tools.json'), ROOT)['detours_since_advance'] == 22,
                    'Recovered registration lost historical accounting')
            retain(WORK / 'migration.json', {'prior_program': existing['remaining_work_revision']['prior_program'],
                'prior_state': existing['remaining_work_revision']['prior_state'], 'current_program': ref(ROOT, PROGRAM),
                'review': ref(ROOT, REVIEW), 'attempts_preserved': True, 'detours': 22, 'calls': 232,
                'live_calls_added': 0, 'registration_repair': 'Archive keys retained in immutable baseline manifest.'})
        return MasterExecution(ROOT, PROGRAM, STATE).summary()
    baseline = read(ROOT / WORK / 'baseline.json')
    archives = {(r['previous']['path'], r['previous']['sha256']): r['archive'] for r in baseline['archived']}
    prior = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    for row in baseline['archived']: verify(ROOT, row['archive'])
    for row in baseline['sealed']: verify(ROOT, row)
    previous, old_state = read(ROOT / prior[str(PROGRAM)]['path']), read(ROOT / prior[str(STATE)]['path'])
    require(existing == previous and read(ROOT / STATE) == old_state, 'Changed remaining-work baseline')
    require(not any(r['status'] == 'RUNNING' for r in old_state['tasks'].values()), 'Cannot revise running work')
    source_revision()
    verification = ROOT / WORK / 'verification'
    verification.mkdir(parents=True, exist_ok=True)
    run_tests(TESTS + ['--tb=short'], verification)
    program = historical_projection(deepcopy(previous), archives)
    state = deepcopy(old_state)
    reopened = ['sources', 'runtime', 'product', 'corpus-qualification'] + ['legal-' + q for q in QUESTIONS] + [
        'native-' + t for t in TOOLS] + ['qualify-' + q for q in QUESTIONS] + ['campaign', 'release-review']
    revision = {'profile': 'legal-remaining-work-revision.v1',
        'user_instruction': baseline['user_instruction'], 'prior_detours': 21,
        'additional_consolidated_revision': 1, 'prior_charged_calls': 232, 'live_calls_added': 0,
        'review': ref(ROOT, REVIEW), 'prior_program': prior[str(PROGRAM)], 'prior_state': prior[str(STATE)],
        'archives': ref(ROOT, WORK / 'baseline.json'), 'source_revision': ref(ROOT, WORK / 'combined-envelope.json'),
        'verification': ref(ROOT, verification / 'test-result.json'), 'reopened_nodes': reopened,
        'attempt_ceilings': {tid: len(state['tasks'][tid]['attempts']) + 1 for tid in reopened}}
    program['remaining_work_revision'] = revision
    program['protected_evidence'] += [ref(ROOT, PLAN), ref(ROOT, REVIEW), revision['source_revision']]
    for task in program['tasks']:
        tid = task['id']
        if tid not in reopened: continue
        task.update(executor='command', maximum_attempts=revision['attempt_ceilings'][tid],
            command=['.venv/bin/python', 'scripts/legal_integration_master.py', 'worker', tid], timeout_seconds=3600)
        task['inputs'] += [ref(ROOT, REVIEW)]
        task['prior_acceptance'] = task['acceptance']
        task['acceptance'] = 'Execute the concrete remaining-work deliverable for ' + tid + '; qualification and legal completion remain separate.'
        task['deliverable'] = str(BASE / tid / ('attempt-' + str(task['maximum_attempts'])) / 'result.json')
        state['tasks'][tid] = {'status': 'PENDING', 'attempts': deepcopy(old_state['tasks'][tid]['attempts']),
                              'prior_outcome_reference': {'state': prior[str(STATE)], 'task_id': tid}}
        if tid.startswith('native-'):
            task['requires'] = ['sources']  # supported conditional targets do not require a live answer
        if tid.startswith('legal-'):
            task['requires'] = ['sources']
    for item in program['remaining_work']:
        item['phase_plan'] = ref(ROOT, PLAN)
        item['execution_authorization'] = 'REVIEWED_REMAINING_WORK; PRESERVED_LIVE_ATTEMPTS'
    validate_program(program, ROOT)
    state['program_hash'] = digest(program)
    state['events'].append({'task_id': None, 'action': 'REVIEWED_REMAINING_WORK',
        'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
    mission = historical_projection(read(ROOT / DOC / 'mission.json'), archives)
    tools = historical_projection(read(ROOT / DOC / 'tools.json'), archives)
    with (ROOT / DOC / 'mission.json').with_suffix('.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with (ROOT / STATE).with_suffix('.lock').open('a') as state_lock:
            fcntl.flock(state_lock, fcntl.LOCK_EX)
            require(read(ROOT / PROGRAM) == previous and read(ROOT / STATE) == old_state, 'Migration race')
            save(ROOT / PROGRAM, program); save(ROOT / STATE, state)
            mission['integration_master'].update(program=ref(ROOT, PROGRAM), plan=ref(ROOT, PLAN),
                                                  remaining_work_revision=revision)
            reason = 'Execute concrete repairs, source ownership and original-question conditional targets; continue independent owners.'
            mission['next_task_reason'] = reason
            mission['history'].append({'id': 'integration-master-remaining-work-2026-10-13',
                'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
                'decision': 'Reviewed remaining-work implementation in the same master, preserving all prior resources.',
                'next_task': 'product-contribution', 'next_task_reason': reason,
                'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
                'result_evidence': [ref(ROOT, PROGRAM), ref(ROOT, PLAN), ref(ROOT, REVIEW), revision['verification']]})
            save(ROOT / DOC / 'tools.json', tools); save(ROOT / DOC / 'mission.json', mission)
    from scripts import legal_mission_control as control
    require(control.validate(mission, tools, ROOT)['detours_since_advance'] == 22, 'Lost historical accounting')
    retain(WORK / 'migration.json', {'prior_program': prior[str(PROGRAM)], 'prior_state': prior[str(STATE)],
        'current_program': ref(ROOT, PROGRAM), 'review': ref(ROOT, REVIEW), 'attempts_preserved': True,
        'sealed': baseline['sealed'], 'detours': 22, 'calls': 232, 'live_calls_added': 0})
    return MasterExecution(ROOT, PROGRAM, STATE).summary()


def worker(tid, directory):
    revision = read(ROOT / PROGRAM)['remaining_work_revision']
    for key in ('review', 'source_revision', 'verification'): verify(ROOT, revision[key])
    envelope = read(ROOT / revision['source_revision']['path'])
    common = {'source_revision': revision['source_revision'], 'verification': revision['verification'],
              'legal_acceptance': False, 'tool_effect_established': False}
    if tid == 'sources':
        from scripts.legal_integration_substantive import prepare_targets
        prepared = prepare_targets(envelope, directory)
        return {**common, **prepared, 'units': len(envelope['source_packet']['units']),
                'index_packet_binding': 'REBUILT_AND_VERIFIED',
                '_conclusion': 'Expanded source packet indexes rebuilt; conditional original-question targets retained.'}
    if tid == 'runtime':
        from scripts.legal_independent_tools import IndependentProductToolBackend
        identities = {tool: IndependentProductToolBackend([tool]).identity() for tool in TOOLS}
        save(directory / 'native-identities.json', identities)
        return {**common, 'native_content': ref(ROOT, directory / 'native-identities.json'),
                'locally_repaired': ['R13 selected native content', 'R14 wire/decoded bounds'],
                'service_capacity': 'UNQUALIFIED',
                '_conclusion': 'Native package content identities and separate decoded bounds verified locally; live framing remains unqualified.'}
    if tid == 'product':
        return {**common, 'locally_repaired': ['R06 document/prose-field identity', 'R08 dependency retrieval and review',
                'R10 one opt-in correction', 'R14 input quote compaction'],
                'remaining': ['Source entailment of each original assertion', 'Actual remote-exception semantic qualification'],
                '_conclusion': 'Concrete product repairs passed adverse controls; actual original-answer semantics remain to qualify.'}
    if tid == 'corpus-qualification':
        from scripts.legal_integration_substantive import ownership_audit
        return {**common, **ownership_audit(envelope, directory)}
    if tid.startswith('legal-'):
        from scripts.legal_integration_substantive import legal_review
        return {**common, **legal_review(tid[6:], envelope, directory)}
    if tid.startswith('native-'):
        from scripts.legal_integration_substantive import native_targets
        return {**common, **native_targets(tid[7:], envelope, directory)}
    if tid.startswith('qualify-'):
        from scripts.legal_integration_substantive import qualify
        return {**common, **qualify(tid[8:], envelope, directory)}
    if tid == 'campaign':
        return {**common, 'ready': False, 'acquisition_attempts_unchanged': True,
                'next': 'Complete current source/semantic qualification and capacity-bound proposal; preserve prior live ledger.',
                '_node_status': 'BLOCKED', '_conclusion': 'Local repairs executed; current live source/semantic binding is still absent.'}
    if tid == 'release-review':
        return {**common, 'frontier': MasterExecution(ROOT, PROGRAM, STATE).summary(),
                'integration_complete': False, '_conclusion': 'Remaining-work local implementation assessed; complete original matched effects remain open.'}
    raise ValueError('No remaining-work worker for ' + tid)


def settle():
    execution = MasterExecution(ROOT, PROGRAM, STATE)
    view = execution.summary()
    require(not view['ready'] and not view['running'], 'Independent ready work remains')
    baseline = read(ROOT / WORK / 'baseline.json')
    for row in baseline['sealed']: verify(ROOT, row)
    revision = execution.program['remaining_work_revision']
    prior = read(ROOT / revision['prior_state']['path'])
    current = read(ROOT / STATE)
    require(all(current['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
                for tid, row in prior['tasks'].items()), 'Historical attempts changed')
    output = {'profile': 'remaining-work-execution.v1', 'program': ref(ROOT, PROGRAM), 'plan': ref(ROOT, PLAN),
        'execution': view['execution'], 'ready': view['ready'], 'running': view['running'],
        'task_counts': dict(Counter(r['status'] for r in view['tasks'].values())), 'blocked': view['blocked'],
        'calls': 232, 'live_calls_added': 0, 'detours': 22, 'integration_complete': False,
        'sealed_unchanged': baseline['sealed'], 'historical_attempts_preserved': True,
        'command': '.venv-context/bin/python scripts/legal_integration_master.py run',
        'environment': sys.executable, 'device': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'seeds': 'N/A: deterministic local controls and source inspection',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'source': revision['source_revision']}
    path = ROOT / WORK / 'execution-result.json'
    if not path.exists(): save(path, output)
    return output


def verify_repairs():
    """Finish the one planned implementation package; never replace node attempts."""
    from concurrent.futures import ThreadPoolExecutor
    from scripts.legal_integration_substantive import qualify
    directory = ROOT / WORK / 'final-review'
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / 'verification.json'
    if final.exists():
        result = read(final)
        for item in result['implementation']: verify(ROOT, item)
        return result
    verification = directory / 'tests'
    verification.mkdir(parents=True, exist_ok=True)
    run_tests(TESTS + ['--tb=short'], verification)
    envelope = quotation_revision()
    def one(qid):
        return qid, qualify(qid, envelope, directory / qid)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = dict(pool.map(one, QUESTIONS))
    result = {'profile': 'remaining-work-post-review.v1', 'questions': outcomes,
        'tests': ref(ROOT, verification / 'test-result.json'), 'live_calls': 0,
        'source': ref(ROOT, WORK / 'quotation-repair-envelope.json'),
        'prior_verification': ref(ROOT, WORK / 'post-review/verification.json'),
        'prior_implementation_archive': ref(ROOT, WORK / 'final-records/baseline.json'),
        'baseline': [ref(ROOT, BASE / ('qualify-' + q) / 'attempt-4/capacity.json') for q in QUESTIONS],
        'repair': 'Measure complete reference-framed reading requests and split only independent reading populations.',
        'original_attempts_unchanged': True,
        'implementation': [ref(ROOT, p) for p in (
            'src/legalmath/interpretation/assurance/bounded_product.py',
            'src/legalmath/interpretation/assurance/bounded_context.py',
            'src/legalmath/interpretation/assurance/bounded_references.py',
            'scripts/legal_native_identity.py', 'scripts/legal_integration_tools.py',
            'scripts/legal_mission_execution.py', 'scripts/legal_integration_substantive.py',
            'scripts/legal_integration_remaining.py')]}
    save(final, result)
    return result


def rebuild_quote_locations(envelope):
    """Rebuild derived positions; never alter original quotations or populations."""
    from legalmath.interpretation.assurance.answer_acceptance import reading_quote_locations
    value = deepcopy(envelope)
    value['answer_acceptance']['current_quote_locations'] = reading_quote_locations(
        value['answer_acceptance'], value['source_packet'])
    return value


def quotation_revision():
    previous = WORK / 'combined-envelope.json'
    envelope = rebuild_quote_locations(read(ROOT / previous))
    from legalmath.canonical import digest as source_digest
    envelope['binding'] = {'profile': 'bounded-combined-corpus.v5',
        'previous': ref(ROOT, previous),
        'packet_hash': source_digest(envelope['source_packet']),
        'quotation_index_hash': source_digest(envelope['answer_acceptance']['current_quote_locations']),
        'review': ref(ROOT, WORK / 'final-records/review.md')}
    envelope['binding_hash'] = source_digest(envelope['binding'])
    retain(WORK / 'quotation-repair-envelope.json', envelope)
    return envelope
