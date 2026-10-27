from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import SERVICE_REPAIRED_RETRY_POLICY as POLICY
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import retry_checkpoint as retry
from tests.assurance.test_review_deployment_service import successor
from tests.assurance import test_delayed_service_recovery as delayed

def migrated(tmp_path,monkeypatch):
    allowance,_,path=successor(tmp_path,monkeypatch)
    prior=json.loads(path.read_text())
    prior['charges'] += [dict(failed_slot=n,request_hash='earlier-'+str(n)) for n in range(89,289)]
    save(tmp_path/'v7.json',prior)
    save(tmp_path/'retry-authority.json',dict(additional_service_recoveries=500,cumulative_service_recoveries=788,
        global_calls_added=0,deadline_extended=False,user_instruction='500 more retries'))
    stage=dict(name='retry-successor',service_recovery_policy=POLICY,service_recovery_maximum=788)
    save(tmp_path/'stage/stage.json',stage);pointer=evidence_file(tmp_path/'stage/stage.json',tmp_path)
    save(tmp_path/'current-stage.json',pointer)
    binding=json.loads((tmp_path/'current-binding.json').read_text())
    binding.update(service_recovery_policy=POLICY,
        repaired_retry_service_predecessor=evidence_file(tmp_path/'v7.json',tmp_path),
        repaired_retry_authority=evidence_file(tmp_path/'retry-authority.json',tmp_path))
    save(tmp_path/'current-binding.json',binding)
    save(path,{**prior,'profile':POLICY['profile'],'maximum':788,'stage_hash':pointer['sha256']})
    return allowance,prior,path

def test_extra_500_keep_history_and_per_request_exhaustion(tmp_path,monkeypatch):
    allowance,prior,path=migrated(tmp_path,monkeypatch)
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path,289))
    assert caught.value.code=='E_RESOURCE_LIMIT'
    monkeypatch.setattr(delayed,'REQUEST',{'question':'new reviewed exact request'})
    allowance.expected=digest(delayed.REQUEST)
    assert allowance.reserve_service_recovery(delayed.failure(tmp_path,289))==300
    value=json.loads(path.read_text())
    assert value['charges'][:288]==prior['charges'] and len(value['charges'])==289
    assert value['maximum']==788

def test_spent_charges_cannot_be_reset_or_mutated(tmp_path,monkeypatch):
    allowance,_,path=migrated(tmp_path,monkeypatch)
    current=json.loads(path.read_text());current['charges'][200]['failed_slot']=9999;save(path,current)
    with pytest.raises(LegalMathError) as caught:allowance.reserve_service_recovery(delayed.failure(tmp_path,289))
    assert 'Lost 288 predecessor' in caught.value.details

@pytest.mark.parametrize('field,value',[('global_calls_added',500),('deadline_extended',True),('additional_service_recoveries',501)])
def test_retry_grant_cannot_extend_unrelated_authority(tmp_path,monkeypatch,field,value):
    allowance,_,_=migrated(tmp_path,monkeypatch)
    auth=json.loads((tmp_path/'retry-authority.json').read_text());auth[field]=value
    save(tmp_path/'retry-authority.json',auth)
    binding=json.loads((tmp_path/'current-binding.json').read_text())
    binding['repaired_retry_authority']=evidence_file(tmp_path/'retry-authority.json',tmp_path)
    save(tmp_path/'current-binding.json',binding)
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(delayed.failure(tmp_path,289))

def test_exhaustion_and_model_output_remain_vetoes(tmp_path,monkeypatch):
    allowance,_,path=migrated(tmp_path,monkeypatch)
    with pytest.raises(LegalMathError):allowance.reserve_service_recovery(delayed.failure(tmp_path,289,completed=True))
    current=json.loads(path.read_text());current['charges'] += [dict(failed_slot=n,request_hash=str(n)) for n in range(289,789)]
    save(path,current)
    with pytest.raises(LegalMathError) as caught:allowance.reserve_service_recovery(delayed.failure(tmp_path,789))
    assert caught.value.details=='Stage replacement reserve exhausted'

