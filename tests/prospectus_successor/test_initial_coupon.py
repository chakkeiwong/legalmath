"""Initial coupon interfaces: exact arithmetic, form separation and selected sources."""
from copy import deepcopy
from fractions import Fraction
import pytest
from scripts.prospectus_closure_fixtures import request, REVIEW
from legalmath.prospectus.successor import contract_assembly, contract_terms, occurrences, service, source_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.coupon_amounts import quoted_amount


def fixture(tmp_path, *, selected=False, form='DEFINITIVE', short=False):
    s = {'profile':'fixed-coupon.v3','premise_kind':'HYPOTHETICAL','currency':'GBP','annual_rate':'0.01',
         'accrual_start':'2020-09-10','accrual_end':'2021-12-10','due_date':'2021-12-10','payment_date':'2021-12-10',
         'coupon_anchor':'2021-12-10','day_count':'ACT_ACT_ICMA',
         'references':[{'start':'2019-12-10','end':'2020-12-10'},{'start':'2020-12-10','end':'2021-12-10'}],
         'frequency':1,'eom':False,'stub':'LONG_FIRST','adjustment':'UNADJUSTED',
         'calculation_amount':'1000','fixed_coupon_amount':'10','broken_coupon_amount':'12.49','note_form':form,
         'calendar':{'edition':'Synthetic calendar','valid_from':'2021-12-01','valid_until':'2021-12-20',
                     'holidays':[],'weekend':[5,6],'coverage':'COMPLETE_DECLARED_INTERVAL'},
         'rounding':{'quantum':'0.01','rule':'HALF_UP','aggregation':'PER_LEGAL_HOLDER' if form=='GLOBAL' else 'PER_CALCULATION_AMOUNT'},
         'holdings':[{'legal_holder_id':'hypothetical','account_id':'declared','principal':'500000000' if form=='GLOBAL' else '100000','entitled':True}],
         'event_scope':{k:'REQUIRED' if k in {'accrual_start','accrual_end','determination','payment'} else 'NOT_APPLICABLE'
                        for k in ('accrual_start','accrual_end','notice','observation','determination','record','ex_coupon','payment')},
         'events':[{'id':k,'kind':k,'at':day+'T00:00:00Z','order':order} for k,day,order in (
             ('accrual_start','2020-09-10',0),('accrual_end','2021-12-10',0),('determination','2021-12-10',1),('payment','2021-12-10',2))]}
    if short:
        s.update(accrual_start='2021-09-10',stub='SHORT_FIRST',broken_coupon_amount='2.49',references=[{'start':'2020-12-10','end':'2021-12-10'}])
        s['events'][0]['at']='2021-09-10T00:00:00Z'
    names = sorted(contract_terms.REQUIRED | contract_terms.EXTENDED | {'coupon_anchor','note_form','broken_coupon_amount'})
    values = {k:s[k] for k in names if k in s}
    values.update(issue_principal='500000000',maturity_date='2030-12-10')
    quotes = {'currency':'Pound Sterling ("£")','annual_rate':'1.000 per cent.','frequency':'in each year',
              'issue_principal':'£500,000,000','calculation_amount':'£1,000','fixed_coupon_amount':'£10.00','broken_coupon_amount':'£12.49',
              'accrual_start':'10 September 2020','accrual_end':'10 December 2021','due_date':'10 December 2021',
              'coupon_anchor':'10 December 2021','maturity_date':'10 December 2030'}
    if short:
        quotes.update(accrual_start='10 September 2021',broken_coupon_amount='£2.49')
    req = request(tmp_path,[quotes.get(k,str(values[k])) for k in names]+['Explicit hypothetical events/calendar/entitlement'])
    graph = source_graph.build(req['bundle'],tmp_path)
    assembly = contract_assembly.assemble(graph,req['assembly'])
    by_name = dict(zip(names,graph['units']))
    s.update(issue_id=graph['instrument_id'],source_sha256=graph['documents'][0]['sha256'])
    s['evidence'] = {k:{'source':occurrences.anchor(by_name.get(k,graph['units'][-1])),
                        'reason':'Supplied synthetic interpretation, no actual events'}
                     for k in s if k not in {'profile','issue_id','source_sha256','premise_kind'}}
    if not selected:
        req['financial_scenario']=s
        return req
    rules = {'currency':'currency-label','annual_rate':'percent','frequency':'annual',
             **{k:'amount' for k in ('issue_principal','calculation_amount','fixed_coupon_amount','broken_coupon_amount')},
             **{k:'english-date' for k in ('accrual_start','accrual_end','due_date','coupon_anchor','maturity_date')}}
    terms = {k:{'value':values[k],'source':occurrences.anchor(by_name[k]),'use':by_name[k]['id'],
                'rule':rules.get(k,'reviewed-convention'),'reason':'Supplied synthetic interpretation, no actual events'} for k in names}
    packet = {'version':'selected-coupon-terms.v4','assembly_sha256':digest(assembly),'review':REVIEW,'terms':terms}
    for k in names:
        s.pop(k,None)
        s['evidence'].pop(k,None)
    req['term_interpretations']=packet
    req['contract_calculation']={'version':'selected-coupon-calculation.v1',
        'terms_sha256':digest(contract_terms.admit(graph,assembly,packet)),'premises':s}
    return req


