from copy import deepcopy
from pathlib import Path
import sys
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.invariant import prepare,decide,str_time_facts,report_history
from legalmath.interpretation.assurance.invariant_java import build,run
from legalmath.interpretation.assurance.explicit_resolution import validate_proposal,obligations,validate_exclusions
from tests.assurance.support import packet,reading

ROOT=Path(__file__).resolve().parents[2]
AT='2026-09-26T00:00:00.000000Z'

def question():
    return {'control_id':'gift','question':'Is this benefit caught by the gift restriction?',
        'actor':'distributor','unit_of_assessment':'one benefit','temporal_basis':'frozen provision',
        'result_kind':'PROHIBITED','true_means':'caught','false_means':'not caught',
        'source_evidence':reading()['citations']}

def prepared(left=None,right=None):
    q=question()
    return prepare(packet(),q,{'a':{'question':q,'reading':left or reading()},
        'b':{'question':q,'reading':right or reading()}},['a','b'],AT)

def snap(gift,discount):
    values={'gift':gift,'discount':discount}; facts={}
    for name,v in values.items():
        facts[name]={'type':'bool','status':'unknown','reason':'MISSING'} if v is None else {
            'type':'bool','status':'known','value':v,'evidence_ids':['test.fixture'],
            'valid_from':AT,'valid_until':None,'recorded_at':AT}
    return {'subject_id':'test','facts':facts}

@pytest.mark.parametrize('gift,discount,value',[(True,False,True),(True,True,False),(False,False,False),(False,None,False)])
def test_all_retained_agree_on_known_result(gift,discount,value):
    result=decide(prepared(),snap(gift,discount),digest(packet()),AT,AT)
    assert result['status']=='INVARIANT_KNOWN' and result['value'] is value
    assert result['conditional_on_retained_hypotheses'] and not result['release_eligible']

def test_rival_exception_has_concrete_witness_and_no_majority():
    p=prepared(right=reading(omitted=True))
    r=decide(p,snap(True,True),digest(packet()),AT,AT)
    assert r['status']=='INTERPRETATION_DISAGREEMENT' and r['value'] is None
    assert {r['outcomes'][k]['value'] for k in r['outcomes']}=={False,True}

def test_unencoded_rival_and_unknown_cannot_be_dropped():
    r=reading();r['formalization']=None
    assert decide(prepared(right=r),snap(True,False),digest(packet()),AT,AT)['status']=='UNENCODED_ALTERNATIVE'
    assert decide(prepared(),snap(True,None),digest(packet()),AT,AT)['status']=='UNKNOWN_OR_CONFLICT'
    with pytest.raises(LegalMathError):prepare(packet(),question(),{'a':{'question':question(),'reading':reading()}},['a','b'],AT)

def test_question_polarity_and_fact_definitions_are_part_of_identity():
    q=question();other={**q,'result_kind':'COMPLIANT'}
    with pytest.raises(LegalMathError):prepare(packet(),q,{'a':{'question':other,'reading':reading()}},['a'],AT)
    r=reading();r['formalization']['facts'][0]['meaning']='The opposite classification'
    with pytest.raises(LegalMathError):prepared(right=r)
    r=reading();r['statement']=r['statement'].replace('TRUE_IS_PROHIBITED','TRUE_IS_COMPLIANT')
    with pytest.raises(LegalMathError):prepared(right=r)

def test_source_change_and_tamper_invalidate_current_assurance():
    p=prepared()
    assert decide(p,snap(True,False),'0'*64,AT,AT)['status']=='SOURCE_CHANGED'
    p['alternatives'].pop('b')
    with pytest.raises(LegalMathError):decide(p,snap(True,False),digest(packet()),AT,AT)

def test_scope_disagreement_is_not_false_agreement():
    r=reading();r['formalization']['scope']='false'
    assert decide(prepared(right=r),snap(False,False),digest(packet()),AT,AT)['status']=='INTERPRETATION_DISAGREEMENT'
    assert decide(prepared(r,r),snap(False,False),digest(packet()),AT,AT)['status']=='INVARIANT_NOT_APPLICABLE'

