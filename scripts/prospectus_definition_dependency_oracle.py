"""Independent full-question expectation frozen before the candidate exists."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest

KEY='definition_dependency_review'
VERSION='definition-dependency-review.v1'
DISCOVERY='definition-discovery:finite-dossier'
PATHS=[['Q1'],['Q2'],['Q2','subquestions','compulsory_common'],
       ['Q2','subquestions','possible_common'],['Q2','subquestions','common_only']]

def at(questions,path):
    value=questions
    for key in path:value=value[key]
    return value

def freeze_content(ordinary):
    review=ordinary['definition_remainder_review'];records=[]
    for record in review['records']:
        indices=record['use_indices'];items=[review['uses'][i] for i in indices]
        assert all(u['record']==record['id'] for u in items)
        reasons=sorted({s for u in items for s in u['remaining']})
        issues=[{'id':'definition-premise:'+record['id']+':'+str(n),
            'reason':reason,'use_indices':[i for i in indices if reason in review['uses'][i]['remaining']]}
            for n,reason in enumerate(reasons)]
        records.append({'record':record['id'],'original_dependency':'definition-source:'+record['id'],
            'source_record_sha256':record['original_record_sha256'],'use_indices':deepcopy(indices),
            'occurrences':[{'use_index':i,**{k:deepcopy(review['uses'][i][k]) for k in
                ('origin','interval','start','end','quote','disposition','remaining')}} for i in indices],
            'remaining_premises':issues,'interpretation':'SUPPLIED_FINITE_SOURCE_REVIEW',
            'legal_scope_resolved':False})
    lookup={r['original_dependency']:r for r in records};links=[]
    for path in PATHS:
        question=at(ordinary['questions'],path)
        prior=[x for x in question['unresolved'] if x.startswith('definition-source:')]
        assert len(prior)==len(lookup) and set(prior)==set(lookup)
        links.append({'path':['questions',*path],'replaced':prior,
            'replacement_ids':[issue['id'] for old in prior for issue in lookup[old]['remaining_premises']],
            'discovery_limit':DISCOVERY,'retained_status':question['status'],
            'retained_value':deepcopy(question['value'])})
    return {'records':records,'question_links':links,'source_review_sha256':digest(review),
        'discovery_limit':{'id':DISCOVERY,'reason':'Finite source dossier; general naming, use and governing-relation discovery is not established',
            'known_misses':deepcopy(ordinary['definition_sources']['known_misses'])},
        'original_associations':610,'supplemental_associations':2,'reviewed_records':62,
        'assistance':'SUPPLIED_SOURCE_REVIEW_APPLIED_TO_CURRENT_QUESTION_DEPENDENCIES',
        'historical_answer_preserved_in_source_reports':True,'nondefinition_dependencies_preserved':True,
        'question_statuses_preserved':True,'actual_facts_established':False,
        'historical_law_established':False,'general_recall_established':False,'whole_task_complete':False}

def question_projection(ordinary,content):
    questions=deepcopy(ordinary['questions']);records={r['original_dependency']:r for r in content['records']}
    for link in content['question_links']:
        target=at(questions,link['path'][1:]);updated=[]
        for item in target['unresolved']:
            if item in records:updated.extend(i['id'] for i in records[item]['remaining_premises'])
            else:updated.append(item)
        updated.append(DISCOVERY);target['unresolved']=updated
    return questions

def expected_answer(ordinary,products,profile,content):
    value={**ordinary,KEY:{'version':VERSION,'profile_sha256':digest(profile),
        'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),**deepcopy(content)},
        'questions':question_projection(ordinary,content)}
    value['report_sha256']=digest({k:v for k,v in value.items() if k!='report_sha256'})
    return value

def verify(actual,ordinary,products,profile,content):
    assert actual==expected_answer(ordinary,products,profile,content),'Complete current-question projection differs from frozen expectation'
    return {'status':'PASS','whole_answer_equal_to_independent_expectation':True,
        'question_paths':5,'reviewed_records':62,'associations':612}
