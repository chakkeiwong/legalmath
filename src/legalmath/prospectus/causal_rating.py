"""Source-defined conditional rating event; chronology does not prove causation."""
from copy import deepcopy
from . import frankfurt_cutoff
from .successor import calendar_facts
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch,names

VERSION='basf-causal-rating.v1'
KEY='causal_rating_review'
COMPUTED='control_put.rating'
QUALIFICATIONS=('agency_qualified','rating_subject_qualified','previously_assigned',
                'counting_convention_supported','grade_classification_supported')
GRADES={'INVESTMENT_GRADE','NON_INVESTMENT_GRADE','UNKNOWN'}
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def context(products):
    node=frankfurt_cutoff.context(products)
    if not all(s in node['quote'] for s in ('auf Grund des Kontrollwechsels','120 Tage','zurückgezogen','Investment Grade Rating')):
        raise ValueError('Complete source rating alternatives and causal requirement required')
    return node


def boolean(value):
    if value is not None and value!='conflict' and type(value) is not bool:
        raise ValueError('Rating premises must be Boolean,unknown or conflict')


def analyze(row,node,instrument):
    keys={'id','kind','events','rating_action','before_grade','after_grade','causal_link',
          'other_facts','cutoff_scenario',*QUALIFICATIONS}
    fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical rating scenario required')
    for key in QUALIFICATIONS:boolean(row[key])
    action=row['rating_action']
    if not isinstance(action,str) or action not in {'WITHDRAWAL','DOWNGRADE','UNKNOWN'}:
        raise ValueError('Explicit rating event alternative required')
    for key in ('before_grade','after_grade'):
        if not isinstance(row[key],str) or row[key] not in GRADES:raise ValueError('Declared supported rating category required')
    events=row['events'];keys={'instrument_id','control_event_id','rating_event_id','control','rating','convention'}
    fields(events,keys,keys)
    if events['instrument_id']!=instrument:raise ValueError('Rating instrument mismatch')
    identifiers=[events[k] for k in ('control_event_id','rating_event_id')]
    if any(not isinstance(v,str) or not v for v in identifiers) or len(set(identifiers))!=2:
        raise ValueError('Distinct control and rating event identities required')
    convention=events['convention'];empty=events['control'] is None and events['rating'] is None
    if not (convention is None and empty):
        if not isinstance(convention,str) or convention not in calendar_facts.CONVENTIONS:
            raise ValueError('Explicit supported rating-window convention required')
    values={};unresolved=[]
    for label,role in (('control','CONTROL_CHANGE'),('rating','RATING_EVENT')):
        item=events[label]
        if item is None:unresolved.append('Missing '+label+' date');continue
        fields(item,{'event_id','role','value'},{'event_id','role','value'})
        if item['event_id']!=events[label+'_event_id'] or item['role']!=role:raise ValueError('Rating date event or role mismatch')
        values[label]=calendar_facts.operand_value(item['value'],convention)
    within=None;exact=None
    if len(values)==2:
        if values['rating']<values['control']:
            within=False;exact={'order':'RATING_PRECEDES_CONTROL','convention':convention}
        else:within,exact=calendar_facts.compare(values['control'],values['rating'],convention,120,'LE')
    causal=None;link=row['causal_link']
    if link is not None:
        keys={'kind','instrument_id','control_event_id','rating_event_id','value'};fields(link,keys,keys)
        if (link['kind']!='HYPOTHETICAL_CAUSAL_LINK' or link['instrument_id']!=instrument
                or any(link[k]!=events[k] for k in ('control_event_id','rating_event_id'))):
            raise ValueError('Only disclosed hypothetical causal linkage to these exact events is supported')
        boolean(link['value']);causal=link['value']
    before=None if row['before_grade']=='UNKNOWN' else row['before_grade']=='INVESTMENT_GRADE'
    after=None if row['after_grade']=='UNKNOWN' else row['after_grade']=='NON_INVESTMENT_GRADE'
    if action=='WITHDRAWAL':event=dispatch('assigned',{'assigned':row['previously_assigned']})
    elif action=='DOWNGRADE':
        event=dispatch({'all':['assigned','before','after','classification']},{'assigned':row['previously_assigned'],
            'before':before,'after':after,'classification':row['grade_classification_supported']})
    else:event=dispatch('action',{'action':None})
    premises={'source_rating_event':VALUE[event['status']],'within_120_day_window':within,
        'agency_qualified':row['agency_qualified'],'rating_subject_qualified':row['rating_subject_qualified'],
        'counting_convention_supported':row['counting_convention_supported'],'due_to_control_change':causal}
    derived=dispatch({'all':list(premises)},premises)
    expression={'all':[node['conditions'],{'not':node['exceptions']}]}
    facts=row['other_facts'];fields(facts,names(expression)-{COMPUTED})
    for value in facts.values():boolean(value)
    cutoff_review=None;observations={**facts,COMPUTED:VALUE[derived['status']]}
    if row['cutoff_scenario'] is not None:
        cutoff=deepcopy(row['cutoff_scenario'])
        if not isinstance(cutoff,dict) or cutoff.get('id')!=row['id'] or cutoff.get('other_facts') is not None:
            raise ValueError('Cutoff composition requires shared scenario and no embedded premise overrides')
        if frankfurt_cutoff.COMPUTED in facts:raise ValueError('Computed cutoff cannot also be supplied')
        cutoff['other_facts']=observations
        cutoff_review=frankfurt_cutoff.analyze(cutoff,node,instrument)
        observations=cutoff_review['derived_observations'];complete=cutoff_review['complete_control_put']
    else:complete=dispatch(expression,observations)
    return {'scenario':deepcopy(row),'within_120_day_window':within,'exact_rating_window':exact,
        'unresolved_dates':unresolved,'source_rating_event':event,'rating_premises':premises,
        'derived_rating':derived,'cutoff_review':cutoff_review,'derived_observations':observations,
        'complete_control_put':complete,'actual_causal_link':'NOT_ESTABLISHED','actual_rating_event':'NOT_ESTABLISHED',
        'automatic_rating_classification':False,'meaning':'Conditional source consequences; chronology alone never supplies causation'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned rating profile or complete baseline changed')
    if profile['actual_event_established'] is not False:raise ValueError('Conditional rating cannot establish actual causal events')
    node=context(products)
    if profile['context']!=node:raise ValueError('Complete control-put rating source changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not rows or len(rows)>128 or any(not isinstance(r,dict) for r in rows):raise ValueError('Bounded rating scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Distinct rating scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or first['other_facts'] or first['rating_action']!='UNKNOWN'
            or any(first[k] is not None for k in (*QUALIFICATIONS,'causal_link','cutoff_scenario'))
            or any(first['events'][k] is not None for k in ('control','rating','convention'))
            or any(first[k]!='UNKNOWN' for k in ('before_grade','after_grade'))):
        raise ValueError('Explicit all-open rating baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':node,'scenarios':[analyze(r,node,instrument) for r in rows],
        'actual_event_established':False,'classification':'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
                !={k:v for k,v in ordinary.items() if k!='report_sha256'}):raise ValueError('Complete rating answer changed baseline or digest')
    expected=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY)!=expected:raise ValueError('Computed rating answer differs from full reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(expected['scenarios'])}
