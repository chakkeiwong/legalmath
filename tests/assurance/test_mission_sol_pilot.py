"""Boundary checks for Sol continuation; no network or live model calls."""
import pytest

from tests.assurance.test_mission_live_pilot import grant  # Shared synthetic authorization fixture.
from scripts import legal_mission_live_pilot as pilot
from scripts import legal_mission_sol_pilot as sol
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Settings


def test_equal_remaining_effort_preserves_eight_spent_calls(grant):
    root, out, _ = grant
    old = pilot.PilotAllowance('baseline', root=root, directory=out)
    for _ in range(8):
        old.reserve('a' * 64)
    prefix = pilot.read(old.path)['calls'][:]
    for arm in pilot.ARMS:
        allowance = sol.SolAllowance(arm, root=root, directory=out)
        for _ in range(28):
            allowance.reserve('b' * 64)
        with pytest.raises(LegalMathError) as caught:
            allowance.reserve('c' * 64)
        assert caught.value.code == 'E_RESOURCE_LIMIT'
        allowance.stage = 'synthesis'
        allowance.reserve('d' * 64)
        with pytest.raises(LegalMathError):
            allowance.reserve('e' * 64)
    assert pilot.read(old.path)['calls'][:8] == prefix


def test_explicit_model_keeps_configured_service_and_forbids_drift(grant, monkeypatch):
    root, out, _ = grant
    allowance = sol.SolAllowance('baseline', root=root, directory=out)
    provider = sol.SolProvider(allowance=allowance, protocol_directory=out)
    configured = sol.CodexProvider().routing
    assert provider.routing == {**configured, 'model': 'gpt-6.1-sol'}
    command = provider.command(out, out / 'schema.json', out / 'output.json')
    assert command[command.index('--model') + 1] == 'gpt-6.1-sol'
    assert '--ignore-user-config' in command and '--ephemeral' in command
    monkeypatch.setattr(sol, 'check_frozen', lambda *_: {'route': provider.expected_route})
    provider.routing['model'] = 'gpt-6-astra'
    with pytest.raises(LegalMathError) as caught:
        provider.complete({'task': 'GENERATE'}, {}, Settings())
    assert caught.value.code == 'E_STALE_REVIEW' and allowance.verify()['used'] == 0


def test_deadline_clipping_and_stop_after_one_failed_transport(grant, monkeypatch):
    root, out, _ = grant
    allowance = sol.SolAllowance('baseline', root=root, directory=out)
    provider = sol.SolProvider(allowance=allowance, protocol_directory=out)
    monkeypatch.setattr(sol, 'check_frozen', lambda *_: {'route': provider.expected_route})
    monkeypatch.setattr(allowance, 'remaining_seconds', lambda: 7)
    limits = []
    def fail(self, request, schema, settings):
        limits.append(settings.timeout_seconds)
        self.allowance.reserve(digest(request))
        raise LegalMathError('E_DEPENDENCY', details='Test stream failure')
    monkeypatch.setattr(sol.CodexProvider, 'complete', fail)
    for _ in range(2):
        with pytest.raises(LegalMathError):
            provider.complete({'task': 'GENERATE'}, {}, Settings(timeout_seconds=300))
    assert limits == [7] and allowance.verify()['used'] == 1


def test_terminal_or_uncertain_execution_is_not_repeated(tmp_path, monkeypatch):
    monkeypatch.setattr(sol, 'OUT', tmp_path)
    pilot.save(tmp_path / 'result.json', {'status': 'PAIR_UNAVAILABLE', 'used_calls': 9})
    assert sol.execute()['used_calls'] == 9
    (tmp_path / 'result.json').unlink()
    pilot.save(tmp_path / 'execution-started.json', {'epoch_seconds': 1})
    with pytest.raises(LegalMathError) as caught:
        sol.execute()
    assert caught.value.code == 'E_JOB_STATE'
