"""Necessary conditions from retained WpUG30(2); no actual concert finding."""
from copy import deepcopy
from .causal_rating import boolean
from .successor.anchors import fields
from .successor.contracts import bound_path,digest
from .successor.predicates import dispatch

VERSION='basf-concert-necessary.v1'
KEY='concert_necessary_review'
PREMISES=('coordination_by_agreement_or_other_means','understanding_about_voting',
          'other_cooperation','lasting_change_aim','substantial_direction_change_aim',
          'individual_case_agreement_exception')
EXPRESSION={'all':['coordination_by_agreement_or_other_means',
    {'any':['understanding_about_voting',{'all':['other_cooperation','lasting_change_aim','substantial_direction_change_aim']}]},
    {'not':'individual_case_agreement_exception'}]}


def context(products,ordinary):
    report=products['P3']['payload'].get('statutory_references')
    if report is None or ordinary.get('statutory_references')!=report:
        raise ValueError('Complete current statutory reading required')
    rows=[r for r in report['records'] if r['id']=='H16']
    if len(rows)!=1 or rows[0]['availability']!='RETAINED_PRIMARY_READING':
        raise ValueError('Retained H16 original reading required')
    from .successor.statutory_references import specification
    registered=next(r for r in specification()['records'] if r['id']=='H16')
    if any(rows[0].get(k)!=v for k,v in registered.items()):
        raise ValueError('H16 source differs from registered reading')
    source=rows[0]['legal_sources'][0]
    matches=[e for e in source['excerpts'] if '(2) Dem Bieter werden auch Stimmrechte' in e['quote']]
    if len(matches)!=1:raise ValueError('Exact retained coordinated-action source required')
    excerpt=matches[0];a=excerpt['quote'].index('(2) Dem Bieter');b=excerpt['quote'].index('(3)',a)
    quote=excerpt['quote'][a:b]
    if not all(s in quote for s in ('ausgenommen sind Vereinbarungen in Einzelfällen',
        'setzt voraus','über die Ausübung von Stimmrechten verständigen oder',
        'dauerhaften und erheblichen Änderung','gilt Absatz 1 entsprechend')):
        raise ValueError('Coordination alternatives,exception or onward rule changed')
    return {'statutory_profile_sha256':report['profile_sha256'],'H16':deepcopy(rows[0]),
        'necessary_source':{'path':source['text_path'],'sha256':source['text_sha256'],
            'start':excerpt['start']+a,'end':excerpt['start']+b,'quote':quote},
        'meaning':'Explicitly modeled necessary conditions only;legal sufficiency and group attribution not established'}


def analyze(row,instrument):
    keys={'id','kind','pair','premises','reading_applies'};fields(row,keys,keys)
    if not isinstance(row['id'],str) or not row['id'] or row['kind']!='HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical coordinated-action scenario required')
    pair=row['pair'];keys={'instrument_id','control_event_id','pair_id','left_person','right_person','target'}
    fields(pair,keys,keys)
    if pair['instrument_id']!=instrument or pair['target']!='BASF_SE':
        raise ValueError('Coordination instrument or target mismatch')
    if any(not isinstance(pair[k],str) or not pair[k] for k in ('control_event_id','pair_id','left_person','right_person')):
        raise ValueError('Distinct identified persons,pair and control event required')
    if pair['left_person']==pair['right_person']:raise ValueError('Pair requires two different persons')
    premises=row['premises'];fields(premises,PREMISES,PREMISES)
    for value in premises.values():boolean(value)
    boolean(row['reading_applies'])
    necessary=dispatch(EXPRESSION,premises)
    value={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[necessary['status']]
    applied=dispatch({'all':['necessary','reading_applies']},{'necessary':value,'reading_applies':row['reading_applies']})
    return {'scenario':deepcopy(row),'necessary_conditions':necessary,'conditional_necessary_conditions':applied,
        'sufficient_legal_test':False,'actual_concert':'NOT_ESTABLISHED','group_wide_concert':'NOT_ESTABLISHED',
        'eligible_ownership_or_attribution':'NOT_DERIVED','historical_application':'NOT_ESTABLISHED',
        'control_premise_supplied':False,'onward_section_30_1':'OPEN',
        'meaning':'Necessary conditions for one supplied pair;YES does not establish actual legal concert or eligible voting totals'}


def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','context','scenarios','actual_event_established','historical_application_proved','complete_legal_test'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
        or profile['products_sha256']!=digest(products) or profile['ordinary_answer_sha256']!=digest(ordinary)
        or ordinary.get('report_sha256')!=digest({k:v for k,v in ordinary.items() if k!='report_sha256'}) or KEY in ordinary):
        raise ValueError('Pinned coordination profile or complete baseline changed')
    if any(profile[k] is not False for k in ('actual_event_established','historical_application_proved','complete_legal_test')):
        raise ValueError('Necessary conditions cannot establish actual,historical or complete legal status')
    actual=context(products,ordinary)
    if profile['context']!=actual:raise ValueError('Complete H16 source context changed')
    for source in actual['H16']['legal_sources']:
        raw=bound_path(root,source['text_path']).read_bytes()
        if digest(raw)!=source['text_sha256']:raise ValueError('Retained H16 source bytes changed')
        text=raw.decode('utf-8')
        for e in source['excerpts']:
            if text[e['start']:e['end']]!=e['quote']:raise ValueError('Retained H16 excerpt changed')
    rows=profile['scenarios']
    if not isinstance(rows,list) or not rows or len(rows)>128 or any(not isinstance(r,dict) for r in rows):
        raise ValueError('Bounded coordinated-action scenarios required')
    ids=[r.get('id') for r in rows]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Distinct scenario identities required')
    first=rows[0]
    if first['id']!='all-open' or first['reading_applies'] is not None or any(v is not None for v in first['premises'].values()):
        raise ValueError('All-open coordinated-action baseline required')
    instrument=products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'context':actual,'scenarios':[analyze(r,instrument) for r in rows],
        'actual_event_established':False,'historical_application_proved':False,'complete_legal_test':False,
        'classification':'SUPPLIED_SOURCE_BOUND_NECESSARY_CONDITIONS'}


def verify_answer(answer,ordinary,profile,products,root,*,expected_profile_sha256):
    if (answer.get('report_sha256')!=digest({k:v for k,v in answer.items() if k!='report_sha256'})
        or {k:v for k,v in answer.items() if k not in (KEY,'report_sha256')}!={k:v for k,v in ordinary.items() if k!='report_sha256'}):
        raise ValueError('Coordination answer changed complete baseline or digest')
    expected=evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY)!=expected:raise ValueError('Coordination answer differs from source reconstruction')
    return {'status':'PASS','baseline_unchanged':True,'scenarios':len(expected['scenarios'])}
