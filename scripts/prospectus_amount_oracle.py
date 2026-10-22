"""Separate integer-scaled amount oracle and manually transcribed default formula."""
from copy import deepcopy
from itertools import product

FACTS=('default.notice','default.c.accelerated','default.c.disputed','default.c.security',
       'default.c.cured','default.quorum','default.other_at_receipt',
       'representative.c.entrusted','representative.c.express_permission')


def rational(value):
    a=value.split('.');return int(''.join(a)),10**(len(a[1]) if len(a)==2 else 0)


def decision(values,formula):
    if any(v=='conflict' for v in values):return 'CONFLICT'
    outcomes={formula(*world) for world in product(*[(False,True) if v is None else (v,) for v in values])}
    return 'YES' if outcomes=={True} else 'NO' if outcomes=={False} else 'UNKNOWN'


def classify(row):
    p=row['payment'];above=None
    if p['amount'] is not None and (p['currency']=='EUR' or p['fx'] is not None):
        n,d=rational(p['amount']);rn,rd=(1,1) if p['currency']=='EUR' else rational(p['fx']['rate'])
        above=n*rn>200000000*d*rd
    overdue=decision([above,row['qualified_obligation'],row['thirty_day_condition'],row['currency_basis_supported']],lambda *v:all(v))
    values=[row['other_facts'].get(n) for n in FACTS]
    values.append({'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[overdue])
    outcome=decision(values,lambda notice,accelerated,disputed,security,cured,quorum,other,entrusted,permission,overdue:
        notice and (accelerated or (overdue and not disputed) or security) and not cured
        and (quorum or other) and (not entrusted or permission))
    return {'above':above,'overdue':overdue,'default_c':outcome}


def projection(actual):
    return {'above':actual['amount_above_threshold'],'overdue':actual['derived_overdue']['status'],
            'default_c':actual['complete_default_c']['status']}


def scenarios(instrument):
    def case(name,amount='200000000.01',currency='EUR',rate=None):
        fx=None if rate is None else {'instrument_id':instrument,'event_id':name,'source_currency':currency,
            'target_currency':'EUR','unit':'EUR_PER_SOURCE_UNIT','rate':rate}
        return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','payment':{'instrument_id':instrument,
            'event_id':name,'amount':amount,'currency':currency,'fx':fx},'qualified_obligation':True,
            'thirty_day_condition':True,'currency_basis_supported':True,
            'other_facts':{**dict.fromkeys(FACTS,False),'default.notice':True,'default.quorum':True}}
    rows=[case('all-open',None)]
    rows[0].update(qualified_obligation=None,thirty_day_condition=None,currency_basis_supported=None,other_facts={})
    for name,amount in [('below','199999999.99'),('exact','200000000'),('above','200000000.01'),
                        ('large-precise','200000000.0000000000000000000001'),('zero','0'),('missing',None)]:
        rows.append(case(name,amount))
    rows.extend([case('fx-exact','250000000','USD','0.8'),case('fx-below','250000000','USD','0.799999999999999999999'),
                 case('fx-above','250000000','USD','0.800000000000000000001'),case('fx-missing','250000000','USD')])
    for field in ('qualified_obligation','thirty_day_condition','currency_basis_supported'):
        for suffix,value in [('missing',None),('false',False),('conflict','conflict')]:
            row=case(field+'-'+suffix);row[field]=value;rows.append(row)
    for name,changes in [('good-faith-dispute',{'default.c.disputed':True}),('cured',{'default.c.cured':True}),
        ('notice-missing',{'default.notice':None}),('quorum-missing',{'default.quorum':None}),
        ('representative-restricted',{'representative.c.entrusted':True}),
        ('representative-permission',{'representative.c.entrusted':True,'representative.c.express_permission':True}),
        ('other-ground-at-receipt',{'default.quorum':False,'default.other_at_receipt':True})]:
        row=case(name);row['other_facts'].update(changes);rows.append(row)
    for branch in ('accelerated','security'):
        for amount in ('1',None):
            row=case(branch+'-'+('missing' if amount is None else 'small'),amount)
            row['other_facts']['default.c.'+branch]=True;rows.append(row)
    return rows
