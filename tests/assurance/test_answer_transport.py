"""Exact original-population and adversarial answer-consumer transport checks."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import answer_transport as transport, answer_evidence
from legalmath.interpretation.assurance import dossier_answer as whole
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .test_dossier_answer import prepared
from .test_successor_workflow import investigation

ROOT = Path(__file__).resolve().parents[2]


def original_envelope():
    value = loads((ROOT/'artifacts/legal-mission-control/2026-10-12/completion/target-qualification/mandatory-envelope.json').read_bytes())
    return {'task':'REVIEW_DOSSIER_EVIDENCE', **value}


def test_original_population_and_historical_quotes_survive_common_and_nested_transport():
    original = original_envelope()
    for request in (original, answer_evidence.review_request(original, {'answers':[]})):
        wire = transport.encode(request)
        restored = transport.decode(wire, expected_request_hash=digest(compact_request(request,profile='v2')))
        assert restored == compact_request(request,profile='v2')
        base = restored.get('context', restored)
        assert len(base['answer_acceptance']['acceptance_obligations']) == 46
        assert len(base['answer_acceptance']['original_readings']) == 35
        assert base['answer_acceptance'] == original['answer_acceptance']
        assert transport.wire_size(request) < whole.wire_size(request)
    assert transport.wire_size(original) < 200000 < whole.wire_size(original)


@pytest.mark.parametrize('fault', ['source', 'path', 'text', 'verbatim', 'binding', 'extra'])
def test_corrupted_or_rebound_transport_is_rejected(fault):
    request = original_envelope()
    wire = transport.encode(request)
    trusted = wire['request_hash']
    if fault == 'source': wire['shared']['source_packet']['units'][0]['text'] += 'Changed law.'
    if fault == 'path': wire['shared']['columns'][0][0] = 'changed'
    if fault == 'text': wire['shared']['texts'][0] += 'Changed warrant.'
    if fault == 'verbatim': wire['verbatim']['reviews'] = [{'fabricated':True}]
    if fault == 'binding': wire['request_hash'] = '0'*64
    if fault == 'extra': wire['hidden'] = 'omitted obligation'
    with pytest.raises(LegalMathError): transport.decode(wire,expected_request_hash=trusted)


def test_actual_dispatch_matches_measured_bytes_and_keeps_response_schema(tmp_path):
    request = original_envelope()
    provider = FunctionProvider(lambda r: {'receipt':True})
    schema = {'type':'object'}
    adapter = transport.AnswerProvider(provider,tmp_path)
    size = transport.wire_size(request)
    adapter.complete(request,schema,Settings(max_input_bytes=size))
    assert len(canonical(provider.requests[0])) == size
    assert loads((tmp_path/'schema.json').read_bytes()) == schema
    with pytest.raises(LegalMathError):
        adapter.complete(request,schema,Settings(max_input_bytes=size-1))
    assert len(provider.requests) == 1


def test_literal_variable_fields_have_additive_size():
    request = original_envelope()
    request.update(reviews=[{'reason':'short'}],interaction={'finding':'short'})
    before = transport.wire_size(request)
    changed = deepcopy(request)
    changed['reviews'][0]['reason'] = 'unique uncompressed reasoning '*100
    changed['interaction']['finding'] = 'different uncompressed reasoning '*100
    delta = sum(len(canonical(changed[k]))-len(canonical(request[k])) for k in ('reviews','interaction'))
    assert transport.wire_size(changed) - before == delta


def test_answer_dependent_binding_hashes_cannot_change_fixed_context_sharing():
    request = answer_evidence.review_request(original_envelope(), {'answers':[]})
    request['context']['fixed_evidence'] = 'b'*64
    request['binding_hash'] = 'b'*64
    changed = deepcopy(request)
    changed['binding_hash'] = 'c'*64
    assert transport.wire_size(changed) == transport.wire_size(request)


def test_review_reservation_covers_repeated_escaped_answer_fields():
    base = original_envelope()
    answer = {'answers':[{'question_id':'p10','answer':'A retained conditional answer.',
        'qualifications':['Escaped evidence "quoted" \\ path and 中文 '*3 for _ in range(128)]}]}
    budget = transport.final_review_budget(base,answer_bytes=len(canonical(answer)),answer_fields=129,
                                           maximum_input_bytes=1000000)
    request = answer_evidence.review_request(base,answer)
    transport.enforce_final_review_budget(request,budget)


def test_historical_citation_locations_preserve_ids_and_do_not_assert_identity():
    from legalmath.interpretation.assurance.answer_acceptance import reading_quote_locations
    manifest = {'original_readings':[{'id':'retained', 'citations':[
        {'unit_id':'old-edition','quote':'kept exact'},
        {'unit_id':'old-edition','quote':'not in current source'}]}]}
    packet={'units':[{'unit_id':'current','text':'kept exact in this extraction'}]}
    rows = reading_quote_locations(manifest,packet)['citations']
    assert rows[0]['status']=='EXACT_TEXT_LOCATION'
    assert rows[0]['locations']==[{'unit_id':'current','start':0,'end':10}]
    assert not rows[0]['source_identity_and_warrant_established']
    assert rows[1]['status']=='UNRESOLVED'
    assert manifest['original_readings'][0]['citations'][0]['unit_id']=='old-edition'
    packet['units'].append({'unit_id':'other','text':'kept exact elsewhere'})
    assert reading_quote_locations(manifest,packet)['citations'][0]['status']=='AMBIGUOUS_TEXT_LOCATION'
    packet['units'] = [{'unit_id':'repeated','text':'kept exact and kept exact'}]
    repeated = reading_quote_locations(manifest,packet)['citations'][0]
    assert repeated['status']=='AMBIGUOUS_TEXT_LOCATION' and len(repeated['locations'])==2


def test_final_review_reservation_blocks_original_target_before_calls(prepared):
    original = original_envelope()
    budget = transport.final_review_budget(original,answer_bytes=16000,answer_fields=128)
    assert not budget['admitted'] and budget['final_review_input_bound'] > 200000
    root,directory,ref,args,_ = prepared
    # An excessive final-review reservation must fail before any consumer call.
    provider = FunctionProvider(lambda r: pytest.fail('Unadmitted review dispatched'))
    acceptance={'profile':'product-answer-acceptance.v1','original_questions':prepared[4]['original_questions'],
        'acceptance_obligations':[{'id':'control','question_ids':['gift']}],'cases':[],'source_documents':[]}
    from legalmath.interpretation.assurance.monitor import save
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    save(directory/'transport-acceptance.json',acceptance)
    result=whole.propose(root,ref,provider,directory/'transport-refusal',**args,
        acceptance_ref=evidence_file(directory/'transport-acceptance.json',root),
        input_profile=transport.PROFILE,raw_evidence_policy='complete',maximum_extra_dependency_bytes=0,
        maximum_answer_output_bytes=200000,maximum_answer_fields=10000)
    assert result['status']=='CAPACITY_BLOCKED' and result['details']['stage']=='FINAL_REVIEW_ADMISSION'
    assert result['provider_calls']==0 and not provider.requests
