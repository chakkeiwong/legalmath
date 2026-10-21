from copy import deepcopy
import pytest
from scripts import legal_integration_synthesis_resolution as repair
from scripts.legal_mission_execution import save, ref, Refused


def setup(root):
    old = {'tasks': [{'id': 'acquire-'+q, 'maximum_attempts': n, 'inputs': [], 'deliverable': 'old'}
        for q, n in repair.ATTEMPTS.items()] + [{'id':'answer-p10', 'maximum_attempts':2, 'inputs':[]}],
        'protected_evidence': [], 'deadline_utc': repair.DEADLINE, 'global_call_ceiling': 8100,
        'synthesis_continuation': {'time_extension': {'path':'original-extension','sha256':'held'}}}
    before = {'tasks': {t['id']: {'status':'FAILED', 'attempts':[{'number':i} for i in range(t['maximum_attempts'])]}
        for t in old['tasks']}, 'events':[], 'continuation_vetoes':[{'reason':'unrelated'}]}
    save(root/'before.json', before)
    save(root/repair.PLAN, {'plan':'current'})
    revision = {'prior_state':ref(root,'before.json'),'implementation':{},'review':{},'result':{},
        'baseline':{},'recoveries':{},'successors':{}}
    return old, before, repair.expected_program(old, revision, root)


def test_four_independent_owners_gain_one_attempt_without_resource_reset(tmp_path):
    old, before, program = setup(tmp_path)
    for prior, current in zip(old['tasks'], program['tasks']):
        if prior['id'] in repair.REOPEN:
            assert current['maximum_attempts'] == prior['maximum_attempts'] + 1
        else:
            assert prior == current
    assert program['deadline_utc'] == old['deadline_utc']
    assert program['synthesis_continuation'] == old['synthesis_continuation']
    assert program['global_call_ceiling'] == 8100
    state = repair.project_state(before, program, 'now')
    repair.validate_state_history(program, state, tmp_path)
    for tid in repair.REOPEN:
        assert state['tasks'][tid]['status'] == 'PENDING'
        assert state['tasks'][tid]['attempts'] == before['tasks'][tid]['attempts']


@pytest.mark.parametrize('change', ['running', 'lost_attempt', 'lost_veto', 'unrelated'])
def test_registration_preserves_running_owners_history_and_independent_limits(tmp_path, change):
    old, before, program = setup(tmp_path)
    if change == 'running':
        before['tasks']['acquire-p10']['status'] = 'RUNNING'
        with pytest.raises(Refused): repair.project_state(before, program, 'now')
        return
    state = repair.project_state(before, program, 'now')
    if change == 'lost_attempt': state['tasks']['acquire-p10']['attempts'].pop()
    elif change == 'lost_veto': state['continuation_vetoes'].clear()
    else: state['tasks']['answer-p10']['status'] = 'PENDING'
    with pytest.raises(Refused): repair.validate_state_history(program, state, tmp_path)
