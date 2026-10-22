"""Exact hypothetical amount derivation for the selected default(c) branch."""
from copy import deepcopy
import re
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch,names
from .successor.ratio_facts import number

VERSION='basf-cross-default-amount.v1'
KEY='cross_default_amount_review'
NODE='basf-default:c'
THRESHOLD='200000000'
COMPUTED='default.c.overdue'


def context(products):
    rows=[n for n in products['P3']['payload']['clauses']['nodes'] if n['id']==NODE]
    if len(rows)!=1 or rows[0]['effect']!='repayment' or 'mehr als EUR 200.000.000' not in rows[0]['quote']:
        raise ValueError('Exact selected default(c) source required')
    return deepcopy(rows[0])


def analyze(row,node,instrument):
    required={'id','kind','payment','qualified_obligation','thirty_day_condition',
              'currency_basis_supported','other_facts'}
    fields(row,required,required)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical amount scenario required')
    for key in ('qualified_obligation','thirty_day_condition','currency_basis_supported'):
        value=row[key]
        if value is not None and value!='conflict' and type(value) is not bool:
            raise ValueError('Amount qualifications must be Boolean,unknown or conflict')
    payment=row['payment'];keys={'instrument_id','event_id','amount','currency','fx'}
    fields(payment,keys,keys)
    if payment['instrument_id']!=instrument or payment['event_id']!=row['id']:
        raise ValueError('Payment instrument or event mismatch')
    currency=payment['currency']
    if not isinstance(currency,str) or re.fullmatch('[A-Z]{3}',currency) is None:
        raise ValueError('Explicit three-letter source currency required')
    amount=number(payment['amount']) if payment['amount'] is not None else None
    rate=None;unresolved=[]
    if amount is None:unresolved.append('Missing payment amount')
    if currency=='EUR':
        if payment['fx'] is not None:raise ValueError('EUR amount must not carry an FX conversion')
        rate=number('1')
    elif payment['fx'] is None:
        unresolved.append('Missing explicit EUR-per-source-unit conversion')
    else:
        fx=payment['fx'];keys={'instrument_id','event_id','source_currency','target_currency','unit','rate'}
        fields(fx,keys,keys)
        if (fx['instrument_id']!=instrument or fx['event_id']!=row['id']
                or fx['source_currency']!=currency or fx['target_currency']!='EUR'
                or fx['unit']!='EUR_PER_SOURCE_UNIT'):
            raise ValueError('FX currency,direction,instrument or event mismatch')
        rate=number(fx['rate'])
        if rate<=0:raise ValueError('FX conversion rate must be positive')
    exact=None;above=None
    if amount is not None and rate is not None:
        converted=amount*rate;above=converted>number(THRESHOLD)
        exact={'amount':str(amount),'rate_eur_per_source_unit':str(rate),
               'eur_equivalent':str(converted),'threshold_eur':THRESHOLD,'operator':'GT',
               'method':'exact rational multiplication and strict comparison'}
    qualification={'amount_above_threshold':above,'qualified_obligation':row['qualified_obligation'],
                   'thirty_day_condition':row['thirty_day_condition'],'currency_basis_supported':row['currency_basis_supported']}
    overdue=dispatch({'all':list(qualification)},qualification)
    allowed=names(node['conditions'])-{COMPUTED};facts=row['other_facts'];fields(facts,allowed)
    if any(v is not None and v!='conflict' and type(v) is not bool for v in facts.values()):
        raise ValueError('Default premises must be Boolean,unknown or conflict')
    observations={**facts,COMPUTED:{'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[overdue['status']]}
    outcome=dispatch(node['conditions'],observations)
    return {'scenario':deepcopy(row),'amount_above_threshold':above,'exact_amount':exact,'unresolved_amount':unresolved,
            'derived_overdue':overdue,'overdue_premises':qualification,'complete_default_c':outcome,
            'derived_observations':observations,'actual_default':'NOT_ESTABLISHED',
            'actual_exercise':'NOT_ESTABLISHED','governing_rate_date':'NOT_ESTABLISHED',
            'meaning':'Conditional computation for one declared payment;no inferred aggregation or actual legal classification'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products)
            or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned amount profile or complete baseline changed')
    if profile['actual_event_established'] is not False:
        raise ValueError('Conditional amount cannot establish actual events')
    node=context(products)
    if profile['context']!=node:raise ValueError('Complete default(c) source context changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not rows or len(rows)>128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded hypothetical scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Distinct amount scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or first['payment']['amount'] is not None or first['other_facts']
            or any(first[k] is not None for k in ('qualified_obligation','thirty_day_condition','currency_basis_supported'))):
        raise ValueError('Explicit all-open amount baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
            'ordinary_answer_sha256':digest(ordinary),'context':node,
            'scenarios':[analyze(row,node,instrument) for row in rows],
            'actual_event_established':False,'classification':'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
                !={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Complete amount answer changed baseline or digest')
    expected=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY)!=expected:raise ValueError('Computed amount answer differs from full reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(expected['scenarios'])}
