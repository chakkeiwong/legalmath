"""Observed transport failures and mutation of a reused dispatch journal."""
from copy import deepcopy
from threading import Thread

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import transient_service_details
from legalmath.interpretation.assurance.phased import account_recovery
from tests.assurance.test_account_recovery_lineage import lineage, put


def events(message):
    return [{'type': 'error', 'message': message},
            {'type': 'turn.failed', 'error': {'message': message}}]


def test_observed_gateway_timeout_is_service_failure_only_without_output():
    recorded = events('unexpected status 504 Gateway Timeout: Gateway Timeout')
    assert transient_service_details(recorded, output_present=False)
    assert transient_service_details(recorded, output_present=True) is None
    assert transient_service_details(recorded + [{'type': 'turn.completed'}], output_present=False) is None


@pytest.mark.parametrize('message', [
    'unexpected status 499 <unknown status code>: Client Closed Request',
    '{"error":{"code":"invalid_request","type":"invalid_request_error"}}',
    'This request was blocked by our safety systems. Reason: Potentially unintended activity.',
])
def test_unresolved_failures_cannot_become_retries_through_wrapper_text(message):
    assert transient_service_details(events(message), output_present=False) is None
    assert transient_service_details(events(message) + events('stream disconnected before completion'),
                                     output_present=False) is None


def test_changed_dispatch_during_validation_is_rejected(tmp_path, monkeypatch):
    manifest, *_ = lineage(tmp_path)
    pointer = put(tmp_path, 'composite.json', manifest)
    original = account_recovery.read_evidence
    changed = []

    def read(reference, root, **kwargs):
        value = original(reference, root, **kwargs)
        if reference == manifest['account_recovery']['details'] and not changed:
            # An independently writing thread changes valid JSON after the first
            # dispatch read. The final byte check must still catch it.
            path = tmp_path / manifest['dispatch']['path']
            worker = Thread(target=lambda: path.write_bytes(path.read_bytes() + b' '))
            worker.start(); worker.join()
            changed.append(True)
        return value

    monkeypatch.setattr(account_recovery, 'read_evidence', read)
    with pytest.raises(LegalMathError):
        account_recovery.load(tmp_path, pointer, manifest['input_hash'])
    assert changed


def test_validation_does_not_reuse_journal_across_operations(tmp_path):
    manifest, *_ = lineage(tmp_path)
    pointer = put(tmp_path, 'composite.json', manifest)
    assert account_recovery.load(tmp_path, pointer, manifest['input_hash']) == manifest
    path = tmp_path / manifest['dispatch']['path']
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(LegalMathError):
        account_recovery.load(tmp_path, pointer, manifest['input_hash'])


def test_changed_origin_mapping_does_not_share_another_journal(tmp_path):
    manifest, *_ = lineage(tmp_path)
    changed = deepcopy(manifest)
    changed['original_dispatches']['detail-1'] = changed['dispatch']
    pointer = put(tmp_path, 'changed-origin.json', changed)
    with pytest.raises(LegalMathError):
        account_recovery.load(tmp_path, pointer, changed['input_hash'])
