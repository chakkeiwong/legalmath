"""A reboot resumes one saved wait without resampling or blocking other owners."""
from types import SimpleNamespace
import json

import pytest

from legalmath.canonical import digest
from legalmath.interpretation.search.providers import Completion
from scripts import legal_integration_reboot_resume as reboot
from scripts.legal_mission_execution import save


@pytest.fixture
def pending(tmp_path, monkeypatch):
    request, schema = {'task': 'pending'}, {'type': 'object'}
    monkeypatch.setattr(reboot, 'WORK', tmp_path)
    monkeypatch.setattr(reboot, 'TARGET', digest(request))
    monkeypatch.setattr(reboot, 'SCHEMA', digest(schema))
    monkeypatch.setattr(reboot, 'authority', lambda: {})
    save(tmp_path / 'baseline.json', {'charge': {'next_retry_at_utc': '2026-10-20T00:32:37+00:00'}})
    calls = []
    allowance = SimpleNamespace(wait_service_recovery=lambda failure: calls.append(('wait', failure.allowance_slot)))
    provider = SimpleNamespace(allowance=allowance)
    def complete(provider, value, shape, settings):
        calls.append(('call', value))
        return Completion({'ok': True}, {'slot': 3437})
    monkeypatch.setattr(reboot, 'ORIGINAL_COMPLETE', complete)
    return provider, request, schema, calls


def test_reboot_resumes_existing_wait_before_exact_call_and_cannot_resample(pending):
    provider, request, schema, calls = pending
    reboot.resume_complete(provider, request, schema, None)
    assert calls == [('wait', 3436), ('call', request)]
    assert provider.allowance.expected == digest(request)
    assert provider.allowance.expected_schema == digest(schema)
    with pytest.raises(Exception, match='already started'):
        reboot.resume_complete(provider, request, schema, None)


def test_other_request_cannot_precede_recovery_but_can_follow_success(pending):
    provider, request, schema, calls = pending
    other = {'task': 'independent'}
    with pytest.raises(Exception, match='preceded'):
        reboot.resume_complete(provider, other, schema, None)
    assert calls == []
    reboot.resume_complete(provider, request, schema, None)
    reboot.resume_complete(provider, other, schema, None)
    assert calls[-1] == ('call', other)


def test_failed_candidate_does_not_add_dependency_to_independent_work(pending, monkeypatch):
    provider, request, schema, calls = pending
    def complete(provider, value, shape, settings):
        if value == request:
            raise ValueError('candidate failed')
        return Completion({'independent': True}, {})
    monkeypatch.setattr(reboot, 'ORIGINAL_COMPLETE', complete)
    with pytest.raises(ValueError, match='candidate failed'):
        reboot.resume_complete(provider, request, schema, None)
    assert not (reboot.WORK / 'recovered-response.json').exists()
    assert reboot.resume_complete(provider, {'task': 'independent'}, schema, None).value['independent']


def test_changed_schema_cannot_consume_wait(pending):
    provider, request, schema, calls = pending
    with pytest.raises(Exception, match='schema'):
        reboot.resume_complete(provider, request, {'type': 'string'}, None)
    assert calls == []
    assert not (reboot.WORK / 'resume-started.json').exists()


def test_wait_integrity_failure_does_not_release_unrelated_call(pending):
    provider, request, schema, calls = pending
    def invalid(_):
        raise ValueError('changed evidence')
    provider.allowance.wait_service_recovery = invalid
    with pytest.raises(ValueError):
        reboot.resume_complete(provider, request, schema, None)
    assert not (reboot.WORK / 'pending-call-settled.json').exists()
    with pytest.raises(Exception, match='preceded'):
        reboot.resume_complete(provider, {'task': 'other'}, schema, None)


@pytest.mark.parametrize('output', ['result.json', 'raw.json', 'wire-response.json'])
def test_any_saved_output_blocks_pending_reconciliation(tmp_path, monkeypatch, output):
    wire = {'request': {'pending': True}, 'schema': {'type': 'object'},
        'original_request': {'original': True}, 'original_schema': {'type': 'object'}}
    monkeypatch.setattr(reboot, 'TARGET', digest(wire['request']))
    monkeypatch.setattr(reboot, 'SCHEMA', digest(wire['schema']))
    monkeypatch.setattr(reboot, 'historical_request', lambda value, reviewed: value['original_request'])
    for filename, value in [('reference-binding.json', wire), ('request.json', wire['original_request']),
            ('schema.json', wire['original_schema']), (output, {})]:
        save(tmp_path / filename, value)
    with pytest.raises(Exception, match='already has output'):
        reboot.authenticated_wire(tmp_path)
