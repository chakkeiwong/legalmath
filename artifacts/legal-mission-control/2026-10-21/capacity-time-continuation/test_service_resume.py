from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import importlib.util
import json
import shutil
import pytest

spec = importlib.util.spec_from_file_location('capacity_service_resume',Path(__file__).with_name('service_resume.py'))
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)


def events(message='request timed out'):
    return [{'type':'error','message':message},{'type':'turn.failed','error':{'message':message}}]


def test_recognizes_ended_cli_timeout():
    assert resume.classify(events(),output_present=False)['message'] == 'request timed out'


@pytest.mark.parametrize('change',['output','completed','message','no_failure','no_error','quota','auth','safety','unknown'])
def test_refuses_ambiguous_or_nonservice_timeout(change):
    value = events()
    if change == 'completed': value.append({'type':'turn.completed'})
    elif change == 'message': value.append({'type':'item.completed','item':{'type':'agent_message','text':'partial'}})
    elif change == 'no_failure': value.pop()
    elif change == 'no_error': value.pop(0)
    elif change in ('quota','auth','safety','unknown'):
        message = {'quota':'insufficient_quota','auth':'authentication failed','safety':'blocked by our safety systems',
            'unknown':'unclassified timeout detail'}[change]
        value.append({'type':'error','message':message})
    assert resume.classify(value,output_present=change == 'output') is None


def test_original_gateway_classification_is_unchanged():
    value = events('unexpected status 503 Service Unavailable')
    assert resume.classify(value,output_present=False) == resume.ORIGINAL_CLASSIFY(value,output_present=False)


def test_authentic_receipt_and_tampered_bytes(tmp_path):
    from scripts.legal_mission_execution import Refused
    shutil.copytree(resume.RECEIPT,tmp_path/'receipt')
    request,schema = resume.terminal_receipt(tmp_path/'receipt')
    assert resume.digest(request) == resume.TARGET and resume.digest(schema) == resume.SCHEMA
    (tmp_path/'receipt/events.jsonl').write_text('{}')
    with pytest.raises(Refused): resume.terminal_receipt(tmp_path/'receipt')


def test_ended_timeout_settles_counts_waits_and_probes_once(tmp_path,monkeypatch):
    from legalmath.errors import LegalMathError
    from legalmath.interpretation.assurance import bounded_provider as module
    from tests.assurance.test_delayed_service_recovery import setup,failure,REQUEST,SCHEMA
    from legalmath.interpretation.search.providers import CodexProvider,Completion
    from legalmath.interpretation.search.models import Settings
    allowance,clock = setup(tmp_path,monkeypatch)
    # An existing gateway failure remains charged before this timeout recovery.
    first = failure(tmp_path,1)
    allowance.service_circuit(failure=first)
    allowance.reserve_service_recovery(first)
    allowance.wait_service_recovery(first)
    allowance.service_circuit(reserving=True)
    previous = json.loads((tmp_path/'stage/service-recovery.json').read_text())
    ended = failure(tmp_path,2,message='request timed out')
    monkeypatch.setattr(resume.providers,'transient_service_details',resume.classify)
    allowance.service_circuit(failure=ended)
    assert allowance.reserve_service_recovery(ended) == 7200
    before_wait = clock.now
    allowance.wait_service_recovery(ended)
    assert clock.now-before_wait == timedelta(hours=2)
    allowance.service_circuit(reserving=True)
    with pytest.raises(LegalMathError): allowance.service_circuit(reserving=True)
    allowance.service_circuit(success=True)
    after = json.loads((tmp_path/'stage/service-recovery.json').read_text())
    assert after['maximum'] == previous['maximum'] == 24
    assert after['charges'][:1] == previous['charges'] and len(after['charges']) == 2
    circuit = json.loads((tmp_path/'stage/service-circuit.json').read_text())
    assert circuit['failed_slots'] == [1,2] and not circuit['open'] and not circuit.get('half_open_reserved')
    with pytest.raises(LegalMathError): allowance.reserve_service_recovery(ended)
