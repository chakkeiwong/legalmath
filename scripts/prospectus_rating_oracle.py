"""Independent rating branches,integer timing and complete control-put oracle."""
from copy import deepcopy
from scripts.prospectus_calendar_oracle import civil_number,instant_number
from scripts.prospectus_amount_oracle import decision
from scripts import prospectus_cutoff_oracle as cutoff_oracle

QUALIFICATIONS=('agency_qualified','rating_subject_qualified','previously_assigned',
                'counting_convention_supported','grade_classification_supported')
FACTS=('control_put.control','control_put.event_notice','control_put.timely_exercise','control_put.valid_declaration',
       'control_put.delivery','control_put.payment_day','control_put.earlier_tax_notice',
       'representative.put.entrusted','representative.put.express_permission')
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def classify(row):
    events=row['events'];within=None;exact=None
    if events['control'] is not None and events['rating'] is not None:
        convention=events['convention'];start,end=(events[k]['value'] for k in ('control','rating'))
        if convention=='ELAPSED_24_HOUR_DAYS':gap=instant_number(end)-instant_number(start);right=120*86400000000;unit='microseconds'
        else:gap=civil_number(end)-civil_number(start);right=120;unit='civil_days'
        if gap<0:within=False;exact={'order':'RATING_PRECEDES_CONTROL','convention':convention}
        else:
            left=max(0,gap-1) if convention=='CLEAR_CIVIL_DAYS' else gap;within=left<=right
            exact={'left':str(left),'right':str(right),'operator':'LE','unit':unit,'convention':convention}
    before=None if row['before_grade']=='UNKNOWN' else row['before_grade']=='INVESTMENT_GRADE'
    after=None if row['after_grade']=='UNKNOWN' else row['after_grade']=='NON_INVESTMENT_GRADE'
    if row['rating_action']=='WITHDRAWAL':event=decision([row['previously_assigned']],lambda v:v)
    elif row['rating_action']=='DOWNGRADE':event=decision([row['previously_assigned'],before,after,row['grade_classification_supported']],lambda *v:all(v))
    else:event='UNKNOWN'
    causal=row['causal_link']['value'] if row['causal_link'] is not None else None
    derived=decision([VALUE[event],within,row['agency_qualified'],row['rating_subject_qualified'],row['counting_convention_supported'],causal],lambda *v:all(v))
    cutoff=None
    if row['cutoff_scenario'] is not None:
        other=deepcopy(row['cutoff_scenario']);other['other_facts']={**row['other_facts'],'control_put.rating':VALUE[derived]}
        cutoff=cutoff_oracle.classify(other);complete=cutoff['control_put']
    else:
        complete=decision([*[row['other_facts'].get(k) for k in FACTS],VALUE[derived]],
            lambda control,notice,timely,declaration,delivery,payment,tax,entrusted,permission,rating:
            control and notice and timely and declaration and delivery and payment and rating and not tax
            and (not entrusted or permission))
    return {'within':within,'exact':exact,'event':event,'rating':derived,'complete':complete,'cutoff':cutoff}


def projection(result):
    cutoff=result['cutoff_review']
    return {'within':result['within_120_day_window'],'exact':result['exact_rating_window'],
        'event':result['source_rating_event']['status'],'rating':result['derived_rating']['status'],
        'complete':result['complete_control_put']['status'],'cutoff':None if cutoff is None else cutoff_oracle.projection(cutoff)}


def case(name,instrument='bond',action='DOWNGRADE',control='2024-01-01',rating='2024-04-30',convention='CIVIL_DATE_GAP'):
    cid,rid=name+':control',name+':rating'
    return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','events':{'instrument_id':instrument,
        'control_event_id':cid,'rating_event_id':rid,'convention':convention,
        'control':None if control is None else {'event_id':cid,'role':'CONTROL_CHANGE','value':control},
        'rating':None if rating is None else {'event_id':rid,'role':'RATING_EVENT','value':rating}},
        'rating_action':action,'before_grade':'INVESTMENT_GRADE','after_grade':'NON_INVESTMENT_GRADE',
        **dict.fromkeys(QUALIFICATIONS,True),'causal_link':{'kind':'HYPOTHETICAL_CAUSAL_LINK','instrument_id':instrument,
            'control_event_id':cid,'rating_event_id':rid,'value':True},'cutoff_scenario':None,
        'other_facts':{**dict.fromkeys(FACTS,True),'control_put.earlier_tax_notice':False,
            'representative.put.entrusted':False,'representative.put.express_permission':False}}


