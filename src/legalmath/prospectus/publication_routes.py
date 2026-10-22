"""Conditional non-share publication routes with unresolved source application."""
from copy import deepcopy
import json
from .causal_rating import boolean
from .successor.anchors import fields
from .successor.contracts import bound_path, digest
from .successor.predicates import dispatch

VERSION='basf-publication-routes.v1'
KEY='publication_routes_review'
SOURCE='docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-059/requests/section/'
SOURCE_HASHES={'trusted-body':'6cebf04da8b414f608fd4d100c7403462be017ddaa3160c5a3d8d25898714765',
    'trusted-text.txt':'c204aba0a6885b17f3328d1065fdc76c519cd6b366146efde7b72f4a7afbd01e',
    'trusted-receipt.json':'c7ce84f07c39dde0921ef094dd9b12d5c6c533833806cce1967bc6c8056af331'}
INFORMATION=('admitted_security_rights_change','nonshare_terms_change_affecting_rights','relevant_third_country_information')
QUALIFIED=('inlandsemittent_qualified',*INFORMATION)
DUTIES=('statutory_reading_applies','implementing_rules_satisfied',
        'simultaneous_bafin_notification','simultaneous_register_transmission')
ROUTE=('german_seat','bundesanzeiger_publication','section13_notice_satisfied','prompt_publication')
COMMON=('contract_reading_applies','suitable_public_announcement_at_issuer_expense','separate_website_duty_satisfied')
PREMISES=(*QUALIFIED,*DUTIES,*ROUTE,*COMMON)
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}


def context(products,ordinary,root):
    from .successor.basf_meeting_procedure import explain
    full=explain(products['P3']['payload']['clauses'],products['P1']['payload']['graph'],
                 products['P2']['payload']['assembly'])
    kinds={'resolution_publication','german_seat_publication','resolution_website'}
    selected=[r for r in full if r['kind'] in kinds]
    if {r['kind'] for r in selected}!=kinds or len(selected)!=3:
        raise ValueError('Complete publication paragraph and separate website duty required')
    for row in selected:
        if row['kind']=='german_seat_publication' and 'historical-WpHG-50-1-publication' not in str(row['references']):
            raise ValueError('Original unresolved H43 dependency missing')
    h43=ordinary.get('residual_coverage_review',{}).get('H43')
    if not h43 or h43.get('status')!='SOURCE_EDITION_AND_APPLICATION_OPEN':
        raise ValueError('Original H43 uncertainty must remain')
    sources={}
    for name,checksum in SOURCE_HASHES.items():
        raw=bound_path(root,SOURCE+name).read_bytes()
        if digest(raw)!=checksum:raise ValueError('Retained current WpHG source or receipt changed')
        sources[name]={'path':SOURCE+name,'sha256':checksum}
    text=bound_path(root,SOURCE+'trusted-text.txt').read_text()
    receipt=json.loads(bound_path(root,SOURCE+'trusted-receipt.json').read_text())
    return {'original_H43':deepcopy(h43),'contract_clauses':selected,'source_files':sources,
        'complete_current_section50':text,'retrieval':receipt,'current_source_available':True,
        'historical_application':'NOT_ESTABLISHED','implementing_rules':'NOT_RETRIEVED',
        'issuer_definition':'NOT_RETRIEVED;full qualification supplied hypothetically',
        'share_derivative_branch':'RETAINED_IN_SOURCE;outside nonshare scenario domain',
        'section13_alternative_scope':'TWO_CONDITIONAL_READINGS;neither selected',
        'onward_register_delivery':'Issuer transmits to register operator; operator onward delivery is not inferred as issuer act'}


def routes(values):
    keys=(*ROUTE,'statutory_conditions')
    fields(values,keys,keys)
    for value in values.values():boolean(value)
    not_german={'not':'german_seat'}
    broad={'any':[not_german,{'all':['prompt_publication',{'any':[
        {'all':['bundesanzeiger_publication','section13_notice_satisfied']},'statutory_conditions']}]}]}
    retained={'any':[not_german,{'all':['prompt_publication','section13_notice_satisfied',
        {'any':['bundesanzeiger_publication','statutory_conditions']}]}]}
    return {'broad_replacement':dispatch(broad,values),'section13_retained':dispatch(retained,values)}


def analyze(row,instrument):
    fields(row,{'id','kind','identity','premises'},{'id','kind','identity','premises'})
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical publication case required')
    identity=row['identity'];keys={'instrument_id','issuer','resolution_id','security_kind'}
    fields(identity,keys,keys)
    if (identity['instrument_id']!=instrument or identity['security_kind']!='NONSHARE_BOND'
            or any(not isinstance(identity[k],str) or not identity[k].strip() for k in keys)):
        raise ValueError('Identified nonshare bond,issuer and resolution required')
    p=row['premises'];fields(p,PREMISES,PREMISES)
    for value in p.values():boolean(value)
    trigger=dispatch({'all':['inlandsemittent_qualified',{'any':list(INFORMATION)}]},p)
    duties=dispatch({'all':['trigger',*DUTIES]},{**p,'trigger':VALUE[trigger['status']]})
    route=routes({**{k:p[k] for k in ROUTE},'statutory_conditions':VALUE[duties['status']]})
    answers={}
    for key,result in route.items():
        answers[key]=dispatch({'all':['route',*COMMON]},{**p,'route':VALUE[result['status']]})
    return {'scenario':deepcopy(row),'qualified_information':trigger,'statutory_conditions':duties,
        'german_seat_routes':route,'conditional_contract_readings':answers,
        'readings_agree_for_these_inputs':len({a['status'] for a in answers.values()})==1,
        'selected_interpretation':None,'actual_publication':'NOT_ESTABLISHED',
        'actual_resolution_validity':'NOT_ESTABLISHED','complete_legal_test':False}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios',
          'actual_event_established','historical_application_proved','complete_legal_test'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
            or KEY in ordinary):raise ValueError('Pinned publication profile or prior answer changed')
    if any(profile[k] is not False for k in ('actual_event_established','historical_application_proved','complete_legal_test')):
        raise ValueError('Conditional publication cannot establish actual or complete legal status')
    source=context(products,ordinary,root)
    if profile['context']!=source:raise ValueError('Complete H43 source or remaining uncertainty changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not 1<=len(rows)<=128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded nonempty publication scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Distinct publication case identities required')
    if rows[0]['id']!='all-open' or any(v is not None for v in rows[0]['premises'].values()):
        raise ValueError('All-open publication baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':source,
        'scenarios':[analyze(row,instrument) for row in rows],
        'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}
            !={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Publication analysis changed complete prior answer')
    if answer.get(KEY)!=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256):
        raise ValueError('Publication answer differs from source reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(profile['scenarios'])}
