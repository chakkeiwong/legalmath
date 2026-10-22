"""Timing changes do not change evidence, resource limits or product semantics."""
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import subprocess
import sys

import pytest

spec = importlib.util.spec_from_file_location('five_minute_retry', Path(__file__).with_name('five_minute_retry.py'))
retry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retry)
from legalmath.canonical import digest
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import CodexProvider, Completion
from scripts.legal_mission_execution import save
from tests.assurance.test_delayed_service_recovery import setup, failure, REQUEST, SCHEMA


def fixture(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    work = tmp_path / 'timing'
    work.mkdir()
    monkeypatch.setattr(retry, 'ROOT', tmp_path)
    monkeypatch.setattr(retry, 'WORK', work)
    monkeypatch.setattr(retry, 'AUTH', work / 'authority.json')
    monkeypatch.setattr(retry, 'utc', lambda: clock.now)
    pointer, directory, _ = allowance.service_scope()
    auth = dict(service_scope=pointer)
    save(retry.AUTH, auth)
    monkeypatch.setattr(retry, 'authority', lambda: auth)
    monkeypatch.setattr(retry.providers, 'transient_service_details', retry.resume.classify)
    return allowance, clock, directory


def reserve(allowance, tmp_path, slot=1, **kwargs):
    ended = failure(tmp_path, slot, **kwargs)
    allowance.service_circuit(failure=ended)
    allowance.reserve_service_recovery(ended)
    return ended


def test_elapsed_wait_is_credited_and_original_charge_is_unchanged(tmp_path, monkeypatch):
    allowance, clock, directory = fixture(tmp_path, monkeypatch)
    ended = reserve(allowance, tmp_path, message='request timed out')
    before = (directory / 'service-recovery.json').read_bytes()
    clock.now += timedelta(minutes=20)
    retry.five_minute_wait(allowance, ended)
    assert clock.sleeps == []
    assert (directory / 'service-recovery.json').read_bytes() == before
    allowance.service_circuit(reserving=True)
    with pytest.raises(Exception):
        allowance.service_circuit(reserving=True)
    with pytest.raises(Exception):
        retry.five_minute_wait(allowance, ended)


def test_restart_with_two_minutes_elapsed_waits_only_three_minutes(tmp_path, monkeypatch):
    allowance, clock, _ = fixture(tmp_path, monkeypatch)
    ended = reserve(allowance, tmp_path)
    clock.now += timedelta(minutes=2)
    retry.five_minute_wait(allowance, ended)
    assert sum(clock.sleeps) == 180


def test_normal_provider_two_failures_then_success_uses_five_minutes_each(tmp_path, monkeypatch):
    allowance, clock, directory = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(retry.bp, 'recovery_delay', retry.retry_delay)
    monkeypatch.setattr(retry.bp.CampaignAllowance, 'wait_service_recovery', retry.five_minute_wait)
    provider = object.__new__(retry.bp.BoundedCodexProvider)
    provider.allowance, provider.check = allowance, lambda: None
    provider.measure, provider.encode = lambda *args: {}, list
    provider.limits = SimpleNamespace(output_tokens=1000)
    sent = []

    def complete(self, request, schema, settings):
        self.allowance.service_circuit(reserving=True)
        sent.append((request, schema, clock.now))
        if len(sent) < 3:
            raise failure(tmp_path, len(sent), message='request timed out')
        return Completion({'ok': True}, {'provider': 'offline-fixture'})

    monkeypatch.setattr(CodexProvider, 'complete', complete)
    result = provider.complete(REQUEST, SCHEMA, Settings(timeout_seconds=300))
    assert result.value == {'ok': True}
    assert all(row[:2] == (REQUEST, SCHEMA) for row in sent)
    assert sent[1][2] - sent[0][2] == sent[2][2] - sent[1][2] == timedelta(minutes=5)
    ledger = json.loads((directory / 'service-recovery.json').read_text())
    assert len(ledger['charges']) == 2 and ledger['maximum'] == 24
    assert [r['backoff_seconds'] for r in ledger['charges']] == [300, 300]
    assert result.provenance['application_replacements'] == 2


def test_longer_server_delay_wins(tmp_path, monkeypatch):
    allowance, clock, _ = fixture(tmp_path, monkeypatch)
    ended = reserve(allowance, tmp_path, message='HTTP 503 Service Unavailable; retry-after: 601 seconds')
    retry.five_minute_wait(allowance, ended)
    assert sum(clock.sleeps) == 601


@pytest.mark.parametrize('details', [dict(unparsed_retry_after=True), dict(retry_after_seconds=-1),
    dict(retry_after_seconds=float('inf')), dict(retry_after_seconds='300'), dict(retry_after_seconds=True)])
def test_ambiguous_server_delays_are_refused(details):
    with pytest.raises(Exception):
        retry.retry_delay(retry.bp.SERVICE_DELAYED_POLICY, 0, details)


@pytest.mark.parametrize('fault', ['request', 'schema', 'receipt', 'stage', 'ledger', 'scope', 'partial', 'completed'])
def test_mutated_evidence_cannot_open_circuit(tmp_path, monkeypatch, fault):
    allowance, clock, directory = fixture(tmp_path, monkeypatch)
    ended = reserve(allowance, tmp_path)
    path = directory / 'service-recovery.json'
    ledger = json.loads(path.read_text())
    receipt = tmp_path / ledger['charges'][0]['evidence']
    if fault == 'request':
        allowance.expected = 'changed'
    elif fault == 'schema':
        allowance.expected_schema = 'changed'
    elif fault == 'receipt':
        receipt.write_text('{}')
    elif fault == 'stage':
        save(tmp_path / 'current-stage.json', {'path': 'changed', 'sha256': '0' * 64})
    elif fault == 'ledger':
        ledger['maximum'] = 25
        save(path, ledger)
    elif fault == 'scope':
        monkeypatch.setattr(retry, 'authority', lambda: {'service_scope': {'path': 'changed'}})
    else:
        events = receipt.parent / 'events.jsonl'
        with events.open('a') as handle:
            handle.write('\n' + json.dumps({'type': 'turn.completed'} if fault == 'completed' else
                {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}}))
        manifest = json.loads(receipt.read_text())
        manifest['files']['events.jsonl']['retained_sha256'] = retry.sha256(events.read_bytes()).hexdigest()
        save(receipt, manifest)
        ledger['charges'][0]['receipt_sha256'] = retry.sha256(receipt.read_bytes()).hexdigest()
        save(path, ledger)
    with pytest.raises(Exception):
        retry.five_minute_wait(allowance, ended)
    assert json.loads((directory / 'service-circuit.json').read_text())['open']


