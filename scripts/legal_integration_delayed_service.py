"""User-authorized hourly service recovery in the existing integration master."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import (read, save, ref, verify, require, digest,
    validate_program, historical_evidence, merged_historical_archives)
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission
from legalmath.interpretation.assurance.bounded_provider import SERVICE_DELAYED_POLICY

KEY = 'delayed_service_recovery'
WORK = Path('artifacts/legal-mission-control/2026-10-16/delayed-service')
REVIEW = DOC / 'results/delayed-service-retry-policy.md'
USER = 'I think sol can work, right?  it may not be reliable.  so if it does not work, you can wait for an hour or two and try again.'
REOPEN = ['acquire-p10', 'acquire-evidence']
MUTATED = {str(PLAN), 'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_master.py', 'scripts/legal_integration_delayed_service.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/phased/admission.py'}


def projection(baseline, *, mission=False):
    allowed = MUTATED | ({str(PROGRAM)} if mission else set())
    return archives([row for row in baseline['archived'] if row['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline', 'review', 'result')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-delayed-service.v1'
        and revision['user_instruction'] == USER and revision['work'] == str(WORK)
        and revision['prior_detours'] == 51 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == revision['additional_task_attempts'] == 0
        and revision['additional_transport_replacements'] == 24
        and revision['service_recovery_policy'] == SERVICE_DELAYED_POLICY
        and revision['attempts_reset'] is False and revision['reopened_nodes'] == REOPEN,
        'Unreviewed delayed service authority')
    for key in ('baseline', 'review', 'result', 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger', 'prior_grant'):
        verify(root, revision[key])
    require(set(revision['implementation']) == MUTATED - {str(PLAN)}, 'Delayed implementation scope changed')
    for pointer in revision['implementation'].values(): verify(root, pointer)
    baseline = read(root / revision['baseline']['path'])
    held = {row['previous']['path']: row['archive'] for row in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    require(baseline['prior_detours'] == 51 and baseline['calls'] == 2359
        and baseline['running_owners'] == baseline['reserved_dispatches'] == 0, 'Changed delayed comparator')
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE),
            ('prior_binding', BASE / 'current-binding.json'), ('prior_ledger', BASE / 'live-calls.json'),
            ('prior_grant', BASE / 'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost delayed predecessor: ' + key)
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('local_refresh') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled delayed predecessor')
    nodes = {n['id']: n for n in old['tasks']}
    for tid in REOPEN:
        require(before['tasks'][tid]['status'] == 'BLOCKED'
            and before['tasks'][tid].get('dispatch_status') == 'NOT_DISPATCHED'
            and len(before['tasks'][tid]['attempts']) < nodes[tid]['maximum_attempts'],
            'Delayed continuation needs its own unused attempt: ' + tid)
    mapping = merged_historical_archives(root, projection(baseline))
    projected = historical_projection(old, mapping)
    with historical_evidence(root, mapping): validate_program(projected, root)
    expected = expected_program(projected, revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference),
        'Delayed continuation changed graph, deadlines, attempts or unrelated evidence')
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0
        and result['ledger_unchanged'] and result['legal_acceptance'] is False,
        'Missing bounded delayed-retry evidence')
    for pointer in result['evidence']: verify(root, pointer)
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def project_state(before, program, now):
    state = deepcopy(before)
    require(not any(r['status'] == 'RUNNING' for r in state['tasks'].values()), 'Running owner cannot migrate')
    nodes = {n['id']: n for n in program['tasks']}
    for tid in REOPEN:
        row = state['tasks'][tid]
        require(row['status'] == 'BLOCKED' and row.get('dispatch_status') == 'NOT_DISPATCHED'
            and len(row['attempts']) < nodes[tid]['maximum_attempts'], 'No unused deferred attempt: ' + tid)
        row.update(status='PENDING', reason='User-authorized delayed service recovery; existing unused attempt')
        for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'): row.pop(key, None)
    state['program_hash'] = digest(program)
    state['events'].append(dict(action='REVIEWED_DELAYED_SERVICE', task_id=None, at_utc=now,
        review=program[KEY]['review'], attempts_reset=False, calls_added=0))
    return state


def validate_state_history(program, state, root):
    before = read(root / program[KEY]['prior_state']['path'])
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'],
            'Delayed continuation changed old attempts: ' + tid)
        if tid not in REOPEN and row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Delayed continuation changed an unrelated settled owner: ' + tid)


def retained(path, value):
    if path.exists(): require(read(path) == value, 'Refuse to replace retained delayed evidence: ' + str(path))
    else: save(path, value)


def check_staged_binding(stage, binding):
    """Use the real allowance validator on staged current bytes, with no call."""
    from unittest.mock import patch
    from scripts.legal_integration_campaign import provider
    # Relocating grant files changes the exact path bound by old approvals.
    # Overlay only the two proposed current files; all historical approval
    # bytes and their logical paths remain exactly as in actual execution.
    targets = {ROOT / PROGRAM: ROOT / stage / 'program.json',
        ROOT / BASE / 'current-binding.json': ROOT / stage / 'binding.json'}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def staged_text(path, *args, **kwargs):
        return original_text(targets.get(path, path), *args, **kwargs)
    def staged_bytes(path, *args, **kwargs):
        return original_bytes(targets.get(path, path), *args, **kwargs)
    with patch.object(Path, 'read_text', staged_text), patch.object(Path, 'read_bytes', staged_bytes):
        actual = provider().check()
    require(len(actual['calls']) == 2359, 'Staged provider check changed charges')


def candidate_binding(program, program_pointer, baseline, held):
    """Retain the old outage, and use the user's elapsed-hour instruction once."""
    revision = program[KEY]
    prior = read(ROOT / revision['prior_binding']['path'])
    grant, ledger = read(ROOT / revision['prior_grant']['path']), read(ROOT / revision['prior_ledger']['path'])
    old_scope = prior['phase_service_scope']
    old_dir = Path(old_scope['path']).parent
    circuit_ref, recovery_ref = (held[str(old_dir / name)] for name in ('service-circuit.json', 'service-recovery.json'))
    circuit, replacements = read(ROOT / circuit_ref['path']), read(ROOT / recovery_ref['path'])
    require(circuit['open'] and circuit['stage_hash'] == old_scope['sha256']
        and len(replacements['charges']) == 48, 'Old outage or spent replacements changed')
    slot = circuit['failed_slots'][-1]
    charge = ledger['calls'][slot - 1]
    receipt_dir = BASE / 'provider-evidence' / f"{slot:04}-{charge['request_hash'][:16]}"
    manifest = read(ROOT / receipt_dir / 'manifest.json')
    require(manifest['allowance_slot'] == slot and manifest['request_hash'] == charge['request_hash']
        and not manifest['complete_output_present'], 'Old outage lacks exact receipt')
    import hashlib, json
    data = (ROOT / receipt_dir / 'events.jsonl').read_bytes()
    require(hashlib.sha256(data).hexdigest() == manifest['files']['events.jsonl']['retained_sha256'],
        'Old outage receipt changed')
    from legalmath.interpretation.search.providers import transient_service_details
    details = transient_service_details([json.loads(line) for line in data.splitlines() if line.strip()], output_present=False)
    require(details is not None and not details.get('unparsed_retry_after'), 'Old outage is not an eligible transient failure')
    # The old 300-second process timeout gives a conservative latest failure
    # time even though the original manifest did not retain an end timestamp.
    due = datetime.fromtimestamp(int(charge['issued_at_ns']) / 1e9, timezone.utc) + timedelta(
        seconds=305 + max(3600, details.get('retry_after_seconds') or 0))
    require(datetime.now(timezone.utc) >= due, 'Prior outage has not yet waited one hour')
    require(datetime.now(timezone.utc) + timedelta(seconds=305) <= datetime.fromisoformat(grant['deadline_utc']),
        'Original grant deadline cannot fit a new request')
    scope = dict(profile='reviewed-shared-phase-service.v1', grant_hash=digest(grant), review=revision['review'],
        prior_scope=old_scope, prior_circuit=circuit_ref, prior_replacements=recovery_ref,
        prior_replacement_count=48, additional_replacements=24, first_eligible_at_utc=due.isoformat(),
        previous_failure_receipt=ref(ROOT, receipt_dir / 'manifest.json'), service_recovery_policy=SERVICE_DELAYED_POLICY,
        requalification='First necessary P10/evidence request after elapsed cooldown; no availability claim before completion.')
    retained(ROOT / WORK / 'service/scope.json', scope)
    scope_ref = ref(ROOT, WORK / 'service/scope.json')
    retained(ROOT / WORK / 'service/service-circuit.json', dict(stage_hash=scope_ref['sha256'],
        consecutive_failures=0, failed_slots=[], open=False, prior_circuit=circuit_ref))
    retained(ROOT / WORK / 'service/service-recovery.json', dict(profile=SERVICE_DELAYED_POLICY['profile'],
        stage_hash=scope_ref['sha256'], maximum=24, charges=[]))
    binding = deepcopy(prior)
    binding.pop('phase_service_predecessor', None)
    binding.update(user_instruction=USER, review=revision['review'], predecessor=revision['prior_binding'],
        ledger_before=revision['prior_ledger'], program=program_pointer,
        phase_service_scope=scope_ref, service_recovery_policy=SERVICE_DELAYED_POLICY)
    paths = sorted((ROOT / 'src/legalmath').rglob('*.py')) + sorted((ROOT / 'scripts').glob('legal_*.py'))
    paths += [ROOT / p for p in (PLAN, REVIEW, Path(program['prerequisite_repair']['source']['path']),
        BASE / 'campaign-routing.toml', Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] = [ref(ROOT, p) for p in paths] + [program_pointer, scope_ref]
    binding['bindings'] += [revision[k] for k in ('baseline', 'result', 'prior_grant', 'prior_ledger')]
    binding['bindings'] += [old_scope, circuit_ref, recovery_ref]
    historical = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    local = read(ROOT / program['local_refresh']['baseline']['path'])
    for row in local['archived'] + baseline['archived']:
        historical[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(historical.values())
    return binding


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        initial = read(ROOT / PROGRAM)
        for path in dict.fromkeys((active_live(initial) / 'supervisor.lock', LIVE / 'supervisor.lock',
                STATE.with_suffix('.run.lock'), DOC / 'mission.execution.lock', STATE.with_suffix('.lock'))):
            handle = stack.enter_context((ROOT / path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / journal).exists():
            if read(ROOT / journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            require(read(ROOT / PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different delayed registration')
            provider().check()
            return {'registered': True, 'resumed': True, 'calls_added': 0}
        baseline = read(ROOT / WORK / 'baseline.json')
        held = {row['previous']['path']: row['archive'] for row in baseline['archived']}
        old_binding = read(ROOT / BASE / 'current-binding.json')
        service_dir = Path(old_binding['phase_service_scope']['path']).parent
        for path in (PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json', BASE / 'live-calls.json',
                BASE / 'live-grant.json', service_dir / 'service-circuit.json', service_dir / 'service-recovery.json',
                *map(Path, baseline['dispatch_census'])):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Delayed baseline changed: ' + str(path))
        old, before = read(ROOT / PROGRAM), read(ROOT / STATE)
        revision = dict(profile='integration-delayed-service.v1', user_instruction=USER, work=str(WORK),
            prior_detours=51, additional_consolidated_revision=1, live_calls_added=0, additional_task_attempts=0,
            additional_transport_replacements=24, service_recovery_policy=SERVICE_DELAYED_POLICY,
            attempts_reset=False, reopened_nodes=REOPEN,
            baseline=ref(ROOT, WORK / 'baseline.json'), review=ref(ROOT, REVIEW), result=ref(ROOT, WORK / 'local-result.json'),
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
        binding = candidate_binding(program, pointer, baseline, held)
        save(ROOT / stage / 'binding.json', binding)
        check_staged_binding(stage, binding)
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), **{KEY: revision})
        reason = ('Resume the existing P10/evidence attempts and their eligible baseline/tool/comparison work. '
            'Transient Sol failures retain an exact one-hour then two-hour schedule. '
            'P14 and Gatecoin retain separate blockers; global calls, deadline and old charges remain unchanged.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-delayed-service-2026-10-16',
            task_id='product-contribution', kind='product_evaluation', outcome='no_advance',
            decision='Apply explicit delayed-retry instruction within existing global grant and unused owner attempts.',
            next_task='product-contribution', next_task_reason=reason, recorded_at_utc=now,
            result_evidence=[pointer, revision['review'], revision['result']]))
        save(ROOT / stage / 'mission.json', mission)
        save(ROOT / WORK / 'registration-check.json', validate_staged_mission(ROOT, stage, mission, 52))
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'),
                (BASE / 'current-binding.json', 'binding.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
        provider().check()
    return {'registered': True, 'detours': 52, 'reopened_nodes': REOPEN, 'calls_added': 0,
        'automatic_delayed_replacements': 24, 'prior_replacements_retained': 48}


def verification(directory=None):
    program = read(ROOT / PROGRAM); validate_program(program, ROOT)
    revision = program[KEY]
    state = read(ROOT / STATE); validate_state_history(program, state, ROOT)
    ledger, prior = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Delayed continuation changed old charges')
    require(ref(ROOT, BASE / 'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Delayed grant changed')
    binding = read(ROOT / BASE / 'current-binding.json')
    require(binding['review'] == revision['review'] and binding['program'] == ref(ROOT, PROGRAM)
        and binding['service_recovery_policy'] == SERVICE_DELAYED_POLICY, 'Delayed live binding changed')
    for pointer in binding['bindings']: verify(ROOT, pointer)
    scope = read(ROOT / binding['phase_service_scope']['path'])
    for key in ('prior_scope', 'prior_circuit', 'prior_replacements'): verify(ROOT, scope[key])
    service_dir = ROOT / Path(binding['phase_service_scope']['path']).parent
    recovery, circuit = read(service_dir / 'service-recovery.json'), read(service_dir / 'service-circuit.json')
    require(recovery['maximum'] == 24 and len(recovery['charges']) <= 24
        and recovery['stage_hash'] == circuit['stage_hash'] == binding['phase_service_scope']['sha256'],
        'Delayed service accounting changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    result = dict(profile='integration-delayed-service-verification.v1', calls=len(ledger['calls']), historical_calls=41,
        detours=52, prior_calls_preserved=True, prior_attempts_preserved=True, live_binding_current=True,
        delayed_replacements=len(recovery['charges']), prior_replacements_retained=48,
        service_circuit_open=circuit['open'], latest_retry=recovery['charges'][-1] if recovery['charges'] else None,
        original_questions=list(QUESTIONS), original_obligations=46, original_readings=35,
        integration_complete=False, **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')})
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
