"""Conditional, attributed performance evidence distinct from a duty trigger."""
from copy import deepcopy
from typing import Literal
from pydantic import Field
from ...canonical import digest
from ...domain import timestamp
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, parse
from ..search.models import Quote
from .semantics import check_quotes
from .temporal_inputs import Event, Coverage, project


class Contact(Strict):
    event: Event
    actor_id: Id
    counterparty_id: Id
    channel: Literal['EMAIL','PHONE','FAX','OTHER']


class ContactCoverage(Strict):
    coverage: Coverage
    actor_id: Id
    counterparty_id: Id
    channels: list[Literal['EMAIL','PHONE','FAX','OTHER']] = Field(min_length=1,max_length=4)


class ContactPolicy(Strict):
    policy_id: Id
    source_packet_hash: str
    source_evidence: list[Quote] = Field(min_length=1,max_length=12)
    counterparty_id: Id
    channels: list[Literal['EMAIL','PHONE','FAX']] = Field(min_length=1,max_length=3)
    from_inclusive: Text
    until_exclusive: Text
    time_interpretation: Text
    conditions: list[Text] = Field(min_length=1,max_length=12)


def project_contact(packet,policy,contacts,coverage,*,actor_id,str_id,assessment_at,known_at):
    if len(contacts)>2000 or len(coverage)>100:raise LegalMathError('E_RESOURCE_LIMIT')
    p=parse(ContactPolicy,policy)
    if p['source_packet_hash']!=digest(packet):raise LegalMathError('E_STALE_REVIEW')
    check_quotes(p['source_evidence'],packet)
    for t in (p['from_inclusive'],p['until_exclusive'],assessment_at,known_at):timestamp(t)
    if p['from_inclusive']>=p['until_exclusive']:raise LegalMathError('E_TIME')
    if len(p['channels'])!=len(set(p['channels'])):raise LegalMathError('E_DUPLICATE_ID')
    class Subject(Strict):
        actor_id: Id
        str_id: Id
    parse(Subject,{'actor_id':actor_id,'str_id':str_id})
    cs=[parse(Contact,c) for c in contacts];cover=[parse(ContactCoverage,c) for c in coverage]
    all_events={}
    for c in cs:
        e=c['event']
        timestamp(e['occurred_at']);timestamp(e['recorded_at'])
        if e['recorded_at']<e['occurred_at']:raise LegalMathError('E_TIME')
        if e['kind']!='CONTACT':raise LegalMathError('E_EVENT_ATTRIBUTION')
        if e['related_event_id'] is not None:raise LegalMathError('E_EVENT_ATTRIBUTION')
        if e['event_id'] in all_events and c!=all_events[e['event_id']]:raise LegalMathError('E_EVENT_ID_COLLISION')
        all_events[e['event_id']]=c
    for c in cover:
        v=c['coverage']
        for name in ('from_inclusive','through_inclusive','recorded_at'):timestamp(v[name])
        if v['from_inclusive']>v['through_inclusive'] or v['recorded_at']<v['through_inclusive']:raise LegalMathError('E_TIME')
        if len(set(c['channels']))!=len(c['channels']):raise LegalMathError('E_DUPLICATE_ID')
    if not p['from_inclusive']<=assessment_at<p['until_exclusive']:
        return {'status':'OUT_OF_SCOPE','question':'Contact observed during the declared blackout interval',
                'legal_performance_established':False,'release_eligible':False}
    selected=[c['event'] for c in cs if c['actor_id']==actor_id and c['counterparty_id']==p['counterparty_id']
              and c['channel'] in p['channels']]
    covered=[c['coverage'] for c in cover if c['actor_id']==actor_id and c['counterparty_id']==p['counterparty_id']
             and set(p['channels'])<=set(c['channels'])]
    result=project(selected,covered,str_id=str_id,kind='CONTACT',since=p['from_inclusive'],
                   assessment_at=assessment_at,known_at=known_at)
    return {**result,'policy_hash':digest(p),'actor_id':actor_id,
            'scope':'Observed contact with the named recipient through a listed channel for this STR and actor',
            'remaining_premises':p['conditions'],'deadline_violation_established':False}


def duty_state(trigger,performance):
    allowed={'TRUE','FALSE','UNKNOWN','CONFLICT','OUT_OF_SCOPE','ERROR'}
    if trigger['status'] not in allowed or performance['status'] not in allowed:raise LegalMathError('E_SCHEMA')
    t,p=trigger['status'],performance['status']
    state=('INPUT_CONFLICT' if 'CONFLICT' in (t,p) else 'EVALUATION_ERROR' if 'ERROR' in (t,p)
           else 'TRIGGER_NOT_ESTABLISHED' if t=='FALSE' else 'OUTSIDE_DECLARED_SCOPE' if 'OUT_OF_SCOPE' in (t,p)
           else 'TRIGGER_UNCERTAIN' if t!='TRUE' else 'REQUIRED_CONTACT_OBSERVED' if p=='TRUE'
           else 'REQUIRED_CONTACT_NOT_YET_OBSERVED' if p=='FALSE' else 'PERFORMANCE_HISTORY_INCOMPLETE')
    return {'state':state,'trigger':deepcopy(trigger),'performance':deepcopy(performance),
            'overall_compliance':'NOT_ESTABLISHED','deadline_violation_established':False,'release_eligible':False}
