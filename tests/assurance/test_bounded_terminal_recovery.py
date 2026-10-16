"""Offline checks for the reviewed terminal-service recovery boundary."""
from pathlib import Path
import hashlib
import json
from types import SimpleNamespace

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider, CampaignAllowance
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import (
    CodexProvider, Completion, TerminalServiceFailure, terminal_service_error)
from scripts.legal_mission_execution import ref


def test_terminal_service_classifier_requires_ended_no_output():
    service = [{'type': 'error', 'message': 'unexpected status 502 Bad Gateway'}]
    assert terminal_service_error(service, output_present=False)
    assert terminal_service_error([{'type': 'error',
        'message': 'stream disconnected before completion'}], output_present=False)
    assert terminal_service_error(service, output_present=True) is None
    assert terminal_service_error([*service, {'type':'turn.completed'}], output_present=False) is None
    assert terminal_service_error([{'type':'error', 'message':'invalid schema'}], output_present=False) is None


def test_semantic_recovery_is_stage_bound_charged_and_requires_exact_terminal_receipt(tmp_path):
    stage = tmp_path/'stages/semantic-preflight/stage.json'
    save(stage, {'name':'semantic-preflight', 'terminal_recovery_maximum':2})
    save(tmp_path/'current-stage.json', ref(tmp_path, stage))
    allowance = CampaignAllowance(tmp_path, {}, root=tmp_path)
    def failed(slot, message='unexpected status 502 Bad Gateway'):
        request_hash = digest({'slot':slot})
        evidence = tmp_path/'provider-evidence'/f'{slot:04}-{request_hash[:16]}'
        evidence.mkdir(parents=True)
        events = json.dumps({'type':'error','message':message})+'\n'
        (evidence/'events.jsonl').write_text(events)
        save(evidence/'manifest.json', {'allowance_slot':slot, 'request_hash':request_hash,
            'complete_output_present':False,
            'files':{'events.jsonl':{'retained_sha256':hashlib.sha256(events.encode()).hexdigest()}}})
        return TerminalServiceFailure(message, allowance_slot=slot, request_hash=request_hash)
    first = failed(1)
    assert allowance.reserve_terminal_recovery(first)==1
    with pytest.raises(LegalMathError): allowance.reserve_terminal_recovery(first)
    second = failed(2, 'stream disconnected before completion')
    assert allowance.reserve_terminal_recovery(second)==2
    with pytest.raises(LegalMathError) as caught: allowance.reserve_terminal_recovery(failed(3))
    assert caught.value.code=='E_RESOURCE_LIMIT'
    assert len(json.loads((stage.parent/'terminal-recovery.json').read_text())['charges'])==2


def test_provider_retries_only_explicit_terminal_failure(monkeypatch):
    provider = object.__new__(BoundedCodexProvider)
    calls = []
    provider.check = lambda: None
    provider.measure = lambda request, schema: {'local_tokens':0}
    provider.allowance = SimpleNamespace(expected=None,
        terminal_recovery_enabled=lambda: True,
        reserve_terminal_recovery=lambda failure: calls.append(('recovery',failure.allowance_slot)))
    provider.encode = list
    provider.limits = SimpleNamespace(output_tokens=1000)
    def respond(self, request, schema, settings):
        calls.append(('call',settings.timeout_seconds))
        if len([v for v in calls if v[0]=='call'])==1:
            raise TerminalServiceFailure('unexpected status 502 Bad Gateway',
                allowance_slot=1, request_hash=digest(request))
        return Completion({'ok':True},{'provider':'fixture'})
    monkeypatch.setattr(CodexProvider,'complete',respond)
    assert provider.complete({'x':1},{},Settings()).value=={'ok':True}
    assert calls == [('call',120),('recovery',1),('call',120)]
    calls.clear()
    def invalid(self, request, schema, settings):
        calls.append(('call',settings.timeout_seconds))
        raise LegalMathError('E_SCHEMA',details='Invalid output')
    monkeypatch.setattr(CodexProvider,'complete',invalid)
    with pytest.raises(LegalMathError) as caught:
        provider.complete({'x':1},{},Settings())
    assert caught.value.code=='E_SCHEMA' and calls==[('call',120)]
