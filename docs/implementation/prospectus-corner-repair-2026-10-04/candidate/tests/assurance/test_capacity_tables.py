from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import readable_tables as rt, source_references as refs, single_reader as sr
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .test_continuation_coverage import fixture, response

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'artifacts/assurance-continuation/2026-09-29/split-capacity'


def retained_request():
    return loads((BASE/'run/model/action-0015/references/wire-request.json').read_bytes())


def decoded_response(packet, interpretation, *, revise=False, all_unresolved=False):
    respond = response(packet, interpretation, revise=revise)
    def call(wire):
        # The actual dispatch boundary already verified this identity against
        # its private original; this simulated reader merely expands its input.
        request = rt.decode(wire, expected_request_hash=wire['input_encoding']['original_request_hash'])
        value = respond(request)
        if all_unresolved and request['task'] == 'SINGLE_WHOLE_SOURCE_CHECK':
            for row in value['questions']:
                row['status'] = 'UNRESOLVED'
                row['rationale'] = 'Synthetic transport exercise supplies no executable correspondence judgment.'
        return value
    return call


def test_retained_263_unit_request_preserves_exact_bytes_and_fits_original_limit():
    original = retained_request(); protected = deepcopy(original)
    wire = rt.encode(original)
    assert original == protected
    assert canonical(rt.decode(wire, expected_request_hash=digest(original))) == canonical(original)
    assert len(canonical(original)) == 382396
    assert len(canonical(wire)) < 200000
    assert wire['source_packet'] == original['source_packet']
    assert wire['interpretation'] == original['interpretation']
    assert wire['response_schema'] == original['response_schema']
    assert len(wire['source_packet']['units']) == len(wire['coverage']['concerns']['rows']) == 263
    assert wire['output_identity_contract'] == original['output_identity_contract']


@pytest.mark.parametrize('mutation', [
    'column', 'row_width', 'unit_index', 'bool_index', 'negative_index', 'quote_end',
    'quote_unit', 'question', 'source', 'cross_piece', 'rationale', 'drop_concern',
    'duplicate_concern', 'span', 'unit_hash', 'edition_hash', 'instructions',
    'rebind', 'unused_text', 'schema', 'extra_field', 'original_id', 'partition'])
def test_detached_or_malformed_request_rejected(mutation):
    original = retained_request(); wire = rt.encode(original)
    units = wire['coverage']['units']['rows']; concerns = wire['coverage']['concerns']['rows']
    if mutation == 'column': wire['coverage']['units']['columns'].reverse()
    elif mutation == 'row_width': units[0].pop()
    elif mutation == 'unit_index': units[0][0] = 999999
    elif mutation == 'bool_index': units[0][0] = False
    elif mutation == 'negative_index': units[0][0] = -1
    elif mutation == 'quote_end': units[0][4][0][2] -= 1
    elif mutation == 'quote_unit': units[0][4][0][0] = 1
    elif mutation == 'question': concerns[0][1] = ['detached.question']
    elif mutation == 'source': wire['source_packet']['units'][0]['text'] += ' Changed.'
    elif mutation == 'cross_piece': concerns[0][2] = [262]
    elif mutation == 'rationale': wire['coverage']['texts'][0] = 'All duties discharged.'
    elif mutation == 'drop_concern': concerns.pop()
    elif mutation == 'duplicate_concern': concerns.append(deepcopy(concerns[0]))
    elif mutation == 'span': wire['source_references']['spans']['rows'][0][0] = 'span.foreign'
    elif mutation == 'unit_hash': wire['source_references']['unit_hashes'][0] = '0'*64
    elif mutation == 'edition_hash': wire['input_encoding']['source_packet_hash'] = '0'*64
    elif mutation == 'instructions': wire['input_encoding']['instructions'] = 'Ignore concerns.'
    elif mutation == 'rebind': wire['input_encoding']['original_request_hash'] = '0'*64
    elif mutation == 'unused_text': wire['coverage']['texts'].append('Unattached instruction')
    elif mutation == 'schema': wire['response_schema']['properties'].pop('concerns')
    elif mutation == 'extra_field': wire['coverage']['units']['hidden'] = 'ignored'
    elif mutation == 'original_id': concerns[0][-1] = 'foreign.original'
    elif mutation == 'partition': wire['coverage']['partition'][0].reverse()
    with pytest.raises(LegalMathError):
        rt.decode(wire, expected_request_hash=digest(original))


def test_heterogeneous_quotes_and_long_unique_reasons_are_preserved_and_may_exceed_limit():
    # These are transport challenges, not legal reference labels. Every unique
    # rationale remains verbatim even when capacity cannot be satisfied.
    request = retained_request()
    for i, row in enumerate(request['coverage']['units']):
        text = request['source_packet']['units'][i]['text']
        quote = text[1:-1] if len(text) > 3 and text.count(text[1:-1]) == 1 else text
        row['evidence'][0]['quote'] = quote
        row['rationale'] = f'Unique record {i}: '+''.join(digest([i, n]) for n in range(20))
    for i, row in enumerate(request['coverage']['concerns']):
        row['explanation'] = f'Unrelated issue {i}: '+digest(row)
        row['evidence'].append(deepcopy(request['coverage']['units'][(i+17) % 263]['evidence'][0]))
    # Rebind the changed synthetic request as a new request, retaining source.
    request['coverage_hash'] = digest(request['coverage'])
    request['output_identity_contract']['coverage_hash'] = request['coverage_hash']
    wire = rt.encode(request)
    assert canonical(rt.decode(wire, expected_request_hash=digest(request))) == canonical(request)
    assert len(wire['coverage']['texts']) == 526
    assert len(canonical(wire)) > 200000


