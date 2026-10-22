"""Independent dates and exact fractions for an explicitly declared coupon anchor."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
import pytest
from legalmath.prospectus.successor import contract_assembly, contract_terms, service, source_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.coupon_dates import anchored_date, lattice_index
from legalmath.prospectus.successor.fixed_coupon import calculate, year_fraction
from scripts.prospectus_closure_fixtures import anchored_direct_fixture, anchored_selected_fixture, full_term_fixture

ANCHOR='2023-08-30'
DATES=['2023-08-30','2024-02-29','2024-08-30','2025-02-28']
REFERENCES=[{'start':a,'end':b} for a,b in zip(DATES,DATES[1:])]


def fraction(start,end,refs,**kwargs):
    return year_fraction(start,end,'ACT_ACT_ICMA',references=refs,frequency=2,eom=False,**kwargs)


def scenario(tmp_path):
    request=anchored_direct_fixture(tmp_path)
    return source_graph.build(request['bundle'],tmp_path),request['financial_scenario']


def accrual(value,start,end,stub,refs):
    value.update(accrual_start=start,accrual_end=end,due_date=end,payment_date=end,stub=stub,references=deepcopy(refs))
    value.pop('fixed_coupon_amount',None)
    value['evidence'].pop('fixed_coupon_amount',None)
    for event in value['events']:
        event['at']=(start if event['kind']=='accrual_start' else end)+'T00:00:00Z'


def test_coupon_anchor_reproduced_regular_and_legacy_boundary():
    for start,end,refs,expected in (
        ('2024-02-29','2024-08-30',REFERENCES[1:2],Fraction(1,2)),
        ('2023-08-30','2024-08-30',REFERENCES[:2],Fraction(1))):
        with pytest.raises(ValueError,match='regular periods'):
            fraction(start,end,refs)
        assert fraction(start,end,refs,coupon_anchor=ANCHOR)==expected
    assert contract_terms.regular_schedule('2023-08-30','2024-02-29','2024-08-30',2,False,'REGULAR')==DATES[1:3]
    assert contract_terms.regular_schedule('2024-02-29','2024-08-30','2025-02-28',2,False,'REGULAR',coupon_anchor=ANCHOR)==DATES[2:]
    assert fraction('2024-02-29','2024-08-29',[{'start':'2024-02-29','end':'2024-08-29'}])==Fraction(1,2)


@pytest.mark.parametrize('anchor,frequency,eom,expected',[
    ('2023-08-28',2,False,['2024-02-28','2024-08-28']),
    ('2023-08-29',2,False,['2024-02-29','2024-08-29']),
    ('2023-08-30',2,False,['2024-02-29','2024-08-30','2025-02-28']),
    ('2023-08-31',2,False,['2024-02-29','2024-08-31','2025-02-28']),
    ('2024-01-31',4,False,['2024-04-30','2024-07-31','2024-10-31','2025-01-31']),
    ('2024-02-29',4,True,['2024-05-31','2024-08-31','2024-11-30','2025-02-28']),
    ('2023-02-28',1,False,['2024-02-28','2025-02-28']),
    ('2023-02-28',1,True,['2024-02-29','2025-02-28']),
    ('2024-02-29',1,False,['2025-02-28','2026-02-28','2027-02-28','2028-02-29'])])
def test_coupon_anchor_independently_listed_dates(anchor,frequency,eom,expected):
    assert [anchored_date(anchor,n*(12//frequency),eom).isoformat() for n in range(1,len(expected)+1)]==expected
    assert contract_terms.regular_schedule(anchor,expected[0],expected[-1],frequency,eom,'REGULAR',coupon_anchor=anchor)==expected
    if len(expected)>1:
        assert contract_terms.regular_schedule(expected[0],expected[1],expected[-1],frequency,eom,'REGULAR',coupon_anchor=anchor)==expected[1:]
    refs=[{'start':a,'end':b} for a,b in zip([anchor]+expected,expected)]
    assert year_fraction(anchor,expected[-1],'ACT_ACT_ICMA',references=refs,frequency=frequency,eom=eom,coupon_anchor=anchor)==Fraction(len(expected),frequency)


@pytest.mark.parametrize('anchor',['20230830','2023-02-29','2023-13-01','not-a-date',30,True])
def test_coupon_anchor_malformed_date_rejected(anchor):
    with pytest.raises(ValueError):
        fraction('2024-02-29','2024-08-30',REFERENCES[1:2],coupon_anchor=anchor)


@pytest.mark.parametrize('refs',[
    [{'start':'2024-02-29','end':'2024-08-29'}],
    [{'start':'2024-02-29','end':'2024-08-31'}],
    [{'start':'2024-02-29','end':'2024-09-30'}],
    [{'start':'2024-02-28','end':'2024-08-30'}],
    [{'start':'2023-08-30','end':'2024-02-29'},{'start':'2024-08-30','end':'2025-02-28'}],
    [{'start':'2023-08-30','end':'2024-02-29'},{'start':'2023-08-30','end':'2024-02-29'}],
    [{'start':'2024-02-29','end':'2024-08-30'},{'start':'2023-08-30','end':'2024-02-29'}],
    [{'start':'2023-08-30','end':'2024-02-29'}]])
def test_coupon_anchor_wrong_dates_gaps_overlap_and_coverage_rejected(refs):
    with pytest.raises(ValueError):
        fraction('2023-08-30','2024-08-30',refs,coupon_anchor=ANCHOR)


@pytest.mark.parametrize('frequency,eom',[(True,False),(5,False),(4,False),(2,'false')])
def test_coupon_anchor_explicit_conventions_required(frequency,eom):
    with pytest.raises(ValueError):
        year_fraction('2024-02-29','2024-08-30','ACT_ACT_ICMA',references=REFERENCES[1:2],frequency=frequency,eom=eom,coupon_anchor=ANCHOR)


def test_coupon_anchor_negative_lattice_index_and_mismatched_start():
    assert lattice_index('2023-08-30','2024-08-30',2,False)==-2
    assert anchored_date('2024-08-30',-6,False).isoformat()=='2024-02-29'
    for start in ('2024-02-28','2024-03-30'):
        with pytest.raises(ValueError,match='lattice'):
            contract_terms.regular_schedule(start,'2024-08-30','2025-02-28',2,False,'REGULAR',coupon_anchor=ANCHOR)


@pytest.mark.parametrize('stub,start,end,overlap_days,denominator_days,expected',[
    ('SHORT_FIRST','2023-12-30','2024-02-29',[61],[183],Fraction(1,6)),
    ('LONG_FIRST','2023-11-30','2024-08-30',[91,183],[183,183],Fraction(137,183)),
    ('SHORT_FINAL','2024-02-29','2024-05-30',[91],[183],Fraction(91,366)),
    ('LONG_FINAL','2024-02-29','2024-11-30',[183,92],[183,182],Fraction(137,182))])
def test_coupon_anchor_independent_stub_oracles(tmp_path,stub,start,end,overlap_days,denominator_days,expected):
    # Enumerate days on the independently listed dates, never a production helper.
    refs=REFERENCES[:1] if stub=='SHORT_FIRST' else REFERENCES[:2] if stub=='LONG_FIRST' else REFERENCES[1:2] if stub=='SHORT_FINAL' else REFERENCES[1:]
    assert [(date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days for r in refs]==denominator_days
    assert [(min(date.fromisoformat(end),date.fromisoformat(r['end']))-max(date.fromisoformat(start),date.fromisoformat(r['start']))).days for r in refs]==overlap_days
    assert sum((Fraction(n,2*d) for n,d in zip(overlap_days,denominator_days)),Fraction())==expected
    assert fraction(start,end,refs,coupon_anchor=ANCHOR)==expected
    graph,value=scenario(tmp_path)
    accrual(value,start,end,stub,refs)
    output=calculate(value,graph)
    assert output['day_fraction']==str(expected)
    assert output['actual_event']=='NOT_ESTABLISHED' and not output['full_settlement_supported']


@pytest.mark.parametrize('stub,start,end',[
    ('REGULAR','2023-11-30','2024-05-31'),
    ('SHORT_FIRST','2024-03-30','2024-05-30'),
    ('SHORT_FINAL','2024-03-30','2024-05-30'),
    ('LONG_FIRST','2023-11-30','2024-11-30'),
    ('LONG_FINAL','2023-11-30','2024-11-30')])
def test_coupon_anchor_fraction_does_not_prove_stub_classification(tmp_path,stub,start,end):
    graph,value=scenario(tmp_path)
    accrual(value,start,end,stub,REFERENCES)
    if stub=='REGULAR':
        assert fraction(start,end,REFERENCES,coupon_anchor=ANCHOR)==Fraction(1,2)
    with pytest.raises(ValueError,match='classification'):
        calculate(value,graph)


@pytest.mark.parametrize('selected',[False,True])
def test_coupon_anchor_both_real_service_routes(tmp_path,selected):
    request=(anchored_selected_fixture if selected else anchored_direct_fixture)(tmp_path)
    report=service.assess(request,tmp_path)
    answer=report['questions']['Q5']
    assert answer['status']=='CONDITIONAL'
    value=answer['value']
    calculation=value['calculation'] if selected else value
    assert calculation['day_fraction']=='1/2' and calculation['coupon_anchor']==ANCHOR
    assert [p['amount'] for p in calculation['transfers']]==['5','5/2']
    assert calculation['source_evidence']['coupon_anchor']['source']['quote']=='30 August 2023'
    assert calculation['actual_event']=='NOT_ESTABLISHED' and not calculation['full_settlement_supported']
    if selected:
        assert value['regular_due_dates']==['2024-08-30','2025-02-28','2025-08-30']
        assert value['contract_terms']['version']=='admitted-coupon-terms.v2'
        assert value['contract_terms']['terms']['coupon_anchor']['value']==ANCHOR
    p1=service.source_product(request,tmp_path)
    p2=service.construction_product(p1,tmp_path)
    p3=service.interpretation_product(p1,p2)
    products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
    assert service.consume(products,tmp_path,mode='current')['questions']==report['questions']


@pytest.mark.parametrize('change',['missing_anchor','changed_anchor','missing_evidence','unrelated_quote','foreign_edition','legacy_profile','wrong_convention','null_anchor'])
def test_coupon_anchor_direct_service_rejects_unbound_or_wrong_version(tmp_path,change):
    request=anchored_direct_fixture(tmp_path)
    value=request['financial_scenario']
    if change=='missing_anchor': value.pop('coupon_anchor')
    elif change=='changed_anchor': value['coupon_anchor']='2023-08-29'
    elif change=='null_anchor': value['coupon_anchor']=None
    elif change=='missing_evidence': value['evidence'].pop('coupon_anchor')
    elif change=='unrelated_quote': value['evidence']['coupon_anchor']=deepcopy(value['evidence']['calendar'])
    elif change=='foreign_edition': value['evidence']['coupon_anchor']['source']['source_sha256']='0'*64
    elif change=='legacy_profile': value['profile']='fixed-coupon.v1'
    elif change=='wrong_convention': value['day_count']='ACT_365_FIXED'
    assert service.assess(request,tmp_path)['questions']['Q5']['status']=='UNSUPPORTED'


@pytest.mark.parametrize('change',['missing_anchor','changed_anchor','wrong_rule','invented_quote','foreign_edition','excluded_source','legacy_packet','legacy_profile','override_anchor'])
def test_coupon_anchor_selected_source_and_version_rejections(tmp_path,change):
    request=anchored_selected_fixture(tmp_path)
    packet=request['term_interpretations']
    row=packet['terms']['coupon_anchor']
    if change=='missing_anchor': packet['terms'].pop('coupon_anchor')
    elif change=='changed_anchor': row['value']='2023-08-29'
    elif change=='wrong_rule': row['rule']='reviewed-convention'
    elif change=='invented_quote': row['source']['quote']='29 August 2023'
    elif change=='foreign_edition': row['source']['source_sha256']='0'*64
    elif change=='legacy_packet': packet['version']='selected-coupon-terms.v2'
    elif change=='legacy_profile': request['contract_calculation']['premises']['profile']='fixed-coupon.v1'
    elif change=='override_anchor': request['contract_calculation']['premises']['coupon_anchor']=ANCHOR
    elif change=='excluded_source':
        next(r for r in request['assembly']['operations'] if r['unit']==row['use'])['role']='EXCLUDED'
        graph=source_graph.build(request['bundle'],tmp_path)
        packet['assembly_sha256']=digest(contract_assembly.assemble(graph,request['assembly']))
    with pytest.raises(ValueError):
        service.assess(request,tmp_path)


def test_coupon_anchor_legacy_selected_profile_cannot_borrow_new_anchor(tmp_path):
    request=full_term_fixture(tmp_path)
    value=request['contract_calculation']['premises']
    value.update(profile='fixed-coupon.v2',coupon_anchor='2024-01-01')
    with pytest.raises(ValueError,match='matching calculation profile'):
        service.assess(request,tmp_path)


def test_coupon_anchor_selected_path_remains_regular_only(tmp_path):
    request=anchored_selected_fixture(tmp_path)
    graph=source_graph.build(request['bundle'],tmp_path)
    assembly=contract_assembly.assemble(graph,request['assembly'])
    packet=request['term_interpretations']
    packet['terms']['stub']['value']='LONG_FIRST'
    packet['terms']['accrual_start']['value']='2023-08-30'
    packet['terms']['accrual_start']['source']=deepcopy(packet['terms']['coupon_anchor']['source'])
    packet['terms']['accrual_start']['use']=packet['terms']['coupon_anchor']['use']
    packet['terms']['references']['value']=deepcopy(REFERENCES[:2])
    # A published amount cannot be supplied for a non-regular coupon, and the
    # selected profile also rejects stub schedules; neither is broadened here.
    admitted=contract_terms.admit(graph,assembly,packet)
    request['contract_calculation']['terms_sha256']=digest(admitted)
    request['contract_calculation']['premises']['events'][0]['at']='2023-08-30T00:00:00Z'
    with pytest.raises(ValueError,match='Published fixed coupon'):
        service.assess(request,tmp_path)
    with pytest.raises(ValueError,match='no stub'):
        contract_terms.regular_schedule('2023-11-30','2024-08-30','2025-08-30',2,False,'LONG_FIRST',coupon_anchor=ANCHOR)


@pytest.mark.parametrize('field,invalid', [('quantum', 0), ('quantum', '1/0'), ('rule', [])])
@pytest.mark.parametrize('entitled', [True, False])
@pytest.mark.parametrize('aggregation', ['PER_LEGAL_HOLDER', 'PER_CALCULATION_AMOUNT'])
def test_coupon_anchor_rounding_domain_before_entitlement(tmp_path, field, invalid, entitled, aggregation):
    req = anchored_direct_fixture(tmp_path)
    supplied = req['financial_scenario']
    supplied['rounding']['aggregation'] = aggregation
    if aggregation == 'PER_LEGAL_HOLDER':
        for key in ['calculation_amount', 'fixed_coupon_amount']:
            supplied.pop(key)
            supplied['evidence'].pop(key)
    for row in supplied['holdings']:
        row['entitled'] = entitled
    assert service.assess(req, tmp_path)['questions']['Q5']['status'] == 'CONDITIONAL'
    supplied['rounding'][field] = invalid
    before = deepcopy(req)
    answer = service.assess(req, tmp_path)['questions']['Q5']
    assert answer['status'] == 'UNSUPPORTED'
    assert 'rounding' in ' '.join(answer['unresolved'])
    assert req == before
