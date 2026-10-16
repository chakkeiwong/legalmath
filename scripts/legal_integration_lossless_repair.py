"""One finite, reviewed lossless-account continuation of the existing master."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-15/lossless-recovery')
REVIEW = Path('docs/plans/legal-integration-lossless-recovery-2026-10-15.md')
KEY = 'lossless_account_repair'
USER = 'refresh the plan. continue'
REOPEN = ('current-binding', 'account-qualification', 'continuation-review',
    *('acquire-' + q for q in QUESTIONS))


def projected_archives(baseline, *, mission=False):
    rows = [r for r in baseline['archived'] if r['previous']['path'] in baseline['projected_paths']]
    return archives(rows, mission=mission)


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in
        ('review', 'baseline', 'local_review', 'qualification_inputs', 'local_validation')]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        if node['id'] in REOPEN:
            n = len(before['tasks'][node['id']]['attempts']) + 1
            node.update(maximum_attempts=n, deliverable=str(BASE / node['id'] / f'attempt-{n}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-lossless-account-repair.v1'
        and revision['prior_detours'] == 38 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['qualification_logical_calls'] == 3
        and revision['additional_transport_replacements'] == 0
        and revision['service_recovery_policy'] == SERVICE_SINGLE_DISPATCH_POLICY,
        'Unreviewed lossless continuation')
    for key in ('review', 'baseline', 'local_review', 'qualification_inputs', 'local_validation',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    before, old = read(root / revision['prior_state']['path']), read(root / revision['prior_program']['path'])
    require(old.get('response_schema_repair') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled lossless baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2112, 'Lost baseline charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archived bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, projected_archives(baseline))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Lossless correction changed unrelated graph or limits')
    local = read(root / revision['local_review']['path'])
    require(local['verdict'] == 'PASS' and local['provider_calls'] == 0, 'Unreviewed local correction')
    for pointer in local['evidence']:
        verify(root, pointer)
    validation = read(root / revision['local_validation']['path'])
    require(validation['population'] == 227 and validation['exact_reconstruction']
        and validation['retained_response_roundtrips'] == 14
        and sum(r['retained_successes'] for r in validation['recoveries'].values()) == 359,
        'Incomplete population or success preservation')
    require(set(revision['recoveries']) == set(QUESTIONS), 'Lost original question')
    for q, pointer in revision['recoveries'].items():
        verify(root, pointer)
        require(len(before['tasks']['acquire-' + q]['attempts']) == 5
            and next(n for n in program['tasks'] if n['id'] == 'acquire-' + q)['maximum_attempts'] == 6,
            'Acquisition must preserve five spent attempts and one bounded continuation')
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


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
        old, state = read(ROOT / PROGRAM), read(ROOT / STATE)
        revision = {'profile': 'integration-lossless-account-repair.v1', 'prior_detours': 38,
            'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
            'user_instruction': USER, 'review': ref(ROOT, REVIEW), 'baseline': ref(ROOT, WORK / 'baseline.json'),
            'local_review': ref(ROOT, WORK / 'local-review.json'),
            'local_validation': ref(ROOT, WORK / 'local-validation.json'),
            'qualification_inputs': ref(ROOT, WORK / 'qualification-inputs.json'),
            'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
            'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
            'reopened_nodes': list(REOPEN), 'qualification_logical_calls': 3,
            'additional_transport_replacements': 0, 'service_recovery_policy': SERVICE_SINGLE_DISPATCH_POLICY,
            'recoveries': {q: ref(ROOT, WORK / ('recovery-' + q + '.json')) for q in QUESTIONS}}
        program = expected_program(historical_projection(old, projected_archives(baseline)), state, revision, ROOT)
        validate_program(program, ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING', reason='Reviewed lossless recovery; preserve all spent attempts')
            state['tasks'][tid].pop('result', None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_LOSSLESS_ACCOUNT_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), projected_archives(baseline, mission=True))
        stage = ROOT / WORK / 'registration-stage'
        save(stage / 'program.json', program); save(stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']; master.update(program=pointer, plan=ref(ROOT, PLAN))
        master[KEY] = revision
        for key in ('response_schema_repair', 'account_capacity_repair', 'route_context_repair',
                    'phased_acquisition_repair', 'canary_validation_repair', 'retry_delay_repair',
                    'service_continuation', 'execution_recovery', 'prerequisite_repair', 'execution_refresh'):
            master[key] = program[key]
        reason = 'Qualify lossless account encoding once, reuse 359 valid responses, defer known service outages and continue independently eligible original answers and tools.'
        mission['history'].append({'id': 'integration-master-lossless-account-repair-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Count the consolidated lossless/recovery/deferral repair as detour 39; preserve attempts, charges and spent reserve.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['local_validation'], revision['local_review']]})
        mission['next_task_reason'] = reason; save(stage / 'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 39, 'reopened_nodes': list(REOPEN)}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM); revision = program[KEY]
    prior = read(ROOT / revision['prior_binding']['path'])
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    grant = read(ROOT / BASE / 'live-grant.json')
    previous_scope = prior['phase_service_scope']
    service_dir = Path(previous_scope['path']).parent
    previous_circuit = ref(ROOT, service_dir / 'service-circuit.json')
    previous_replacements = ref(ROOT, service_dir / 'service-recovery.json')
    circuit = read(ROOT / previous_circuit['path']); replacements = read(ROOT / previous_replacements['path'])
    require(circuit['open'] and len(replacements['charges']) == replacements['maximum'] == 48,
        'Service settlement differs from reviewed open circuit')
    scope_dir = WORK / 'live/service'
    scope = {'profile': 'reviewed-shared-phase-service.v1', 'grant_hash': digest(grant),
        'review': revision['review'], 'prior_scope': previous_scope, 'prior_circuit': previous_circuit,
        'prior_replacements': previous_replacements, 'additional_replacements': 0,
        'requalification': 'One reviewed qualification and sixth acquisition; first terminal service failure defers remaining live owners.'}
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
        preflight_stage_maximum=3)
    binding['bindings'] = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in sorted((ROOT / 'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in (PROGRAM, PLAN, REVIEW,
        Path(program['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in ('baseline', 'local_review', 'qualification_inputs', 'local_validation')]
    binding['bindings'] += list(revision['recoveries'].values()) + [scope_ref, previous_scope, previous_circuit, previous_replacements]
    for row in read(ROOT / revision['qualification_inputs']['path'])['cases']:
        binding['bindings'] += [row[k] for k in ('envelope', 'request')]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'prior_replacements_preserved': 48,
        'additional_replacements': 0, '_conclusion': 'Exact lossless recovery bound; one finite service requalification, no new replacement reserve.'}


def verification(directory=None):
    program = read(ROOT / PROGRAM); validate_program(program, ROOT); revision = program[KEY]
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, old = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])] == old['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    result = {'profile': 'lossless-account-repair-verification.v1', 'calls': len(ledger['calls']),
        'detours': 39, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'integration_complete': False, 'tools_fully_evaluated': 0,
        '_conclusion': 'Lossless continuation accounting verified; original answers and matched tool effects remain required.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
