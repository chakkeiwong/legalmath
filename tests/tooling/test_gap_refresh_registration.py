"""A proved constructor repair cannot erase failures or renew shared authority."""
from copy import deepcopy

import pytest

from scripts import legal_integration_gap_refresh as frontier
from scripts.legal_integration_phased_live import active_live, question_live, common_directory
from scripts.legal_mission_execution import ref, save, digest, Refused


def fixture(root, monkeypatch):
    tasks = [{'id': tid, 'maximum_attempts': maximum} for tid, maximum in
        [('acquire-p10', 7), ('acquire-evidence', 6), ('acquire-p14', 10),
         ('acquire-gatecoin', 13), ('baseline-p10', 2)]]
    old = {'tasks': tasks, 'protected_evidence': [], 'deadline_utc': 'retained',
        'global_call_ceiling': 8100, 'delayed_service_recovery': {'retained': True},
        'repair_execution': {'repair_ids': ['R' + str(n) for n in range(1, 11)],
                            'cumulative_additional_attempts': 19}}
    save(root / 'failed-receipt.json', {'retained': True})
    veto = dict(code='E_INTEGRITY', reason=frontier.VETO_REASON,
                evidence=[ref(root, 'failed-receipt.json')])
    unrelated_veto = dict(code='E_AUTHORITY', reason='Unrelated unresolved dispatch')
    states = {n['id']: {'status': 'FAILED', 'attempts': [{'number': i}
        for i in range(1, n['maximum_attempts'] + 1)]} for n in tasks[:4]}
    states['acquire-evidence'] = {'status': 'PENDING', 'attempts': [{'number': i} for i in range(1, 6)]}
    states['baseline-p10'] = {'status': 'PENDING', 'attempts': []}
    before = dict(program_hash=digest(old), tasks=states, events=[],
        continuation_vetoes=[veto, unrelated_veto],
        resolved_continuation_vetoes=[{'veto': {'reason': 'older'}, 'evidence': 'retained'}])
    paths = {str(frontier.PROGRAM): old, str(frontier.STATE): before,
        str(frontier.BASE / 'current-binding.json'): {'old_scope': 'retained'},
        str(frontier.BASE / 'live-calls.json'): {'calls': ['retained']},
        str(frontier.BASE / 'live-grant.json'): {'deadline': 'retained'}}
    held, rows = {}, []
    for name, value in paths.items():
        save(root / 'before' / name, value)
        held[name] = ref(root, root / 'before' / name)
        rows.append({'previous': {'path': name, 'sha256': held[name]['sha256']}, 'archive': held[name]})
    save(root / 'baseline.json', dict(prior_detours=52, calls=2369,
        running_owners=0, reserved_dispatches=0, archived=rows))
    save(root / 'review.json', {'reviewed': True})
    save(root / 'before-replay.json', dict(reproduced_error=frontier.VETO_REASON,
        same_record_population=True, schema_equal=True, ledger_unchanged=True, provider_calls=0,
        differences=[{'path': '/records/6/id'}]))
    save(root / 'after-replay.json', dict(receipt_reused=True, differences=[],
        schema_equal=True, ledger_unchanged=True, provider_calls=0))
    save(root / 'tests.json', dict(exit_code=0, semantic_mutations_rejected=True,
        delayed_499_controls_passed=True))
    save(root / 'result.json', dict(verdict='PASS', provider_calls=0, ledger_unchanged=True,
        legal_acceptance=False, evidence=[], before_replay=ref(root, 'before-replay.json'),
        after_replay=ref(root, 'after-replay.json'), test_result=ref(root, 'tests.json')))
    implementation = {}
    for name in frontier.MUTATED:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Reviewed frontier implementation or plan.')
        if name != str(frontier.PLAN): implementation[name] = ref(root, path)
    revision = dict(profile='integration-frontier-refresh.v1', user_instruction=frontier.USER,
        work=str(frontier.WORK), prior_detours=52, additional_consolidated_revision=1,
        live_calls_added=0, additional_task_attempts=1, cumulative_additional_attempts=20,
        attempt_increments={'acquire-p10': 1}, additional_transport_replacements=0,
        repair_allowance_added=0, service_scope_reset=False, attempts_reset=False,
        reopened_nodes=list(frontier.REOPEN), resolved_vetoes=[veto],
        terminal_cancellation_recovery=deepcopy(frontier.TERMINAL_CANCELLATION_POLICY),
        service_recovery_policy=deepcopy(frontier.SERVICE_DELAYED_POLICY),
        baseline=ref(root, 'baseline.json'), review=ref(root, 'review.json'), result=ref(root, 'result.json'),
        implementation=implementation, prior_program=held[str(frontier.PROGRAM)],
        prior_state=held[str(frontier.STATE)], prior_binding=held[str(frontier.BASE / 'current-binding.json')],
        prior_ledger=held[str(frontier.BASE / 'live-calls.json')],
        prior_grant=held[str(frontier.BASE / 'live-grant.json')])
    # The actual staged mission recursively authenticates the historical program.
    # These small controls isolate the new amendment's migration boundary.
    monkeypatch.setattr(frontier, 'validate_program', lambda value, root: None)
    return old, before, frontier.expected_program(old, revision, root)


