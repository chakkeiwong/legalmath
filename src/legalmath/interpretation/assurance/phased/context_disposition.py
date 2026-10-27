"""One evidence-dependent continuation with explicit accounting for every need.

This opt-in successor preserves the original verdict. Structural checks prevent
lost needs and invented evidence; substantive necessity remains a review judgment.
"""
from copy import deepcopy
from jsonschema import validate as validate_schema
from legalmath.canonical import digest
from ..bounded_context import require
from ..bounded_product import AUDIT, QUOTE, TEXT, obj, array
from ..integration_contract import read_evidence
from ..monitor import save

PROFILE = 'explicit-context-need-disposition.v1'


def need_rows(product, item, initial, *, prefix=''):
    mapping = set()
    retained_sources = {}
    # The classifications bind exact original decisions. A fresh corrected
    # review is a new population, even when its assignment IDs are unchanged.
    # Match review_checkpoint.resume's original-only reuse boundary.
    if not prefix and product.capacity_checkpoint is not None:
        outer = read_evidence(product.capacity_checkpoint, product.root)
        if outer.get('individual_reviews'):
            checkpoint = read_evidence(outer['individual_reviews'], product.root)
            if checkpoint.get('mapping_needs'):
                reviewed = read_evidence(checkpoint['mapping_needs'], product.root)
                for row in reviewed['needs']:
                    if row['assignment_id'] == item['id']:
                        require(row['decision_hash'] == digest(initial['value']),
                            'Changed mapping-need predecessor', 'E_INTEGRITY')
                        mapping.add(row['need_hash'])
            if checkpoint.get('retained_source_needs'):
                reviewed = read_evidence(checkpoint['retained_source_needs'], product.root)
                for row in reviewed['needs']:
                    if row['assignment_id'] == item['id']:
                        require(row['decision_hash'] == digest(initial['value']) and row['record_ids'],
                            'Changed retained-source need predecessor', 'E_INTEGRITY')
                        retained_sources[row['need_hash']] = row
    needs = initial['value'].get('context_needs', [])
    if not needs:
        needs = [dict(kind='REVIEW_QUESTION', reason=initial['value']['reason'])]
    require(mapping <= {digest(n) for n in needs}, 'Missing enumerated mapping need', 'E_INTEGRITY')
    require(set(retained_sources) <= {digest(n) for n in needs} and not mapping.intersection(retained_sources),
        'Missing or conflicting retained-source need', 'E_INTEGRITY')
    rows = []
    for i, need in enumerate(needs):
        row = dict(need_id='need-'+str(i), original_need=deepcopy(need),
            route='ASSIGNMENT_MAPPING' if digest(need) in mapping else need['kind'])
        if digest(need) in retained_sources:
            require(need['kind'] == 'EXTERNAL_AUTHORITY', 'Invalid source reclassification', 'E_INTEGRITY')
            reviewed = retained_sources[digest(need)]
            row.update(route='SOURCE_TEXT', reviewed_source_need=dict(kind='SOURCE_TEXT',
                record_ids=reviewed['record_ids'], locators=[], query='', reason=reviewed['reason']),
                reclassification_reason=reviewed['reason'])
        rows.append(row)
    return rows


def answer_paths(answer):
    paths=[]
    def visit(value,path=''):
        if isinstance(value,dict):
            for key,child in value.items():
                visit(child,path+'/'+key.replace('~','~0').replace('/','~1'))
        elif isinstance(value,list):
            for i,child in enumerate(value): visit(child,path+'/'+str(i))
        elif isinstance(value,str): paths.append(path)
    visit(answer)
    return paths


def schema(rows, answer=None):
    from .group_review import schema as grouped_schema
    result = deepcopy(AUDIT)
    need = grouped_schema(['x'])['$defs']['Decision']['properties']['context_needs']
    result['properties']['context_needs'] = deepcopy(need)
    result['properties']['need_dispositions'] = array(obj({
        'need_id': {'type': 'string', 'enum': [r['need_id'] for r in rows]},
        'disposition': {'type': 'string', 'enum': ['STILL_REQUIRED', 'SUPPLIED_SOURCE',
            'MAPPING_CLARIFIED', 'NOT_REQUIRED_FOR_CONDITIONAL_ANSWER']},
        'reason': TEXT, 'answer_evidence': obj({'path': ({'type': 'string', 'enum': ['',*answer_paths(answer)]}
            if answer is not None else {'type':'string'}), 'quote': {'type': 'string'}}),
        'support': array(QUOTE)}))
    result['required'] += ['context_needs', 'need_dispositions']
    return result


