"""Raw rating boundaries must drive the real conditional event calculation."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import rating_labels as module

@pytest.mark.parametrize('name,investment,noninvestment',[
    ('S&P','BBB-','BB+'),('S&P Global Ratings Europe Limited','BBB-','BB+'),
    ("Moody's",'Baa3','Ba1'),("Moody's Deutschland GmbH",'Baa3','Ba1'),
    ('Fitch','BBB-','BB+'),('Fitch Ratings Ireland Limited','BBB-','BB+')])
def test_exact_source_thresholds(name,investment,noninvestment):
    got=module.classify(name,investment,noninvestment)
    assert got['agency']['qualified'] is True
    assert got['before']['category']=='INVESTMENT_GRADE'
    assert got['after']['category']=='NON_INVESTMENT_GRADE'

@pytest.mark.parametrize('name,before,after',[
    ('S&P','Baa3','Ba1'),("Moody's",'BBB-','BB+'),('Fitch','Baa3','Ba1'),
    ('s&p','BBB-','BB+'),('S&P ','BBB-','BB+'),('successor','BBB-','BB+'),
    ('S&P','AAA','CCC'),('S&P','BBB- ','BB+ (negative)'),('Fitch','BBB-(sf)','BB+(sf)'),
    (None,'BBB-','BB+'),('S&P',None,None),('','','')])
def test_unlisted_labels_remain_unknown(name,before,after):
    result=module.classify(name,before,after)
    assert result['before']['category']==result['after']['category']=='UNKNOWN'

@pytest.mark.parametrize('bad',[True,2,[],{},'x'*257])
def test_malformed_observations_refused(bad):
    with pytest.raises(ValueError):module.classify('S&P',bad,'BB+')

def case():
    return {'id':'example','kind':'HYPOTHETICAL_DEVELOPMENT','template':'unit',
        'agency_label':'S&P','before_label':'BBB-','after_label':'BB+',
        'scenario':{'id':'example','kind':'HYPOTHETICAL_DEVELOPMENT',
            'events':{'instrument_id':'bond','control_event_id':'control','rating_event_id':'rating',
                'control':{'event_id':'control','role':'CONTROL_CHANGE','value':'2024-01-01'},
                'rating':{'event_id':'rating','role':'RATING_EVENT','value':'2024-01-02'},'convention':'CIVIL_DATE_GAP'},
            'rating_action':'DOWNGRADE','rating_subject_qualified':True,'previously_assigned':True,
            'counting_convention_supported':True,
            'causal_link':{'kind':'HYPOTHETICAL_CAUSAL_LINK','instrument_id':'bond','control_event_id':'control',
                'rating_event_id':'rating','value':True},'cutoff_scenario':None,'other_facts':{'earlier_tax_notice':False}}}

def test_raw_labels_change_downstream_event_without_fabricating_cause():
    node={'conditions':'control_put.rating','exceptions':'earlier_tax_notice'}
    raw=case();before=deepcopy(raw)
    assert module.analyze(raw,node,'bond')['rating_evaluation']['complete_control_put']['status']=='YES'
    assert raw==before
    raw['before_label']='AAA'
    assert module.analyze(raw,node,'bond')['rating_evaluation']['complete_control_put']['status']=='UNKNOWN'
    raw['before_label']='BBB-';raw['scenario']['causal_link']=None
    assert module.analyze(raw,node,'bond')['rating_evaluation']['complete_control_put']['status']=='UNKNOWN'
    raw['scenario']['other_facts']['earlier_tax_notice']=True
    assert module.analyze(raw,node,'bond')['rating_evaluation']['complete_control_put']['status']=='NO'

def test_withdrawal_does_not_require_known_grades():
    raw=case();raw.update(before_label=None,after_label=None);raw['scenario']['rating_action']='WITHDRAWAL'
    node={'conditions':'control_put.rating','exceptions':'earlier_tax_notice'}
    assert module.analyze(raw,node,'bond')['rating_evaluation']['complete_control_put']['status']=='YES'

@pytest.mark.parametrize('field',['agency_qualified','before_grade','after_grade','grade_classification_supported'])
def test_derived_premise_override_refused(field):
    raw=case();raw['scenario'][field]=True
    with pytest.raises(ValueError):module.analyze(raw,{},'bond')
