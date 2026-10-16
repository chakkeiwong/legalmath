"""Actual overload receipts, bounded outage stops and exact corrected reuse."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from legalmath.errors import LegalMathError
from legalmath.canonical import digest
from legalmath.interpretation.search.providers import transient_service_details, terminal_service_error, TerminalServiceFailure, CodexProvider, Completion
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY, BoundedCodexProvider, recovery_delay
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from tests.assurance.test_execution_recovery import recovery_allowance, receipt
from tests.assurance.test_initial_checkpoint import initial
from tests.assurance.test_bounded_product import Scripted, envelope, limits


def events(message):
    return [{'type':'error','message':message},{'type':'turn.failed','error':{'message':message}}]


@pytest.mark.parametrize('message,wait',[
    ('rate limit exceeded: The upstream service is temporarily overloaded. Please try again in 30s.',30),
    ('unexpected status 503 Service Unavailable; Retry-After: 60',60),
    ('rate limit reached; try again in 1.5 minutes',90),
    ('rate limit exceeded; try again in 2 hours',7200),
    ('429 Too Many Requests',None),
    ('unexpected status 503 Service Unavailable',None),
    ('stream disconnected before completion',None)])
def test_classifies_only_explicit_service_errors(message,wait):
    assert transient_service_details(events(message),output_present=False)['retry_after_seconds']==wait
    assert terminal_service_error(events(message),output_present=False)==message
    assert transient_service_details(events(message),output_present=True) is None
    assert transient_service_details(events(message)+[{'type':'turn.completed'}],output_present=False) is None


@pytest.mark.parametrize('message',[
    '429 insufficient_quota: quota exceeded, try again in 30s',
    '429 Too Many Requests: billing limit',
    '503 Service Unavailable: authentication invalid',
    'quota exceeded', 'malformed output', '401 unauthorized'])
def test_does_not_retry_quota_auth_or_invalid_output(message):
    assert transient_service_details(events(message),output_present=False) is None


def test_requested_wait_is_never_shortened(monkeypatch):
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.random.uniform',lambda a,b:2)
    policy=SERVICE_CONTINUATION_POLICY
    assert recovery_delay(policy,0,{'retry_after_seconds':60})==62
    assert recovery_delay(policy,2,{})==122
    for detail in ({'retry_after_seconds':121},{'unparsed_retry_after':True}):
        with pytest.raises(LegalMathError):recovery_delay(policy,0,detail)
    for message in ('rate limit exceeded; try again in 2 hours',
                    '503 Service Unavailable; Retry-After: Wed, 14 Oct 2026 11:00:00 GMT',
                    'rate limit exceeded; try again in 2 days'):
        details=transient_service_details(events(message),output_present=False)
        with pytest.raises(LegalMathError):recovery_delay(policy,0,details)
    details=transient_service_details(events('503 Service Unavailable')+
        events('rate limit exceeded; try again in 90s'),output_present=False)
    assert recovery_delay(policy,0,details)==92


def circuit_allowance(tmp_path):
    allowance=recovery_allowance(tmp_path)
    save(tmp_path/'stage/stage.json',{'name':'test-stage',
        'service_recovery_policy':SERVICE_CONTINUATION_POLICY,'service_recovery_maximum':48})
    save(tmp_path/'current-stage.json',evidence_file(tmp_path/'stage/stage.json',tmp_path))
    save(tmp_path/'current-binding.json',{'service_recovery_policy':SERVICE_CONTINUATION_POLICY})
    return allowance


def test_circuit_persists_across_forks_and_success_does_not_reopen(tmp_path):
    allowance=circuit_allowance(tmp_path)
    for slot in range(1,8):allowance.service_circuit(failure=receipt(tmp_path,slot))
    with pytest.raises(LegalMathError):allowance.service_circuit(failure=receipt(tmp_path,8))
    allowance.service_circuit(success=True)  # Retain in-flight output; do not reopen.
    with pytest.raises(LegalMathError):allowance.service_circuit()
    other=type(allowance)(tmp_path,{},root=tmp_path)
    with pytest.raises(LegalMathError):other.service_circuit()
    value=json.loads((tmp_path/'stage/service-circuit.json').read_text())
    assert value['open'] and len(value['failed_slots'])==8


def test_success_resets_streak_but_duplicate_failure_does_not_double_count(tmp_path):
    allowance=circuit_allowance(tmp_path);failure=receipt(tmp_path,1)
    allowance.service_circuit(failure=failure);allowance.service_circuit(failure=failure)
    assert json.loads((tmp_path/'stage/service-circuit.json').read_text())['consecutive_failures']==1
    allowance.service_circuit(success=True)
    assert json.loads((tmp_path/'stage/service-circuit.json').read_text())['consecutive_failures']==0


def test_open_circuit_prevents_wire_dispatch(tmp_path,monkeypatch):
    allowance=circuit_allowance(tmp_path)
    for slot in range(1,9):
        try:allowance.service_circuit(failure=receipt(tmp_path,slot))
        except LegalMathError:pass
    provider=object.__new__(BoundedCodexProvider);provider.allowance=allowance
    provider.check=lambda:None;provider.measure=lambda *args:{}
    monkeypatch.setattr(CodexProvider,'complete',lambda *args:pytest.fail('Wire called while circuit open'))
    with pytest.raises(LegalMathError):provider.complete({'test':1},{},Settings(timeout_seconds=300))


def full_checkpoint(tmp_path):
    original,initial_result,records,path,manifest=initial(tmp_path)
    result=original.note('correction-p14','CORRECT_REVIEWED_ANSWER','Question',records,None,[])
    review=original.note('corrected-audit-source-p14-0','AUDIT_ANSWER_AGAINST_SOURCE','Question',
        records,result['value'],[r['id'] for r in records],audit=True)
    directory=original.directory/'calls'
    state=json.loads((directory/'dispatch.json').read_text())
    manifest.update(profile='bounded-full-checkpoint.v3',dispatch=evidence_file(directory/'dispatch.json',tmp_path),
        calls={k:{field:evidence_file(directory/k/(field+'.json'),tmp_path) for field in ('request','schema','result')} for k in state['calls']},
        recoverable_failures={},held_failures=[])
    save(path,manifest)
    return records,path,manifest,result,review


def test_completed_correction_and_reviews_reuse_without_resampling(tmp_path):
    records,path,manifest,result,review=full_checkpoint(tmp_path)
    provider=Scripted();product=BoundedProduct(tmp_path,tmp_path/'new',provider,envelope(),list,limits=limits(),retained_initial=evidence_file(path,tmp_path))
    assert product.note('correction-p14','CORRECT_REVIEWED_ANSWER','Question',records,None,[])==result
    assert product.note('corrected-audit-source-p14-0','AUDIT_ANSWER_AGAINST_SOURCE','Question',records,
        result['value'],[r['id'] for r in records],audit=True)==review
    assert provider.requests==[]


def test_adverse_corrected_review_is_retained(tmp_path):
    records,path,manifest,result,review=full_checkpoint(tmp_path)
    key='corrected-audit-source-p14-0'
    review['value'].update(verdict='REJECT',issues=['Supported adverse fixture'],reason='Adverse content retained')
    rpath=tmp_path/manifest['calls'][key]['result']['path'];save(rpath,review)
    manifest['calls'][key]['result']=evidence_file(rpath,tmp_path)
    dpath=tmp_path/manifest['dispatch']['path'];state=json.loads(dpath.read_text())
    state['calls'][key]['result_hash']=digest(review);save(dpath,state)
    manifest['dispatch']=evidence_file(dpath,tmp_path);save(path,manifest)
    provider=Scripted();product=BoundedProduct(tmp_path,tmp_path/'new',provider,envelope(),list,limits=limits(),retained_initial=evidence_file(path,tmp_path))
    actual=product.note(key,'AUDIT_ANSWER_AGAINST_SOURCE','Question',records,result['value'],[r['id'] for r in records],audit=True)
    assert actual['value']['verdict']=='REJECT' and not provider.requests


def test_full_checkpoint_refuses_silently_omitted_correction(tmp_path):
    records,path,manifest,result,review=full_checkpoint(tmp_path)
    del manifest['calls']['correction-p14'];save(path,manifest)
    provider=Scripted();product=BoundedProduct(tmp_path,tmp_path/'new',provider,envelope(),list,limits=limits(),retained_initial=evidence_file(path,tmp_path))
    with pytest.raises(LegalMathError):product.note('correction-p14','CORRECT_REVIEWED_ANSWER','Question',records,None,[])
    assert not provider.requests


@pytest.mark.parametrize('fault',['hash','completed','corrupt','quota'])
def test_recovery_receipts_must_match_wire_request_and_terminal_events(tmp_path,fault):
    from legalmath.interpretation.assurance.bounded_checkpoint import verify_no_output_receipts
    from legalmath.interpretation.assurance.bounded_references import prepare
    import hashlib
    original,_,records,_,_=initial(tmp_path)
    request=original.request('ANSWER_ORIGINAL_QUESTION','Question',records,payload=None,expected=[])
    from legalmath.interpretation.assurance.bounded_product import NOTE
    wire=prepare(request,NOTE)['request'];rh=digest(wire)
    failure=receipt(tmp_path,99,request_hash=rh)
    directory=tmp_path/'provider-evidence'/f'0099-{rh[:16]}'
    path=directory/'manifest.json';manifest=json.loads(path.read_text())
    if fault=='hash':manifest['request_hash']='0'*64
    if fault in ('completed','quota'):
        value=events('429 insufficient_quota; billing limit') if fault=='quota' else [{'type':'turn.completed'}]
        data=''.join(json.dumps(row)+'\n' for row in value).encode()
        (directory/'events.jsonl').write_bytes(data)
        manifest['files']['events.jsonl']['retained_sha256']=hashlib.sha256(data).hexdigest()
    save(path,manifest)
    if fault=='corrupt':(directory/'events.jsonl').write_text('changed')
    with pytest.raises(LegalMathError):verify_no_output_receipts(tmp_path,{'receipts':[evidence_file(path,tmp_path)]},request,NOTE)
