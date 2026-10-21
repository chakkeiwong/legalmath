from copy import deepcopy
from dataclasses import replace
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE, AUDIT
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased import account_input, account_encoding, downstream_input, synthesis
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from tests.assurance.test_bounded_product import Scripted, envelope, limits


def product(tmp_path, **kwargs):
    return BoundedProduct(tmp_path, tmp_path / 'product', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), **kwargs)


@pytest.mark.parametrize('task,schema', [
    ('SYNTHESIZE_FINDINGS', NOTE), ('ANSWER_ORIGINAL_QUESTION', NOTE),
    ('AUDIT_ANSWER_AND_DETAILED_ACCOUNT', AUDIT), ('ASSESS_MATCHED_TOOL_EFFECT', NOTE)])
def test_downstream_wire_preserves_complete_request_and_schema(tmp_path, task, schema):
    p = product(tmp_path)
    records = [r for r in p.route.records.values() if r['kind'] == 'source']
    original = p.request(task, envelope()['original_questions'][0], records,
        payload={'complete': records}, expected=['obligation'])
    plain = prepare(original, schema)
    selected = deepcopy(original)
    selected['downstream_input_profile'] = downstream_input.PROFILE
    packed = prepare(selected, schema)
    expanded = account_encoding.expand({'request': packed['request'], 'response_schema': packed['schema']})
    wire = account_input.expand(expanded['request'])
    del wire['downstream_input_profile']
    assert wire == plain['request'] and expanded['response_schema'] == plain['schema']
    assert account_input.input_token_limit(selected, p.route.limits) == 32768
    assert account_input.input_token_limit(packed['request'], p.route.limits) == 32768
    assert account_input.input_token_limit(original, p.route.limits) == 12000


@pytest.mark.parametrize('change', ['task', 'mixed', 'profile', 'baseline'])
def test_downstream_capacity_cannot_enlarge_other_contracts(tmp_path, change):
    p = product(tmp_path)
    request = {'task': 'SYNTHESIZE_FINDINGS', 'downstream_input_profile': downstream_input.PROFILE}
    bounds = p.route.limits
    if change == 'task': request['task'] = 'ASSESS_ORIGINAL_REQUIREMENT'
    elif change == 'mixed': request['account_input_profile'] = account_input.PROFILE
    elif change == 'profile': request['downstream_input_profile'] = 'unreviewed'
    else: bounds = replace(bounds, input_tokens=50000)
    with pytest.raises(LegalMathError): account_input.input_token_limit(request, bounds)


def test_singleton_normalization_contracts_once_and_preserves_membership(tmp_path, monkeypatch):
    p = PhasedProduct(tmp_path, tmp_path/'answer', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), phase_admit=lambda *a: {}, phase_identity='fixture',
        downstream_input_profile=downstream_input.PROFILE)
    originals = [{'id': 'large-' + str(i), 'value': {'large': True}} for i in range(3)]
    monkeypatch.setattr(synthesis, 'prepare', lambda *args: (deepcopy(originals), {}))
    p.retained_acquisition, p.retained_details = {}, []
    def measure(request, schema):
        if len(request['payload']) > 1 and any(r['value'].get('large') for r in request['payload']):
            raise LegalMathError('E_RESOURCE_LIMIT', details='Originals fit individually only')
        return {'bytes': 100, 'local_tokens': 30}
    monkeypatch.setattr(p.dispatch, 'measure', measure)
    calls = []
    def run(name, items):
        calls.extend(items)
        return {'execution_complete': True, 'results': [{'key': r['key'],
            'result': {'status': 'VALIDATED', 'value': {'considered': r['request']['required_considered']}}}
            for r in items]}
    monkeypatch.setattr(p, 'run_phase', run)
    result = p.reduce('p14', envelope()['original_questions'][0], [])
    assert len(result) == 1 and len(calls) == 4
    assert [c['request']['payload'][0] for c in calls[:3]] == originals
    assert set(result[0]['children']) == {c['key'] for c in calls[:3]}


def test_noncontracting_normalized_results_stop_without_repeat_calls(tmp_path, monkeypatch):
    p = PhasedProduct(tmp_path, tmp_path/'answer', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), phase_admit=lambda *a: {}, phase_identity='fixture',
        downstream_input_profile=downstream_input.PROFILE)
    rows = [{'id': 'large-' + str(i), 'value': {}} for i in range(2)]
    monkeypatch.setattr(synthesis, 'prepare', lambda *args: (deepcopy(rows), {}))
    p.retained_acquisition, p.retained_details = {}, []
    def measure(request, schema):
        if len(request['payload']) > 1: raise LegalMathError('E_RESOURCE_LIMIT', details='Cannot combine')
        return {'bytes': 100}
    monkeypatch.setattr(p.dispatch, 'measure', measure)
    counts = []
    def run(name, items):
        counts.append(len(items))
        return {'execution_complete': True, 'results': [{'key': r['key'],
            'result': {'status': 'VALIDATED', 'value': {}}} for r in items]}
    monkeypatch.setattr(p, 'run_phase', run)
    with pytest.raises(LegalMathError): p.reduce('p14', envelope()['original_questions'][0], [])
    assert counts == [2]


