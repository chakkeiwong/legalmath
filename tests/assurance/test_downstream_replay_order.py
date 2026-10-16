"""Exact persisted downstream transport, including rejected altered bindings."""
from copy import deepcopy
import json

import pytest

from legalmath.canonical import canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import NOTE
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.phased import account_encoding, account_input, downstream_input
from tests.assurance.test_downstream_capacity import product
from tests.assurance.test_bounded_product import envelope


def request(tmp_path):
    instance = product(tmp_path)
    records = [r for r in instance.route.records.values() if r['kind'] == 'source']
    value = instance.request('SYNTHESIZE_FINDINGS', envelope()['original_questions'][0],
        records, payload={'findings': []}, expected=['obligation'])
    value['downstream_input_profile'] = downstream_input.PROFILE
    return value


def response():
    return {'conclusion': 'Conditional.', 'support': [{'span_id': 0}], 'contrary': [],
        'assumptions': [], 'unresolved': ['Facts remain unknown.'], 'alternatives': [],
        'considered': {'c0': 'r2'}, 'source_gaps': [], 'assertion_bindings': []}


def test_canonical_reload_preserves_wire_binding_and_decoded_response(tmp_path):
    original = request(tmp_path)
    before = deepcopy(original)
    prepared = prepare(original, NOTE)
    persisted = json.loads(canonical(prepared))
    assert original == before
    assert prepare(json.loads(canonical(original)), NOTE) == prepared
    assert resolve(response(), persisted, maximum_bytes=2000000) == resolve(
        response(), prepared, maximum_bytes=2000000)


def test_extra_record_fields_survive_reload_in_exact_transport(tmp_path):
    original = request(tmp_path)
    for i, record in enumerate(original['records']):
        record['z_custom'] = i
        record['a_custom'] = -i
    packed = prepare(original, NOTE)
    assert prepare(json.loads(canonical(original)), NOTE) == packed
    expanded = account_encoding.expand({'request': packed['request'],
        'response_schema': packed['schema']})
    wire = account_input.expand(expanded['request'])
    plain = deepcopy(original)
    del plain['downstream_input_profile']
    del wire['downstream_input_profile']
    assert wire == prepare(plain, NOTE)['request']


@pytest.mark.parametrize('mutation', ['source', 'binding', 'columns'])
def test_persisted_binding_tampering_is_rejected(tmp_path, mutation):
    prepared = json.loads(canonical(prepare(request(tmp_path), NOTE)))
    if mutation == 'source':
        prepared['original_request']['records'][0]['text'] += 'changed'
    elif mutation == 'binding':
        prepared['binding'] = 'changed'
    else:
        prepared['request']['account_record_table']['columns'].reverse()
    with pytest.raises(LegalMathError):
        resolve(response(), prepared, maximum_bytes=2000000)


def test_ordinary_reference_profile_is_unchanged(tmp_path):
    original = request(tmp_path)
    del original['downstream_input_profile']
    prepared = prepare(original, NOTE)
    assert 'account_record_table' not in prepared['request']
    assert prepare(json.loads(canonical(original)), NOTE) == prepared
