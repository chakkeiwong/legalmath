"""Conditional30-day nonpayment clocks for selected default(a)/(c) sources."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import re
from . import cross_default_amount
from .successor import calendar_facts
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch,names

VERSION='basf-payment-deadline.v1'
KEY='payment_deadline_review'
QUALIFICATIONS=('source_trigger_supported','counting_convention_supported','payment_state_supported')
STATES={'FULL_PAYMENT','UNPAID_THROUGH_ASSESSMENT','UNKNOWN'}
CONVENTIONS={'ELAPSED_30_DAYS_INCLUSIVE','FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE'}
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def context(products):
    result={}
    for letter in ('a','c'):
        nodes=[n for n in products['P3']['payload']['clauses']['nodes'] if n['id']=='basf-default:'+letter]
        if len(nodes)!=1 or nodes[0]['effect']!='repayment' or 'nicht innerhalb von 30 Tagen' not in nodes[0]['quote']:
            raise ValueError('Complete selected30-day payment sources required')
        result[letter]=deepcopy(nodes[0])
    if 'nach Inanspruchnahme' not in result['c']['quote']:
        raise ValueError('Separate guarantee invocation source required')
    return result


def fixed_offset(value):
    if not isinstance(value,str) or re.fullmatch(r'[+-]\d{2}:\d{2}',value) is None:
        raise ValueError('Explicit fixed UTC offset required for civil clock')
    hour,minute=int(value[1:3]),int(value[4:6])
    if hour>23 or minute>59:raise ValueError('Invalid civil UTC offset')
    return timezone(timedelta(minutes=(hour*60+minute)*(1 if value[0]=='+' else -1)))


def clock_result(row,instrument):
    clock=row['clock'];keys={'instrument_id','event_id','trigger','assessment','payment','convention','utc_offset'}
    fields(clock,keys,keys)
    if clock['instrument_id']!=instrument or clock['event_id']!=row['id']:
        raise ValueError('Payment clock instrument or event mismatch')
    convention=clock['convention'];empty=all(clock[k] is None for k in ('trigger','assessment','payment'))
    if not (convention is None and empty):
        if not isinstance(convention,str) or convention not in CONVENTIONS:raise ValueError('Explicit supported payment clock required')
    zone=None
    if convention=='FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE':zone=fixed_offset(clock['utc_offset'])
    elif clock['utc_offset'] is not None:raise ValueError('Fixed offset only applies to civil payment clock')
    state=row['payment_state']
    if not isinstance(state,str) or state not in STATES:raise ValueError('Explicit payment state required')
    if state=='FULL_PAYMENT' and clock['payment'] is None:raise ValueError('Stipulated full payment requires its timestamp')
    if state!='FULL_PAYMENT' and clock['payment'] is not None:raise ValueError('Unknown/unpaid state cannot carry full payment timestamp')
    if not isinstance(row['trigger_kind'],str) or row['trigger_kind'] not in ('DUE_DATE','GUARANTEE_INVOCATION'):
        raise ValueError('Explicit due-date or guarantee-invocation trigger required')
    if row['route']=='a' and row['trigger_kind']!='DUE_DATE':raise ValueError('Default(a) requires due-date trigger')
    roles={'trigger':row['trigger_kind'],'assessment':'ASSESSMENT','payment':'FULL_PAYMENT'}
    values={};unresolved=[]
    for label in ('trigger','assessment','payment'):
        item=clock[label]
        if item is None:
            if label!='payment':unresolved.append('Missing '+label)
            continue
        fields(item,{'value','role'},{'value','role'})
        if item['role']!=roles[label]:raise ValueError('Payment clock operand role mismatch')
        values[label]=calendar_facts.operand_value(item['value'],'ELAPSED_24_HOUR_DAYS').astimezone(timezone.utc)
    if 'assessment' in values:
        if 'trigger' in values and values['assessment']<values['trigger']:raise ValueError('Assessment precedes trigger')
        if 'payment' in values and values['payment']>values['assessment']:raise ValueError('Payment postdates assessment')
    raw=None;exact=None
    if 'trigger' in values:
        trigger=values['trigger']
        try:
            if convention=='ELAPSED_30_DAYS_INCLUSIVE':
                limit=trigger+timedelta(days=30);inclusive=True
            else:
                day=trigger.astimezone(zone).date()+timedelta(days=31)
                limit=datetime.combine(day,datetime.min.time(),tzinfo=zone).astimezone(timezone.utc);inclusive=False
        except (ValueError,OverflowError) as error:raise ValueError('Payment deadline outside supported datetime range') from error
        assessed=values.get('assessment');paid=values.get('payment')
        expired=None if assessed is None else (assessed>limit if inclusive else assessed>=limit)
        timely=None if paid is None else (paid<=limit if inclusive else paid<limit)
        if expired is False:raw=False
        elif expired is True:
            raw=(not timely) if state=='FULL_PAYMENT' else True if state=='UNPAID_THROUGH_ASSESSMENT' else None
        exact={'trigger_utc':trigger.isoformat(),'limit_utc':limit.isoformat(),'limit_inclusive':inclusive,
            'assessment_utc':assessed.isoformat() if assessed is not None else None,
            'payment_utc':paid.isoformat() if paid is not None else None,'assessment_after_payment_window':expired,
            'payment_within_window':timely,'convention':convention,'fixed_utc_offset':clock['utc_offset']}
    return raw,exact,unresolved


def analyze(row,nodes,instrument):
    keys={'id','kind','route','trigger_kind','clock','payment_state','qualified_note_payment','other_facts','amount_scenario',*QUALIFICATIONS}
    fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT' or row['route'] not in ('a','c'):
        raise ValueError('Explicit hypothetical payment route required')
    for key in (*QUALIFICATIONS,'qualified_note_payment'):
        v=row[key]
        if v is not None and v!='conflict' and type(v) is not bool:raise ValueError('Payment qualifications must be Boolean,unknown or conflict')
    raw,exact,unresolved=clock_result(row,instrument)
    premises={'failure_within_declared_window':raw,**{k:row[k] for k in QUALIFICATIONS}}
    derived=dispatch({'all':list(premises)},premises)
    amount_review=None
    if row['route']=='a':
        if row['amount_scenario'] is not None:raise ValueError('Default(a) cannot carry cross-default amount scenario')
        node=nodes['a'];computed='default.a.payment30'
        condition=dispatch({'all':['timed_failure','qualified_note_payment']},
            {'timed_failure':VALUE[derived['status']],'qualified_note_payment':row['qualified_note_payment']})
        expression={'all':[node['conditions'],{'not':node['exceptions']}]}
        facts=row['other_facts'];fields(facts,names(expression)-{computed})
        if any(v is not None and v!='conflict' and type(v) is not bool for v in facts.values()):raise ValueError('Invalid default(a) premise')
        observations={**facts,computed:VALUE[condition['status']]};complete=dispatch(expression,observations)
    else:
        if row['other_facts'] is not None or row['qualified_note_payment'] is not None:
            raise ValueError('Cross-default uses amount-scenario premises only')
        amount=deepcopy(row['amount_scenario'])
        if not isinstance(amount,dict) or 'thirty_day_condition' in amount:raise ValueError('Computed payment time cannot be overridden')
        if amount.get('id')!=row['id']:raise ValueError('Amount/time scenario identity mismatch')
        amount['thirty_day_condition']=VALUE[derived['status']]
        amount_review=cross_default_amount.analyze(amount,nodes['c'],instrument)
        condition=amount_review['derived_overdue'];observations=amount_review['derived_observations'];complete=amount_review['complete_default_c']
    return {'scenario':deepcopy(row),'failure_within_declared_window':raw,'exact_payment_clock':exact,
        'unresolved_clock':unresolved,'timing_premises':premises,'derived_thirty_day_condition':derived,
        'derived_source_payment_premise':condition,'amount_review':amount_review,'complete_default':complete,
        'derived_observations':observations,'actual_default':'NOT_ESTABLISHED','actual_full_payment':'NOT_ESTABLISHED',
        'legal_counting_convention_established':False,'meaning':'Conditional payment failure; late payment and cure remain separate propositions'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned payment profile or complete baseline changed')
    if profile['actual_event_established'] is not False:raise ValueError('Conditional payment cannot establish actual default')
    nodes=context(products)
    if profile['context']!=nodes:raise ValueError('Complete default(a)/(c) source context changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not rows or len(rows)>128 or any(not isinstance(r,dict) for r in rows):raise ValueError('Bounded payment scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Distinct payment scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or first['route']!='a' or first['other_facts'] or first['payment_state']!='UNKNOWN'
            or any(first[k] is not None for k in (*QUALIFICATIONS,'qualified_note_payment','amount_scenario'))
            or any(first['clock'][k] is not None for k in ('trigger','assessment','payment','convention','utc_offset'))):
        raise ValueError('Explicit all-open payment baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':nodes,'scenarios':[analyze(r,nodes,instrument) for r in rows],
        'actual_event_established':False,'classification':'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
                !={k:v for k,v in ordinary.items() if k!='report_sha256'}):raise ValueError('Complete payment answer changed baseline or digest')
    expected=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY)!=expected:raise ValueError('Computed payment answer differs from full reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(expected['scenarios'])}
