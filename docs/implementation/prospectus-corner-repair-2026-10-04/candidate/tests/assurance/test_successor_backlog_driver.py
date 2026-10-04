"""Full retained denominator through scripted proposals; no remote model calls."""
import json
from pathlib import Path
import sys
import tempfile
from copy import deepcopy
import pytest
from legalmath.canonical import digest,canonical,raw_digest
from legalmath.interpretation.search.providers import CodexProvider,Completion
from legalmath.interpretation.assurance.rendered_provider import RenderedSourceProvider
from legalmath.errors import LegalMathError

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import assurance_successor_live as driver


def answer(request):
    task=request['task']
    if task=='SCOPED_SOURCE_FIDELITY':
        candidates={r['candidate_id']:r for r in request['candidates']}
        return {'checks':[{'claim_id':p['claim_id'],'candidate_id':p['candidate_id'],
            'source_support':{'status':'UNASSESSED','evidence':[],'rationale':'Scripted harness response, not a source judgment'},
            'question_relation':{'status':'UNASSESSED','question_hash':candidates[p['candidate_id']]['question_hash'],
                'evidence':[],'rationale':'Scripted harness response'},
            'executable_correspondence':{'status':'UNASSESSED','representation_quotes':[],'rationale':'Scripted harness response'},
            'authority':{'status':'UNASSESSED','dependency_ids':[],'rationale':'Scripted harness response'},
            'followup_questions':['Retain this unassessed controlled test item.']} for p in request['required_pairs']],
            'additional_concerns':[]}
    if task=='SOURCE_REGION_MATERIALITY':
        return {'judgments':[{'issue_id':r['issue_id'],'disposition':'LAYOUT_RELATION_UNCERTAIN',
            'printed_text':'Synthetic fixture; no actual visual judgment','explanation':'Scripted whole-driver check',
            'affected_condition':None} for r in request['issues']],'remaining_questions':['Unresolved fixture']}
    if task=='INVESTIGATE_AUTHORITY_QUESTION':
        return {'question_id':request['question']['id'],'status':'NOT_ESTABLISHED','proposition':'Controlled test, no authority judgment',
            'evidence':[],'missing_premises':['All actual source judgments remain unassessed in this fixture.'],
            'next_source_questions':['Review actual authority evidence separately.']}
    raise AssertionError(task)


def test_full_backlog_driver_accounts_for_every_source_and_pair(monkeypatch):
    with tempfile.TemporaryDirectory(prefix='successor-backlog-fixture-',dir=ROOT/'artifacts') as td:
        out=Path(td);old=out/'prior.json';old.write_bytes(canonical({'maximum':1,'calls':[{'request_hash':'a'*64,'issued_at_ns':'1'}]}))
        grant=out/'grant.json';grant.write_bytes(canonical({'schema':'legalmath.additional-grant.v1','grant_id':'controlled.fixture',
            'authorized_calls':500,'authorization':'Local scripted transport fixture only','predecessor':{'path':'prior.json','sha256':raw_digest(old.read_bytes())},
            'ledger':'local-allowance.json'}))
        class Fake(CodexProvider):
            def __init__(self,*,allowance):self.allowance=allowance;self.routing={'local_fixture':True}
            def complete(self,request,schema,settings):
                assert len(canonical(request))<=settings.max_input_bytes
                slot=self.allowance.reserve(digest(request))
                return Completion(answer(request),{'local_fixture':True,'allowance_slot':slot})
        class ImageFake(RenderedSourceProvider):
            def complete(self,request,schema,settings):
                assert len(canonical(request))+200<=settings.max_input_bytes
                slot=self.allowance.reserve(digest(request));self._check()
                return Completion(answer(request),{'local_fixture':True,'allowance_slot':slot,'source_image_hash':self.image_hash})
        monkeypatch.setattr(driver,'OUT',out);monkeypatch.setattr(driver,'GRANT',grant)
        monkeypatch.setattr(driver,'CodexProvider',Fake);monkeypatch.setattr(driver,'RenderedSourceProvider',ImageFake)
        result=driver.run(out/'phase')
        assert result['scoped_pairs']==232 and result['two_perspective_pairs']==232
        assert result['pairs_with_four_dimensions_assessed']==0
        assert result['pdf_items']==330 and result['authority_questions']==6
        assert not result['release_eligible'] and result['new_calls']<=260
        pdf=driver.read(out/'live-backlog/pdf/result.json')
        assert all(r['followup_attempted'] for r in pdf['items'])
        assert all(not r['source_materiality_certified'] for r in pdf['items'])
        authorities=driver.read(out/'live-backlog/authority/result.json')
        assert len(authorities['proposals'])==12
        assert all(r['result']['status']=='VALIDATED_PROPOSAL' for r in authorities['proposals'])
        # A completed visual investigation is verified from its original jobs,
        # never rebuilt in a potentially different parallel-completion order.
        from assurance_successor_audit import check_pdf_result
        pending=set(driver.read(ROOT/'artifacts/interpretation/round15/remaining-work.json')['pdf_pending_ids'])
        issues=[r for r in driver.read(ROOT/'artifacts/interpretation/round14/pdf-resolution.json')['issues']
                if r['issue_id'] in pending]
        path=out/'live-backlog/pdf/result.json';before=path.read_bytes()
        assert check_pdf_result(path,ROOT,issues)['issues']==330
        pdf['items'][0]['proposals'][0]['printed_text']='A detached altered transcription'
        driver.save(path,pdf)
        with pytest.raises(LegalMathError):check_pdf_result(path,ROOT,issues)
        path.write_bytes(before)
