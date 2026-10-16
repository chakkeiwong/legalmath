"""Regression controls for reproduced cache and native boundary defects."""
from copy import deepcopy
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_integration_rehearsal import UnresolvedProvider
from tests.assurance.test_bounded_product import Scripted, envelope, limits


@pytest.mark.parametrize('shared', [False, True])
@pytest.mark.parametrize('change', ['model', 'live', 'settings', 'protocol'])
def test_completed_dispatch_rejects_changed_provider(tmp_path, shared, change):
    provider = Scripted()
    provider.routing = {'model': 'model-a'}
    first = BoundedProduct(tmp_path, tmp_path/'first', provider, envelope(), list, limits=limits())
    first.investigate()
    fresh = Scripted()
    fresh.routing = {'model': 'model-b' if change == 'model' else 'model-a'}
    if change == 'live': fresh.live = True
    if change == 'protocol': fresh.reference_transport = True
    resumed = BoundedProduct(tmp_path, tmp_path/('second' if shared else 'first'), fresh,
        envelope(), list, limits=limits(), shared_prefix=tmp_path/'first/calls' if shared else None)
    if change == 'settings': resumed.dispatch.settings.timeout_seconds = 119
    with pytest.raises(LegalMathError): resumed.investigate()
    assert not fresh.requests


def test_provider_mutation_mid_run_refuses_next_dispatch(tmp_path):
    provider = Scripted()
    provider.routing = {'model': 'model-a'}
    product = BoundedProduct(tmp_path, tmp_path/'p', provider, envelope(), list, limits=limits())
    provider.routing['model'] = 'model-b'
    with pytest.raises(LegalMathError) as caught: product.investigate()
    assert caught.value.code == 'E_AUTHORITY'
    assert not provider.requests


class Native:
    tools = ('bm25',)

    def __init__(self, fault=None):
        self.fault, self.calls = fault, 0
        self.binding = {'implementation': 'fixture-v1', 'tools': list(self.tools)}

    def identity(self): return self.binding

    def retrieval(self, packet, inputs, folder):
        self.calls += 1
        if self.fault == 'packet': packet['units'][0]['text'] = 'MUTATED'
        if self.fault == 'inputs': inputs['question'] = 'MUTATED'
        if self.fault == 'backend': self.binding['implementation'] = 'fixture-v2'
        if self.fault == 'failure': raise RuntimeError('Native worker failed')
        if self.fault == 'uncertain': raise KeyboardInterrupt()
        if self.fault == 'status': return {'status': 'ACCEPT'}
        if self.fault == 'reserved': return {'status': 'PASS', 'packet_hash': 'FORGED'}
        return {'status': 'PASS', 'tool': 'Fixture', 'passages': deepcopy(packet['units'])}


def product_with_native(tmp_path):
    return BoundedProduct(tmp_path, tmp_path/'p', UnresolvedProvider(), envelope(), list,
                          limits=limits(), selected_tools=['bm25'])


def run_native(product, backend):
    return product.tools('p14', envelope()['original_questions'][0], backend)


def test_native_resume_reuses_exact_completed_result(tmp_path):
    backend = Native()
    first = run_native(product_with_native(tmp_path), backend)
    result_path = tmp_path/'p/native/p14/bm25/product-result.json'
    before = result_path.read_bytes()
    assert run_native(product_with_native(tmp_path), backend) == first
    assert backend.calls == 1
    assert result_path.read_bytes() == before


@pytest.mark.parametrize('change', ['result', 'backend', 'input'])
def test_native_resume_rejects_changed_binding_or_result(tmp_path, change):
    backend = Native()
    product = product_with_native(tmp_path)
    run_native(product, backend)
    question = envelope()['original_questions'][0]
    if change == 'result':
        save(tmp_path/'p/native/p14/bm25/product-result.json', {'status': 'PASS', 'passages': []})
    if change == 'backend': backend.binding['implementation'] = 'fixture-v2'
    if change == 'input': question['text'] = 'Changed question'
    with pytest.raises(LegalMathError): product.tools('p14', question, backend)
    assert backend.calls == 1


@pytest.mark.parametrize('fault', ['packet', 'inputs', 'backend', 'status', 'reserved'])
def test_native_mutation_or_invalid_output_stops_downstream_generation(tmp_path, fault):
    backend = Native(fault)
    product = product_with_native(tmp_path)
    original = deepcopy(product.route.envelope)
    with pytest.raises(LegalMathError): run_native(product, backend)
    assert product.route.envelope == original
    assert not product.provider.requests
    journal = json.loads((tmp_path/'p/native/p14/bm25/product-binding.json').read_text())
    assert journal['status'] == 'FAILED'
    with pytest.raises(LegalMathError): run_native(product, backend)
    assert backend.calls == 1


@pytest.mark.parametrize('fault', ['failure', 'uncertain'])
def test_native_failed_or_uncertain_action_is_not_replayed(tmp_path, fault):
    backend = Native(fault)
    product = product_with_native(tmp_path)
    with pytest.raises(KeyboardInterrupt if fault == 'uncertain' else RuntimeError):
        run_native(product, backend)
    with pytest.raises(LegalMathError) as caught: run_native(product, backend)
    assert caught.value.code == ('E_AUTHORITY' if fault == 'uncertain' else 'E_DEPENDENCY')
    assert backend.calls == 1
    assert not product.provider.requests
