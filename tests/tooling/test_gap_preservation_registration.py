from copy import deepcopy
import pytest
from scripts import legal_integration_gap_preservation as repair
from scripts.legal_mission_execution import save,ref,Refused

def setup(root):
    old={'tasks':[{'id':'acquire-'+q,'maximum_attempts':n,'inputs':[],'deliverable':'old'}
        for q,n in [('p10',10),('p14',10),('evidence',7),('gatecoin',13)]],
        'protected_evidence':[],'deadline_utc':'original','global_call_ceiling':8100}
    before={'tasks':{t['id']:{'status':'FAILED','attempts':[{'number':i} for i in range(t['maximum_attempts'])]} for t in old['tasks']},
        'events':[],'continuation_vetoes':[{'reason':'unrelated'}]}
    save(root/'before.json',before);save(root/repair.PLAN,{'plan':'current'})
    r={'prior_state':ref(root,'before.json'),'implementation':{},'review':{},'result':{},'baseline':{},'recovery':{}}
    return old,before,repair.expected_program(old,r,root)

def test_reopens_one_owner_preserving_attempts_other_branches_and_limits(tmp_path):
    old,before,program=setup(tmp_path)
    assert [t['maximum_attempts'] for t in program['tasks']]==[11,10,7,13]
    assert program['tasks'][1:]==old['tasks'][1:]
    assert program['deadline_utc']=='original' and program['global_call_ceiling']==8100
    state=repair.project_state(before,program,'now');repair.validate_state_history(program,state,tmp_path)
    assert state['tasks']['acquire-p10']['attempts']==before['tasks']['acquire-p10']['attempts']

def test_active_owner_cannot_migrate(tmp_path):
    old,before,program=setup(tmp_path);before['tasks']['acquire-p10']['status']='RUNNING'
    with pytest.raises(Refused):repair.project_state(before,program,'now')

def test_prior_attempt_cannot_disappear(tmp_path):
    old,before,program=setup(tmp_path);state=repair.project_state(before,program,'now')
    state['tasks']['acquire-p10']['attempts'].pop()
    with pytest.raises(Refused):repair.validate_state_history(program,state,tmp_path)
