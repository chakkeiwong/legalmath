from copy import deepcopy
import pytest
from scripts import legal_integration_time_continuation as amendment
from scripts.legal_mission_execution import save, ref, Refused


def fixture(root):
    old = dict(deadline_utc='old', global_call_ceiling=0,
        tasks=[dict(id='baseline-p14',maximum_attempts=5),dict(id='baseline-gatecoin',maximum_attempts=3)],
        protected_evidence=[], common_capacity={'profile':'prior'}, delayed_service_recovery={'maximum_replacements':24})
    before = dict(tasks={'baseline-p14':dict(status='PENDING',attempts=[{'number':1}]),
        'baseline-gatecoin':dict(status='SUCCEEDED',attempts=[{'number':1}])},events=[{'action':'prior'}],
        continuation_vetoes=[{'reason':'preserved'}],resolved_continuation_vetoes=[{'reason':'old'}])
    save(root/'before.json',before)
    revision = dict(prior_state=ref(root,'before.json'),implementation={},baseline={},review={},result={},time_extension={})
    plan = save(root/'plan.json',{'review':'test'})
    program = amendment.expected_program(old,revision,root,plan_reference=ref(root,'plan.json'))
    return old,before,program


def test_time_only_projection_preserves_tasks_budgets_and_completed_work(tmp_path):
    old,before,program = fixture(tmp_path)
    assert program['tasks'] == old['tasks']
    assert program['global_call_ceiling'] == old['global_call_ceiling']
    assert program['delayed_service_recovery'] == old['delayed_service_recovery']
    assert program['deadline_utc'] == amendment.DEADLINE
    after = amendment.project_state(before,program,'now')
    assert after['tasks'] == before['tasks']
    amendment.validate_state_history(program,after,tmp_path)
    after['tasks']['baseline-p14']['attempts'].append({'number':2})
    after['tasks']['baseline-p14']['status'] = 'SUCCEEDED'
    amendment.validate_state_history(program,after,tmp_path)


@pytest.mark.parametrize('mutation',['active','attempt','settled','veto','resolved','event'])
def test_lost_history_or_active_owner_is_rejected(tmp_path,mutation):
    old,before,program = fixture(tmp_path)
    if mutation == 'active':
        before['tasks']['baseline-p14']['status'] = 'RUNNING'
        with pytest.raises(Refused): amendment.project_state(before,program,'now')
        return
    after = amendment.project_state(before,program,'now')
    if mutation == 'attempt': after['tasks']['baseline-p14']['attempts'].clear()
    elif mutation == 'settled': after['tasks']['baseline-gatecoin']['status'] = 'PENDING'
    elif mutation == 'veto': after['continuation_vetoes'].clear()
    elif mutation == 'resolved': after['resolved_continuation_vetoes'].clear()
    else: after['events'].pop(0)
    with pytest.raises(Refused): amendment.validate_state_history(program,after,tmp_path)
