"""One bounded instruction correction in the existing integration master.

No new global allowance, replacement reserve, task population or deadline.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_integration_master import (
    ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, TOKENIZER, MasterExecution,
)
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_qualification_continuation import projected_archives
from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-15/account-instructions')
PREVIOUS = WORK.parent / 'qualification-continuation'
REVIEW = WORK / 'review.md'
KEY = 'account_instruction_repair'
USER = 'refresh the master program, continue the execution'
REOPEN = ('current-binding', 'account-qualification', 'campaign', 'continuation-review',
    *('acquire-' + q for q in QUESTIONS))
POINTERS = ('review', 'baseline', 'local_review', 'local_validation', 'qualification_input', 'diagnosis')


def replay_request(retained):
    """Restore record column order from the actual historical wire, for replay only.

    Canonical JSON sorts object keys; the historical encoder used their insertion
    order to choose table columns. Keep the encoder and all sealed bytes unchanged.
    Full reconstruction below refuses any other difference.
    """
    from legalmath.interpretation.assurance.bounded_references import prepare
    request = deepcopy(retained['original_request'])
    columns = retained['request'].get('account_record_table', {}).get('columns', [])
    require(len(columns) == len(set(columns)), 'Duplicate retained account columns')
    if columns:
        for index, row in enumerate(request['records']):
            require(set(columns) <= set(row), 'Retained column missing from source record')
            request['records'][index] = {**{k: v for k, v in row.items() if k not in columns},
                **{k: row[k] for k in columns}}
    require(prepare(request, retained['original_schema']) == retained,
        'Historical account wire reconstruction differs')
    return request


def corrected_request(retained):
    from legalmath.interpretation.assurance.bounded_references import prepare
    from legalmath.interpretation.assurance.phased import account_instructions
    request = replay_request(retained)
    request['account_instruction_profile'] = account_instructions.PROFILE
    changed = prepare(request, retained['original_schema'])
    require(changed['schema'] == retained['schema'], 'Instruction correction changed schema')
    old_wire, new_wire = deepcopy(retained['request']), deepcopy(changed['request'])
    for value in (old_wire, new_wire):
        for field in ('instructions', 'response_reference_instructions', 'account_instruction_profile'):
            value.pop(field, None)
    require(old_wire == new_wire, 'Instruction correction changed source, assignment or encoding')
    return request


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in POINTERS]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        if node['id'] in REOPEN:
            number = len(before['tasks'][node['id']]['attempts']) + 1
            node.update(maximum_attempts=number,
                deliverable=str(BASE / node['id'] / f'attempt-{number}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
        if node['id'] == 'account-qualification':
            node['acceptance'] = ('One actual failed two-child account with schema-specific instructions '
                'passes strict wire schema, considered coverage and typed citation checks; no legal promotion.')
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-account-instruction-repair.v1'
        and revision['prior_detours'] == 40 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['qualification_logical_calls'] == 1
        and revision['additional_transport_replacements'] == 0
        and revision['service_recovery_policy'] == SERVICE_SINGLE_DISPATCH_POLICY,
        'Unreviewed account instruction repair')
    for key in (*POINTERS, 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('qualification_continuation') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled instruction baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2129, 'Lost prior charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archive bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, projected_archives(baseline))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Instruction repair changed unrelated graph or resources')
    local, validation = (read(root / revision[k]['path']) for k in ('local_review', 'local_validation'))
    require(local['verdict'] == 'PASS' and local['provider_calls'] == validation['provider_calls'] == 0
        and validation['exact_input_preservation'] and validation['legacy_wire_replays'] == 19
        and validation['malformed_responses_rejected'] == 7
        and validation['over_limit_requests'] == 0, 'Incomplete local instruction validation')
    for pointer in local['evidence'] + validation['evidence']:
        verify(root, pointer)
    require(set(revision['recoveries']) == set(QUESTIONS), 'Lost original question')
    for q, pointer in revision['recoveries'].items():
        verify(root, pointer)
        expected = 6 if q in ('p14', 'gatecoin') else 5
        require(len(before['tasks']['acquire-' + q]['attempts']) == expected
            and next(n for n in program['tasks'] if n['id'] == 'acquire-' + q)['maximum_attempts'] == expected + 1,
            'Unexpected acquisition allowance')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def registration_candidate():
    baseline = read(ROOT / WORK / 'baseline.json')
    refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / refs[str(PROGRAM)]['path']), read(ROOT / refs[str(STATE)]['path'])
    revision = {'profile': 'integration-account-instruction-repair.v1', 'prior_detours': 40,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': USER, 'review': ref(ROOT, REVIEW),
        'baseline': ref(ROOT, WORK / 'baseline.json'), 'local_review': ref(ROOT, WORK / 'local-review.json'),
        'local_validation': ref(ROOT, WORK / 'local-validation.json'),
        'qualification_input': ref(ROOT, WORK / 'qualification-input.json'),
        'diagnosis': ref(ROOT, WORK / 'diagnosis.json'),
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
        'reopened_nodes': list(REOPEN), 'qualification_logical_calls': 1,
        'additional_transport_replacements': 0, 'service_recovery_policy': SERVICE_SINGLE_DISPATCH_POLICY,
        'recoveries': {q: ref(ROOT, WORK / ('recovery-' + q + '.json')) for q in QUESTIONS}}
    program = expected_program(historical_projection(old, projected_archives(baseline)), before, revision, ROOT)
    validate_program(program, ROOT)
    return program, before, revision


def validate_staged_mission(root, stage, mission):
    """Validate actual staged bytes with only the prospective program path mapped.

    No check is disabled. All other source/evidence paths retain ordinary reads;
    the summary validates the staged program and state with the real scheduler.
    This scope runs serially under the registration locks and restores adapters.
    """
    from unittest.mock import patch
    from scripts import legal_mission_control as control, legal_integration_master as master
    staged = MasterExecution(root, stage / 'program.json', stage / 'state.json')
    summary = staged.summary()
    original_safe = control.safe_path
    def prospective_path(base, name):
        actual = original_safe(base, name)
        return root / stage / 'program.json' if actual == root / PROGRAM else actual
    with patch.object(control, 'safe_path', prospective_path), patch.object(master, 'summary', lambda _: summary):
        checked = control.validate(mission, read(root / DOC / 'tools.json'), root)
    require(checked['detours_since_advance'] == 41, 'Candidate detour reconciliation differs')
    return {'verdict': 'PASS', 'detours': 41, 'ready': summary['ready'],
        'program': ref(root, stage / 'program.json'), 'state': ref(root, stage / 'state.json')}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        for path in (DOC / 'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT / path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX)
        if (ROOT / journal).exists():
            if read(ROOT / journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            return {'registered': True, 'resumed': True}
        baseline = read(ROOT / WORK / 'baseline.json')
        refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json', BASE / 'live-calls.json'):
            require(ref(ROOT, path)['sha256'] == refs[str(path)]['sha256'], 'Baseline changed: ' + str(path))
        program, state, revision = registration_candidate()
        for tid in REOPEN:
            row = state['tasks'][tid]
            row.update(status='PENDING', reason='Reviewed account instructions; preserve spent attempts and failures')
            row.pop('result', None)
            for key in ('dispatch_status', 'prerequisite_evidence', 'shared_scope'):
                row.pop(key, None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_ACCOUNT_INSTRUCTION_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projected_archives(baseline, mission=True))
        stage = WORK / 'registration-stage'
        save(ROOT / stage / 'program.json', program); save(ROOT / stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']; master.update(program=pointer, plan=ref(ROOT, PLAN))
        for key, value in program.items():
            if (key in master or key == KEY) and isinstance(value, dict) and 'prior_state' in value and value.get('profile'):
                require(key == KEY or master[key].get('profile') == value['profile'], 'Historical registration differs')
                master[key] = deepcopy(value)
        reason = ('Qualify the corrected instructions on one failed actual account, then continue independent '
            'original acquisitions, answers and tools; reconcile failures without resetting resources.')
        mission['history'].append({'id': 'integration-master-account-instruction-repair-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed consolidated detour 41 for reproduced instruction/schema contradiction; no new global allowance.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['local_validation'], revision['local_review']]})
        mission['next_task_reason'] = reason; save(ROOT / stage / 'mission.json', mission)
        save(ROOT / WORK / 'registration-check.json', validate_staged_mission(ROOT, stage, mission))
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 41, 'reopened_nodes': list(REOPEN)}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM); revision = program[KEY]
    prior = read(ROOT / revision['prior_binding']['path'])
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    grant = read(ROOT / BASE / 'live-grant.json')
    previous_scope = prior['phase_service_scope']; service_dir = Path(previous_scope['path']).parent
    previous_circuit = ref(ROOT, service_dir / 'service-circuit.json')
    previous_replacements = ref(ROOT, service_dir / 'service-recovery.json')
    circuit, replacements = read(ROOT / previous_circuit['path']), read(ROOT / previous_replacements['path'])
    require(circuit['open'] and len(replacements['charges']) == replacements['maximum'] == 48,
        'Service settlement differs from reviewed circuit')
    scope_dir = WORK / 'live/service'
    require(not (ROOT / scope_dir / 'scope.json').exists(), 'Service scope cannot reset on resume')
    scope = {'profile': 'reviewed-shared-phase-service.v1', 'grant_hash': digest(grant),
        'review': revision['review'], 'prior_scope': previous_scope, 'prior_circuit': previous_circuit,
        'prior_replacements': previous_replacements, 'additional_replacements': 0,
        'requalification': 'One actual corrected account; first terminal service failure defers untouched owners.'}
    save(ROOT / scope_dir / 'scope.json', scope); scope_ref = ref(ROOT, scope_dir / 'scope.json')
    save(ROOT / scope_dir / 'service-circuit.json', {'stage_hash': scope_ref['sha256'],
        'consecutive_failures': 0, 'failed_slots': [], 'open': False, 'prior_circuit': previous_circuit})
    save(ROOT / scope_dir / 'service-recovery.json', {**replacements,
        'profile': SERVICE_SINGLE_DISPATCH_POLICY['profile'], 'stage_hash': scope_ref['sha256'],
        'prior_replacements': previous_replacements})
    binding = deepcopy(prior); binding.pop('phase_service_predecessor', None)
    save(directory / 'ledger-before.json', read(ROOT / BASE / 'live-calls.json'))
    binding.update(user_instruction=USER, review=revision['review'], predecessor=revision['prior_binding'],
        ledger_before=ref(ROOT, directory / 'ledger-before.json'), program=ref(ROOT, PROGRAM),
        phase_service_scope=scope_ref, service_recovery_policy=SERVICE_SINGLE_DISPATCH_POLICY,
        preflight_stage_maximum=1)
    binding['bindings'] = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in sorted((ROOT / 'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in (PROGRAM, PLAN, REVIEW,
        Path(program['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in POINTERS]
    binding['bindings'] += list(revision['recoveries'].values()) + [scope_ref, previous_scope, previous_circuit, previous_replacements]
    case = read(ROOT / revision['qualification_input']['path'])
    binding['bindings'] += [case[k] for k in ('request', 'schema', 'envelope', 'prior_binding')]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'additional_replacements': 0,
        '_conclusion': 'Schema-specific account instructions bound; one actual qualification and original recovery under unchanged global limits.'}


def qualify_accounts(service):
    from scripts.legal_integration_phased_live import phase_admit
    from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
    from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_instructions
    from legalmath.interpretation.assurance.phased.product import PhasedProduct
    revision = read(ROOT / PROGRAM)[KEY]
    case = read(ROOT / revision['qualification_input']['path'])
    for key in ('request', 'schema', 'envelope', 'prior_binding'): verify(ROOT, case[key])
    product = PhasedProduct(ROOT, ROOT / WORK / 'live/account-qualification', service,
        read(ROOT / case['envelope']['path']), tokenizer(ROOT / TOKENIZER), limits=Limits(), maximum_calls=1,
        phase_admit=phase_admit('account-instruction-qualification'),
        phase_identity=ref(ROOT, BASE / 'current-binding.json')['sha256'],
        requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_instruction_profile=account_instructions.PROFILE)
    retained = read(ROOT / case['prior_binding']['path'])
    request = corrected_request(retained)
    schema = read(ROOT / case['schema']['path'])
    require(request == read(ROOT / case['request']['path']) and schema == retained['original_schema'],
        'Qualification assignment differs from reviewed failed account')
    require(product.dispatch.measure(request, schema) == case['measurement'], 'Qualification measurement changed')
    def check(value):
        account_contract.validate(value, product, request['records'])
        require(len(value['considered']) == len(set(value['considered']))
            and set(value['considered']) == set(request['required_considered']), 'Lost actual account assignment')
    phase = product.run_phase('account-protocol', [{'key': 'account-protocol', 'request': request,
        'schema': schema, 'validate': check}])
    result = phase['results'][0]['result'] if phase['results'] else phase['resource_refusal']
    passed = result['status'] == 'VALIDATED'
    path = WORK / 'live/account-qualification/result.json'
    save(ROOT / path, {'qualified': passed, 'complete': True, 'result': result,
        'logical_call_ceiling': 1, 'original_failed_slot': 2119,
        'scope': 'Actual account interface qualification; not legal acceptance or tool effect.'})
    return {'qualification': ref(ROOT, path), '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': ('Corrected instructions passed the actual account interface; continue original acquisitions.' if passed
            else 'Corrected actual account failed; retain exact failure and reconcile independent local work.')}


def verification(directory=None):
    from scripts.legal_integration_acceptance import evaluation_summary
    program = read(ROOT / PROGRAM); validate_program(program, ROOT); revision = program[KEY]
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, prior = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    evaluations = evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT)
    result = {'profile': 'account-instruction-repair-verification.v1', 'calls': len(ledger['calls']),
        'historical_calls': 41, 'detours': 41, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'original_questions': list(QUESTIONS), 'original_obligations': 46, 'original_readings': 35,
        'integration_complete': False, 'tools_fully_evaluated': evaluations['selected_tools_fully_evaluated'],
        'remaining': ['Complete source-grounded original accounts and answers',
            'Matched actual answer effects of six selected tools', 'Dated applicability and later treatment'],
        '_conclusion': 'Instruction repair accounting verified; original legal answers and matched effects govern acceptance.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result


def campaign(directory):
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    owners = ('current-binding', 'semantic-preflight', 'account-qualification')
    statuses = {tid: view['tasks'][tid]['status'] for tid in owners}
    passed = all(s == 'SUCCEEDED' for s in statuses.values())
    ledger, grant = read(ROOT / BASE / 'live-calls.json'), read(ROOT / BASE / 'live-grant.json')
    save(directory / 'campaign-reconciliation.json', {'prerequisites': statuses,
        'acquisitions': {q: {key: view['tasks']['acquire-' + q][key]
            for key in ('status', 'attempts_used', 'maximum_attempts')} for q in QUESTIONS},
        'charges': len(ledger['calls']), 'ceiling': grant['maximum_calls'],
        'deadline_utc': grant['deadline_utc'], 'account_protocol_ready': passed,
        'complete_integration': False,
        'next': 'Drain eligible original acquisitions, answers and comparisons; retain local/legal residuals.'})
    return {'campaign': ref(ROOT, directory / 'campaign-reconciliation.json'),
        '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': 'Campaign prerequisites reconciled; ' +
            ('continue eligible original product work.' if passed else 'failed qualification blocks its consumers.')}
