"""Finite completion authority survives reloads; no provider or host-rule writes."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from scripts import legal_mission_completion as completion
from scripts import legal_mission_control as control


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def local_package(tmp_path, monkeypatch):
    base = tmp_path/'completion'
    document = tmp_path/'plan.md'
    document.write_text('Protected local plan')
    now = datetime.now(timezone.utc)
    record = {'live_calls':0, 'additional_attempts':1, 'reconciled_prior_attempts':1,
        'prior_registered_detours':14, 'started_utc':(now-timedelta(minutes=1)).isoformat(),
        'deadline_utc':(now+timedelta(minutes=1)).isoformat(),
        'protected_evidence':[{'path':'plan.md','sha256':hashlib.sha256(document.read_bytes()).hexdigest()}]}
    write(base/'authorization.json', record)
    write(base/'state.json', {'assessment':{'status':'WAITING'}})
    write(tmp_path/'docs/implementation/legal-mission-control/mission.json', {'history':[]})
    monkeypatch.setattr(completion,'BASE',base)
    monkeypatch.setattr(completion,'ROOT',tmp_path)
    return tmp_path, base, record


@pytest.mark.parametrize('where', ['state', 'history'])
def test_settlement_cannot_be_restarted_by_reload(local_package, where):
    root, base, _ = local_package
    completion.check(active=True)
    if where == 'state':
        write(base/'state.json', {'assessment':{'status':'PASS'}})
    else:
        write(root/'docs/implementation/legal-mission-control/mission.json',
              {'history':[{'id':'integration-completion-assessment-2026-10-12'}]})
    with pytest.raises(AssertionError, match='settled'):
        completion.check(active=True)
    completion.check()  # Read-only status remains available.


def test_settlement_reports_no_remaining_attempt(local_package):
    root, _, record = local_package
    local = {'authorization':{'path':'completion/authorization.json'}, 'plan':{}}
    mission = {'history':[]}
    assert control.completion_status(local,mission,root)['repair_attempts_available'] == 1
    mission['history'].append({'id':'integration-completion-assessment-2026-10-12'})
    status = control.completion_status(local,mission,root)
    assert status['settled'] and status['repair_attempts_reserved'] == 1
    assert not status['execution_allowed'] and status['repair_attempts_available'] == 0


def test_controller_checks_nested_protected_completion_evidence(monkeypatch):
    mission = control.read(control.ROOT/control.BASE/'mission.json')
    tools = control.read(control.ROOT/control.BASE/'tools.json')
    original = control.read
    auth_path = control.ROOT/mission['local_completion_revision']['authorization']['path']
    def altered(path):
        value = original(path)
        if path == auth_path:
            value = deepcopy(value)
            value['protected_evidence'][-1]['sha256'] = '0'*64
        return value
    monkeypatch.setattr(control,'read',altered)
    with pytest.raises(control.Refused, match='Changed evidence:'):
        control.validate(mission,tools)
