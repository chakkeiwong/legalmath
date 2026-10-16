"""The reviewed inventory timeout remains inside unchanged core/global clocks."""
from copy import deepcopy

import pytest

from tests.assurance.test_mission_live_pilot import grant
from scripts import legal_mission_live_pilot as pilot
from scripts import legal_mission_sol_inventory_window as window
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import Completion
from legalmath.canonical import digest


@pytest.fixture
def provider(grant, monkeypatch):
    root, out, _ = grant
    allowance = window.WindowAllowance('baseline', root=root, directory=out)
    value = window.WindowProvider(allowance=allowance, protocol_directory=out)
    monkeypatch.setattr(window, 'check_frozen', lambda *_: {
        'route': value.expected_route, 'inventory_policy': window.POLICY})
    return value


@pytest.mark.parametrize('task,expected', [
    ('SOURCE_INVENTORY', 900), ('INVENTORY_CROSS_CHECK', 900),
    ('GENERATE', 300), ('SCOPED_SOURCE_FIDELITY', 300),
    ('SYNTHESIZE_WHOLE_DOSSIER_ANSWER', 300)])
def test_task_specific_window_and_original_task_output_repair(provider, monkeypatch, task, expected):
    seen = []
    def complete(self, request, schema, settings):
        seen.append(settings.timeout_seconds)
        slot = self.allowance.reserve(digest(request))
        return Completion({}, {'allowance_slot': slot, 'wall_milliseconds': 1})
    monkeypatch.setattr(window.CodexProvider, 'complete', complete)
    provider.complete({'task': 'REPAIR_OUTPUT', 'original_task': task}, {}, Settings(timeout_seconds=300))
    assert seen == [expected]
    record = pilot.read(provider.protocol_directory / 'effective-settings/0001.json')
    assert record['caller_settings']['timeout_seconds'] == 300
    assert record['effective_settings']['timeout_seconds'] == expected
    assert Settings().timeout_seconds == 180


def test_long_inventory_window_obeys_original_core_and_global_deadlines(provider, monkeypatch):
    seen = []
    def complete(self, request, schema, settings):
        seen.append(settings.timeout_seconds)
        slot = self.allowance.reserve(digest(request))
        return Completion({}, {'allowance_slot': slot, 'wall_milliseconds': 1})
    monkeypatch.setattr(window.CodexProvider, 'complete', complete)
    monkeypatch.setattr(window.time, 'monotonic', lambda: 1000)
    provider.core_deadline = 1011
    provider.complete({'task': 'SOURCE_INVENTORY'}, {}, Settings(timeout_seconds=300))
    provider.core_deadline = 2000
    monkeypatch.setattr(provider.allowance, 'remaining_seconds', lambda: 7)
    provider.complete({'task': 'SOURCE_INVENTORY'}, {}, Settings(timeout_seconds=300))
    provider.core_deadline = 1002
    with pytest.raises(LegalMathError):
        provider.complete({'task': 'SOURCE_INVENTORY'}, {}, Settings(timeout_seconds=300))
    assert seen == [11, 7] and provider.allowance.verify()['used'] == 2


def test_equal_twenty_seven_remaining_core_calls(grant):
    root, out, _ = grant
    original = pilot.PilotAllowance('baseline', root=root, directory=out)
    for _ in range(9):
        original.reserve('a' * 64)
    prefix = deepcopy(pilot.read(original.path)['calls'])
    for arm in pilot.ARMS:
        allowance = window.WindowAllowance(arm, root=root, directory=out)
        for _ in range(27):
            allowance.reserve('b' * 64)
        with pytest.raises(LegalMathError):
            allowance.reserve('c' * 64)
    assert pilot.read(original.path)['calls'][:9] == prefix


def test_timeout_is_retained_without_automatic_retry(provider, monkeypatch):
    def fail(self, request, schema, settings):
        self.allowance.reserve(digest(request))
        raise LegalMathError('E_RESOURCE_LIMIT', details='Codex call deadline')
    monkeypatch.setattr(window.CodexProvider, 'complete', fail)
    for _ in range(2):
        with pytest.raises(LegalMathError):
            provider.complete({'task': 'SOURCE_INVENTORY'}, {}, Settings(timeout_seconds=300))
    assert provider.allowance.verify()['used'] == 1


def test_seventh_detour_is_counted_and_cannot_repeat():
    from scripts import legal_mission_control as control
    mission = control.read(pilot.ROOT / control.BASE / 'mission.json')
    tools = control.read(pilot.ROOT / control.BASE / 'tools.json')
    mission['history'] = [r for r in mission['history']
        if r.get('bounded_method_revision', {}).get('id') != 'sol-inventory-window']
    row = {'id': 'test-inventory-window-bound', 'task_id': 'product-contribution',
        'kind': 'product_evaluation', 'outcome': 'no_advance',
        'decision': 'Synthetic counter check only.', 'next_task_reason': 'Test the retained seventh bound.',
        'next_task': 'product-contribution', 'result_evidence': [pilot.ref(window.PLAN)],
        'bounded_method_revision': {'id': 'sol-inventory-window', 'prior_detours': 6,
            'enabling_deadline_utc': '2026-10-10T11:30:00+00:00', 'additional_attempts': 1}}
    mission['history'].append(row)
    assert control.validate(mission, tools)['detours_since_advance'] == 7
    again = deepcopy(row); again['id'] += '-again'
    mission['history'].append(again)
    with pytest.raises(control.Refused, match='repeated inventory-window'):
        control.validate(mission, tools)


def test_terminal_or_uncertain_execution_refuses_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(window, 'OUT', tmp_path)
    pilot.save(tmp_path / 'result.json', {'status': 'PAIR_UNAVAILABLE', 'used_calls': 10})
    assert window.execute()['used_calls'] == 10
    (tmp_path / 'result.json').unlink()
    pilot.save(tmp_path / 'execution-started.json', {'epoch_seconds': 1})
    with pytest.raises(LegalMathError) as caught:
        window.execute()
    assert caught.value.code == 'E_JOB_STATE'
