"""Retry waits must survive the real ledger before another wire call."""
import json
from types import SimpleNamespace

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import (
    BoundedCodexProvider, SERVICE_CONTINUATION_POLICY, recovery_delay)
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider, Completion
from tests.assurance.test_execution_recovery import receipt
from tests.assurance.test_service_continuation import circuit_allowance


def test_fractional_jitter_persists_without_changing_retry_ceilings(tmp_path, monkeypatch):
    allowance = circuit_allowance(tmp_path)
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.random.uniform',
                        lambda a, b: 1.5)
    request_hash = digest({'same': 'request'})
    waits = [allowance.reserve_service_recovery(receipt(tmp_path, slot, request_hash=request_hash))
             for slot in (1, 2, 3)]
    assert waits == [32, 62, 122] and all(type(wait) is int for wait in waits)
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(receipt(tmp_path, 4, request_hash=request_hash))
    for slot in range(5, 50):
        allowance.reserve_service_recovery(receipt(tmp_path, slot))
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(receipt(tmp_path, 50))
    ledger = json.loads((tmp_path/'stage/service-recovery.json').read_text())
    assert len(ledger['charges']) == 48
    assert [row['backoff_seconds'] for row in ledger['charges'][:3]] == waits


def test_fractional_requested_wait_rounds_up(monkeypatch):
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.random.uniform',
                        lambda a, b: 0.25)
    wait = recovery_delay(SERVICE_CONTINUATION_POLICY, 0, {'retry_after_seconds': 30.5})
    assert type(wait) is int and wait == 31


def test_provider_sleeps_persisted_wait_and_keeps_same_request(tmp_path, monkeypatch):
    allowance = circuit_allowance(tmp_path)
    provider = object.__new__(BoundedCodexProvider)
    provider.allowance = allowance
    provider.check = lambda: None
    provider.measure = lambda *args: {}
    provider.encode = list
    provider.limits = SimpleNamespace(output_tokens=1000)
    dispatched, slept = [], []
    request, schema = {'same': 'request'}, {'type': 'object'}

    def complete(self, actual, actual_schema, settings):
        dispatched.append((actual, actual_schema, settings.timeout_seconds))
        if len(dispatched) <= 3:
            raise receipt(tmp_path, len(dispatched), request_hash=digest(actual))
        return Completion({'ok': True}, {'provider': 'offline-fixture'})

    def sleep(wait):
        ledger = json.loads((tmp_path/'stage/service-recovery.json').read_text())
        assert ledger['charges'][-1]['backoff_seconds'] == wait
        slept.append(wait)

    monkeypatch.setattr(CodexProvider, 'complete', complete)
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.random.uniform',
                        lambda a, b: 1.5)
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.time.sleep', sleep)
    result = provider.complete(request, schema, Settings(timeout_seconds=300))
    assert result.value == {'ok': True}
    assert result.provenance['application_replacements'] == 3
    assert dispatched == [(request, schema, 300)] * 4
    assert slept == [32, 62, 122]


@pytest.mark.parametrize('changed', [False, True])
def test_missing_only_checkpoint_refuses_new_or_changed_completed_request(tmp_path, changed):
    from tests.assurance.test_service_continuation import full_checkpoint
    from tests.assurance.test_bounded_product import Scripted, envelope, limits
    from legalmath.interpretation.assurance.bounded_product import BoundedProduct
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    from legalmath.interpretation.assurance.monitor import save
    records, path, manifest, result, review = full_checkpoint(tmp_path)
    manifest['missing_only'] = True
    save(path, manifest)
    provider = Scripted()
    product = BoundedProduct(tmp_path, tmp_path/'new', provider, envelope(), list,
        limits=limits(), retained_initial=evidence_file(path, tmp_path))
    with pytest.raises(LegalMathError):
        product.note('correction-p14' if changed else 'corrected-audit-new',
            'CORRECT_REVIEWED_ANSWER', 'Changed' if changed else 'Question', records, None, [])
    assert not provider.requests
