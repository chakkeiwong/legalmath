from copy import deepcopy
import json

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2, source_references as refs
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .support import packet
from .test_round16 import scoped_fixture


@pytest.mark.parametrize('text', ['unless\u00a0excluded', 'e\u0301 versus é', 'a😀b', 'a\r\nb', 'x x', 'a\x00b'])
def test_whole_unit_resolves_exact_unicode_without_normalization(text):
    p = packet(); p['units'][0]['text'] = text
    t = refs.table(p, 'a'*64)
    selected = {'span_ids': [t['spans'][0]['span_id']]}
    assert refs.resolve(selected, t, p, 'a'*64) == {'unit_id': p['units'][0]['unit_id'], 'quote': text}


def test_adjacent_segments_restore_qualifications_including_boundary_characters():
    p = packet(); text = 'a'*31 + '😀 unless\u00a0excluded. ' + 'b'*50
    p['units'][0]['text'] = text
    t = refs.table(p, 'a'*64, chunk_size=32)
    segments = [r for r in t['spans'] if r['unit_id'] == p['units'][0]['unit_id']][1:]
    assert refs.resolve({'span_ids': [r['span_id'] for r in segments]}, t, p, 'a'*64)['quote'] == text
    with pytest.raises(LegalMathError):
        refs.resolve({'span_ids': [segments[0]['span_id'], segments[-1]['span_id']]}, t, p, 'a'*64)


@pytest.mark.parametrize('mutation', ['packet', 'request', 'text_hash', 'offset', 'coordinate', 'identifier', 'duplicate', 'foreign', 'raw_offset'])
def test_altered_or_foreign_references_rejected(mutation):
    p = packet(); t = refs.table(p, 'a'*64); binding = 'a'*64
    selection = {'span_ids': [t['spans'][0]['span_id']]}
    if mutation == 'packet': p['units'][0]['text'] += ' amended'
    elif mutation == 'request': binding = 'b'*64
    elif mutation == 'text_hash': t['unit_hashes'][p['units'][0]['unit_id']] = '0'*64
    elif mutation == 'offset': t['spans'][0]['start_codepoint'] = True
    elif mutation == 'coordinate': t['coordinates'] = 'UTF-16'
    elif mutation == 'identifier': t['spans'][0]['span_id'] = 'foreign'
    elif mutation == 'duplicate': selection['span_ids'] *= 2
    elif mutation == 'foreign': selection['span_ids'] = [refs.table(p, 'b'*64)['spans'][0]['span_id']]
    else: selection['start_codepoint'] = 0
    with pytest.raises(LegalMathError): refs.resolve(selection, t, p, binding)


def encode_quotes(value, references):
    """Synthetic fixture provider chooses the full source unit, not a legal oracle."""
    if isinstance(value, dict):
        if set(value) == {'unit_id', 'quote'}:
            selected = next(r for r in references['spans'] if r['unit_id'] == value['unit_id'])
            return {'span_ids': [selected['span_id']]}
        return {k: encode_quotes(v, references) for k, v in value.items()}
    if isinstance(value, list): return [encode_quotes(v, references) for v in value]
    return value


def test_transport_preserves_raw_references_and_uses_existing_semantic_validator(tmp_path):
    p, c, r, q, v = scoped_fixture()
    v['checks'][0]['source_support']['status'] = 'NOT_ESTABLISHED'
    v['checks'][0]['executable_correspondence']['status'] = 'UNASSESSED'
    request = fidelity_v2.request(p, c, r, q)
    provider = FunctionProvider(lambda req: encode_quotes(v, req['source_references']))
    answer = refs.complete(provider, request, fidelity_v2.FidelityV2.model_json_schema(), Settings(), tmp_path)
    result = fidelity_v2.validate(answer.value, p, c, r, q)
    assert result['checks'][0]['source_support']['status'] == 'NOT_ESTABLISHED'
    assert json.loads((tmp_path/'validation.json').read_text())['semantic_support'] == 'NOT_ESTABLISHED'
    raw = json.loads((tmp_path/'raw-response.json').read_text())['value']
    assert 'span_ids' in raw['checks'][0]['source_support']['evidence'][0]
    assert 'quote' in answer.value['checks'][0]['source_support']['evidence'][0]
    assert provider.requests[0]['source_packet'] == p


@pytest.mark.parametrize('direction', ['relation', 'correspondence', 'support'])
def test_cross_field_diagnostic_identifies_the_exact_pair_and_preserves_response(direction):
    p, c, r, q, v = scoped_fixture(); row = v['checks'][0]
    if direction == 'relation': row['question_relation']['status'] = 'NOT_APPLICABLE_TO_THIS_QUESTION'
    elif direction == 'correspondence': row['executable_correspondence']['status'] = 'NOT_APPLICABLE'
    else: row['source_support']['status'] = 'NOT_ESTABLISHED'
    before = deepcopy(v)
    with pytest.raises(LegalMathError) as error: fidelity_v2.validate(v, p, c, r, q)
    assert error.value.details['field'] == 'executable_correspondence.status'
    assert error.value.details['claim_id'] == row['claim_id']
    assert error.value.details['candidate_id'] == row['candidate_id']
    assert v == before


def test_unencoded_executable_assessment_has_exact_row_diagnostic():
    p,c,r,q,v=scoped_fixture();r['candidate']['formalization']=None
    with pytest.raises(LegalMathError) as caught:fidelity_v2.validate(v,p,c,r,q)
    assert caught.value.code=='E_REFERENCE'
    assert caught.value.details['candidate_id']=='candidate'
    assert caught.value.details['field'].startswith('executable_correspondence')
