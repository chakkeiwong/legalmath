"""One explicit, jointly delivered context review; never automatic resolution."""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import require,_indexed_locator_spans
from legalmath.interpretation.assurance.bounded_product import AUDIT


def select_context(product,qid,item,needs):
    require(needs and all(n.get('kind')=='SOURCE_TEXT' for n in needs),
        'Only explicit source-text needs can use this bridge','E_DEPENDENCY')
    origin=product.route.records.get(item['origin_id'])
    require(origin and origin['kind']=='source' and qid in product.acquisition_questions(origin),
        'Wrong bridge source scope','E_INTEGRITY')
    ids=[origin['id']];receipts=[]
    indexes={i['index_hash']:i for i in product.route.envelope.get('legal_indexes',[])}
    for need in needs:
        selected=list(need.get('record_ids',[]))
        for reference in need.get('locators',[]):
            require(reference['index_hash'] in indexes,'Unknown bridge document','E_INTEGRITY')
            index=indexes[reference['index_hash']]
            spans=_indexed_locator_spans(index,product.route.units,reference['locator'])
            require(spans,'Required locator has no retained source','E_DEPENDENCY')
            matches=[r['id'] for r in product.route.records.values() if r['kind']=='source' and
                any(r['unit_id']==span['unit_id'] and r['start']<span['end'] and r['end']>span['start']
                    for span in spans)]
            require(matches,'Required locator has no source records','E_DEPENDENCY')
            selected.extend(matches)
        if not selected and need.get('query'):
            retrieval=product.route.retrieve(need['query'],expand=False)
            receipts.append(retrieval)
            selected.extend(retrieval['record_ids'])
        require(selected,'Explicit source need has no deliverable context','E_DEPENDENCY')
        for rid in selected:
            record=product.route.records.get(rid)
            require(record and record['kind']=='source','Foreign source in bridge','E_INTEGRITY')
            require(qid in product.acquisition_questions(record),
                'Requested source is outside declared question scope','E_DEPENDENCY')
            ids.append(rid)
    return [product.route.records[rid] for rid in dict.fromkeys(ids)],receipts


def review(product,qid,question,answer,item,initial,needs,*,prefix='',admit=None):
    require(initial.get('status')=='VALIDATED' and initial['value']['verdict']=='UNRESOLVED',
        'Context continuation is for unresolved reviews; adverse verdicts need warrant assessment')
    require(initial['value']['considered']==[item['id']],'Initial context review belongs to another item')
    retained={'profile':'explicit-dependency-context-review.v1','original_review':deepcopy(initial),
        'item':deepcopy(item),'answer_hash':digest(answer),'needs':deepcopy(needs),
        'maximum_bridge_calls':1,'classification':'CONTEXT_CONTINUATION_NOT_ANSWER_RESAMPLING'}
    remaining = [n for n in initial['value'].get('context_needs', []) if n['kind'] != 'SOURCE_TEXT']
    if getattr(product, 'review_repair_profile', None):
        retained['remaining_context_needs'] = deepcopy(remaining)
    try:
        records,retrieval=select_context(product,qid,item,needs)
        payload={'answer':answer,'item':item,'original_review':initial['value'],'needs':needs,
            'assignment':'Review the original issue with all newly delivered context jointly. '
                'Determine whether the answer preserves the operative relationship, condition, '
                'exception and supported rival. Do not treat a retrieval hit or the earlier '
                'UNRESOLVED label as proof. ACCEPT only if this supplied evidence is sufficient '
                'for the assigned conditional answer. Preserve any further necessary missing '
                'authority or client fact explicitly. No further automatic bridge follows.'}
        request=product._request('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT',question,records,
            payload=payload,expected=[item['id']])
        measurement=product.dispatch.measure(request,AUDIT)
        key=prefix+'audit-context-'+qid+'-'+digest([item['id'],needs,digest(answer)])[:24]
        def check(value):
            require(value['considered']==[item['id']],'Lost bridge assignment')
            product.citations(value,records)
            if getattr(product, 'review_repair_profile', None):
                from .review_repair import validate_verdict
                validate_verdict(value)
                require(not remaining or value['verdict'] != 'ACCEPT',
                    'Source bridge cannot discharge an absent fact or external authority')
            require(value['verdict']!='ACCEPT' or (value['support'] and not value['issues'] and
                not value['source_gaps']),'Unsupported bridge acceptance')
        if admit is None:
            result=product.dispatch.call(key,request,AUDIT,check)
        else:
            from .phase import execute
            outcome=execute(product,key,[{'key':key,'request':request,'schema':AUDIT,'validate':check}],
                implementation_identity=product.phase_identity,admit=admit)
            result=(outcome['results'][0]['result'] if outcome['results'] else outcome['resource_refusal'])
        retained.update(result=result,delivered_ids=[r['id'] for r in records],
            retrieval=retrieval,measurement=measurement)
        if result['status'] == 'VALIDATED' and getattr(product, 'review_repair_profile', None):
            result['value']['context_needs'] = deepcopy(remaining)
    except Exception as exc:
        retained['result']=product.failure(exc)
    from legalmath.interpretation.assurance.monitor import save
    save(product.directory/(prefix+'context-review-'+digest(item['id'])[:24]+'.json'),retained)
    return retained
