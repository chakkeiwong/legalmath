"""Alias spelling must preserve the actual source/executable contracts."""
from copy import deepcopy

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import source_references as sources
from legalmath.interpretation.assurance import executable_references_v2 as expressions
from legalmath.interpretation.assurance import fidelity_v2 as fv
from scripts import legal_coverage_aliases as aliases
from .test_integration_assessment import limited_fixture
from .test_round16 import scoped_fixture


def fixture(status='UNAVAILABLE', *, extra_unit=False):
    p, claims, candidates, questions, answer = scoped_fixture() if status == 'PRESERVES' else limited_fixture(status)
    if extra_unit:
        p['units'].append({**p['units'][0], 'unit_id': 'p2', 'locator': 'paragraph 2',
                           'text': 'The discount exception does not establish general compliance.'})
    request = fv.request(p, claims, candidates, questions)
    schema = fv.FidelityV2.model_json_schema()
    executable_wire, executable_schema, erefs = expressions.prepare(request, schema, readings=candidates, questions=questions)
    wire, wire_schema, srefs = sources.prepare(executable_wire, executable_schema)
    value = deepcopy(answer)
    for row in value['checks']:
        for key in ('source_support', 'question_relation'):
            row[key]['evidence'] = [{'span_ids': [next(s['span_id'] for s in srefs['spans'] if s['unit_id'] == q['unit_id'])]}
                                   for q in row[key]['evidence']]
        if row['executable_correspondence']['representation_quotes']:
            row['executable_correspondence']['representation_quotes'] = [next(s['span_id'] for s in erefs['spans'] if s['expression_kind'] == 'result')]
    return wire, wire_schema, value, (p, claims, candidates, questions), (request, schema, executable_schema, erefs, srefs)


@pytest.mark.parametrize('status', ['UNAVAILABLE', 'BLOCKED', 'PRESERVES'])
def test_exact_roundtrip_preserves_judgments_and_passes_original_validators(status):
    wire, schema, original, inputs, context = fixture(status)
    model_wire, _, references = aliases.prepare(wire, schema)
    encoded = aliases.encode_response(original, wire, schema)
    decoded = aliases.resolve(encoded, wire, schema, references)
    assert decoded == original and model_wire['source_packet'] == wire['source_packet']
    assert 'original_request' not in model_wire
    assert model_wire['response_identity_aliases']['pairs']['p0'] == references['pairs']['p0']
    assert model_wire['response_schema']['$defs']['Quote']['properties']['span_ids']['items']['enum'][0] == 's0'
    p, claims, candidates, questions = inputs
    request, original_schema, executable_schema, erefs, srefs = context
    sourced = sources.resolve_response(decoded, executable_schema, schema, srefs, p, srefs['request_hash'])
    resolved = expressions.resolve(sourced, request, original_schema, erefs, readings=candidates, questions=questions)
    assert fv.validate(resolved, p, claims, candidates, questions)
    assert resolved['checks'][0]['executable_correspondence']['status'] == status
    assert original['checks'][0]['source_support']['rationale'] == decoded['checks'][0]['source_support']['rationale']


@pytest.mark.parametrize('fault', ['question', 'source', 'table', 'pair', 'duplicate', 'missing', 'foreign_quote', 'duplicate_quote'])
def test_detached_changed_or_incomplete_aliases_are_rejected(fault):
    wire, schema, original, _, _ = fixture()
    _, _, references = aliases.prepare(wire, schema)
    value = aliases.encode_response(original, wire, schema)
    if fault == 'question': wire['candidates'][0]['question_hash'] = '0' * 64
    elif fault == 'source': wire['source_packet']['units'][0]['text'] += ' changed'
    elif fault == 'table': references['pairs']['p0'][0] = 999
    elif fault == 'pair': value['checks'][0]['pair'] = 'p999'
    elif fault == 'duplicate': value['checks'].append(deepcopy(value['checks'][0]))
    elif fault == 'missing': value['checks'] = []
    elif fault == 'foreign_quote': value['checks'][0]['source_support']['evidence'][0]['span_ids'] = ['s999']
    elif fault == 'duplicate_quote': value['checks'][0]['source_support']['evidence'][0]['span_ids'] *= 2
    with pytest.raises(LegalMathError): aliases.resolve(value, wire, schema, references)


def test_aliases_cannot_manufacture_executable_comparison_for_unformalized_reading():
    wire, schema, original, inputs, context = fixture()
    _, _, references = aliases.prepare(wire, schema)
    value = aliases.encode_response(original, wire, schema)
    value['checks'][0]['executable_correspondence']['status'] = 'OMITS'
    decoded = aliases.resolve(value, wire, schema, references)
    p, claims, candidates, questions = inputs
    request, original_schema, executable_schema, erefs, srefs = context
    sourced = sources.resolve_response(decoded, executable_schema, schema, srefs, p, srefs['request_hash'])
    with pytest.raises(LegalMathError): expressions.resolve(sourced, request, original_schema, erefs, readings=candidates, questions=questions)


def test_cross_unit_quotation_is_rejected_and_separate_selected_quotes_validate():
    wire, schema, original, inputs, context = fixture(extra_unit=True)
    _, output_schema, references = aliases.prepare(wire, schema)
    value = aliases.encode_response(original, wire, schema)
    quotes = value['checks'][0]['question_relation']['evidence']
    quotes[0]['span_ids'].append('s1')
    with pytest.raises(LegalMathError): aliases.resolve(value, wire, schema, references)
    quotes[0]['span_ids'].pop()
    quotes.append({'span_ids': ['s1']})
    decoded = aliases.resolve(value, wire, schema, references)
    p, claims, candidates, questions = inputs
    request, original_schema, executable_schema, erefs, srefs = context
    sourced = sources.resolve_response(decoded, executable_schema, schema, srefs, p, srefs['request_hash'])
    resolved = expressions.resolve(sourced, request, original_schema, erefs, readings=candidates, questions=questions)
    assert fv.validate(resolved, p, claims, candidates, questions)
    assert resolved['checks'][0]['question_relation']['evidence'] == [
        {'unit_id': u['unit_id'], 'quote': u['text']} for u in p['units']]
    assert output_schema['$defs']['Quote']['properties']['span_ids']['maxItems'] == 1
    assert resolved['checks'][0]['question_relation']['rationale'] == original['checks'][0]['question_relation']['rationale']
