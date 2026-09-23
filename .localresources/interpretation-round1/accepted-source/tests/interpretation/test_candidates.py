import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import reference_policy

def test_minority_and_parent_preserved(svc,run,proposal):
    a=svc.propose('author','a',run['run_id'],proposal)
    b=svc.propose('author','b',run['run_id'],{**proposal,'controlled_language':'Product type also sufficient','family_ids':['alternative'],'parent_id':a['candidate_id'],'revision_reason':'Footnote route'})
    values=svc.read('meaning',run['run_id'])['records']['candidate']
    assert len(values)==2 and values[0]==a and values[1]['parent_id']==a['candidate_id']
    assert b['probability_of_legal_correctness'] is None

@pytest.mark.parametrize('change',[{'source_packet_hash':'0'*64},{'source_unit_ids':['invented']},{'family_ids':['new']},{'reviewer_role':'meaning'},{'parent_id':'missing'}])
def test_untrusted_candidate(svc,run,proposal,change):
    with pytest.raises(LegalMathError): svc.propose('author','bad',run['run_id'],{**proposal,**change})

def test_cap_keeps_frontier_and_issue(svc,packet,proposal):
    run=svc.create('author','capped',packet,{**reference_policy(),'max_candidates':1})
    proposal['source_packet_hash']=run['source_packet_hash']
    svc.propose('author','first',run['run_id'],proposal)
    result=svc.propose('author','minority',run['run_id'],{**proposal,'family_ids':['alternative']})
    records=svc.read('meaning',run['run_id'])['records']
    assert result['deferred'] and records['frontier'][0]['proposal']['family_ids']==['alternative']
    assert records['issue'][0]['kind']=='SEARCH_INCOMPLETE'

def test_assumption_creates_issue(svc,run,proposal):
    proposal['assumptions']=[{'assumption_id':'assumption','statement':'Type means risk class','provenance_refs':[],'status':'PROVISIONAL'}]
    c=svc.propose('author','a',run['run_id'],proposal)
    assert c['issue_ids']

def test_frontier_bundle_is_also_release_bound(svc,packet,proposal,case):
    from legalmath.interpretation.review import guard
    run=svc.create('author','cap2',packet,{**reference_policy(),'max_candidates':1})
    proposal['source_packet_hash']=run['source_packet_hash']
    svc.propose('author','p1',run['run_id'],proposal)
    bh=svc.lc.create('author','bundle',case['bundle'])['bundle_hash']
    result=svc.propose('author','p2',run['run_id'],{**proposal,'bundle_hash':bh})
    assert result['deferred']
    with svc.db.connect() as con:
        assert con.execute('SELECT count(*) FROM interpretation_bindings WHERE bundle_hash=?',(bh,)).fetchone()[0]==1
        with pytest.raises(LegalMathError): guard(svc.db,con,bh)


def test_cyclic_argument_is_rejected(svc,run,proposal):
    proposal['arguments']=[dict(argument_id='arg',conclusion='Circular argument',premise_refs=['arg'],inference='self',inference_kind='STRICT',source_refs=['p10'],opposes_argument_ids=[])]
    with pytest.raises(LegalMathError,match='cycle|Cycle|cyclic'):
        svc.propose('author','cycle',run['run_id'],proposal)
