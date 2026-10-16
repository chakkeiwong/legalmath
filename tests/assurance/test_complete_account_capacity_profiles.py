from copy import deepcopy
from dataclasses import replace
import json

import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased import (
    account_contract, account_encoding, account_input, account_recovery,
)
from legalmath.interpretation.assurance.integration_contract import evidence_file
from tests.assurance.test_bounded_product import envelope, limits, Scripted
from tests.assurance.test_lossless_account_recovery import fixture


def selected(tmp_path):
    product, original = fixture(tmp_path)
    original['payload'] = {'original_assignment': {'assignment': 'Preserve both readings'},
        'partial_source_readings': [{'conclusion': 'Conditional duty'}, {'conclusion': 'Consent exception'}]}
    request = account_contract.select(original, input_profile=account_encoding.PROFILE,
        capacity_profile=account_input.CAPACITY_PROFILE)
    return product, original, request


@pytest.mark.parametrize('packed', [False, True])
def test_optional_bound_preserves_schema_sources_and_historical_bounds(tmp_path, packed):
    product, original, request = selected(tmp_path)
    legacy = deepcopy(request); legacy.pop('account_capacity_profile')
    assert account_recovery.baseline_request(request, account_contract.provider_schema())[0] == original
    new_wire, old_wire = (prepare(r, account_contract.provider_schema()) for r in (request, legacy))
    assert new_wire['schema'] == old_wire['schema']
    changed = deepcopy(new_wire['request']); changed.pop('account_capacity_profile')
    assert changed == old_wire['request']
    new = new_wire['request'] if packed else request
    old = old_wire['request'] if packed else legacy
    assert account_input.input_token_limit(new, product.route.limits) == 32768
    assert account_input.input_token_limit(old, product.route.limits) == 16384
    leaf = deepcopy(legacy); leaf['payload'] = original['payload']['original_assignment']
    assert account_input.input_token_limit(leaf, product.route.limits) == 12000
    with pytest.raises(LegalMathError):
        account_input.input_token_limit(new, replace(product.route.limits, input_tokens=24000))


@pytest.mark.parametrize('packed', [False, True])
@pytest.mark.parametrize('mutation', ['unknown', 'task', 'contract', 'references', 'encoding',
    'no_input_profile', 'no_assignment', 'one_child', 'three_children', 'empty_child', 'leaf'])
def test_capacity_cannot_escape_its_declared_contract(tmp_path, packed, mutation):
    product, _, request = selected(tmp_path)
    if packed:
        request = prepare(request, account_contract.provider_schema())['request']
    if mutation == 'unknown': request['account_capacity_profile'] = 'unreviewed'
    elif mutation == 'task': request['task'] = 'ANSWER_ORIGINAL_QUESTION'
    elif mutation == 'contract': request.pop('account_contract')
    elif mutation == 'references': request['response_reference_profile'] = 'foreign'
    elif mutation == 'encoding': request['account_input_profile'] = account_input.PROFILE
    elif mutation == 'no_input_profile': request.pop('account_input_profile')
    elif mutation == 'no_assignment': request['payload'].pop('original_assignment')
    elif mutation == 'one_child': request['payload']['partial_source_readings'].pop()
    elif mutation == 'three_children': request['payload']['partial_source_readings'].append({'extra': True})
    elif mutation == 'empty_child': request['payload']['partial_source_readings'][0] = {}
    else: request['payload'] = {'assignment': 'Leaf'}
    with pytest.raises(LegalMathError) as caught:
        account_input.input_token_limit(request, product.route.limits)
    assert caught.value.code == 'E_AUTHORITY'


@pytest.mark.parametrize('tokens,accepted', [(23000, True), (32768, True), (32769, False)])
def test_product_and_packed_provider_enforce_the_same_finite_bound(tmp_path, tokens, accepted):
    product, _, request = selected(tmp_path)
    schema = account_contract.provider_schema()
    product.route.encode = lambda _: range(tokens)
    provider = object.__new__(BoundedCodexProvider)
    provider.command = lambda *args: ['developer_instructions=Capacity boundary control']
    provider.limits = product.route.limits
    provider.encode = lambda _: range(tokens)
    packed = prepare(request, schema)
    checks = [lambda: product.dispatch.measure(request, schema),
        lambda: provider.measure(packed['request'], packed['schema'])]
    for check in checks:
        if accepted:
            assert check()['local_tokens'] == tokens
        else:
            with pytest.raises(LegalMathError) as caught:
                check()
            assert caught.value.code == 'E_RESOURCE_LIMIT'
    product.route.limits = replace(product.route.limits, input_bytes=1)
    provider.limits = product.route.limits
    for check in checks:
        with pytest.raises(LegalMathError):
            check()
    assert not product.provider.requests


def test_saved_success_keeps_exact_contract_and_only_new_combination_selects_capacity(tmp_path):
    prior = BoundedProduct(tmp_path, tmp_path/'prior', Scripted(fail_at=2), envelope(), list,
        limits=replace(limits(), input_tokens=12000), requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE)
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    q = envelope()['original_questions'][0]
    payload = {'original_assignment': {'assignment': 'Preserve both'},
        'partial_source_readings': [{'conclusion': 'Conditional duty'}, {'conclusion': 'Consent exception'}]}
    good = prior.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, payload, ['o1'])
    failed = prior.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, payload, ['o2'])
    assert good['status'] == 'VALIDATED' and failed['status'] == 'FAILED'
    details = [{'id': 'o1', 'result': good}, {'id': 'o2', 'result': failed}]
    (prior.directory/'requirement-details.json').write_text(json.dumps(details))
    recovery = account_recovery.build(tmp_path, prior.directory/'calls', details)
    path = tmp_path/'recovery.json'; path.write_text(json.dumps(recovery))
    fresh = Scripted()
    options = dict(limits=replace(limits(), input_tokens=12000),
        requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_capacity_profile=account_input.CAPACITY_PROFILE,
        requirement_account_recovery=evidence_file(path, tmp_path))
    product = BoundedProduct(tmp_path, tmp_path/'next', fresh, envelope(), list, **options)
    assert product.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, payload, ['o1']) == good
    assert not fresh.requests
    assert (product.directory/'calls/detail-0/request.json').read_bytes() == (
        prior.directory/'calls/detail-0/request.json').read_bytes()
    result = product.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, payload, ['o2'])
    assert result['status'] == 'VALIDATED'
    assert fresh.requests[0]['account_capacity_profile'] == account_input.CAPACITY_PROFILE
    options.pop('requirement_account_capacity_profile')
    with pytest.raises(LegalMathError):
        BoundedProduct(tmp_path, tmp_path/'next', fresh, envelope(), list, **options)


def test_ordinary_account_retains_base_bound_even_when_candidate_is_selected(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path/'product', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE,
        requirement_account_capacity_profile=account_input.CAPACITY_PROFILE)
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    assert product.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', envelope()['original_questions'][0],
        records, {'assignment': 'Ordinary leaf'}, ['o1'])['status'] == 'VALIDATED'
    request = product.provider.requests[0]
    assert 'account_capacity_profile' not in request
    assert account_input.input_token_limit(request, product.route.limits) == 12000
