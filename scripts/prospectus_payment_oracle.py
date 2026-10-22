"""Independent integer payment clocks and source-formula comparisons."""
from copy import deepcopy
from scripts.prospectus_calendar_oracle import instant_number
from scripts.prospectus_cutoff_oracle import stamp,DAY
from scripts.prospectus_amount_oracle import decision,classify as amount_classify,scenarios as amounts

QUALIFICATIONS=('source_trigger_supported','counting_convention_supported','payment_state_supported')
FACTS=('default.notice','default.a.cured','representative.a.entrusted','representative.a.express_permission')
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def clock(row):
    c=row['clock'];raw=None;exact=None
    if c['trigger'] is not None:
        trigger=instant_number(c['trigger']['value']);convention=c['convention']
        if convention=='ELAPSED_30_DAYS_INCLUSIVE':limit=trigger+30*DAY;inclusive=True
        else:
            offset=c['utc_offset'];minutes=(int(offset[1:3])*60+int(offset[4:]))*(1 if offset[0]=='+' else -1)
            shift=minutes*60000000;day=(trigger+shift)//DAY;limit=(day+31)*DAY-shift;inclusive=False
        assessed=instant_number(c['assessment']['value']) if c['assessment'] is not None else None
        paid=instant_number(c['payment']['value']) if c['payment'] is not None else None
        expired=None if assessed is None else (assessed>limit if inclusive else assessed>=limit)
        timely=None if paid is None else (paid<=limit if inclusive else paid<limit)
        if expired is False:raw=False
        elif expired is True:raw=not timely if row['payment_state']=='FULL_PAYMENT' else True if row['payment_state']=='UNPAID_THROUGH_ASSESSMENT' else None
        exact={'trigger_utc':stamp(trigger),'limit_utc':stamp(limit),'limit_inclusive':inclusive,
            'assessment_utc':stamp(assessed) if assessed is not None else None,'payment_utc':stamp(paid) if paid is not None else None,
            'assessment_after_payment_window':expired,'payment_within_window':timely,'convention':convention,'fixed_utc_offset':c['utc_offset']}
    return raw,exact


def classify(row):
    raw,exact=clock(row);timing=decision([raw,*[row[k] for k in QUALIFICATIONS]],lambda *v:all(v));money=None
    if row['route']=='a':
        premise=decision([VALUE[timing],row['qualified_note_payment']],lambda *v:all(v))
        full=decision([*[row['other_facts'].get(k) for k in FACTS],VALUE[premise]],
            lambda notice,cured,entrusted,permission,payment:notice and payment and not cured and (not entrusted or permission))
    else:
        amount=deepcopy(row['amount_scenario']);amount['thirty_day_condition']=VALUE[timing];money=amount_classify(amount)
        premise=money['overdue'];full=money['default_c']
    return {'failure':raw,'exact':exact,'timing':timing,'premise':premise,'complete':full,'amount':money}


def projection(result):
    money=result['amount_review']
    return {'failure':result['failure_within_declared_window'],'exact':result['exact_payment_clock'],
        'timing':result['derived_thirty_day_condition']['status'],'premise':result['derived_source_payment_premise']['status'],
        'complete':result['complete_default']['status'],'amount':None if money is None else {
            'above':money['amount_above_threshold'],'overdue':money['derived_overdue']['status'],'default_c':money['complete_default_c']['status']}}


def case(name,instrument='bond',route='a',convention='ELAPSED_30_DAYS_INCLUSIVE',
         trigger='2024-01-01T00:00:00Z',assessment='2024-02-02T00:00:00Z',payment=None,state='UNPAID_THROUGH_ASSESSMENT'):
    money=None
    if route=='c':
        money=next(r for r in amounts(instrument) if r['id']=='above');money.pop('thirty_day_condition')
        money['id']=name;money['payment']['event_id']=name
    return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','route':route,'trigger_kind':'DUE_DATE',
        'clock':{'instrument_id':instrument,'event_id':name,'convention':convention,
            'utc_offset':'+00:00' if convention=='FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE' else None,
            'trigger':None if trigger is None else {'value':trigger,'role':'DUE_DATE'},
            'assessment':None if assessment is None else {'value':assessment,'role':'ASSESSMENT'},
            'payment':None if payment is None else {'value':payment,'role':'FULL_PAYMENT'}},
        'payment_state':state,**dict.fromkeys(QUALIFICATIONS,True),'qualified_note_payment':True if route=='a' else None,
        'other_facts':{**dict.fromkeys(FACTS,False),'default.notice':True} if route=='a' else None,'amount_scenario':money}


