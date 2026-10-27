"""Shared outages pause pending provider work without creating failed reviews."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, AUDIT
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.phased import capacity_policy, group_review, context_bridge
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased.phase import execute
from legalmath.interpretation.assurance.phased.service_prerequisite import PROFILE, ServiceDeferred
from legalmath.interpretation.assurance.phased.source_review import assignments
from tests.assurance.test_bounded_product import envelope, limits, Scripted
from tests.assurance.test_source_review_repair import decision


class Outage(Scripted):
    def __init__(self, *, fail_at=None):
        super().__init__(fail_at)
        self.open = False
        self.checks = 0

    def check_service(self, request, schema):
        self.checks += 1
        if self.open:
            raise ServiceDeferred('Shared service circuit open')

    def complete(self, request, schema, settings):
        if not self.requests:
            self.open = True
        return super().complete(request, schema, settings)


def setup(tmp_path, *, capacity=False, provider=None):
    service = provider or Outage()
    p = PhasedProduct(tmp_path, tmp_path/'p', service, envelope(), list, limits=limits(),
        phase_identity='test.v1', phase_admit=lambda name, count: dict(name=name, count=count),
        common_capacity_profile=capacity_policy.PROFILE if capacity else None,
        service_prerequisite_profile=PROFILE)
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    request = p._request('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT', envelope()['original_questions'][0],
        sources, payload={'answer': {'conclusion': 'Conditional.'}}, expected=[r['id'] for r in sources])
    calls = [dict(key='review-'+str(i), request=deepcopy(request), schema=AUDIT,
        validate=lambda value: p.citations(value, sources)) for i in range(3)]
    return p, calls


@pytest.mark.parametrize('capacity', [False, True])
def test_midphase_outage_keeps_settled_result_and_resumes_without_duplicate(tmp_path, capacity):
    p, calls = setup(tmp_path, capacity=capacity)
    with pytest.raises(ServiceDeferred):
        p.run_phase('reviews', calls)
    assert len(p.provider.requests) == 1
    journal = p.dispatch.directory/'dispatch.json'
    assert set(json.loads(journal.read_text())['calls']) == {'review-0'}
    assert not (p.dispatch.directory/'review-1').exists()
    saved = (p.dispatch.directory/'review-0/result.json').read_bytes()
    if capacity:
        state = json.loads((p.directory/'capacity/review-1/state.json').read_text())
        assert state['status'] == 'DEFERRED_SERVICE' and 'result_hash' not in state
        assert not (p.directory/'capacity-phases/reviews/outcome.json').exists()
    else:
        state = json.loads((p.directory/'phases/reviews/phase.json').read_text())
        assert state['status'] == 'DEFERRED_SERVICE'
        assert not (p.directory/'phases/reviews/outcome.json').exists()
    # Authenticated recovery is the supervisor's responsibility. This fixture
    # changes availability only; it does not replenish any budget or attempt.
    p.provider.open = False
    outcome = p.run_phase('reviews', calls)
    assert outcome['execution_complete'] and len(p.provider.requests) == 3
    assert (p.dispatch.directory/'review-0/result.json').read_bytes() == saved
    assert p.run_phase('reviews', calls) == outcome and len(p.provider.requests) == 3


def test_actual_failed_dispatch_stays_failed_and_pending_siblings_are_not_failed(tmp_path):
    p, calls = setup(tmp_path, capacity=True, provider=Outage(fail_at=1))
    with pytest.raises(ServiceDeferred):
        p.run_phase('reviews', calls)
    first = json.loads((p.dispatch.directory/'review-0/result.json').read_text())
    assert first['status'] == 'FAILED' and first['error'] == 'RuntimeError'
    p.provider.open = False
    outcome = p.run_phase('reviews', calls)
    assert outcome['results'][0]['result'] == first
    assert all(r['result']['status'] == 'VALIDATED' for r in outcome['results'][1:])
    assert len(p.provider.requests) == 3


def test_open_circuit_does_not_block_exact_shared_result_or_local_validation(tmp_path):
    service = Outage()
    p = BoundedProduct(tmp_path, tmp_path/'old', service, envelope(), list, limits=limits())
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    request = p._request('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT', envelope()['original_questions'][0],
        sources, expected=[r['id'] for r in sources])
    old = p.dispatch.call('read-reviewed', request, AUDIT, lambda value: p.citations(value, sources))
    p2 = BoundedProduct(tmp_path, tmp_path/'new', service, envelope(), list, limits=limits(),
        shared_prefix=p.dispatch.directory, service_prerequisite_profile=PROFILE)
    current = p2.dispatch.call('read-reviewed', request, AUDIT, lambda value: p2.citations(value, sources))
    assert current == old and service.checks == 0 and len(service.requests) == 1
    p2.citations(current['value'], sources)


def test_context_loop_propagates_deferral_instead_of_failed_bridges(tmp_path, monkeypatch):
    p, _ = setup(tmp_path, capacity=True)
    item = assignments(p, 'p14', [])[0]
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    value = decision(sources[0], 'UNRESOLVED')
    value.update(considered=[item['id']], context_needs=[dict(kind='SOURCE_TEXT',
        record_ids=[sources[-1]['id']], locators=[], query='', reason='Exception needed')])
    initial = dict(status='VALIDATED', value=value)
    monkeypatch.setattr(group_review, 'run', lambda *a, **k: [deepcopy(initial)])
    p.provider.open = True
    with pytest.raises(ServiceDeferred):
        p.audit_answer('p14', envelope()['original_questions'][0], {'conclusion': 'Conditional.'}, [])
    assert not p.provider.requests
    assert not list(p.directory.glob('context-review-*.json'))


@pytest.mark.parametrize('reason,deferred', [
    ('Shared service circuit open after repeated terminal failures; stage requires reviewed continuation', True),
    ('Only the scheduled service retry may probe the open circuit', True),
    ('Stage replacement reserve exhausted', False),
])
def test_exact_provider_preflight_only_classifies_known_unavailability(reason, deferred):
    allowance = SimpleNamespace()
    def refuse():
        raise LegalMathError('E_RESOURCE_LIMIT', details=reason)
    allowance.service_circuit = refuse
    service = SimpleNamespace(fork=lambda: SimpleNamespace(check=lambda: None, allowance=allowance))
    request, schema = {'task': 'test'}, {'type': 'object'}
    with pytest.raises(LegalMathError) as error:
        BoundedCodexProvider.check_service(service, request, schema)
    assert isinstance(error.value, ServiceDeferred) == deferred
    assert allowance.expected == digest(request) and allowance.expected_schema == digest(schema)


def test_uncertain_dispatch_remains_authority_veto(tmp_path):
    p, calls = setup(tmp_path, capacity=True)
    with pytest.raises(ServiceDeferred):
        p.run_phase('reviews', calls)
    journal = p.dispatch.directory/'dispatch.json'
    state = json.loads(journal.read_text())
    state['calls']['review-0']['status'] = 'RESERVED'
    journal.write_text(json.dumps(state))
    p.provider.open = False
    with pytest.raises(LegalMathError) as error:
        p.run_phase('reviews', calls)
    assert error.value.code == 'E_AUTHORITY' and len(p.provider.requests) == 1
