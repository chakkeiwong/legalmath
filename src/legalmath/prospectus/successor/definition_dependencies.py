"""Apply finite reviewed definition evidence to current question uncertainty."""
from copy import deepcopy
import json
from pathlib import Path
from .anchors import fields
from .contracts import digest
from .definition_applications import require
from .definition_bindings import _checked_report

VERSION='definition-dependency-review.v1'
KEY='definition_dependency_review'
SPEC_SHA256 = 'accbf26c38b59d89a37ad276221c2cc26db4a9f879faeb95fb1ab9c1a55b0967'
DISCOVERY='definition-discovery:finite-dossier'
PATHS=(('Q1',),('Q2',),('Q2','subquestions','compulsory_common'),
       ('Q2','subquestions','possible_common'),('Q2','subquestions','common_only'))

def specification():
    value=json.loads(Path(__file__).with_name('definition_dependencies_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(value)==SPEC_SHA256,'Registered dependency specification changed')
    return value

def _record(record,review,source):
    original=next((r for r in source['records'] if r['id']==record['id']),None)
    require(original is not None and digest(original)==record['original_record_sha256'],
        'Source definition record changed')
    indices=record['use_indices'];uses=review['uses']
    require(isinstance(indices,list) and len(indices)==len(set(indices))
        and all(type(i) is int and 0<=i<len(uses) for i in indices)
        and indices==[i for i,u in enumerate(uses) if u['record']==record['id']],
        'Definition use index coverage changed')
    items=[uses[i] for i in indices]
    require(all(u['disposition']!='UNRECONCILED' and isinstance(u['remaining'],list)
        and all(isinstance(v,str) and v.strip() for v in u['remaining']) for u in items),
        'Unreviewed use or malformed remaining premise')
    ordinary=[u for u in items if u['origin']=='ORIGINAL']
    require(len(ordinary)==len(original['uses'])==record['original_uses'],
        'Original occurrence count changed')
    for current,expected in zip(ordinary,original['uses']):
        interval=source['intervals'][expected['interval']]
        require(current['interval']==expected['interval'] and all(current[k]==interval[k]
            for k in ('start','end','quote')),'Original occurrence identity changed')
    extra=[u for u in items if u['origin']=='SUPPLEMENTAL']
    require(len(items)==len(ordinary)+len(extra) and len(extra)==record['supplemental_uses'],
        'Supplemental occurrence count changed')
    for current in extra:
        expected=source['application_supplement']['source_supplement']['new_occurrence']
        require(current['interval'] is None and record['id'] in expected['candidate_record_associations']
            and all(current[k]==expected[k] for k in ('start','end','quote')),
            'Supplemental source occurrence changed')
    reasons=sorted({reason for u in items for reason in u['remaining']})
    issues=[{'id':'definition-premise:'+record['id']+':'+str(n),'reason':reason,
        'use_indices':[i for i in indices if reason in uses[i]['remaining']]} for n,reason in enumerate(reasons)]
    return {'record':record['id'],'original_dependency':'definition-source:'+record['id'],
        'source_record_sha256':record['original_record_sha256'],'use_indices':deepcopy(indices),
        'occurrences':[{'use_index':i,**{k:deepcopy(uses[i][k]) for k in
            ('origin','interval','start','end','quote','disposition','remaining')}} for i in indices],
        'remaining_premises':issues,'interpretation':'SUPPLIED_FINITE_SOURCE_REVIEW','legal_scope_resolved':False}

def _question_projection(questions,records):
    lookup={r['original_dependency']:r for r in records}
    require(len(lookup)==len(records),'Duplicate definition dependency')
    projected=deepcopy(questions);links=[]
    for path in PATHS:
        target=projected
        for key in path:target=target[key]
        unresolved=target['unresolved']
        require(isinstance(unresolved,list) and all(isinstance(s,str) for s in unresolved),
            'Explicit unresolved list required')
        prior=[s for s in unresolved if s.startswith('definition-source:')]
        require(len(prior)==len(lookup) and set(prior)==set(lookup)
            and not any(s.startswith(('definition-premise:','definition-discovery:')) for s in unresolved)
            and target['status'] in ('UNKNOWN','CONFLICT') and target['value'] is None,
            'Original question uncertainty changed')
        replacement=[issue['id'] for old in prior for issue in lookup[old]['remaining_premises']]
        require(len(replacement)==len(set(replacement)),'Duplicate remaining issue identifier')
        updated=[]
        for old in unresolved:
            if old in lookup:updated.extend(issue['id'] for issue in lookup[old]['remaining_premises'])
            else:updated.append(old)
        target['unresolved']=[*updated,DISCOVERY]
        links.append({'path':['questions',*path],'replaced':prior,'replacement_ids':replacement,
            'discovery_limit':DISCOVERY,'retained_status':target['status'],
            'retained_value':deepcopy(target['value'])})
    return projected,links

def project(ordinary,source):
    review=ordinary['definition_remainder_review']
    require(len(review['records'])==62 and len(review['uses'])==612
        and {r['id'] for r in review['records']}=={r['id'] for r in source['records']}
        and sum(u['origin']=='ORIGINAL' for u in review['uses'])==610,
        'Complete definition denominator changed')
    records=[_record(r,review,source) for r in review['records']]
    require(sorted(i for r in records for i in r['use_indices'])==list(range(612)),
        'Definition associations missing or duplicated')
    questions,links=_question_projection(ordinary['questions'],records)
    content={'records':records,'question_links':links,'source_review_sha256':digest(review),
        'discovery_limit':{'id':DISCOVERY,'reason':'Finite source dossier; general naming, use and governing-relation discovery is not established',
            'known_misses':deepcopy(source['known_misses'])},
        'original_associations':610,'supplemental_associations':2,'reviewed_records':62,
        'assistance':'SUPPLIED_SOURCE_REVIEW_APPLIED_TO_CURRENT_QUESTION_DEPENDENCIES',
        'historical_answer_preserved_in_source_reports':True,'nondefinition_dependencies_preserved':True,
        'question_statuses_preserved':True,'actual_facts_established':False,
        'historical_law_established':False,'general_recall_established':False,'whole_task_complete':False}
    return questions,content

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False,'Pinned definition dependency source or prior answer differs')
    source,_=_checked_report(products,ordinary)
    questions,content=project(ordinary,source)
    require(digest(content)==spec['expected_content_sha256'],'Registered dependency content differs')
    require(content['records']==spec['decisions'],'Registered occurrence and issue mapping differs')
    return {'questions':questions,KEY:{'version':VERSION,'profile_sha256':digest(profile),
        'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),**content}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    expected={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    require(actual==expected,'Complete current-question answer differs from dependency reconstruction')
    return {'status':'PASS','whole_answer_equal':True,'legal_truth_established':False}
