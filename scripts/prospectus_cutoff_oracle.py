"""Independent Gregorian/UTC cutoff oracle within the reviewed2000–2030 domain."""
from itertools import product
from scripts.prospectus_calendar_oracle import civil_number,instant_number

DAY=86400000000
TZIF_SHA256='5ee475f71a0fc1a32faeb849f8c39c6e7aa66d6d41ec742b97b3a7436b3b0701'
QUALIFICATIONS=('publication_is_event_notice','receipt_at_designated_office',
                'counting_convention_supported','timezone_basis_supported')
FACTS=('control_put.control','control_put.rating','control_put.event_notice','control_put.valid_declaration',
       'control_put.delivery','control_put.payment_day','control_put.earlier_tax_notice',
       'representative.put.entrusted','representative.put.express_permission')


def civil_string(number):
    low,high=1,10000
    while low+1<high:
        middle=(low+high)//2
        if civil_number(f'{middle:04d}-01-01')<=number:low=middle
        else:high=middle
    year=low;remaining=number-civil_number(f'{year:04d}-01-01')
    leap=year%4==0 and (year%100!=0 or year%400==0)
    lengths=(31,29 if leap else 28,31,30,31,30,31,31,30,31,30,31)
    month=1
    for length in lengths:
        if remaining<length:break
        remaining-=length;month+=1
    return f'{year:04d}-{month:02d}-{remaining+1:02d}'


