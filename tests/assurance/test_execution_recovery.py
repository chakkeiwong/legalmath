"""Regression checks for the actual fifth-attempt delivery/recovery failures."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import (
    BoundedCodexProvider, CampaignAllowance, SERVICE_RECOVERY_POLICY)
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.search.providers import (
    CodexProvider, Completion, TerminalServiceFailure, TerminatedCallTimeout)
from scripts.legal_mission_execution import ref
from tests.assurance.test_initial_checkpoint import initial
from tests.assurance.test_bounded_product import Scripted, envelope, limits
from tests.assurance.test_requirement_correction import setup_product


def recovery_allowance(tmp_path):
    stage=tmp_path/'stage/stage.json'
    save(stage,{'name':'baseline-p14','service_recovery_policy':SERVICE_RECOVERY_POLICY,
        'service_recovery_maximum':48})
    save(tmp_path/'current-stage.json',ref(tmp_path,stage))
    save(tmp_path/'current-binding.json',{'service_recovery_policy':SERVICE_RECOVERY_POLICY})
    return CampaignAllowance(tmp_path,{},root=tmp_path)


def receipt(tmp_path,slot,*,timeout=False,request_hash=None,completed=False,corrupt=False):
    rh=request_hash or digest({'slot':slot})
    directory=tmp_path/'provider-evidence'/f'{slot:04}-{rh[:16]}'
    directory.mkdir(parents=True)
    events=[{'type':'error','message':'unexpected status 503 Service Unavailable'}]
    if completed:events.append({'type':'turn.completed'})
    data=''.join(json.dumps(e)+'\n' for e in events).encode()
    (directory/'events.jsonl').write_bytes(data)
    files={'events.jsonl':{'retained_sha256':hashlib.sha256(data).hexdigest()}}
    if timeout:
        termination={'reason':'LOCAL_DEADLINE','process_terminated':True,'returncode':-9,
            'timeout_seconds':300,'complete_output_present':False,'completed_turn_present':completed}
        save(directory/'termination.json',termination)
        files['termination.json']={'retained_sha256':hashlib.sha256((directory/'termination.json').read_bytes()).hexdigest()}
    save(directory/'manifest.json',{'allowance_slot':slot,'request_hash':rh,
        'complete_output_present':False,'files':files})
    if corrupt:(directory/'events.jsonl').write_text('changed')
    cls=TerminatedCallTimeout if timeout else TerminalServiceFailure
    return cls('terminal no-output failure',allowance_slot=slot,request_hash=rh)


def test_replacement_backoff_and_limits_preserve_every_charge(tmp_path):
    allowance=recovery_allowance(tmp_path);rh=digest({'same':'request'})
    for slot,delay in enumerate((2,8,20),1):
        assert allowance.reserve_service_recovery(receipt(tmp_path,slot,request_hash=rh))==delay
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(receipt(tmp_path,4,request_hash=rh))
    for slot in range(5,50):allowance.reserve_service_recovery(receipt(tmp_path,slot))
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(receipt(tmp_path,50))
    ledger=json.loads((tmp_path/'stage/service-recovery.json').read_text())
    assert len(ledger['charges'])==48 and ledger['charges'][0]['failed_slot']==1


@pytest.mark.parametrize('timeout',[False,True])
def test_only_exact_no_output_receipts_authorize_recovery(tmp_path,timeout):
    allowance=recovery_allowance(tmp_path)
    failure=receipt(tmp_path,1,timeout=timeout)
    assert allowance.reserve_service_recovery(failure)==2
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(failure)
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(receipt(tmp_path,2,timeout=timeout,completed=True))
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(receipt(tmp_path,3,timeout=timeout,corrupt=True))
    if timeout:
        failure=receipt(tmp_path,4,timeout=True)
        directory=tmp_path/'provider-evidence'/f'0004-{failure.request_hash[:16]}'
        (directory/'termination.json').unlink()
        with pytest.raises(OSError):allowance.reserve_service_recovery(failure)


def test_provider_uses_bound_timeout_and_recovers_http_burst(monkeypatch):
    provider=object.__new__(BoundedCodexProvider);calls=[]
    provider.check=lambda:None;provider.measure=lambda *a:{};provider.encode=list
    provider.limits=SimpleNamespace(output_tokens=1000)
    provider.allowance=SimpleNamespace(expected=None,
        service_recovery_policy=lambda:SERVICE_RECOVERY_POLICY,
        reserve_service_recovery=lambda failure:(calls.append(('replacement',failure.allowance_slot)) or 2))
    def complete(self,request,schema,settings):
        calls.append(('call',settings.timeout_seconds))
        n=sum(k=='call' for k,v in calls)
        if n<=3:raise TerminalServiceFailure('unexpected status 503 Service Unavailable',allowance_slot=n,request_hash=digest(request))
        return Completion({'ok':True},{'provider':'fixture'})
    monkeypatch.setattr(CodexProvider,'complete',complete)
    monkeypatch.setattr('legalmath.interpretation.assurance.bounded_provider.time.sleep',lambda s:calls.append(('sleep',s)))
    result=provider.complete({'x':1},{},Settings(timeout_seconds=300))
    assert result.value=={'ok':True} and result.provenance['application_replacements']==3
    assert [v for k,v in calls if k=='call']==[300]*4
    assert len([k for k,v in calls if k=='replacement'])==3
    before=deepcopy(calls)
    with pytest.raises(LegalMathError):provider.complete({'x':1},{},Settings(timeout_seconds=120))
    assert calls==before


def test_real_process_timeout_is_classified_only_after_kill(tmp_path,monkeypatch):
    provider=object.__new__(CodexProvider)
    provider.allowance=SimpleNamespace(grant_path=tmp_path/'grant.json',path=tmp_path/'ledger.json',reserve=lambda request_hash:1)
    provider.command=lambda directory,*args:['fixture']
    times=iter((0,301));monkeypatch.setattr('legalmath.interpretation.search.providers.time.monotonic',lambda:next(times))
    proc=SimpleNamespace(pid=321,returncode=None)
    proc.poll=lambda:proc.returncode
    proc.wait=lambda **kw:setattr(proc,'returncode',-9)
    monkeypatch.setattr('legalmath.interpretation.search.providers.subprocess.Popen',lambda *a,**kw:proc)
    monkeypatch.setattr('legalmath.interpretation.search.providers.os.killpg',lambda *a:None)
    schema={'type':'object','properties':{'ok':{'type':'boolean'}},'required':['ok'],'additionalProperties':False}
    with pytest.raises(TerminatedCallTimeout):provider.complete({'x':1},schema,Settings(timeout_seconds=300))
    folder=next((tmp_path/'provider-evidence').iterdir())
    ended=json.loads((folder/'termination.json').read_text())
    assert ended['process_terminated'] and ended['returncode']==-9 and not ended['complete_output_present']
    assert 'termination.json' in json.loads((folder/'manifest.json').read_text())['files']


@pytest.mark.parametrize('changed',[False,True])
def test_partial_checkpoint_reuses_exact_and_dispatches_changed_requests(tmp_path,changed):
    _,result,records,path,manifest=initial(tmp_path)
    manifest['profile']='bounded-exact-checkpoint.v2';save(path,manifest)
    provider=Scripted()
    product=BoundedProduct(tmp_path,tmp_path/'new',provider,envelope(),list,limits=limits(),
        retained_initial=evidence_file(path,tmp_path))
    answer=product.note('answer-p14','ANSWER_ORIGINAL_QUESTION','Changed' if changed else 'Question',records,None,[])
    assert len(provider.requests)==int(changed)
    if not changed:assert answer==result
    product.note('answer-new','ANSWER_ORIGINAL_QUESTION','New question',records,None,[])
    assert len(provider.requests)==1+int(changed)


def test_missing_unrelated_review_does_not_block_supported_correction(tmp_path):
    _,product,answer,details,adverse=setup_product(tmp_path)
    missing={'status':'FAILED','error':'E_DEPENDENCY','reason':'HTTP 503'}
    candidate,fresh,retained=product.correct_answer('p14','When does duty apply?',answer,[missing,adverse],details,[])
    assert retained['status']=='REVIEWED' and retained['incomplete_original_reviews']==[0]
    assert retained['original_reviews'][0]==missing
    assert retained['requirement_corrections'][0]['result']['status']=='VALIDATED'
    assert fresh and all(r['status']=='VALIDATED' for r in fresh)


@pytest.mark.parametrize('status',['RESERVED','FAILED','VALIDATED'])
def test_partial_checkpoint_cannot_silently_omit_existing_identical_request(tmp_path,status):
    _,_,records,path,manifest=initial(tmp_path)
    dispatch_path=tmp_path/manifest['dispatch']['path'];dispatch=json.loads(dispatch_path.read_text())
    dispatch['calls']['answer-p14']['status']=status;save(dispatch_path,dispatch)
    manifest.update(profile='bounded-exact-checkpoint.v2',calls={},dispatch=evidence_file(dispatch_path,tmp_path))
    save(path,manifest)
    provider=Scripted()
    product=BoundedProduct(tmp_path,tmp_path/'new',provider,envelope(),list,limits=limits(),
        retained_initial=evidence_file(path,tmp_path))
    with pytest.raises(LegalMathError):product.note('answer-p14','ANSWER_ORIGINAL_QUESTION','Question',records,None,[])
    assert not provider.requests


def test_missing_corrected_review_still_blocks_acceptance(tmp_path,monkeypatch):
    _,product,answer,details,adverse=setup_product(tmp_path)
    monkeypatch.setattr(product,'audit_dependencies',lambda *a,**kw:[{'status':'FAILED','reason':'HTTP 503'}])
    _,fresh,retained=product.correct_answer('p14','Question',answer,[adverse],details,[])
    assert retained['status']=='REVIEWED'
    assert not all(r['status']=='VALIDATED' and r['value']['verdict']=='ACCEPT' for r in fresh)


def test_requirement_retrieval_delivers_operative_rule_and_incorporation(tmp_path):
    from scripts.legal_integration_reopening_live import fixture
    from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
    from scripts.legal_integration_master import ROOT,TOKENIZER
    source=fixture(explicit_scope=True,missing_authority=True)
    source['answer_acceptance']['acceptance_obligations']=[{'id':'synthetic-duty','question_ids':['p14'],
        'statement':'Resolve the requested applicable regime, preserving genuinely missing incorporated authority.'}]
    product=BoundedProduct(tmp_path,tmp_path/'p',Scripted(),source,tokenizer(ROOT/TOKENIZER),limits=Limits())
    delivered=[]
    def note(key,task,question,records,payload,expected):
        delivered.extend(records);return {'status':'MEASURED_ONLY'}
    product.note=note
    product.requirement_details()
    assert {'unit.0','unit.7'} <= {r['unit_id'] for r in delivered}
