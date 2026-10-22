from copy import deepcopy
from itertools import product
import pytest
from legalmath.prospectus.publication_routes import analyze,routes,ROUTE
from scripts.prospectus_publication_oracle import route,expected,scenarios


def test_all_four_valued_publication_routes():
    keys=(*ROUTE,'statutory_conditions')
    for combination in product((True,False,None,'conflict'),repeat=5):
        values=dict(zip(keys,combination))
        assert {k:v['status'] for k,v in routes(values).items()}==route(values)


@pytest.mark.parametrize('row',scenarios('instrument'),ids=lambda r:r['id'])
def test_source_qualified_publication_cases(row):
    actual=analyze(row,'instrument');wanted=expected(row)
    for name in ('qualified_information','statutory_conditions'):
        assert actual[name]['status']==wanted[name]
    for name in ('german_seat_routes','conditional_contract_readings'):
        assert {k:v['status'] for k,v in actual[name].items()}==wanted[name]
    assert actual['actual_publication']=='NOT_ESTABLISHED'
    assert actual['selected_interpretation'] is None


def test_alternative_scope_is_not_silently_selected():
    row=next(r for r in scenarios('instrument') if r['id']=='interpretations-diverge')
    actual=analyze(row,'instrument')['conditional_contract_readings']
    assert actual['broad_replacement']['status']=='YES'
    assert actual['section13_retained']['status']=='NO'


@pytest.mark.parametrize('kind',('share','wrong-instrument','missing-regulator','raw-seat-override','empty-resolution'))
def test_refuse_scope_and_missing_duties(kind):
    row=deepcopy(scenarios('instrument')[1])
    if kind=='share':row['identity']['security_kind']='SHARE'
    elif kind=='wrong-instrument':row['identity']['instrument_id']='other'
    elif kind=='missing-regulator':row['premises'].pop('simultaneous_bafin_notification')
    elif kind=='raw-seat-override':row['premises']['inlandsemittent']=True
    else:row['identity']['resolution_id']=''
    with pytest.raises(ValueError):analyze(row,'instrument')
