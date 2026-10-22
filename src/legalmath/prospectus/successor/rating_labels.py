"""Exact printed rating boundaries, connected to conditional holder-option analysis."""
from copy import deepcopy
import json
from pathlib import Path
from .anchors import fields
from .contracts import digest
from .definition_applications import require
from .. import causal_rating

VERSION='basf-rating-labels.v1'
KEY='rating_label_review'
SPEC_SHA256 = '38969dd9fd95ab643ca5f39e779a4df7553aab30ae69582acd536e6a08b11090'
AGENCIES={
    'S&P':('S&P Global Ratings Europe Limited','BBB-','BB+'),
    'S&P Global Ratings Europe Limited':('S&P Global Ratings Europe Limited','BBB-','BB+'),
    "Moody's":("Moody's Deutschland GmbH",'Baa3','Ba1'),
    "Moody's Deutschland GmbH":("Moody's Deutschland GmbH",'Baa3','Ba1'),
    'Fitch':('Fitch Ratings Ireland Limited','BBB-','BB+'),
    'Fitch Ratings Ireland Limited':('Fitch Ratings Ireland Limited','BBB-','BB+')}
DERIVED={'agency_qualified','before_grade','after_grade','grade_classification_supported'}

def specification():
    value=json.loads(Path(__file__).with_name('rating_labels_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(value)==SPEC_SHA256,'Registered rating-label specification changed')
    return value

def classify(agency,before,after):
    for value in (agency,before,after):
        require(value is None or isinstance(value,str) and len(value)<=256,
            'Bounded literal rating observation or null required')
    recognized=AGENCIES.get(agency)
    def grade(value):
        category='UNKNOWN'
        if recognized is not None:
            if value==recognized[1]:category='INVESTMENT_GRADE'
            elif value==recognized[2]:category='NON_INVESTMENT_GRADE'
        return {'label':value,'category':category,'basis':'PRINTED_BOUNDARY' if category!='UNKNOWN'
            else 'OUTSIDE_PRINTED_BOUNDARY_DOMAIN'}
    return {'agency':{'label':agency,'source_name':recognized[0] if recognized else None,
        'qualified':True if recognized else None,'basis':'EXACT_SOURCE_NAME' if recognized else 'UNSUPPORTED_OR_MISSING'},
        'before':grade(before),'after':grade(after)}

def analyze(case,node,instrument):
    keys={'id','kind','agency_label','before_label','after_label','template','scenario'}
    fields(case,keys,keys)
    require(isinstance(case['id'],str) and case['id'] and case['kind']=='HYPOTHETICAL_DEVELOPMENT',
        'Explicit hypothetical raw-label case required')
    scenario=case['scenario']
    require(isinstance(scenario,dict) and scenario.get('id')==case['id'] and not DERIVED.intersection(scenario)
        and scenario.get('kind')=='HYPOTHETICAL_DEVELOPMENT','Derived rating category or agency cannot be supplied')
    classified=classify(case['agency_label'],case['before_label'],case['after_label'])
    before,after=classified['before']['category'],classified['after']['category']
    derived=deepcopy(scenario)
    derived.update(agency_qualified=classified['agency']['qualified'],before_grade=before,after_grade=after,
        grade_classification_supported=True if before!='UNKNOWN' and after!='UNKNOWN' else None)
    evaluated=causal_rating.analyze(derived,node,instrument)
    return {'input':deepcopy(case),'classification':classified,'rating_evaluation':evaluated}

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False,'Pinned rating-label source or prior answer differs')
    decisions=spec['decisions'];node=causal_rating.context(products)
    require(node==decisions['source_context']==ordinary['causal_rating_review']['context'],
        'Complete rating context differs')
    require(decisions['source_names']=={k:v[0] for k,v in AGENCIES.items()},'Source agency names differ')
    text=products['P2']['payload']['assembly']['continuous_text']
    for span in decisions['source_evidence']:
        require(type(span['start']) is int and type(span['end']) is int
            and 0<=span['start']<span['end']<=len(text) and text[span['start']:span['end']]==span['quote'],
            'Printed rating source span changed')
    cases=decisions['cases'];require(len({c['id'] for c in cases})==len(cases),'Duplicate raw-label case')
    content={'context':deepcopy(node),'source_thresholds':deepcopy(decisions['thresholds']),
        'scenarios':[analyze(case,node,ordinary['instrument_id']) for case in cases],
        'supported_domain':'EXACT_PRINTED_AGENCY_NAMES_AND_BOUNDARY_LABELS',
        'complete_rating_scale_supported':False,'successor_or_selected_agency_supported':False,
        'actual_event_established':False,'actual_agency_identity_established':False,
        'prior_answer_preserved':True,'whole_task_complete':False}
    require(digest(content)==spec['expected_content_sha256'],'Registered raw-label consequences differ')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),**content}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    expected={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    require(actual==expected,'Complete rating-label answer differs from reconstruction')
    return {'status':'PASS','whole_answer_equal':True,'legal_truth_established':False}
