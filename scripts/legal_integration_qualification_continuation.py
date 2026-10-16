"""Reuse exact successful controls and continue the existing integration master.

This amendment adds no acquisition attempts, calls, deadline or replacements.
Retained responses are revalidated locally; only the missing control dispatches.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, TOKENIZER, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY
from legalmath.interpretation.assurance.bounded_references import prepare as prepare_references, resolve
from legalmath.interpretation.assurance.phased import account_contract, account_input
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from scripts.legal_integration_account_controls import check_account

WORK = Path('artifacts/legal-mission-control/2026-10-15/qualification-continuation')
LOSSLESS = Path('artifacts/legal-mission-control/2026-10-15/lossless-recovery')
RETRY = Path('artifacts/legal-mission-control/2026-10-15/sol-retry')
REVIEW = WORK / 'review.md'
KEY = 'qualification_continuation'
USER = 'refresh the master program, continue the execution'
REOPEN = ('current-binding', 'account-qualification', 'corpus-qualification', 'campaign', 'continuation-review')
REUSE = (
    ('largest-actual', 2113, LOSSLESS / 'live/account-qualification/largest-actual',
     BASE / 'provider-evidence/2113-f6841b987a380aa7', None),
    ('near-cap-exception', 2115, RETRY / 'product',
     BASE / 'provider-evidence/2115-e96c422a1ede9cd7', '__main__.ExactRetryProvider'),
)


def projected_archives(baseline, *, mission=False):
    paths = set(baseline['projected_paths'])
    if mission:
        paths.add(str(PROGRAM))
    return archives([r for r in baseline['archived']
        if r['previous']['path'] in paths], mission=mission)


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in
        ('review', 'baseline', 'local_review', 'qualification_inputs', 'retained_replay')]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        tid = node['id']
        if tid in REOPEN:
            number = len(before['tasks'][tid]['attempts']) + 1
            node.update(maximum_attempts=number,
                deliverable=str(BASE / tid / f'attempt-{number}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
        if tid == 'campaign':
            node['after'] = list(dict.fromkeys(node['after'] +
                ['current-binding', 'semantic-preflight', 'account-qualification']))
        if tid == 'continuation-review':
            node['after'] = list(dict.fromkeys(node['after'] + ['corpus-qualification', 'campaign'] +
                [n['id'] for n in value['tasks'] if n['id'].startswith(('baseline-', 'tool-', 'compare-'))]))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-qualification-continuation.v1'
        and revision['prior_detours'] == 39 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['qualification_logical_calls'] == 1
        and revision['reused_slots'] == [2113, 2115]
        and revision['additional_transport_replacements'] == 0
        and revision['service_recovery_policy'] == SERVICE_SINGLE_DISPATCH_POLICY,
        'Unreviewed qualification continuation')
    for key in ('review', 'baseline', 'local_review', 'qualification_inputs', 'retained_replay',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('lossless_account_repair') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled continuation baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2115, 'Lost baseline charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archived bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, projected_archives(baseline))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Continuation changed unrelated graph or limits')
    local = read(root / revision['local_review']['path'])
    replay = read(root / revision['retained_replay']['path'])
    require(local['verdict'] == 'PASS' and local['provider_calls'] == 0
        and replay['valid'] and replay['provider_calls'] == 0
        and [r['slot'] for r in replay['rows']] == [2113, 2115], 'Unreviewed local continuation')
    for pointer in local['evidence'] + replay['evidence']:
        verify(root, pointer)
    for q in QUESTIONS:
        require(len(before['tasks']['acquire-' + q]['attempts']) == 5
            and next(n for n in program['tasks'] if n['id'] == 'acquire-' + q)['maximum_attempts'] == 6,
            'Acquisition must retain five spent and one already registered attempt')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def verify_receipt(root, directory, slot, request, schema):
    """Check retained bytes as well as receipt fields; no provider methods."""
    manifest = read(root / directory / 'manifest.json')
    require(manifest['allowance_slot'] == slot and manifest['complete_output_present']
        and manifest['request_hash'] == digest(request), 'Wrong retained provider receipt')
    require({'request.json', 'schema.json', 'result.json'} <= set(manifest['files']), 'Incomplete receipt')
    evidence = [ref(root, directory / 'manifest.json')]
    for name, row in manifest['files'].items():
        require(Path(name).name == name, 'Invalid receipt member')
        data = (root / directory / name).read_bytes()
        require(len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['retained_sha256'],
            'Retained provider bytes changed: ' + name)
        evidence.append(ref(root, directory / name))
    require(read(root / directory / 'request.json') == request
        and read(root / directory / 'schema.json') == schema, 'Changed retained wire request/schema')
    return read(root / directory / 'result.json'), evidence


def replay_controls():
    from jsonschema import validate
    from scripts.legal_integration_campaign import provider
    inputs = read(ROOT / LOSSLESS / 'qualification-inputs.json')
    service = provider()  # Constructor and measure are local; never check/complete/fork here.
    require(service.routing['model'] == 'gpt-6.1-sol', 'Retained model changed')
    rows, evidence = [], [ref(ROOT, LOSSLESS / 'qualification-inputs.json')]
    ledger = read(ROOT / BASE / 'live-calls.json')
    for name, slot, directory, receipt_dir, implementation in REUSE:
        case = next(c for c in inputs['cases'] if c['name'] == name)
        for key in ('request', 'envelope'):
            verify(ROOT, case[key]); evidence.append(case[key])
        product = BoundedProduct(ROOT, ROOT / WORK / 'replays' / name, service,
            read(ROOT / case['envelope']['path']), tokenizer(ROOT / TOKENIZER), limits=Limits(),
            maximum_calls=1, requirement_account_profile=account_contract.PROFILE,
            requirement_account_input_profile=account_input.PROFILE)
        request, schema = read(ROOT / case['request']['path']), account_contract.provider_schema()
        prepared = prepare_references(request, schema)
        call = directory / 'calls/account-protocol'
        require(read(ROOT / call / 'request.json') == request
            and read(ROOT / call / 'schema.json') == schema
            and read(ROOT / call / 'reference-binding.json') == prepared, 'Retained request identity changed')
        dispatch = read(ROOT / directory / 'calls/dispatch.json')
        record = dispatch['calls']['account-protocol']
        binding = deepcopy(product.dispatch.provider_binding)
        if implementation:
            binding['implementation'] = implementation
        require(record['identity'] == digest({'request': request, 'schema': schema, 'provider_binding': binding})
            and dispatch['input_hash'] == product.route.input_hash and dispatch['maximum_calls'] == 1,
            'Changed dispatch identity')
        measurement = product.dispatch.measure(request, schema)
        require(measurement == case['measurement'] == record['measurement'], 'Changed retained measurement')
        wire, receipt_evidence = verify_receipt(ROOT, receipt_dir, slot, prepared['request'], prepared['schema'])
        evidence += receipt_evidence
        response = read(ROOT / call / 'wire-response.json')
        result = read(ROOT / call / 'result.json')
        raw = read(ROOT / call / 'raw.json')
        require(response['value'] == wire and digest(result) == record['result_hash']
            and result['status'] == record['status'] == 'VALIDATED'
            and result['request_hash'] == digest(request), 'Changed successful response')
        value = resolve(wire, prepared, maximum_bytes=product.route.limits.decoded_output_bytes)
        validate(value, schema)
        require(value == result['value'] == raw['value'] and raw['provenance'] == result['provenance'],
            'Changed decoded response')
        provenance = result['provenance']
        require(provenance == {**response['provenance'], 'reference_protocol': prepared['protocol'],
                'reference_binding': prepared['binding']}
            and provenance['allowance_slot'] == slot and provenance['application_replacements'] == 0
            and provenance['model'] == service.routing['model']
            and provenance['provider_route_hash'] == digest(service.routing)
            and provenance['request_hash'] == digest(prepared['request']) == ledger['calls'][slot-1]['request_hash'],
            'Changed successful provenance')
        limits = product.route.limits
        require(len(canonical(wire)) <= limits.output_bytes
            and len(product.route.encode(canonical(wire).decode())) <= limits.output_tokens
            and len(canonical(value)) <= limits.decoded_output_bytes
            and len(product.route.encode(canonical(value).decode())) <= limits.decoded_output_tokens,
            'Retained output exceeds bounds')
        check_account(product, request, value, case)
        evidence += [ref(ROOT, call / f) for f in
            ('request.json', 'schema.json', 'reference-binding.json', 'wire-response.json', 'raw.json', 'result.json')]
        evidence.append(ref(ROOT, directory / 'calls/dispatch.json'))
        rows.append({'name': name, 'slot': slot, 'passed': True, 'measurement': measurement,
            'request': case['request'], 'result': ref(ROOT, call / 'result.json'), 'reused': True})
    result = {'profile': 'exact-retained-account-replay.v1', 'valid': True,
        'provider_calls': 0, 'rows': rows, 'evidence': evidence,
        'failed_slot_preserved': 2114, 'scope': 'Exact engineering revalidation; no fresh model or legal evidence.'}
    save(ROOT / WORK / 'retained-replay.json', result)
    return result


def registration_candidate():
    baseline = read(ROOT / WORK / 'baseline.json')
    refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / refs[str(PROGRAM)]['path']), read(ROOT / refs[str(STATE)]['path'])
    revision = {'profile': 'integration-qualification-continuation.v1', 'prior_detours': 39,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': USER, 'review': ref(ROOT, REVIEW), 'baseline': ref(ROOT, WORK / 'baseline.json'),
        'local_review': ref(ROOT, WORK / 'local-review.json'),
        'qualification_inputs': ref(ROOT, LOSSLESS / 'qualification-inputs.json'),
        'retained_replay': ref(ROOT, WORK / 'retained-replay.json'),
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
        'reopened_nodes': list(REOPEN), 'qualification_logical_calls': 1, 'reused_slots': [2113, 2115],
        'additional_transport_replacements': 0, 'service_recovery_policy': SERVICE_SINGLE_DISPATCH_POLICY}
    program = expected_program(historical_projection(old, projected_archives(baseline)), before, revision, ROOT)
    validate_program(program, ROOT)
    return program, before, revision


def synchronize_revisions(master, program):
    for key, value in program.items():
        if (key in master or key == KEY) and isinstance(value, dict) and 'prior_state' in value and value.get('profile'):
            require(key == KEY or master[key].get('profile') == value['profile'],
                'Incompatible historical registration: ' + key)
            master[key] = deepcopy(value)


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
            state['tasks'][tid].update(status='PENDING', reason='Reviewed qualification continuation; preserve all prior attempts')
            state['tasks'][tid].pop('result', None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_QUALIFICATION_CONTINUATION', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projected_archives(baseline, mission=True))
        stage = ROOT / WORK / 'registration-stage'
        save(stage / 'program.json', program); save(stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']; master.update(program=pointer, plan=ref(ROOT, PLAN))
        # Keep every nested historical registration consistent with its projected program.
        synchronize_revisions(master, program)
        reason = 'Reuse exact passing Sol controls, dispatch only the missing-authority control, reconcile sources independently and drain original answers/tools under unchanged limits.'
        mission['history'].append({'id': 'integration-master-qualification-continuation-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed consolidated detour 40; no added acquisition attempts, calls, deadlines or replacements.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['local_review'], revision['retained_replay']]})
        mission['next_task_reason'] = reason; save(stage / 'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 40, 'reopened_nodes': list(REOPEN)}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM); revision = program[KEY]
    prior = read(ROOT / revision['prior_binding']['path'])
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    replay = replay_controls()
    require(ref(ROOT, WORK / 'retained-replay.json') == revision['retained_replay'], 'Control replay changed')
    grant = read(ROOT / BASE / 'live-grant.json')
    previous_scope = prior['phase_service_scope']; service_dir = Path(previous_scope['path']).parent
    previous_circuit = ref(ROOT, service_dir / 'service-circuit.json')
    previous_replacements = ref(ROOT, service_dir / 'service-recovery.json')
    circuit, replacements = read(ROOT / previous_circuit['path']), read(ROOT / previous_replacements['path'])
    require(circuit['open'] and len(replacements['charges']) == replacements['maximum'] == 48,
        'Service settlement differs from reviewed open circuit')
    scope_dir = WORK / 'live/service'
    require(not (ROOT / scope_dir / 'scope.json').exists(), 'Service scope must not reset on resume')
    scope = {'profile': 'reviewed-shared-phase-service.v1', 'grant_hash': digest(grant),
        'review': revision['review'], 'prior_scope': previous_scope, 'prior_circuit': previous_circuit,
        'prior_replacements': previous_replacements, 'successful_controls': revision['retained_replay'],
        'additional_replacements': 0, 'requalification': 'One missing control; first terminal service failure defers live consumers.'}
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
    binding['bindings'] += [revision[k] for k in ('baseline', 'local_review', 'qualification_inputs', 'retained_replay')]
    binding['bindings'] += replay['evidence'] + [scope_ref, previous_scope, previous_circuit, previous_replacements]
    prior_archives = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        prior_archives[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(prior_archives.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'retained_controls': revision['retained_replay'],
        'additional_replacements': 0, '_conclusion': 'Exact passing Sol controls retained; one missing-authority control admitted under unchanged authority.'}


def qualify_accounts(service):
    from scripts.legal_integration_phased_live import phase_admit
    revision = read(ROOT / PROGRAM)[KEY]
    verify(ROOT, revision['retained_replay'])
    replay = replay_controls()
    require(ref(ROOT, WORK / 'retained-replay.json') == revision['retained_replay'], 'Retained replay changed')
    inputs = read(ROOT / revision['qualification_inputs']['path'])
    case = next(c for c in inputs['cases'] if c['name'] == 'near-cap-missing')
    for key in ('request', 'envelope'):
        verify(ROOT, case[key])
    product = PhasedProduct(ROOT, ROOT / WORK / 'live/account-qualification/near-cap-missing', service,
        read(ROOT / case['envelope']['path']), tokenizer(ROOT / TOKENIZER), limits=Limits(), maximum_calls=1,
        phase_admit=phase_admit('account-qualification-near-cap-missing'),
        phase_identity=ref(ROOT, BASE / 'current-binding.json')['sha256'],
        requirement_account_profile=account_contract.PROFILE, requirement_account_input_profile=account_input.PROFILE)
    request, schema = read(ROOT / case['request']['path']), account_contract.provider_schema()
    measurement = product.dispatch.measure(request, schema)
    require(measurement == case['measurement'], 'Missing-control measurement changed')
    phase = product.run_phase('account-protocol', [{'key': 'account-protocol', 'request': request,
        'schema': schema, 'validate': lambda value: check_account(product, request, value, case)}])
    result = phase['results'][0]['result'] if phase['results'] else phase['resource_refusal']
    rows = replay['rows'] + [{'name': case['name'], 'result': result, 'measurement': measurement,
        'passed': result['status'] == 'VALIDATED', 'reused': False}]
    passed = all(r['passed'] for r in rows)
    save(ROOT / WORK / 'live/account-qualification/result.json', {'rows': rows, 'qualified': passed,
        'complete': True, 'logical_call_ceiling': 1, 'reused_slots': [2113, 2115],
        'scope': 'Named account qualification only; original legal answers and tool effects remain required.'})
    return {'qualification': ref(ROOT, WORK / 'live/account-qualification/result.json'),
        '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': 'Account protocol ' + ('qualified using two exact replays and one fresh missing control.'
            if passed else 'failed on the missing-authority control; retain failure and continue independent work.')}


def verify_tree(value):
    if isinstance(value, dict):
        if {'path', 'sha256'} <= value.keys():
            verify(ROOT, value)
        else:
            for child in value.values():
                verify_tree(child)
    elif isinstance(value, list):
        for child in value:
            verify_tree(child)


def corpus(directory):
    rows, evidence = {}, []
    for name in ('2023', '2025', 'handbook'):
        path = BASE / ('ownership-' + name) / 'attempt-3/evidence.json'
        value = read(ROOT / path); verify_tree(value)
        evidence.append(ref(ROOT, path)); evidence.append(value['ownership'])
        ownership = read(ROOT / value['ownership']['path']); verify_tree(ownership)
        if name == 'handbook':
            require(value['verified_pages'] == value['pages'] == 35
                and not value['page_mismatches'] and not value['cross_page_delivery_gaps'], 'Handbook fidelity mismatch')
            rows[name] = {k: value[k] for k in ('verified_pages', 'pages', 'page_mismatches', 'cross_page_delivery_gaps')}
            rows[name].update(edition=ownership['edition'], index_date=ownership['index_date'])
        else:
            require(value['main_labels_verified'] == value['main_labels_total']
                and value['components_verified'] == value['components_total']
                and value['footnotes_verified'] == value['footnotes_total']
                and value['unresolved_count'] == 0, 'Judgment ownership mismatch')
            rows[name] = {k: v for k, v in value.items() if k != 'ownership'}
    result = {'profile': 'retained-corpus-reconciliation.v1', 'regions': rows, 'evidence': evidence,
        'fidelity_reconciled': True, 'corpus_acceptance_complete': False,
        'remaining': ['Dated legal applicability and later treatment',
            'Source-backed original-answer propositions and positive/false-attribution citation controls']}
    save(directory / 'corpus-reconciliation.json', result)
    return {'reconciliation': ref(ROOT, directory / 'corpus-reconciliation.json'),
        '_node_status': 'BLOCKED', '_conclusion': 'Judgment ownership and 35 Handbook pages verified; dated applicability and actual answer/citation use remain open.'}


def campaign(directory):
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    owners = ('current-binding', 'semantic-preflight', 'account-qualification')
    statuses = {tid: view['tasks'][tid]['status'] for tid in owners}
    passed = all(s == 'SUCCEEDED' for s in statuses.values())
    ledger, grant = read(ROOT / BASE / 'live-calls.json'), read(ROOT / BASE / 'live-grant.json')
    save(directory / 'campaign-reconciliation.json', {'prerequisites': statuses,
        'acquisition_attempts_unchanged': True, 'charges': len(ledger['calls']),
        'ceiling': grant['maximum_calls'], 'deadline_utc': grant['deadline_utc'],
        'account_protocol_ready': passed, 'complete_integration': False,
        'next': 'Drain eligible original acquisitions, answers and comparisons; retain local/legal residuals.'})
    return {'campaign': ref(ROOT, directory / 'campaign-reconciliation.json'),
        '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': 'Campaign current prerequisites reconciled; ' +
            ('eligible original product work remains authorized.' if passed else 'failed live prerequisite affects its consumers only.')}


def verification(directory=None):
    from scripts.legal_integration_acceptance import evaluation_summary
    program = read(ROOT / PROGRAM); validate_program(program, ROOT); revision = program[KEY]
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, old = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])] == old['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    tool_evaluations = evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT)
    findings = {
        'R01': 'Original English/legal interpretation remains open; passing synthetic controls cannot close it.',
        'R02': 'Complete original answers and matched tool effects still require their actual execution/results.',
        'R08': 'Dependency and qualification controls retained; actual downstream use remains to assess.',
        'R14': 'Two retained exact controls passed; missing control and complete final-review capacity use actual node results.',
        'S02': 'Judgment labels/components/footnotes and 35 Handbook pages have later fidelity evidence; dated applicability and actual citation use remain open.',
        'S01': 'Retained sources present; complete original product use remains unqualified.',
        'L01': 'Governing standards and later treatment remain partly qualified.',
        'F01': 'Missing client facts require conditional analysis and do not halt source work.'}
    result = {'profile': 'qualification-continuation-verification.v1', 'calls': len(ledger['calls']),
        'detours': 40, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')}, 'remaining_findings': findings,
        'original_questions': list(QUESTIONS), 'original_obligations': 46, 'original_readings': 35,
        'integration_complete': False,
        'tools_fully_evaluated': tool_evaluations['selected_tools_fully_evaluated'],
        'tool_evaluations': tool_evaluations,
        '_conclusion': 'Same-master continuation accounting verified; use actual original answers and matched effects for substantive acceptance.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
