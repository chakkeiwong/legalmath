from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import pytest
from legalmath.errors import LegalMathError
from .support import packet,reading

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_evaluate import validate_mappings,replay_mappings,assess_case_arm,AT


def value():
    return {'mappings':[{'case_id':'c','candidate_id':'r','alignment':'SAME_BOOLEAN_QUESTION',
        'facts':[{'name':n,'status':'KNOWN','value':'true','rationale':'Stipulated'} for n in ('gift','discount')],
        'rationale':'Same conditional question','source_evidence':reading()['citations'],'assumptions':[]}], 'unresolved':[]}


@pytest.mark.parametrize('mutation',['missing_fact','invented_fact','missing_pair','unbound_quote','false_known','unencoded','different_question_snapshot'])
def test_evaluation_does_not_repair_the_program_or_hide_missing_bindings(mutation):
    v=value();rs={'r':reading()};row=v['mappings'][0]
    if mutation=='missing_fact':row['facts'].pop()
    elif mutation=='invented_fact':row['facts'][0]['name']='overall_compliant'
    elif mutation=='missing_pair':v['mappings']=[]
    elif mutation=='unbound_quote':row['source_evidence'][0]['quote']='not in the source'
    elif mutation=='false_known':row['facts'][0]['value']=None
    elif mutation=='unencoded':rs['r']['formalization']=None
    elif mutation=='different_question_snapshot':row['alignment']='DIFFERENT_OR_UNENCODED_QUESTION'
    with pytest.raises(LegalMathError):validate_mappings(v,packet(),rs,[{'case_id':'c'}])


def test_unaligned_reading_is_retained_without_fabricated_facts():
    v=value();row=v['mappings'][0];row['alignment']='DIFFERENT_OR_UNENCODED_QUESTION';row['facts']=[]
    assert validate_mappings(v,packet(),{'r':reading()},[{'case_id':'c'}])==v


def test_all_frozen_circular_case_identifiers_are_accepted_only_when_requested():
    import json
    root=Path(__file__).resolve().parents[2]
    cases=json.loads((root/'artifacts/assurance-successor/2026-09-28/conditional-case-reference.json').read_text())['cases']
    for case in cases:
        v=value();v['mappings'][0]['case_id']=case['case_id']
        assert validate_mappings(v,packet(),{'r':reading()},[case])==v
        with pytest.raises(LegalMathError):validate_mappings(v,packet(),{'r':reading()},[{'case_id':'unrequested'}])


def test_numeric_circular_reference_reaches_the_actual_java_program(tmp_path):
    from legalmath.interpretation.search.formal import Comparisons
    root=Path(__file__).resolve().parents[2]
    v=value();v['mappings'][0]['case_id']='26ec55.equal.threshold'
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    result=replay_mappings(v,packet(),{'r':reading()},checker)[0]
    assert result['case_id']=='26ec55.equal.threshold'
    assert result['replay']['java']['status']=='FALSE'


@pytest.mark.parametrize('row',[
    {'alignment':'DIFFERENT_OR_UNENCODED_QUESTION','answer':'NOT_ESTABLISHED'},
    {'alignment':'SAME_BOOLEAN_QUESTION','answer':'NOT_ESTABLISHED'},
    {'alignment':'SAME_BOOLEAN_QUESTION','answer':'NOT_ESTABLISHED','replay':{'java':{'status':'ERROR'}}}])
def test_missing_or_failed_program_is_not_credited_as_correct_abstention(row):
    result=assess_case_arm([row],'NOT_ESTABLISHED')
    assert not result['compatible_answer_retained'] and result['aligned_executed_count']==0


def test_actual_conditional_abstention_and_contrary_alternative_stay_distinct():
    unknown={'alignment':'SAME_BOOLEAN_QUESTION','answer':'NOT_ESTABLISHED','replay':{'java':{'status':'UNKNOWN'}}}
    contrary={'alignment':'SAME_BOOLEAN_QUESTION','answer':'TRUE','replay':{'java':{'status':'TRUE'}}}
    result=assess_case_arm([unknown,contrary],'NOT_ESTABLISHED')
    assert result['compatible_answer_retained'] and result['contrary_decisive_proposals']==['TRUE']
