"""Study scheduling tests use synthetic tasks and never dispatch a model."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
from legalmath.canonical import canonical,raw_digest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_successor_study as study


@pytest.fixture
def harness(tmp_path,monkeypatch):
    out=tmp_path/'out';out.mkdir();source=tmp_path/'source.txt';source.write_text('Synthetic source only.')
    refs=[]
    for index in range(4):
        tid='fixture.'+str(index);p=tmp_path/(tid+'.json')
        task={'task_id':tid,'publication_design':'SYNTHETIC_SCHEDULING_FIXTURE','packet':{'units':[]},
              'selected_slice':'Controlled scheduler test','source':{'path':'source.txt','sha256':study.sha(source),
              'url':'https://example.test/source','media_type':'text/plain'}}
        study.save(p,task);refs.append({'task_id':tid,'path':p.name,'sha256':study.sha(p)})
    study.save(out/'task-freeze.json',{'tasks':refs});study.save(out/'conditional-case-reference.json',{'fixture':True})
    old=out/'prior.json';old.write_bytes(canonical({'maximum':1,'calls':[{'request_hash':'a'*64,'issued_at_ns':'1'}]}))
    grant=out/'grant.json';grant.write_bytes(canonical({'schema':'legalmath.additional-grant.v1',
        'grant_id':'local.scheduler.fixture','authorized_calls':500,'authorization':'Scripted transport only',
        'predecessor':{'path':'prior.json','sha256':raw_digest(old.read_bytes())},'ledger':'allowance.json'}))
    record=SimpleNamespace(pilot_complete=False,single_valid=True,seen=[])
    class Provider:
        def __init__(self,*,allowance,**kwargs):self.allowance=allowance
        def complete(self,*args):raise AssertionError('Scheduling fixture must not dispatch a model')
    class Runner:
        def __init__(self,root,directory,*args,**kwargs):self.directory=Path(directory)
        def run(self,*args,**kwargs):
            tid=self.directory.parent.name;record.seen.append((tid,'ensemble'))
            study.save(self.directory/'current.json',{'synthetic_only':True})
            path=self.directory/'packet.json';study.save(path,{'units':[]})
            return {'execution_complete':record.pilot_complete or tid!='fixture.0',
                    'packet':{'path':str(path.relative_to(tmp_path))}}
    def single(task,provider,directory):
        record.seen.append((task['task_id'],'single'))
        result={'candidates':{'controlled.reading':{}} if record.single_valid else {},'synthetic_only':True}
        study.save(directory/'result.json',result);return result
    def prepare(root,where,tasks):
        study.save(where/'study-source-freeze.json',{'synthetic_only':True})
        return {t['task_id']:{'task':t,'sources':[{'url':t['source']['url'],
            'media_type':'text/plain','data':source.read_bytes()}]} for t in tasks}
    for key,value in {'ROOT':tmp_path,'OUT':out,'GRANT':grant,'used':lambda:0,'prepare_sources':prepare,
        'rel':lambda p:str(Path(p).relative_to(tmp_path)),'CodexProvider':Provider,'ResumingCodex':Provider,
        'CompleteInvestigation':Runner,'single_reader':single,
        'verify':lambda *args:{'synthetic_only':True},
        'semantic_followups':lambda *args:{'synthetic_only':True}}.items():
        monkeypatch.setattr(study,key,value)
    return tmp_path,out,record


def test_incomplete_pilot_retains_all_tasks_and_blocks_peer_dispatch(harness):
    root,out,record=harness
    result=study.run(root/'phase')
    assert not result['execution_complete'] and result['selected_tasks']==4
    assert record.seen==[('fixture.0','single'),('fixture.0','ensemble')]
    assert all(r['ensemble']['status']=='NOT_STARTED_PENDING_PILOT_REPAIR' for r in result['tasks'][1:])
    # An EXECUTED summary with execution_complete=False must be revisited.
    record.pilot_complete=True;record.seen.clear()
    repaired=study.run(root/'repair-phase')
    assert repaired['execution_complete'] and repaired['complete_ensemble_investigations']==4
    assert ('fixture.0','ensemble') in record.seen and ('fixture.0','single') not in record.seen
    assert [r['task_id'] for r in repaired['tasks']]==['fixture.'+str(i) for i in range(4)]
    assert len(record.seen)==7
    assert list((out/'unfamiliar-study/fixture.0').glob('ensemble-prior-*.json'))


def test_no_valid_single_reading_cannot_pass_pilot(harness):
    root,out,record=harness;record.pilot_complete=True;record.single_valid=False
    result=study.run(root/'phase')
    assert not result['execution_complete']
    assert result['tasks'][0]['single']['status']=='INCOMPLETE'
    assert not result['tasks'][0]['single']['validated_interpretation_returned']
    assert all(tid=='fixture.0' for tid,_ in record.seen)


def test_reviewed_mechanism_pilot_schedules_every_task_without_promoting_incomplete_study(harness,monkeypatch):
    root,out,record=harness
    monkeypatch.setattr(study,'reviewed_pilot',lambda *args:{'workers':4,'continuation_id':'synthetic.reviewed.mechanism'})
    result=study.run(root/'phase')
    assert len(record.seen)==8 and {tid for tid,_ in record.seen}=={'fixture.'+str(i) for i in range(4)}
    assert not result['execution_complete'] and result['complete_ensemble_investigations']==3
    assert result['selected_tasks']==4 and result['reviewed_scheduling']['workers']==4


def test_character_capacity_can_split_short_unit_count_and_preserve_all_text(tmp_path):
    task={'packet':{'units':[{'unit_id':str(i),'text':'x'*300} for i in range(35)]}}
    assert study.inventory_profile(task,tmp_path)==(6000,40)
    assert sum(len(u['text']) for u in task['packet']['units'])==10500


def test_failed_fidelity_partition_shrinks_without_discarding_completed_batches(tmp_path):
    from legalmath.canonical import digest
    binding={'settings':{'max_fidelity_pairs_per_call':32}};revision=digest(binding)
    study.save(tmp_path/'revisions.json',[{'revision':revision,'binding':binding}])
    p=tmp_path/'revisions'/revision/'core/actions/action-0001/interpretation/fidelity-rounds/round-000/plan.json'
    study.save(p,{'failure':{'constraint':'validated_batch_unavailable'},'validated_batches':[]})
    assert study.fidelity_batch_profile(tmp_path)==12
    study.save(p,{'failure':{'constraint':'validated_batch_unavailable'},'validated_batches':[{'retained':True}]})
    assert study.fidelity_batch_profile(tmp_path)==32
    newer={'settings':{'max_fidelity_pairs_per_call':40}};new_revision=digest(newer)
    study.save(tmp_path/'revisions.json',[{'revision':revision,'binding':binding},{'revision':new_revision,'binding':newer}])
    study.save(tmp_path/'revisions'/new_revision/'core/actions/action-0001/interpretation/fidelity-rounds/round-000/plan.json',{'validated_batches':[]})
    assert study.fidelity_batch_profile(tmp_path)==32
