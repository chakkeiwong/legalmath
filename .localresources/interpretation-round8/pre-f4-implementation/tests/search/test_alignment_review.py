from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from legalmath.api.app import create_app
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation import Interpretations
from legalmath.interpretation.search import alignment_review as ar
from legalmath.interpretation.search.engine import Search
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.review import guard
from legalmath.storage.archive import export_history, import_history
from tests.search.support import packet, generation, FunctionProvider
from tests.search.test_alignment import proposal
from tests.search.test_engine import setup, AT


@pytest.fixture
def finished(db, root, tmp_path):
    def responses(request):
        value = generation('>' if request['role'] == 'alternatives' else '>=')
        if request['role'] == 'alternatives':
            value['readings'][0]['formalization']['facts'][0]['meaning'] = 'Months under a different cutoff convention'
        return value
    provider = FunctionProvider(responses)
    search = setup(db, root, tmp_path, provider, Settings(max_model_calls=3))
    report = search.drive()
    assert report['status'] == 'BLOCKED_UNRESOLVED'
    search.s.lc.register({'reviewer': {'token': 'reviewer', 'roles': ['meaning']},
                         'other': {'token': 'other', 'roles': ['author']}})
    a, b = search.state['nodes']
    p = proposal(a['reading'], b['reading'], {'months':'months'})
    return search, a, b, p, report


def save(finished):
    s, a, b, p, _ = finished
    return ar.propose(s.s, 'author', 'alignment', s.rid, a['node_id'], b['node_id'], p)


def test_proposal_and_review_preserve_search_report_and_survive_archive(finished, tmp_path):
    s, a, b, p, report = finished
    review_packet = ar.packet(s.s, 'reviewer', s.rid, a['node_id'], b['node_id'])
    assert review_packet['left'] == a['reading'] and review_packet['right'] == b['reading']
    saved = save(finished)
    assert ar.propose(s.s, 'author', 'duplicate', s.rid, a['node_id'], b['node_id'], p) == saved
    with pytest.raises(LegalMathError):
        ar.propose(s.s, 'author', 'alignment', s.rid, a['node_id'], b['node_id'], {**p,'rationale':'Changed rationale'})
    for caller in ('author','other'):
        with pytest.raises(LegalMathError):
            ar.review(s.s,caller,'forge.'+caller,s.rid,saved['alignment_id'],saved['proposal_hash'],
                      'ACCEPT_FOR_CONDITIONAL_ANALYSIS','Claimed approval',['p1'])
    with pytest.raises(LegalMathError):
        ar.review(s.s,'reviewer','stale',s.rid,saved['alignment_id'],'0'*64,'UNRESOLVED','Missing date convention',['p1'])
    with pytest.raises(LegalMathError):
        ar.review(s.s,'reviewer','bad-unit',s.rid,saved['alignment_id'],saved['proposal_hash'],'UNRESOLVED','Missing date convention',['missing'])
    reviewed = ar.review(s.s,'reviewer','review',s.rid,saved['alignment_id'],saved['proposal_hash'],
                         'ACCEPT_FOR_CONDITIONAL_ANALYSIS','Investigate the hypothesis, without accepting legal meaning',['p1'])
    assert not reviewed['legal_source_commitment_resolved']
    assert s.verify_report() == report
    with s.db.connect() as con:
        for n in s.state['nodes']:
            with pytest.raises(LegalMathError): guard(s.db,con,n['bundle_hash'])
    archive = tmp_path/'with-alignment.zip'; export_history(s.db, archive)
    restored = Interpretations(import_history(archive, tmp_path/'restored'))
    assert ar.read(restored,'reviewer',s.rid,saved['alignment_id']) == ar.read(s.s,'reviewer',s.rid,saved['alignment_id'])
    assert Search(restored,'author',s.rid,s.provider,s.checker).verify_report() == report


