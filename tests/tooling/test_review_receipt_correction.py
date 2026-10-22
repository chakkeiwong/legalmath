from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import signal
import pytest
from scripts import legal_review_receipt_correction as correction
from scripts.legal_mission_execution import save, ref, Refused
from tests.assurance.test_source_review_repair import product, MixedReviews
from tests.assurance.test_bounded_product import envelope, limits
from legalmath.interpretation.assurance.phased import review_repair, phase, capacity_policy
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased.downstream_input import PROFILE as INPUT, CAPACITY_PROFILE


def test_new_binding_reuses_exact_settled_group_then_repairs_once(tmp_path, monkeypatch):
    provider=MixedReviews()
    p=product(tmp_path,provider)
    original=phase.execute
    def boundary(product,name,calls,**kwargs):
        if name.startswith('invalid-reviews-'): raise RuntimeError('Reviewed handover boundary')
        return original(product,name,calls,**kwargs)
    monkeypatch.setattr(phase,'execute',boundary)
    answer={'conclusion':'Same conditional answer','support':[],'source_gaps':[]}
    with pytest.raises(RuntimeError,match='handover'):
        p.audit_answer('p14',envelope()['original_questions'][0],answer,[])
    assert len(provider.requests)==1
    manifest=correction.seed_runtime(tmp_path,p.directory,tmp_path/'resumed',provider)
    assert not manifest['phase_contracts_copied'] and manifest['provider_calls']==0
    assert all(r['source']['sha256']==r['copy']['sha256'] for r in manifest['files'])
    monkeypatch.setattr(phase,'execute',original)
    resumed=PhasedProduct(tmp_path,tmp_path/'resumed',provider,envelope(),list,
        limits=replace(limits(),input_tokens=12000),maximum_corrections=1,
        phase_admit=lambda name,count:{'binding':'new','name':name,'count':count},phase_identity='new-binding',
        downstream_input_profile=INPUT,downstream_capacity_profile=CAPACITY_PROFILE,
        common_capacity_profile=capacity_policy.PROFILE,review_repair_profile=review_repair.PROFILE)
    rows=resumed.audit_answer('p14',envelope()['original_questions'][0],answer,[])
    assert len(provider.requests)==2
    assert sum(r['status']=='VALIDATED' for r in rows)==1
    assert sum(r.get('invalid_review_repair_exhausted',False) for r in rows)==1
    assert resumed.audit_answer('p14',envelope()['original_questions'][0],answer,[])==rows
    assert len(provider.requests)==2
    with pytest.raises(Refused,match='already started'):
        correction.seed_runtime(tmp_path,resumed.directory,tmp_path/'forbidden',provider)


@pytest.mark.parametrize('tamper',['result','reserved','provider'])
def test_seed_refuses_changed_or_uncertain_dispatch(tmp_path,tamper):
    p=product(tmp_path)
    p.audit_answer('p14',envelope()['original_questions'][0],{'conclusion':'Same'},[])
    journal=p.directory/'calls/dispatch.json'
    state=json.loads(journal.read_text())
    key=next(iter(state['calls']))
    if tamper=='result':
        path=p.directory/'calls'/key/'result.json'
        result=json.loads(path.read_text()); result['status']='FAILED'; save(path,result)
    elif tamper=='reserved':
        state['calls'][key]['status']='RESERVED';save(journal,state)
    else:
        p.provider.routing={'model':'different'}
    with pytest.raises(Refused):
        correction.seed_runtime(tmp_path,p.directory,tmp_path/'new',p.provider)


def fixture_handover(root):
    owner={'pid':987654,'start':'101'}
    save(root/correction.WORK/'worker.json',{'process':owner})
    state={'tasks':{'baseline-gatecoin':{'status':'RUNNING','attempts':[{}]*4,'live_supervisor':owner}}}
    save(root/correction.STATE,state)
    save(root/correction.BASE/'live-calls.json',{'maximum':8100,'calls':[{}]})
    save(root/correction.WORK/'service/service-circuit.json',{'open':False})
    journal=root/correction.WORK/'live/arms/gatecoin/baseline/calls/dispatch.json'
    save(journal,{'calls':{'group':{'status':'VALIDATED'}}})
    return owner,journal


