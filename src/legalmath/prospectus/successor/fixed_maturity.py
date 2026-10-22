"""Conditional scheduled principal and coupons for the supplied Shell2030 profile."""
from copy import deepcopy
from datetime import timedelta
from fractions import Fraction
from importlib.resources import files
import json

from .anchors import bind, fields
from .contracts import digest, timestamp
from .coupon_amounts import quoted_amount
from .coupon_dates import english_date
from .fixed_coupon import adjusted
from .fixed_term import calculate as coupon_term
from .occurrences import _DependencyLookup
from ..semantics import exact


ASSUMPTIONS = {'no_prior_redemption_or_cancellation', 'no_improper_withholding_or_refusal',
    'presentation_and_surrender_requirements_satisfied', 'no_missing_coupon_deduction',
    'payment_law_requirements_satisfied', 'no_deductions_or_additional_sums',
    'note_form_requirements_satisfied', 'denomination_valid', 'unamended_terms'}


def source_terms(profile, admitted, graph, assembly):
    expected=json.loads(files(__package__).joinpath('shell_maturity_spec.json').read_text())
    if (profile != expected or digest(profile) != digest(expected)
            or graph['instrument_id'] != expected['instrument_id']):
        raise ValueError('Scheduled maturity source profile or instrument changed')
    lookup=_DependencyLookup(graph,assembly)
    roles={}
    for unit in assembly['units']:
        if unit['unit'] in roles:
            raise ValueError('Duplicate selected occurrence identity')
        roles[unit['unit']]=unit['role']
    contexts={}
    for key, sources in expected['groups'].items():
        contexts[key]=[]
        for source in sources:
            matches=lookup.uses(graph,assembly,source,roles=('OPERATIVE','UNKNOWN'))
            if len(matches)!=1:
                raise ValueError('Maturity requires one complete unchanged selected source copy')
            contexts[key].append({**matches[0],'role':roles[matches[0]['unit']]})
    unit=quoted_amount(expected['groups']['denominations_and_unit'][-1]['quote'],'GBP')
    amount=expected['groups']['final_amount'][-1]['quote']
    suffix=' per Calculation Amount'
    if not amount.endswith(suffix):
        raise ValueError('Final redemption amount requires its explicit unit')
    amount=quoted_amount(amount[:-len(suffix)],'GBP')
    maturity=english_date(expected['groups']['maturity'][-1]['quote'])
    terms={k:v['value'] for k,v in admitted['terms'].items()}
    if (terms['currency']!='GBP' or exact(terms['calculation_amount'])!=unit
            or terms['maturity_date']!=maturity or unit<=0 or amount<=0
            or terms['note_form'] not in {'GLOBAL','DEFINITIVE'}):
        raise ValueError('Coupon terms disagree with the selected maturity source profile')
    return unit,amount,maturity,contexts


