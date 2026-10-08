from copy import deepcopy
from itertools import product
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import conditional_elimination as e
from .test_challenge_contract import inputs


def obligation(packet,question):
    return {'obligation_id':'exception.precludes', 'packet_hash':digest(packet), 'question_hash':digest(question),
        'when':'discount','expected':False,'evidence':question['source_evidence'],
        'premise_status':'PROPOSED_FORMAL_PREMISE','rationale':'Declared fixture relation, not English entailment.'}


def test_actual_counterexample_and_correct_candidate_remain_distinct():
    p,r,q,_=inputs(); question=q['candidate.a']; candidate=r['candidate.a']; o=[obligation(p,question)]
    good=e.check(p,candidate,question,o)
    assert good['status']=='NO_DECLARED_OBLIGATION_VIOLATION' and good['valuations_checked']==4
    candidate['formalization']['result']='gift'
    bad=e.check(p,candidate,question,o)
    assert bad['status']=='CONDITIONALLY_REJECTED'
    assert bad['witnesses'][0]['assignment']=={'gift':True,'discount':True}
    assert not bad['legal_elimination'] and bad['original_candidate_retained']
    assert e.verify(bad,p,candidate,question,o)==bad


@pytest.mark.parametrize('mutation',['witness','candidate','question','premise','status'])
def test_certificate_cannot_be_transferred_or_forged(mutation):
    p,r,q,_=inputs(); candidate=r['candidate.a']; candidate['formalization']['result']='gift'
    question=q['candidate.a']; o=[obligation(p,question)]; cert=e.check(p,candidate,question,o)
    if mutation=='witness':cert['witnesses'][0]['assignment']['gift']=False
    elif mutation=='candidate':candidate['formalization']['result']='false'
    elif mutation=='question':question['question']+=' changed'
    elif mutation=='premise':o[0]['expected']=True
    else:cert['source_entailment']='PROVED'
    with pytest.raises(LegalMathError):e.verify(cert,p,candidate,question,o)


def test_scope_failure_is_not_hidden_by_correct_body():
    p,r,q,_=inputs(); candidate=r['candidate.a'];candidate['formalization']['scope']='false'
    assert e.check(p,candidate,q['candidate.a'],[obligation(p,q['candidate.a'])])['witnesses']


@pytest.mark.parametrize('expression',['(> gift discount)','(not gift discount)','(and unknown gift)','(and ())','(fact gift)'])
def test_unsupported_grammar_is_never_called_valid(expression):
    p,r,q,_=inputs(); candidate=r['candidate.a']; candidate['formalization']['result']=expression
    assert e.check(p,candidate,q['candidate.a'],[])['status']=='UNSUPPORTED'


def test_unknown_and_conflict_values_are_outside_total_domain():
    tree=e.parse_boolean('(and gift (not discount))',['gift','discount'])
    for value in (None,'UNKNOWN','CONFLICT',1):
        with pytest.raises(LegalMathError):e.evaluate(tree,{'gift':value,'discount':False})


def test_breadth_first_enumeration_preserves_truncated_frontier():
    complete=e.enumerate_grammar(['a'],maximum_depth=1,maximum_expressions=24)
    assert complete['declared_grammar_complete'] and len(complete['expressions'])==24
    limited=e.enumerate_grammar(['a'],maximum_depth=2,maximum_expressions=24)
    assert not limited['declared_grammar_complete'] and limited['completed_depth']==1
    assert limited['frontier']['depth']==2 and not limited['all_legal_interpretations_found']
    assert limited['expressions']==complete['expressions']


def test_independent_evaluator_matches_explicit_truth_relations():
    for a,b,c in product((False,True),repeat=3):
        values={'a':a,'b':b,'c':c}
        for expression,expected in [('(or (and a b) (not c))',(a and b) or not c),
                                    ('(if a b c)',b if a else c),('(= a b)',a==b)]:
            assert e.evaluate(e.parse_boolean(expression,list(values)),values)==expected


def test_no_formal_premises_does_not_create_a_vacuous_legal_pass():
    p,r,q,_=inputs(); result=e.check(p,r['candidate.a'],q['candidate.a'],[])
    assert result['status']=='NO_FORMAL_OBLIGATIONS' and result['source_entailment']=='NOT_ESTABLISHED'