@pytest.mark.parametrize('problem',['reserved','child','repair_started','identity','open_circuit'])
def test_handover_never_signals_unsettled_worker(tmp_path,monkeypatch,problem):
    import scripts.legal_mission_execution as execution
    owner,journal=fixture_handover(tmp_path)
    monkeypatch.setattr(execution,'process_identity',lambda pid:None if problem=='identity' else owner)
    original=Path.read_text
    def read(path,*a,**k):
        if str(path).startswith('/proc/'):
            return '12345' if problem=='child' else ''
        return original(path,*a,**k)
    monkeypatch.setattr(Path,'read_text',read)
    signals=[]
    monkeypatch.setattr(correction.os,'kill',lambda *args:signals.append(args))
    if problem=='reserved':save(journal,{'calls':{'group':{'status':'RESERVED'}}})
    if problem=='repair_started':save(journal,{'calls':{'repair-review-x':{'status':'VALIDATED'}}})
    if problem=='open_circuit':save(tmp_path/correction.WORK/'service/service-circuit.json',{'open':True})
    if problem in ('identity','repair_started'):
        with pytest.raises(Refused):correction.settle_once(tmp_path,expected=owner)
    else:
        assert not correction.settle_once(tmp_path,expected=owner)['settled']
    assert not signals


def test_handover_retains_reservation_and_ledger(tmp_path,monkeypatch):
    import scripts.legal_mission_execution as execution
    owner,_=fixture_handover(tmp_path)
    before_state=ref(tmp_path,correction.STATE)
    before_ledger=ref(tmp_path,correction.BASE/'live-calls.json')
    signals=[]
    monkeypatch.setattr(execution,'process_identity',lambda pid:None if signal.SIGCONT in signals else owner)
    monkeypatch.setattr(correction.os,'kill',lambda pid,which:signals.append(which))
    original=Path.read_text
    def read(path,*a,**k):
        if str(path).startswith('/proc/'):
            return '' if path.name=='children' else '987654 (python) T 0'
        return original(path,*a,**k)
    monkeypatch.setattr(Path,'read_text',read)
    result=correction.settle_once(tmp_path,expected=owner)
    assert result['supervisor_ended'] and result['reserved_dispatches']==0
    assert signals==[signal.SIGSTOP,signal.SIGTERM,signal.SIGCONT]
    assert ref(tmp_path,correction.STATE)==before_state
    assert ref(tmp_path,correction.BASE/'live-calls.json')==before_ledger


def test_correction_history_preserves_attempts_and_completed_success(tmp_path):
    before={'events':[{'old':True}],'tasks':{
        'a':{'status':'RUNNING','attempts':[{'number':4,'started_at_utc':'then'}]},
        'b':{'status':'SUCCEEDED','attempts':[{'number':1,'result':{}}]}}}
    save(tmp_path/'before.json',before)
    program={'review_repair':{'receipt_correction':{'prior_state':ref(tmp_path,'before.json')}}}
    state=deepcopy(before)
    state['tasks']['a']['attempts'][0]['result']={'finished':True}
    correction.validate_history(program,state,tmp_path)
    state['tasks']['a']['attempts'][0]['number']=1
    with pytest.raises(Refused):correction.validate_history(program,state,tmp_path)


def test_program_amendment_changes_no_task_or_authority(tmp_path):
    old={'review_repair':{'attempt_additions':{'baseline-gatecoin':1}},'tasks':[{'id':'a','maximum_attempts':4}],
        'deadline_utc':'unchanged','global_call_ceiling':8100,'protected_evidence':[]}
    save(tmp_path/'baseline.json',{'archived':[]})
    correction_row={'implementation':{},'review':{},'result':{},'baseline':ref(tmp_path,'baseline.json'),'seed':{}}
    result=correction.expected_program(old,correction_row,tmp_path,{'plan':'new'})
    assert result['tasks']==old['tasks']
    assert result['deadline_utc']==old['deadline_utc'] and result['global_call_ceiling']==8100
    assert result['review_repair']['attempt_additions']==old['review_repair']['attempt_additions']