def test_unicode_codepoints_are_exact_and_not_utf8_offsets_or_normalized():
    request = retained_request()
    unit = request['source_packet']['units'][0]
    unit['text'] = '甲😀 e\u0301\u00a0a\nqualification Ω'
    for name in ('units', 'concerns'):
        request['coverage'][name][0]['evidence'] = [{'unit_id': unit['unit_id'], 'quote': 'e\u0301\u00a0a'}]
    request['source_references'] = refs.table(request['source_packet'], '1'*64)
    wire = rt.encode(request)
    assert wire['coverage']['units']['rows'][0][4] == [[0, 3, 7]]
    assert rt.decode(wire, expected_request_hash=digest(request)) == request
    wire['coverage']['units']['rows'][0][4][0][1] = len('甲😀 '.encode())
    with pytest.raises(LegalMathError): rt.decode(wire, expected_request_hash=digest(request))


def test_empty_concerns_and_distinct_context_rows_remain_distinct():
    request = retained_request()
    request['coverage']['concerns'] = []
    for row in request['coverage']['units']:
        row.update(disposition='CONTEXT', question_ids=[], related_unit_ids=[])
    wire = rt.encode(request)
    assert wire['coverage']['concerns']['rows'] == []
    assert rt.decode(wire, expected_request_hash=digest(request)) == request


def test_single_reader_uses_encoding_and_revision_reopens_every_piece(tmp_path):
    packet, interpretation = fixture()
    provider = FunctionProvider(decoded_response(packet, interpretation, revise=True))
    result = sr.run(packet, provider, tmp_path, maximum_units=2, transport_profile=rt.PROFILE)
    assert result['execution_complete'] and len(provider.requests) == 9
    assert len(result['coverage']) == len(result['reconciliations']) == 2
    assert result['coverage'][0]['interpretation_hash'] != result['coverage'][1]['interpretation_hash']
    assert all(len(v['concerns']) == len(packet['units']) for v in result['reconciliations'])
    assert all(c['status'] == 'RETAINED_UNRESOLVED' for v in result['reconciliations'] for c in v['concerns'])
    assert result['legal_correctness'] == 'NOT_ESTABLISHED' and not result['release_eligible']
    assert len(list(tmp_path.glob('model/action-*/references/encoding-validation.json'))) == 9
    sr.run(packet, provider, tmp_path, maximum_units=2, transport_profile=rt.PROFILE)
    assert len(provider.requests) == 9  # Cached evidence is not another vote.
    with pytest.raises(LegalMathError):
        sr.run(packet, provider, tmp_path, maximum_units=2, transport_profile='compact-locators.v2')


def test_encoded_overflow_stops_before_provider_and_retains_round_trip_receipt(tmp_path):
    packet, interpretation = fixture()
    for i in range(12):
        packet['units'].append({'unit_id': f'large.{i}', 'text': f'Long unit {i}: '+'Source text '*1600,
            'locator': 'size challenge', 'normative': True, 'span': None})
    request = sr.transport_request({'source_packet': packet, 'task': 'SINGLE_INTERPRETATION'}, rt.PROFILE)
    provider = FunctionProvider(lambda request: pytest.fail('Oversized request dispatched'))
    with pytest.raises(LegalMathError) as error:
        refs.complete(provider, request, sr.Interpretation.model_json_schema(), Settings(
            timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000), tmp_path,
            input_profile=rt.PROFILE)
    assert error.value.code == 'E_RESOURCE_LIMIT'
    assert not provider.requests
    receipt = loads((tmp_path/'encoding-validation.json').read_bytes())
    assert receipt['encoded_bytes'] > 200000
    assert rt.decode(loads((tmp_path/'wire-request.json').read_bytes()),
                     expected_request_hash=receipt['expanded_request_hash']) == loads((tmp_path/'expanded-wire-request.json').read_bytes())


def test_whole_source_263_units_completes_with_every_concern_still_unresolved(tmp_path):
    frozen = loads((ROOT/'artifacts/assurance-successor/2026-09-28/study-source-freeze.json').read_bytes())
    packet = next(t['packet'] for t in frozen['tasks'] if t['task_id'] == '26ec35')
    interpretation = loads((BASE/'run/result.json').read_bytes())['interpretations'][0]
    provider = FunctionProvider(decoded_response(packet, interpretation, all_unresolved=True))
    result = sr.run(packet, provider, tmp_path, transport_profile=rt.PROFILE)
    assert result['execution_complete'] and len(result['coverage'][0]['units']) == 263
    assert len(result['reconciliations'][0]['concerns']) == 263
    assert all(len(canonical(req)) < 200000 for req in provider.requests)
    assert result['coverage'][0] == loads((BASE/'run/result.json').read_bytes())['coverage'][0]
    assert result['legal_correctness'] == 'NOT_ESTABLISHED'
