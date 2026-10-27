from copy import deepcopy
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import context_bridge, group_review
from legalmath.interpretation.assurance.phased import review_budget_yield as budget
from legalmath.interpretation.assurance.phased.phase import execute
from legalmath.interpretation.assurance.phased.source_review import assignments
from tests.assurance.test_baseline_corpus_repairs import put
from tests.assurance.test_context_need_disposition import setup
from tests.assurance.test_bounded_product import envelope


def refusal():
    return dict(status='FAILED',error='E_RESOURCE_LIMIT',reason='Exact branch refusal',
        resource_details=dict(reason=budget.REASON,owner='p14-baseline',remaining=1482,
            requested=1,protected_other_calls=1482,used_since_revision={'p14':2407}))


def test_actual_loop_yields_preserves_needs_and_detailed_account_population(tmp_path,monkeypatch):
    args=setup(tmp_path,('CLIENT_FACT',))
    p,item,answer,initial=args[:4]
    p.capacity_checkpoint=put(tmp_path,'yield.json',{budget.FIELD:budget.PROFILE})
    other=assignments(p,'p14',[])[1]
    sibling=deepcopy(initial);sibling['value']['considered']=[other['id']]
    original=[deepcopy(initial),deepcopy(sibling)]
    monkeypatch.setattr(group_review,'run',lambda *a,**kw:deepcopy(original))
    calls=[]
    def bridge(*a,**kw):
        calls.append(a[4]['id'])
        return {'result':refusal(),'original_review':deepcopy(a[5])}
    monkeypatch.setattr(context_bridge,'review',bridge)
    p.note=lambda *a,**kw:pytest.fail('Detailed review after budget exhaustion')
    details=[{'id':'obligation-one'},{'id':'reading-two'}]
    result=p.audit_answer('p14',envelope()['original_questions'][0],answer,details,prefix='fixed-')
    assert len(calls)==1 and len(result)==4
    assert [r['value'] for r in result[:2]]==[r['value'] for r in original]
    assert result[1]['context_continuation_deferred']
    assert all(r['status']=='FAILED' and r['review_deferred'] for r in result[2:])
    assert not all(r['status']=='VALIDATED' and r['value']['verdict']=='ACCEPT' for r in result)
    saved=json.loads((p.directory/'fixed-review-budget-deferral-p14.json').read_text())
    assert saved['deferred_context_ids']==[other['id']]
    assert saved['deferred_detailed_account_ids']==['obligation-one','reading-two']
    assert saved['attempted_deferred_items']==0 and not saved['legal_acceptance']


@pytest.mark.parametrize('change',[
    {'remaining':1483,'requested':2}, {'owner':'gatecoin-baseline'},
    {'remaining':'1482'}, {'reason':'Output exceeds local token limit'},
    {'requested':0},
])
def test_only_zero_spendable_same_branch_refusal_yields(change):
    row=refusal();row['resource_details'].update(change)
    assert not budget.exhausted(row,'p14')


@pytest.mark.parametrize('change',[
    {'status':'VALIDATED'}, {'error':'E_SCHEMA'}, {'error':'E_SERVICE'},
    {'resource_details':None}, {'resource_details':{}},
])
def test_other_failures_do_not_become_budget_refusals(change):
    row=refusal();row.update(change)
    assert not budget.exhausted(row,'p14')


def test_same_refusal_does_not_defer_independent_question():
    assert budget.exhausted(refusal(),'p14')
    assert not budget.exhausted(refusal(),'gatecoin')


def test_legacy_loop_and_semantic_unresolved_continue(tmp_path,monkeypatch):
    args=setup(tmp_path,('CLIENT_FACT',));p,item,answer,initial=args[:4]
    other=assignments(p,'p14',[])[1]
    sibling=deepcopy(initial);sibling['value']['considered']=[other['id']]
    monkeypatch.setattr(group_review,'run',lambda *a,**k:deepcopy([initial,sibling]))
    calls=[]
    def bridge(*a,**kw):
        calls.append(a[4]['id'])
        return {'result':deepcopy(a[5])}
    monkeypatch.setattr(context_bridge,'review',bridge)
    result=p.audit_answer('p14',envelope()['original_questions'][0],answer,[],prefix='legacy-')
    assert len(calls)==2 and all(r['value']['verdict']=='UNRESOLVED' for r in result)
    assert not list(p.directory.glob('*review-budget-deferral*'))


def test_phase_preserves_structured_refusal_only_under_selected_profile(tmp_path):
    args=setup(tmp_path,('CLIENT_FACT',));p=args[0]
    p.capacity_checkpoint=put(tmp_path,'yield.json',{budget.FIELD:budget.PROFILE})
    request,shape=args[4],args[5]
    def refuse(*a,**kw):
        raise LegalMathError('E_RESOURCE_LIMIT',details=refusal()['resource_details'])
    result=execute(p,'budget-leaf',[dict(key='budget-leaf',request=request,schema=shape,
        validate=lambda v:None)],implementation_identity=p.phase_identity,admit=refuse,_capacity_leaf=True)
    assert result['results']==[]
    assert budget.exhausted(result['resource_refusal'],'p14')
    assert result['resource_refusal']['resource_details']==refusal()['resource_details']


def test_unrecognized_profile_fails_closed(tmp_path):
    p=setup(tmp_path)[0]
    p.capacity_checkpoint=put(tmp_path,'yield.json',{budget.FIELD:'unknown'})
    with pytest.raises(LegalMathError):budget.enabled(p)
