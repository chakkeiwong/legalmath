"""One reviewed frontier amendment; preserve the existing master and authority."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission
from legalmath.interpretation.assurance.bounded_provider import SERVICE_DELAYED_POLICY, TERMINAL_CANCELLATION_POLICY

KEY = 'frontier_refresh'
WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh')
REVIEW = DOC / 'results/gap-refresh-2026-10-17.md'
USER = ('for the other gaps. refresh the master program with your suggestion for closing them.  '
        'for HTTP 499 error, do the same, wait for some time and try again.   continue the execution')
REOPEN = ['acquire-p10']
VETO_REASON = 'Receipt reuse changed source, assignment, instructions or response schema'
MUTATED = {str(PLAN), 'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_master.py', 'scripts/legal_integration_gap_refresh.py',
    'scripts/legal_integration_delayed_service.py',
    'scripts/legal_integration_phased_live.py',
    'tests/tooling/test_delayed_service_registration.py',
    'src/legalmath/interpretation/search/providers.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py'}


def projection(baseline, *, mission=False):
    allowed = MUTATED | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        if task['id'] == 'acquire-p10': task['maximum_attempts'] += 1
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline', 'review', 'result')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_proof(root, revision):
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0
        and result['ledger_unchanged'] and result['legal_acceptance'] is False,
        'Missing frontier repair result')
    for pointer in result['evidence']: verify(root, pointer)
    for name in ('before_replay', 'after_replay', 'test_result'): verify(root, result[name])
    before, after, tests = (read(root / result[k]['path'])
        for k in ('before_replay', 'after_replay', 'test_result'))
    require(before['reproduced_error'] == VETO_REASON and before['same_record_population']
        and before['schema_equal'] and before['ledger_unchanged'] and before['provider_calls'] == 0
        and before['differences'] and all(r['path'].startswith('/records/') for r in before['differences']),
        'Before replay does not prove the retained order-only blocker')
    require(after['receipt_reused'] and not after['differences'] and after['schema_equal']
        and after['ledger_unchanged'] and after['provider_calls'] == 0,
        'Actual repaired constructor did not reuse the complete receipt')
    require(tests['exit_code'] == 0 and tests['semantic_mutations_rejected']
        and tests['delayed_499_controls_passed'], 'Missing adversarial frontier controls')
    return result


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-frontier-refresh.v1'
        and revision['user_instruction'] == USER and revision['work'] == str(WORK)
        and revision['prior_detours'] == 52 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == revision['additional_transport_replacements'] == 0
        and revision['additional_task_attempts'] == 1 and revision['cumulative_additional_attempts'] == 20
        and revision['attempt_increments'] == {'acquire-p10': 1}
        and revision['reopened_nodes'] == REOPEN and revision['attempts_reset'] is False
        and revision['repair_allowance_added'] == 0 and revision['service_scope_reset'] is False
        and revision['terminal_cancellation_recovery'] == TERMINAL_CANCELLATION_POLICY
        and revision['service_recovery_policy'] == SERVICE_DELAYED_POLICY,
        'Unreviewed frontier authority')
    for key in ('baseline', 'review', 'result', 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger', 'prior_grant'):
        verify(root, revision[key])
    require(set(revision['implementation']) == MUTATED - {str(PLAN)}, 'Frontier implementation scope changed')
    for pointer in revision['implementation'].values(): verify(root, pointer)
    baseline = read(root / revision['baseline']['path'])
    held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Frontier historical bytes changed')
        verify(root, row['archive'])
    require(baseline['prior_detours'] == 52 and baseline['calls'] == 2369
        and baseline['running_owners'] == baseline['reserved_dispatches'] == 0, 'Changed frontier comparator')
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE),
            ('prior_binding', BASE / 'current-binding.json'), ('prior_ledger', BASE / 'live-calls.json'),
            ('prior_grant', BASE / 'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost frontier predecessor: ' + key)
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('delayed_service_recovery') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values())
        and old['repair_execution']['repair_ids'] == ['R' + str(n) for n in range(1, 11)]
        and old['repair_execution']['cumulative_additional_attempts'] == 19,
        'Frontier revision renewed the exhausted repair allowance')
    owner = before['tasks']['acquire-p10']
    ceiling = next(n['maximum_attempts'] for n in old['tasks'] if n['id'] == 'acquire-p10')
    require(owner['status'] == 'FAILED' and len(owner['attempts']) == ceiling == 7,
        'Frontier continuation has a different owner baseline')
    targets = revision['resolved_vetoes']
    require(len(targets) == 1 and before.get('continuation_vetoes', []).count(targets[0]) == 1
        and targets[0]['code'] == 'E_INTEGRITY' and targets[0]['reason'] == VETO_REASON,
        'Frontier repair cannot remove unrelated vetoes')
    for pointer in targets[0]['evidence']: verify(root, pointer)
    validate_proof(root, revision)
    mapping = projection(baseline)
    projected = historical_projection(old, mapping)
    with historical_evidence(root, mapping): validate_program(projected, root)
    expected = expected_program(projected, revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference),
        'Frontier changed unrelated graph, evidence, attempts or deadlines')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def project_state(before, program, now):
    revision = program[KEY]
    state = deepcopy(before)
    require(not any(r['status'] == 'RUNNING' for r in state['tasks'].values()), 'Running owner cannot migrate')
    for target in revision['resolved_vetoes']:
        require(state.get('continuation_vetoes', []).count(target) == 1
            and target['code'] == 'E_INTEGRITY' and target['reason'] == VETO_REASON,
            'Missing exact receipt veto')
        state['continuation_vetoes'].remove(target)
        state.setdefault('resolved_continuation_vetoes', []).append(dict(veto=target,
            review=revision['review'], evidence=revision['result'], at_utc=now,
            basis='Actual constructor replay; complete record/base equality and semantic mutation controls.',
            attempts_reset=False, calls_added=0))
    row = state['tasks']['acquire-p10']
    require(row['status'] == 'FAILED' and len(row['attempts']) == 7, 'Changed P10 predecessor')
    row.update(status='PENDING', reason='Authenticated completed-contract repair; final existing owner allocation')
    for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'): row.pop(key, None)
    state['program_hash'] = digest(program)
    state['events'].append(dict(action='REVIEWED_FRONTIER_REFRESH', task_id=None, at_utc=now,
        review=revision['review'], attempts_reset=False, calls_added=0, additional_task_attempts=1))
    return state


def validate_state_history(program, state, root):
    revision = program[KEY]
    before = read(root / revision['prior_state']['path'])
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'],
            'Frontier changed historical attempts: ' + tid)
        if tid not in REOPEN and row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Frontier changed unrelated settled owner: ' + tid)
    prior_resolved = before.get('resolved_continuation_vetoes', [])
    resolved = state.get('resolved_continuation_vetoes', [])
    require(resolved[:len(prior_resolved)] == prior_resolved, 'Frontier lost old veto resolutions')
    for target in revision['resolved_vetoes']:
        require(any(r['veto'] == target and r['review'] == revision['review']
            and r['evidence'] == revision['result'] for r in resolved), 'Missing retained receipt-veto resolution')
    require(all(v in state.get('continuation_vetoes', []) for v in before.get('continuation_vetoes', [])
        if v not in revision['resolved_vetoes']), 'Frontier lost an unresolved predecessor veto')


def candidate_binding(program, pointer, baseline):
    revision = program[KEY]
    prior = read(ROOT / revision['prior_binding']['path'])
    binding = deepcopy(prior)
    binding.update(user_instruction=USER, review=revision['review'], program=pointer,
        predecessor=revision['prior_binding'], phase_service_predecessor=revision['prior_binding'],
        ledger_before=revision['prior_ledger'], terminal_cancellation_recovery=TERMINAL_CANCELLATION_POLICY)
    # Inherit the exact scope, circuit and spent delayed-replacement ledger.
    require(prior['service_recovery_policy'] == SERVICE_DELAYED_POLICY, 'Foreign delayed policy')
    paths = sorted((ROOT / 'src/legalmath').rglob('*.py')) + sorted((ROOT / 'scripts').glob('legal_*.py'))
    paths += [ROOT / p for p in (PLAN, REVIEW, Path(program['prerequisite_repair']['source']['path']),
        BASE / 'campaign-routing.toml', Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] = [ref(ROOT, p) for p in paths] + [pointer, prior['phase_service_scope']]
    binding['bindings'] += [revision[k] for k in ('baseline', 'result', 'prior_binding', 'prior_grant', 'prior_ledger')]
    historical = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in baseline['archived']:
        historical[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(historical.values())
    return binding


def check_staged_binding(stage):
    from unittest.mock import patch
    from scripts.legal_integration_campaign import provider
    targets = {ROOT / PROGRAM: ROOT / stage / 'program.json',
        ROOT / BASE / 'current-binding.json': ROOT / stage / 'binding.json'}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def staged_text(path, *args, **kwargs): return original_text(targets.get(path, path), *args, **kwargs)
    def staged_bytes(path, *args, **kwargs): return original_bytes(targets.get(path, path), *args, **kwargs)
    with patch.object(Path, 'read_text', staged_text), patch.object(Path, 'read_bytes', staged_bytes):
        service = provider()
        actual = service.check()
        require(service.retry_terminal_499, 'Staged provider did not select cancellation policy')
    require(len(actual['calls']) == 2369, 'Staged provider changed prior charges')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        initial = read(ROOT / PROGRAM)
        for path in dict.fromkeys((active_live(initial) / 'supervisor.lock', WORK / 'live/supervisor.lock',
                LIVE / 'supervisor.lock', STATE.with_suffix('.run.lock'),
                DOC / 'mission.execution.lock', STATE.with_suffix('.lock'))):
            (ROOT / path).parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context((ROOT / path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / journal).exists():
            if read(ROOT / journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            require(read(ROOT / PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different frontier registration')
            provider().check()
            return {'registered': True, 'resumed': True, 'calls_added': 0}
        baseline = read(ROOT / WORK / 'baseline.json')
        held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        old_binding = read(ROOT / BASE / 'current-binding.json')
        service_dir = Path(old_binding['phase_service_scope']['path']).parent
        for path in (PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json', BASE / 'live-calls.json',
                BASE / 'live-grant.json', service_dir / 'service-circuit.json', service_dir / 'service-recovery.json',
                *map(Path, baseline['dispatch_census'])):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Frontier baseline changed: ' + str(path))
        old, before = read(ROOT / PROGRAM), read(ROOT / STATE)
        targets = [v for v in before.get('continuation_vetoes', [])
            if v['code'] == 'E_INTEGRITY' and v['reason'] == VETO_REASON]
        revision = dict(profile='integration-frontier-refresh.v1', user_instruction=USER, work=str(WORK),
            prior_detours=52, additional_consolidated_revision=1, live_calls_added=0,
            additional_task_attempts=1, cumulative_additional_attempts=20, attempt_increments={'acquire-p10': 1},
            additional_transport_replacements=0, repair_allowance_added=0, service_scope_reset=False,
            attempts_reset=False, reopened_nodes=REOPEN, resolved_vetoes=targets,
            terminal_cancellation_recovery=TERMINAL_CANCELLATION_POLICY, service_recovery_policy=SERVICE_DELAYED_POLICY,
            baseline=ref(ROOT, WORK / 'baseline.json'), review=ref(ROOT, REVIEW),
            result=ref(ROOT, WORK / 'local-result-registration.json'),
            implementation={p: ref(ROOT, p) for p in sorted(MUTATED - {str(PLAN)})},
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)],
            prior_binding=held[str(BASE / 'current-binding.json')], prior_ledger=held[str(BASE / 'live-calls.json')],
            prior_grant=held[str(BASE / 'live-grant.json')])
        program = expected_program(historical_projection(old, projection(baseline)), revision, ROOT)
        validate_program(program, ROOT)
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before, program, now)
        stage = WORK / 'registration-stage'
        save(ROOT / stage / 'program.json', program); save(ROOT / stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        binding = candidate_binding(program, pointer, baseline)
        save(ROOT / stage / 'binding.json', binding)
        check_staged_binding(stage)
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), **{KEY: revision})
        reason = ('Continue repaired P10 and independent evidence using existing authority, then their eligible '
            'full baseline/tool/comparison tasks. Terminal no-output HTTP 499 shares the retained hourly ledger. '
            'P14 invalid request and Gatecoin refusal remain separate; original legal and tool acceptance stays open.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-frontier-refresh-2026-10-17',
            task_id='product-contribution', kind='product_evaluation', outcome='no_advance',
            decision='Adopt proved receipt-construction repair and delayed 499 recovery; allocate last existing owner attempt.',
            next_task='product-contribution', next_task_reason=reason, recorded_at_utc=now,
            result_evidence=[pointer, revision['review'], revision['result']]))
        save(ROOT / stage / 'mission.json', mission)
        save(ROOT / WORK / 'registration-check.json', validate_staged_mission(ROOT, stage, mission, 53))
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'),
                (BASE / 'current-binding.json', 'binding.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
        provider().check()
    return {'registered': True, 'detours': 53, 'reopened_nodes': REOPEN, 'calls_added': 0,
        'additional_attempts_allocated': 20, 'repairs_allocated': 10, 'replacement_reserve_reset': False}


def verification(directory=None):
    program = read(ROOT / PROGRAM); validate_program(program, ROOT)
    revision = program[KEY]
    state = read(ROOT / STATE); validate_state_history(program, state, ROOT)
    ledger, prior = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Frontier changed prior charges')
    require(ref(ROOT, BASE / 'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Frontier grant changed')
    binding, old_binding = read(ROOT / BASE / 'current-binding.json'), read(ROOT / revision['prior_binding']['path'])
    require(binding['review'] == revision['review'] and binding['program'] == ref(ROOT, PROGRAM)
        and binding['service_recovery_policy'] == SERVICE_DELAYED_POLICY
        and binding['terminal_cancellation_recovery'] == TERMINAL_CANCELLATION_POLICY
        and binding['phase_service_scope'] == old_binding['phase_service_scope']
        and binding['phase_service_predecessor'] == binding['predecessor'] == revision['prior_binding'],
        'Frontier live binding changed')
    for pointer in binding['bindings']: verify(ROOT, pointer)
    service_dir = Path(binding['phase_service_scope']['path']).parent
    recovery = read(ROOT / service_dir / 'service-recovery.json')
    prior_recovery = read(ROOT / WORK / 'before' / service_dir / 'service-recovery.json')
    require(recovery['maximum'] == 24 and len(recovery['charges']) <= 24
        and recovery['charges'][:len(prior_recovery['charges'])] == prior_recovery['charges'],
        'Frontier reset spent replacements')
    circuit = read(ROOT / service_dir / 'service-circuit.json')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    result = dict(profile='integration-frontier-verification.v1', calls=len(ledger['calls']), historical_calls=41,
        detours=53, additional_attempts_allocated=20, repairs_allocated=10, prior_calls_preserved=True,
        prior_attempts_preserved=True, live_binding_current=True, delayed_replacements=len(recovery['charges']),
        prior_replacements_retained=48, service_circuit_open=circuit['open'],
        latest_retry=recovery['charges'][-1] if recovery['charges'] else None,
        original_questions=list(QUESTIONS), original_obligations=46, original_readings=35,
        integration_complete=False, **{k:view[k] for k in ('execution', 'ready', 'running', 'blocked')})
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
