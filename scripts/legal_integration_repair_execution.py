"""Reviewed rounds within one explicit ten-repair/twenty-attempt allowance.

Each round preserves the same master, ledger, service scope and predecessors.
Staging a reviewed round grants no model calls, deadline or successful resample.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives

WORK = Path('artifacts/legal-mission-control/2026-10-16/integration-repairs')
KEY = 'repair_execution'
USER = 'you have 10 repairs and 20 attemps. continue the execution'
POINTERS = ('authorization', 'review', 'baseline', 'local_review', 'local_validation', 'round_spec')
LOCAL_WORK = WORK / 'local-refresh'
LOCAL_USER = 'git commit.  refresh the master program with what you suggested.  review the program.  continue the execution'
LOCAL_MUTATED = {str(PLAN), 'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_master.py', 'scripts/legal_integration_repair_execution.py',
    'src/legalmath/interpretation/search/providers.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py'}


def local_refresh_projection(baseline, *, mission=False):
    allowed = LOCAL_MUTATED | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in allowed], mission=mission)


def expected_local_refresh(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value['local_refresh'] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline', 'review', 'result')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_local_refresh(program, root, *, plan_reference=None):
    """One local package after R10; the exhausted grant is not extended."""
    revision = program['local_refresh']
    require(revision['profile'] == 'integration-post-r10-local-refresh.v1'
        and revision['user_instruction'] == LOCAL_USER and revision['work'] == str(LOCAL_WORK)
        and revision['prior_detours'] == 50 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == revision['additional_task_attempts'] == 0
        and revision['additional_transport_replacements'] == 0
        and revision['attempts_reset'] is False and revision['reopened_nodes'] == [],
        'Unreviewed local refresh authority')
    for key in ('baseline', 'review', 'result', 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    require(set(revision['implementation']) == LOCAL_MUTATED - {str(PLAN)},
        'Local implementation scope changed')
    for pointer in revision['implementation'].values():
        verify(root, pointer)
    baseline = read(root / revision['baseline']['path'])
    held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Local archive changed historical bytes')
        verify(root, row['archive'])
    require(baseline['prior_detours'] == 50 and baseline['calls'] == 2359
        and baseline['running_owners'] == baseline['reserved_dispatches'] == 0,
        'Local refresh comparator changed')
    require(all(revision[key] == held[str(path)] for key, path in (
        ('prior_program', PROGRAM), ('prior_state', STATE),
        ('prior_binding', BASE / 'current-binding.json'), ('prior_ledger', BASE / 'live-calls.json'))),
        'Local refresh lost its frozen predecessor')
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(not old.get('local_refresh') and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values())
        and old[KEY]['repair_ids'] == ['R' + str(i) for i in range(1, 11)]
        and old[KEY]['cumulative_additional_attempts'] == 19, 'Local refresh renewed or changed old allocation')
    mapping = local_refresh_projection(baseline)
    projected = historical_projection(old, mapping)
    with historical_evidence(root, mapping):
        validate_program(projected, root)
    expected = expected_local_refresh(projected, revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference),
        'Local refresh changed graph, deadlines, attempts or unrelated evidence')
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0
        and result['ledger_unchanged'] and result['legal_acceptance'] is False,
        'Local refresh lacks bounded result evidence')
    for pointer in result['evidence']:
        verify(root, pointer)
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def register_local_refresh():
    """Adopt the reviewed local package without reopening any live owner."""
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    journal = LOCAL_WORK / 'registration.json'
    initial = read(ROOT / PROGRAM)
    with ExitStack() as stack:
        for path in dict.fromkeys((active_live(initial) / 'supervisor.lock', LIVE / 'supervisor.lock',
                STATE.with_suffix('.run.lock'), DOC / 'mission.execution.lock', STATE.with_suffix('.lock'))):
            handle = stack.enter_context((ROOT / path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / journal).exists():
            if read(ROOT / journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            require(read(ROOT / PROGRAM).get('local_refresh', {}).get('work') == str(LOCAL_WORK),
                'Local registration belongs to a different program')
            return {'registered': True, 'resumed': True, 'live_calls_added': 0}
        baseline = read(ROOT / LOCAL_WORK / 'baseline.json')
        held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json',
                     BASE / 'live-calls.json', BASE / 'live-grant.json', *map(Path, baseline['dispatch_census'])):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Local baseline changed: ' + str(path))
        old, before = read(ROOT / PROGRAM), read(ROOT / STATE)
        binding = read(ROOT / BASE / 'current-binding.json')
        for name in ('service-circuit.json', 'service-recovery.json'):
            path = Path(binding['phase_service_scope']['path']).parent / name
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Service state changed during local work')
        revision = dict(profile='integration-post-r10-local-refresh.v1', user_instruction=LOCAL_USER,
            work=str(LOCAL_WORK), prior_detours=50, additional_consolidated_revision=1,
            live_calls_added=0, additional_task_attempts=0, additional_transport_replacements=0,
            attempts_reset=False, reopened_nodes=[],
            baseline=ref(ROOT, LOCAL_WORK / 'baseline.json'), review=ref(ROOT, LOCAL_WORK / 'review.md'),
            result=ref(ROOT, LOCAL_WORK / 'local-result.json'),
            implementation={p: ref(ROOT, p) for p in sorted(LOCAL_MUTATED - {str(PLAN)})},
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)],
            prior_binding=held[str(BASE / 'current-binding.json')], prior_ledger=held[str(BASE / 'live-calls.json')])
        program = expected_local_refresh(historical_projection(old, local_refresh_projection(baseline)), revision, ROOT)
        validate_program(program, ROOT)
        state = deepcopy(before)
        state['program_hash'] = digest(program)
        now = datetime.now(timezone.utc).isoformat()
        state['events'].append(dict(action='REVIEWED_LOCAL_REFRESH', task_id=None, at_utc=now,
            review=revision['review'], attempts_reset=False, calls_added=0))
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), local_refresh_projection(baseline, mission=True))
        stage = LOCAL_WORK / 'registration-stage'
        save(ROOT / stage / 'program.json', program); save(ROOT / stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), local_refresh=revision)
        reason = ('Local service/refresh repairs and four-question/six-tool preparation are complete. '
            'Next: diagnose P14 invalid_request and 499 cancellation; obtain legitimate Gatecoin refusal review; '
            'qualify service and bind current code before any existing independent live owner. '
            'Reuse the newest 36-account/20-synthesis P14 frontier. No blanket retry, new allowance or legal closure.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-local-refresh-2026-10-16',
            task_id='product-contribution', kind='product_evaluation', outcome='no_advance',
            decision='One reviewed local package after R10; preserve the exhausted 10/20 allocation and all live state.',
            next_task='product-contribution', next_task_reason=reason, recorded_at_utc=now,
            result_evidence=[pointer, revision['review'], revision['result']]))
        save(ROOT / stage / 'mission.json', mission)
        checked = validate_staged_mission(ROOT, stage, mission, 51)
        save(ROOT / LOCAL_WORK / 'registration-check.json', checked)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
    return {'registered': True, 'detours': 51, 'reopened_nodes': [], 'live_calls_added': 0}


def validate_allocation(old, before, revision, authorization):
    previous = old.get(KEY, {})
    expected_detours = previous['prior_detours'] + 1 if previous else 43
    require(type(revision['prior_detours']) is int and revision['prior_detours'] == expected_detours,
        'Repair detour predecessor changed')
    nodes = {n['id']: n for n in old['tasks']}
    reopened = revision['round_reopened_nodes']
    increments = revision['attempt_increments']
    require(isinstance(reopened, list) and len(set(reopened)) == len(reopened)
        and set(reopened) <= set(nodes) and set(increments) <= set(reopened), 'Invalid repair owners')
    require(all(type(v) is int and v > 0 for v in increments.values()), 'Invalid attempt increment')
    require(all(before['tasks'][tid]['status'] != 'SUCCEEDED'
        or tid in ('current-binding', 'continuation-review') for tid in reopened),
        'Successful product owner cannot be resampled')
    require(set(revision['reopened_nodes']) == set(previous.get('reopened_nodes', [])) | set(reopened),
        'Historical reopening scope changed')
    ids = revision['repair_ids']
    require(isinstance(ids, list) and 0 < len(ids) <= authorization['maximum_repairs']
        and len(set(ids)) == len(ids) and all(isinstance(i, str) and i in
            ['R' + str(n) for n in range(1, 11)] for i in ids)
        and set(previous.get('repair_ids', [])) <= set(ids), 'Invalid repair allocation')
    targets = revision['resolved_vetoes']
    require(len({digest(v) for v in targets}) == len(targets), 'Duplicate veto resolution')
    for target in targets:
        require(before.get('continuation_vetoes', []).count(target) == 1
            and target['code'] == 'E_INTEGRITY'
            and target['reason'] == 'Successful account request changed; resampling is forbidden',
            'Veto resolution has a different predecessor')


def validate_local_evidence(root, revision):
    validation, review = (read(root / revision[k]['path']) for k in ('local_validation', 'local_review'))
    require(validation['verdict'] == review['verdict'] == 'PASS'
        and validation['provider_calls'] == review['provider_calls'] == 0
        and validation['ledger_unchanged'] and validation['exact_contract_replay']
        and validation['actual_account_source_measurement'] and validation['finite_reduction']
        and validation['live_answer_and_comparison_population_unchecked'] is True,
        'Missing or overstated repair evidence')
    for pointer in validation['evidence'] + review['evidence']:
        verify(root, pointer)
    for key in ('replay', 'capacity'):
        verify(root, validation[key])
    replay = read(root / validation['replay']['path'])
    prior_program = read(root / revision['prior_program']['path'])
    replay_ledger_hash = revision['prior_ledger']['sha256']
    if prior_program.get(KEY) and not revision['resolved_vetoes']:
        prior_validation = read(root / prior_program[KEY]['local_validation']['path'])
        require(validation['replay'] == prior_validation['replay']
            and validation['capacity'] == prior_validation['capacity']
            and revision['recoveries'] == prior_program[KEY]['recoveries'],
            'Inherited repair evidence changed')
        replay_ledger_hash = prior_validation.get('replay_ledger_sha256',
            read(root / prior_validation['replay']['path'])['ledger']['sha256'])
    require(replay['verdict'] == 'PASS' and replay['provider_calls'] == 0
        and replay['ledger_unchanged'] and replay['ledger']['sha256'] == replay_ledger_hash,
        'Replay differs from exact repair predecessor')
    require({b['question'] for b in replay['branches']} == set(QUESTIONS), 'Incomplete replay population')
    for branch in replay['branches']:
        require(branch['recovery'] == revision['recoveries'][branch['question']]
            and branch['successes'] == len(branch['results']), 'Replay checkpoint mismatch')
    capacity = read(root / validation['capacity']['path'])
    require(capacity['verdict'] == 'PASS' and capacity['provider_calls'] == 0
        and capacity['same_synthesis_representation'] and capacity['finite_reduction']
        and capacity['live_answer_and_comparison_population_unchecked'] is True
        and capacity['all_atomic_rows'] > 0 and capacity['source_review_assignments'] > 0
        and all(m['round_trip'] for m in capacity['measurements']), 'Invalid capacity evidence')
    return validation


def archive_map(baseline, *, mission=False):
    # Only archived code/plan references that actually changed are projected.
    # A fixed list is retained in each round specification before adoption.
    paths = set(baseline['projection_paths']) | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in paths], mission=mission)


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in POINTERS]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        tid = node['id']
        if tid in revision['round_reopened_nodes']:
            number = node['maximum_attempts'] + revision['attempt_increments'].get(tid, 0)
            require(len(before['tasks'][tid]['attempts']) < number, 'No authorized attempt: ' + tid)
            node.update(maximum_attempts=number, deliverable=str(BASE / tid / f'attempt-{number}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_validation']]
    return value


def project_retained_plan(value, root, plan_reference):
    """Resolve repeated exact plan references in a nested sealed comparison."""
    if plan_reference is None or plan_reference['path'] == str(PLAN):
        return value
    verify(root, plan_reference)
    return historical_projection(value, {(str(PLAN), plan_reference['sha256']): plan_reference})


def validate_synthesis_successor(root, revision, spec):
    """A finite reviewed task continuation never resets automatic replacements."""
    from legalmath.interpretation.assurance.phased import synthesis_recovery
    service = revision['service_continuation']
    if service.get('profile') == 'one-explicit-account-continuation.v1':
        from scripts.legal_integration_account_successor import validate
        return validate(root, revision, spec)
    require(spec.get('execution_scope') == 'exact-synthesis-service-continuation'
        and service == spec['service_continuation']
        and revision['synthesis_successors'] == spec['synthesis_successors']
        and revision['successor_replay'] == spec['successor_replay']
        and service['profile'] == 'one-explicit-synthesis-continuation.v1'
        and service['maximum_explicit_redispatches'] == 1
        and service['automatic_replacements'] == 0
        and set(revision['synthesis_successors']) == {service['question']},
        'Unreviewed synthesis service scope')
    prior = read(root / revision['prior_binding']['path'])
    require(service['prior_scope'] == prior['phase_service_scope'], 'Foreign service predecessor')
    for key in ('prior_scope', 'prior_circuit', 'prior_replacements'):
        verify(root, service[key])
    circuit, replacements = (read(root / service[k]['path']) for k in ('prior_circuit', 'prior_replacements'))
    require(circuit['open'] and circuit['stage_hash'] == service['prior_scope']['sha256']
        and service['failed_slot'] in circuit['failed_slots']
        and len(replacements['charges']) == replacements['maximum'] == 48,
        'Successor changed previous circuit or replacement charges')
    q = service['question']
    combined = synthesis_recovery.composite(root, revision['synthesis_successors'][q],
        revision['recoveries'][q], read(root / revision['recoveries'][q]['path'])['input_hash'])
    checkpoint = synthesis_recovery.load(root, combined['synthesis'], combined['input_hash'])
    require(checkpoint['ledger'] == revision['prior_ledger'], 'Successor uses another charge baseline')
    failures = [(key, row) for key, row in checkpoint['rows'].items()
        if row['disposition'] == 'CHARGED_NO_OUTPUT_FAILURE']
    require(len(failures) == 1 and failures[0][0] == service['failed_key']
        and failures[0][1]['slot'] == service['failed_slot'], 'Explicit retry population changed')
    verify(root, revision['successor_replay'])
    replay = read(root / revision['successor_replay']['path'])
    require(replay['verdict'] == 'PASS' and replay['provider_calls'] == 0
        and replay['ledger_unchanged'] and replay['composite'] == revision['synthesis_successors'][q]
        and replay['exact_contracts'] == len(checkpoint['rows'])
        and replay['exact_successes'] == sum(r['disposition'] == 'RETAIN_EXACT_SUCCESS'
            for r in checkpoint['rows'].values()) and replay['production_reconstruction'],
        'Missing actual successor replay')
    rejected = sorted(k for k, row in checkpoint['rows'].items()
        if row['disposition'] == 'COMPLETED_RESPONSE_REJECTED')
    if revision.get('downstream_instruction_profile'):
        from legalmath.interpretation.assurance.phased.downstream_instructions import PROFILE as INSTRUCTIONS
        require(revision['downstream_instruction_profile'] == spec.get('downstream_instruction_profile')
            == checkpoint.get('instruction_profile') == INSTRUCTIONS
            and revision['response_correction_keys'] == spec.get('response_correction_keys') == rejected
            and service.get('maximum_response_corrections') == len(rejected)
            and replay.get('reproduced_rejections') == rejected
            and replay.get('original_evidence_preserved') is True
            and replay.get('first_missing_key') == service['failed_key'],
            'Unreviewed downstream response correction scope')
        edit_keys = sorted(checkpoint.get('edit_corrections', {}))
        if edit_keys:
            from legalmath.interpretation.assurance.phased.downstream_edits import PROFILE as EDIT_PROFILE
            require(len(edit_keys) == 1 and edit_keys == rejected
                and revision.get('downstream_edit_profile') == spec.get('downstream_edit_profile')
                    == checkpoint.get('edit_profile') == EDIT_PROFILE
                and revision.get('response_edit_keys') == spec.get('response_edit_keys') == edit_keys
                and replay.get('wire_schema_preserved') is False
                and replay.get('changed_wire_schema_keys') == edit_keys
                and replay.get('unchanged_wire_schemas') == len(checkpoint['rows']) - 1
                and replay.get('original_rejections_reproduced') == edit_keys
                and replay.get('edit_slots_verified') is True,
                'Unreviewed fixed-path edit schema or predecessor evidence')
        else:
            require(not revision.get('downstream_edit_profile') and not revision.get('response_edit_keys')
                and not spec.get('downstream_edit_profile') and not spec.get('response_edit_keys')
                and not checkpoint.get('edit_profile')
                and not replay.get('changed_wire_schema_keys')
                and replay.get('wire_schema_preserved') is True,
                'Response schema changed outside reviewed edit scope')
    else:
        require(not rejected and not revision.get('response_correction_keys')
            and not service.get('maximum_response_corrections')
            and not revision.get('downstream_edit_profile') and not revision.get('response_edit_keys')
            and not checkpoint.get('edit_profile') and not checkpoint.get('edit_corrections'),
            'Response correction lacks reviewed scope')
    require(set(revision['round_reopened_nodes']) == {'current-binding', 'continuation-review'}
        | {'acquire-' + question for question in QUESTIONS}
        and revision['attempt_increments'] == {'current-binding': 1, 'continuation-review': 1,
            'acquire-' + q: 1}, 'Unreviewed successor task attempts')


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-repair-execution.v1'
        and revision['user_instruction'] == USER and revision['live_calls_added'] == 0
        and revision['attempts_reset'] is False and revision['service_scope_reset'] is False
        and revision['additional_transport_replacements'] == 0, 'Unreviewed repair authority')
    for key in (*POINTERS, 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    authorization = read(root / revision['authorization']['path'])
    verify(root, authorization['baseline'])
    verify(root, authorization['plan'])
    require(authorization['user_instruction'] == USER and authorization['maximum_repairs'] == 10
        and authorization['maximum_additional_task_attempts'] == 20
        and authorization['additional_model_calls'] == authorization['additional_transport_replacements'] == 0,
        'Changed user repair allowance')
    old, before = (read(root / revision[k]['path']) for k in ('prior_program', 'prior_state'))
    validate_allocation(old, before, revision, authorization)
    require(before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled repair baseline')
    baseline = read(root / revision['baseline']['path'])
    frozen = read(root / baseline['frozen_baseline']['path'])
    verify(root, baseline['frozen_baseline'])
    require(baseline['archived'] == frozen['archived'] and baseline['calls'] == frozen['calls']
        and baseline['prior_detours'] == frozen['prior_detours'], 'Changed frozen comparator')
    if not old.get(KEY):
        require(baseline['frozen_baseline'] == authorization['baseline'], 'Changed initial frozen baseline')
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archive bytes')
        verify(root, row['archive'])
    held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    paths = baseline['projection_paths']
    require(len(set(paths)) == len(paths) and set(paths) <= set(held)
        and all(p == str(PLAN) or (p.endswith('.py') and
            (p.startswith('scripts/') or p.startswith('src/legalmath/'))) for p in paths),
        'Projection exceeds reviewed implementation and plan')
    require(revision['prior_program'] == held[str(PROGRAM)] and revision['prior_state'] == held[str(STATE)]
        and revision['prior_binding'] == held[str(BASE / 'current-binding.json')]
        and revision['prior_ledger'] == held[str(BASE / 'live-calls.json')], 'Foreign repair predecessor')
    for path in frozen['dispatch_census']:
        require(all(c['status'] in ('VALIDATED', 'FAILED')
            for c in read(root / held[path]['path'])['calls'].values()), 'Unsettled retained dispatch')
    projected = historical_projection(old, archive_map(baseline))
    with historical_evidence(root, archive_map(baseline)):
        validate_program(projected, root)
    expected = expected_program(projected, before, revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference),
        'Repair altered unrelated graph or limits')
    limits = authorization['baseline_attempt_limits']
    require({n['id'] for n in program['tasks']} == set(limits), 'Repair changed original owners')
    increments = {n['id']: n['maximum_attempts'] - limits[n['id']] for n in program['tasks']}
    require(all(v >= 0 for v in increments.values()) and sum(increments.values()) <= 20
        and revision['cumulative_additional_attempts'] == sum(increments.values()), 'Repair attempt allowance exceeded')
    require(0 < len(revision['repair_ids']) <= 10 and len(set(revision['repair_ids'])) == len(revision['repair_ids']),
        'Repair allowance exceeded or repeated')
    prior_revision = old.get(KEY, {})
    require(set(prior_revision.get('repair_ids', [])) <= set(revision['repair_ids'])
        and revision['prior_detours'] == baseline['prior_detours']
        and revision['additional_consolidated_revision'] == 1, 'Repair history reset')
    spec = read(root / revision['round_spec']['path'])
    if spec.get('execution_scope') == 'local-settlement-only':
        require(set(revision['round_reopened_nodes']) <= {'current-binding', 'continuation-review'}
            and not revision['resolved_vetoes'] and old.get(KEY), 'Local-only repair reopened live work')
        require(all(revision[k] == old[KEY][k] for k in
            ('recoveries', 'common_directories', 'live_directories')), 'Local-only repair changed live checkpoints')
    require(spec['attempt_increments'] == revision['attempt_increments']
        and spec['repair_ids'] == revision['repair_ids']
        and spec['round_reopened_nodes'] == revision['round_reopened_nodes']
        and spec['resolved_vetoes'] == revision['resolved_vetoes']
        and spec['projection_paths'] == baseline['projection_paths'], 'Unreviewed attempt allocation')
    require(set(revision['reopened_nodes']) == set(prior_revision.get('reopened_nodes', []))
        | set(revision['round_reopened_nodes']), 'Historical reopening scope changed')
    validate_local_evidence(root, revision)
    if revision.get('service_continuation'):
        validate_synthesis_successor(root, revision, spec)
    else:
        require(not revision.get('synthesis_successors') and not revision.get('account_successor') and not revision.get('successor_replay'),
            'Synthesis checkpoint requires its reviewed continuation')
    require(revision['downstream_input_profile'] == 'exact-downstream-input-32k.v1', 'Unknown downstream scope')
    from legalmath.interpretation.assurance.phased import account_recovery
    for q in QUESTIONS:
        verify(root, revision['recoveries'][q])
        checkpoint = read(root / revision['recoveries'][q]['path'])
        account_recovery.load(root, revision['recoveries'][q], checkpoint['input_hash'])
        own = not old.get(KEY) or 'acquire-' + q in revision['round_reopened_nodes']
        common = str(Path(revision['work']) / 'live/common' / q) if own else old[KEY]['common_directories'][q]
        live = str(Path(revision['work']) / 'live') if own else old[KEY]['live_directories'][q]
        require(revision['common_directories'][q] == common
            and revision['live_directories'][q] == live, 'Changed round evidence route')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def project_state(before, program, revision, at_utc):
    state = deepcopy(before)
    require(not any(r['status'] == 'RUNNING' for r in state['tasks'].values()), 'Running owner cannot migrate')
    targets = revision['resolved_vetoes']
    for target in targets:
        require(state.get('continuation_vetoes', []).count(target) == 1, 'Exact reviewed veto missing or repeated')
        require(target['code'] == 'E_INTEGRITY' and target['reason'] ==
            'Successful account request changed; resampling is forbidden', 'Unreviewed veto resolution')
        state['continuation_vetoes'].remove(target)
        state.setdefault('resolved_continuation_vetoes', []).append({'veto': target,
            'review': revision['review'], 'evidence': revision['local_validation'], 'at_utc': at_utc,
            'basis': 'Exact successful contracts replayed with no provider calls; content changes refused.',
            'attempts_reset': False, 'calls_added': 0})
    for tid in revision['round_reopened_nodes']:
        row = state['tasks'][tid]
        row.update(status='PENDING', reason='Reviewed bounded repair; previous attempts and failures retained')
        for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'):
            row.pop(key, None)
    state['program_hash'] = digest(program)
    state['events'].append({'action': 'REVIEWED_REPAIR_EXECUTION', 'task_id': None,
        'at_utc': at_utc, 'review': revision['review'], 'attempts_reset': False})
    return state


def candidate():
    pending = read(ROOT / WORK / 'pending-round.json')
    folder = Path(pending['work'])
    require(folder.is_relative_to(WORK), 'Round outside repair allowance')
    baseline = read(ROOT / folder / 'adoption-baseline.json')
    refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / refs[str(PROGRAM)]['path']), read(ROOT / refs[str(STATE)]['path'])
    spec = read(ROOT / folder / 'round-spec.json')
    previous = old.get(KEY, {})
    revision = {'profile': 'integration-repair-execution.v1', 'user_instruction': USER,
        'work': str(folder), 'prior_detours': baseline['prior_detours'], 'additional_consolidated_revision': 1,
        'live_calls_added': 0, 'attempts_reset': False, 'service_scope_reset': False,
        'additional_transport_replacements': 0, 'downstream_input_profile': 'exact-downstream-input-32k.v1',
        **{k: ref(ROOT, p) for k, p in (('authorization', WORK / 'authorization.json'),
            ('review', folder / 'review.md'), ('baseline', folder / 'adoption-baseline.json'),
            ('local_review', folder / 'local-review.json'), ('local_validation', folder / 'local-validation.json'),
            ('round_spec', folder / 'round-spec.json'))},
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
        'round_reopened_nodes': spec['round_reopened_nodes'], 'attempt_increments': spec['attempt_increments'],
        'reopened_nodes': sorted(set(previous.get('reopened_nodes', [])) | set(spec['round_reopened_nodes'])),
        'repair_ids': spec['repair_ids'],
        'cumulative_additional_attempts': previous.get('cumulative_additional_attempts', 0) + sum(spec['attempt_increments'].values()),
        'resolved_vetoes': spec['resolved_vetoes'],
        'recoveries': spec.get('recoveries') or {q: ref(ROOT, folder / ('recovery-' + q + '.json')) for q in QUESTIONS},
        'live_directories': spec.get('live_directories') or {q: str(folder / 'live') for q in QUESTIONS},
        'common_directories': spec.get('common_directories') or {q: str(folder / 'live/common' / q) for q in QUESTIONS},
        **{k: spec[k] for k in ('service_continuation', 'synthesis_successors', 'account_successor', 'successor_replay',
            'downstream_instruction_profile', 'response_correction_keys',
            'downstream_edit_profile', 'response_edit_keys') if k in spec}}
    program = expected_program(historical_projection(old, archive_map(baseline)), before, revision, ROOT)
    validate_program(program, ROOT)
    return program, before, revision


def validate_staged_mission(root, stage, mission, detours):
    from unittest.mock import patch
    from scripts import legal_mission_control as control, legal_integration_master as master
    view = MasterExecution(root, stage / 'program.json', stage / 'state.json').summary()
    original = control.safe_path
    def staged(base, name):
        path = original(base, name)
        return root / stage / 'program.json' if path == root / PROGRAM else path
    with patch.object(control, 'safe_path', staged), patch.object(master, 'summary', lambda _: view):
        checked = control.validate(mission, read(root / DOC / 'tools.json'), root)
    require(checked['detours_since_advance'] == detours, 'Wrong cumulative detour reconciliation')
    return {'verdict': 'PASS', 'detours': detours, 'ready': view['ready'],
        'program': ref(root, stage / 'program.json'), 'state': ref(root, stage / 'state.json')}


def register(*, dry_run=False):
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import LIVE
    folder = Path(read(ROOT / WORK / 'pending-round.json')['work'])
    journal = folder / 'registration.json'
    with ExitStack() as stack:
        for path in (LIVE / 'supervisor.lock', DOC / 'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT / path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / journal).exists():
            if read(ROOT / journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            require(read(ROOT / PROGRAM)[KEY]['work'] == str(folder), 'Registration belongs to another round')
            reconcile_ledger(read(ROOT / PROGRAM))
            return {'registered': True, 'resumed': True}
        program, before, revision = candidate()
        baseline = read(ROOT / revision['baseline']['path'])
        refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC / 'mission.json', BASE / 'current-binding.json', BASE / 'live-calls.json'):
            require(ref(ROOT, path)['sha256'] == refs[str(path)]['sha256'], 'Baseline changed: ' + str(path))
        frozen = read(ROOT / baseline['frozen_baseline']['path'])
        for path in frozen['dispatch_census']:
            require(ref(ROOT, path)['sha256'] == refs[path]['sha256'], 'Dispatch changed during repair')
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before, program, revision, now)
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), archive_map(baseline, mission=True))
        stage = folder / 'registration-stage'
        save(ROOT / stage / 'program.json', program); save(ROOT / stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=pointer, plan=ref(ROOT, PLAN))
        for key, value in program.items():
            if (key in master or key == KEY) and isinstance(value, dict) and 'prior_state' in value and value.get('profile'):
                master[key] = deepcopy(value)
        reason = 'Continue original acquisitions and independent answers, tools and comparisons; repair only evidenced failures within the same ten-repair/twenty-attempt allowance.'
        mission['history'].append({'id': 'integration-repair-execution-' + folder.name,
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed consolidated detour ' + str(revision['prior_detours'] + 1) + '; existing global calls/deadlines and service scope retained.',
            'next_task': 'product-contribution', 'next_task_reason': reason, 'recorded_at_utc': now,
            'result_evidence': [pointer, revision['review'], revision['local_validation']]})
        mission['next_task_reason'] = reason
        save(ROOT / stage / 'mission.json', mission)
        save(ROOT / folder / 'registration-check.json', validate_staged_mission(ROOT, stage, mission, revision['prior_detours'] + 1))
        if dry_run:
            return {'registered': False, 'staged_validation': 'PASS',
                'result': ref(ROOT, folder / 'registration-check.json')}
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    reconcile_ledger(program)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'repairs_allocated': len(revision['repair_ids']),
        'additional_attempts_allocated': revision['cumulative_additional_attempts'], 'detours': revision['prior_detours'] + 1}


def reconcile_ledger(program):
    revision = program[KEY]
    ledger = read(ROOT / WORK / 'repair-ledger.json')
    ledger['allocated_additional_task_attempts'] = {n['id']: n['maximum_attempts'] -
        read(ROOT / WORK / 'authorization.json')['baseline_attempt_limits'][n['id']] for n in program['tasks']
        if n['maximum_attempts'] > read(ROOT / WORK / 'authorization.json')['baseline_attempt_limits'][n['id']]}
    ledger['active_round'] = revision['work']
    for repair in ledger['reserved_repairs']:
        if repair['id'] in revision['repair_ids']:
            repair['status'] = 'LOCALLY_VALIDATED_ADOPTED'
    save(ROOT / WORK / 'repair-ledger.json', ledger)


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM); revision = program[KEY]
    current = read(ROOT / BASE / 'current-binding.json')
    if current.get('review') == revision['review'] and current.get('program') == ref(ROOT, PROGRAM):
        provider().check()
        return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'resumed': True}
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'], 'Changed binding')
    require(ref(ROOT, BASE / 'live-calls.json')['sha256'] == revision['prior_ledger']['sha256'], 'Changed charges')
    prior = read(ROOT / revision['prior_binding']['path'])
    scope = prior['phase_service_scope']; verify(ROOT, scope)
    local_only = read(ROOT / revision['round_spec']['path']).get('execution_scope') == 'local-settlement-only'
    successor = revision.get('service_continuation')
    require(local_only or successor or not read(ROOT / Path(scope['path']).parent / 'service-circuit.json')['open'],
        'Shared service circuit is open')
    binding = deepcopy(prior)
    save(directory / 'ledger-before.json', read(ROOT / BASE / 'live-calls.json'))
    binding.update(user_instruction=USER, review=revision['review'], predecessor=revision['prior_binding'],
        phase_service_predecessor=revision['prior_binding'],
        ledger_before=ref(ROOT, directory / 'ledger-before.json'), program=ref(ROOT, PROGRAM))
    if successor:
        from scripts.legal_integration_complete_account_capacity import retain_successor_files
        from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY
        validate_synthesis_successor(ROOT, revision, read(ROOT / revision['round_spec']['path']))
        scope_value = {'profile': 'reviewed-shared-phase-service.v1',
            'grant_hash': digest(read(ROOT / BASE / 'live-grant.json')),
            'review': revision['review'], 'prior_scope': successor['prior_scope'],
            'prior_circuit': successor['prior_circuit'], 'prior_replacements': successor['prior_replacements'],
            'additional_replacements': 0, 'explicit_continuation': successor,
            'requalification': 'One exact failed request; first terminal failure closes the successor.'}
        scope = retain_successor_files(ROOT, Path(revision['work']) / 'live/service', scope_value,
            read(ROOT / successor['prior_replacements']['path']), successor['prior_circuit'])
        binding.pop('phase_service_predecessor', None)
        binding.update(phase_service_scope=scope, service_recovery_policy=SERVICE_SINGLE_DISPATCH_POLICY)
    binding['bindings'] = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in sorted((ROOT / 'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in (PROGRAM, PLAN, Path(revision['review']['path']),
        Path(program['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in POINTERS] + list(revision['recoveries'].values()) + [scope]
    if successor:
        binding['bindings'] += list(revision.get('synthesis_successors', {}).values()) + [revision['successor_replay']]
        if revision.get('account_successor'):
            binding['bindings'].append(revision['account_successor'])
        binding['bindings'] += [successor[k] for k in ('prior_scope', 'prior_circuit', 'prior_replacements')]
    held = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        held[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(held.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'service_scope': scope,
        'explicit_successor': bool(successor),
        '_conclusion': 'Current repairs bound; old scopes, all charges, zero automatic replacements and original deadline retained.'}


def verification(directory=None):
    program = read(ROOT / PROGRAM); validate_program(program, ROOT)
    revision = program[KEY]
    before, state = read(ROOT / revision['prior_state']['path']), read(ROOT / STATE)
    prior, ledger = read(ROOT / revision['prior_ledger']['path']), read(ROOT / BASE / 'live-calls.json')
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Historical charges changed')
    require(all(state['tasks'][k]['attempts'][:len(v['attempts'])] == v['attempts']
        for k, v in before['tasks'].items()), 'Historical attempts changed')
    local = program.get('local_refresh')
    if local:
        require(state['tasks'] == read(ROOT / local['prior_state']['path'])['tasks'],
            'Local refresh changed owner attempts or outcomes')
        require(ref(ROOT, BASE / 'live-calls.json')['sha256'] == local['prior_ledger']['sha256']
            and ref(ROOT, BASE / 'current-binding.json')['sha256'] == local['prior_binding']['sha256'],
            'Local refresh changed calls or live binding')
        held = {r['previous']['path']: r['archive'] for r in read(ROOT / local['baseline']['path'])['archived']}
        binding = read(ROOT / BASE / 'current-binding.json')
        for name in ('service-circuit.json', 'service-recovery.json'):
            path = Path(binding['phase_service_scope']['path']).parent / name
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Local refresh changed service state')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    from scripts.legal_integration_acceptance import evaluation_summary
    evaluations = evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT)
    result = {'profile': 'integration-repair-execution-verification.v1',
        'calls': len(ledger['calls']), 'historical_calls': 41,
        'detours': local['prior_detours'] + 1 if local else revision['prior_detours'] + 1,
        'repairs_allocated': len(revision['repair_ids']), 'additional_attempts_allocated': revision['cumulative_additional_attempts'],
        'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'tools_fully_evaluated': evaluations['selected_tools_fully_evaluated'],
        'original_questions': list(QUESTIONS), 'original_obligations': 46, 'original_readings': 35,
        'integration_complete': False, '_conclusion': 'Repair and accounting verified; original legal acceptance remains required.'}
    if local:
        result.update(local_refresh_verified=True, live_binding_current=False,
            additional_local_packages=1, additional_live_task_attempts=0)
    save((directory or ROOT / (local or revision)['work']) / 'verification.json', result)
    return result