def test_unanimous_common_error_has_no_legal_approval():
    # Both omit the same source exception. Agreement alone cannot detect this.
    r=decide(prepared(reading(True),reading(True)),snap(True,True),digest(packet()),AT,AT)
    assert r['status']=='INVARIANT_KNOWN' and r['value'] is True
    assert r['release_eligible'] is False  # source-explicit answer would be false

def test_actual_generated_java_ensemble_and_refusals(tmp_path):
    for index,p in enumerate((prepared(),prepared(right=reading(True)),prepared(right={**reading(),'formalization':None}))):
        built=build(p,tmp_path/str(index),ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1')
        requests=[{'snapshot':snap(g,d),'source_packet_hash':s,'valid_at':AT,'known_at':AT}
            for g,d,s in [(True,False,digest(packet())),(True,True,digest(packet())),(True,None,digest(packet())),(True,False,'0'*64)]]
        observed=run(built,requests,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1')
        assert observed==[decide(p,r['snapshot'],r['source_packet_hash'],AT,AT) for r in requests]

@pytest.mark.parametrize('instant,blackout,calendar,operational',[
    ('2026-01-27T23:59:59+08:00',False,False,False),('2026-01-28T00:00:00+08:00',True,False,False),
    ('2026-02-02T02:00:00+08:00',True,True,False),('2026-02-02T09:00:00+08:00',False,True,True),
    ('2026-02-02T01:00:00Z',False,True,True)])
def test_str_interval_boundaries(instant,blackout,calendar,operational):
    assert str_time_facts(instant)==dict(blackout=blackout,calendar_start=calendar,operational_start=operational)

def test_time_unknown_and_no_silent_local_timezone():
    assert all(v is None for v in str_time_facts(None).values())
    with pytest.raises(LegalMathError):str_time_facts('2026-02-02T09:00:00')

def test_history_witness_differs_from_complete_absence():
    assert report_history([False],history_complete=False) is None
    assert report_history([True],history_complete=False) is True
    assert report_history([False,None],history_complete=True) is None
    assert report_history([False],history_complete=True) is False
    assert report_history([],history_complete=True) is False

def test_decomposition_cannot_erase_parent_questions_or_relabel_new_meaning():
    original=reading();original['formalization']=None;original['questions']=['Which package definition applies?']
    proposal={'original_hash':digest(original),'change_kind':'NEW_FORMALIZATION','children':[reading()],
        'parent_relation':'Child is conditional; parent unresolved.','residual_questions':original['questions'],
        'obligations':[{'parent_item':p,'treatment':'UNRESOLVED','child_ids':[],
            'explanation':'Authority unresolved'} for p in obligations(original)]}
    result=validate_proposal(original,packet(),proposal,AT)
    assert result['parent_remains_retained'] and result['original']['formalization'] is None
    broken=deepcopy(proposal);broken['obligations'].pop()
    with pytest.raises(LegalMathError):validate_proposal(original,packet(),broken,AT)
    broken=deepcopy(proposal);broken['change_kind']='NOTATION_REPAIR'
    with pytest.raises(LegalMathError):validate_proposal(original,packet(),broken,AT)

def test_exclusion_challenge_must_account_exact_pairs():
    row={'claim_id':'c','candidate_id':'a','judgment':'RELEVANCE_FOUND',
         'evidence':reading()['citations'],'rationale':'Exception is cross-cutting'}
    with pytest.raises(LegalMathError):validate_exclusions({'checks':[row],'missed_qualifications':[]},packet(),[('c','a'),('d','a')])

def test_pdf_joining_cannot_erase_substantive_changes():
    sys.path.insert(0,str(ROOT/'scripts'))
    from resolution_pdf import split_word_evidence
    w={'text':'30-day','x0':1,'x1':30,'top':1,'bottom':12}
    def issue(a,b):return {'change':{'left_tokens':a,'right_tokens':b}}
    assert split_word_evidence(issue(['30-','day'],['30-day']),[w])
    for a,b in [(['30-day'],['31-day']),(['not','permitted'],['permitted']),(['million'],['billion']),
                (['unless'],['when']),(['7-day'],['1-day']),(['now','here'],['nowhere'])]:
        assert split_word_evidence(issue(a,b),[w]) is None
    assert split_word_evidence(issue(['30-','day'],['30-day']),[w,w]) is None