def test_only_last_existing_p10_attempt_and_exact_veto_are_reopened(tmp_path, monkeypatch):
    old, before, program = fixture(tmp_path, monkeypatch)
    ceilings = frontier.validate_revision(program, tmp_path)
    assert ceilings['acquire-p10'] == 8 and ceilings['acquire-evidence'] == 6
    assert program['tasks'][1:] == old['tasks'][1:]
    state = frontier.project_state(before, program, 'now')
    frontier.validate_state_history(program, state, tmp_path)
    assert state['tasks']['acquire-p10']['status'] == 'PENDING'
    assert state['tasks']['acquire-p10']['attempts'] == before['tasks']['acquire-p10']['attempts']
    assert state['continuation_vetoes'] == before['continuation_vetoes'][1:]
    assert state['resolved_continuation_vetoes'][:-1] == before['resolved_continuation_vetoes']
    state['tasks']['acquire-evidence']['status'] = 'RUNNING'
    state['tasks']['acquire-evidence']['attempts'].append({'number': 6})
    frontier.validate_state_history(program, state, tmp_path)


@pytest.mark.parametrize('field,value', [('live_calls_added', 1), ('additional_task_attempts', 2),
    ('cumulative_additional_attempts', 21), ('additional_transport_replacements', 1),
    ('repair_allowance_added', 1), ('service_scope_reset', True), ('attempts_reset', True),
    ('reopened_nodes', ['acquire-p14']), ('prior_detours', 0), ('user_instruction', 'forever')])
def test_frontier_cannot_expand_authority(tmp_path, monkeypatch, field, value):
    _, _, program = fixture(tmp_path, monkeypatch)
    program[frontier.KEY][field] = value
    with pytest.raises(Refused): frontier.validate_revision(program, tmp_path)


@pytest.mark.parametrize('fault', ['owner', 'deadline', 'calls', 'repairs', 'veto', '499_policy', 'wait'])
def test_hidden_graph_and_policy_changes_are_rejected(tmp_path, monkeypatch, fault):
    _, _, program = fixture(tmp_path, monkeypatch)
    revision = program[frontier.KEY]
    if fault == 'owner': program['tasks'][2]['maximum_attempts'] += 1
    elif fault == 'deadline': program['deadline_utc'] = 'renewed'
    elif fault == 'calls': program['global_call_ceiling'] += 1
    elif fault == 'repairs': program['repair_execution']['repair_ids'].append('R11')
    elif fault == 'veto': revision['resolved_vetoes'].append({'code': 'E_AUTHORITY', 'reason': 'Unrelated unresolved dispatch'})
    elif fault == '499_policy': revision['terminal_cancellation_recovery']['requires_no_model_output'] = False
    else: revision['service_recovery_policy']['backoff_seconds'][0] = 0
    with pytest.raises(Refused): frontier.validate_revision(program, tmp_path)


@pytest.mark.parametrize('fault', ['attempts', 'settled', 'veto', 'old_resolution'])
def test_history_is_preserved_during_later_execution(tmp_path, monkeypatch, fault):
    _, before, program = fixture(tmp_path, monkeypatch)
    state = frontier.project_state(before, program, 'now')
    if fault == 'attempts': state['tasks']['acquire-p10']['attempts'].pop()
    elif fault == 'settled': state['tasks']['acquire-gatecoin']['status'] = 'PENDING'
    elif fault == 'veto': state['continuation_vetoes'] = []
    else: state['resolved_continuation_vetoes'].pop(0)
    with pytest.raises(Refused): frontier.validate_state_history(program, state, tmp_path)


def test_new_phase_admission_retains_saved_calls_and_common_evidence():
    program = {'frontier_refresh': {'work': str(frontier.WORK)}, 'repair_execution': {
        'work': 'old', 'live_directories': {'p10': 'saved-live'}, 'common_directories': {'p10': 'saved-common'}}}
    assert active_live(program) == frontier.WORK / 'live'
    assert str(question_live(program, 'p10')) == 'saved-live'
    assert str(common_directory(program, 'p10')) == 'saved-common'
