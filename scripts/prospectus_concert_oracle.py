"""Separate truth-table reading of retained necessary coordination conditions."""
from scripts.prospectus_amount_oracle import decision
PREMISES=('coordination_by_agreement_or_other_means','understanding_about_voting','other_cooperation',
    'lasting_change_aim','substantial_direction_change_aim','individual_case_agreement_exception')
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def classify(row):
    necessary=decision([row['premises'][k] for k in PREMISES],
        lambda coordinate,vote,other,lasting,substantial,exception:coordinate and (vote or (other and lasting and substantial)) and not exception)
    applied=decision([VALUE[necessary],row['reading_applies']],lambda a,b:a and b)
    return {'necessary':necessary,'conditional':applied}


def projection(result):
    return {'necessary':result['necessary_conditions']['status'],'conditional':result['conditional_necessary_conditions']['status']}


def case(name,instrument='bond'):
    return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','pair':{'instrument_id':instrument,
        'control_event_id':name+':control','pair_id':name+':pair','left_person':'person-A','right_person':'person-B','target':'BASF_SE'},
        'premises':dict(zip(PREMISES,(True,True,False,False,False,False))),'reading_applies':True}


def scenarios(instrument):
    rows=[case('all-open',instrument)];rows[0].update(premises=dict.fromkeys(PREMISES,None),reading_applies=None)
    for name,values in [('voting-understanding-no-lasting-aim',(True,True,False,False,False,False)),
        ('other-cooperation-qualified',(True,False,True,True,True,False)),
        ('other-without-lasting',(True,False,True,False,True,False)),
        ('other-without-substantial',(True,False,True,True,False,False)),
        ('parallel-vote-only',(False,False,False,False,False,False)),
        ('individual-case-exception',(True,True,False,False,False,True))]:
        r=case(name,instrument);r['premises']=dict(zip(PREMISES,values));rows.append(r)
    for key in PREMISES:
        for suffix,value in [('missing',None),('conflict','conflict')]:
            r=case(key+'-'+suffix,instrument);r['premises'][key]=value;rows.append(r)
    for suffix,value in [('unknown',None),('denied',False),('conflict','conflict')]:
        r=case('reading-'+suffix,instrument);r['reading_applies']=value;rows.append(r)
    return rows
