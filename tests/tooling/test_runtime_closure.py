from copy import deepcopy
from types import SimpleNamespace
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import review_budget_yield as budget
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from scripts import legal_product_closure as closure
from tests.assurance.test_baseline_corpus_repairs import put
from tests.assurance.test_context_need_disposition import setup
from tests.assurance.test_bounded_product import envelope


def test_runtime_profile_does_not_change_provider_request(tmp_path):
    p,item,answer,initial,request,schema=setup(tmp_path)[:6]
    before=p._request('AUDIT_ANSWER_AND_DETAILED_ACCOUNT',envelope()['original_questions'][0],[],payload={'answer':answer},expected=['one'])
    p.review_budget_yield_profile=budget.PROFILE
    after=p._request('AUDIT_ANSWER_AND_DETAILED_ACCOUNT',envelope()['original_questions'][0],[],payload={'answer':answer},expected=['one'])
    assert budget.enabled(p) and before==after


def test_unknown_runtime_profile_rejected_before_initialization():
    with pytest.raises(LegalMathError):
        PhasedProduct(phase_admit=lambda *a:None,phase_identity='old',review_budget_yield_profile='bad')


def test_runtime_and_checkpoint_selection_both_validate(tmp_path):
    p=setup(tmp_path)[0];p.review_budget_yield_profile=budget.PROFILE
    p.capacity_checkpoint=put(tmp_path,'bad.json',{budget.FIELD:'bad'})
    with pytest.raises(LegalMathError):budget.enabled(p)


def test_runtime_projection_preserves_tasks_limits_and_checkpoints(tmp_path):
    baseline={'changed_paths':[], 'archived':[]}
    old={'tasks':[{'id':'baseline-p14','maximum_attempts':9}], 'maximum_calls':8100,
         'deadline_utc':'2026-10-27T05:15:09Z', 'product_closure':{'arm_checkpoints':{'p14':'retained'},'phase_identity':'unchanged'},
         'protected_evidence':[], 'workers':1}
    rev={'baseline':put(tmp_path,'baseline.json',baseline),'review':{},'result':{},'handover':{},
         'master_plan':{'path':'plan','sha256':'fixed'},'implementation':{},'acquisition_fairness_profile':'reviewed'}
    before=deepcopy(old);actual=closure.expected_runtime(old,rev,tmp_path)
    assert old==before
    assert all(actual[k]==old[k] for k in ('tasks','maximum_calls','deadline_utc','workers'))
    assert actual['product_closure']['arm_checkpoints']==old['product_closure']['arm_checkpoints']
    assert actual['product_closure']['phase_identity']=='unchanged'
    assert actual['protected_evidence'][-1]==rev['master_plan']


def test_actual_entry_forwards_runtime_profile(tmp_path,monkeypatch):
    from scripts import legal_product_completion as entry
    from legalmath.interpretation.assurance import answer_acceptance
    from legalmath.interpretation.assurance.bounded_product import PROFILE
    from legalmath.interpretation.assurance.phased import product
    captured={}
    class Stop(Exception):pass
    def constructor(*args,**kwargs):
        captured.update(kwargs);raise Stop()
    monkeypatch.setattr(product,'PhasedProduct',constructor)
    monkeypatch.setattr(answer_acceptance,'validate_manifest',lambda *a:None)
    env={'original_questions':[],'answer_acceptance':{}}
    with pytest.raises(Stop):
        entry.run_product(tmp_path,tmp_path/'out',object(),tmp_path,'date',sources=[],questions=[],
          acceptance_ref=None,qualification={},required={'maximum_calls':8100},deadline_utc='date',selected_tools=[],
          settings=None,consumer_profile=PROFILE,bounded_envelope=env,bounded_encode=lambda x:[],
          bounded_execution='phased',bounded_acquisition_ref={},bounded_phase_admit=lambda *a:None,
          bounded_phase_identity='unchanged',bounded_review_budget_yield_profile=budget.PROFILE)
    assert captured['review_budget_yield_profile']==budget.PROFILE
    assert captured['phase_identity']=='unchanged'


@pytest.mark.parametrize('preparation_only',[True,False])
def test_actual_route_preserves_checkpoint_and_phase_identity(tmp_path,monkeypatch,preparation_only):
    from pathlib import Path
    from scripts import legal_integration_phased_live as live
    from scripts import legal_product_completion as entry
    checkpoint={'path':'retained.json','sha256':'retained'}
    program={'product_closure':{'phase_identity':'old-identity',
        'arm_checkpoints':{'p14':{'baseline':checkpoint}},
        'runtime':{'review_budget_yield_profile':budget.PROFILE}}}
    campaign=SimpleNamespace(ENVELOPE=Path('envelope.json'),effective_deadline=lambda:'unchanged')
    monkeypatch.setattr(live,'ROOT',tmp_path)
    monkeypatch.setattr(live,'configure',lambda:campaign)
    monkeypatch.setattr(live,'read',lambda p:program if p==tmp_path/live.PROGRAM else {'original_questions':[]})
    monkeypatch.setattr(live,'common_directory',lambda *a:Path('common'))
    monkeypatch.setattr(live,'question_live',lambda *a:Path('live'))
    monkeypatch.setattr(live,'phase_admit',lambda *a:'original-admission')
    monkeypatch.setattr(live,'tokenizer',lambda *a:lambda x:[])
    monkeypatch.setattr(live,'ref',lambda *a:{'path':'retained','sha256':'retained'})
    monkeypatch.setattr(entry,'run_product',lambda *a,**kw:kw)
    result=live.product_route('p14',None,object(),preparation_only=preparation_only)
    assert result['bounded_review_budget_yield_profile']==budget.PROFILE
    assert result['bounded_phase_identity']=='old-identity'
    assert result['bounded_phase_admit']=='original-admission'
    if not preparation_only:
        assert result['bounded_capacity_checkpoint']==checkpoint
