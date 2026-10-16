"""Finite account recovery amendment with independent reviewer qualification."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution, task
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_route_repair import WORK as C
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-15/account-continuation')
REVIEW = Path('docs/plans/legal-integration-account-continuation-2026-10-15.md')
AUDIT = C / 'account-recovery-audit'
ACCOUNT = C / 'account-contract-candidate'
USER = 'refresh the plan. continue'
NEW = 'account-qualification'
REOPEN = ('current-binding', 'semantic-preflight', 'continuation-review',
          *('acquire-' + q for q in QUESTIONS))


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value['account_capacity_repair'] = revision
    value['protected_evidence'] += [revision[k] for k in
        ('review', 'baseline', 'local_review', 'population', 'qualification_inputs')]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        tid = node['id']
        if tid in REOPEN:
            n = len(before['tasks'][tid]['attempts']) + 1
            node.update(maximum_attempts=n, deliverable=str(BASE / tid / f'attempt-{n}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
        if tid.startswith('acquire-'):
            node['requires'] = list(dict.fromkeys([*node['requires'], NEW]))
        if tid == 'semantic-preflight':
            node['acceptance'] = 'Conditional answer accepted and unsupported definitive answer rejected under clarified review-context scope; prior adverse controls retained.'
        if tid == 'continuation-review':
            node['after'] = list(dict.fromkeys([*node['after'], NEW, *('acquire-' + q for q in QUESTIONS)]))
    node = task(NEW, ['current-binding'], agent=True,
        deliverable='Largest actual account combination and two near-cap exception/missing-authority controls pass exact schema, source and conditional checks.')
    node.update(maximum_attempts=1, inputs=[revision['review'], revision['qualification_inputs']],
                deliverable=str(BASE / NEW / 'attempt-1/result.json'))
    value['tasks'].append(node)
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program['account_capacity_repair']
    require(revision['profile'] == 'integration-account-capacity-repair.v1'
        and revision['prior_detours'] == 36 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['new_nodes'] == [NEW] and revision['service_scope_reset'] is False
        and revision['qualification_logical_calls'] == {'reviewer': 2, 'account': 3}
        and revision['service_recovery_policy'] == SERVICE_CONTINUATION_POLICY,
        'Unreviewed account continuation')
    for key in ('review', 'baseline', 'local_review', 'population', 'qualification_inputs',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    before, old = read(root / revision['prior_state']['path']), read(root / revision['prior_program']['path'])
    require(old.get('route_context_repair') and not old.get('account_capacity_repair')
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled account baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2080, 'Lost baseline charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archive')
        verify(root, row['archive'])
    projected = historical_projection(old, archives(baseline['archived']))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Account continuation changed unrelated graph or limits')
    require(all(len(before['tasks']['acquire-' + q]['attempts']) == 4 for q in QUESTIONS),
        'Acquisition baseline differs')
    local = read(root / revision['local_review']['path'])
    require(local['verdict'] == 'PASS' and local['provider_calls'] == 0, 'Unreviewed local adoption')
    for pointer in local['evidence']:
        verify(root, pointer)
    population = read(root / revision['population']['path'])
    require(sum(r['revalidated_successes'] for r in population['questions']) == 346
        and sum(r['measured_requests'] for r in population['questions']) == 224
        and all(set(r['measurements_status']) == {'FITS'} for r in population['questions']),
        'Final population is not qualified locally')
    require(set(revision['recoveries']) == set(QUESTIONS), 'Lost independent question')
    for pointer in revision['recoveries'].values():
        verify(root, pointer)
    return {t['id']: t['maximum_attempts'] for t in program['tasks']}


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
        revision = {'profile': 'integration-account-capacity-repair.v1', 'prior_detours': 36,
            'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
            'user_instruction': USER, 'review': ref(ROOT, REVIEW), 'baseline': ref(ROOT, WORK / 'baseline.json'),
            'local_review': ref(ROOT, WORK / 'local-review.json'), 'population': ref(ROOT, AUDIT / 'final-population.json'),
            'qualification_inputs': ref(ROOT, WORK / 'qualification-inputs.json'),
            'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
            'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
            'reopened_nodes': list(REOPEN), 'new_nodes': [NEW], 'service_scope_reset': False,
            'qualification_logical_calls': {'reviewer': 2, 'account': 3},
            'service_recovery_policy': SERVICE_CONTINUATION_POLICY,
            'recoveries': {q: ref(ROOT, ACCOUNT / ('recovery-' + q + '.json')) for q in QUESTIONS}}
        program = expected_program(historical_projection(old, archives(baseline['archived'])), state, revision, ROOT)
        validate_program(program, ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING', reason='Reviewed targeted account and conditional-review continuation')
            state['tasks'][tid].pop('result', None)
        state['tasks'][NEW] = {'status': 'PENDING', 'attempts': []}
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_ACCOUNT_CAPACITY_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), archives(baseline['archived'], mission=True))
        stage = ROOT / WORK / 'registration-stage'
        save(stage / 'program.json', program)
        save(stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=pointer, plan=ref(ROOT, PLAN), account_capacity_repair=revision)
        for key in ('route_context_repair', 'phased_acquisition_repair', 'canary_validation_repair',
                    'retry_delay_repair', 'service_continuation', 'execution_recovery', 'prerequisite_repair', 'execution_refresh'):
            master[key] = program[key]
        reason = 'Qualify account protocol and conditional review independently; recover named failed accounts with exact success reuse, then continue eligible original answers and tools.'
        mission['history'].append({'id': 'integration-master-account-capacity-repair-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Count the whole account contract/capacity package as detour 37; preserve prior charges and attempts.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['population'], revision['local_review']]})
        mission['next_task_reason'] = reason
        save(stage / 'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 37, 'reopened_nodes': list(REOPEN), 'new_nodes': [NEW]}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    revision = read(ROOT / PROGRAM)['account_capacity_repair']
    prior = read(ROOT / revision['prior_binding']['path'])
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    binding = deepcopy(prior)
    save(directory / 'ledger-before.json', read(ROOT / BASE / 'live-calls.json'))
    binding.update(user_instruction=USER, review=revision['review'], predecessor=revision['prior_binding'],
        phase_service_predecessor=revision['prior_binding'], ledger_before=ref(ROOT, directory / 'ledger-before.json'),
        program=ref(ROOT, PROGRAM), preflight_stage_maximum=15)
    binding['bindings'] = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in sorted((ROOT / 'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in (PROGRAM, PLAN, REVIEW,
        Path(read(ROOT / PROGRAM)['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in ('baseline', 'local_review', 'population', 'qualification_inputs')]
    binding['bindings'] += list(revision['recoveries'].values()) + [prior['phase_service_scope']]
    inputs = read(ROOT / revision['qualification_inputs']['path'])
    for row in inputs['cases']:
        binding['bindings'] += [row[k] for k in ('envelope', 'request')]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'service_scope_preserved': True,
        '_conclusion': 'Targeted account recovery and conditional review bound; grant, circuit and old successes preserved.'}


def verification(directory=None):
    program = read(ROOT / PROGRAM)
    validate_program(program, ROOT)
    revision = program['account_capacity_repair']
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, old = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])] == old['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    result = {'profile': 'account-capacity-repair-verification.v1', 'calls': len(ledger['calls']),
        'detours': 37, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'integration_complete': False, 'tools_fully_evaluated': 0,
        '_conclusion': 'Account continuation accounting verified; original answer and matched tool effects remain required.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
