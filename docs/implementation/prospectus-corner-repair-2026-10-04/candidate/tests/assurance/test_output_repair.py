"""Regression for the live wrong-field response and its ineffective generic repair."""
from copy import deepcopy
import pytest
from legalmath.canonical import canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import parse
from legalmath.interpretation.assurance.engine import Assurance
from legalmath.interpretation.assurance.semantics import (
    Fidelity, fidelity_request, validate_fidelity)
from tests.search.support import FunctionProvider
from .support import packet, inventory, reading, fidelity
from .test_integration import settings, AT


def inputs():
    claims = inventory()['claims']
    candidates = {'candidate.a': reading()}
    valid = fidelity(claims, candidates)
    malformed = deepcopy(valid)
    row = malformed['checks'][0]
    row['status'] = row.pop('label')
    row['failed_stage'] = row.pop('failing_stage')
    row['representation_evidence'] = row.pop('representation_quotes')
    malformed['task'] = 'SOURCE_FIDELITY'
    return claims, candidates, valid, malformed


def test_wrong_fields_remain_rejected_with_locations_and_no_input_echo():
    _, _, _, malformed = inputs()
    malformed['task'] = 'Untrusted input must not be copied into diagnostics'
    with pytest.raises(LegalMathError) as error:
        parse(Fidelity, malformed)
    details = error.value.details
    locations = {(tuple(e['loc']), e['type']) for e in details['validation_errors']}
    assert (('checks', 0, 'label'), 'missing') in locations
    assert (('checks', 0, 'status'), 'extra_forbidden') in locations
    assert (('checks', 0, 'failing_stage'), 'missing') in locations
    assert (('checks', 0, 'representation_quotes'), 'missing') in locations
    assert (('task',), 'extra_forbidden') in locations
    assert all('input' not in e and 'ctx' not in e for e in details['validation_errors'])
    assert b'Untrusted input' not in canonical(details)


def test_large_schema_failure_has_a_bounded_explicitly_incomplete_diagnostic():
    _, _, _, malformed = inputs()
    malformed['checks'] *= 32
    with pytest.raises(LegalMathError) as error:
        parse(Fidelity, malformed)
    details = error.value.details
    assert details['total_errors'] > len(details['validation_errors']) == 64
    assert details['truncated'] is True
    canonical(details)


@pytest.mark.parametrize('repair_succeeds', [True, False])
def test_bounded_repair_receives_real_contract_and_repeated_failure_is_preserved(root, tmp_path, repair_succeeds):
    claims, candidates, valid, malformed = inputs()
    received = []
    def respond(request):
        received.append(request)
        if request['task'] == 'REPAIR_OUTPUT':
            assert request['response_schema'] == Fidelity.model_json_schema()
            assert request['validation_error_data']['model'] == 'Fidelity'
            assert any(e['loc'] == ['checks', 0, 'label'] for e in request['validation_error_data']['validation_errors'])
            assert request['invalid_response'] == malformed
            if repair_succeeds:
                return valid
        return malformed
    engine = Assurance(tmp_path/'run', FunctionProvider(respond),
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings())
    request = fidelity_request(packet(), claims, candidates)
    assert request['response_schema'] == Fidelity.model_json_schema()
    result = engine.invoke(request, Fidelity, lambda v: validate_fidelity(v, packet(), claims, candidates))
    assert len(received) == 2
    assert result == (valid if repair_succeeds else None)
    assert len(engine.failures) == (1 if repair_succeeds else 2)
    assert (tmp_path/'run/calls/call-000/response.json').exists()
    assert (tmp_path/'run/calls/call-001/response.json').exists()