def test_conditional_analysis_and_later_rejection_are_separate_immutable_evidence(finished, root):
    s, _, _, _, report = finished; saved=save(finished)
    at=AT; domain={'months':{'min':'0','max':'12','allow_unknown':True}}
    result=ar.analyze(s.s,'author','analysis',s.rid,saved['alignment_id'],at,domain,
                      root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
    assert result['result']['status']=='CONDITIONAL_ANALYSIS'
    assert result['result']['encoded_comparison']['status']=='DIFFERENT'
    assert len(result['java_checks'])==2 and not result['release_eligible']
    ar.review(s.s,'reviewer','reject',s.rid,saved['alignment_id'],saved['proposal_hash'],
              'REJECT','The two calendar conventions should not be equated',['p1'])
    detail=ar.read(s.s,'author',s.rid,saved['alignment_id'])
    assert detail['current_decision']=='REJECT' and detail['analyses']==[result]
    with pytest.raises(LegalMathError):
        ar.analyze(s.s,'author','new-analysis',s.rid,saved['alignment_id'],at,domain,
                   root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
    assert s.verify_report()==report


def test_changed_source_invalidates_existing_correspondence(finished):
    s, a, b, p, _=finished;saved=save(finished)
    changed=packet();changed['units'][0]['text']='The requirement has changed.'
    s.s.invalidate_source('reviewer','source-change',changed['source_key'],changed,'Replacement source')
    for op in (
        lambda:ar.packet(s.s,'author',s.rid,a['node_id'],b['node_id']),
        lambda:ar.propose(s.s,'author','new-proposal',s.rid,a['node_id'],b['node_id'],p),
        lambda:ar.read(s.s,'reviewer',s.rid,saved['alignment_id']),
        lambda:ar.review(s.s,'reviewer','late-review',s.rid,saved['alignment_id'],saved['proposal_hash'],'UNRESOLVED','Old source',['p1'])):
        with pytest.raises(LegalMathError) as error:op()
        assert error.value.code=='E_STALE_REVIEW'


def test_rejection_arriving_during_local_analysis_is_rechecked(finished, root, monkeypatch):
    s, _, _, _, _=finished;saved=save(finished)
    original=ar.Comparisons.compare_conditional
    def concurrent_rejection(checker,*args):
        result=original(checker,*args)
        ar.review(s.s,'reviewer','concurrent-reject',s.rid,saved['alignment_id'],saved['proposal_hash'],
                  'REJECT','Reject correspondence while local compilation is in progress',['p1'])
        return result
    monkeypatch.setattr(ar.Comparisons,'compare_conditional',concurrent_rejection)
    with pytest.raises(LegalMathError) as error:
        ar.analyze(s.s,'author','analysis',s.rid,saved['alignment_id'],AT,None,
                   root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
    assert error.value.code=='E_RELEASE_BLOCKED'
    assert ar.read(s.s,'author',s.rid,saved['alignment_id'])['analyses']==[]


def test_alignment_api_enforces_roles_and_server_toolchain(finished):
    s,a,b,p,_=finished
    app=create_app(s.db.root,run_jobs=False)
    base='/v1/interpretation-search/'+s.rid
    headers={'Authorization':'Bearer author','Idempotency-Key':'api-proposal'}
    with TestClient(app) as client:
        bad=client.get(base+'/fact-correspondence',params={'left_node_id':a['node_id'],'right_node_id':b['node_id']},
                       headers={'Authorization':'Bearer other'})
        assert bad.status_code==403
        body={'left_node_id':a['node_id'],'right_node_id':b['node_id'],'proposal':p}
        created=client.post(base+'/alignments',json=body,headers=headers)
        assert created.status_code==201,created.text
        saved=created.json();url=base+'/alignments/'+saved['alignment_id']
        forged=client.post(url+'/review',headers={**headers,'Idempotency-Key':'review'},json={
            'proposal_hash':saved['proposal_hash'],'decision':'ACCEPT_FOR_CONDITIONAL_ANALYSIS',
            'rationale':'Claim approval','evidence_refs':['p1']})
        assert forged.status_code==403
        unsupported=client.post(url+'/analyze',headers={**headers,'Idempotency-Key':'analyze'},json={'at':AT})
        assert unsupported.status_code==422 and unsupported.json()['error']=='E_DEPENDENCY'
        command=client.post(url+'/analyze',headers={**headers,'Idempotency-Key':'command'},json={'at':AT,'jdk':'/arbitrary/executable'})
        assert command.status_code==422
        viewed=client.get(url,headers={'Authorization':'Bearer reviewer'})
        assert viewed.status_code==200 and viewed.json()['current_decision']=='UNREVIEWED'
