"""Reusable command boundaries, with a counted synthetic provider only."""
from copy import deepcopy
from pathlib import Path
import fcntl
import importlib.util
import pytest
from legalmath.canonical import digest,loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.providers import Allowance,Completion

ROOT=Path('/home/chakwong/python/legalmath')
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'


def module():
    spec=importlib.util.spec_from_file_location('legalmath.interpretation.assurance.public_issue','/tmp/legalmath-issue-cli/public_issue.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def fixture(tmp_path,*,crash=False):
    study=loads((ROOT/'docs/implementation/interpretation-round9/study.json').read_bytes())
    public=deepcopy(study['public_interfaces']['family-offices.clean'])
    reading=deepcopy(next(c for c in study['study']['cases'] if c['case_id']=='family-offices.clean')['reference']['binding_reading'])
    ledger=tmp_path/'allowance.json';save(ledger,{'maximum':100,'calls':[]})
    allowance=Allowance(ledger,100,reservation_ceiling=24)
    class Provider:
        provider_id='test.public.issue';live=True;routing={'provider':'fixture','model':'controlled'}
        def __init__(self):self.calls=0
        def complete(self,request,schema,settings):
            self.calls+=1;slot=allowance.reserve(digest(request))
            if crash and self.calls==1:raise KeyboardInterrupt()
            answer={'readings':[reading],'vocabulary_concerns':[], 'questions':['Fixture source uncertainty persists.']}
            return Completion(answer,{'request_hash':digest(request),'response_hash':digest(answer),
                'allowance_slot':slot,'provider_route_hash':digest(self.routing),'provider':self.provider_id,'fresh_context':True})
    return public,ledger,Provider()


def test_issue_command_completes_and_reuses_exact_results_without_model_dispatch(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path);out=tmp_path/'issue'
    result=m.run_public_issue(public,out,ledger,JDK,arm='single-reader',provider=provider)
    assert result['status']=='UNCERTAINTY_RETAINED' and not result['release_eligible']
    assert provider.calls==1 and result['model_calls']==1
    assert all(d['question']==public['issue']['question'] and d['meaning']=='TRUE_IS_SATISFIED'
               for d in result['output_descriptors'].values())
    assert m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)==result
    assert provider.calls==1
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',provider=provider)
    changed=deepcopy(public);changed['issue']['question']='Different legal question'
    with pytest.raises(LegalMathError):m.run_public_issue(changed,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)
    assert provider.calls==1
    monkeypatch.setattr(m,'implementation_hash',lambda:'b'*64)
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)


def test_saved_method_evidence_and_allowance_history_are_checked_on_resume(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path);out=tmp_path/'issue'
    m.run_public_issue(public,out,ledger,JDK,arm='single-reader',provider=provider)
    original=ledger.read_bytes();data=loads(original);data['calls'][0]['issued_at_ns']='1';save(ledger,data)
    # The initial empty checkpoint alone cannot authenticate later consumption;
    # validated queue receipts supply the binding to actual dispatch history.
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)
    ledger.write_bytes(original)
    save(out/'work/result.json',{'changed':True})
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)


def test_cli_forwards_only_explicit_input_and_recovery_options(monkeypatch,capsys):
    import sys
    m=module();seen=[]
    monkeypatch.setattr(m,'execute_cli',lambda args:seen.append(args) or {'status':'RECOVERED','release_eligible':False})
    monkeypatch.setitem(sys.modules,'legalmath.interpretation.assurance.public_issue',m)
    spec=importlib.util.spec_from_file_location('legalmath.cli','/tmp/legalmath-issue-cli/cli.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    monkeypatch.setattr(sys,'argv',['legalmath','assurance-interpret-issue','--public','question.json',
        '--out','run','--allowance','existing-grant.json','--jdk','jdk','--method','search','--recover'])
    cli.main()
    assert seen[0].public=='question.json' and seen[0].recover and not seen[0].resume
    assert seen[0].method=='search' and seen[0].deadline_seconds==3600
    assert 'RECOVERED' in capsys.readouterr().out


def test_interruption_requires_recovery_and_preserves_consumed_call(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path,crash=True);out=tmp_path/'issue'
    with pytest.raises(KeyboardInterrupt):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',provider=provider)
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)
    recovered=m.run_public_issue(public,out,ledger,JDK,arm='single-reader',recover=True,provider=provider)
    assert recovered['status']=='RECOVERED' and recovered['recovery']['recovered_tasks']==1
    result=m.run_public_issue(public,out,ledger,JDK,arm='single-reader',resume=True,provider=provider)
    assert result['model_calls']==2 and provider.calls==2
    assert len(loads(ledger.read_bytes())['calls'])==2


def test_missing_allowance_changed_history_and_concurrent_operation_fail_before_dispatch(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path);out=tmp_path/'issue'
    with pytest.raises(LegalMathError):m.run_public_issue(public,out,tmp_path/'missing.json',JDK,provider=provider)
    assert provider.calls==0
    out.mkdir()
    with (out/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with pytest.raises(LegalMathError):m.run_public_issue(public,out,ledger,JDK,resume=True,provider=provider)
    assert provider.calls==0


def test_partial_remaining_allowance_is_rejected_without_reset_or_dispatch(tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path)
    save(ledger,{'maximum':10,'calls':[]})
    with pytest.raises(LegalMathError):m.run_public_issue(public,tmp_path/'out',ledger,JDK,provider=provider)
    assert provider.calls==0 and loads(ledger.read_bytes())=={'maximum':10,'calls':[]}


@pytest.mark.parametrize('defect',['timestamp','duplicate_source_unit','invalid_packet','missing_jdk'])
def test_invalid_public_environment_is_rejected_before_paid_dispatch(defect,tmp_path,monkeypatch):
    m=module();monkeypatch.setattr(m,'implementation_hash',lambda:'a'*64)
    public,ledger,provider=fixture(tmp_path);jdk=JDK
    if defect=='timestamp':public['at']='not a UTC time'
    elif defect=='duplicate_source_unit':
        public['packet']['units'].append(deepcopy(public['packet']['units'][0]))
        public['issue']['source_packet_hash']=digest(public['packet'])
    elif defect=='invalid_packet':public['packet']['extra']='unvalidated field'
    else:jdk=tmp_path/'absent-jdk'
    with pytest.raises(LegalMathError):m.run_public_issue(public,tmp_path/'out',ledger,jdk,provider=provider)
    assert provider.calls==0 and loads(ledger.read_bytes())['calls']==[]
