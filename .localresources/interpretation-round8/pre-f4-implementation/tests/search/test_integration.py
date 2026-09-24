from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.engine import Search
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.evaluation import compare_runs
from legalmath.interpretation.search import annotations
from legalmath.storage.archive import export_history,import_history
from legalmath.interpretation import Interpretations
from tests.search.support import packet,generation,FunctionProvider
from tests.search.test_engine import setup,answers


def test_search_archive_and_source_change(db,root,tmp_path):
    search=setup(db,root,tmp_path,FunctionProvider(answers),Settings(max_model_calls=3))
    report=search.drive();archive=tmp_path/'history.zip';export_history(db,archive)
    restored=import_history(archive,tmp_path/'restored')
    replay=Search(Interpretations(restored),'author',search.rid,FunctionProvider(answers),search.checker)
    assert replay.verify_report()==report
    replacement=packet();replacement['units'][0]['text']='A changed source.'
    search.s.invalidate_source('meaning','change',replacement['source_key'],replacement,'New source version')
    from legalmath.interpretation.review import guard
    with db.connect() as con:
        for node in search.state['nodes']:
            with pytest.raises(LegalMathError):guard(db,con,node['bundle_hash'])


def test_annotation_packets_are_source_first_and_require_distinct_reviewers(db,root,tmp_path):
    search=setup(db,root,tmp_path,FunctionProvider(answers),Settings(max_model_calls=3))
    service=search.s
    service.lc.register({n:{'token':n,'roles':['meaning']} for n in ('reviewer1','reviewer2','adjudicator')})
    annotations.assign(service,'author','assign',search.rid,['reviewer1','reviewer2'])
    with pytest.raises(LegalMathError):
        annotations.assign(service,'author','replace',search.rid,['reviewer2','adjudicator'])
    public=annotations.reviewer_packet(service,'reviewer1',search.rid)
    assert set(public)=={'packet_hash','source_packet','instructions'} and 'readings' not in str(public)
    a={'packet_hash':public['packet_hash'],'source_unit_id':'p1','duty':'Minimum history',
       'alternatives':['Inclusive six-month minimum'],'scope':'Fund returns','exceptions':[],
       'effective_time':'Unresolved','missing_authorities':[],'uncertainty':'Calendar definition'}
    with pytest.raises(LegalMathError):annotations.submit(service,'author','forge',search.rid,[a],True)
    with pytest.raises(LegalMathError):annotations.submit(service,'reviewer1','not-independent',search.rid,[a],False)
    annotations.submit(service,'reviewer1','a1',search.rid,[a],True)
    with pytest.raises(LegalMathError):annotations.freeze(service,'adjudicator','early',search.rid,{},'Not ready')
    annotations.submit(service,'reviewer2','a2',search.rid,[a],True)
    frozen=annotations.freeze(service,'adjudicator','freeze',search.rid,
        {'p1':{'accepted_readings':a['alternatives'],'unresolved':True,'reason':'Need calendar definition'}},'Both readings retained')
    assert not frozen['legal_accuracy_certified']
    from legalmath.interpretation.search.evaluation import compare_frozen
    results={'case':{'source_hash':public['packet_hash'],'budget':3,'status':'CLEAN','decision':a['alternatives'][0]}}
    assessed=compare_frozen(service,'adjudicator',results,results,
        {'case':{'run_id':search.rid,'source_unit_id':'p1'}})
    assert assessed['counts']['candidate']['unadjudicated']==1
    assert assessed['counts']['candidate']['correct_clean']==0
    assert assessed['reference_freeze_hashes']
    search.drive()
    with pytest.raises(LegalMathError):annotations.assign(service,'author','late',search.rid,['reviewer1','reviewer2'])


def test_all_abstain_cannot_be_promoted_or_hidden():
    ref={'x':{'source_hash':'a','accepted':['NO']},'y':{'source_hash':'b','accepted':None}}
    a={k:{'source_hash':v['source_hash'],'budget':8,'status':'CLEAN','decision':'YES'} for k,v in ref.items()}
    b={k:{**v,'status':'BLOCKED'} for k,v in a.items()}
    result=compare_runs(a,b,ref)
    assert result['counts']['baseline']['unsafe_clean']==1 and result['counts']['candidate']['blocked']==1
    assert result['counts']['candidate']['correct_clean']==0 and not result['promotion_eligible']
    b['x']['budget']=9
    with pytest.raises(LegalMathError):compare_runs(a,b,ref)


def test_cancelled_return_cannot_become_a_candidate(db,root,tmp_path):
    from legalmath.interpretation.reports import Reports
    holder={}
    def cancel(request):
        Reports(holder['search'].s).cancel('author','cancel',holder['search'].rid)
        return generation()
    search=setup(db,root,tmp_path,FunctionProvider(cancel));holder['search']=search
    report=search.drive()
    assert not search.state['nodes'] and not report['release_eligible']
    assert report['status']=='CANCELLED'