def calculate(admitted, calculation, graph, assembly):
    fields(calculation, {'version','terms_sha256','coupon_term','redemption'},
           {'version','terms_sha256','coupon_term','redemption'})
    if (calculation['version']!='selected-fixed-maturity-calculation.v1'
            or calculation['terms_sha256']!=digest(admitted)
            or admitted.get('version')!='admitted-coupon-terms.v3'
            or admitted['graph_sha256']!=digest(graph)
            or admitted['assembly_sha256']!=digest(assembly)):
        raise ValueError('Maturity terms or context binding changed')
    c=calculation['coupon_term'];r=calculation['redemption']
    if not isinstance(c,dict) or c.get('version')!='selected-fixed-term-calculation.v1':
        raise ValueError('Maturity requires the full supported coupon-term request')
    required={'version','premise_kind','source_profile','payment_date',
              'principal_entitlements','assumptions','events','evidence'}
    fields(r,required,required)
    if r['version']!='conditional-scheduled-redemption.v1' or r['premise_kind']!='HYPOTHETICAL':
        raise ValueError('Only hypothetical scheduled-redemption premises are supported')
    fields(r['assumptions'],ASSUMPTIONS,ASSUMPTIONS)
    if any(v is not True for v in r['assumptions'].values()):
        raise ValueError('Every scheduled-redemption assumption must be explicitly true')
    evidence_fields={'principal_entitlements','assumptions','payment_date','events'}
    fields(r['evidence'],evidence_fields,evidence_fields)
    for evidence in r['evidence'].values():
        fields(evidence,{'source','reason'},{'source','reason'})
        if not isinstance(evidence['reason'],str) or not evidence['reason'].strip():
            raise ValueError('Redemption premises need a nonblank reason')
        bind(graph,evidence['source'])

    # Validate independent principal entitlement before the more expensive source
    # and coupon evaluations. Do not infer it from the coupon's entitlement flag.
    common=c.get('premises')
    if not isinstance(common,dict) or not isinstance(common.get('holdings'),list):
        raise ValueError('Declared full-term holdings required')
    holdings=common['holdings'];eligible={};accounts=set()
    for holding in holdings:
        fields(holding,{'legal_holder_id','account_id','principal','entitled'},
               {'legal_holder_id','account_id','principal','entitled'})
        if not isinstance(holding['account_id'],str) or holding['account_id'] in accounts:
            raise ValueError('Distinct account identity required')
        accounts.add(holding['account_id'])
    if not isinstance(r['principal_entitlements'],list):
        raise ValueError('Separate principal entitlement list required')
    for row in r['principal_entitlements']:
        fields(row,{'account_id','principal_entitled'},{'account_id','principal_entitled'})
        if (not isinstance(row['account_id'],str) or row['account_id'] not in accounts
                or row['account_id'] in eligible or type(row['principal_entitled']) is not bool):
            raise ValueError('Principal entitlement must identify each known account once with a Boolean')
        eligible[row['account_id']]=row['principal_entitled']
    if set(eligible)!=accounts:
        raise ValueError('Principal entitlement missing for a declared account')
    unit_value=exact(admitted['terms']['calculation_amount']['value'])
    if unit_value<=0 or any((exact(h['principal'])/unit_value).denominator!=1 for h in holdings):
        raise ValueError('Scheduled principal requires integral calculation amounts')

    maturity=admitted['terms']['maturity_date']['value']
    payment=adjusted(maturity,'FOLLOWING',common['calendar'])
    if payment!=r['payment_date']:
        raise ValueError('Redemption payment date contradicts the declared calendar')
    if not isinstance(r['events'],list) or len(r['events'])!=3:
        raise ValueError('Exactly three scheduled-redemption events required')
    events={};ids=set();instants=set()
    for event in r['events']:
        fields(event,{'id','kind','at','order'},{'id','kind','at','order'})
        if (not isinstance(event['id'],str) or not event['id'].strip() or event['id'] in ids
                or not isinstance(event['kind'],str) or event['kind'] not in {'redemption_due','presentation','payment'}
                or event['kind'] in events or type(event['order']) is not int or not isinstance(event['at'],str)):
            raise ValueError('Unique typed redemption event identity and ordering required')
        at=timestamp(event['at']);instant=(at,event['order'])
        # This bounded route uses UTC event dates explicitly; timezone/local-date
        # conversion needs its own reviewed model rather than silent truncation.
        if at.utcoffset()!=timedelta(0) or instant in instants:
            raise ValueError('Distinct UTC redemption event instants required')
        ids.add(event['id']);instants.add(instant);events[event['kind']]=instant
    if (events['redemption_due'][0].date().isoformat()!=maturity
            or events['payment'][0].date().isoformat()!=payment
            or not events['redemption_due']<events['payment']
            or not events['presentation']<events['payment']):
        raise ValueError('Redemption due date, presentation or payment ordering changed')

    unit,amount,maturity,contexts=source_terms(r['source_profile'],admitted,graph,assembly)
    coupons=coupon_term(admitted,c,graph,assembly)
    if coupons['calculations'][-1]['payment_date']!=payment:
        raise ValueError('Final coupon and scheduled redemption require the same declared payment day')
    principal_by_holder={}
    for holding in holdings:
        if eligible[holding['account_id']]:
            holder=holding['legal_holder_id']
            principal_by_holder[holder]=principal_by_holder.get(holder,Fraction())+exact(holding['principal'])
    payment_event=next(e['id'] for e in r['events'] if e['kind']=='payment')
    transfers=[{'legal_holder_id':holder,'currency':'GBP','principal':str(principal),
                'calculation_units':str(principal/unit),'amount':str(principal/unit*amount),
                'payment_event':payment_event} for holder,principal in sorted(principal_by_holder.items())]
    flows=[];totals={}
    for i,(period,result) in enumerate(zip(coupons['coupon_schedule'],coupons['calculations'])):
        for transfer in result['transfers']:
            flows.append({'kind':'COUPON','period':i+1,'due_date':period['due_date'],
                'payment_date':result['payment_date'],**{k:transfer[k] for k in ('legal_holder_id','currency','amount','payment_event')}})
            holder=transfer['legal_holder_id'];totals.setdefault(holder,[Fraction(),Fraction()])[0]+=exact(transfer['amount'])
    for transfer in transfers:
        flows.append({'kind':'PRINCIPAL','due_date':maturity,'payment_date':payment,
            **{k:transfer[k] for k in ('legal_holder_id','currency','amount','payment_event')}})
        holder=transfer['legal_holder_id'];totals.setdefault(holder,[Fraction(),Fraction()])[1]+=exact(transfer['amount'])
    total_rows=[{'legal_holder_id':h,'currency':'GBP','coupon_amount':str(v[0]),
                 'principal_amount':str(v[1]),'total_amount':str(sum(v))} for h,v in sorted(totals.items())]
    return {'version':'conditional-fixed-maturity.v1','selected_terms_sha256':digest(admitted),
        'coupons':coupons,'redemption':{'due_date':maturity,'payment_date':payment,'currency':'GBP',
            'amount_per_calculation_unit':str(amount),'calculation_unit':str(unit),'transfers':transfers,
            'assumptions':deepcopy(r['assumptions']),'principal_entitlements':deepcopy(r['principal_entitlements']),
            'events':deepcopy(r['events']),'source_profile':deepcopy(r['source_profile']),
            'source_occurrences':contexts,'source_applicability':'CONDITIONAL_ON_SUPPLIED_PROFILE',
            'source_applicability_established':False,'actual_cancellation':'NOT_ESTABLISHED',
            'additional_interest_for_payment_day_delay':'0',
            'payment_basis':'ONE_HYPOTHETICAL_GLOBAL_RECIPIENT' if coupons['note_form']=='GLOBAL' else 'DECLARED_DEFINITIVE_RECIPIENTS'},
        'cash_flows':flows,'totals':total_rows,'calculation_inputs':deepcopy(calculation),
        'redemption_calculated':True,'actual_event':'NOT_ESTABLISHED',
        'legal_entitlement_established':False,'full_settlement_supported':False}
