from copy import deepcopy
from legalmath.interpretation.assurance.resolution import Answers,choose_action,action_key,residual_questions
from .support import packet,inventory


def test_actions_prefer_discriminating_evidence_and_never_repeat_identical_failure():
    actions=[{'kind':'CHECK_SOURCE_CLAIM','issue_key':'i','inputs':{'version':1},'separated_pairs':4},
             {'kind':'EXTERNAL_QUESTION','issue_key':'i','inputs':{},'separated_pairs':100},
             {'kind':'ACQUIRE_AUTHORITY','issue_key':'i','inputs':{},'separated_pairs':3}]
    scope={'source':'v1'}
    first=choose_action(actions,set(),scope,remaining_cost=10)
    assert first['kind']=='ACQUIRE_AUTHORITY'
    second=choose_action(actions,{action_key(first,scope)},scope,remaining_cost=10)
    assert second['kind']=='CHECK_SOURCE_CLAIM'
    assert choose_action(actions,{action_key(a,scope) for a in actions},scope,remaining_cost=100) is None


def test_reuse_requires_exact_source_scope_assumptions_method_and_binding(tmp_path):
    answers=Answers(tmp_path)
    scope={'method':'v1','fact_schema':'f1','assumptions':['discount is solely fees'],'control':'gift'}
    answers.record('  Is this a fee discount? ','Under the retained evidence, yes.',scope,
                   inventory()['claims'][0]['evidence'],packet(),evidence_class='MACHINE_DIAGNOSTIC',limitations=['Unverified model judgment'])
    assert len(answers.lookup('is this a fee discount?',scope,packet()))==1
    for key in scope:
        altered=deepcopy(scope);altered[key]=['other'] if isinstance(scope[key],list) else 'changed'
        assert answers.lookup('is this a fee discount?',altered,packet())==[]
    p=packet();p['units'][0]['text']+=' A new qualification applies.'
    assert answers.lookup('is this a fee discount?',scope,p)==[]


def test_duplicate_residual_questions_retain_all_candidates():
    findings=[{'kind':'SOURCE_NOT_ESTABLISHED','stage':'FORMALIZATION','question':'Where is the exception?',
               'claim_id':'exception','candidate_id':c} for c in ('a','b','c')]
    result=residual_questions(findings)
    assert len(result)==1 and result[0]['candidate_ids']==['a','b','c']
    assert not result[0]['external_consultancy_required']


def test_atomic_increment_cap_does_not_change_authorized_global_maximum(tmp_path):
    import pytest
    from legalmath.interpretation.search.providers import Allowance
    from legalmath.errors import LegalMathError
    from legalmath.canonical import loads
    path=tmp_path/'calls.json';allowance=Allowance(path,100,reservation_ceiling=2)
    allowance.reserve('a'*64);allowance.reserve('b'*64)
    with pytest.raises(LegalMathError):allowance.reserve('c'*64)
    assert loads(path.read_bytes())['maximum']==100
