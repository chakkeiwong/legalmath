"""Separate completion oracle for the two expressly unselected H43 readings."""
from copy import deepcopy
from itertools import product

INFO=('admitted_security_rights_change','nonshare_terms_change_affecting_rights','relevant_third_country_information')
QUALIFIED=('inlandsemittent_qualified',*INFO)
DUTIES=('statutory_reading_applies','implementing_rules_satisfied','simultaneous_bafin_notification','simultaneous_register_transmission')
ROUTE=('german_seat','bundesanzeiger_publication','section13_notice_satisfied','prompt_publication')
COMMON=('contract_reading_applies','suitable_public_announcement_at_issuer_expense','separate_website_duty_satisfied')
PREMISES=(*QUALIFIED,*DUTIES,*ROUTE,*COMMON)
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def decide(values,predicate):
    if 'conflict' in values.values():return 'CONFLICT'
    keys=list(values);outcomes=set()
    for row in product(*([False,True] if values[k] is None else [values[k]] for k in keys)):
        outcomes.add(bool(predicate(dict(zip(keys,row)))))
    return 'UNKNOWN' if len(outcomes)==2 else 'YES' if True in outcomes else 'NO'


def route(values):
    def broad(w):
        if not w['german_seat']:return True
        if not w['prompt_publication']:return False
        if w['statutory_conditions']:return True
        return w['bundesanzeiger_publication'] and w['section13_notice_satisfied']
    def retained(w):
        if not w['german_seat']:return True
        if not w['prompt_publication'] or not w['section13_notice_satisfied']:return False
        return w['bundesanzeiger_publication'] or w['statutory_conditions']
    return {'broad_replacement':decide(values,broad),'section13_retained':decide(values,retained)}


def expected(row):
    p=row['premises']
    trigger=decide({k:p[k] for k in QUALIFIED},lambda w:w['inlandsemittent_qualified'] and any(w[k] for k in INFO))
    duties=decide({'trigger':VALUE[trigger],**{k:p[k] for k in DUTIES}},lambda w:all(w.values()))
    r=route({k:p[k] for k in ROUTE}|{'statutory_conditions':VALUE[duties]})
    answers={k:decide({'route':VALUE[v],**{c:p[c] for c in COMMON}},lambda w:all(w.values())) for k,v in r.items()}
    return {'qualified_information':trigger,'statutory_conditions':duties,
            'german_seat_routes':r,'conditional_contract_readings':answers}


def scenarios(instrument):
    base={'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT',
        'identity':{'instrument_id':instrument,'issuer':'hypothetical-issuer',
                    'resolution_id':'hypothetical-resolution','security_kind':'NONSHARE_BOND'},
        'premises':dict.fromkeys(PREMISES)}
    rows=[deepcopy(base)]
    good=deepcopy(base);good['id']='complete-statutory-route'
    good['premises']={k:True for k in PREMISES}
    good['premises'].update(bundesanzeiger_publication=False,
        nonshare_terms_change_affecting_rights=False,relevant_third_country_information=False)
    rows.append(deepcopy(good))
    for field in PREMISES:
        for value in (False,None,'conflict'):
            row=deepcopy(good);row['id']=field+'-'+str(value);row['premises'][field]=value;rows.append(row)
    for field in INFO[1:]:
        row=deepcopy(good);row['id']='only-'+field
        row['premises'].update({k:False for k in INFO});row['premises'][field]=True;rows.append(row)
    for label,changes in (
        ('conventional-route-unknown-statute',{'bundesanzeiger_publication':True,'statutory_reading_applies':None}),
        ('interpretations-diverge',{'section13_notice_satisfied':False}),
        ('german-seat-is-not-inlandsemittent',{'inlandsemittent_qualified':None}),
        ('no-covered-information',{k:False for k in INFO}),
        ('website-still-open',{'separate_website_duty_satisfied':None})):
        row=deepcopy(good);row['id']=label;row['premises'].update(changes);rows.append(row)
    return rows