def test_requested_envelope_is_checked_at_dispatch_and_provider(tmp_path):
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    p = product(tmp_path)
    # A controlled counter tests bound enforcement; production replay uses the
    # real tokenizer. This test does not estimate service context capacity.
    p.route.encode = lambda value: range(50000)
    service = object.__new__(BoundedCodexProvider)
    service.encode, service.limits = p.route.encode, p.route.limits
    service.command = lambda *args: ['developer_instructions=fixture']
    request = {'task': 'SYNTHESIZE_FINDINGS', 'records': [], 'payload': 'x' * 205000,
        'downstream_input_profile': downstream_input.PROFILE}
    for measure in (p.dispatch.measure, service.measure):
        with pytest.raises(LegalMathError): measure(request, NOTE)
        selected = {**request, 'downstream_capacity_profile': downstream_input.CAPACITY_PROFILE}
        result = measure(selected, NOTE)
        assert 200000 < result['bytes'] < 250000 and result['local_tokens'] == 50000
        with pytest.raises(LegalMathError): measure({**selected, 'payload': 'x' * 250000}, NOTE)
        with pytest.raises(LegalMathError): measure({**selected, 'downstream_capacity_profile': 'unknown'}, NOTE)


def test_nonadjacent_pair_contracts_without_changing_members():
    from legalmath.interpretation.assurance.phased.grouping import contract_pair
    rows = [{'id': str(i), 'value': {'support': i}} for i in range(4)]
    visited = []
    def measure(items):
        ids = tuple(r['id'] for r in items)
        visited.append(ids)
        return {'bytes': 10} if len(items) == 1 or ids == ('0', '2') else None
    groups = contract_pair(rows, measure)
    assert [[r['id'] for r in g['members']] for g in groups] == [['0', '2'], ['1'], ['3']]
    assert {r['id']: r for g in groups for r in g['members']} == {r['id']: r for r in rows}
    assert ('0', '1') in visited and ('0', '2') in visited


def test_pair_search_is_finite_and_never_truncates():
    from legalmath.interpretation.assurance.phased.grouping import contract_pair
    visited = []
    def missing(items): visited.append([r['id'] for r in items])
    rows = [{'id': str(i)} for i in range(17)]
    assert contract_pair(rows, missing) is None and not visited
    assert contract_pair(rows[:16], missing) is None and len(visited) == 120
    with pytest.raises(LegalMathError): contract_pair([rows[0], rows[0]], missing)


@pytest.mark.parametrize('enlarged,outside', [(True, False), (False, False), (True, True)])
def test_new_intermediate_capacity_is_checked_before_atomic_rejection(tmp_path, monkeypatch, enlarged, outside):
    p = PhasedProduct(tmp_path, tmp_path/'answer', Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), phase_admit=lambda *a: {}, phase_identity='fixture',
        downstream_input_profile=downstream_input.PROFILE,
        downstream_capacity_profile=downstream_input.CAPACITY_PROFILE if enlarged else None)
    originals = [{'id': 'original-' + str(i), 'value': {}} for i in range(3)]
    monkeypatch.setattr(synthesis, 'prepare', lambda *args: (deepcopy(originals), {}))
    p.retained_acquisition, p.retained_details = {}, []

    def measure(request, schema):
        expanded = any(r['value'].get('expanded_support') for r in request['payload'])
        tokens = (71000 if outside else 35000) if expanded else 100
        cap = 70000 if request.get('downstream_capacity_profile') else 32768
        if tokens > cap or len(request['payload']) > 2:
            raise LegalMathError('E_RESOURCE_LIMIT', details='Complete intermediate with its sources exceeds input')
        return {'bytes': 100, 'local_tokens': tokens}

    monkeypatch.setattr(p.dispatch, 'measure', measure)
    phases = []

    def run(name, calls):
        phases.append(calls)
        return {'execution_complete': True, 'results': [{'key': c['key'],
            'result': {'status': 'VALIDATED', 'value': {'expanded_support': True}}} for c in calls]}

    monkeypatch.setattr(p, 'run_phase', run)
    if enlarged and not outside:
        result = p.reduce('p14', envelope()['original_questions'][0], [])
        assert len(result) == 1 and len(phases) == 2
        assert set(result[0]['children']) == {c['key'] for c in phases[0]}
        assert all(c['request']['downstream_capacity_profile'] == downstream_input.CAPACITY_PROFILE
            for c in phases[1])
    else:
        with pytest.raises(LegalMathError): p.reduce('p14', envelope()['original_questions'][0], [])
        assert len(phases) == 1
    assert [r for c in phases[0] for r in c['request']['payload']] == originals
    assert all('downstream_capacity_profile' not in c['request'] for c in phases[0])
