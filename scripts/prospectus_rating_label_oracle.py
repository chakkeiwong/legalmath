"""Source-enumerated raw labels and independent Boolean consequences."""
from copy import deepcopy
from itertools import product
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus import causal_rating

KEY='rating_label_review'
VERSION='basf-rating-labels.v1'
NAMES={'S&P':'S&P Global Ratings Europe Limited','S&P Global Ratings Europe Limited':'S&P Global Ratings Europe Limited',
       "Moody's":"Moody's Deutschland GmbH","Moody's Deutschland GmbH":"Moody's Deutschland GmbH",
       'Fitch':'Fitch Ratings Ireland Limited','Fitch Ratings Ireland Limited':'Fitch Ratings Ireland Limited'}
TABLE=[('S&P Global Ratings Europe Limited','BBB-','INVESTMENT_GRADE'),
       ('S&P Global Ratings Europe Limited','BB+','NON_INVESTMENT_GRADE'),
       ("Moody's Deutschland GmbH",'Baa3','INVESTMENT_GRADE'),
       ("Moody's Deutschland GmbH",'Ba1','NON_INVESTMENT_GRADE'),
       ('Fitch Ratings Ireland Limited','BBB-','INVESTMENT_GRADE'),
       ('Fitch Ratings Ireland Limited','BB+','NON_INVESTMENT_GRADE')]

def grade(name,label):
    found=[category for agency,value,category in TABLE if agency==name and value==label]
    return {'label':label,'category':found[0] if found else 'UNKNOWN',
        'basis':'PRINTED_BOUNDARY' if found else 'OUTSIDE_PRINTED_BOUNDARY_DOMAIN'}

def labels(agency,before,after):
    name=NAMES.get(agency)
    return {'agency':{'label':agency,'source_name':name,'qualified':True if name else None,
        'basis':'EXACT_SOURCE_NAME' if name else 'UNSUPPORTED_OR_MISSING'},
        'before':grade(name,before),'after':grade(name,after)}

def boolean_status(values):
    """Independent explicit worlds for a conjunction, including contradictions."""
    if any(v is False for v in values):return 'NO'
    if 'conflict' in values:return 'CONFLICT'
    worlds=list(product(*[(False,True) if v is None else (v,) for v in values]))
    outcomes={all(w) for w in worlds}
    return 'YES' if outcomes=={True} else 'NO' if outcomes=={False} else 'UNKNOWN'

