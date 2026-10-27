from copy import deepcopy
import pytest
from scripts.legal_mission_execution import save,ref,Refused
from scripts import legal_review_deployment as deployment


def test_deployment_preserves_failed_attempts_and_independent_orphan(tmp_path):
    before=dict(tasks={'baseline-p14':dict(status='FAILED',attempts=[dict(number=n) for n in range(1,5)],result={}),
        'baseline-gatecoin':dict(status='RUNNING',attempts=[dict(number=n) for n in range(1,5)],live_supervisor={'pid':123}),
        'done':dict(status='SUCCEEDED',attempts=[dict(number=1)])},events=[dict(action='old')],
        continuation_vetoes=[dict(reason='do not erase')])
    save(tmp_path/'before.json',before)
    program=dict(review_repair=dict(deployment=dict(review={},prior_state=ref(tmp_path,'before.json'))))
    state=deployment.project_state(before,program,'now')
    deployment.validate_history(program,state,tmp_path)
    assert state['tasks']['baseline-gatecoin']==before['tasks']['baseline-gatecoin']
    assert state['tasks']['baseline-p14']['status']=='PENDING'
    assert state['tasks']['baseline-p14']['attempts']==before['tasks']['baseline-p14']['attempts']
    broken=deepcopy(state)
    broken['tasks']['baseline-p14']['attempts'][0]['number']=99
    with pytest.raises(Refused): deployment.validate_history(program,broken,tmp_path)
    broken=deepcopy(state)
    broken['continuation_vetoes']=[]
    with pytest.raises(Refused): deployment.validate_history(program,broken,tmp_path)
    before['tasks']['baseline-p14']['status']='SUCCEEDED'
    with pytest.raises(Refused): deployment.project_state(before,program,'now')
