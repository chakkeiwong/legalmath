"""Conditional Frankfurt exercise cutoff for the selected control-put clause."""
import base64,hashlib,json
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
from .successor import calendar_facts
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch,names

VERSION='basf-frankfurt-cutoff.v1'
KEY='frankfurt_cutoff_review'
NODE='basf-redemption:control_put'
COMPUTED='control_put.timely_exercise'
TZIF_SHA256='5ee475f71a0fc1a32faeb849f8c39c6e7aa66d6d41ec742b97b3a7436b3b0701'
CONVENTIONS={'PUBLICATION_INSTANT_INCLUSIVE','NEXT_LOCAL_DAY_INCLUSIVE'}
QUALIFICATIONS=('publication_is_event_notice','receipt_at_designated_office',
                'counting_convention_supported','timezone_basis_supported')
ROLES={'publication':'event_notice_publication','receipt':'fiscal_agent_exercise_receipt'}


def timezone_fixture():
    return json.loads((Path(__file__).parent/'successor/frankfurt_timezone.json').read_text())


def timezone_model():
    fixture=timezone_fixture()
    if (fixture.get('zone')!='Europe/Berlin' or fixture.get('version')!='2026c'
            or fixture.get('tzif_sha256')!=TZIF_SHA256):
        raise ValueError('Pinned Frankfurt timezone identity changed')
    try:blob=base64.b64decode(fixture['tzif_base64'],validate=True)
    except (KeyError,TypeError,ValueError) as error:raise ValueError('Malformed pinned timezone bytes') from error
    if hashlib.sha256(blob).hexdigest()!=TZIF_SHA256:
        raise ValueError('Pinned Frankfurt timezone bytes changed')
    return ZoneInfo.from_file(BytesIO(blob),key='Europe/Berlin'),fixture


def context(products):
    rows=[n for n in products['P3']['payload']['clauses']['nodes'] if n['id']==NODE]
    if (len(rows)!=1 or rows[0]['effect']!='repayment'
            or 'nach 17:00 Uhr Frankfurt am Main Zeit am 45. Tag' not in rows[0]['quote']
            or rows[0]['exceptions']!='control_put.earlier_tax_notice'):
        raise ValueError('Complete selected control-put cutoff and tax exception required')
    return deepcopy(rows[0])


def analyze(row,node,instrument):
    keys={'id','kind','interval','other_facts',*QUALIFICATIONS};fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical cutoff scenario required')
    for key in QUALIFICATIONS:
        v=row[key]
        if v is not None and v!='conflict' and type(v) is not bool:
            raise ValueError('Cutoff qualifications must be Boolean,unknown or conflict')
    interval=row['interval'];keys={'instrument_id','event_id','publication','receipt','convention'}
    fields(interval,keys,keys)
    if interval['instrument_id']!=instrument or interval['event_id']!=row['id']:
        raise ValueError('Cutoff instrument or event mismatch')
    convention=interval['convention'];empty=interval['publication'] is None and interval['receipt'] is None
    if not (convention is None and empty):
        if not isinstance(convention,str) or convention not in CONVENTIONS:
            raise ValueError('Explicit supported cutoff convention required')
    zone,fixture=timezone_model();values={};unresolved=[]
    for label in ('publication','receipt'):
        operand=interval[label]
        if operand is None:unresolved.append('Missing '+label);continue
        fields(operand,{'value','role'},{'value','role'})
        if operand['role']!=ROLES[label]:raise ValueError('Cutoff publication or receipt role mismatch')
        value=calendar_facts.operand_value(operand['value'],'ELAPSED_24_HOUR_DAYS')
        local=value.astimezone(zone)
        if not 2000<=local.year<=2030:raise ValueError('Cutoff outside reviewed2000–2030 domain')
        values[label]=value.astimezone(timezone.utc)
    timely=None;exact=None
    if 'publication' in values:
        publication=values['publication'];day=publication.astimezone(zone).date();deadline_day=day+timedelta(days=45)
        payment_day=deadline_day+timedelta(days=15)
        if payment_day.year>2030:raise ValueError('Computed cutoff/payment day outside reviewed domain')
        deadline=datetime.combine(deadline_day,datetime.min.time().replace(hour=17),tzinfo=zone).astimezone(timezone.utc)
        first=(publication if convention=='PUBLICATION_INSTANT_INCLUSIVE' else
            datetime.combine(day+timedelta(days=1),datetime.min.time(),tzinfo=zone).astimezone(timezone.utc))
        receipt=values.get('receipt')
        if receipt is not None:timely=first<=receipt<=deadline
        exact={'publication_frankfurt':publication.astimezone(zone).isoformat(),
            'earliest_utc':first.isoformat(),'deadline_utc':deadline.isoformat(),
            'deadline_frankfurt':deadline.astimezone(zone).isoformat(),
            'receipt_utc':receipt.isoformat() if receipt is not None else None,
            'expected_payment_date':payment_day.isoformat(),'convention':convention,
            'deadline_inclusive':True,'timezone_sha256':fixture['tzif_sha256']}
    qualifications={'within_declared_window':timely,**{k:row[k] for k in QUALIFICATIONS}}
    derived=dispatch({'all':list(qualifications)},qualifications)
    expression={'all':[node['conditions'],{'not':node['exceptions']}]}
    allowed=names(expression)-{COMPUTED};facts=row['other_facts'];fields(facts,allowed)
    if any(v is not None and v!='conflict' and type(v) is not bool for v in facts.values()):
        raise ValueError('Control-put premises must be Boolean,unknown or conflict')
    observations={**facts,COMPUTED:{'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[derived['status']]}
    return {'scenario':deepcopy(row),'within_declared_window':timely,'exact_cutoff':exact,
        'unresolved_interval':unresolved,'derived_timely_exercise':derived,'cutoff_premises':qualifications,
        'complete_control_put':dispatch(expression,observations),'derived_observations':observations,
        'actual_exercise':'NOT_ESTABLISHED','actual_payment_day':'NOT_ESTABLISHED',
        'legal_counting_convention_established':False,'timezone_applicability_established':False,
        'meaning':'Conditional exercised-repayment calculation; missing issuer notice does not extinguish the underlying option'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established','timezone_sha256'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned cutoff profile or complete baseline changed')
    if profile['actual_event_established'] is not False:raise ValueError('Conditional cutoff cannot establish actual exercise')
    _,fixture=timezone_model()
    if profile['timezone_sha256']!=digest(fixture):raise ValueError('Complete cutoff timezone fixture changed')
    node=context(products)
    if profile['context']!=node:raise ValueError('Complete control-put source context changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not rows or len(rows)>128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded hypothetical cutoff scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):raise ValueError('Distinct cutoff scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or first['other_facts'] or any(first[k] is not None for k in QUALIFICATIONS)
            or any(first['interval'][k] is not None for k in ('publication','receipt','convention'))):
        raise ValueError('Explicit all-open cutoff baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':node,'timezone_fixture':fixture,
        'scenarios':[analyze(row,node,instrument) for row in rows],
        'actual_event_established':False,'classification':'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
                !={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Complete cutoff answer changed baseline or digest')
    expected=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY)!=expected:raise ValueError('Computed cutoff answer differs from full reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(expected['scenarios'])}
