from copy import deepcopy
from scripts import legal_integration_failure_recovery as repair
from scripts.legal_mission_execution import save,ref,Refused
import pytest

def setup(root):
    old={'tasks':[{'id':'acquire-'+q,'maximum_attempts':n,'inputs':[],'deliverable':'old'}
        for q,n in [('p10',9),('p14',10),('evidence',7),('gatecoin',13)]],
        'protected_evidence':[],'deadline_utc':'original','global_call_ceiling':8100}
    before={'tasks':{t['id']:{'status':'FAILED','attempts':[{'number':i} for i in range(t['maximum_attempts'])]} for t in old['tasks']},
        'events':[],'continuation_vetoes':[{'reason':'unrelated'}]}
    save(root/'before.json',before);save(root/repair.PLAN,{'plan':'current'})
    r={'prior_state':ref(root,'before.json'),'implementation':{},'review':{},'result':{},'baseline':{},'recovery':{}}
    program=repair.expected_program(old,r,root)
    return old,before,program

def test_one_owner_reopens_without_resetting_other_branches(tmp_path):
    old,before,program=setup(tmp_path)
    assert [t['maximum_attempts'] for t in program['tasks']]==[10,10,7,13]
    assert program['tasks'][1:]==old['tasks'][1:]
    assert program['deadline_utc']=='original' and program['global_call_ceiling']==8100
    state=repair.project_state(before,program,'now')
    repair.validate_state_history(program,state,tmp_path)
    assert state['tasks']['acquire-p10']['status']=='PENDING'
    assert state['tasks']['acquire-p10']['attempts']==before['tasks']['acquire-p10']['attempts']

def test_running_owner_rejected(tmp_path):
    old,before,program=setup(tmp_path);before['tasks']['acquire-p10']['status']='RUNNING'
    with pytest.raises(Refused):repair.project_state(before,program,'now')

def test_history_mutation_rejected(tmp_path):
    old,before,program=setup(tmp_path);state=repair.project_state(before,program,'now')
    state['tasks']['acquire-p10']['attempts'].pop()
    with pytest.raises(Refused):repair.validate_state_history(program,state,tmp_path)


def test_failure_triggers_next_pass_and_restart_reuses_results(tmp_path,monkeypatch):
    from scripts import legal_integration_phased_live as live
    from legalmath.interpretation.assurance.phased import account_recovery,failure_recovery
    from legalmath.errors import LegalMathError
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    monkeypatch.setattr(live,'ROOT',tmp_path)
    work=repair.WORK
    save(tmp_path/'initial.json',{'failure_recovery':{'actions':{'detail-0':'repair'}},'input_hash':'source'})
    save(tmp_path/repair.PROGRAM,{'failure_recovery':{'recovery':ref(tmp_path,'initial.json'),'maximum_passes':2}})
    save(tmp_path/live.LIVE/'acquisition/investigation.json',{'question_acquisition_complete':{'p10':True}})
    monkeypatch.setattr(live,'acquisition',lambda service:{'question_acquisition_complete':{'p10':True}})
    attempted=[]
    def product(q,tool,service,*,preparation_only,recovery_context):
        folder=tmp_path/recovery_context['common_directory'];attempted.append(str(folder))
        save(folder/'requirement-details.json',[{'id':'original','result':{'status':'FAILED'}}])
        result={'answers':{'p10':{'status':'PREPARED' if len(attempted)==2 else 'FAILED'}}}
        save(folder/'result.json',result)
        if len(attempted)==1:raise LegalMathError('E_DEPENDENCY',details='First pass exposes a new repairable failure')
        return result
    monkeypatch.setattr(live,'product_route',product)
    monkeypatch.setattr(account_recovery,'build',lambda *a,**kw:{'input_hash':'source'})
    monkeypatch.setattr(account_recovery,'load',lambda *a,**kw:None)
    monkeypatch.setattr(failure_recovery,'diagnose',lambda *a,**kw:{'input_hash':'source','failure_recovery':{'actions':{'new-leaf':'repair'} if len(attempted)==1 else {}}})
    result=repair.acquire('p10',object())
    assert len(attempted)==2 and result['question']=='p10'
    assert repair.read(tmp_path/work/'progress.json')['passes'][0]['prepared'] is False
    assert repair.acquire('p10',object())==result
    assert len(attempted)==2  # Durable pass cursor prevents redispatch on restart.
