"""Source causation,withdrawal/downgrade alternatives and composed exercise checks."""
from copy import deepcopy
from itertools import product
import pytest
from legalmath.prospectus import causal_rating as module
from scripts import prospectus_rating_oracle as oracle

NODE={'conditions':{'all':['control_put.control','control_put.rating','control_put.event_notice',
    'control_put.timely_exercise','control_put.valid_declaration','control_put.delivery','control_put.payment_day',
    {'any':[{'not':'representative.put.entrusted'},'representative.put.express_permission']}]},'exceptions':'control_put.earlier_tax_notice'}


@pytest.mark.parametrize('row',oracle.scenarios('bond'),ids=lambda r:r['id'])
def test_rating_and_complete_source_formula_matches_independent_oracle(row):
    assert oracle.projection(module.analyze(row,NODE,'bond'))==oracle.classify(row)


def test_finite_causal_and_full_formula_cases():
    count=0
    for action in ('WITHDRAWAL','DOWNGRADE'):
        for values in product((False,True),repeat=6):
            row=oracle.case('causal',action=action);row.update(zip(oracle.QUALIFICATIONS,values[:5]));row['causal_link']['value']=values[5]
            assert oracle.projection(module.analyze(row,NODE,'bond'))==oracle.classify(row);count+=1
    for values in product((False,True),repeat=9):
        row=oracle.case('full');row['other_facts']=dict(zip(oracle.FACTS,values))
        assert oracle.projection(module.analyze(row,NODE,'bond'))==oracle.classify(row);count+=1
    assert count==640


@pytest.mark.parametrize('kind',['instrument','same-events','date-event','date-role','link-kind','link-event',
    'link-instrument','link-value','grade','action','convention','missing-convention','precision',
    'override','cutoff-override','cutoff-id','cutoff-other-facts','qualification'])
def test_unbound_or_malformed_inputs_refuse(kind):
    row=oracle.case('bad')
    if kind=='instrument':row['events']['instrument_id']='other'
    elif kind=='same-events':row['events']['rating_event_id']=row['events']['control_event_id']
    elif kind=='date-event':row['events']['rating']['event_id']='other'
    elif kind=='date-role':row['events']['rating']['role']='CONTROL_CHANGE'
    elif kind=='link-kind':row['causal_link']['kind']='ACTUAL_SOURCE_ATTRIBUTION'
    elif kind=='link-event':row['causal_link']['rating_event_id']='other'
    elif kind=='link-instrument':row['causal_link']['instrument_id']='other'
    elif kind=='link-value':row['causal_link']['value']=1
    elif kind=='grade':row['before_grade']='BBB-'
    elif kind=='action':row['rating_action']='DOWN'
    elif kind=='convention':row['events']['convention']='BUSINESS_DAYS'
    elif kind=='missing-convention':row['events']['convention']=None
    elif kind=='precision':
        row['events']['control']=None;row['events']['convention']='ELAPSED_24_HOUR_DAYS'
        row['events']['rating']['value']='2024-04-30T00:00:00.0000001Z'
    elif kind=='override':row['other_facts']['control_put.rating']=True
    elif kind.startswith('cutoff'):
        row=next(r for r in oracle.scenarios('bond') if r['id']=='composed-timely')
        if kind=='cutoff-override':row['other_facts']['control_put.timely_exercise']=True
        elif kind=='cutoff-id':row['cutoff_scenario']['id']='other'
        else:row['cutoff_scenario']['other_facts']={'control_put.rating':True}
    else:row['agency_qualified']=1
    with pytest.raises(ValueError):module.analyze(row,NODE,'bond')


def test_chronology_does_not_substitute_for_causal_evidence():
    row=oracle.case('chronology');row['causal_link']=None
    result=module.analyze(row,NODE,'bond')
    assert result['within_120_day_window'] is True
    assert result['derived_rating']['status']=='UNKNOWN'
    assert result['complete_control_put']['status']=='UNKNOWN'


def test_withdrawal_does_not_inherit_downgrade_grade_restriction():
    row=oracle.case('withdrawal',action='WITHDRAWAL');row['before_grade']='NON_INVESTMENT_GRADE'
    row['after_grade']='UNKNOWN';row['grade_classification_supported']=None
    assert module.analyze(row,NODE,'bond')['derived_rating']['status']=='YES'
    row['rating_action']='DOWNGRADE'
    assert module.analyze(row,NODE,'bond')['derived_rating']['status']=='NO'
