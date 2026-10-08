from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.duty_performance import project_contact,duty_state
from .support import packet


def fixture():
    p=packet();p['units'][0]['text']='During the blackout, for urgent STRs please contact the JFIU by email, phone or fax.'
    policy={'policy_id':'contact','source_packet_hash':digest(p),'source_evidence':[{'unit_id':'p1','quote':p['units'][0]['text']}],
       'counterparty_id':'jfiu','channels':['EMAIL','PHONE','FAX'],'from_inclusive':'2026-01-27T16:00:00.000000Z',
       'until_exclusive':'2026-02-02T01:00:00.000000Z','time_interpretation':'Declared fixture interval',
       'conditions':['Identity and urgency classifications remain supplied premises.']}
    at='2026-01-29T04:00:00.000000Z'
    c={'actor_id':'firm.a','counterparty_id':'jfiu','channel':'EMAIL','event':{'event_id':'contact.1',
       'str_id':'str.a','kind':'CONTACT','related_event_id':None,'occurred_at':'2026-01-29T03:00:00.000000Z',
       'recorded_at':'2026-01-29T03:00:00.000000Z','status':'CONFIRMED','evidence_ids':['record.1']}}
    cover={'actor_id':'firm.a','counterparty_id':'jfiu','channels':['EMAIL','PHONE','FAX'],'coverage':{
       'str_id':'str.a','kinds':['CONTACT'],'from_inclusive':policy['from_inclusive'],
       'through_inclusive':at,'recorded_at':at,'evidence_ids':['complete.assertion']}}
    return p,policy,c,cover,{'actor_id':'firm.a','str_id':'str.a','assessment_at':at,'known_at':at}


@pytest.mark.parametrize('change,expected',[('none','TRUE'),('actor','FALSE'),('recipient','FALSE'),('report','FALSE'),
    ('channel','FALSE'),('late','FALSE'),('recorded_late','FALSE'),('disputed','CONFLICT'),('no_history','UNKNOWN')])
def test_exact_actor_report_channel_and_historical_cutoff(change,expected):
    p,policy,c,cover,kw=fixture();contacts=[c];covers=[cover]
    if change=='actor':c['actor_id']='firm.b'
    elif change=='recipient':c['counterparty_id']='someone.else'
    elif change=='report':c['event']['str_id']='str.b'
    elif change=='channel':c['channel']='OTHER'
    elif change=='late':c['event'].update(occurred_at='2026-01-29T05:00:00.000000Z',recorded_at='2026-01-29T05:00:00.000000Z')
    elif change=='recorded_late':c['event']['recorded_at']='2026-01-29T05:00:00.000000Z'
    elif change=='disputed':c['event']['status']='DISPUTED'
    elif change=='no_history':contacts=[];covers=[]
    actual=project_contact(p,policy,contacts,covers,**kw)
    assert actual['status']==expected
    assert not duty_state({'status':'TRUE'},actual)['deadline_violation_established']


def test_partial_channel_history_does_not_prove_absence():
    p,policy,c,cover,kw=fixture();cover['channels']=['EMAIL']
    assert project_contact(p,policy,[],[cover],**kw)['status']=='UNKNOWN'


def test_same_event_id_cannot_be_attributed_to_two_actors():
    p,policy,c,cover,kw=fixture();other=deepcopy(c);other['actor_id']='firm.b'
    with pytest.raises(LegalMathError):project_contact(p,policy,[c,other],[cover],**kw)


def test_contact_is_not_overall_compliance_and_missing_contact_is_not_proved_breach():
    yes=duty_state({'status':'TRUE'},{'status':'TRUE'})
    no=duty_state({'status':'TRUE'},{'status':'FALSE'})
    assert yes['state']=='REQUIRED_CONTACT_OBSERVED' and no['state']=='REQUIRED_CONTACT_NOT_YET_OBSERVED'
    assert yes['overall_compliance']==no['overall_compliance']=='NOT_ESTABLISHED'
