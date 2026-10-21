"""The user's early timing is exact, counted, and cannot resample a success."""
from datetime import timedelta
from types import SimpleNamespace
import json

import pytest

from scripts import legal_integration_retry_schedule as schedule
from legalmath.canonical import digest
from legalmath.interpretation.search.providers import Completion
from scripts.legal_mission_execution import save
from tests.assurance.test_delayed_service_recovery import setup, failure, REQUEST, SCHEMA


def fixture(tmp_path, monkeypatch, *, index=0):
    allowance, clock = setup(tmp_path, monkeypatch)
    work = tmp_path / 'timing'
    work.mkdir()
    monkeypatch.setattr(schedule, 'ROOT', tmp_path)
    monkeypatch.setattr(schedule, 'WORK', work)
    monkeypatch.setattr(schedule, 'AUTH', work / 'authorization.json')
    monkeypatch.setattr(schedule, 'TARGET', digest(REQUEST))
    monkeypatch.setattr(schedule, 'SCHEMA', digest(SCHEMA))
    monkeypatch.setattr(schedule, 'utc', lambda: clock.now)
    ended = failure(tmp_path, 1, message='stream disconnected before completion: Our servers are currently overloaded')
    allowance.service_circuit(failure=ended)
    allowance.reserve_service_recovery(ended)
    scope, directory, _ = allowance.service_scope()
    auth = dict(maximum_early_probes=3, service_scope=scope,
        times_utc=[(clock.now + timedelta(minutes=m)).isoformat() for m in (0, 17, 77)])
    save(schedule.AUTH, auth)
    monkeypatch.setattr(schedule, 'authority', lambda: auth)
    return allowance, ended, clock, directory, auth


def test_immediate_retry_preserves_charge_and_grants_only_one_exact_probe(tmp_path, monkeypatch):
    allowance, ended, clock, directory, _ = fixture(tmp_path, monkeypatch)
    before = (directory / 'service-recovery.json').read_bytes()
    schedule.scheduled_wait(allowance, ended)
    assert clock.sleeps == []
    assert (directory / 'service-recovery.json').read_bytes() == before
    allowance.service_circuit(reserving=True)
    with pytest.raises(Exception):
        allowance.service_circuit(reserving=True)
    with pytest.raises(Exception):
        schedule.scheduled_wait(allowance, ended)


def test_second_retry_uses_requested_clock_time_and_preserves_previous_charge(tmp_path, monkeypatch):
    allowance, ended, clock, directory, auth = fixture(tmp_path, monkeypatch)
    schedule.scheduled_wait(allowance, ended)
    allowance.service_circuit(reserving=True)
    other = failure(tmp_path, 2, message='stream disconnected before completion: overloaded')
    allowance.service_circuit(failure=other)
    allowance.reserve_service_recovery(other)
    before = (directory / 'service-recovery.json').read_bytes()
    schedule.scheduled_wait(allowance, other)
    assert sum(clock.sleeps) == 17 * 60
    assert (directory / 'service-recovery.json').read_bytes() == before
    assert len(json.loads((schedule.WORK / 'timing.json').read_text())['decisions']) == 2


@pytest.mark.parametrize('fault', ['schema', 'request', 'receipt', 'stage', 'partial_output'])
def test_changed_evidence_cannot_release_retry(tmp_path, monkeypatch, fault):
    allowance, ended, clock, directory, auth = fixture(tmp_path, monkeypatch)
    if fault == 'schema':
        allowance.expected_schema = 'different'
    elif fault == 'request':
        allowance.expected = 'different'
    elif fault == 'receipt':
        path = tmp_path / 'provider-evidence' / f'0001-{digest(REQUEST)[:16]}' / 'events.jsonl'
        path.write_text('{}\n')
    elif fault == 'stage':
        save(tmp_path / 'current-stage.json', {'path': 'changed', 'sha256': '0' * 64})
    else:
        path = tmp_path / 'provider-evidence' / f'0001-{digest(REQUEST)[:16]}' / 'manifest.json'
        value = json.loads(path.read_text())
        value['complete_output_present'] = True
        save(path, value)
    with pytest.raises(Exception):
        schedule.scheduled_wait(allowance, ended)
    assert json.loads((directory / 'service-circuit.json').read_text())['open']


def test_server_wait_overrides_earlier_user_time(tmp_path, monkeypatch):
    _, _, clock, directory, auth = fixture(tmp_path, monkeypatch)
    charge = json.loads((directory / 'service-recovery.json').read_text())['charges'][0]
    assert schedule.requested_due(auth['times_utc'], 0, charge, {'retry_after_seconds': 7200.2}) == (
        clock.now + timedelta(seconds=7201))
    with pytest.raises(Exception):
        schedule.requested_due(auth['times_utc'], 3, charge, {})


def test_unrelated_failure_retains_original_wait(tmp_path, monkeypatch):
    allowance, ended, _, _, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(schedule, 'TARGET', 'another request')
    calls = []
    monkeypatch.setattr(schedule, 'ORIGINAL_WAIT', lambda a, f: calls.append((a, f)))
    schedule.scheduled_wait(allowance, ended)
    assert calls == [(allowance, ended)]
    assert not (schedule.WORK / 'timing.json').exists()


def test_success_cancels_later_times_and_cannot_be_resent(tmp_path, monkeypatch):
    allowance, _, _, _, _ = fixture(tmp_path, monkeypatch)
    calls = []
    def complete(provider, request, schema, settings):
        calls.append(request)
        return Completion({'answer': 'retained'}, {'test': True})
    monkeypatch.setattr(schedule, 'ORIGINAL_COMPLETE', complete)
    monkeypatch.setattr(schedule, 'SLOT', 1)
    provider = SimpleNamespace(allowance=allowance)
    schedule.resumed_complete(provider, REQUEST, SCHEMA, None)
    assert json.loads((schedule.WORK / 'timing.json').read_text())['unused_times_cancelled']
    with pytest.raises(Exception):
        schedule.resumed_complete(provider, REQUEST, SCHEMA, None)
    assert calls == [REQUEST]
