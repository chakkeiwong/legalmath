from copy import deepcopy
import pytest
from scripts import legal_product_closure as closure
from scripts.legal_mission_execution import save,ref,Refused

def test_projection_preserves_graph_limits_and_exact_historical_sources(tmp_path):
    (tmp_path/'before.py').write_text('old')
    oldref={'path':'code.py','sha256':ref(tmp_path,'before.py')['sha256']}
    archived={'previous':oldref,'archive':ref(tmp_path,'before.py')}
    save(tmp_path/'baseline.json',dict(changed_paths=['code.py'],archived=[archived]))
    old=dict(tasks=[dict(id='a',requires=['b'],after=['c'],maximum_attempts=4)],
        workers=1,deadline_utc='2026-10-27T05:15:09Z',protected_evidence=[oldref],
        original={'path':'code.py','sha256':oldref['sha256']})
    revision=dict(baseline=ref(tmp_path,'baseline.json'),review={},result={},handover={},
        implementation={'code.py':{'path':'code.py','sha256':'new'}},
        master_plan={'path':'plan.md','sha256':'plan'},
        substantive_evidence={'review':{'path':'answer.json','sha256':'answer'}})
    actual=closure.expected_program(old,revision,tmp_path)
    assert actual['tasks']==old['tasks'] and actual['workers']==old['workers']
    assert actual['deadline_utc']==old['deadline_utc']
    assert actual['original']==archived['archive'] and old['original']==oldref
    assert actual['protected_evidence'][-1]==revision['master_plan']
    assert revision['substantive_evidence']['review'] in actual['protected_evidence']

def test_corpus_failure_does_not_cancel_independent_scheduler(tmp_path,monkeypatch):
    from scripts import legal_review_repair
    monkeypatch.setattr(closure,'ROOT',tmp_path)
    monkeypatch.setattr(closure,'runtime_directory',lambda:tmp_path/closure.WORK)
    monkeypatch.setattr(closure,'corpus',lambda:(_ for _ in ()).throw(ValueError('branch failure')))
    calls=[]
    monkeypatch.setattr(legal_review_repair,'live',lambda:calls.append('validated scheduler') or {'ready':[]})
    assert closure.drain_independent()=={'ready':[]}
    assert calls==['validated scheduler']
    assert (tmp_path/closure.WORK/'corpus-handler-error.json').is_file()

def test_shared_scheduler_veto_is_not_swallowed(tmp_path,monkeypatch):
    from scripts import legal_review_repair
    monkeypatch.setattr(closure,'ROOT',tmp_path)
    monkeypatch.setattr(closure,'runtime_directory',lambda:tmp_path/closure.WORK)
    monkeypatch.setattr(closure,'corpus',lambda:dict(status='BLOCKED'))
    monkeypatch.setattr(legal_review_repair,'live',lambda:(_ for _ in ()).throw(Refused('authority veto')))
    with pytest.raises(Refused,match='authority veto'):closure.drain_independent()

def test_closure_history_rejects_lost_attempt_and_reopened_failure(tmp_path,monkeypatch):
    from scripts import legal_repaired_retry_continuation
    monkeypatch.setattr(legal_repaired_retry_continuation,'validate_history',lambda *args:None)
    before=dict(events=[{'old':True}],tasks={'a':dict(status='FAILED',attempts=[{'number':1}]),
        'b':dict(status='RUNNING',attempts=[{'number':1}])})
    save(tmp_path/'state.json',before);save(tmp_path/'program.json',{})
    save(tmp_path/'baseline.json',dict(changed_paths=[],archived=[]))
    p={closure.KEY:dict(prior_state=ref(tmp_path,'state.json'),prior_program=ref(tmp_path,'program.json'),
        baseline=ref(tmp_path,'baseline.json'))}
    closure.validate_history(p,before,tmp_path)
    current=deepcopy(before);current['tasks']['a']['status']='PENDING'
    with pytest.raises(Refused):closure.validate_history(p,current,tmp_path)
    current=deepcopy(before);current['tasks']['b']['attempts']=[]
    with pytest.raises(Refused):closure.validate_history(p,current,tmp_path)
    current=deepcopy(before);current['events']=[]
    with pytest.raises(Refused):closure.validate_history(p,current,tmp_path)

def test_old_objections_without_disposition_remain_protected():
    from legalmath.interpretation.assurance.phased.current_issue_disposition import apply
    from types import SimpleNamespace
    assert apply(SimpleNamespace(capacity_checkpoint=None),'q',{}, {}, {},[],[],[]) is None

def test_followthrough_adds_only_one_named_attempt_and_keeps_final_plan(tmp_path):
    save(tmp_path/'baseline.json',dict(changed_paths=[],archived=[]))
    old=dict(tasks=[dict(id='baseline-p14',maximum_attempts=8),dict(id='baseline-gatecoin',maximum_attempts=6)],
        protected_evidence=[],product_closure={'phase_identity':'retained'},deadline_utc='same')
    fix=dict(baseline=ref(tmp_path,'baseline.json'),review={},result={},handover={},
        implementation={},corpus_components={},master_plan={'path':'new.md','sha256':'new'})
    result=closure.expected_followthrough(old,fix,tmp_path)
    assert [x['maximum_attempts'] for x in result['tasks']]==[9,6]
    assert old['tasks'][0]['maximum_attempts']==8 and result['deadline_utc']=='same'
    assert result['product_closure']['phase_identity']=='retained'
    assert result['protected_evidence'][-1]==fix['master_plan']

def test_corpus_handler_uses_registered_components_without_reopening(tmp_path,monkeypatch):
    from scripts import legal_integration_qualification_continuation as handler
    from legalmath.interpretation.assurance import corpus_components
    monkeypatch.setattr(handler,'ROOT',tmp_path)
    monkeypatch.setattr(handler,'BASE',__import__('pathlib').Path('base'))
    monkeypatch.setattr(handler,'PROGRAM',__import__('pathlib').Path('program.json'))
    monkeypatch.setattr(handler,'verify_tree',lambda value:None)
    rows={}
    for name in ('2023','2025','handbook'):
        pointer={'path':name+'.json','sha256':name}
        rows[str(tmp_path/'base'/('ownership-'+name)/'attempt-3/evidence.json')]=dict(ownership=pointer,
            main_labels_verified=1,main_labels_total=1,components_verified=1,components_total=1,
            footnotes_verified=1,footnotes_total=1,unresolved_count=0,verified_pages=35,pages=35,
            page_mismatches=[],cross_page_delivery_gaps=[])
        rows[str(tmp_path/(name+'.json'))]=dict(source=pointer,edition='fixture',index_date='fixture')
    registration={'expected_context':{'fixture':True},'components':{'fixture':True}}
    rows[str(tmp_path/'program.json')]={'product_closure':{'corpus_components':registration}}
    for path,value in rows.items():
        target=__import__('pathlib').Path(path);target.parent.mkdir(parents=True,exist_ok=True)
        save(target,value)
    monkeypatch.setattr(handler,'read',lambda p:rows[str(p)])
    called=[]
    def consume(root,actual,**kwargs):
        called.append((root,actual,kwargs))
        return dict(status='BLOCKED',remaining=['p10 missing'],corpus_acceptance_complete=False)
    monkeypatch.setattr(corpus_components,'consume',consume)
    target=tmp_path/'out';target.mkdir()
    result=handler.corpus(target)
    assert result['_node_status']=='BLOCKED' and len(called)==1
    assert called[0][1]==registration and set(called[0][2]['reconciled_sources'])=={'2023','2025','handbook'}
    assert (target/'corpus-components.json').is_file()