def scenarios(instrument):
    rows=[case('all-open',instrument,'UNKNOWN',None,None,None)]
    rows[0].update(**dict.fromkeys(QUALIFICATIONS,None),causal_link=None,other_facts={},before_grade='UNKNOWN',after_grade='UNKNOWN')
    for name,control,rating,convention in [('day120','2024-01-01','2024-04-30','CIVIL_DATE_GAP'),
        ('day121','2024-01-01','2024-05-01','CIVIL_DATE_GAP'),('clear-day120','2024-01-01','2024-05-01','CLEAR_CIVIL_DAYS'),
        ('rating-before-control','2024-01-02','2024-01-01','CIVIL_DATE_GAP'),
        ('elapsed120','2024-01-01T00:00:00Z','2024-04-30T00:00:00Z','ELAPSED_24_HOUR_DAYS'),
        ('elapsed-after120','2024-01-01T00:00:00Z','2024-04-30T00:00:00.000001Z','ELAPSED_24_HOUR_DAYS'),
        ('spring-offset','2024-01-01T12:00:00+01:00','2024-04-30T12:00:00+02:00','ELAPSED_24_HOUR_DAYS'),
        ('missing-control',None,'2024-04-30','CIVIL_DATE_GAP'),('missing-rating','2024-01-01',None,'CIVIL_DATE_GAP')]:
        rows.append(case(name,instrument,control=control,rating=rating,convention=convention))
    for name,before,classification in [('withdrawal-noninvestment','NON_INVESTMENT_GRADE',True),
        ('withdrawal-grade-unknown','UNKNOWN',None),('withdrawal-classification-conflict','UNKNOWN','conflict')]:
        row=case(name,instrument,action='WITHDRAWAL');row.update(before_grade=before,after_grade='UNKNOWN',grade_classification_supported=classification);rows.append(row)
    for name,changes in [('unchanged-investment',{'after_grade':'INVESTMENT_GRADE'}),
        ('already-noninvestment',{'before_grade':'NON_INVESTMENT_GRADE'}),('unknown-prior-grade',{'before_grade':'UNKNOWN'}),
        ('unknown-action',{'rating_action':'UNKNOWN'})]:
        row=case(name,instrument);row.update(changes);rows.append(row)
    for field in QUALIFICATIONS:
        for suffix,value in [('missing',None),('false',False),('conflict','conflict')]:
            row=case(field+'-'+suffix,instrument);row[field]=value;rows.append(row)
    for name,value in [('causal-denied',False),('causal-unknown',None),('causal-conflict','conflict')]:
        row=case(name,instrument);row['causal_link']['value']=value;rows.append(row)
    row=case('chronology-only',instrument);row['causal_link']=None;rows.append(row)
    for name,changes in [('tax-exception',{'control_put.earlier_tax_notice':True}),
        ('exercise-unknown',{'control_put.timely_exercise':None}),('representative-restricted',{'representative.put.entrusted':True}),
        ('representative-permitted',{'representative.put.entrusted':True,'representative.put.express_permission':True})]:
        row=case(name,instrument);row['other_facts'].update(changes);rows.append(row)
    for name,receipt,causal in [('composed-timely','2024-06-15T17:00:00+02:00',True),
        ('composed-late','2024-06-15T17:00:00.000001+02:00',True),('composed-causal-unknown','2024-06-15T17:00:00+02:00',None)]:
        row=case(name,instrument);row['causal_link']['value']=causal;row['other_facts'].pop('control_put.timely_exercise')
        cutoff=cutoff_oracle.case(name,instrument,'2024-05-01T12:00:00+02:00',receipt)
        cutoff['other_facts']=None;row['cutoff_scenario']=cutoff;rows.append(row)
    return rows
