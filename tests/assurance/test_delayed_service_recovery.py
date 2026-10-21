"""Hourly service recovery preserves the exact request and global authority."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from types import SimpleNamespace

import pytest

from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_provider as module
from legalmath.interpretation.assurance.bounded_provider import SERVICE_DELAYED_POLICY as POLICY
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider, Completion
from tests.assurance.test_execution_recovery import receipt
from tests.assurance.test_service_continuation import circuit_allowance, events


REQUEST, SCHEMA = {'question': 'retained request'}, {'type': 'object'}


def setup(tmp_path, monkeypatch, *, hours=48):
    allowance = circuit_allowance(tmp_path)
    stage = {'name': 'delayed', 'service_recovery_policy': POLICY,
             'service_recovery_maximum': POLICY['maximum_replacements']}
    save(tmp_path / 'stage/stage.json', stage)
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    save(tmp_path / 'current-stage.json', evidence_file(tmp_path / 'stage/stage.json', tmp_path))
    save(tmp_path / 'current-binding.json', {'service_recovery_policy': POLICY})
    clock = SimpleNamespace(now=datetime(2026, 10, 16, 14, tzinfo=timezone.utc), sleeps=[])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.now

    monkeypatch.setattr(module, 'datetime', Clock)
    save(allowance.grant_path, {'deadline_utc': (clock.now + timedelta(hours=hours)).isoformat()})
    allowance.check = lambda: None
    allowance.expected, allowance.expected_schema = digest(REQUEST), digest(SCHEMA)

    def sleep(seconds):
        assert 0 < seconds <= 60
        assert json.loads((tmp_path / 'stage/service-circuit.json').read_text())['open']
        clock.sleeps.append(seconds)
        clock.now += timedelta(seconds=seconds)

    monkeypatch.setattr(module.time, 'sleep', sleep)
    return allowance, clock


def failure(tmp_path, slot, *, message=None, **kwargs):
    value = receipt(tmp_path, slot, request_hash=digest(REQUEST), **kwargs)
    folder = tmp_path / 'provider-evidence' / f'{slot:04}-{value.request_hash[:16]}'
    manifest = json.loads((folder / 'manifest.json').read_text())
    content = {'request.json': canonical(REQUEST), 'schema.json': canonical(SCHEMA)}
    if message is not None:
        content['events.jsonl'] = b'\n'.join(canonical(e) for e in events(message))
    for name, data in content.items():
        (folder / name).write_bytes(data)
        manifest['files'][name] = {'retained_sha256': hashlib.sha256(data).hexdigest()}
    save(folder / 'manifest.json', manifest)
    return value


def test_hourly_schedule_honors_longer_server_delay():
    assert module.recovery_delay(POLICY, 0, {}) == 3600
    assert module.recovery_delay(POLICY, 1, {}) == 7200
    assert module.recovery_delay(POLICY, 0, {'retry_after_seconds': 10000.5}) == 10001
    with pytest.raises(LegalMathError):
        module.recovery_delay(POLICY, 0, {'unparsed_retry_after': True})


def test_exact_half_open_probe_is_once_only_and_success_keeps_failures(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    ended = failure(tmp_path, 1)
    allowance.service_circuit(failure=ended)
    assert allowance.reserve_service_recovery(ended) == 3600
    ledger = json.loads((tmp_path / 'stage/service-recovery.json').read_text())
    charge = ledger['charges'][0]
    assert datetime.fromisoformat(charge['next_retry_at_utc']) == clock.now + timedelta(hours=1)
    assert charge['schema_hash'] == digest(SCHEMA) and charge['worker']['pid'] > 0
    with pytest.raises(LegalMathError): allowance.service_circuit()
    allowance.wait_service_recovery(ended)
    assert sum(clock.sleeps) == 3600 and max(clock.sleeps) == 60
    other = type(allowance)(tmp_path, {}, root=tmp_path)
    other.expected, other.expected_schema = digest(REQUEST), digest({'different': 'schema'})
    with pytest.raises(LegalMathError): other.service_circuit(reserving=True)
    allowance.service_circuit(reserving=True)
    with pytest.raises(LegalMathError): allowance.service_circuit(reserving=True)
    with pytest.raises(LegalMathError): allowance.wait_service_recovery(ended)
    allowance.service_circuit(success=True)
    state = json.loads((tmp_path / 'stage/service-circuit.json').read_text())
    assert not state['open'] and state['failed_slots'] == [1] and state['consecutive_failures'] == 0
    assert json.loads((tmp_path / 'stage/service-recovery.json').read_text()) == ledger
    assert allowance.reserve_service_recovery(failure(tmp_path, 2)) == 7200


def test_restarted_wait_uses_saved_due_time(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    ended = failure(tmp_path, 1)
    allowance.service_circuit(failure=ended)
    allowance.reserve_service_recovery(ended)
    clock.now += timedelta(minutes=35)
    restarted = type(allowance)(tmp_path, {}, root=tmp_path)
    restarted.check = lambda: None
    restarted.expected, restarted.expected_schema = digest(REQUEST), digest(SCHEMA)
    restarted.wait_service_recovery(ended)
    assert sum(clock.sleeps) == 25 * 60


def test_deadline_refuses_unschedulable_retry_without_charge(tmp_path, monkeypatch):
    allowance, _ = setup(tmp_path, monkeypatch, hours=1)
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(failure(tmp_path, 1))
    assert not (tmp_path / 'stage/service-recovery.json').exists()


@pytest.mark.parametrize('fault', ['due', 'schema', 'receipt', 'stage', 'ledger', 'different_failure'])
def test_changed_schedule_or_evidence_cannot_reopen(tmp_path, monkeypatch, fault):
    allowance, clock = setup(tmp_path, monkeypatch)
    ended = failure(tmp_path, 1)
    allowance.service_circuit(failure=ended)
    allowance.reserve_service_recovery(ended)
    path = tmp_path / 'stage/service-recovery.json'
    value = json.loads(path.read_text())
    if fault == 'due': value['charges'][0]['next_retry_at_utc'] = clock.now.isoformat()
    elif fault == 'schema': allowance.expected_schema = 'changed'
    elif fault == 'receipt': (tmp_path / value['charges'][0]['evidence']).write_text('{}')
    elif fault == 'stage': save(tmp_path / 'current-stage.json', {'path': 'changed', 'sha256': '0'*64})
    elif fault == 'ledger': value['maximum'] += 1
    else: allowance.service_circuit(failure=failure(tmp_path, 2))
    save(path, value)
    clock.now += timedelta(hours=1)
    with pytest.raises((LegalMathError, OSError)): allowance.wait_service_recovery(ended)
    assert json.loads((tmp_path / 'stage/service-circuit.json').read_text())['open']


@pytest.mark.parametrize('message', ['invalid_request: invalid parameter', 'HTTP 499',
    'I cannot assist with this request', '401 unauthorized', '429 insufficient_quota'])
def test_nonservice_outcomes_do_not_get_hourly_replacements(tmp_path, monkeypatch, message):
    allowance, _ = setup(tmp_path, monkeypatch)
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(failure(tmp_path, 1, message=message))


def test_completed_turn_cannot_be_retried(tmp_path, monkeypatch):
    allowance, _ = setup(tmp_path, monkeypatch)
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(failure(tmp_path, 1, completed=True))


def test_timeout_cannot_hide_a_refusal_or_invalid_request(tmp_path, monkeypatch):
    allowance, _ = setup(tmp_path, monkeypatch)
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(failure(tmp_path, 1, timeout=True,
            message='invalid_request: blocked by our safety systems'))


def test_delayed_replacements_remain_finite_and_duplicate_charge_is_rejected(tmp_path, monkeypatch):
    allowance, _ = setup(tmp_path, monkeypatch)
    first = failure(tmp_path, 1)
    allowance.reserve_service_recovery(first)
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(first)
    for slot in range(2, 25): allowance.reserve_service_recovery(failure(tmp_path, slot))
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(failure(tmp_path, 25))
    assert len(json.loads((tmp_path / 'stage/service-recovery.json').read_text())['charges']) == 24


def test_provider_waits_then_sends_exact_request_once(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    provider = object.__new__(module.BoundedCodexProvider)
    provider.allowance, provider.check = allowance, lambda: None
    provider.measure, provider.encode = lambda *args: {}, list
    provider.limits = SimpleNamespace(output_tokens=1000)
    sent = []

    def complete(self, request, schema, settings):
        self.allowance.service_circuit(reserving=True)
        sent.append((deepcopy(request), deepcopy(schema), clock.now))
        if len(sent) == 1:
            raise failure(tmp_path, 1)
        return Completion({'ok': True}, {'provider': 'offline-fixture'})

    monkeypatch.setattr(CodexProvider, 'complete', complete)
    result = provider.complete(REQUEST, SCHEMA, Settings(timeout_seconds=300))
    assert result.value == {'ok': True} and result.provenance['application_replacements'] == 1
    assert sent[0][:2] == sent[1][:2] == (REQUEST, SCHEMA)
    assert sent[1][2] - sent[0][2] == timedelta(hours=1)


def test_hourly_phase_reserves_calls_but_not_hypothetical_two_day_outage(tmp_path):
    from tests.assurance.test_phased_admission import setup as phase_setup
    from legalmath.interpretation.assurance.phased.admission import admit
    base, live, allowance = phase_setup(tmp_path)
    path = tmp_path / base / 'current-binding.json'
    binding = json.loads(path.read_text())
    binding['service_recovery_policy'] = POLICY
    save(path, binding)
    grant_path = tmp_path / base / 'live-grant.json'
    grant = json.loads(grant_path.read_text())
    grant['deadline_utc'] = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    save(grant_path, grant)
    pointer = admit(tmp_path, base, live, 'first', 1, owner='p10')
    assert json.loads((tmp_path / pointer['path']).read_text())['maximum_calls'] == 25
    with pytest.raises(LegalMathError): admit(tmp_path, base, live, 'too-long', 24, owner='p10')
