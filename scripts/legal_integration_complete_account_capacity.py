"""One finite complete-account capacity amendment of the existing master.

Historical contracts, attempts, open service scope and global grants are preserved.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, TOKENIZER, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-16/execution-refresh')
REVIEW = WORK / 'review.md'
KEY = 'complete_account_capacity_repair'
USER = 'refresh the master program, continue the execution'
POINTERS = ('review', 'baseline', 'local_review', 'local_validation', 'qualification_input', 'diagnosis')
PROJECTED = {str(PLAN), 'scripts/legal_product_completion.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_master.py', 'scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/phased/account_input.py',
    'src/legalmath/interpretation/assurance/phased/account_contract.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py',
    'src/legalmath/interpretation/assurance/phased/account_output.py',
    'src/legalmath/interpretation/assurance/phased/account_receipt.py',
    'src/legalmath/interpretation/assurance/phased/phase.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/bounded_checkpoint.py',
    'src/legalmath/interpretation/assurance/bounded_product.py'}


def reopened(before):
    return ['current-binding', 'account-qualification', 'campaign', 'continuation-review',
        *('acquire-' + q for q in QUESTIONS if before['tasks']['acquire-' + q]['status'] in ('FAILED', 'BLOCKED'))]


def dispatch_roots(program):
    from scripts.legal_integration_phased_live import active_live, LIVE
    roots = {str(active_live(program)), str(LIVE)}
    for value in program.values():
        if isinstance(value, dict):
            for pointer in value.get('recoveries', {}).values():
                held = read(ROOT / pointer['path'])
                roots.add(str(Path(held['dispatch']['path']).parents[2]))
    return sorted(roots)


def check_settled_census(root, baseline, old, *, current=False):
    require(baseline['dispatch_roots'] == dispatch_roots(old), 'Wrong dispatch census roots')
    rows = baseline['dispatch_census']
    paths = [r['previous']['path'] for r in rows]
    require(paths and paths == sorted(set(paths)), 'Missing or duplicate dispatch census')
    for row in rows:
        path = Path(row['previous']['path'])
        require(path.name == 'dispatch.json' and any(path.is_relative_to(p)
            for p in map(Path, baseline['dispatch_roots'])), 'Dispatch outside settled owner roots')
        require(row in baseline['archived'] and row['previous']['sha256'] == row['archive']['sha256'],
            'Changed or unarchived dispatch census bytes')
        verify(root, row['archive'])
        require(all(c['status'] in ('VALIDATED', 'FAILED')
            for c in read(root / row['archive']['path'])['calls'].values()),
            'Unsettled retained dispatch reservation')
        if current:
            verify(root, row['previous'])
    if current:
        found = sorted({str(p.relative_to(root)) for name in baseline['dispatch_roots']
            for p in (root / name).rglob('dispatch.json')})
        require(paths == found, 'Incomplete current dispatch census')


def projected_archives(baseline, *, mission=False):
    paths = PROJECTED | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in paths], mission=mission)


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in POINTERS]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        if node['id'] in reopened(before):
            spent = len(before['tasks'][node['id']]['attempts'])
            deferred = before['tasks'][node['id']]['status'] == 'BLOCKED' and node['id'].startswith('acquire-')
            require(not deferred or spent < node['maximum_attempts'], 'Deferred owner has no unused attempt')
            number = node['maximum_attempts'] if deferred else spent + 1
            node.update(maximum_attempts=number,
                deliverable=str(BASE / node['id'] / f'attempt-{number}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
        if node['id'] == 'account-qualification':
            node['acceptance'] = ('One actual oversized complete two-child account passes the '
                'unchanged strict response schema, assignment coverage and citations; reuse its '
                'exact result in common preparation. This does not establish legal correctness.')
    return value


def validate_revision(program, root, *, plan_reference=None):
    from legalmath.interpretation.assurance.phased.account_input import CAPACITY_PROFILE
    revision = program[KEY]
    require(revision['profile'] == 'integration-complete-account-capacity-repair.v1'
        and revision['prior_detours'] == 42 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['qualification_logical_calls'] == 1
        and revision['additional_transport_replacements'] == 0
        and revision['service_scope_reset'] is False
        and revision['service_requalification'] == 'one-reviewed-successor; zero-replacements; no-automatic-reset'
        and revision['output_profile'] == 'typed-account-output-4k.v1'
        and revision['capacity_profile'] == CAPACITY_PROFILE,
        'Unreviewed complete-account capacity repair')
    for key in (*POINTERS, 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('account_reconstruction_repair') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled capacity baseline')
    baseline = read(root / revision['baseline']['path'])
    ledger = read(root / revision['prior_ledger']['path'])
    require(len(ledger['calls']) == baseline['calls'] and baseline['reserved_dispatches'] == 0
        and baseline['supervisor_alive'] is False, 'Unsettled charges or supervisor')
    # The allowance ledger records charges, not dispatch statuses. Reservations
    # belong to the authentic per-product journals frozen at settlement.
    check_settled_census(root, baseline, old)
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archive bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, projected_archives(baseline))
    with historical_evidence(root, projected_archives(baseline)):
        validate_program(projected, root)
    require(revision['reopened_nodes'] == reopened(before)
        and revision['failed_questions'] == [q for q in QUESTIONS if before['tasks']['acquire-' + q]['status'] == 'FAILED']
        and revision['deferred_questions'] == [q for q in QUESTIONS if before['tasks']['acquire-' + q]['status'] == 'BLOCKED'],
        'Capacity repair changed attempt scope')
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Capacity repair changed unrelated graph, resources or acceptance')
    local, validation = (read(root / revision[k]['path']) for k in ('local_review', 'local_validation'))
    require(local['verdict'] == validation['verdict'] == 'PASS'
        and local['provider_calls'] == validation['provider_calls'] == 0
        and validation['ledger_unchanged'] and validation['exact_input_preservation']
        and validation['all_frontiers_measured'] and validation['qualified_result_reuse_tested']
        and {r['question'] for r in validation['branches']} == set(QUESTIONS),
        'Incomplete local capacity validation')
    for pointer in local['evidence'] + validation['evidence']:
        verify(root, pointer)
    require(before['tasks']['semantic-preflight']['status'] == 'SUCCEEDED'
        and 'semantic-preflight' not in reopened(before), 'Successful semantic qualification changed')
    diagnosis = read(root / revision['diagnosis']['path'])
    require(diagnosis['failed_questions'] == revision['failed_questions']
        and diagnosis['deferred_questions'] == revision['deferred_questions']
        and diagnosis['capacity_only_failures'] is False
        and set(diagnosis['causes']) == {'input_capacity', 'completed_output_allowance', 'service_disconnect', 'deferred_before_reservation'}
        and diagnosis['unclassified_failures'] == [] and revision['failed_questions'], 'Unreviewed failure cause')
    from scripts.legal_integration_phased_live import active_live
    previous_live = active_live(old)
    for q in QUESTIONS:
        require(before['tasks']['acquire-' + q]['status'] in ('FAILED', 'SUCCEEDED', 'BLOCKED'), 'Unsettled acquisition')
        verify(root, revision['recoveries'][q])
        failed = q in revision['failed_questions']
        expected_directory = str((WORK / 'live' if failed else previous_live) / 'common' / q)
        expected_live = str(WORK / 'live' if failed else previous_live)
        require(revision['common_directories'][q] == expected_directory
            and revision['live_directories'][q] == expected_live, 'Common or answer evidence route changed')
        from legalmath.interpretation.assurance.phased import account_recovery
        checkpoint = read(root / revision['recoveries'][q]['path'])
        account_recovery.load(root, revision['recoveries'][q], checkpoint['input_hash'])
        if failed:
            require(checkpoint['account_recovery']['details']['path'] == str(previous_live / 'common' / q / 'requirement-details.json')
                and checkpoint['dispatch']['path'] == str(previous_live / 'common' / q / 'calls/dispatch.json'),
                'Recovery does not come from the settled original owner')
        if not failed:
            require(revision['recoveries'][q] == old['account_reconstruction_repair']['recoveries'][q],
                'Successful acquisition recovery changed')
    case = read(root / revision['qualification_input']['path'])
    for key in ('request', 'schema', 'prepared', 'original_refusal'):
        verify(root, case[key])
    request, schema = qualification_request(root, case)
    from legalmath.interpretation.assurance.phased import account_contract, account_input
    account_input.validate_capacity(request, revision['capacity_profile'])
    require(case['question'] in revision['failed_questions'] and case['logical_calls'] == 1
        and 16384 < case['measurement']['local_tokens'] <= 32768
        and case['measurement']['bytes'] <= 200000
        and schema == account_contract.provider_schema()
        and account_recovery.KEY.fullmatch(case['key']), 'Wrong failed-request qualification')
    refused = read(root / case['original_refusal']['path'])
    old_request = deepcopy(request)
    old_request.pop('account_capacity_profile')
    old_request.pop('account_output_profile')
    require(refused == {'request': old_request, 'schema': schema},
        'Qualification changed refused sources, assignment or response schema')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def qualification_request(root, case):
    from scripts.legal_integration_account_instruction_repair import replay_request
    prepared = read(root / case['prepared']['path'])
    request = replay_request(prepared)
    schema = read(root / case['schema']['path'])
    require(request == read(root / case['request']['path'])
        and schema == prepared['original_schema'], 'Changed qualification request or strict schema')
    return request, schema


def registration_candidate():
    baseline = read(ROOT / WORK / 'baseline.json')
    refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / refs[str(PROGRAM)]['path']), read(ROOT / refs[str(STATE)]['path'])
    failed = [q for q in QUESTIONS if before['tasks']['acquire-' + q]['status'] == 'FAILED']
    from scripts.legal_integration_phased_live import active_live
    previous_live = active_live(old)
    revision = {'profile': 'integration-complete-account-capacity-repair.v1', 'prior_detours': 42,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': USER, **{key: ref(ROOT, path) for key, path in (
            ('review', REVIEW), ('baseline', WORK / 'baseline.json'),
            ('local_review', WORK / 'local-review.json'), ('local_validation', WORK / 'local-validation.json'),
            ('qualification_input', WORK / 'qualification-input.json'), ('diagnosis', WORK / 'diagnosis.json'))},
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
        'reopened_nodes': reopened(before), 'failed_questions': failed, 'qualification_logical_calls': 1,
        'deferred_questions': [q for q in QUESTIONS if before['tasks']['acquire-' + q]['status'] == 'BLOCKED'],
        'additional_transport_replacements': 0, 'service_scope_reset': False,
        'service_requalification': 'one-reviewed-successor; zero-replacements; no-automatic-reset',
        'capacity_profile': 'complete-two-child-account-32k.v1',
        'output_profile': 'typed-account-output-4k.v1',
        'recoveries': {q: ref(ROOT, WORK / ('recovery-' + q + '.json')) if q in failed else
            old['account_reconstruction_repair']['recoveries'][q] for q in QUESTIONS},
        'live_directories': {q: str(WORK / 'live' if q in failed else previous_live) for q in QUESTIONS},
        'common_directories': {q: str((WORK / 'live' if q in failed else previous_live) / 'common' / q)
            for q in QUESTIONS}}
    program = expected_program(historical_projection(old, projected_archives(baseline)), before, revision, ROOT)
    validate_program(program, ROOT)
    return program, before, revision


def validate_staged_mission(root, stage, mission):
    from unittest.mock import patch
    from scripts import legal_mission_control as control, legal_integration_master as master
    summary = MasterExecution(root, stage / 'program.json', stage / 'state.json').summary()
    original_safe = control.safe_path
    def prospective_path(base, name):
        actual = original_safe(base, name)
        return root / stage / 'program.json' if actual == root / PROGRAM else actual
    with patch.object(control, 'safe_path', prospective_path), patch.object(master, 'summary', lambda _: summary):
        checked = control.validate(mission, read(root / DOC / 'tools.json'), root)
    require(checked['detours_since_advance'] == 43, 'Candidate detour reconciliation differs')
    return {'verdict': 'PASS', 'detours': 43, 'ready': summary['ready'],
        'program': ref(root, stage / 'program.json'), 'state': ref(root, stage / 'state.json')}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import LIVE
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        supervisor_lock = stack.enter_context((ROOT / LIVE / 'supervisor.lock').open('a'))
        fcntl.flock(supervisor_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
        require(not Path('/proc/' + str(baseline['supervisor_pid'])).exists(),
            'Predecessor supervisor is still alive')
        check_settled_census(ROOT, baseline, read(ROOT / refs[str(PROGRAM)]['path']), current=True)
        program, state, revision = registration_candidate()
        for tid in revision['reopened_nodes']:
            row = state['tasks'][tid]
            row.update(status='PENDING', reason='Reviewed complete-account capacity repair; preserve prior attempts')
            row.pop('result', None)
            for key in ('dispatch_status', 'prerequisite_evidence', 'shared_scope'):
                row.pop(key, None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_COMPLETE_ACCOUNT_CAPACITY_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projected_archives(baseline, mission=True))
        stage = WORK / 'registration-stage'
        save(ROOT / stage / 'program.json', program)
        save(ROOT / stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=pointer, plan=ref(ROOT, PLAN))
        for key, value in program.items():
            if (key in master or key == KEY) and isinstance(value, dict) and 'prior_state' in value and value.get('profile'):
                require(key == KEY or master[key].get('profile') == value['profile'], 'Historical registration differs')
                master[key] = deepcopy(value)
        reason = ('Qualify one actual oversized complete account, then resume each failed original question '
            'independently using exact saved successes; continue ready answers, tools and comparisons.')
        mission['history'].append({'id': 'integration-master-complete-account-capacity-repair-2026-10-16',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed consolidated detour 43 for finite complete-account capacity; no new global allowance.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['local_validation'], revision['local_review']]})
        mission['next_task_reason'] = reason
        save(ROOT / stage / 'mission.json', mission)
        save(ROOT / WORK / 'registration-check.json', validate_staged_mission(ROOT, stage, mission))
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 43, 'reopened_nodes': revision['reopened_nodes']}


def retain_successor_files(root, directory, scope, replacements, circuit):
    """Resume only an unconsumed partial preparation; never reset a used scope."""
    save_scope = root / directory / 'scope.json'
    scope_hash = hashlib.sha256((json.dumps(scope, indent=2, ensure_ascii=False) + '\n').encode()).hexdigest()
    expected = {'scope.json': scope,
        'service-circuit.json': {'stage_hash': scope_hash, 'consecutive_failures': 0,
            'failed_slots': [], 'open': False, 'prior_circuit': circuit},
        'service-recovery.json': {**replacements,
            'profile': SERVICE_SINGLE_DISPATCH_POLICY['profile'], 'stage_hash': scope_hash,
            'prior_replacements': scope['prior_replacements']}}
    for name, value in expected.items():
        path = root / directory / name
        require(not path.exists() or read(path) == value,
            'Successor service preparation changed or was already consumed: ' + name)
    require(not save_scope.exists() or ref(root, save_scope)['sha256'] == scope_hash,
        'Successor scope bytes changed during partial preparation')
    for name, value in expected.items():
        path = root / directory / name
        if not path.exists():
            save(path, value)
    return ref(root, save_scope)


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM)
    revision = program[KEY]
    current = read(ROOT / BASE / 'current-binding.json')
    if current.get('predecessor') == revision['prior_binding'] and current.get('review') == revision['review']:
        require(current['program'] == ref(ROOT, PROGRAM)
            and current['phase_service_scope']['path'] == str(WORK / 'live/service/scope.json'),
            'Resumed binding differs from this reviewed successor')
        provider().check()
        return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'resumed': True,
            'additional_replacements': 0, '_conclusion': 'Existing reviewed successor reused without resetting service state.'}
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    require(ref(ROOT, BASE / 'live-calls.json')['sha256'] == revision['prior_ledger']['sha256'],
        'Charges changed before successor preparation')
    prior = read(ROOT / revision['prior_binding']['path'])
    previous_scope = prior['phase_service_scope']
    service_dir = Path(previous_scope['path']).parent
    circuit, replacement_ref = (ref(ROOT, service_dir / name) for name in ('service-circuit.json', 'service-recovery.json'))
    replacements = read(ROOT / replacement_ref['path'])
    require(read(ROOT / circuit['path'])['open']
        and len(replacements['charges']) == replacements['maximum'] == 48, 'Service prerequisite changed')
    scope_dir = WORK / 'live/service'
    scope = {'profile': 'reviewed-shared-phase-service.v1',
        'grant_hash': digest(read(ROOT / BASE / 'live-grant.json')),
        'review': revision['review'], 'prior_scope': previous_scope, 'prior_circuit': circuit,
        'prior_replacements': replacement_ref, 'additional_replacements': 0,
        'requalification': 'One actual needed oversized account; first terminal failure defers untouched owners.'}
    scope_ref = retain_successor_files(ROOT, scope_dir, scope, replacements, circuit)
    binding = deepcopy(prior)
    binding.pop('phase_service_predecessor', None)
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
    binding['bindings'] += list(revision['recoveries'].values()) + [scope_ref, previous_scope, circuit, replacement_ref]
    case = read(ROOT / revision['qualification_input']['path'])
    binding['bindings'] += [case[k] for k in ('request', 'schema', 'prepared', 'original_refusal')]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'additional_replacements': 0,
        '_conclusion': 'Reviewed input/output profiles bound; old open circuit retained, one explicit successor scope, zero new replacements.'}


def qualify_accounts(service):
    from scripts.legal_integration_phased_live import phase_admit
    from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
    from legalmath.interpretation.assurance.phased import account_contract, account_encoding, account_instructions, account_input
    from legalmath.interpretation.assurance.phased.product import PhasedProduct
    revision = read(ROOT / PROGRAM)[KEY]
    case = read(ROOT / revision['qualification_input']['path'])
    for key in ('request', 'schema', 'prepared', 'original_refusal'):
        verify(ROOT, case[key])
    q = case['question']
    # Same directory, request key and complete product identity as acquisition.
    # A validated qualification is reused there, never sampled a second time.
    product = PhasedProduct(ROOT, ROOT / revision['common_directories'][q], service,
        read(ROOT / read(ROOT / PROGRAM)['prerequisite_repair']['source']['path']), tokenizer(ROOT / TOKENIZER),
        limits=Limits(), maximum_calls=8100, maximum_corrections=1, active_questions=[q],
        phase_admit=phase_admit('account-capacity-qualification'),
        phase_identity=ref(ROOT, BASE / 'current-binding.json')['sha256'],
        requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_instruction_profile=account_instructions.PROFILE,
        requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
        requirement_account_output_profile=revision['output_profile'],
        requirement_account_recovery=revision['recoveries'][q])
    request, schema = qualification_request(ROOT, case)
    require(product.dispatch.measure(request, schema) == case['measurement'], 'Qualification measurement changed')
    def check(value):
        account_contract.validate(value, product, request['records'])
        require(len(value['considered']) == len(set(value['considered']))
            and set(value['considered']) == set(request['required_considered']), 'Lost actual account assignment')
        if request.get('account_correction') is not None:
            require(value['source_gaps'] == request['account_correction']['required_source_gaps'],
                'Account correction changed required document-qualified source gaps')
    phase = product.run_phase('account-capacity-qualification', [{'key': case['key'], 'request': request,
        'schema': schema, 'validate': check}])
    result = phase['results'][0]['result'] if phase['results'] else phase['resource_refusal']
    passed = result['status'] == 'VALIDATED'
    path = WORK / 'live/account-qualification/result.json'
    save(ROOT / path, {'qualified': passed, 'complete': True, 'result': result,
        'logical_call_ceiling': 1, 'reused_in_original_common_directory': revision['common_directories'][q],
        'request_key': case['key'], 'scope': 'Actual capacity/interface qualification; not legal acceptance or tool effect.'})
    return {'qualification': ref(ROOT, path), '_node_status': 'SUCCEEDED' if passed else 'BLOCKED',
        '_conclusion': ('Actual complete account passed; reuse it and continue independent original questions.' if passed
            else 'Actual complete account failed qualification; retain the precise response or service limitation.')}


def campaign(directory):
    from scripts.legal_integration_account_instruction_repair import campaign as reconcile
    return reconcile(directory)


def verification(directory=None):
    from scripts.legal_integration_acceptance import evaluation_summary
    program = read(ROOT / PROGRAM)
    validate_program(program, ROOT)
    revision = program[KEY]
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, prior = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    require(state['tasks']['semantic-preflight'] == before['tasks']['semantic-preflight'],
        'Successful semantic owner changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    evaluations = evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT)
    result = {'profile': 'complete-account-capacity-repair-verification.v1', 'calls': len(ledger['calls']),
        'historical_calls': 41, 'detours': 43, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'original_questions': list(QUESTIONS), 'original_obligations': 46, 'original_readings': 35,
        'integration_complete': False, 'tools_fully_evaluated': evaluations['selected_tools_fully_evaluated'],
        'remaining': ['Complete source-grounded original accounts and answers',
            'Matched actual answer effects of six selected tools', 'Dated applicability and later treatment'],
        '_conclusion': 'Capacity amendment and accounting verified; original legal acceptance remains required.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
