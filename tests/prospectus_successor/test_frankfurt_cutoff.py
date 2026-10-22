"""Source-specific cutoff,timezone and complete control-put checks."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from itertools import product
import pytest
from legalmath.prospectus import frankfurt_cutoff as module
from scripts import prospectus_cutoff_oracle as oracle

NODE={'conditions':{'all':['control_put.control','control_put.rating','control_put.event_notice',
    'control_put.timely_exercise','control_put.valid_declaration','control_put.delivery','control_put.payment_day',
    {'any':[{'not':'representative.put.entrusted'},'representative.put.express_permission']}]},
    'exceptions':'control_put.earlier_tax_notice'}


@pytest.mark.parametrize('row',oracle.scenarios('bond'),ids=lambda r:r['id'])
def test_cutoff_matches_independent_integer_calendar_and_formula(row):
    assert oracle.projection(module.analyze(row,NODE,'bond'))==oracle.classify(row)


def test_complete_boolean_formula_including_tax_exception():
    for values in product((False,True),repeat=13):
        row=oracle.case('ladder');row.update(zip(oracle.QUALIFICATIONS,values[:4]))
        row['other_facts']=dict(zip(oracle.FACTS,values[4:]))
        assert oracle.projection(module.analyze(row,NODE,'bond'))==oracle.classify(row)


def test_pinned_timezone_agrees_daily_and_at_transition_instants():
    zone,_=module.timezone_model();day=datetime(2000,1,1,12,tzinfo=timezone.utc);count=0
    while day.year<=2030:
        n=oracle.instant_number(day.isoformat())
        assert day.astimezone(zone).utcoffset()==timedelta(hours=oracle.offset_hours(n));count+=1
        day+=timedelta(days=1)
    assert count==11323
    for year in range(2000,2031):
        for month in (3,10):
            last=oracle.civil_number(f'{year}-{month:02d}-31');sunday=last-((last+1)%7)
            instant=sunday*oracle.DAY+3600000000
            for delta in (-1,0,1):
                text=oracle.stamp(instant+delta);value=datetime.fromisoformat(text)
                assert value.astimezone(zone).utcoffset()==timedelta(hours=oracle.offset_hours(instant+delta))


@pytest.mark.parametrize('kind',['instrument','event','publication-role','receipt-role','override','naive',
    'precision','offset','convention','missing-convention','domain-low','domain-high','computed-domain',
    'qualification','extra','receipt-malformed-without-publication'])
def test_malformed_or_unreviewed_inputs_refuse(kind):
    row=oracle.case('bad');interval=row['interval']
    if kind=='instrument':interval['instrument_id']='other'
    elif kind=='event':interval['event_id']='other'
    elif kind=='publication-role':interval['publication']['role']='control_change'
    elif kind=='receipt-role':interval['receipt']['role']='sent_to_holder'
    elif kind=='override':row['other_facts'][module.COMPUTED]=True
    elif kind=='naive':interval['receipt']['value']='2024-02-15T17:00:00'
    elif kind=='precision':interval['receipt']['value']='2024-02-15T17:00:00.0000001+01:00'
    elif kind=='offset':interval['receipt']['value']='2024-02-15T17:00:00+01:60'
    elif kind=='convention':interval['convention']='BUSINESS_DAYS'
    elif kind=='missing-convention':interval['convention']=None
    elif kind=='domain-low':interval['publication']['value']='1999-01-01T00:00:00Z'
    elif kind=='domain-high':interval['receipt']['value']='2031-01-01T00:00:00Z'
    elif kind=='computed-domain':interval['publication']['value']='2030-12-01T12:00:00+01:00'
    elif kind=='qualification':row['timezone_basis_supported']=1
    elif kind=='extra':interval['days']=44
    else:interval['publication']=None;interval['receipt']['value']='invalid'
    with pytest.raises(ValueError):module.analyze(row,NODE,'bond')


def test_timezone_mutation_refused(monkeypatch):
    fixture=module.timezone_fixture();fixture['tzif_base64']='AAAA'
    monkeypatch.setattr(module,'timezone_fixture',lambda:fixture)
    with pytest.raises(ValueError,match='timezone bytes changed'):module.timezone_model()


def test_independent_formula_detects_omitted_tax_exception():
    row=oracle.case('tax');row['other_facts']['control_put.earlier_tax_notice']=True
    expected=oracle.classify(row);assert expected['control_put']=='NO'
    bad=deepcopy(NODE);bad['exceptions']=False
    row['other_facts'].pop('control_put.earlier_tax_notice')
    assert module.analyze(row,bad,'bond')['complete_control_put']['status']=='YES'
