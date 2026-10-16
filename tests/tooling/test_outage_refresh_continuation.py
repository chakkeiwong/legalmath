from contextlib import contextmanager
from types import SimpleNamespace
import subprocess
import pytest
from scripts import legal_integration_phased_live as live
from scripts.legal_mission_execution import Refused


class Deferred:
    def __init__(self, error):
        self.error, self.events, self.blocked, self.state = error, [], [], {}
    def summary(self): return {'ready': ['acquire-p10', 'acquire-evidence']}
    def block_before_dispatch(self, tid, *args, **kwargs): self.blocked.append(tid)
    def sync_mission(self): raise self.error
    @contextmanager
    def locked(self): yield self.state
    def event(self, state, tid, action, **kwargs): self.events.append((tid, action))


def install(monkeypatch, tmp_path):
    scope = {'path': 'service/scope.json', 'sha256': 'scope'}
    (tmp_path / 'service').mkdir()
    (tmp_path / 'service/service-circuit.json').write_text('{}')
    monkeypatch.setattr(live, 'ROOT', tmp_path)
    monkeypatch.setattr(live, 'read', lambda p: {'phase_service_scope': scope}
        if p.name == 'current-binding.json' else {'open': True, 'stage_hash': 'scope'})
    monkeypatch.setattr(live, 'save', lambda *a: None)
    monkeypatch.setattr(live, 'ref', lambda *a: scope)
    from legalmath.interpretation.assurance import integration_contract
    monkeypatch.setattr(integration_contract, 'read_evidence', lambda *a: {})


def test_timeout_preserves_both_deferrals_without_attempts(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path)
    execution = Deferred(subprocess.TimeoutExpired(['refresh'], 300))
    assert live.defer_open_service(execution, 'acquire-p10')
    assert live.defer_open_service(execution, 'acquire-evidence')
    assert execution.blocked == ['acquire-p10', 'acquire-evidence']
    assert execution.events == [('acquire-p10', 'MISSION_SYNC_FAILED'), ('acquire-evidence', 'MISSION_SYNC_FAILED')]
    assert 'timed out' in execution.state['mission_sync_error']


def test_integrity_refusal_still_propagates(monkeypatch, tmp_path):
    install(monkeypatch, tmp_path)
    execution = Deferred(Refused('Changed evidence'))
    with pytest.raises(Refused, match='Changed evidence'):
        live.defer_open_service(execution, 'acquire-p10')
    assert execution.blocked == ['acquire-p10']
    assert not execution.events
