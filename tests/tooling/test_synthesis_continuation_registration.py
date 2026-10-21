from copy import deepcopy
import pytest
from scripts import legal_integration_synthesis_continuation as repair
from scripts.legal_mission_execution import save, ref, Refused


def setup(root):
    old = {'tasks':[{'id':'acquire-'+q,'maximum_attempts':n,'inputs':[],'deliverable':'old'}
        for q,n in [('p10',11),('p14',10),('evidence',7),('gatecoin',13)]],
        'protected_evidence':[],'deadline_utc':'original','global_call_ceiling':8100}
    before = {'tasks':{t['id']:{'status':'FAILED','attempts':[{'number':i} for i in range(t['maximum_attempts'])]} for t in old['tasks']},
        'events':[],'continuation_vetoes':[{'reason':'unrelated'}]}
    save(root/'before.json',before);save(root/repair.PLAN,{'plan':'current'})
    r = {'prior_state':ref(root,'before.json'),'implementation':{},'review':{},'result':{},'baseline':{},'recovery':{},'time_extension':{}}
    return old,before,repair.expected_program(old,r,root)


def test_one_continuation_preserves_other_attempts_and_call_ceiling(tmp_path):
    old,before,program = setup(tmp_path)
    assert [t['maximum_attempts'] for t in program['tasks']] == [12,10,7,13]
    assert program['tasks'][1:] == old['tasks'][1:]
    assert program['deadline_utc'] == repair.DEADLINE and program['global_call_ceiling'] == 8100
    state = repair.project_state(before,program,'now');repair.validate_state_history(program,state,tmp_path)
    assert state['tasks']['acquire-p10']['attempts'] == before['tasks']['acquire-p10']['attempts']


def test_active_owner_and_dropped_history_are_rejected(tmp_path):
    old,before,program = setup(tmp_path)
    running = deepcopy(before);running['tasks']['acquire-p10']['status'] = 'RUNNING'
    with pytest.raises(Refused):repair.project_state(running,program,'now')
    state = repair.project_state(before,program,'now');state['tasks']['acquire-p10']['attempts'].pop()
    with pytest.raises(Refused):repair.validate_state_history(program,state,tmp_path)


def test_no_account_repairs_still_enters_synthesis_and_diagnoses_returned_failure(tmp_path,monkeypatch):
    from scripts import legal_integration_phased_live as live
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    save(tmp_path/repair.PROGRAM,{repair.KEY:{'recovery':{'path':'checkpoint.json'}}})
    save(tmp_path/'checkpoint.json',{'failure_recovery':{'actions':{}}})
    monkeypatch.setattr(live,'acquisition',lambda _: {'question_acquisition_complete':{'p10':True}})
    calls = []
    def route(q,tool,service,**kwargs):
        calls.append(kwargs)
        directory = tmp_path/kwargs['recovery_context']['common_directory']
        result = {'answers':{'p10':{'status':'FAILED','error':'E_DEPENDENCY','reason':'Dependent synthesis failed'}}}
        save(directory/'result.json',result)
        save(directory/'phases/reduction-p10-0/outcome.json',{'phase':'reduction-p10-0','execution_complete':False,
            'resource_refusal':{'error':'E_RESOURCE_LIMIT','reason':'window'}})
        return result
    monkeypatch.setattr(live,'product_route',route)
    with pytest.raises(Refused):repair.acquire('p10',object())
    assert len(calls) == 1
    report = repair.read(tmp_path/repair.WORK/'next-actions.json')
    assert report['failures'][0]['origin'] == 'returned_answer'
    assert report['incomplete_phases'][0]['resource_refusal']['error'] == 'E_RESOURCE_LIMIT'
    assert report['provider_calls_authorized'] == 0
