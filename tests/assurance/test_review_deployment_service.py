from copy import deepcopy
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_provider import SERVICE_REVIEW_DEPLOYMENT_POLICY as POLICY
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from tests.assurance.test_review_repair_budget_service import migrated
from tests.assurance import test_delayed_service_recovery as delayed


def successor(tmp_path,monkeypatch):
    allowance,clock,prior=migrated(tmp_path,monkeypatch)
    path=tmp_path/'stage/service-recovery.json'
    previous=json.loads(path.read_text())
    previous['charges'] += [dict(failed_slot=n,request_hash='earlier-'+str(n)) for n in range(25,89)]
    save(tmp_path/'v6.json',previous)
    save(tmp_path/'authority.json',dict(additional_service_recoveries=200,cumulative_service_recoveries=288,
        global_calls_added=0,user_instruction='200 additional service recoveries'))
    stage={'name':'deployment','service_recovery_policy':POLICY,'service_recovery_maximum':288}
    save(tmp_path/'stage/stage.json',stage)
    pointer=evidence_file(tmp_path/'stage/stage.json',tmp_path)
    save(tmp_path/'current-stage.json',pointer)
    binding=json.loads((tmp_path/'current-binding.json').read_text())
    binding.update(service_recovery_policy=POLICY,
        review_deployment_service_predecessor=evidence_file(tmp_path/'v6.json',tmp_path),
        review_deployment_authority=evidence_file(tmp_path/'authority.json',tmp_path))
    save(tmp_path/'current-binding.json',binding)
    save(path,{**previous,'profile':POLICY['profile'],'maximum':288,'stage_hash':pointer['sha256']})
    return allowance,previous,path


def test_extra_200_preserve_all_88_charges_and_old_per_request_limit(tmp_path,monkeypatch):
    allowance,previous,path=successor(tmp_path,monkeypatch)
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path,89))
    assert caught.value.details=='Request replacements exhausted'
    monkeypatch.setattr(delayed,'REQUEST',{'question':'new exact failed request'})
    allowance.expected=digest(delayed.REQUEST)
    assert allowance.reserve_service_recovery(delayed.failure(tmp_path,89))==300
    current=json.loads(path.read_text())
    assert current['charges'][:88]==previous['charges'] and len(current['charges'])==89
    assert current['maximum']==288


def test_deployment_cannot_reset_history_or_exceed_cumulative_reserve(tmp_path,monkeypatch):
    allowance,previous,path=successor(tmp_path,monkeypatch)
    current=json.loads(path.read_text())
    changed=deepcopy(current)
    changed['charges'][70]['failed_slot']=999
    save(path,changed)
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path,89))
    assert 'Lost predecessor charges' in caught.value.details
    current['charges'] += [dict(failed_slot=n,request_hash=str(n)) for n in range(89,289)]
    save(path,current)
    with pytest.raises(LegalMathError) as caught:
        allowance.reserve_service_recovery(delayed.failure(tmp_path,289))
    assert caught.value.details=='Stage replacement reserve exhausted'


def test_new_policy_keeps_output_and_authentication_veto(tmp_path,monkeypatch):
    allowance,_,_=successor(tmp_path,monkeypatch)
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(delayed.failure(tmp_path,89,completed=True))
    with pytest.raises(LegalMathError):
        allowance.reserve_service_recovery(delayed.failure(tmp_path,90,message='401 unauthorized'))


def test_successor_recovery_preserves_old_admission_and_uses_current_binding(tmp_path,monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    from scripts import legal_review_repair_service as service, legal_integration_campaign as campaign
    from tests.assurance.test_phased_admission import setup
    base,live,_=setup(tmp_path)
    monkeypatch.setattr(service,'ROOT',tmp_path)
    monkeypatch.setattr(service,'BASE',Path(base))
    monkeypatch.setattr(service,'PROGRAM',Path('program.json'))
    monkeypatch.setattr(service,'STATE',Path('state.json'))
    monkeypatch.setattr(service,'WORK',Path('previous'))
    binding=json.loads((tmp_path/base/'current-binding.json').read_text())
    program=dict(review_repair=dict(review=binding['review'],service_policy=POLICY,
        deployment=dict(runtime='successor/live')))
    save(tmp_path/'program.json',program)
    binding.update(program=evidence_file(tmp_path/'program.json',tmp_path),
        execution_review=binding['review'],service_recovery_policy=POLICY)
    save(tmp_path/base/'current-binding.json',binding)
    save(tmp_path/'state.json',dict(tasks={}))
    save(tmp_path/live/'service/service-circuit.json',dict(open=True,failed_slots=[1],
        stage_hash=binding['phase_service_scope']['sha256']))
    ledger=json.loads((tmp_path/base/'live-calls.json').read_text())
    ledger['calls']=[dict(request_hash='request')]
    save(tmp_path/base/'live-calls.json',ledger)
    old=tmp_path/'previous/service-live/phases/service-requalification/exact-ended-1/stage.json'
    save(old,dict(binding_hash='old-binding',status='retained-unstarted'))
    previous=old.read_bytes()
    monkeypatch.setattr(service,'terminal_receipt',lambda *a,**k: ({},{},object(),tmp_path/'receipt.json'))
    monkeypatch.setattr(campaign,'provider',lambda:SimpleNamespace(check=lambda:None))
    original=service.admit
    class BeforeReserve(BaseException): pass
    def admitted(*a,**k):
        pointer=original(*a,**k)
        assert pointer['path'].startswith('successor/service-live/')
        stage=json.loads((tmp_path/pointer['path']).read_text())
        assert stage['binding_hash']==digest(binding) and stage['logical_calls']==1
        raise BeforeReserve()
    monkeypatch.setattr(service,'admit',admitted)
    with pytest.raises(BeforeReserve): service.recover()
    assert old.read_bytes()==previous
    assert json.loads((tmp_path/base/'live-calls.json').read_text())==ledger
    assert not (tmp_path/'successor/service-resumption/1/started.json').exists()
