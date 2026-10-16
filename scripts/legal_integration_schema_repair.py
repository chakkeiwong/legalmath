"""One finite response-schema amendment of the existing integration master."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-15/schema-continuation')
REVIEW = Path('docs/plans/legal-integration-schema-continuation-2026-10-15.md')
KEY = 'response_schema_repair'
USER = 'refresh the plan. continue'
REOPEN = ('current-binding', 'semantic-preflight', 'account-qualification', 'continuation-review')


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in
        ('review', 'baseline', 'local_review', 'qualification_inputs', 'positive_replay')]
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for node in value['tasks']:
        if node['id'] in REOPEN:
            number = len(before['tasks'][node['id']]['attempts']) + 1
            node.update(maximum_attempts=number,
                deliverable=str(BASE / node['id'] / f'attempt-{number}' / 'result.json'))
            node['inputs'] += [revision['review'], revision['local_review']]
        if node['id'] == 'semantic-preflight':
            node['acceptance'] = 'Exact retained positive revalidates; fresh adverse response rejects unsupported answer with genuine context identities.'
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-response-schema-repair.v1'
        and revision['prior_detours'] == 37 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['service_scope_reset'] is False
        and revision['qualification_logical_calls'] == {'reviewer': 1, 'account': 3}
        and revision['service_recovery_policy'] == SERVICE_CONTINUATION_POLICY,
        'Unreviewed response-schema continuation')
    for key in ('review', 'baseline', 'local_review', 'qualification_inputs', 'positive_replay',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    before = read(root / revision['prior_state']['path'])
    old = read(root / revision['prior_program']['path'])
    require(old.get('account_capacity_repair') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled schema baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2086, 'Lost prior charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archived bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, archives(baseline['archived']))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Schema correction changed unrelated graph or limits')
    local = read(root / revision['local_review']['path'])
    require(local['verdict'] == 'PASS' and local['provider_calls'] == 0, 'Unreviewed schema correction')
    for pointer in local['evidence']:
        verify(root, pointer)
    positive = read(root / revision['positive_replay']['path'])
    require(positive['positive_passed'] and positive['new_provider_calls'] == 0, 'Invalid retained positive')
    for pointer in positive['evidence']:
        verify(root, pointer)
    for q in QUESTIONS:
        task = next(n for n in program['tasks'] if n['id'] == 'acquire-' + q)
        require(len(before['tasks']['acquire-' + q]['attempts']) == 4
            and task['maximum_attempts'] == 5, 'Acquisition allowance changed')
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
        revision = {'profile': 'integration-response-schema-repair.v1', 'prior_detours': 37,
            'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
            'user_instruction': USER, 'review': ref(ROOT, REVIEW), 'baseline': ref(ROOT, WORK / 'baseline.json'),
            'local_review': ref(ROOT, WORK / 'local-review.json'),
            'qualification_inputs': ref(ROOT, WORK / 'qualification-inputs.json'),
            'positive_replay': ref(ROOT, WORK / 'positive-replay.json'),
            'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
            'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
            'reopened_nodes': list(REOPEN), 'service_scope_reset': False,
            'qualification_logical_calls': {'reviewer': 1, 'account': 3},
            'service_recovery_policy': SERVICE_CONTINUATION_POLICY}
        program = expected_program(historical_projection(old, archives(baseline['archived'])), state, revision, ROOT)
        validate_program(program, ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING', reason='Reviewed response-schema correction; original acquisition allowance preserved')
            state['tasks'][tid].pop('result', None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_RESPONSE_SCHEMA_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT / DOC / 'mission.json'), archives(baseline['archived'], mission=True))
        stage = ROOT / WORK / 'registration-stage'
        save(stage / 'program.json', program)
        save(stage / 'state.json', state)
        pointer = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage / 'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=pointer, plan=ref(ROOT, PLAN))
        master[KEY] = revision
        for key in ('account_capacity_repair', 'route_context_repair', 'phased_acquisition_repair',
                    'canary_validation_repair', 'retry_delay_repair', 'service_continuation',
                    'execution_recovery', 'prerequisite_repair', 'execution_refresh'):
            master[key] = program[key]
        reason = 'Qualify exact account inputs and genuine reviewer context identities independently; continue original acquisitions, answers and tools without resetting attempts.'
        mission['history'].append({'id': 'integration-master-response-schema-repair-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Count the reproduced response-contract correction as detour 38; preserve prior charges and attempts.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [pointer, revision['review'], revision['positive_replay'], revision['local_review']]})
        mission['next_task_reason'] = reason
        save(stage / 'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage / name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC / 'mission.json', 'mission.json'))]
        save(ROOT / journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 38, 'reopened_nodes': list(REOPEN)}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM)
    revision = program[KEY]
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
        Path(program['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in ('baseline', 'local_review', 'qualification_inputs', 'positive_replay')]
    binding['bindings'] += list(program['account_capacity_repair']['recoveries'].values()) + [prior['phase_service_scope']]
    for row in read(ROOT / revision['qualification_inputs']['path'])['cases']:
        binding['bindings'] += [row[k] for k in ('envelope', 'request')]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'service_scope_preserved': True,
        '_conclusion': 'Response-schema correction bound; source, strict local validation, grant and circuit preserved.'}


def verification(directory=None):
    program = read(ROOT / PROGRAM)
    validate_program(program, ROOT)
    revision = program[KEY]
    state, before = read(ROOT / STATE), read(ROOT / revision['prior_state']['path'])
    ledger, old = read(ROOT / BASE / 'live-calls.json'), read(ROOT / revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])] == old['calls'], 'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts']
        for tid, row in before['tasks'].items()), 'Prior attempts changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    result = {'profile': 'response-schema-repair-verification.v1', 'calls': len(ledger['calls']),
        'detours': 38, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'integration_complete': False, 'tools_fully_evaluated': 0,
        '_conclusion': 'Schema continuation accounting verified; legal answers and matched tool effects remain required.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
