"""Recovery retains consumed attempts and cannot revive unrelated failures."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from scripts import legal_integration_settled_recovery as recovery
from scripts import legal_integration_phased_live as live
from scripts.legal_mission_execution import save, ref, Refused

def fixture(root):
    ids = [('acquire-p10',8),('acquire-evidence',6),('acquire-p14',10),('acquire-gatecoin',13)]
    old = {'tasks':[{'id':k,'maximum_attempts':n,'inputs':[],'deliverable':'old'} for k,n in ids],
        'protected_evidence':[], 'global_call_ceiling':8100, 'deadline_utc':'unchanged'}
    before = {'tasks':{k:{'status':'FAILED','attempts':[{'number':i} for i in range(1,n+1)]} for k,n in ids},
        'events':[], 'continuation_vetoes':[{'code':'E_INTEGRITY','reason':'Changed phase on resume',
        'scope':['acquire-p10']},{'code':'E_AUTHORITY','reason':'unrelated'}],
        'resolved_continuation_vetoes':[{'veto':'older'}]}
    save(root/'before.json',before); save(root/'review.md',{'review':'bounded'})
    save(root/'result.json',{'status':'checked'}); save(root/recovery.PLAN,{'plan':'current'})
    revision = {'prior_state':ref(root,'before.json'),'review':ref(root,'review.md'),
        'result':ref(root,'result.json'),'baseline':ref(root,'before.json'),
        'implementation':{},'recoveries':{},'resolved_vetoes':[before['continuation_vetoes'][0]]}
    program = recovery.expected_program(old,revision,root)
    return old,before,program

def test_exact_two_owner_increments_preserve_other_limits(tmp_path):
    old,before,program=fixture(tmp_path)
    assert {t['id']:t['maximum_attempts'] for t in program['tasks']}=={
        'acquire-p10':9,'acquire-evidence':7,'acquire-p14':10,'acquire-gatecoin':13}
    assert program['tasks'][2:]==old['tasks'][2:]
    assert program['global_call_ceiling']==8100 and program['deadline_utc']=='unchanged'
    state=recovery.project_state(before,program,'now')
    recovery.validate_state_history(program,state,tmp_path)
    assert state['continuation_vetoes']==before['continuation_vetoes'][1:]
    for tid in recovery.REOPEN:
        assert state['tasks'][tid]['attempts']==before['tasks'][tid]['attempts']
        assert state['tasks'][tid]['status']=='PENDING'

@pytest.mark.parametrize('mutation',['old_attempt','unrelated_owner','unrelated_veto','resolved_history'])
def test_recovery_rejects_lost_history_and_unrelated_changes(tmp_path,mutation):
    _,before,program=fixture(tmp_path); state=recovery.project_state(before,program,'now')
    if mutation=='old_attempt': state['tasks']['acquire-evidence']['attempts'][0]['number']=99
    elif mutation=='unrelated_owner': state['tasks']['acquire-p14']['status']='PENDING'
    elif mutation=='unrelated_veto': state['continuation_vetoes']=[]
    else: state['resolved_continuation_vetoes']=[]
    with pytest.raises(Refused): recovery.validate_state_history(program,state,tmp_path)

def test_running_owner_cannot_be_migrated(tmp_path):
    _,before,program=fixture(tmp_path); before['tasks']['acquire-p10']['status']='RUNNING'
    with pytest.raises(Refused): recovery.project_state(before,program,'now')

def test_recovery_routes_only_named_questions():
    p={'repair_execution':{'live_directories':{q:'old-live/'+q for q in ('evidence','p10','p14','gatecoin')},
        'common_directories':{q:'old-common/'+q for q in ('evidence','p10','p14','gatecoin')}},
        'settled_recovery':{'work':'recovery','live_directories':{'evidence':'new-live/evidence','p10':'new-live/p10'},
        'common_directories':{'evidence':'new-common/evidence','p10':'new-common/p10'}}}
    for q in ('evidence','p10'):
        assert str(live.question_live(p,q))=='new-live/'+q
        assert str(live.common_directory(p,q))=='new-common/'+q
    for q in ('p14','gatecoin'):
        assert str(live.question_live(p,q))=='old-live/'+q
        assert str(live.common_directory(p,q))=='old-common/'+q

def test_product_route_uses_exact_successor_not_stale_synthesis(monkeypatch,tmp_path):
    from scripts import legal_product_completion
    q='evidence'; pointer={'path':'new-checkpoint','sha256':'exact'}
    program={'prerequisite_repair':{'source':{'path':'envelope'}},
        'repair_execution':{'recoveries':{q:{'path':'old','sha256':'old'}},
        'downstream_input_profile':'exact-downstream-input-32k.v1',
        'downstream_instruction_profile':'schema-specific-downstream-instructions.v1',
        'synthesis_successors':{q:{'path':'stale','sha256':'stale'}},
        'live_directories':{q:'old-live'},'common_directories':{q:'old-common'}},
        'lossless_account_repair':{'retained':True},'account_instruction_repair':{'retained':True},
        'settled_recovery':{'work':'recovery','recoveries':{q:pointer},
        'live_directories':{q:'new-live'},'common_directories':{q:'new-common'}}}
    monkeypatch.setattr(live,'configure',lambda:SimpleNamespace(ENVELOPE='envelope'))
    def read(path):
        if path==live.ROOT/live.PROGRAM:return program
        if str(path).endswith('live-grant.json'):return {'deadline_utc':'unchanged'}
        return {'original_questions':[{'question_id':q}]}
    monkeypatch.setattr(live,'read',read); monkeypatch.setattr(live,'ref',lambda *a:{'path':'test','sha256':'test'})
    monkeypatch.setattr(live,'tokenizer',lambda *a:object()); monkeypatch.setattr(live,'phase_admit',lambda *a:object())
    monkeypatch.setattr(legal_product_completion,'run_product',lambda *args,**kw:(args,kw))
    args,kw=live.product_route(q,None,object(),preparation_only=True)
    assert args[1]==live.ROOT/'new-common'
    assert kw['bounded_requirement_account_recovery']==pointer
    assert 'retained_initial' not in kw and kw['shared_prefix'] is None
    assert kw['deadline_utc']=='unchanged'

def test_failed_answer_does_not_prevent_other_ready_tool(monkeypatch):
    queue=['baseline-evidence','tool-evidence-pyarg','tool-evidence-clingo']
    execution=SimpleNamespace(summary=lambda:{'ready':list(queue),'running':[]})
    attempted=[]
    def complete(execution,tid,action):
        attempted.append(tid); queue.remove(tid)
        try:action()
        except RuntimeError:pass
    def answer(q,tool,service):
        if tool is None:raise RuntimeError('Rejected baseline')
        return {'tool':tool}
    monkeypatch.setattr(live,'answer',answer)
    monkeypatch.setattr(live,'defer_open_service',lambda *a:False)
    live.drain_answers(execution,SimpleNamespace(complete_node=complete),object())
    assert attempted==['baseline-evidence','tool-evidence-pyarg','tool-evidence-clingo']


def test_phase_veto_reaches_only_real_dependants():
    from scripts.legal_integration_campaign import continuation_scope
    execution=SimpleNamespace(program={'settled_recovery':{'reviewed':True}},tasks={
        'acquire-p10':{'requires':[]}, 'baseline-p10':{'requires':['acquire-p10']},
        'compare-p10-pyarg':{'requires':['baseline-p10']},
        'acquire-evidence':{'requires':[],'after':['acquire-p10']},
        'baseline-evidence':{'requires':['acquire-evidence']}})
    value={'error':'E_INTEGRITY','reason':'Changed phase on resume'}
    assert continuation_scope(execution,'acquire-p10',value)==[
        'acquire-p10','baseline-p10','compare-p10-pyarg']
    value['reason']='Changed shared source'
    assert set(continuation_scope(execution,'acquire-p10',value))==set(execution.tasks)