def answer_quote(answer, path, quote):
    require(path.startswith('/') and quote, 'Need waiver lacks an exact answer quotation')
    value = answer
    try:
        for component in path[1:].split('/'):
            component = component.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                require(component.isdigit(), 'Invalid answer quote index')
                value = value[int(component)]
            else:
                value = value[component]
    except (KeyError, IndexError, TypeError):
        require(False, 'Need waiver points outside the actual answer')
    require(isinstance(value, str) and quote in value,
        'Need waiver quotation is absent from the actual answer')


def validate(product, qid, value, answer, item, rows, records, failures):
    from .review_repair import validate_verdict
    validate_schema(value, schema(rows,answer))
    require(value['considered'] == [item['id']], 'Lost context-continuation assignment')
    product.citations(value, records)
    validate_verdict(value)
    dispositions = value['need_dispositions']
    require(len(dispositions) == len(rows) and
        {r['need_id'] for r in dispositions} == {r['need_id'] for r in rows},
        'Missing or duplicate prior-need dispositions')
    table = {r['need_id']: r for r in rows}
    for result in dispositions:
        row = table[result['need_id']]
        need, disposition = row['original_need'], result['disposition']
        evidence = result['answer_evidence']
        if evidence['path'] or evidence['quote']:
            from legalmath.errors import LegalMathError
            try:
                answer_quote(answer, evidence['path'], evidence['quote'])
            except LegalMathError as exc:
                require(False, 'Invalid response answer quotation: ' + str(exc.details or exc), 'E_SCHEMA')
        if row['need_id'] in failures:
            require(disposition == 'STILL_REQUIRED', 'Failed source delivery cannot be waived')
        if disposition == 'STILL_REQUIRED':
            require(value['verdict'] != 'ACCEPT', 'Accepted review retains a necessary need')
            if row['route'] != 'REVIEW_QUESTION':
                require(need in value['context_needs'], 'Necessary original context need was lost')
        elif disposition == 'SUPPLIED_SOURCE':
            require(row['route'] == 'SOURCE_TEXT' and result['support'],
                'Source text cannot supply a missing fact, authority or assignment mapping')
        elif disposition == 'MAPPING_CLARIFIED':
            require(row['route'] == 'ASSIGNMENT_MAPPING', 'Unreviewed mapping-need waiver')
        else:
            require(result['support'], 'Conditional need waiver lacks delivered source support')
            answer_quote(answer, result['answer_evidence']['path'], result['answer_evidence']['quote'])
    indexes = {i['index_hash'] for i in product.route.envelope.get('legal_indexes', [])}
    for need in value['context_needs']:
        if need['kind'] == 'SOURCE_TEXT':
            require(need['record_ids'] or need['locators'] or need['query'].strip(),
                'Source need lacks an identification or query')
            for rid in need['record_ids']:
                record = product.route.records.get(rid)
                require(record and record['kind'] == 'source' and qid in product.acquisition_questions(record),
                    'Foreign source context request')
            require(all(r['index_hash'] in indexes for r in need['locators']), 'Unknown context document')
        else:
            require(not need['record_ids'] and not need['locators'],
                'Missing client facts or authority cannot carry retained-source identifiers')


