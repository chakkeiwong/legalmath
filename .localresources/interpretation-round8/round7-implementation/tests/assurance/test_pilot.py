"""Recovery must retain prior consumption and cannot become an unscoped replay."""
import importlib.util
from pathlib import Path
import pytest
from legalmath.canonical import canonical,digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.search.models import Settings


def pilot():
    path=Path(__file__).resolve().parents[2]/'scripts/interpretation_assurance_pilot.py'
    spec=importlib.util.spec_from_file_location('assurance_pilot',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class Provider:
    provider_id='test';live=True;routing={}
    def __init__(self):self.calls=0
    def complete(self,request,schema,settings):
        self.calls+=1;return Completion({'fresh':True},{'new_live_invocation':True})


def inputs(tmp_path):
    request={'task':'SOURCE_INVENTORY','role':'reader'};response={'claims':[]};schema={'type':'object'}
    record={'request':request,'response':response,'schema':schema,'request_hash':digest(request),
            'response_hash':digest(response),'contract_status':'VALID_CONTRACT','events_jsonl':'',
            'origin':'Completed prior invocation'}
    recovery=tmp_path/'recovered.json';recovery.write_bytes(canonical(record))
    allowance=tmp_path/'allowance.json';allowance.write_bytes(canonical({'maximum':100,'calls':[{'request_hash':digest(request)}]}))
    return request,schema,recovery,allowance


def test_recovery_requires_exact_request_and_schema_and_is_used_once(tmp_path):
    request,schema,recovery,allowance=inputs(tmp_path);provider=Provider()
    wrapper=pilot().IncrementCap(provider,allowance,recovery)
    assert wrapper.complete({**request,'role':'other'},schema,Settings()).value=={'fresh':True}
    assert wrapper.complete(request,{'type':'array'},Settings()).value=={'fresh':True}
    answer=wrapper.complete(request,schema,Settings())
    assert answer.provenance['allowance_slot']==1 and answer.provenance['new_live_invocation'] is False
    assert wrapper.complete(request,schema,Settings()).value=={'fresh':True}
    assert provider.calls==3


def test_recovery_rejects_a_response_without_prior_counted_dispatch(tmp_path):
    _,_,recovery,allowance=inputs(tmp_path)
    allowance.write_bytes(canonical({'maximum':100,'calls':[]}))
    with pytest.raises(LegalMathError):pilot().IncrementCap(Provider(),allowance,recovery)


def test_journal_bounds_inflight_call_by_remaining_run_deadline(tmp_path):
    from legalmath.interpretation.assurance.journal import JournalProvider
    received=[]
    class Bounded(Provider):
        def complete(self,request,schema,settings):
            received.append(settings.timeout_seconds)
            return super().complete(request,schema,settings)
    journal=JournalProvider(Bounded(),tmp_path/'calls',deadline_seconds=10)
    journal.complete({'task':'TEST'},{},Settings(timeout_seconds=300))
    assert 1<=received[0]<=10


def test_increment_refuses_dispatch_at_reviewed_ceiling_and_matches_plan(tmp_path):
    import json
    module=pilot();provider=Provider()
    plan=json.loads((Path(__file__).resolve().parents[2]/'docs/implementation/interpretation-round3/master-plan.json').read_text())
    assert module.RESERVATION_CEILING==plan['initial_used']+plan['increment_live_cap']<=plan['live_call_allowance']
    allowance=tmp_path/'allowance.json'
    allowance.write_bytes(canonical({'maximum':100,'calls':[{}]*module.RESERVATION_CEILING}))
    with pytest.raises(LegalMathError) as error:
        module.IncrementCap(provider,allowance).complete({'task':'SOURCE_FIDELITY'},{},Settings())
    assert error.value.code=='E_RESOURCE_LIMIT' and provider.calls==0


def test_task_replay_requires_exact_override_evidence_without_dispatch(tmp_path):
    from .test_retained import retained
    base,allowance,request,schema=retained(tmp_path)
    module=pilot();provider=Provider()
    plan={'directory':str(base),'allowed_live_tasks':[],
          'task_overrides':{'SOURCE_INVENTORY':str(base)}}
    replay=module.TaskReplay(provider,allowance,plan)
    before=allowance.read_bytes()
    with pytest.raises(LegalMathError):replay.complete(request,{'type':'array'},Settings())
    answer=replay.complete(request,schema,Settings())
    assert answer.provenance['allowance_slot']==1
    assert answer.provenance['new_live_invocation'] is False
    with pytest.raises(LegalMathError):replay.complete({'task':'STRUCTURED_CRITICISM'},schema,Settings())
    assert allowance.read_bytes()==before and provider.calls==0


def test_failed_source_does_not_skip_independent_checks_or_pass_acceptance(tmp_path,monkeypatch):
    import json
    import sys
    module=pilot();seen=[]
    allowance=tmp_path/'allowance.json';allowance.write_bytes(canonical({'maximum':100,'calls':[]}))
    class Engine:
        def __init__(self,directory,*args):self.ref=directory.name
        def drive(self,*args):
            seen.append(self.ref)
            return {'execution_complete':False,'model_calls':7,'inventories':[],
                    'fidelity':None,'argumentation':None,'release_eligible':False,
                    'status':'UNRESOLVED','residual_questions':['Missing check'],'failures':[]}
        def verify(self):pass
    monkeypatch.setattr(module,'Assurance',Engine)
    monkeypatch.setattr(module,'CodexProvider',lambda **kwargs:Provider())
    monkeypatch.setattr(module,'source',lambda ref:ref)
    def challenge(*args):seen.append('challenge');return {'passed':True}
    monkeypatch.setattr(module,'omission_challenge',challenge)
    out=tmp_path/'pilot'
    monkeypatch.setattr(sys,'argv',['pilot','--out',str(out),'--allowance',str(allowance)])
    with pytest.raises(SystemExit) as error:module.main()
    assert error.value.code==1 and seen==['23EC46','24EC16','challenge']
    assert json.loads((out/'result.json').read_text())['engineering_pass'] is False