@pytest.mark.parametrize('selected',[False,True])
@pytest.mark.parametrize('form,expected',[('GLOBAL',Fraction('6243169.40')),('DEFINITIVE',Fraction(1249))])
def test_initial_coupon_both_actual_consumers(tmp_path,selected,form,expected):
    req=fixture(tmp_path,selected=selected,form=form)
    answer=service.assess(req,tmp_path)
    q=answer['questions']['Q5']
    assert q['status']=='CONDITIONAL'
    value=q['value']['calculation'] if selected else q['value']
    assert value['day_fraction']=='457/366'
    assert Fraction(value['transfers'][0]['amount'])==expected
    assert value['published_coupon']['initial_amount_used_for_payment']==(form=='DEFINITIVE')
    assert not value['published_coupon']['actual_note_form_established']
    assert value['actual_event']=='NOT_ESTABLISHED' and not value['full_settlement_supported']
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']
    if selected:
        schedule=q['value']['coupon_schedule']
        assert [r['due_date'] for r in schedule]==[f'{y}-12-10' for y in range(2021,2031)]
        assert schedule[0]['stub']=='LONG_FIRST' and all(r['stub']=='REGULAR' for r in schedule[1:])
        assert q['value']['schedule_scope']=='UNADJUSTED_DUE_DATES_ONLY'
        assert 'regular_due_dates' not in q['value']


@pytest.mark.parametrize('change,reason',[
    ('amount','source quotation'),('swapped_broken','Published initial broken'),('swapped_regular','Published regular'),
    ('form','rounding basis'),('global_multiple','one explicitly declared'),('reference','contiguous regular'),
    ('anchor','Coupon anchor differs'),('source','Source edition'),('missing','Missing fields'),
    ('legacy','Unexpected or missing fields'),('stub','first stub'),('due_date','first stub'),
    ('units','integral admitted'),('unknown_form','rounding basis'),('unknown_convention','anchored ACT/ACT')])