def scenarios(instrument):
    rows=[case('all-open',instrument,trigger=None,assessment=None,convention=None,state='UNKNOWN')]
    rows[0].update(**dict.fromkeys(QUALIFICATIONS,None),qualified_note_payment=None,other_facts={})
    for name,route,convention,trigger,assessment,payment,state in [
        ('elapsed-before','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-01-30T23:59:59.999999Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('elapsed-exact','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-01-31T00:00:00Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('elapsed-after','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-01-31T00:00:00.000001Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('timely-paid','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-01T00:00:00Z','2024-01-31T00:00:00Z','FULL_PAYMENT'),
        ('late-paid','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-01T00:00:00Z','2024-01-31T00:00:00.000001Z','FULL_PAYMENT'),
        ('advance-payment','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-01T00:00:00Z','2023-12-31T00:00:00Z','FULL_PAYMENT'),
        ('civil-last-microsecond','a','FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE','2024-01-01T12:00:00Z','2024-01-31T23:59:59.999999Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('civil-expired','a','FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE','2024-01-01T12:00:00Z','2024-02-01T00:00:00Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('civil-timely-paid','a','FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE','2024-01-01T12:00:00Z','2024-02-02T00:00:00Z','2024-01-31T23:59:59.999999Z','FULL_PAYMENT'),
        ('civil-late-paid','a','FIXED_OFFSET_CIVIL_DAY30_INCLUSIVE','2024-01-01T12:00:00Z','2024-02-02T00:00:00Z','2024-02-01T00:00:00Z','FULL_PAYMENT'),
        ('leap-clock','a','ELAPSED_30_DAYS_INCLUSIVE','2024-02-01T00:00:00Z','2024-03-02T00:00:00.000001Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('offset-equivalent','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T08:00:00+08:00','2024-01-31T00:00:00Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('unknown-payment','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-02T00:00:00Z',None,'UNKNOWN'),
        ('unknown-before-expiry','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-01-02T00:00:00Z',None,'UNKNOWN'),
        ('missing-trigger','a','ELAPSED_30_DAYS_INCLUSIVE',None,'2024-02-02T00:00:00Z',None,'UNKNOWN'),
        ('missing-assessment','a','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z',None,None,'UNKNOWN'),
        ('cross-default-overdue','c','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-02T00:00:00Z',None,'UNPAID_THROUGH_ASSESSMENT'),
        ('cross-default-unknown','c','ELAPSED_30_DAYS_INCLUSIVE','2024-01-01T00:00:00Z','2024-02-02T00:00:00Z',None,'UNKNOWN')]:
        rows.append(case(name,instrument,route,convention,trigger,assessment,payment,state))
    for field in (*QUALIFICATIONS,'qualified_note_payment'):
        for suffix,value in [('missing',None),('false',False),('conflict','conflict')]:
            row=case(field+'-'+suffix,instrument);row[field]=value;rows.append(row)
    for name,changed in [('cured',{'default.a.cured':True}),('no-notice',{'default.notice':False}),
        ('representative-restricted',{'representative.a.entrusted':True}),
        ('representative-permitted',{'representative.a.entrusted':True,'representative.a.express_permission':True})]:
        row=case(name,instrument);row['other_facts'].update(changed);rows.append(row)
    for name in ('guarantee-invoked','amount-exact','disputed','cross-cured','accelerated-no-payment','security-no-payment'):
        row=case(name,instrument,route='c')
        money=row['amount_scenario']
        if name=='guarantee-invoked':row['trigger_kind']='GUARANTEE_INVOCATION';row['clock']['trigger']['role']='GUARANTEE_INVOCATION'
        elif name=='amount-exact':money['payment']['amount']='200000000'
        elif name=='disputed':money['other_facts']['default.c.disputed']=True
        elif name=='cross-cured':money['other_facts']['default.c.cured']=True
        else:
            row['clock']['trigger']=None;row['payment_state']='UNKNOWN'
            money['payment']['amount']='1';money['other_facts']['default.c.'+name.split('-')[0]]=True
        rows.append(row)
    return rows
