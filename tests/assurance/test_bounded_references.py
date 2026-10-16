from copy import deepcopy

import pytest
from jsonschema import ValidationError

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import ContextRoute
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, AUDIT
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def test_exact_span_expansion_preserves_unicode_and_rejects_foreign_selection():
    original = envelope()
    original['source_packet']['units'][0]['text'] = 'Custody is not ownership. 所有權≠保管。\nRetain the exception.'
    route = ContextRoute(original, list, limits=limits())
    source = next(r for r in route.records.values() if r['kind'] == 'source')
    packet = route.make_packet('READ_SOURCE', [source['id']])
    prepared = prepare(packet['request'], packet['schema'])
    wire = {'records': [{'id': 'r0', 'status': 'PROPOSED', 'findings': [{
        'statement': 'The distinction and exception are preserved.',
        'support': [{'span_id': 's0'}], 'contrary': []}], 'open_dependencies': []}]}
    result = resolve(wire, prepared, maximum_bytes=24000)
    assert result['records'][0]['id'] == source['id']
    assert result['records'][0]['findings'][0]['support'][0] == {
        'record_id': source['id'], 'quote': source['text']}
    route.validate_response(packet, result)
    wire['records'][0]['findings'][0]['support'][0]['span_id'] = 's9999'
    with pytest.raises(ValidationError): resolve(wire, prepared, maximum_bytes=24000)


def test_requirement_observation_cannot_become_legal_source_support():
    route = ContextRoute(envelope(), list, limits=limits())
    rid = 'obligation:o1'
    packet = route.make_packet('REVIEW_REQUIREMENTS', [rid])
    prepared = prepare(packet['request'], packet['schema'])
    wire = {'records': [{'id': 'r0', 'status': 'UNRESOLVED', 'findings': [],
        'observations': [{'observation_id': next(k for k,v in prepared['observations'].items()
            if v['path']==['statement']), 'statement': 'The requirement asks for exceptions.'}],
        'open_dependencies': ['The governing legal source remains necessary.']}]}
    result = resolve(wire, prepared, maximum_bytes=24000)
    route.validate_response(packet, result)
    false_source = deepcopy(result)
    false_source['records'][0]['findings'] = [{'statement': 'The law requires this.',
        'support': [{'record_id': rid, 'quote': 'Preserve exceptions.'}], 'contrary': []}]
    with pytest.raises(ValidationError): route.validate_response(packet, false_source)
    result['records'][0]['observations'][0]['path'] = ['missing']
    with pytest.raises(LegalMathError): route.validate_response(packet, result)


def test_source_gap_is_packet_limited_and_cannot_support_an_assertion(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path/'product', Scripted(), envelope(), list, limits=limits())
    # Index integrity is checked at product construction in real runs. This fixture
    # isolates reporting rules from the already-tested original-byte index builder.
    index = {'index_hash': digest('fixture'), 'units': {'source.a': {'locators': ['P10'],
        'unit_hash': digest(product.route.units['source.a'])}}}
    product.route.envelope['legal_indexes'] = [index]
    source = next(r for r in product.route.records.values() if r['kind'] == 'source')
    value = {'reason': 'The requested provision is not verified in this packet.', 'support': [],
        'verdict': 'UNRESOLVED', 'source_gaps': [{'index_hash': index['index_hash'], 'locator': 'P14',
            'status': 'NOT_VERIFIED_IN_DELIVERED_RECORDS'}]}
    product.citations(value, [source])
    value['reason'] = 'Paragraph 14 establishes compliance.'
    with pytest.raises(LegalMathError): product.citations(value, [source])
    value['reason'] = 'The requested provision is not verified in this packet.'
    value['source_gaps'][0]['locator'] = 'P10'
    with pytest.raises(LegalMathError): product.citations(value, [source])


def test_reference_table_tampering_and_expansion_budget_are_rejected():
    route = ContextRoute(envelope(), list, limits=limits())
    source = next(r for r in route.records.values() if r['kind'] == 'source')
    request = {'records': [source], 'required_considered': [source['id']]}
    prepared = prepare(request, NOTE)
    wire = {'conclusion': 'Conditional.', 'support': [{'span_id': 's0'}],
        'contrary': [], 'assumptions': [], 'unresolved': ['Facts remain unknown.'],
        'alternatives': [], 'considered': {'c0': 'r0'}, 'source_gaps': [], 'assertion_bindings': []}
    with pytest.raises(LegalMathError): resolve(wire, prepared, maximum_bytes=5)
    prepared['references']['spans'][0]['start_codepoint'] = 1
    with pytest.raises(LegalMathError): resolve(wire, prepared, maximum_bytes=24000)


def test_wire_mandatory_population_is_exact_and_review_accept_cannot_hide_issues():
    route = ContextRoute(envelope(), list, limits=limits())
    source = next(r for r in route.records.values() if r['kind'] == 'source')
    request = {'records': [source], 'required_considered': [source['id']]}
    prepared = prepare(request, NOTE)
    value = {'conclusion': 'Conditional.', 'support': [{'span_id': 's0'}],
        'contrary': [], 'assumptions': [], 'unresolved': ['Facts remain unknown.'],
        'alternatives': [], 'considered': {'c0': 'r0'}, 'source_gaps': [],
        'assertion_bindings': []}
    assert resolve(value, prepared, maximum_bytes=24000)['considered'] == [source['id']]
    for changed in ({}, {'c0': 'r0', 'c1': 'r0'}, {'c0': 'unknown'}):
        bad = deepcopy(value); bad['considered'] = changed
        with pytest.raises(ValidationError): resolve(bad, prepared, maximum_bytes=24000)

    review = prepare(request, AUDIT)
    accepted = {'review': {'verdict': 'ACCEPT', 'support': [{'span_id': 's0'}], 'issues': []},
        'considered': {'c0': 'r0'}, 'reason': 'The scoped passage supports this answer.',
        'source_gaps': [], 'assertion_bindings': []}
    result = resolve(accepted, review, maximum_bytes=24000)
    assert result['verdict'] == 'ACCEPT' and result['considered'] == [source['id']]
    for mutation in ({'issues': ['An issue remains.']}, {'support': []}):
        bad = deepcopy(accepted); bad['review'].update(mutation)
        with pytest.raises(ValidationError): resolve(bad, review, maximum_bytes=24000)


def test_ambiguous_short_spans_are_not_offered_but_complete_source_is_retained():
    source = {'id':'source.r', 'kind':'source', 'unit_id':'r', 'normative':True,
        'locator':'r', 'text':'x'*256 + 'distinct passage' + 'x'*256}
    prepared = prepare({'records':[source], 'required_considered':[]},NOTE)
    assert prepared['request']['records'][0]['text'] == source['text']
    for span in prepared['response_spans'] if 'response_spans' in prepared else prepared['request']['response_spans']:
        assert source['text'].count(source['text'][span['start_codepoint']:span['end_codepoint']]) == 1
    assert any(s['start_codepoint']==0 and s['end_codepoint']==len(source['text'])
               for s in prepared['request']['response_spans'])