def test_initial_coupon_adverse_inputs_are_typed(tmp_path,change,reason):
    req=fixture(tmp_path,form='GLOBAL' if change=='global_multiple' else 'DEFINITIVE')
    s=req['financial_scenario']
    if change=='amount': s['broken_coupon_amount']='12.50'
    elif change=='swapped_broken':
        s['broken_coupon_amount']='10'
        s['evidence']['broken_coupon_amount']=deepcopy(s['evidence']['fixed_coupon_amount'])
    elif change=='swapped_regular':
        s['fixed_coupon_amount']='12.49'
        s['evidence']['fixed_coupon_amount']=deepcopy(s['evidence']['broken_coupon_amount'])
    elif change=='form': s['note_form']='GLOBAL'
    elif change=='global_multiple': s['holdings'].append({**s['holdings'][0],'account_id':'second'})
    elif change=='reference': s['references'][0]['end']='2020-12-11'
    elif change=='anchor': s['coupon_anchor']='2021-12-11'
    elif change=='source': s['evidence']['broken_coupon_amount']['source']['source_sha256']='0'*64
    elif change=='missing': s.pop('broken_coupon_amount')
    elif change=='legacy': s['profile']='fixed-coupon.v2'
    elif change=='stub': s['stub']='LONG_FINAL'
    elif change=='due_date': s['due_date']='2021-12-11'
    elif change=='units': s['holdings'][0]['principal']='100001'
    elif change=='unknown_form': s['note_form']='REGISTERED'
    elif change=='unknown_convention': s['day_count']='30_360'
    q=service.assess(req,tmp_path)['questions']['Q5']
    assert q['status']=='UNSUPPORTED'
    assert reason.lower() in ' '.join(q['unresolved']).lower()


@pytest.mark.parametrize('form',['GLOBAL','DEFINITIVE'])
def test_initial_coupon_no_entitlement_still_checks_published_amount(tmp_path,form):
    req=fixture(tmp_path,form=form)
    s=req['financial_scenario']
    s['holdings'][0]['entitled']=False
    result=service.assess(req,tmp_path)['questions']['Q5']['value']
    assert result['transfers']==[] and result['entitlement_basis']['excluded_accounts']==['declared']
    s['broken_coupon_amount']='12.50'
    assert service.assess(req,tmp_path)['questions']['Q5']['status']=='UNSUPPORTED'


@pytest.mark.parametrize('selected',[False,True])
@pytest.mark.parametrize('form,expected',[('GLOBAL',Fraction('1246575.34')),('DEFINITIVE',Fraction(249))])
def test_initial_coupon_short_first_amounts(tmp_path,selected,form,expected):
    req=fixture(tmp_path,selected=selected,form=form,short=True)
    q=service.assess(req,tmp_path)['questions']['Q5']
    assert q['status']=='CONDITIONAL'
    value=q['value']['calculation'] if selected else q['value']
    assert value['day_fraction']=='91/365'
    assert Fraction(value['transfers'][0]['amount'])==expected
    if selected: assert q['value']['coupon_schedule'][0]['stub']=='SHORT_FIRST'


@pytest.mark.parametrize('change', ['amount','missing','override','legacy','excluded','currency','translation','maturity','principal'])
def test_initial_coupon_selected_source_guards(tmp_path,change):
    req=fixture(tmp_path,selected=True)
    packet=req['term_interpretations']
    if change=='amount': packet['terms']['broken_coupon_amount']['value']='12.50'
    elif change=='missing': packet['terms'].pop('broken_coupon_amount')
    elif change=='override': req['contract_calculation']['premises']['note_form']='GLOBAL'
    elif change=='legacy': packet['version']='selected-coupon-terms.v3'
    elif change=='excluded':
        next(op for op in req['assembly']['operations'] if op['unit']==packet['terms']['broken_coupon_amount']['use'])['role']='EXCLUDED'
        graph=source_graph.build(req['bundle'],tmp_path)
        packet['assembly_sha256']=digest(contract_assembly.assemble(graph,req['assembly']))
    elif change=='currency': packet['terms']['currency']['value']='EUR'
    elif change=='translation': packet['terms']['broken_coupon_amount']['rule']='reviewed-convention'
    elif change=='maturity': packet['terms']['maturity_date']['value']='2030-12-11'
    elif change=='principal': req['contract_calculation']['premises']['holdings'][0]['principal']='500001000'
    with pytest.raises(ValueError):
        service.assess(req,tmp_path)


@pytest.mark.parametrize('quote,currency,amount',[('£1,000','GBP','1000'),('GBP 12.49','GBP','12.49'),('EUR 0.01','EUR','0.01'),('12.49','GBP','12.49')])
def test_initial_coupon_exact_amount_translation(quote,currency,amount):
    assert quoted_amount(quote,currency)==Fraction(amount)


