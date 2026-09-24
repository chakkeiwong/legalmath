from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import commitment
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.assurance.repair import StageHistory, RepairBudget, repair_request, compare_derived, normalized_result
from .support import packet, reading, inventory
from tests.search.test_formal import AT


def test_upstream_repair_invalidates_downstream_but_preserves_evidence():
    h=StageHistory()
    for stage in ('EXTRACTION','INTERPRETATION','FORMALIZATION','JAVA'):h.record(stage,{'v':1},{'evidence':stage})
    assert h.invalidate('FORMALIZATION','exception omitted') == [2,3]
    assert h.records[0]['valid'] and h.records[1]['valid']
    assert h.records[2]['result']=={'evidence':'FORMALIZATION'}
    h.record('FORMALIZATION',{'v':2},{'fixed':True})
    assert len(h.records)==5 and h.records[-1]['valid']


def test_repair_budget_counts_failure_and_forbids_identical_repeat():
    budget=RepairBudget(2)
    assert budget.reserve('exception','FORMALIZATION',{'v':1})['status']=='RESERVED'
    assert budget.reserve('exception','FORMALIZATION',{'v':1})['status']=='NO_NEW_EVIDENCE'
    resumed=RepairBudget(2,budget.attempts)
    assert resumed.reserve('exception','FORMALIZATION',{'v':2})['status']=='RESERVED'
    assert resumed.reserve('exception','FORMALIZATION',{'v':3})['status']=='ISSUE_REPAIR_LIMIT'


def test_missing_source_cannot_be_repaired_by_reprompting_a_rule():
    with pytest.raises(LegalMathError):repair_request(packet(),reading(),[{'stage':'DEPENDENCY'}])
    request=repair_request(packet(),reading(),[{'stage':'FORMALIZATION','kind':'missing.exception'}])
    assert request['failed_stage']=='FORMALIZATION' and request['task']=='SEMANTIC_REPAIR'


def mapped_pair():
    a=reading();b=deepcopy(a)
    offer={**deepcopy(a['formalization']['facts'][0]),'name':'offer','meaning':'Distributor makes the offer'}
    a['formalization']['facts'].append(offer)
    a['formalization']['result']='(and offer gift (not discount))'
    b['formalization']['facts'][0]['name']='offered_gift'
    b['formalization']['result']='(not (and offered_gift (not discount)))'
    common=deepcopy(a['formalization']['facts'])
    mapping={'source_packet_hash':digest(packet()),'left_commitment':commitment(a),'right_commitment':commitment(b),
        'common_facts':common,'left':{'offer':'offer','gift':'gift','discount':'discount'},
        'right':{'offered_gift':'(and offer gift)','discount':'discount'},
        'left_output':'TRUE_IS_PROHIBITED','right_output':'TRUE_IS_COMPLIANT',
        'assumptions':['The offered_gift input is the conjunction of offer and gift under the declared common domain.'],
        'evidence':inventory()['claims'][0]['evidence']}
    return a,b,mapping


def test_derived_split_facts_and_output_polarity_replay_original_java(root,tmp_path):
    a,b,m=mapped_pair();checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    result=compare_derived(a,b,packet(),m,checker)
    assert result['status']=='CONDITIONAL_EQUIVALENT_IN_DECLARED_DOMAIN' and result['cases']==64
    assert any(r['left']['java']['status']=='UNKNOWN' for r in result['rows'])
    assert any(r['left']['java']['status']=='CONFLICT' for r in result['rows'])
    assert not result['release_eligible']
    b['formalization']['result']='(not offered_gift)';m['right_commitment']=commitment(b)
    result=compare_derived(a,b,packet(),m,checker)
    assert result['status']=='CONDITIONAL_DIFFERENCE' and result['witness']['right']['java']


def test_stale_mapping_missing_binding_and_implicit_numeric_domain_rejected(root,tmp_path):
    a,b,m=mapped_pair();checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    stale=deepcopy(m);stale['source_packet_hash']='0'*64
    with pytest.raises(LegalMathError):compare_derived(a,b,packet(),stale,checker)
    bad=deepcopy(m);bad['right'].pop('discount')
    with pytest.raises(LegalMathError):compare_derived(a,b,packet(),bad,checker)
    bad=deepcopy(m);bad['common_facts'][0]['type']='date'
    with pytest.raises(LegalMathError):compare_derived(a,b,packet(),bad,checker)
    assert compare_derived(a,b,packet(),m,checker,max_cases=10)['status']=='MAPPING_DOMAIN_LIMIT'


def test_normalization_keeps_unknown_conflict_out_of_scope():
    for state in ('UNKNOWN','CONFLICT','OUT_OF_SCOPE'):
        value={'status':state,'type':'bool'}
        assert normalized_result(value,'TRUE_IS_COMPLIANT')==value


def test_declared_event_date_boundary_is_compared_in_original_java(root,tmp_path):
    a=reading();a['formalization']['facts']=[{'name':'event','type':'date','meaning':'Event date','unit':'Gregorian date',
        'source_unit_ids':['p1'],'requires_judgment':False}]
    a['formalization']['result']='(>= event (date 2026-06-01))';b=deepcopy(a);b['formalization']['result']='(> event (date 2026-06-01))'
    m={'source_packet_hash':digest(packet()),'left_commitment':commitment(a),'right_commitment':commitment(b),
       'common_facts':deepcopy(a['formalization']['facts']),'left':{'event':'event'},'right':{'event':'event'},
       'left_output':'TRUE_IS_PROHIBITED','right_output':'TRUE_IS_PROHIBITED','assumptions':['Same event date and output meanings.'],
       'evidence':inventory()['claims'][0]['evidence']}
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    result=compare_derived(a,b,packet(),m,checker,domain={'event':['2026-05-31','2026-06-01','2026-06-02','UNKNOWN','CONFLICT']})
    assert result['status']=='CONDITIONAL_DIFFERENCE'
    assert result['witness']['common_snapshot']['facts']['event']['value']=='2026-06-01'
