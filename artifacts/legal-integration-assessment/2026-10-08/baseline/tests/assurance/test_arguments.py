from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.arguments import evaluate_criticism, case_moves
from .support import packet, inventory


def argument(name='a', atom='prohibited', negative=False, kind='DEFEASIBLE'):
    return {'argument_id': name, 'candidate_id': 'candidate', 'premises': [], 'parents': [],
            'inference_id': 'rule.'+name, 'inference_kind': kind, 'inference': 'Declared test inference',
            'conclusion': {'atom': atom, 'negative': negative}, 'evidence': inventory()['claims'][0]['evidence']}


def value(*args):
    return {'arguments': list(args), 'attacks': [], 'preferences': [], 'cases': [], 'case_queries': [], 'questions': []}


def premise(kind, status):
    return {'premise_id': 'p', 'proposition': {'atom': 'gift', 'negative': False}, 'kind': kind,
            'status': status, 'evidence': inventory()['claims'][0]['evidence'] if status in ('SUPPORTED','REJECTED') else [],
            'explanation': 'Controlled premise'}


def test_undercut_targets_inference_not_conclusion_and_propagates():
    a, b, c = argument(), argument('b', 'applicable.rule.a', True, 'STRICT'), argument('c', 'other', kind='STRICT')
    c['parents'] = ['a']; v = value(a,b,c)
    v['attacks'] = [{'attacker': 'b', 'target': 'a', 'kind': 'UNDERCUT', 'target_component': 'rule.a', 'rationale': 'Exception to inference'}]
    result = evaluate_criticism(v, packet(), ['candidate'])
    assert ['b','a'] in result['defeats'] and ['b','c'] in result['defeats']
    v['attacks'][0]['kind'] = 'REBUT'
    with pytest.raises(LegalMathError): evaluate_criticism(v, packet(), ['candidate'])


def test_premise_attack_and_strict_conclusion_protection():
    a, b = argument(kind='STRICT'), argument('b', 'gift', True)
    a['premises'] = [premise('ORDINARY','SUPPORTED')]; v = value(a,b)
    v['attacks'] = [{'attacker':'b','target':'a','kind':'UNDERMINE','target_component':'p','rationale':'Opposed premise'}]
    assert ['b','a'] in evaluate_criticism(v, packet(), ['candidate'])['defeats']
    v['attacks'][0].update(kind='REBUT', target_component='a')
    with pytest.raises(LegalMathError): evaluate_criticism(v, packet(), ['candidate'])


def test_model_preference_cannot_remove_attack_without_explicit_acceptance():
    a,b = argument(), argument('b','prohibited',True); v=value(a,b)
    v['attacks']=[{'attacker':'b','target':'a','kind':'REBUT','target_component':'a','rationale':'Conflict'}]
    pref={'preferred':'a','over':'b','evidence':a['evidence'],'rationale':'Proposed priority'}; v['preferences']=[pref]
    result=evaluate_criticism(v,packet(),['candidate'])
    assert ['b','a'] in result['defeats'] and result['questions']
    accepted=evaluate_criticism(v,packet(),['candidate'],accepted_preferences=[digest(pref)])
    assert not accepted['defeats']


def test_one_repair_sees_both_wrong_id_namespace_and_abbreviated_quote():
    a,b=argument(),argument('b');v=value(a,b)
    v['preferences']=[{'preferred':'candidate','over':'b','evidence':deepcopy(a['evidence']),
                       'rationale':'A candidate can have several supporting arguments'}]
    v['arguments'][0]['evidence']=[{**a['evidence'][0],'quote':'Distributors ... gifts'}]
    with pytest.raises(LegalMathError) as exc:evaluate_criticism(v,packet(),['candidate'])
    errors=exc.value.details['errors']
    assert any('argument_id, not candidate_id'==e['expected'] for e in errors)
    assert any('contiguous exact quote' in e['expected'] for e in errors)
    v['preferences'][0]['preferred']='a';v['arguments'][0]['evidence']=inventory()['claims'][0]['evidence']
    result=evaluate_criticism(v,packet(),['candidate'])
    assert result['preference_proposals'] and not result['candidate_pruning_authorized']


def test_rebut_repair_gets_exact_target_and_still_must_prove_opposition():
    a,b=argument(),argument('b','prohibited',True);v=value(a,b)
    v['attacks']=[{'attacker':'a','target':'b','kind':'REBUT','target_component':'conclusion','rationale':'Opposite readings'}]
    with pytest.raises(LegalMathError) as exc:evaluate_criticism(v,packet(),['candidate'])
    error=exc.value.details['errors'][0]
    assert error['actual']=='conclusion' and error['expected']=='b'
    v['attacks'][0]['target_component']='b'
    assert ['a','b'] in evaluate_criticism(v,packet(),['candidate'])['defeats']
    v['arguments'][0]['conclusion']['atom']='unrelated'
    with pytest.raises(LegalMathError):evaluate_criticism(v,packet(),['candidate'])


@pytest.mark.parametrize('kind,status,blocked,conditional',[
    ('ORDINARY','QUESTIONED',True,False),('ORDINARY','SUPPORTED',False,False),
    ('ASSUMPTION','STATED',False,True),('ASSUMPTION','QUESTIONED',True,True),
    ('EXCEPTION','SUPPORTED',True,False),('EXCEPTION','STATED',False,True),('EXCEPTION','REJECTED',False,False)])
def test_premise_roles(kind,status,blocked,conditional):
    a=argument();a['premises']=[premise(kind,status)]
    result=evaluate_criticism(value(a),packet(),['candidate'])
    assert ('a' in result['blocked_arguments']) == blocked
    assert ('a' in result['conditional_arguments']) == conditional


def test_cycles_and_bounds_remain_unresolved():
    a,b=argument(),argument('b');a['parents']=['b'];b['parents']=['a']
    assert evaluate_criticism(value(a,b),packet(),['candidate'])['status']=='CYCLIC_SUPPORT_UNRESOLVED'
    assert evaluate_criticism(value(a,b),packet(),['candidate'],maximum=1)['status']=='ARGUMENT_LIMIT'


def test_mutual_rebuttal_retains_both_uncertain_alternatives():
    a,b=argument(),argument('b','prohibited',True);v=value(a,b)
    v['attacks']=[{'attacker':s,'target':t,'kind':'REBUT','target_component':t,'rationale':'Conflict'} for s,t in [('a','b'),('b','a')]]
    result=evaluate_criticism(v,packet(),['candidate'])
    assert result['status']=='UNRESOLVED' and result['semantics']['grounded']==[]
    assert not result['candidate_pruning_authorized']


def test_case_constructors_check_factors_and_evidence():
    case={'case_id':'example','authority':'OFFICIAL_EXAMPLE','outcome':{'atom':'prohibited','negative':False},
          'factors':['gift','product.link'],'evidence':inventory()['claims'][0]['evidence'],'rationale':'Fixture, not real precedent'}
    desired={'atom':'prohibited','negative':True}
    ops={m['operator'] for m in case_moves(case,['gift','product.link','discount'],desired,packet())}
    assert ops == {'ANALOGISE','DISTINGUISH','COUNTERCASE'}
    assert not case_moves(case,['unrelated'],desired,packet())
    case['evidence'][0]['quote']='Invented court decision'
    with pytest.raises(LegalMathError):case_moves(case,['gift'],desired,packet())
