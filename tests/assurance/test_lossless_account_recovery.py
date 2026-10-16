from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from jsonschema import ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.phased import account_contract, account_input, account_encoding, account_recovery
from tests.assurance.test_bounded_product import envelope, limits, Scripted


def fixture(tmp_path):
    product = BoundedProduct(tmp_path, tmp_path / 'product', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000))
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    request = product.request('ASSESS_ORIGINAL_REQUIREMENT', envelope()['original_questions'][0],
        records, payload={'assignment': 'Preserve the exception.'}, expected=['o1'])
    return product, request


@pytest.mark.parametrize('long_source', [False, True])
def test_structure_exactly_reconstructs_regular_and_irregular_spans(tmp_path, long_source):
    _, request = fixture(tmp_path)
    if long_source:
        record = request['records'][0]
        record['text'] = ''.join(chr(0x400 + i) for i in range(700))
        record['start'], record['end'] = 0, len(record['text'])
    original = prepare(account_contract.select(request, input_profile=account_input.PROFILE),
        account_contract.provider_schema())
    value = {'request': original['request'], 'response_schema': original['schema']}
    packed = account_encoding.pack(value)
    assert account_encoding.expand(packed) == value
    recipes = packed['request']['account_span_recipes']
    assert bool(recipes['regular']) == long_source
    assert recipes['explicit']
    changed = deepcopy(packed)
    changed['request']['account_span_recipes']['explicit'].append(recipes['explicit'][0])
    with pytest.raises(LegalMathError):
        account_encoding.expand(changed)


@pytest.mark.parametrize('selector', [0, -1, 100000, True, '0', 0.5, 0.0])
def test_request_bound_integer_selectors_keep_legacy_decode(tmp_path, selector):
    _, request = fixture(tmp_path)
    old = prepare(account_contract.select(request, input_profile=account_input.PROFILE),
        account_contract.provider_schema())
    new = prepare(account_contract.select(request, input_profile=account_encoding.PROFILE),
        account_contract.provider_schema())
    response = {'conclusion': 'The duty depends on consent.', 'support': [{'span_id': selector}],
        'contrary': [], 'assumptions': [], 'unresolved': ['Client facts remain unknown.'],
        'alternatives': [], 'considered': {'c0': next(k for k,v in new['aliases'].items() if v == 'o1')},
        'source_gaps': [], 'assertion_bindings': []}
    if type(selector) is int and selector == 0:
        historical = deepcopy(response); historical['support'][0]['span_id'] = 's0'
        assert resolve(response, new, maximum_bytes=100000) == resolve(historical, old, maximum_bytes=100000)
        tampered = deepcopy(new); tampered['selections']['s0'] = 'foreign'
        with pytest.raises(LegalMathError):
            resolve(response, tampered, maximum_bytes=100000)
    else:
        with pytest.raises((LegalMathError, ValidationError)):
            resolve(response, new, maximum_bytes=100000)


@pytest.mark.parametrize('typed', [False, True])
def test_successful_legacy_and_typed_requests_reuse_without_calls(tmp_path, typed):
    provider = Scripted(fail_at=2)
    kwargs = dict(requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_input.PROFILE) if typed else {}
    prior = BoundedProduct(tmp_path, tmp_path / 'prior', provider, envelope(), list,
        limits=replace(limits(), input_tokens=12000), **kwargs)
    records = [r for r in prior.route.records.values() if r['kind'] == 'source']
    q = envelope()['original_questions'][0]
    good = prior.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, {'assignment': 'Keep exception'}, ['o1'])
    failed = prior.note('detail-1', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, {'assignment': 'Other duty'}, ['o2'])
    assert good['status'] == 'VALIDATED' and failed['status'] == 'FAILED'
    details = [{'id': 'o1', 'result': good}, {'id': 'o2', 'result': failed}]
    (prior.directory / 'requirement-details.json').write_text(json.dumps(details))
    manifest = account_recovery.build(tmp_path, prior.directory / 'calls', details)
    path = tmp_path / 'recovery.json'; path.write_text(json.dumps(manifest))
    pointer = evidence_file(path, tmp_path)
    fresh = Scripted()
    recovered = BoundedProduct(tmp_path, tmp_path / 'recovered', fresh, envelope(), list,
        limits=replace(limits(), input_tokens=12000), requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE, requirement_account_recovery=pointer)
    result = recovered.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, {'assignment': 'Keep exception'}, ['o1'])
    assert result == good and not fresh.requests
    assert (recovered.directory / 'calls/detail-0/request.json').read_bytes() == (prior.directory / 'calls/detail-0/request.json').read_bytes()
    with pytest.raises(LegalMathError):
        recovered.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', q, records, {'assignment': 'Changed'}, ['o1'])


def test_known_open_circuit_defers_owner_without_hiding_independent_work(tmp_path, monkeypatch):
    from scripts import legal_integration_phased_live as live
    from scripts.legal_mission_execution import save
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    scope_path = tmp_path / 'service/scope.json'; save(scope_path, {'profile': 'test'})
    scope = evidence_file(scope_path, tmp_path)
    save(tmp_path / live.BASE / 'current-binding.json', {'phase_service_scope': scope})
    save(scope_path.parent / 'service-circuit.json', {'stage_hash': scope['sha256'], 'open': True})
    ready, blocked, sync = ['acquire-p14', 'local-review'], [], []
    def block(tid, reason, evidence, **kwargs):
        blocked.append((tid, reason, evidence)); ready.remove(tid)
    execution = SimpleNamespace(summary=lambda: {'ready': list(ready), 'running': []},
        block_before_dispatch=block, sync_mission=lambda: sync.append(True))
    assert live.defer_open_service(execution, 'acquire-p14')
    assert ready == ['local-review'] and len(blocked) == len(sync) == 1
    assert not live.defer_open_service(execution, 'acquire-p14')
    assert 'before owner reservation' in blocked[0][1]


def test_same_master_amendment_keeps_reviewer_and_independent_dependencies():
    from scripts.legal_integration_lossless_repair import expected_program, REOPEN
    from scripts.legal_integration_master import task
    nodes = [task(t, ['current-binding'] if t == 'account-qualification' else []) for t in REOPEN]
    nodes += [task('semantic-preflight'), task('unrelated-local')]
    old = {'tasks': nodes, 'protected_evidence': []}
    before = {'tasks': {n['id']: {'attempts': [{}, {}, {}, {}, {}]} for n in nodes}}
    pointer = {'path': 'review.md', 'sha256': 'bound'}
    revision = {k: pointer for k in ('review', 'baseline', 'local_review', 'qualification_inputs', 'local_validation')}
    new = expected_program(old, before, revision, None, plan_reference=pointer)
    for original, updated in zip(nodes, new['tasks']):
        if original['id'] in REOPEN:
            assert updated['maximum_attempts'] == 6
            assert updated['requires'] == original['requires'] and updated['after'] == original['after']
        else:
            assert updated == original


def test_single_dispatch_policy_cannot_issue_new_replacements():
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_SINGLE_DISPATCH_POLICY as policy
    assert policy['per_request_replacements'] == 0
    assert policy['maximum_replacements'] == 48  # Historical charges remain spent.
    assert policy['consecutive_failure_ceiling'] == 1
