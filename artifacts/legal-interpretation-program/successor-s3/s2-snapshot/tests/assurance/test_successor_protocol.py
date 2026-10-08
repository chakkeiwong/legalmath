from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2
from .test_round16 import scoped_fixture


def test_authority_contract_distinguishes_passage_ids_from_external_dependencies():
    p,c,r,q,v=scoped_fixture();req=fidelity_v2.request(p,c,r,q)
    rules=req['authority_field_contract']
    assert rules['source_unit_ids_are_not_dependency_ids']
    assert rules['bound_dependency_ids']==[d['dependency_id'] for d in p['dependencies'] if d['source_hash']]
    assert 'NONE_DECLARED' in rules and 'source_support' in rules['NONE_DECLARED']


def test_invalid_authority_response_identifies_exact_repair_without_relaxing_check():
    p,c,r,q,v=scoped_fixture();row=v['checks'][0]
    row['authority']={'status':'AVAILABLE','dependency_ids':[p['units'][0]['unit_id']],
                       'rationale':'Confused source-passage identity with external source dependency'}
    with pytest.raises(LegalMathError) as caught:fidelity_v2.validate(v,p,c,r,q)
    d=caught.value.details
    assert caught.value.code=='E_REFERENCE' and d['candidate_id']==row['candidate_id']
    assert d['claim_id']==row['claim_id'] and d['field']=='authority.dependency_ids'
    assert d['provided_ids']==[p['units'][0]['unit_id']] and 'bound_dependency_ids' in d


def test_inexact_quote_feedback_locates_the_failed_pair():
    p,c,r,q,v=scoped_fixture();row=v['checks'][0]
    row['source_support']['evidence'][0]['quote']='A fabricated quote'
    with pytest.raises(LegalMathError) as caught:fidelity_v2.validate(v,p,c,r,q)
    assert caught.value.details['field']=='source_support.evidence'
    assert caught.value.details['invalid_quote']['quote']=='A fabricated quote'


def test_previously_unidentified_missing_authority_stays_missing_without_invented_id():
    p,c,r,q,v=scoped_fixture();row=v['checks'][0]
    row['authority']={'status':'MISSING','dependency_ids':[],
                      'rationale':'A separately supplied schema is needed but has no identifiable catalogue entry.'}
    row['followup_questions']=['Obtain the separately supplied JFIU XML schema and bind its actual source identity.']
    result=fidelity_v2.validate(v,p,c,r,q)
    assert result['checks'][0]['authority']['status']=='MISSING'
    assert fidelity_v2.reconcile([result,result],attempt=3)['status']=='UNCERTAINTY_REPORTED'
    row['followup_questions']=[]
    with pytest.raises(LegalMathError):fidelity_v2.validate(v,p,c,r,q)


def test_positive_labels_cannot_hide_an_explicit_followup_question():
    p,c,r,q,v=scoped_fixture()
    v['checks'][0]['followup_questions']=['Does an incorporated exception alter this stated condition?']
    v=fidelity_v2.validate(v,p,c,r,q)
    first=fidelity_v2.reconcile([v,v],attempt=1)
    assert first['status']=='REPAIR_REQUESTED' and first['additional_processing_required']
    last=fidelity_v2.reconcile([v,v],attempt=3)
    assert last['status']=='UNCERTAINTY_REPORTED' and not last['additional_processing_required']
    assert last['continuation_policy']=='explicit-followups.v1'


def test_question_hash_repair_identifies_the_exact_pair_and_expected_binding():
    p,c,r,q,v=scoped_fixture();row=v['checks'][0];row['question_relation']['question_hash']='0'*64
    with pytest.raises(LegalMathError) as caught:fidelity_v2.validate(v,p,c,r,q)
    assert caught.value.code=='E_STALE_REVIEW'
    assert caught.value.details['field']=='question_relation.question_hash'
    assert caught.value.details['candidate_id']==row['candidate_id']
    assert caught.value.details['expected_hash']!='0'*64


def test_open_question_executes_the_next_bounded_round(tmp_path):
    from tests.search.support import FunctionProvider
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    p,c,r,q,v=scoped_fixture();v['checks'][0]['followup_questions']=['Investigate this remaining source qualification.']
    provider=FunctionProvider(lambda request:deepcopy(v))
    result=investigate(p,c,r,q,provider,tmp_path,maximum_rounds=2,maximum_actions=4)
    assert len(provider.requests)==4
    assert result['status']=='UNCERTAINTY_REPORTED' and result['journal_actions']==4
