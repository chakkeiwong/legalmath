"""Conditional section13 deemed dates composed with agent notice intervals."""
from copy import deepcopy
from datetime import timedelta
from . import agent_notice_application as agent
from .causal_rating import boolean
from .successor import calendar_facts
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch

VERSION='basf-notice-delivery.v1'
KEY='notice_delivery_review'
PREMISES=('listed_in_lux','valid_route_event','exchange_rules_permit','issuer_elects_substitution')
IDENTITY=agent.IDENTITY | {'notice_id'}
ROUTES={'PUBLICATION':(3,'PUBLICATION_ON_LUX_EXCHANGE'),
        'CLEARING_SUBSTITUTION':(7,'CLEARING_DELIVERY_FOR_FORWARDING')}


def context(products,ordinary):
    source=agent.context(products,ordinary)
    prior=ordinary.get(agent.KEY)
    if not isinstance(prior,dict) or prior.get('context')!=source:
        raise ValueError('Integrated agent notice with unchanged complete source required')
    publication,clearing,holder=source['notice_clauses']
    if (publication['procedural_reading']['deemed_effective_days_after_publication']!=3
            or clearing['procedural_reading']['deemed_communicated_days_after_clearing_notice']!=7
            or clearing['procedural_reading']['publication_applies_while_listed'] is not True
            or clearing['procedural_reading']['substitution_requires_exchange_rules_permission'] is not True
            or clearing['procedural_reading']['forward_to']!='holders'):
        raise ValueError('Source route delays or conditions changed')
    return {'agent_and_notice_context':source,'direction':'ISSUER_TO_HOLDERS',
            'holder_to_agent_notice_separate':True,'supported_counting':'DECLARED_CIVIL_DATE_GAP_ONLY',
            'qualification':'Finite selected listed-note reading; actual events and full legal validity remain unproved'}


def route_condition(route,premises):
    fields(premises,PREMISES,PREMISES)
    for value in premises.values():boolean(value)
    if route=='UNKNOWN':
        if any(v is not None for v in premises.values()):
            raise ValueError('Unknown notice route cannot carry selected route facts')
        return dispatch('route_known',{'route_known':None})
    if not isinstance(route,str) or route not in ROUTES:
        raise ValueError('Supported issuer notice route required')
    names=['listed_in_lux','valid_route_event']
    if route=='CLEARING_SUBSTITUTION':names+=['exchange_rules_permit','issuer_elects_substitution']
    elif premises['exchange_rules_permit'] is not None or premises['issuer_elects_substitution'] is not None:
        raise ValueError('Publication scenario must not mix clearing substitution premises')
    return dispatch({'all':names},premises)


def analyze(row,instrument):
    keys={'id','kind','identity','route','convention','event','proposed_change','premises','insolvency','reading_applies'}
    fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical delivery scenario required')
    identity=row['identity'];fields(identity,IDENTITY,IDENTITY)
    if identity['instrument_id']!=instrument or any(not isinstance(identity[k],str) or not identity[k].strip() for k in IDENTITY):
        raise ValueError('Notice,change,agent and instrument identities required')
    boolean(row['insolvency']);boolean(row['reading_applies'])
    route=row['route'];condition=route_condition(route,row['premises'])
    convention=row['convention']
    if convention!='CIVIL_DATE_GAP' and not (convention is None and row['event'] is None and row['proposed_change'] is None):
        raise ValueError('Only explicitly declared civil-date composition is supported')
    event=row['event'];candidate=None;event_date=None;delay=None
    if event is not None:
        if route=='UNKNOWN':raise ValueError('A dated event needs its explicit source route')
        keys=IDENTITY|{'role','value'};fields(event,keys,keys)
        delay,role=ROUTES[route]
        if any(event[k]!=identity[k] for k in IDENTITY) or event['role']!=role:
            raise ValueError('Notice event identity or issuer direction mismatch')
        event_date=calendar_facts.operand_value(event['value'],convention)
        try:candidate=(event_date+timedelta(days=delay)).isoformat()
        except OverflowError as error:raise ValueError('Deemed date outside supported range') from error
    end=row['proposed_change']
    if end is not None:
        keys=agent.IDENTITY|{'role','value'};fields(end,keys,keys)
        if any(end[k]!=identity[k] for k in agent.IDENTITY) or end['role']!='PROPOSED_CHANGE':
            raise ValueError('Proposed change identity or role mismatch')
        calendar_facts.operand_value(end['value'],convention)
    subject={k:identity[k] for k in agent.IDENTITY}
    derived={'id':row['id'],'kind':'HYPOTHETICAL_DEVELOPMENT','identity':subject,
        'interval':{'convention':convention,'start':None if candidate is None else {**subject,'role':'HOLDERS_INFORMED','value':candidate},'end':deepcopy(end)},
        'insolvency':row['insolvency'],'section13_notice':agent.VALUES[condition['status']],
        'reading_applies':row['reading_applies']}
    # A proposed change before the candidate notice date has insufficient notice,
    # even though the route event itself may be valid. Do not send a negative
    # interval to an API whose supported interval domain is nonnegative.
    reversed_order=(candidate is not None and end is not None and end['value']<candidate)
    if reversed_order:
        premises={'insolvency':row['insolvency'],'section13_notice':agent.VALUES[condition['status']], 'lower':False,'upper':True}
        necessary=agent.notice_condition(premises)
        applied=dispatch({'all':['necessary','reading_applies']},{'necessary':agent.VALUES[necessary['status']],'reading_applies':row['reading_applies']})
        notice={'scenario':derived,'premises':premises,'notice_precondition':necessary,'conditional_notice_precondition':applied,
            'exact_interval':{'order':'CHANGE_PRECEDES_DEEMED_NOTICE'},'actual_change_effective':'NOT_ESTABLISHED'}
    else:notice=agent.analyze(derived,instrument)
    return {'scenario':deepcopy(row),'route_preconditions':condition,'source_delay_days':delay,
        'arithmetic_candidate_date':candidate,'notice':notice,'candidate_date_is_actual_notice':False,
        'actual_delivery':'NOT_ESTABLISHED','actual_change_effective':'NOT_ESTABLISHED',
        'historical_application_proved':False,'complete_legal_test':False,
        'meaning':'Declared civil-date consequence composed with finite route premises; arithmetic alone does not establish valid notice'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established','historical_application_proved','complete_legal_test'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned delivery profile or complete prior answer changed')
    if any(profile[k] is not False for k in ('actual_event_established','historical_application_proved','complete_legal_test')):
        raise ValueError('Conditional dates cannot establish actual or complete legal status')
    source=context(products,ordinary)
    if profile['context']!=source:raise ValueError('Complete delivery source context changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not 1<=len(rows)<=128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded nonempty delivery scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Distinct delivery scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or first['route']!='UNKNOWN' or first['event'] is not None
            or first['proposed_change'] is not None or first['convention'] is not None
            or first['insolvency'] is not None or first['reading_applies'] is not None
            or any(v is not None for v in first['premises'].values())):
        raise ValueError('All-open delivery baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':source,'scenarios':[analyze(r,instrument) for r in rows],
        'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}!={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Delivery composition changed complete prior answer')
    if answer.get(KEY)!=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256):
        raise ValueError('Delivery answer differs from source reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(profile['scenarios'])}
