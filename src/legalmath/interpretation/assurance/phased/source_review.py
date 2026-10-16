"""Staged complete source/dependency review, isolated from active execution.

This module supplies an executable candidate, not a live authorization. Original
source IDs and dependency IDs each retain a separate decision. Exact source
context is delivered; absent context must remain explicit.
"""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import require
from .grouping import pack_items, decision_schema, validate_decisions


def assignments(product, qid, dependencies):
    selected=[row for row in dependencies if row['question_id']==qid]
    require(len({r['id'] for r in selected})==len(selected),'Duplicate dependency identity')
    sources=[r for r in product.route.records.values() if r['kind']=='source'
        and qid in product.acquisition_questions(r)]
    source_ids={r['id'] for r in sources}
    require(all(r['origin_id'] in source_ids for r in selected),'Dependency origin outside question')
    grouped={rid:[] for rid in source_ids}
    for row in selected:
        grouped[row['origin_id']].append(deepcopy(row))
    result=[]
    for source in sources:
        result.append({'id':source['id'],'origin_id':source['id'],'kind':'source',
            'assignment':'Check every operative condition, exception and contrary inference '
                'in the original passage against this answer.'})
        result.extend(grouped[source['id']])
    return result


def build_request(product, question, answer, rows):
    ids=[r['id'] for r in rows]
    records=list({r['origin_id']:product.route.records[r['origin_id']] for r in rows}.values())
    # Preserve every original dependency field and decision, projecting provider
    # event logs through the existing content-addressed mechanism only.
    payload={'answer':answer,'assignments':rows,
        'assignment':'Review each member separately and return its own verdict. Read the '
            'full supplied original passages. Distinguish missing context in an earlier '
            'fragment from missing authority in the complete corpus. An exact source hash '
            'or a previous reading is not a substitute for delivered source text. '
            'A relevant unresolved dependency can pass only if this answer explicitly '
            'states the supported conditional consequences and needed evidence. If absent '
            'context prevents determining that, return UNRESOLVED with the precise context '
            'need. Preserve contradictory rules, exceptions, rivals and source qualifications. '
            'An assignment outside this question may be accepted only with an explicit '
            'question-scope reason, never by deleting the assignment. An empty/generic '
            'unknown is not adequate conditional legal analysis. Assertion bindings use '
            'paths relative to each decision, such as /reason or /issues/0.'}
    from legalmath.interpretation.assurance.bounded_product import project_provider_events
    projected,receipts=project_provider_events(payload)
    for sha,text in receipts.items():
        path=product.directory/'provenance'/(sha+'.jsonl')
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists(): require(path.read_text()==text,'Changed retained provider log')
        else: path.write_text(text)
    request=product._request('AUDIT_SOURCE_AND_DEPENDENCIES',question,records,payload=projected,expected=ids)
    request['review_scope']={'assigned_source_ids':[r['id'] for r in records],
        'dependency_ids':[r['id'] for r in rows if r.get('kind')!='source'],
        'instruction':'Acceptance is individual and limited to the assignment. Do not '
            'accept a proposition whose necessary source relationship is unresolved.'}
    return request,decision_schema(ids)


def run_review(product,qid,question,answer,dependencies,*,prefix='',maximum_items=4):
    product.route.check()
    corpus=[r for r in product.route.records.values() if r['kind']=='source']
    product.citations({k:v for k,v in answer.items() if k!='source_gaps'},corpus)
    items=assignments(product,qid,dependencies)
    def measure(rows):
        request,schema=build_request(product,question,answer,rows)
        try:
            measurement=product.dispatch.measure(request,schema)
        except LegalMathError as exc:
            if exc.code!='E_RESOURCE_LIMIT':raise
            return None
        return {'request_hash':digest(request),'schema_hash':digest(schema),
            'input':measurement}
    groups,blocked=pack_items(items,measure,maximum_items=maximum_items)
    reviews=[]
    for group in groups:
        rows=group['members'];ids=[r['id'] for r in rows]
        request,schema=build_request(product,question,answer,rows)
        require(digest(request)==group['measurement']['request_hash'] and
            digest(schema)==group['measurement']['schema_hash'],'Review changed after sizing')
        key=prefix+'audit-source-dependencies-'+qid+'-'+digest(ids)[:24]
        try:
            result=product.dispatch.call(key,request,schema,
                lambda value:validate_decisions(product,value,ids,request['records']))
        except Exception as exc:
            result=product.failure(exc)
        # Split only the returned *data*. No additional model samples or
        # affirmative group verdicts are synthesized from member receipts.
        for identity in ids:
            if result['status']=='VALIDATED':
                row={k:deepcopy(v) for k,v in result.items() if k!='value'}
                row['value']={**deepcopy(result['value']['decisions'][identity]),'considered':[identity]}
                row['group_evidence']={'key':key,'member_id':identity,'result_hash':digest(result)}
            else:
                row={**deepcopy(result),'assigned_ids':[identity],
                    'group_evidence':{'key':key,'member_id':identity,'result_hash':digest(result)}}
            reviews.append(row)
    for item in blocked:
        reviews.append({'status':'FAILED','error':'E_RESOURCE_LIMIT',
            'reason':'Complete individual source/dependency review cannot fit',
            'assigned_ids':[item['id']]})
    covered=[identity for row in reviews for identity in
        (row['value']['considered'] if row['status']=='VALIDATED' else row['assigned_ids'])]
    require(len(covered)==len(items) and set(covered)=={r['id'] for r in items},
        'Mandatory source/dependency review coverage lost')
    from legalmath.interpretation.assurance.monitor import save
    save(product.directory/(prefix+'source-dependency-review-'+qid+'.json'),
        {'profile':'staged-grouped-source-dependency-review.v1','reviews':reviews,
         'assigned_ids':[r['id'] for r in items],'group_count':len(groups),
         'blocked_ids':[r['id'] for r in blocked],
         'scope':'Engineering candidate; actual context bridges and live qualification remain required.'})
    return reviews