def prepare(product, qid, question, answer, item, initial, *, prefix=''):
    from .context_bridge import select_context
    require(initial.get('status') == 'VALIDATED' and initial['value']['verdict'] == 'UNRESOLVED'
        and initial['value']['considered'] == [item['id']], 'Invalid context continuation predecessor')
    rows = need_rows(product, item, initial, prefix=prefix)
    origin = product.route.records.get(item['origin_id'])
    require(origin and origin['kind'] == 'source' and qid in product.acquisition_questions(origin),
        'Wrong continuation source scope', 'E_INTEGRITY')
    records = {origin['id']: origin}
    for record in product.source_records({'answer': answer, 'assignment': item, 'review': initial['value']}):
        if qid in product.acquisition_questions(record):
            records[record['id']] = record
    retrieval, failures = [], {}
    for row in rows:
        if row['route'] != 'SOURCE_TEXT':
            continue
        try:
            selected, receipts = select_context(product, qid, item,
                [row.get('reviewed_source_need', row['original_need'])], scoped=True)
            records.update({r['id']: r for r in selected})
            retrieval.append(dict(need_id=row['need_id'], receipts=receipts,
                delivered_ids=[r['id'] for r in selected]))
        except Exception as exc:
            failures[row['need_id']] = product.failure(exc)
    payload = dict(answer=answer, item=item, original_review=initial['value'], prior_needs=rows,
        source_delivery_failures=failures,
        assignment_correspondence=dict(original_assignment_id=item['id'],
            delivered_item={'id': item['id']}, required_considered=[item['id']],
            evidence_kind='IMPLEMENTATION_CORRESPONDENCE_NOT_LEGAL_SOURCE'),
        assignment='Reassess this exact unresolved assignment once against the unchanged answer, '
            'complete assignment and jointly delivered source text. Account for every prior need '
            'exactly once. The correspondence identifies the original assignment explicitly; it '
            'does not settle its legal substance. SUPPLIED_SOURCE requires exact source support '
            'and cannot supply an absent client fact or authority. An explicit reviewed_source_need '
            'reclassifies only the specified already-retained authority passages as source text; '
            'it does not establish current law or waive absent authority. MAPPING_CLARIFIED applies only '
            'to enumerated implementation correspondence needs. NOT_REQUIRED_FOR_CONDITIONAL_ANSWER '
            'requires an exact answer_evidence path and quote plus source support and a specific '
            'explanation of why that conditional claim can be checked without the missing evidence. '
            'answer_evidence.path must be an answer-relative JSON Pointer selected '
            'from the schema, such as /conclusion or /unresolved/4. Do not use JSONPath, brackets, '
            'a dollar prefix or /payload/answer. Use the empty path and quote when no answer '
            'quotation is needed. The quoted text must occur exactly at that selected answer path. '
            'Assess the actual conditional consequences and preserved rivals; generic uncertainty '
            'is insufficient. A failed source delivery must remain STILL_REQUIRED. Retain every '
            'still-required original typed need verbatim in context_needs and identify any new '
            'necessary context. ACCEPT needs source support, no issues, no source gaps, no necessary '
            'needs, and every prior need accounted for. REJECT needs a supported adverse issue. '
            'A REVIEW_QUESTION is an untyped prior explanation, not an invented factual or source '
            'request. Preserve it as STILL_REQUIRED unless its conditional-answer disposition is '
            'specifically justified. No retrieval hit or prior label establishes legal truth. '
            'All assertion paths are relative to this response. No automatic further review follows.')
    request = product._request('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT', question, list(records.values()),
        payload=payload, expected=[item['id']])
    request['context_disposition_profile'] = PROFILE
    request['answer_pointer_profile']='answer-relative-string-pointer.v1'
    reference_profile = getattr(product, 'context_reference_profile', None)
    if reference_profile is not None:
        from .context_references import PROFILE as REFERENCE_PROFILE, FIELD
        require(reference_profile == REFERENCE_PROFILE, 'Unknown context reference profile', 'E_AUTHORITY')
        request[FIELD] = reference_profile
    return request, schema(rows,answer), rows, retrieval, failures


def review(product, qid, question, answer, item, initial, *, prefix='', admit=None):
    retained = dict(profile=PROFILE, original_review=deepcopy(initial), item=deepcopy(item),
        answer_hash=digest(answer), maximum_bridge_calls=1, legal_acceptance=False)
    try:
        request, shape, rows, receipts, failures = prepare(product, qid, question, answer, item, initial,
            prefix=prefix)
        retained.update(prior_needs=rows, retrieval=receipts, source_delivery_failures=failures,
            delivered_ids=[r['id'] for r in request['records']])
        retained['measurement'] = product.dispatch.measure(request, shape)
        key = prefix+'audit-context-disposition-'+qid+'-'+digest([item['id'],initial['value'],answer])[:24]
        def check(value):
            validate(product, qid, value, answer, item, rows, request['records'], failures)
        if admit is None:
            result = product.dispatch.call(key, request, shape, check)
        else:
            from .phase import execute
            outcome = execute(product, key, [dict(key=key,request=request,schema=shape,validate=check)],
                implementation_identity=product.phase_identity, admit=admit)
            result = (outcome['results'][0]['result'] if outcome['results'] else outcome['resource_refusal'])
        retained['result'] = result
    except Exception as exc:
        from .service_prerequisite import ServiceDeferred
        if isinstance(exc, ServiceDeferred) or getattr(exc, 'code', None) in ('E_AUTHORITY', 'E_INTEGRITY'):
            raise
        retained['result'] = product.failure(exc)
    save(product.directory/(prefix+'context-review-'+digest(item['id'])[:24]+'.json'), retained)
    return retained
