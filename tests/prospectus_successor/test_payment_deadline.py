"""Thirty-day payment boundaries must preserve separate default branches."""
from copy import deepcopy
from itertools import product
import pytest
from legalmath.prospectus import payment_deadline as module
from scripts import prospectus_payment_oracle as oracle
from scripts import prospectus_amount_oracle as money_oracle

NODES={'a':{'conditions':{'all':['default.notice','default.a.payment30',{'not':'default.a.cured'},
    {'any':[{'not':'representative.a.entrusted'},'representative.a.express_permission']}]},'exceptions':False},
    'c':{'conditions':{'all':['default.notice',{'any':['default.c.accelerated',
        {'all':['default.c.overdue',{'not':'default.c.disputed'}]},'default.c.security']},
        {'not':'default.c.cured'},{'any':['default.quorum','default.other_at_receipt']},
        {'any':[{'not':'representative.c.entrusted'},'representative.c.express_permission']}]},'exceptions':False}}


@pytest.mark.parametrize('row',oracle.scenarios('bond'),ids=lambda r:r['id'])
def test_payment_clock_and_complete_formula_match_independent_oracle(row):
    assert oracle.projection(module.analyze(row,NODES,'bond'))==oracle.classify(row)


def test_complete_finite_a_and_c_formulas():
    count=0
    for values in product((False,True),repeat=8):
        row=oracle.case('a-ladder');row.update(zip((*oracle.QUALIFICATIONS,'qualified_note_payment'),values[:4]))
        row['other_facts']=dict(zip(oracle.FACTS,values[4:]))
        assert oracle.projection(module.analyze(row,NODES,'bond'))==oracle.classify(row);count+=1
    for values in product((False,True),repeat=9):
        row=oracle.case('c-ladder',route='c');row['amount_scenario']['other_facts']=dict(zip(money_oracle.FACTS,values))
        assert oracle.projection(module.analyze(row,NODES,'bond'))==oracle.classify(row);count+=1
    assert count==768


@pytest.mark.parametrize('kind',['clock-instrument','event','guarantee-a','wrong-role','state',
    'missing-payment','unexpected-payment','future-payment','early-assessment','naive','precision','offset',
    'missing-convention','civil-offset','irrelevant-offset','a-override','c-override','amount-event',
    'cross-other-facts','bad-qualification','overflow'])
def test_invalid_or_overridden_payment_input_refuses(kind):
    row=oracle.case('bad',route='c' if kind in ('c-override','amount-event','cross-other-facts') else 'a');clock=row['clock']
    if kind=='clock-instrument':clock['instrument_id']='other'
    elif kind=='event':clock['event_id']='other'
    elif kind=='guarantee-a':row['trigger_kind']='GUARANTEE_INVOCATION';clock['trigger']['role']='GUARANTEE_INVOCATION'
    elif kind=='wrong-role':clock['trigger']['role']='ASSESSMENT'
    elif kind=='state':row['payment_state']={}
    elif kind=='missing-payment':row['payment_state']='FULL_PAYMENT'
    elif kind=='unexpected-payment':clock['payment']={'value':'2024-01-01T00:00:00Z','role':'FULL_PAYMENT'}
    elif kind=='future-payment':
        row['payment_state']='FULL_PAYMENT';clock['payment']={'value':'2025-01-01T00:00:00Z','role':'FULL_PAYMENT'}
    elif kind=='early-assessment':clock['assessment']['value']='2023-12-31T00:00:00Z'
    elif kind=='naive':clock['assessment']['value']='2024-02-02T00:00:00'
    elif kind=='precision':clock['trigger']=None;clock['assessment']['value']='2024-02-02T00:00:00.0000001Z'
    elif kind=='offset':clock['assessment']['value']='2024-02-02T00:00:00+01:60'
    elif kind=='missing-convention':clock['convention']=None
    elif kind=='civil-offset':clock['convention']='FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE';clock['utc_offset']='+25:00'
    elif kind=='irrelevant-offset':clock['utc_offset']='+00:00'
    elif kind=='a-override':row['other_facts']['default.a.payment30']=True
    elif kind=='c-override':row['amount_scenario']['thirty_day_condition']=True
    elif kind=='amount-event':row['amount_scenario']['id']='other'
    elif kind=='cross-other-facts':row['other_facts']={}
    elif kind=='bad-qualification':row['source_trigger_supported']=1
    else:clock['trigger']['value']='9999-12-20T00:00:00Z';clock['assessment']=None
    with pytest.raises(ValueError):module.analyze(row,NODES,'bond')


def test_civil_offset_equivalence():
    row=oracle.case('offset',convention='FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE',
        trigger='2024-01-01T12:00:00+05:30',assessment='2024-02-01T00:00:00+05:30')
    row['clock']['utc_offset']='+05:30'
    assert oracle.projection(module.analyze(row,NODES,'bond'))==oracle.classify(row)
    assert module.analyze(row,NODES,'bond')['failure_within_declared_window'] is True


def test_late_full_payment_does_not_remove_separate_cure_requirement():
    row=next(r for r in oracle.scenarios('bond') if r['id']=='late-paid')
    assert module.analyze(row,NODES,'bond')['complete_default']['status']=='YES'
    row['other_facts']['default.a.cured']=True
    result=module.analyze(row,NODES,'bond')
    assert result['failure_within_declared_window'] is True
    assert result['complete_default']['status']=='NO'
