from copy import deepcopy
import pytest
from legalmath.prospectus.successor import calendar_facts,service
from scripts.prospectus_agent_window_evidence import independent
from test_calendar_facts import world


@pytest.mark.parametrize('convention',['CIVIL_DATE_GAP','CLEAR_CIVIL_DAYS','ELAPSED_24_HOUR_DAYS'])
@pytest.mark.parametrize('operator',['GE','LE'])
@pytest.mark.parametrize('days',[29,30,45,46])
def test_exact_operator_matches_integer_oracle(tmp_path,convention,operator,days):
    start='2024-01-01T00:00:00Z' if convention=='ELAPSED_24_HOUR_DAYS' else '2024-01-01'
    end='2024-02-15T00:00:00Z' if convention=='ELAPSED_24_HOUR_DAYS' else '2024-02-15'
    ps,data,_=world(tmp_path,start,end,days,convention)
    data['calendar_facts'][0]['operator']=operator
    p4=service.law_product(ps['P1'],ps['P3'],law_input=data)
    c=p4['payload']['question']['value'][0]['calendar_calculations'][0]
    independent(c)
    assert service.consume({**ps,'P4':p4},tmp_path,mode='current')['questions']['Q4']==p4['payload']['question']


def test_upper_microsecond_is_not_integer_complement(tmp_path):
    ps,data,_=world(tmp_path,'2024-01-01T00:00:00Z','2024-02-15T00:00:00.000001Z',45,'ELAPSED_24_HOUR_DAYS')
    data['calendar_facts'][0]['operator']='LE'
    p4=service.law_product(ps['P1'],ps['P3'],law_input=data)
    assert p4['payload']['question']['status']=='NO'
    assert independent(p4['payload']['question']['value'][0]['calendar_calculations'][0])['status']=='NO'
    start=calendar_facts.operand_value('2024-01-01T00:00:00Z','ELAPSED_24_HOUR_DAYS')
    end=calendar_facts.operand_value('2024-02-15T00:00:00.000001Z','ELAPSED_24_HOUR_DAYS')
    assert not calendar_facts.compare(start,end,'ELAPSED_24_HOUR_DAYS',46)[0]


@pytest.mark.parametrize('operator',[None,False,True,0,{},[],'','LT','ge'])
def test_invalid_operator_refused(tmp_path,operator):
    ps,data,_=world(tmp_path);data['calendar_facts'][0]['operator']=operator
    with pytest.raises(ValueError,match='operator must be'):service.law_product(ps['P1'],ps['P3'],law_input=data)


def test_different_operators_require_separate_premises(tmp_path):
    ps,data,_=world(tmp_path)
    other=deepcopy(data['calendar_facts'][0]);other.update(id='second',operator='LE')
    data['calendar_facts'].append(other)
    with pytest.raises(ValueError,match='Different calendar rules'):service.law_product(ps['P1'],ps['P3'],law_input=data)


def test_operator_does_not_weaken_source_validation(tmp_path):
    ps,data,_=world(tmp_path);data['calendar_facts'][0]['operator']='LE'
    data['calendar_facts'][0]['end']['value']='2024-03-16'
    with pytest.raises(ValueError,match='source literal'):service.law_product(ps['P1'],ps['P3'],law_input=data)