def offset_hours(instant):
    year=int(civil_string(instant//DAY)[:4])
    # Buffer UTC years permit the edges of the declared local-calendar domain.
    if not 1999<=year<=2031:raise ValueError('Independent timezone domain')
    boundaries=[]
    for month in (3,10):
        last=civil_number(f'{year:04d}-{month:02d}-31')
        sunday=last-((last+1)%7)
        boundaries.append(sunday*DAY+3600000000)
    return 2 if boundaries[0]<=instant<boundaries[1] else 1


def stamp(instant,offset=0):
    local=instant+offset*3600000000;day,clock=divmod(local,DAY)
    whole,micro=divmod(clock,1000000);hour,rem=divmod(whole,3600);minute,second=divmod(rem,60)
    fraction=f'.{micro:06d}' if micro else ''
    return f'{civil_string(day)}T{hour:02d}:{minute:02d}:{second:02d}{fraction}+{offset:02d}:00'


def local_instant(day,hour):
    # Midnight always has the offset of the preceding UTC22:00;17:00 has noon's offset.
    probe=day*DAY+(-2 if hour==0 else 12)*3600000000
    return day*DAY+hour*3600000000-offset_hours(probe)*3600000000


def decision(values,formula):
    if any(v=='conflict' for v in values):return 'CONFLICT'
    outcomes={formula(*world) for world in product(*[(False,True) if v is None else (v,) for v in values])}
    return 'YES' if outcomes=={True} else 'NO' if outcomes=={False} else 'UNKNOWN'


def classify(row):
    interval=row['interval'];timely=None;exact=None
    if interval['publication'] is not None:
        publication=instant_number(interval['publication']['value']);offset=offset_hours(publication)
        day=(publication+offset*3600000000)//DAY;deadline=local_instant(day+45,17)
        convention=interval['convention'];first=publication if convention=='PUBLICATION_INSTANT_INCLUSIVE' else local_instant(day+1,0)
        receipt=instant_number(interval['receipt']['value']) if interval['receipt'] is not None else None
        if receipt is not None:timely=first<=receipt<=deadline
        exact={'publication_frankfurt':stamp(publication,offset),'earliest_utc':stamp(first),
            'deadline_utc':stamp(deadline),'deadline_frankfurt':stamp(deadline,offset_hours(deadline)),
            'receipt_utc':stamp(receipt) if receipt is not None else None,'expected_payment_date':civil_string(day+60),
            'convention':convention,'deadline_inclusive':True,'timezone_sha256':TZIF_SHA256}
    derived=decision([timely,*[row[k] for k in QUALIFICATIONS]],lambda *v:all(v))
    values=[row['other_facts'].get(k) for k in FACTS]
    values.append({'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[derived])
    full=decision(values,lambda control,rating,notice,declaration,delivery,payment,tax,entrusted,permission,timely:
        control and rating and notice and declaration and delivery and payment and timely and not tax
        and (not entrusted or permission))
    return {'timely':timely,'exact':exact,'derived':derived,'control_put':full}


def projection(result):
    return {'timely':result['within_declared_window'],'exact':result['exact_cutoff'],
        'derived':result['derived_timely_exercise']['status'],'control_put':result['complete_control_put']['status']}


def case(name,instrument='bond',publication='2024-01-01T12:00:00+01:00',
         receipt='2024-02-15T17:00:00+01:00',convention='NEXT_LOCAL_DAY_INCLUSIVE'):
    return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','interval':{'instrument_id':instrument,'event_id':name,
        'convention':convention,'publication':None if publication is None else {'value':publication,'role':'event_notice_publication'},
        'receipt':None if receipt is None else {'value':receipt,'role':'fiscal_agent_exercise_receipt'}},
        **dict.fromkeys(QUALIFICATIONS,True),'other_facts':{**dict.fromkeys(FACTS,True),
        'control_put.earlier_tax_notice':False,'representative.put.entrusted':False,'representative.put.express_permission':False}}


def scenarios(instrument):
    rows=[case('all-open',instrument,None,None,None)]
    rows[0].update(**dict.fromkeys(QUALIFICATIONS,None),other_facts={})
    for name,publication,receipt,convention in [
        ('winter-exact','2024-01-01T12:00:00+01:00','2024-02-15T17:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('winter-late','2024-01-01T12:00:00+01:00','2024-02-15T17:00:00.000001+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('summer-exact','2024-06-01T12:00:00+02:00','2024-07-16T17:00:00+02:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('spring-crossing','2024-03-01T12:00:00+01:00','2024-04-15T15:00:00Z','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('autumn-crossing','2024-10-01T12:00:00+02:00','2024-11-15T16:00:00Z','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('spring-transition-deadline','2024-02-15T12:00:00+01:00','2024-03-31T17:00:00+02:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('autumn-transition-deadline','2024-09-12T12:00:00+02:00','2024-10-27T17:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('leap-day','2024-02-29T12:00:00+01:00','2024-04-14T17:00:00+02:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('year-crossing','2023-12-01T12:00:00+01:00','2024-01-15T17:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('foreign-offset','2024-01-01T19:00:00+08:00','2024-02-16T00:00:00+08:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('repeat-hour-first','2024-10-01T12:00:00+02:00','2024-10-27T02:30:00+02:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('repeat-hour-second','2024-10-01T12:00:00+02:00','2024-10-27T02:30:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('before-publication','2024-01-01T12:00:00+01:00','2024-01-01T11:00:00+01:00','PUBLICATION_INSTANT_INCLUSIVE'),
        ('same-day-included','2024-01-01T12:00:00+01:00','2024-01-01T13:00:00+01:00','PUBLICATION_INSTANT_INCLUSIVE'),
        ('same-day-excluded','2024-01-01T12:00:00+01:00','2024-01-01T13:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('next-day-exact','2024-01-01T12:00:00+01:00','2024-01-02T00:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('domain-start','2000-01-01T00:00:00+01:00','2000-02-15T17:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('missing-publication',None,'2024-02-15T17:00:00+01:00','NEXT_LOCAL_DAY_INCLUSIVE'),
        ('missing-receipt','2024-01-01T12:00:00+01:00',None,'NEXT_LOCAL_DAY_INCLUSIVE')]:
        rows.append(case(name,instrument,publication,receipt,convention))
    for field in QUALIFICATIONS:
        for suffix,value in [('missing',None),('false',False),('conflict','conflict')]:
            row=case(field+'-'+suffix,instrument);row[field]=value;rows.append(row)
    for name,changed in [('earlier-tax-call',{'control_put.earlier_tax_notice':True}),
        ('rating-causality-unknown',{'control_put.rating':None}),('event-notice-missing',{'control_put.event_notice':None}),
        ('invalid-declaration',{'control_put.valid_declaration':False}),('no-delivery',{'control_put.delivery':False}),
        ('payment-day-unknown',{'control_put.payment_day':None}),('representative-restricted',{'representative.put.entrusted':True}),
        ('representative-permission',{'representative.put.entrusted':True,'representative.put.express_permission':True})]:
        row=case(name,instrument);row['other_facts'].update(changed);rows.append(row)
    return rows
