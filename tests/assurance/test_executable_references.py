from copy import deepcopy

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import executable_references as refs, fidelity_v2
from legalmath.interpretation.assurance.scoped_investigation import investigate
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .test_continuation_references import encode_quotes
from .test_round16 import scoped_fixture


def encode(value, references):
    wire = deepcopy(value)
    for row in wire['checks']:
        row['executable_correspondence']['representation_quotes'] = [next(
            x['span_id'] for x in references['spans'] if x['candidate_id'] == row['candidate_id']
            and x['expression_kind'] == 'result')]
    return wire


def test_resolves_exact_expression_and_original_semantic_validation(tmp_path):
    p, c, r, q, value = scoped_fixture()
    req = fidelity_v2.request(p, c, r, q)
    provider = FunctionProvider(lambda wire: encode_quotes(encode(value, wire['executable_references']), wire['source_references']))
    result = refs.complete(provider, req, fidelity_v2.FidelityV2.model_json_schema(), Settings(), tmp_path)
    assert fidelity_v2.validate(result.value, p, c, r, q)
    assert (tmp_path/'raw-response.json').exists()
    assert result.provenance['executable_reference_protocol'] == refs.PROTOCOL


@pytest.mark.parametrize('field', ['reading_hash', 'question', 'representation', 'candidate_id'])
def test_stale_identity_rejects_same_looking_quotation(field):
    p, c, r, q, value = scoped_fixture()
    req = fidelity_v2.request(p, c, r, q)
    schema = fidelity_v2.FidelityV2.model_json_schema()
    _, _, table = refs.prepare(req, schema)
    wire = encode(value, table)
    req['candidates'][0][field] = {'changed': True} if field == 'question' else 'a'*64
    with pytest.raises(LegalMathError):
        refs.resolve(wire, req, schema, table)


def test_unicode_expression_has_codepoint_offsets():
    p, c, r, q, value = scoped_fixture()
    req = fidelity_v2.request(p, c, r, q)
    req['candidates'][0]['representation'] = 'é😀\nScope: true\nResult: e\u0301😀'
    schema = fidelity_v2.FidelityV2.model_json_schema()
    table = refs.table(req, schema)
    result = refs.resolve(encode(value, table), req, schema, table)
    assert result['checks'][0]['executable_correspondence']['representation_quotes'] == ['e\u0301😀']


def test_unencoded_judgment_unavailable_without_rewriting_proposal():
    p, c, r, q, value = scoped_fixture()
    r['candidate']['formalization'] = None
    req = fidelity_v2.request(p, c, r, q)
    schema = fidelity_v2.FidelityV2.model_json_schema()
    table = refs.table(req, schema)
    assert not table['spans'] and not table['candidates'][0]['executable_available']
    value['checks'][0]['executable_correspondence']['representation_quotes'] = []
    with pytest.raises(LegalMathError):
        refs.resolve(value, req, schema, table)
    assert value['checks'][0]['executable_correspondence']['status'] == 'PRESERVES'
    value['checks'][0]['executable_correspondence']['status'] = 'UNASSESSED'
    assert fidelity_v2.validate(refs.resolve(value, req, schema, table), p, c, r, q)


def test_optional_transport_runs_scoped_journal_without_live_calls(tmp_path):
    p, c, r, q, value = scoped_fixture()
    provider = FunctionProvider(lambda wire: encode_quotes(encode(value, wire['executable_references']), wire['source_references']))
    result = investigate(p, c, r, q, provider, tmp_path, maximum_rounds=1, reference_protocol=refs.PROTOCOL)
    assert len(provider.requests) == 2
    assert not result.get('release_eligible', False)
