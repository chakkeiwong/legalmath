"""Independent truth enumeration for retained section15 and substitution terms."""
from copy import deepcopy
from itertools import product
CATEGORIES=('majority_relation_section16','dependency_relation_section17','group_relation_section18',
            'reciprocal_relation_section19','enterprise_agreement_sections291_292')
AFFILIATE=('legally_independent',*CATEGORIES)
PREREQUISITES=('no_principal_or_interest_default','all_note_obligations_assumed','required_permissions_obtained',
    'specified_currency_payment_permitted','payment_without_required_tax_withholding','holder_tax_indemnity_undertaken',
    'programme_guarantee_extended','negative_pledge_extended','required_lawyer_confirmations_received_by_fiscal_agent')
VALUES={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def decide(values,predicate):
    if any(v=='conflict' for v in values.values()):return 'CONFLICT'
    keys=list(values);outcomes=set()
    for row in product(*([False,True] if values[k] is None else [values[k]] for k in keys)):
        outcomes.add(predicate(dict(zip(keys,row))))
    return 'UNKNOWN' if len(outcomes)==2 else 'YES' if True in outcomes else 'NO'


def affiliation(values):return decide(values,lambda w:w['legally_independent'] and any(w[k] for k in CATEGORIES))
def both(values):return decide(values,lambda w:all(w.values()))


def expected(row):
    a=affiliation(row['affiliate_categories'])
    eligible=both({'affiliate':VALUES[a],'applies':row['statutory_reading_applies']})
    condition=both({**row['prerequisites'],'affiliate':VALUES[eligible]})
    applied=both({'conditions':VALUES[condition],'applies':row['contract_reading_applies']})
    elected=both({'conditions':VALUES[applied],'elected':row['issuer_elected']})
    return dict(zip(('affiliate_category_result','conditional_affiliate','listed_prerequisites',
        'conditional_listed_prerequisites','conditional_election_and_prerequisites'),(a,eligible,condition,applied,elected)))


def scenarios(instrument):
    base={'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT',
        'identity':{'instrument_id':instrument,'issuer':'hypothetical-issuer','successor':'hypothetical-successor','substitution_event_id':'hypothetical-substitution'},
        'affiliate_categories':dict.fromkeys(AFFILIATE),'prerequisites':dict.fromkeys(PREREQUISITES),
        'issuer_elected':None,'statutory_reading_applies':None,'contract_reading_applies':None}
    rows=[deepcopy(base)]
    good=deepcopy(base);good.update(id='qualified-majority-category',issuer_elected=True,statutory_reading_applies=True,contract_reading_applies=True)
    good['affiliate_categories']={k:False for k in AFFILIATE};good['affiliate_categories'].update(legally_independent=True,majority_relation_section16=True)
    good['prerequisites']={k:True for k in PREREQUISITES};rows.append(deepcopy(good))
    for category in CATEGORIES[1:]:
        row=deepcopy(good);row['id']='only-'+category;row['affiliate_categories']['majority_relation_section16']=False;row['affiliate_categories'][category]=True;rows.append(row)
    for label,changes in (('no-category',{k:False for k in CATEGORIES}),('not-independent',{'legally_independent':False}),
            ('unknown-independence',{'legally_independent':None}),('conflicting-category',{'group_relation_section18':'conflict'})):
        row=deepcopy(good);row['id']=label;row['affiliate_categories'].update(changes);rows.append(row)
    for key in PREREQUISITES:
        for value in (False,None,'conflict'):
            row=deepcopy(good);row['id']=key+'-'+str(value);row['prerequisites'][key]=value;rows.append(row)
    for key in ('issuer_elected','statutory_reading_applies','contract_reading_applies'):
        for value in (False,None,'conflict'):
            row=deepcopy(good);row['id']=key+'-'+str(value);row[key]=value;rows.append(row)
    return rows
