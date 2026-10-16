from copy import deepcopy
import json

import pytest
from jsonschema import ValidationError

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def note():
    return {'conclusion': 'Conditional.', 'support': [{'span_id': 's0'}],
            'contrary': [], 'assumptions': [], 'unresolved': ['Facts unknown.'],
            'alternatives': [], 'considered': [], 'source_gaps': [], 'assertion_bindings': []}


def test_atomic_quote_contract_excludes_actual_malformed_patterns(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path/'p', Scripted(), envelope(), list, limits=limits())
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    prepared = prepare({'records': records, 'required_considered': []}, NOTE)
    for malformed in ({'span_ids': ['s0', 's1']},
                      {'span_id': ['s0', 's1']},
                      {'span_id': 's0', 'locator': '26EC22 P10'}):
        value = note(); value['support'] = [malformed]
        with pytest.raises(ValidationError): resolve(value, prepared, maximum_bytes=24000)
    value = note(); value['support'].append({'span_id': 's1'})
    out = resolve(value, prepared, maximum_bytes=24000)
    assert len({r['record_id'] for r in out['support']}) == 2
    assert [r['quote'] for r in out['support']] == [r['text'] for r in records]


def test_locators_and_source_gaps_are_bound_choices(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path/'p', Scripted(), envelope(), list, limits=limits())
    source = next(r for r in product.route.records.values() if r['kind'] == 'source')
    request = {'records': [source], 'required_considered': [],
        'verified_locator_bindings': [{'record_id': source['id'], 'index_hash': 'fixture',
            'quote_ranges': [{'start': 0, 'end': len(source['text']), 'locator': 'P10'}]}],
        'unverified_source_locators': [{'index_hash': 'fixture', 'locator': 'P14',
            'status': 'NOT_VERIFIED_IN_DELIVERED_RECORDS'}]}
    prepared = prepare(request, NOTE); value = note()
    value['source_gaps'] = [{'gap_id': 'g0'}]
    out = resolve(value, prepared, maximum_bytes=24000)
    assert out['support'][0]['locator'] == 'P10'
    assert out['source_gaps'] == request['unverified_source_locators']
    changed = deepcopy(prepared); changed['locators']['s0'] = 'P20'
    with pytest.raises(LegalMathError): resolve(value, changed, maximum_bytes=24000)
    value['source_gaps'] = [{'index_hash': 'fixture', 'locator': 'P10',
                            'status': 'NOT_VERIFIED_IN_DELIVERED_RECORDS'}]
    with pytest.raises(ValidationError): resolve(value, prepared, maximum_bytes=24000)


@pytest.mark.parametrize('code', ['E_AUTHORITY', 'E_INTEGRITY'])
def test_dispatch_veto_is_retained_and_remains_a_veto_on_resume(tmp_path, code):
    class Refused(Scripted):
        def complete(self, request, schema, settings):
            self.requests.append(request)
            raise LegalMathError(code, details='Changed bound authority or implementation')
    provider = Refused()
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list, limits=limits())
    for _ in range(2):
        with pytest.raises(LegalMathError) as caught: product.investigate()
        assert caught.value.code == code
    assert len(provider.requests) == 1
    result = json.loads((tmp_path/'p/calls/read-0000/result.json').read_text())
    assert result['continuation_veto'] and result['status'] == 'FAILED'


def test_generation_receives_actual_expression_grammar(tmp_path):
    from scripts.legal_integration_rehearsal import UnresolvedProvider
    from legalmath.interpretation.search.models import GRAMMAR
    provider = UnresolvedProvider()
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list, limits=limits())
    product.tools('p14', envelope()['original_questions'][0], None)
    request = json.loads((tmp_path/'p/calls/candidates-p14/request.json').read_text())
    assert GRAMMAR in request['instructions']


def test_invalid_candidate_or_unsupported_tool_cannot_claim_effect():
    from scripts.legal_integration_campaign import validate_effect
    class Evaluator:
        def citations(self, value, sources): pass
    answer = {'answer': {'value': {'conclusion': 'Conditional conclusion.'}}, 'review_accepted': True,
              'tools': [{'id': 'tool-formal', 'value': {'status': 'PASS'}}]}
    value = {'effect': 'helps', 'baseline_quote': 'Conditional', 'candidate_quote': 'Conditional',
             'support': [{'record_id': 'source', 'quote': 'Evidence'}], 'unresolved': []}
    validate_effect(value, answer, answer, Evaluator(), [])
    for candidate in ({**answer, 'review_accepted': False},
                      {**answer, 'tools': [{'id': 'tool-formal', 'value': {'status': 'UNSUPPORTED'}}]}):
        with pytest.raises(ValueError): validate_effect(value, answer, candidate, Evaluator(), [])
        validate_effect({**value, 'effect': 'insufficient'}, answer, candidate, Evaluator(), [])


def test_question_filter_preserves_shared_reading_keys(tmp_path):
    original = envelope()
    original['original_questions'].append({'question_id': 'gatecoin', 'text': 'Separate question'})
    original['source_question_ids'] = {'source.a': ['gatecoin'], 'source.b': ['p14']}
    provider = Scripted()
    full = BoundedProduct(tmp_path, tmp_path/'full', provider, original, list, limits=limits())
    full.investigate()
    selected = BoundedProduct(tmp_path, tmp_path/'selected', provider, original, list,
        limits=limits(), active_questions=['p14'], shared_prefix=tmp_path/'full/calls')
    before = len(provider.requests)
    result = selected.investigate()
    assert len(provider.requests) == before
    assert result['question_acquisition_complete']['p14']
    assert not result['question_acquisition_complete']['gatecoin']
    assert all(r.get('unit_id') != 'source.a' for o in result['outputs'] for r in o['request']['records'])


def test_pre_dispatch_local_failure_does_not_cancel_siblings(tmp_path, monkeypatch):
    product = BoundedProduct(tmp_path, tmp_path/'p', Scripted(), envelope(), list, limits=limits())
    actual = product.dispatch.call
    def call(key, *args):
        if key == 'read-0000':
            raise LegalMathError('E_RESOURCE_LIMIT', details='Oversized local packet')
        return actual(key, *args)
    monkeypatch.setattr(product.dispatch, 'call', call)
    result = product.investigate()
    assert result['outputs'][0]['result']['status'] == 'FAILED'
    assert result['outputs'][-1]['result']['status'] == 'VALIDATED'
    assert not result['question_acquisition_complete']['p14']


def test_boolean_adapter_rejects_undeclared_fact_before_native_call(tmp_path, monkeypatch):
    from scripts import legal_integration_tools as native
    def forbidden(*args, **kwargs): raise AssertionError('Invalid formula reached native worker')
    monkeypatch.setattr(native, 'worker', forbidden)
    candidate={'citations':[{'unit_id':'u','quote':'Conditional source.'}],
        'formalization':{'result_type':'bool','facts':[], 'scope':'true','result':'invented'}}
    packet={'units':[{'unit_id':'u','text':'Conditional source.'}]}
    result=native.ProductToolBackend(['legalruleml']).candidates(packet,{'candidate':candidate},tmp_path)
    assert result['status']=='UNSUPPORTED'
    assert result['unsupported'][0]['reason']=='UNDECLARED_FACT'
