from copy import deepcopy
from dataclasses import replace
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.phased import downstream_input, account_input, account_encoding, tool_input
from legalmath.interpretation.assurance.arguments import Criticism, criticism_request, evaluate_criticism
from legalmath.interpretation.search.models import Generation, DIMENSIONS, validate_generation
from tests.assurance.test_bounded_product import Scripted, envelope, limits


def fixture(tmp_path):
    p = BoundedProduct(tmp_path, tmp_path/'product', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), downstream_input_profile=downstream_input.PROFILE)
    p.downstream_capacity_profile = downstream_input.CAPACITY_PROFILE
    records = [r for r in p.route.records.values() if r['kind'] == 'source']
    packet = deepcopy(p.route.envelope['source_packet'])
    packet['units'] = [dict(unit_id=r['id'], text=r['text'], normative=r['normative'],
        locator=r['locator'], span=None) for r in records]
    return p, records, packet


@pytest.mark.parametrize('task', sorted(tool_input.TASKS))
def test_complete_tool_packet_and_schema_roundtrip(tmp_path, task):
    p, records, packet = fixture(tmp_path)
    schema = Generation.model_json_schema() if task.startswith('GENERATE') else Criticism.model_json_schema()
    original = dict(task=task, source_packet=packet, records=records, instructions='Retain all sources.')
    plain = prepare(original, schema)
    selected = p.tool_request(original, records)
    packed = prepare(selected, schema)
    restored = account_encoding.expand(dict(request=packed['request'], response_schema=packed['schema']))
    wire = account_input.expand(tool_input.expand(restored['request']))
    for key in ('downstream_input_profile', 'downstream_capacity_profile'): wire.pop(key)
    assert wire == plain['request']
    assert restored['response_schema'] == plain['schema']
    assert account_input.input_token_limit(selected, p.route.limits) == 70000
    assert downstream_input.input_byte_limit(selected, p.route.limits) == 250000
    changed = deepcopy(selected); changed['source_packet']['units'][0]['text'] += 'changed'
    with pytest.raises(LegalMathError): prepare(changed, schema)
    with pytest.raises(LegalMathError): prepare({**selected, 'downstream_capacity_profile':'unknown'}, schema)


def test_generation_decodes_exact_quotes_and_rejects_bad_selectors(tmp_path):
    p, records, packet = fixture(tmp_path)
    request = p.tool_request(dict(task='GENERATE_SOURCE_WARRANTED_CANDIDATES', source_packet=packet,
        records=records, instructions='Retain all sources.'), records)
    binding = prepare(request, Generation.model_json_schema())
    ids = list(binding['aliases'])
    wire = dict(readings=[dict(local_id='candidate', family='scope', subject='Duty',
        statement='A duty is conditional.', distinction='Consent matters.', citations=[{'span_id':0}],
        assumptions=[], questions=[], formalization=None)],
        dimensions=[dict(dimension=d, status='AMBIGUOUS', source_unit_ids=ids,
            explanation='Requires source review.') for d in DIMENSIONS],
        coverage=[dict(unit_id=i, status='CONTEXT', reason='Retained source.') for i in ids], questions=[])
    value = resolve(wire, binding, maximum_bytes=200000)
    validate_generation(value, packet)
    assert value['readings'][0]['citations'][0] == {'unit_id':records[0]['id'], 'quote':records[0]['text']}
    with pytest.raises(LegalMathError): resolve(wire, binding, maximum_bytes=10)
    bad = deepcopy(wire); bad['readings'][0]['citations'][0]['span_id'] = 999999
    with pytest.raises(Exception): resolve(bad, binding, maximum_bytes=200000)


def test_criticism_preserves_candidate_namespace_and_source_quotes(tmp_path):
    p, records, packet = fixture(tmp_path)
    request = p.tool_request(criticism_request(packet, [], {'candidate':{'statement':'Conditional duty'}}), records)
    binding = prepare(request, Criticism.model_json_schema())
    wire = dict(arguments=[dict(argument_id='argument',candidate_id='candidate',premises=[], parents=[],
        inference_id='rule',inference_kind='DEFEASIBLE',inference='Requires source interpretation.',
        conclusion={'atom':'duty','negative':False}, evidence=[{'span_id':0}])],
        attacks=[],preferences=[],cases=[],case_queries=[],questions=[])
    value = resolve(wire,binding,maximum_bytes=200000)
    result = evaluate_criticism(value,packet,['candidate'])
    assert value['arguments'][0]['candidate_id'] == 'candidate'
    assert value['arguments'][0]['evidence'][0]['quote'] == records[0]['text']
    assert result['candidate_pruning_authorized'] is False


def test_tool_specific_instructions_are_not_replaced_by_note_guidance(tmp_path):
    from legalmath.interpretation.assurance.phased.product import PhasedProduct
    from legalmath.interpretation.assurance.phased import downstream_instructions
    p, records, packet = fixture(tmp_path)
    p.__class__ = PhasedProduct
    p.downstream_instruction_profile = downstream_instructions.PROFILE
    call = dict(key='candidate', request=p.tool_request({'task':'GENERATE_SOURCE_WARRANTED_CANDIDATES',
        'source_packet':packet,'records':records,'instructions':'Formal expression grammar.'},records),
        schema=Generation.model_json_schema(), validate=lambda v:None)
    assert p.prepare_calls([call]) == [call]
