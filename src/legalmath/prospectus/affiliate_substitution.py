"""Finite qualified affiliation and substitution conditions, not actual events."""
from copy import deepcopy
from .causal_rating import boolean
from .successor.anchors import bind,fields
from .successor.contracts import bound_path,digest
from .successor.predicates import dispatch
from .successor.basf_agents import source_pieces
from .successor.basf_governance_terms import validate

VERSION='basf-affiliate-substitution.v1'
KEY='affiliate_substitution_review'
CATEGORIES=('majority_relation_section16','dependency_relation_section17',
    'group_relation_section18','reciprocal_relation_section19','enterprise_agreement_sections291_292')
AFFILIATE=('legally_independent',*CATEGORIES)
PREREQUISITES=('no_principal_or_interest_default','all_note_obligations_assumed',
    'required_permissions_obtained','specified_currency_payment_permitted',
    'payment_without_required_tax_withholding','holder_tax_indemnity_undertaken',
    'programme_guarantee_extended','negative_pledge_extended',
    'required_lawyer_confirmations_received_by_fiscal_agent')
VALUE={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}
NODES=('basf-governance:substitution','basf-governance:affiliate',
       'basf-governance:substitution_notice','basf-governance:substitution_changes','basf-governance:substitution_deposit')


def context(products,ordinary):
    report=products['P3']['payload'].get('statutory_references')
    if not report or ordinary.get('statutory_references')!=report:
        raise ValueError('Complete current statutory reading required')
    records=[r for r in report['records'] if r['id']=='H35']
    if len(records)!=1 or records[0]['availability']!='RETAINED_PRIMARY_READING':
        raise ValueError('Exact retained H35 reading required')
    from .successor.statutory_references import specification
    registered=next(r for r in specification()['records'] if r['id']=='H35')
    if any(records[0].get(k)!=v for k,v in registered.items()):
        raise ValueError('H35 differs from registered complete source record')
    clauses=products['P3']['payload']['clauses']['nodes'];nodes=[]
    graph=products['P1']['payload']['graph']
    units={u['unit']:u for u in products['P2']['payload']['assembly']['units']}
    for identity in NODES:
        selected=[n for n in clauses if n['id']==identity]
        if len(selected)!=1:raise ValueError('Complete substitution and onward clauses required')
        node=selected[0]
        quote=' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in node['spans'])
        if node['quote']!=quote or node['role']!='OPERATIVE':raise ValueError('Substitution source extent changed')
        validate(node)
        for r in source_pieces(graph,units,node['spans']):bind(graph,r['source'])
        nodes.append(deepcopy(node))
    text=nodes[0]['quote']
    if not all(s in text for s in ('nicht mit einer Zahlung von Kapital oder Zinsen',
        '(a)','(b)','(c)','(d)','(e)','Steuern','Garantie','Negativverpflichtung','anerkannten Rechtsanwälten')):
        raise ValueError('Compound substitution prerequisites missing')
    if '§ 15 Aktiengesetz' not in nodes[1]['quote']:raise ValueError('Affiliate statutory cross-reference missing')
    return {'H35':deepcopy(records[0]),'statutory_profile_sha256':report['profile_sha256'],
        'contract_clauses':nodes,'categories_mean_full_qualified_relations':True,
        'onward_qualifications':'Sections16-19 and291/292 retain attribution,denominators,presumptions and exclusions; category facts are supplied,not inferred',
        'contractual_confirmation':'Receipt of the specified lawyers confirmations is an express contractual premise,not external approval of this program',
        'historical_application':'NOT_ESTABLISHED'}


def affiliation(premises):
    fields(premises,AFFILIATE,AFFILIATE)
    for value in premises.values():boolean(value)
    return dispatch({'all':['legally_independent',{'any':list(CATEGORIES)}]},premises)


def analyze(row,instrument):
    keys={'id','kind','identity','affiliate_categories','prerequisites','issuer_elected',
          'statutory_reading_applies','contract_reading_applies'}
    fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical substitution scenario required')
    identity=row['identity'];keys={'instrument_id','issuer','successor','substitution_event_id'};fields(identity,keys,keys)
    if identity['instrument_id']!=instrument or any(not isinstance(identity[k],str) or not identity[k].strip() for k in keys):
        raise ValueError('Identified instrument,issuer,successor and substitution event required')
    if identity['issuer']==identity['successor']:raise ValueError('Substitution requires distinct issuer and successor')
    for k in ('issuer_elected','statutory_reading_applies','contract_reading_applies'):boolean(row[k])
    affiliate=affiliation(row['affiliate_categories'])
    eligible=dispatch({'all':['affiliate','statutory_reading_applies']},
        {'affiliate':VALUE[affiliate['status']],'statutory_reading_applies':row['statutory_reading_applies']})
    premises=row['prerequisites'];fields(premises,PREREQUISITES,PREREQUISITES)
    for value in premises.values():boolean(value)
    conditions={**premises,'qualified_affiliate':VALUE[eligible['status']]}
    condition=dispatch({'all':list(conditions)},conditions)
    applied=dispatch({'all':['conditions','contract_reading_applies']},
        {'conditions':VALUE[condition['status']],'contract_reading_applies':row['contract_reading_applies']})
    elected=dispatch({'all':['conditions','issuer_elected']},
        {'conditions':VALUE[applied['status']],'issuer_elected':row['issuer_elected']})
    return {'scenario':deepcopy(row),'affiliate_category_result':affiliate,'conditional_affiliate':eligible,
        'listed_prerequisites':condition,'conditional_listed_prerequisites':applied,'conditional_election_and_prerequisites':elected,
        'actual_affiliation':'NOT_ESTABLISHED','actual_substitution':'NOT_ESTABLISHED',
        'onward_notice_and_document_duties':'SEPARATE_REQUIREMENTS_NOT_DISCHARGED',
        'actual_lawyer_confirmation':'NOT_ESTABLISHED','complete_legal_test':False,
        'meaning':'Finite qualified category and contractual prerequisite computation; neither categories nor conditions prove actual valid substitution'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established','historical_application_proved','complete_legal_test'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
            or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned affiliate profile or complete prior answer changed')
    if any(profile[k] is not False for k in ('actual_event_established','historical_application_proved','complete_legal_test')):
        raise ValueError('Conditional categories cannot establish actual or complete legal status')
    source=context(products,ordinary)
    if profile['context']!=source:raise ValueError('Complete H35 and substitution source context changed')
    for s in source['H35']['legal_sources']:
        raw=bound_path(root,s['text_path']).read_bytes()
        if digest(raw)!=s['text_sha256']:raise ValueError('Retained statutory source changed')
        text=raw.decode('utf-8')
        for e in s['excerpts']:
            if text[e['start']:e['end']]!=e['quote']:raise ValueError('Retained statutory excerpt changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not 1<=len(rows)<=128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded nonempty substitution scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Distinct substitution scenario identities required')
    first=rows[0]
    if (first['id']!='all-open' or any(first[k] is not None for k in ('issuer_elected','statutory_reading_applies','contract_reading_applies'))
            or any(v is not None for v in first['affiliate_categories'].values())
            or any(v is not None for v in first['prerequisites'].values())):
        raise ValueError('All-open substitution baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':source,'scenarios':[analyze(r,instrument) for r in rows],
        'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}!={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Affiliate composition changed complete prior answer')
    if answer.get(KEY)!=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256):
        raise ValueError('Affiliate answer differs from source reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(profile['scenarios'])}
