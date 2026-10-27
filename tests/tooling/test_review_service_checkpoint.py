"""Provider pause preserves the same owner attempt and independent ready work."""
from pathlib import Path
import os
import pytest
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.service_prerequisite import ServiceDeferred
from scripts import legal_integration_campaign as campaign
from scripts.legal_review_repair_service import restore_deferred
from scripts.legal_mission_execution import read, save, ref, Refused, process_identity
from scripts.legal_review_timeout_correction import verify_orphans
from tests.tooling.test_legal_mission_execution import setup, task


def test_paused_owner_resumes_same_attempt_and_does_not_block_independent_task(tmp_path, monkeypatch):
    execution = setup(tmp_path, [task('a', maximum_attempts=1), task('b'), task('child', requires=['a']),
        task('after', after=['a'])])
    monkeypatch.setattr(campaign, 'ROOT', tmp_path)
    monkeypatch.setattr(campaign, 'BASE', Path('live'))
    calls = []
    def unavailable():
        calls.append('pause')
        raise ServiceDeferred('Shared service circuit open')
    result = campaign.complete_node(execution, 'a', unavailable)
    assert result['service_deferred']
    state = read(execution.state_path)
    assert state['tasks']['a']['status'] == 'RUNNING'
    assert len(state['tasks']['a']['attempts']) == 1
    assert 'result' not in state['tasks']['a']['attempts'][0]
    view = execution.summary()
    assert view['ready'] == ['b'] and not view['running']
    assert view['tasks']['child']['status'] == view['tasks']['after']['status'] == 'WAITING'
    assert 'a' in view['blocked']
    with pytest.raises(Refused):
        campaign.complete_node(execution, 'a', unavailable)
    assert calls == ['pause']
    campaign.complete_node(execution, 'b', lambda: dict(independent=True))
    assert execution.summary()['execution'] == 'BLOCKED'
    # The owner cooperatively paused, so this same supervisor can perform the
    # existing authenticated recovery under the ordinary service locks.
    verify_orphans(tmp_path, read(execution.state_path), tmp_path/'runtime')
    value = {'service': 'response'}
    save(tmp_path/'response.json', dict(value=value,
        provenance=dict(response_hash=digest(value)), legal_acceptance=False, substituted_into_product=False))
    assert restore_deferred(execution, ref(tmp_path, 'response.json')) == ['a']
    assert restore_deferred(execution, ref(tmp_path, 'response.json')) == []
    assert execution.summary()['running'] == ['a']
    campaign.complete_node(execution, 'a', lambda: dict(completed=True))
    state = read(execution.state_path)
    assert state['tasks']['a']['status'] == 'SUCCEEDED' and len(state['tasks']['a']['attempts']) == 1
    assert not state['tasks']['a'].get('service_checkpoint')
    assert execution.summary()['ready'] == ['after', 'child']


def test_unknown_active_supervisor_and_uncertain_dispatch_are_not_paused(tmp_path, monkeypatch):
    execution = setup(tmp_path, [task('a')])
    monkeypatch.setattr(campaign, 'ROOT', tmp_path)
    monkeypatch.setattr(campaign, 'BASE', Path('live'))
    execution.start('a')
    with execution.locked() as state:
        state['tasks']['a'].update(master_live=True, live_supervisor=process_identity(os.getpid()))
    with pytest.raises(Refused):
        verify_orphans(tmp_path, read(execution.state_path), tmp_path/'runtime')
    with pytest.raises(Refused):
        campaign.complete_node(execution, 'a', lambda: pytest.fail('Duplicate owner'))


def test_answer_drain_yields_after_service_checkpoint(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import legal_integration_phased_live as live
    monkeypatch.setattr(live, 'defer_open_service', lambda *args: False)
    execution = SimpleNamespace(summary=lambda: dict(ready=['baseline-p14'], running=[]))
    seen = []
    def complete(*args):
        seen.append(args[1])
        return {'service_deferred': True}
    live.drain_answers(execution, SimpleNamespace(complete_node=complete), object())
    assert seen == ['baseline-p14']
