from copy import deepcopy
from dataclasses import replace
import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.question_scope import scopes
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.search.providers import Completion
from scripts.legal_integration_reopening_live import fixture
from tests.assurance.test_bounded_product import envelope, limits, Scripted
from tests.assurance.test_requirement_correction import setup_product


def test_closed_scope_requires_explicit_declaration_and_survives_all_requests(tmp_path):
    original=fixture(explicit_scope=True)
    provider=Scripted()
    product=BoundedProduct(tmp_path,tmp_path/'product',provider,original,list,
        limits=replace(limits(),input_tokens=80000))
    packets,blocked=product.reading_packets()
    assert not blocked
    expected=scopes(original)
    assert all(p['request']['question_scope']==expected for p in packets)
    records=[r for r in product.route.records.values() if r['kind']=='source']
    for task in ('RESOLVE_SOURCE_DEPENDENCY','ANSWER_ORIGINAL_QUESTION','CORRECT_REVIEWED_ANSWER',
                 'AUDIT_ANSWER_AGAINST_SOURCE','ASSESS_REVIEW_WARRANT'):
        request=product.request(task,original['original_questions'][0],records,payload={},expected=[])
        assert request['question_scope']==expected
    assert scopes(fixture())['questions'][0]['mode']=='OPEN_CORPUS'
    assert scopes(fixture(explicit_scope=True,missing_authority=True))['questions'][0]['mode']=='OPEN_CORPUS'
    original['question_scopes']['foreign']={'mode':'SUPPLIED_RULES_ONLY','basis':'bad'}
    with pytest.raises(LegalMathError):scopes(original)


@pytest.mark.parametrize('disposition', ['UNWARRANTED','UNRESOLVED'])
def test_bad_or_unresolved_review_cannot_change_answer(tmp_path,disposition):
    provider,product,answer,details,review=setup_product(tmp_path)
    details[0]['result']['value']['conclusion']='Exception accounted for.'
    original=deepcopy(answer); complete=provider.complete
    def respond(request,schema,settings):
        response=complete(request,schema,settings)
        if request['task']=='ASSESS_REVIEW_WARRANT':
            for row in response.value['decisions']:
                row.update(disposition=disposition,basis='QUESTION_SCOPE',reason='Objection imports hypothetical outside authority.')
        return response
    provider.complete=respond
    candidate,fresh,retained=product.correct_answer('p14',envelope()['original_questions'][0],answer,[review],details,[])
    assert candidate==original
    assert not any(r['task'].startswith('CORRECT_REVIEWED_') for r in provider.requests)
    assert retained['original_reviews']==[review]
    if disposition=='UNRESOLVED':
        assert fresh==[review] and retained['status']=='WARRANT_UNRESOLVED'
    else:
        assert fresh and all(r['value']['verdict']=='ACCEPT' for r in fresh)


def test_fresh_rejection_still_blocks_after_unwarranted_initial_review(tmp_path):
    provider,product,answer,details,review=setup_product(tmp_path)
    complete=provider.complete
    def respond(request,schema,settings):
        response=complete(request,schema,settings)
        if request['task']=='ASSESS_REVIEW_WARRANT':
            for row in response.value['decisions']:row['disposition']='UNWARRANTED'
        return response
    provider.complete=respond
    _,fresh,retained=product.correct_answer('p14',envelope()['original_questions'][0],answer,[review],details,[])
    assert any(r['value']['verdict']=='REJECT' for r in fresh)
    assert retained['status']=='REVIEWED'