@pytest.mark.parametrize('quote,currency',[('£12.49','EUR'),('USD 12.49','GBP'),('1,00','GBP'),('12.49 per amount','GBP'),('NaN','GBP'),('-1','GBP'),('12 49','GBP')])
def test_initial_coupon_ambiguous_or_wrong_currency_amount_rejected(quote,currency):
    with pytest.raises(ValueError): quoted_amount(quote,currency)


@pytest.mark.parametrize('start,first,maturity,freq,eom,stub,anchor,expected',[
    ('2023-12-30','2024-02-29','2025-02-28',2,False,'SHORT_FIRST','2023-08-30',['2024-02-29','2024-08-30','2025-02-28']),
    ('2023-11-30','2024-08-30','2025-02-28',2,False,'LONG_FIRST','2023-08-30',['2024-08-30','2025-02-28']),
    ('2024-01-15','2024-02-29','2024-08-31',2,True,'SHORT_FIRST','2023-08-31',['2024-02-29','2024-08-31']),
    ('2020-09-10','2021-12-10','2021-12-10',1,False,'LONG_FIRST','2021-12-10',['2021-12-10'])])
def test_initial_coupon_independently_listed_schedules(start,first,maturity,freq,eom,stub,anchor,expected):
    result=contract_terms.initial_stub_schedule(start,first,maturity,freq,eom,stub,coupon_anchor=anchor)
    assert [r['due_date'] for r in result]==expected
    assert [r['accrual_start'] for r in result]==[start,*expected[:-1]]


@pytest.mark.parametrize('change', ['final','short','long','maturity','before_first','bound','anchor','frequency'])
def test_initial_coupon_schedule_cannot_guess_missing_conventions(change):
    args=dict(start='2020-09-10',first='2021-12-10',maturity='2030-12-10',frequency=1,eom=False,stub='LONG_FIRST',coupon_anchor='2021-12-10')
    if change=='final': args['stub']='LONG_FINAL'
    elif change=='short': args['stub']='SHORT_FIRST'
    elif change=='long': args['start']='2021-09-10'
    elif change=='maturity': args['maturity']='2030-12-11'
    elif change=='before_first': args['maturity']='2020-12-10'
    elif change=='bound': args['maturity']='2621-12-10'
    elif change=='anchor': args['coupon_anchor']=None
    elif change=='frequency': args['frequency']=True
    with pytest.raises(ValueError): contract_terms.initial_stub_schedule(**args)


@pytest.mark.parametrize('field,invalid', [('quantum', 0), ('quantum', '1/0'), ('rule', [])])
@pytest.mark.parametrize('entitled', [True, False])
@pytest.mark.parametrize('form', ['GLOBAL', 'DEFINITIVE'])
@pytest.mark.parametrize('selected', [False, True])
def test_initial_coupon_rounding_refusal_with_or_without_entitlement(tmp_path, field, invalid, entitled, form, selected):
    req = fixture(tmp_path, selected=selected, form=form)
    supplied = req['contract_calculation']['premises'] if selected else req['financial_scenario']
    rounding = req['term_interpretations']['terms']['rounding']['value'] if selected else supplied['rounding']
    supplied['holdings'][0]['entitled'] = entitled
    assert service.assess(req, tmp_path)['questions']['Q5']['status'] == 'CONDITIONAL'
    rounding[field] = invalid
    if selected:
        graph = source_graph.build(req['bundle'], tmp_path)
        assembly = contract_assembly.assemble(graph, req['assembly'])
        req['contract_calculation']['terms_sha256'] = digest(contract_terms.admit(graph, assembly, req['term_interpretations']))
    before = deepcopy(req)
    if selected:
        with pytest.raises(ValueError, match='rounding'):
            service.assess(req, tmp_path)
    else:
        answer = service.assess(req, tmp_path)['questions']['Q5']
        assert answer['status'] == 'UNSUPPORTED'
        assert 'rounding' in ' '.join(answer['unresolved'])
    assert req == before