def expectations(case,classified):
    scenario=case['scenario'];before=classified['before']['category'];after=classified['after']['category']
    # These frozen templates have independent known chronological cases.
    within=False if case['template']=='day121' else True
    if scenario['rating_action']=='WITHDRAWAL':event=scenario['previously_assigned']
    else:
        parts=[scenario['previously_assigned'],None if before=='UNKNOWN' else before=='INVESTMENT_GRADE',
            None if after=='UNKNOWN' else after=='NON_INVESTMENT_GRADE',
            True if before!='UNKNOWN' and after!='UNKNOWN' else None]
        event={'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[boolean_status(parts)]
    cause=scenario['causal_link']['value'] if scenario['causal_link'] else None
    rating=boolean_status([event,within,classified['agency']['qualified'],
        scenario['rating_subject_qualified'],scenario['counting_convention_supported'],cause])
    facts=scenario['other_facts']
    total=boolean_status([{'YES':True,'NO':False,'UNKNOWN':None,'CONFLICT':'conflict'}[rating],
        *[facts[k] for k in ('control_put.control','control_put.event_notice','control_put.timely_exercise',
                            'control_put.valid_declaration','control_put.delivery','control_put.payment_day')],
        not facts['control_put.earlier_tax_notice'],
        not facts['representative.put.entrusted'] or facts['representative.put.express_permission']])
    return {'rating':rating,'complete_control_put':total}

def input_cases(ordinary):
    prior={r['scenario']['id']:r['scenario'] for r in ordinary['causal_rating_review']['scenarios']}
    rows=[]
    def add(identity,agency,before,after,template='day120'):
        scenario=deepcopy(prior[template]);scenario['id']=identity
        for k in ('agency_qualified','before_grade','after_grade','grade_classification_supported'):scenario.pop(k)
        for label in ('control','rating'):
            event_id=identity+':'+label;scenario['events'][label+'_event_id']=event_id
            if scenario['events'][label] is not None:scenario['events'][label]['event_id']=event_id
            if scenario['causal_link'] is not None:scenario['causal_link'][label+'_event_id']=event_id
        rows.append({'id':identity,'kind':'HYPOTHETICAL_DEVELOPMENT','agency_label':agency,
            'before_label':before,'after_label':after,'template':template,'scenario':scenario})
    for index,name in enumerate(NAMES):
        add('named-'+str(index),name,'Baa3' if 'Moody' in name else 'BBB-','Ba1' if 'Moody' in name else 'BB+')
    for identity,name,before,after in [
        ('wrong-sp-scale','S&P','Baa3','Ba1'),('wrong-moody-scale',"Moody's",'BBB-','BB+'),
        ('wrong-fitch-scale','Fitch','Baa3','Ba1'),('unknown-agency','Other','BBB-','BB+'),
        ('missing-agency',None,'BBB-','BB+'),('empty-agency','','BBB-','BB+'),
        ('case-agency','s&p','BBB-','BB+'),('space-agency','S&P ','BBB-','BB+'),
        ('successor-label','S&P successor','BBB-','BB+'),('higher-unlisted','S&P','AAA','BB+'),
        ('lower-unlisted','S&P','BBB-','B'),('grade-case','S&P','bbb-','bb+'),
        ('grade-space','S&P','BBB- ','BB+'),('grade-outlook','S&P','BBB- (negative)','BB+'),
        ('grade-suffix','Fitch','BBB-(sf)','BB+'),('missing-before','S&P',None,'BB+'),
        ('missing-after','S&P','BBB-',None),('empty-grade','S&P','',''),
        ('unchanged-investment','S&P','BBB-','BBB-'),('already-noninvestment','Fitch','BB+','BB+'),
        ('reversed-grade',"Moody's",'Ba1','Baa3')]:add(identity,name,before,after)
    for template in ('day121','causal-denied','causal-unknown','causal-conflict','tax-exception'):
        add('boundary-'+template,'S&P','BBB-','BB+',template)
    add('withdrawal-unlisted','Fitch','CCC',None,'withdrawal-grade-unknown')
    add('withdrawal-unknown-agency','Other',None,None,'withdrawal-grade-unknown')
    return rows

def derive_scenario(case,classified):
    scenario=deepcopy(case['scenario']);before=classified['before']['category'];after=classified['after']['category']
    scenario.update(agency_qualified=classified['agency']['qualified'],before_grade=before,after_grade=after,
        grade_classification_supported=True if before!='UNKNOWN' and after!='UNKNOWN' else None)
    return scenario

def frozen_content(ordinary,products,cases):
    node=ordinary['causal_rating_review']['context'];instrument=ordinary['instrument_id'];rows=[]
    for case in cases:
        classified=labels(case['agency_label'],case['before_label'],case['after_label'])
        expected=expectations(case,classified)
        evaluated=causal_rating.analyze(derive_scenario(case,classified),node,instrument)
        assert (evaluated['derived_rating']['status'],evaluated['complete_control_put']['status'])==(expected['rating'],expected['complete_control_put'])
        rows.append({'input':deepcopy(case),'classification':classified,'rating_evaluation':evaluated})
    return {'context':deepcopy(node),'source_thresholds':[{'agency':a,'label':l,'category':c} for a,l,c in TABLE],
        'scenarios':rows,'supported_domain':'EXACT_PRINTED_AGENCY_NAMES_AND_BOUNDARY_LABELS',
        'complete_rating_scale_supported':False,'successor_or_selected_agency_supported':False,
        'actual_event_established':False,'actual_agency_identity_established':False,
        'prior_answer_preserved':True,'whole_task_complete':False}

def verify(actual,ordinary,products,profile,content):
    expected={**ordinary,KEY:{'version':VERSION,'profile_sha256':digest(profile),
        'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),**deepcopy(content)}}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    assert actual==expected,'Complete rating-label answer differs from independent source expectation'
    return {'status':'PASS','whole_answer_equal_to_independent_expectation':True,'scenarios':len(content['scenarios'])}
