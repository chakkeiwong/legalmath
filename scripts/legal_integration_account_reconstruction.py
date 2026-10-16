"""Exact corrected-success recovery in the existing integration master.

One reviewed local repair; no service reset, qualification resampling or grant.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives

WORK = Path('artifacts/legal-mission-control/2026-10-15/account-reconstruction')
REVIEW = WORK / 'review.md'
KEY = 'account_reconstruction_repair'
USER = 'refresh the master program, continue the execution'
REOPEN = ('current-binding', 'acquire-gatecoin', 'continuation-review')
POINTERS = ('review', 'baseline', 'local_review', 'local_validation', 'diagnosis')
PROJECTED = {str(PLAN), 'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_master.py', 'scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py'}


def projected_archives(baseline, *, mission=False):
    paths = PROJECTED | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in paths], mission=mission)


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
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-account-reconstruction-repair.v1'
        and revision['prior_detours'] == 41 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['attempts_reset'] is False
        and revision['user_instruction'] == USER and revision['reopened_nodes'] == list(REOPEN)
        and revision['qualification_logical_calls'] == 0
        and revision['additional_transport_replacements'] == 0
        and revision['service_scope_reset'] is False, 'Unreviewed account reconstruction repair')
    for key in (*POINTERS, 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('account_instruction_repair') and not old.get(KEY)
        and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Unsettled reconstruction baseline')
    require(len(read(root / revision['prior_ledger']['path'])['calls']) == 2130, 'Lost prior charges')
    baseline = read(root / revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed archive bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, projected_archives(baseline))
    validate_program(projected, root)
    require(program == expected_program(projected, before, revision, root, plan_reference=plan_reference),
        'Reconstruction changed unrelated graph or resources')
    local, validation = (read(root / revision[k]['path']) for k in ('local_review', 'local_validation'))
    require(local['verdict'] == validation['verdict'] == 'PASS'
        and local['provider_calls'] == validation['provider_calls'] == 0
        and validation['ledger_unchanged'] and validation['exact_contracts'] == 364
        and validation['corrected_successes'] == 1
        and {r['question'] for r in validation['branches']} == set(QUESTIONS)
        and all(r['status'] == 'NEW_REQUEST_BOUNDARY' for r in validation['branches']),
        'Incomplete exact reconstruction validation')
    for pointer in local['evidence'] + validation['evidence']:
        verify(root, pointer)
    require(revision['recoveries'] == old['account_instruction_repair']['recoveries'],
        'Successful recovery population changed')
    nodes = {n['id']: n for n in program['tasks']}
    for tid in ('semantic-preflight', 'account-qualification', 'campaign'):
        require(before['tasks'][tid]['status'] == 'SUCCEEDED' and tid not in REOPEN,
            'Successful qualification or campaign must remain retained')
    for q, used, ceiling in (('p10', 5, 6), ('p14', 6, 7), ('evidence', 5, 6), ('gatecoin', 7, 8)):
        require(len(before['tasks']['acquire-' + q]['attempts']) == used
            and nodes['acquire-' + q]['maximum_attempts'] == ceiling, 'Unexpected acquisition allowance')
        verify(root, revision['recoveries'][q])
    return {n['id']: n['maximum_attempts'] for n in program['tasks']}


def registration_candidate():
    baseline = read(ROOT / WORK / 'baseline.json')
    refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    old, before = read(ROOT / refs[str(PROGRAM)]['path']), read(ROOT / refs[str(STATE)]['path'])
    revision = {'profile': 'integration-account-reconstruction-repair.v1', 'prior_detours': 41,
        'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
        'user_instruction': USER, 'review': ref(ROOT, REVIEW),
        'baseline': ref(ROOT, WORK / 'baseline.json'), 'local_review': ref(ROOT, WORK / 'local-review.json'),
        'local_validation': ref(ROOT, WORK / 'local-validation.json'), 'diagnosis': ref(ROOT, WORK / 'diagnosis.json'),
        'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
        'prior_binding': refs[str(BASE / 'current-binding.json')], 'prior_ledger': refs[str(BASE / 'live-calls.json')],
        'reopened_nodes': list(REOPEN), 'qualification_logical_calls': 0,
        'additional_transport_replacements': 0, 'service_scope_reset': False,
        'recoveries': deepcopy(old['account_instruction_repair']['recoveries'])}
    program = expected_program(historical_projection(old, projected_archives(baseline)), before, revision, ROOT)
    validate_program(program, ROOT)
    return program, before, revision


def validate_staged_mission(root, stage, mission):
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
    require(checked['detours_since_advance'] == 42, 'Candidate detour reconciliation differs')
    return {'verdict': 'PASS', 'detours': 42, 'ready': summary['ready'],
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
            row.update(status='PENDING', reason='Reviewed exact corrected-success recovery; preserve prior attempts')
            row.pop('result', None)
            for key in ('dispatch_status', 'prerequisite_evidence', 'shared_scope'):
                row.pop(key, None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_ACCOUNT_RECONSTRUCTION_REPAIR', 'task_id': None,
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
        reason = ('Resume original independent acquisitions using exact saved successes and retained qualifications; '
            'continue own answer/tool branches and completion reviews without resetting resources.')
        mission['history'].append({'id': 'integration-master-account-reconstruction-repair-2026-10-15',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed consolidated detour 42 for corrected-success reconstruction; no new global allowance.',
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
    return {'registered': True, 'detours': 42, 'reopened_nodes': list(REOPEN)}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    program = read(ROOT / PROGRAM)
    revision = program[KEY]
    require(ref(ROOT, BASE / 'current-binding.json')['sha256'] == revision['prior_binding']['sha256'],
        'Binding differs from reviewed predecessor')
    prior = read(ROOT / revision['prior_binding']['path'])
    binding = deepcopy(prior)
    # Explicitly inherit the authentic prior scope: no new circuit or reserve.
    scope_ref = prior['phase_service_scope']
    scope_dir = Path(scope_ref['path']).parent
    circuit = ref(ROOT, scope_dir / 'service-circuit.json')
    replacements = ref(ROOT, scope_dir / 'service-recovery.json')
    require(not read(ROOT / circuit['path'])['open']
        and len(read(ROOT / replacements['path'])['charges']) == 48, 'Service prerequisite changed')
    save(directory / 'ledger-before.json', read(ROOT / BASE / 'live-calls.json'))
    binding.update(user_instruction=USER, review=revision['review'], predecessor=revision['prior_binding'],
        phase_service_predecessor=revision['prior_binding'], ledger_before=ref(ROOT, directory / 'ledger-before.json'),
        program=ref(ROOT, PROGRAM))
    binding['bindings'] = [ref(ROOT, p) for p in sorted((ROOT / 'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in sorted((ROOT / 'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT, p) for p in (PROGRAM, PLAN, REVIEW,
        Path(program['prerequisite_repair']['source']['path']), BASE / 'campaign-routing.toml',
        Path('requirements-context.lock'), Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in POINTERS]
    binding['bindings'] += list(revision['recoveries'].values()) + [scope_ref, circuit, replacements]
    old = {(r['previous']['path'], r['previous']['sha256']): r for r in prior['historical_archives']}
    for row in read(ROOT / revision['baseline']['path'])['archived']:
        old[(row['previous']['path'], row['previous']['sha256'])] = row
    binding['historical_archives'] = list(old.values())
    save(ROOT / BASE / 'current-binding.json', binding)
    provider().check()
    return {'binding': ref(ROOT, BASE / 'current-binding.json'), 'additional_replacements': 0,
        '_conclusion': 'Exact account recovery bound; successful qualifications and original service scope retained.'}


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
    for tid in ('semantic-preflight', 'account-qualification', 'campaign'):
        require(state['tasks'][tid] == before['tasks'][tid], 'Successful retained owner changed: ' + tid)
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    evaluations = evaluation_summary(read(ROOT / DOC / 'tools.json'), ROOT)
    result = {'profile': 'account-reconstruction-repair-verification.v1', 'calls': len(ledger['calls']),
        'historical_calls': 41, 'detours': 42, 'prior_calls_preserved': True, 'prior_attempts_preserved': True,
        **{k: view[k] for k in ('execution', 'ready', 'running', 'blocked')},
        'original_questions': list(QUESTIONS), 'original_obligations': 46, 'original_readings': 35,
        'integration_complete': False, 'tools_fully_evaluated': evaluations['selected_tools_fully_evaluated'],
        'remaining': ['Complete source-grounded original accounts and answers',
            'Matched actual answer effects of six selected tools', 'Dated applicability and later treatment'],
        '_conclusion': 'Exact recovery accounting verified; original legal answers and matched effects remain required.'}
    save((directory or ROOT / WORK) / 'verification.json', result)
    return result
