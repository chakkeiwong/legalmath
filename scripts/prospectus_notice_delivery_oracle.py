"""Independent Gregorian date addition and finite route/notice expectations."""
from copy import deepcopy
from itertools import product
from scripts.prospectus_calendar_oracle import civil_number
from scripts.prospectus_agent_notice_oracle import condition


def add_days(value,days):
    civil_number(value)
    y,m,d=map(int,value.split('-'))
    for _ in range(days):
        leap=y%4==0 and (y%100!=0 or y%400==0)
        lengths=[31,29 if leap else 28,31,30,31,30,31,31,30,31,30,31]
        d+=1
        if d>lengths[m-1]:d=1;m+=1
        if m>12:m=1;y+=1
        if y>9999:raise ValueError('Independent year overflow')
    return f'{y:04d}-{m:02d}-{d:02d}'


def conjunction(values):
    if 'conflict' in values:return 'CONFLICT'
    possibilities=set()
    for row in product(*([False,True] if v is None else [v] for v in values)):possibilities.add(all(row))
    return 'UNKNOWN' if len(possibilities)==2 else 'YES' if True in possibilities else 'NO'


def expected(row):
    route=row['route'];premises=row['premises']
    required=['listed_in_lux','valid_route_event']
    if route=='CLEARING_SUBSTITUTION':required+=['exchange_rules_permit','issuer_elects_substitution']
    status='UNKNOWN' if route=='UNKNOWN' else conjunction([premises[k] for k in required])
    val={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}
    date=None;lower=upper=None
    if row['event'] is not None:
        date=add_days(row['event']['value'],3 if route=='PUBLICATION' else 7)
        if row['proposed_change'] is not None:
            interval=civil_number(row['proposed_change']['value'])-civil_number(date)
            lower,upper=interval>=30,interval<=45
    notice=condition({'insolvency':row['insolvency'],'section13_notice':val[status],'lower':lower,'upper':upper})
    applied=conjunction([val[notice],row['reading_applies']])
    return {'route':status,'date':date,'notice':notice,'conditional':applied}


def scenarios(instrument):
    identity={'instrument_id':instrument,'agent_id':'hypothetical-calculation-agent',
              'change_event_id':'hypothetical-agent-change','notice_id':'hypothetical-issuer-notice'}
    base={'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT','identity':identity,'route':'UNKNOWN',
          'convention':None,'event':None,'proposed_change':None,
          'premises':{k:None for k in ('listed_in_lux','valid_route_event','exchange_rules_permit','issuer_elects_substitution')},
          'insolvency':None,'reading_applies':None}
    rows=[deepcopy(base)]
    def dated(label,route,start,end):
        row=deepcopy(base);row.update(id=label,route=route,convention='CIVIL_DATE_GAP',insolvency=False,reading_applies=True)
        row['premises'].update(listed_in_lux=True,valid_route_event=True)
        if route=='CLEARING_SUBSTITUTION':row['premises'].update(exchange_rules_permit=True,issuer_elects_substitution=True)
        role='PUBLICATION_ON_LUX_EXCHANGE' if route=='PUBLICATION' else 'CLEARING_DELIVERY_FOR_FORWARDING'
        row['event']={**identity,'role':role,'value':start}
        row['proposed_change']={k:v for k,v in identity.items() if k!='notice_id'}
        row['proposed_change'].update(role='PROPOSED_CHANGE',value=end)
        return row
    for route in ('PUBLICATION','CLEARING_SUBSTITUTION'):
        delay=3 if route=='PUBLICATION' else 7
        for gap in (29,30,45,46):
            rows.append(dated(route+'-'+str(gap),route,'2024-01-01',add_days('2024-01-01',delay+gap)))
        rows.append(dated(route+'-naive-30-reverses',route,'2024-01-01','2024-01-31'))
        rows.append(dated(route+'-naive-46-reverses',route,'2024-01-01','2024-02-16'))
    for label,start in (('leap','2024-02-27'),('common-year','2023-02-27'),('year-end','2024-12-30'),('century-common','2100-02-27')):
        rows.append(dated(label,'PUBLICATION',start,add_days(start,33)))
    for key in ('listed_in_lux','valid_route_event','exchange_rules_permit','issuer_elects_substitution'):
        for value in (None,False,'conflict'):
            row=dated(key+'-'+str(value),'CLEARING_SUBSTITUTION','2024-01-01','2024-02-07');row['premises'][key]=value;rows.append(row)
    for part in ('event','proposed_change'):
        row=dated('missing-'+part,'PUBLICATION','2024-01-01','2024-02-03');row[part]=None;rows.append(row)
    for applies in (None,False,'conflict'):
        row=dated('applies-'+str(applies),'PUBLICATION','2024-01-01','2024-02-03');row['reading_applies']=applies;rows.append(row)
    row=dated('change-before-deemed-date','PUBLICATION','2024-01-01','2024-01-02');rows.append(row)
    row=deepcopy(row);row['id']='insolvency-before-deemed-date';row['insolvency']=True;rows.append(row)
    row=deepcopy(base);row.update(id='insolvency-no-route-or-dates',insolvency=True,reading_applies=True);rows.append(row)
    return rows
