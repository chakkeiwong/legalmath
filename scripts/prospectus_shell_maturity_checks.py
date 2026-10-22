"""Separate integer cash-flow oracle and adversarial checks for maturity evidence."""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction


ASSUMPTIONS = ('no_prior_redemption_or_cancellation', 'no_improper_withholding_or_refusal',
    'presentation_and_surrender_requirements_satisfied', 'no_missing_coupon_deduction',
    'payment_law_requirements_satisfied', 'no_deductions_or_additional_sums',
    'note_form_requirements_satisfied', 'denomination_valid', 'unamended_terms')


def expected(packet):
    """No production calculation, parsing, source profile or date helper is used."""
    request=packet['request']['contract_calculation']
    coupon=request['coupon_term']; redemption=request['redemption']
    form=packet['admitted']['terms']['note_form']['value']
    calendar=coupon['premises']['calendar']
    due=date(2030,12,10);pay=due
    while pay.weekday() in calendar['weekend'] or pay.isoformat() in calendar['holidays']:
        pay+=timedelta(days=1)
    amounts={};principals={};flows=[]
    for h in coupon['premises']['holdings']:
        principal=int(h['principal'])
        assert principal>=0 and principal%1000==0
        holder=h['legal_holder_id']
        if h['entitled']:
            amounts[holder]=amounts.get(holder,0)+principal
        eligible=next(r['principal_entitled'] for r in redemption['principal_entitlements'] if r['account_id']==h['account_id'])
        if eligible:
            principals[holder]=principals.get(holder,0)+principal
    for i in range(10):
        end=date(2021+i,12,10);day=end
        while day.weekday() in calendar['weekend'] or day.isoformat() in calendar['holidays']:
            day+=timedelta(days=1)
        for holder,principal in sorted(amounts.items()):
            # Global: p * 1% * 457/366, rounded to pence once.
            # Definitive: 12.49 per1000 initially; 10.00 thereafter.
            if i==0 and form=='GLOBAL':
                q,r=divmod(principal*457,366);cents=q+int(2*r>=366)
            elif i==0:
                cents=(principal//1000)*1249
            else:
                cents=principal
            flows.append({'kind':'COUPON','period':i+1,'due_date':end.isoformat(),
                'payment_date':day.isoformat(),'legal_holder_id':holder,'currency':'GBP',
                'amount':str(Fraction(cents,100)),
                'payment_event':next(e['id'] for e in coupon['periods'][i]['events'] if e['kind']=='payment')})
    for holder,principal in sorted(principals.items()):
        flows.append({'kind':'PRINCIPAL','due_date':due.isoformat(),'payment_date':pay.isoformat(),
            'legal_holder_id':holder,'currency':'GBP','amount':str(principal),
            'payment_event':next(e['id'] for e in redemption['events'] if e['kind']=='payment')})
    totals=[]
    for holder in sorted(set(amounts)|set(principals)):
        interest=sum((Fraction(f['amount']) for f in flows if f['kind']=='COUPON' and f['legal_holder_id']==holder),Fraction())
        principal=principals.get(holder,0)
        totals.append({'legal_holder_id':holder,'currency':'GBP','coupon_amount':str(interest),
                       'principal_amount':str(principal),'total_amount':str(interest+principal)})
    return {'cash_flows':flows,'totals':totals,'principal_by_holder':principals,'payment_date':pay.isoformat()}


def validate(answer, packet):
    from legalmath.prospectus.successor.contracts import digest
    value=answer['questions']['Q5']['value'];oracle=packet['expected']
    assert value['version']=='conditional-fixed-maturity.v1'
    assert value['coupons']==packet['baseline_answer']['questions']['Q5']['value']
    assert value['cash_flows']==oracle['cash_flows'] and value['totals']==oracle['totals']
    assert value['calculation_inputs']==packet['request']['contract_calculation']
    assert value['selected_terms_sha256']==digest(packet['admitted'])
    assert value['actual_event']=='NOT_ESTABLISHED' and value['redemption_calculated'] is True
    assert value['full_settlement_supported'] is False and value['legal_entitlement_established'] is False
    r=value['redemption'];spec=packet['request']['contract_calculation']['redemption']
    assert r['due_date']=='2030-12-10' and r['payment_date']==oracle['payment_date']
    assert r['currency']=='GBP' and r['amount_per_calculation_unit']=='1000' and r['calculation_unit']=='1000'
    assert r['assumptions']==spec['assumptions'] and r['principal_entitlements']==spec['principal_entitlements']
    assert r['source_profile']==spec['source_profile'] and r['events']==spec['events']
    assert r['additional_interest_for_payment_day_delay']=='0'
    assert r['actual_cancellation']=='NOT_ESTABLISHED'
    assert r['payment_basis']==('ONE_HYPOTHETICAL_GLOBAL_RECIPIENT' if packet['admitted']['terms']['note_form']['value']=='GLOBAL' else 'DECLARED_DEFINITIVE_RECIPIENTS')
    assert {t['legal_holder_id']:int(t['amount']) for t in r['transfers']}==oracle['principal_by_holder']
    for transfer in r['transfers']:
        assert transfer=={'legal_holder_id':transfer['legal_holder_id'],'currency':'GBP',
            'principal':transfer['amount'],'calculation_units':str(int(transfer['amount'])//1000),
            'amount':transfer['amount'],'payment_event':next(e['id'] for e in spec['events'] if e['kind']=='payment')}
    baseline=packet['baseline_answer']
    assert {k:v for k,v in answer['questions'].items() if k!='Q5'}=={k:v for k,v in baseline['questions'].items() if k!='Q5'}
    changed={'questions','consumed_products','request_sha256','report_sha256'}
    assert {k:v for k,v in answer.items() if k not in changed}=={k:v for k,v in baseline.items() if k not in changed}
    assert answer['report_sha256']==digest({k:v for k,v in answer.items() if k!='report_sha256'})
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']


def bad_calculations(calculation):
    for defect in ('early-amount','missing-source-condition','changed-profile','stale-terms','wrong-date',
            'missing-entitlement','duplicate-entitlement','foreign-account','numeric-entitlement',
            'wrong-event-date','late-presentation','missing-event','wrong-evidence','principal-override',
            'coupon-version','out-of-calendar','over-issue','nonintegral-principal','actual-premise'):
        c=deepcopy(calculation);r=c['redemption'];h=c['coupon_term']['premises']['holdings'][0]
        if defect=='early-amount':
            r['source_profile']['groups']['final_amount'][-1]['unit']='shell-2030-final:p3:l31'
        elif defect=='missing-source-condition':r['source_profile']['groups'].pop('interest_cessation')
        elif defect=='changed-profile':r['source_profile']['scope']='ALL_BONDS'
        elif defect=='stale-terms':c['terms_sha256']='0'*64
        elif defect=='wrong-date':r['payment_date']='2030-12-09'
        elif defect=='missing-entitlement':r['principal_entitlements'].pop()
        elif defect=='duplicate-entitlement':r['principal_entitlements'].append(deepcopy(r['principal_entitlements'][0]))
        elif defect=='foreign-account':r['principal_entitlements'][0]['account_id']='unknown'
        elif defect=='numeric-entitlement':r['principal_entitlements'][0]['principal_entitled']=1
        elif defect=='wrong-event-date':r['events'][0]['at']='2030-12-09T00:00:00Z'
        elif defect=='late-presentation':r['events'][1]['at']='2031-01-01T00:00:00Z'
        elif defect=='missing-event':r['events'].pop()
        elif defect=='wrong-evidence':r['evidence']['assumptions']['source']['source_sha256']='0'*64
        elif defect=='principal-override':r['principal_amount']='1'
        elif defect=='coupon-version':c['coupon_term']['version']='selected-fixed-maturity-calculation.v1'
        elif defect=='out-of-calendar':c['coupon_term']['premises']['calendar']['valid_until']='2030-12-10'
        elif defect=='over-issue':h['principal']='500001000'
        elif defect=='nonintegral-principal':h['principal']='100001'
        else:r['premise_kind']='ACTUAL'
        yield defect,c
    for key in ASSUMPTIONS:
        for value in (False,None,1):
            c=deepcopy(calculation);c['redemption']['assumptions'][key]=value
            yield key+'='+repr(value),c


def corrupt_answers(answer):
    from legalmath.prospectus.successor.contracts import digest
    for defect in ('lost-coupon','lost-principal','lost-assumption','actual-event','wrong-total','false-settlement'):
        bad=deepcopy(answer);value=bad['questions']['Q5']['value']
        if defect=='lost-coupon':value['coupons']['calculations'].pop()
        elif defect=='lost-principal':
            value['cash_flows'].append({'kind':'PRINCIPAL','amount':'1'})
        elif defect=='lost-assumption':value['redemption']['assumptions'].pop(ASSUMPTIONS[0])
        elif defect=='actual-event':value['actual_event']='ESTABLISHED'
        elif defect=='wrong-total':value['totals'].append({'total_amount':'1'})
        else:value['full_settlement_supported']=True
        bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
        yield defect,bad