def test_profile_only_reuse_rejects_changed_answer_and_schema_intent(monkeypatch):
    monkeypatch.setattr(retry.capacity_policy,'annotate',lambda x:deepcopy(x))
    old=dict(task='AUDIT_EXPLICIT_DEPENDENCY_CONTEXT',payload={'answer':'fixed'})
    new={**old,'context_reference_profile':'exact-context-answer-and-needs.v1'}
    checkpoint={'retry_profile':retry.PROFILE};row={'mode':'VALIDATED'}
    assert retry.equivalent(old,new,checkpoint,row)
    assert not retry.equivalent(old,{**new,'payload':{'answer':'different'}},checkpoint,row)
    assert not retry.equivalent(old,new,{},row)
    with pytest.raises(LegalMathError):retry.equivalent(old,{**new,'context_reference_profile':'unknown'},checkpoint,row)

def test_failed_retry_never_accepts_success_or_global_veto(tmp_path):
    (tmp_path/'review.md').write_text('Reviewed failed request')
    pointer={'path':'result.json','sha256':'x'}
    checkpoint=dict(retry_profile=retry.PROFILE,reviewed_failed_results=[pointer],
        retry_review=evidence_file(tmp_path/'review.md',tmp_path))
    row={'result':pointer};request={'task':'ASSESS_REVIEW_WARRANT'}
    retry.retryable(checkpoint,row,request,{'status':'FAILED'},tmp_path)
    for prior in ({'status':'VALIDATED'},{'status':'FAILED','continuation_veto':True}):
        with pytest.raises(LegalMathError):retry.retryable(checkpoint,row,request,prior,tmp_path)
    with pytest.raises(LegalMathError):retry.retryable(checkpoint,row,{'task':'ANSWER_ORIGINAL_QUESTION'},{'status':'FAILED'},tmp_path)

def test_fixed_correction_cannot_regenerate_and_retains_unresolved(monkeypatch,tmp_path):
    candidate={'status':'VALIDATED','value':{'conclusion':'fixed'}}
    held=dict(original_reviews=[{'status':'VALIDATED','value':{'verdict':'REJECT'}}],
        candidate=candidate,corrected_requirement_details=[])
    monkeypatch.setattr(retry,'fixed_correction',lambda *a:deepcopy(held))
    assessment={'result':{'status':'VALIDATED','value':{'decisions':[{'disposition':'UNRESOLVED'}]}}}
    product=SimpleNamespace(directory=tmp_path,
        note=lambda *a:pytest.fail('Successful answer was resampled'),
        review_warrants=lambda *a:([assessment],[],False),
        audit_answer=lambda *a,**k:[{'status':'VALIDATED','value':{'verdict':'ACCEPT'}}],
        audit_dependencies=lambda *a,**k:[])
    actual,reviews,record=retry.resume_correction(product,'p14',{},dict(value={}),[],[])
    assert actual==candidate and record['new_answer_calls']==0
    assert reviews[-1]['error']=='E_DEPENDENCY' and record['legal_acceptance'] is False

def test_actual_p14_fixed_correction_is_authenticated_and_cannot_change():
    from pathlib import Path
    from legalmath.interpretation.assurance.phased.evidence_store import load_exact
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.bounded_context import Limits
    root=Path('/home/chakwong/python/legalmath')
    work=root/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
    checkpoint=json.loads((work/'checkpoints/p14/baseline.json').read_text())
    fixed=json.loads((root/checkpoint['fixed_correction']['path']).read_text())
    report=load_exact(root/fixed['answers']['path'])['p14'];held=report['correction']
    row=checkpoint['calls']['correction-p14'];request=json.loads((root/row['request']['path']).read_text())
    from scripts.legal_integration_campaign import provider
    dispatch=BoundDispatch(provider(),work/'unused-dispatch',SimpleNamespace(limits=Limits()))
    dispatch.capacity_manager=True
    product=SimpleNamespace(root=root,capacity_checkpoint=evidence_file(work/'checkpoints/p14/baseline.json',root),
        route=SimpleNamespace(input_hash=checkpoint['input_hash'],records={r['id']:r for r in request['records']}),
        dispatch=dispatch,citations=lambda value,records:None)
    result=retry.fixed_correction(product,'p14',request['question'],held['original_answer']['value'],held['original_requirement_details'])
    assert result['candidate']==held['candidate']
    changed=deepcopy(held['original_answer']['value']);changed['conclusion']+=' changed'
    with pytest.raises(LegalMathError):retry.fixed_correction(product,'p14',request['question'],changed,held['original_requirement_details'])


