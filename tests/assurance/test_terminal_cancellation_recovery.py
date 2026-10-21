"""Terminal cancellation is opt-in and shares the finite delayed ledger."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_provider as module
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search import providers
from legalmath.interpretation.search.models import Settings
from tests.assurance.test_delayed_service_recovery import setup, failure, REQUEST, SCHEMA
from tests.assurance.test_service_continuation import events

MESSAGE = 'unexpected status 499 <unknown status code>: Client Closed Request'


@pytest.mark.parametrize('extra', [
    [{'type': 'turn.completed'}],
    [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}}],
    [{'type': 'turn.failed', 'error': {'message': 'invalid_request: invalid parameter'}}],
    events('401 unauthorized'), events('insufficient_quota'),
    events('blocked by our safety systems'), events('I cannot assist with this request'),
])
def test_cancelled_partial_or_disallowed_outcomes_cannot_retry(extra):
    assert providers.transient_service_details(events(MESSAGE) + extra,
        output_present=False, allow_terminal_499=True) is None


def test_only_explicit_terminal_no_output_cancellation_is_eligible():
    classify = providers.transient_service_details
    assert classify(events(MESSAGE), output_present=False) is None
    assert classify(events(MESSAGE)[:1], output_present=False, allow_terminal_499=True) is None
    assert classify(events(MESSAGE), output_present=True, allow_terminal_499=True) is None
    assert classify(events('question 499; stream disconnected before completion'),
        output_present=False, allow_terminal_499=True) is not None
    assert classify(events(MESSAGE), output_present=False,
        allow_terminal_499=True)['retry_after_seconds'] is None


def opt_in(tmp_path):
    save(tmp_path / 'current-binding.json', {
        'service_recovery_policy': module.SERVICE_DELAYED_POLICY,
        'terminal_cancellation_recovery': module.TERMINAL_CANCELLATION_POLICY})


def test_499_uses_existing_spent_schedule_and_restart_without_reset(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    allowance.reserve_service_recovery(failure(tmp_path, 1))
    opt_in(tmp_path)
    ended = failure(tmp_path, 2, message=MESSAGE)
    allowance.service_circuit(failure=ended)
    assert allowance.reserve_service_recovery(ended) == 7200
    restarted = type(allowance)(tmp_path, {}, root=tmp_path)
    restarted.check = lambda: None
    restarted.expected, restarted.expected_schema = allowance.expected, allowance.expected_schema
    restarted.wait_service_recovery(ended)
    restarted.service_circuit(reserving=True)
    with pytest.raises(LegalMathError): restarted.service_circuit(reserving=True)
    ledger = json.loads((tmp_path / 'stage/service-recovery.json').read_text())
    assert len(ledger['charges']) == 2 and ledger['maximum'] == 24
    assert sum(clock.sleeps) == 7200
    with pytest.raises(LegalMathError): restarted.reserve_service_recovery(ended)


@pytest.mark.parametrize('change', ['policy', 'reserve'])
def test_cancellation_cannot_create_authority_or_replacements(tmp_path, monkeypatch, change):
    allowance, _ = setup(tmp_path, monkeypatch)
    opt_in(tmp_path)
    path = tmp_path / 'current-binding.json'
    binding = json.loads(path.read_text())
    if change == 'policy': binding['service_recovery_policy'] = module.SERVICE_CONTINUATION_POLICY
    else: binding['terminal_cancellation_recovery']['new_calls'] = 1
    save(path, binding)
    with pytest.raises(LegalMathError): allowance.terminal_cancellation_enabled()


def test_real_cli_path_promotes_terminal_499_into_bounded_exact_retry(tmp_path, monkeypatch):
    allowance, clock = setup(tmp_path, monkeypatch)
    opt_in(tmp_path)
    allowance.reserve = lambda request_hash: 1
    provider = object.__new__(module.BoundedCodexProvider)
    provider.allowance, provider.check = allowance, lambda: None
    provider.measure, provider.encode = lambda *args: {}, list
    provider.limits = SimpleNamespace(output_tokens=1000)
    provider.retry_terminal_499 = True
    schema = {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}
    allowance.expected_schema = digest(schema)
    sent = []

    # Keep the real CodexProvider.complete process/result classification path.
    # A fake ended CLI writes the actual event format; no service is contacted.
    provider.command = lambda directory, shape, output: ['offline-cli', str(directory)]
    class Process:
        returncode = 1
        def __init__(self, command, *, stdin, stdout, stderr, **kwargs):
            sent.append((deepcopy(json.loads(stdin.read())), clock.now))
            stdout.write(b'\n'.join(canonical(e) for e in events(MESSAGE)))
        def poll(self): return self.returncode
    monkeypatch.setattr(providers.subprocess, 'Popen', Process)
    # On the second exact request return a fixture after proving due admission.
    original = providers.CodexProvider.complete
    def complete(self, request, schema, settings):
        if not sent: return original(self, request, schema, settings)
        self.allowance.service_circuit(reserving=True)
        sent.append((deepcopy(request), clock.now))
        return providers.Completion({'ok': True}, {'provider': 'offline-fixture'})
    monkeypatch.setattr(providers.CodexProvider, 'complete', complete)
    result = provider.complete(REQUEST, schema, Settings(timeout_seconds=300))
    assert result.value == {'ok': True}
    assert sent[0][0] == sent[1][0] == REQUEST
    assert (sent[1][1] - sent[0][1]).total_seconds() == 3600
    assert len(json.loads((tmp_path / 'stage/service-recovery.json').read_text())['charges']) == 1