def test_five_minute_reservations_do_not_replenish_budget(tmp_path, monkeypatch):
    allowance, _, directory = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(retry.bp, 'recovery_delay', retry.retry_delay)
    for slot in range(1, 25):
        allowance.reserve_service_recovery(failure(tmp_path, slot))
    before = (directory / 'service-recovery.json').read_bytes()
    with pytest.raises(Exception):
        allowance.reserve_service_recovery(failure(tmp_path, 25))
    assert (directory / 'service-recovery.json').read_bytes() == before


def test_deadline_is_checked_again_before_release(tmp_path, monkeypatch):
    allowance, clock, directory = fixture(tmp_path, monkeypatch)
    ended = reserve(allowance, tmp_path)
    save(allowance.grant_path, {'deadline_utc': (clock.now + timedelta(minutes=6)).isoformat()})
    with pytest.raises(Exception):
        retry.five_minute_wait(allowance, ended)
    assert json.loads((directory / 'service-circuit.json').read_text())['open']


def test_actual_retained_timeout_has_exact_request_identity():
    request, schema = retry.resume.terminal_receipt(retry.resume.RECEIPT)
    assert digest(request) == retry.resume.TARGET and digest(schema) == retry.resume.SCHEMA


@pytest.mark.parametrize('race', [False, True])
def test_handover_terminates_only_verified_sleeper_and_resumes_on_race(tmp_path, monkeypatch, race):
    work, base, service = (tmp_path / name for name in ('work', 'base', 'service'))
    for directory in (work, base, service):
        directory.mkdir()
    monkeypatch.setattr(retry, 'ROOT', tmp_path)
    monkeypatch.setattr(retry, 'WORK', work)
    monkeypatch.setattr(retry, 'BASE', base)
    monkeypatch.setattr(retry, 'AUTH', work / 'authority.json')
    monkeypatch.setattr(retry.resume, 'SERVICE', service)
    monkeypatch.setattr(retry, 'authority', lambda: {})
    save(retry.AUTH, {})
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        before = dict(worker=retry.process_identity(child.pid), ledger={'calls': [1]},
            recovery={'charges': [1]}, circuit={'open': True}, stage={'test': True})
        for path, value in ((base / 'live-calls.json', before['ledger']),
                (base / 'current-stage.json', before['stage']), (base / 'execution-state.json', {}),
                (service / 'service-recovery.json', before['recovery']),
                (service / 'service-circuit.json', before['circuit'])):
            save(path, value)
        before['state'] = retry.ref(tmp_path, base / 'execution-state.json')
        save(work / 'baseline.json', before)
        snapshots = []

        def snapshot():
            snapshots.append(True)
            return {'changed': True} if race and len(snapshots) == 2 else before

        monkeypatch.setattr(retry, 'snapshot', snapshot)
        if race:
            with pytest.raises(Exception):
                retry.handover()
            assert retry.process_alive(before['worker'])
            assert not (work / 'handover.json').exists()
        else:
            retry.handover()
            child.wait(timeout=2)
            assert not retry.process_alive(before['worker'])
            assert json.loads((work / 'handover.json').read_text())['provider_calls_added'] == 0
    finally:
        if child.poll() is None:
            child.terminate()
        child.wait(timeout=2)