def test_identical_diagnostic_relocation_keeps_request_but_changed_content_does_not(tmp_path,monkeypatch):
    monkeypatch.setattr(retry.capacity_policy,'annotate',lambda x:deepcopy(x))
    (tmp_path/'old.json').write_text('fixed diagnostic')
    (tmp_path/'new.json').write_text('fixed diagnostic')
    old=dict(task='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS',payload={'invalid_review_repair':
        {'full_diagnostic':evidence_file(tmp_path/'old.json',tmp_path),'reason':'fixed'}})
    current=deepcopy(old);current['payload']['invalid_review_repair']['full_diagnostic']=evidence_file(tmp_path/'new.json',tmp_path)
    checkpoint={'retry_profile':retry.PROFILE};row={'mode':'VALIDATED'}
    assert retry.equivalent(old,current,checkpoint,row,tmp_path)
    current['payload']['invalid_review_repair']['reason']='changed'
    assert not retry.equivalent(old,current,checkpoint,row,tmp_path)
    current['payload']['invalid_review_repair']['reason']='fixed'
    (tmp_path/'new.json').write_text('changed diagnostic')
    with pytest.raises(LegalMathError):retry.equivalent(old,current,checkpoint,row,tmp_path)


def test_exact_recovery_uses_same_capacity_as_product_dispatch():
    from pathlib import Path
    from scripts.legal_review_repair_service import probe_settings
    from legalmath.interpretation.assurance.bounded_context import Limits
    from legalmath.canonical import canonical
    root=Path('/home/chakwong/python/legalmath')
    request=json.loads((root/'artifacts/legal-mission-control/2026-10-13/master/provider-evidence/6471-c585d8d50bb60dc3/request.json').read_text())
    value=probe_settings(SimpleNamespace(limits=Limits()),request)
    assert 100000 < len(canonical(request)) < value.max_input_bytes==250000
    assert value.max_output_bytes==262144 and value.timeout_seconds==300
    request['downstream_capacity_profile']='unreviewed'
    with pytest.raises(LegalMathError):probe_settings(SimpleNamespace(limits=Limits()),request)

def test_started_probe_with_a_new_charge_must_not_repeat(tmp_path,monkeypatch):
    from scripts import legal_review_repair_service as service
    from scripts.legal_mission_execution import Refused,ref
    from pathlib import Path
    monkeypatch.setattr(service,'ROOT',tmp_path);monkeypatch.setattr(service,'BASE',Path('base'))
    folder=tmp_path/'probe';stage={'path':'stage.json','sha256':'s'}
    charge=dict(failed_slot=1,request_hash='r',schema_hash='s',stage=stage)
    save(tmp_path/'before.json',dict(calls=[]));save(tmp_path/'failure.json',{})
    save(folder/'scheduled.json',dict(charge=charge,original_failure=ref(tmp_path,'failure.json')))
    save(folder/'started.json',dict(stage=stage,ledger_before=ref(tmp_path,'before.json')))
    save(tmp_path/'base/current-stage.json',stage);save(tmp_path/'base/live-calls.json',dict(calls=[{}]))
    circuit=dict(open=False,half_open_reserved=False,half_open_request_hash='r',half_open_schema_hash='s')
    with pytest.raises(Refused,match='may have dispatched'):
        service.resume_undispatched_probe(SimpleNamespace(_complete=lambda *a:pytest.fail('Repeated transport')),folder,circuit,{})
