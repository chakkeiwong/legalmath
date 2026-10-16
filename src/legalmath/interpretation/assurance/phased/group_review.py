"""Measured grouped reviews with explicit source needs and individual verdicts."""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.bounded_product import obj, array, TEXT, project_provider_events
from legalmath.interpretation.assurance.monitor import save
from .context_table import factor
from .grouping import pack_items
from .source_review import assignments
from .shared_rationale import schema as shared_schema, decisions as shared_decisions
from .phase import execute


def schema(ids, *, legal_indexes=None):
    result = shared_schema(ids)
    need = obj({'kind': {'type': 'string', 'enum': ['SOURCE_TEXT', 'CLIENT_FACT', 'EXTERNAL_AUTHORITY']},
        'reason': TEXT, 'record_ids': array(TEXT),
        'locators': array(obj({'index_hash': TEXT, 'locator': {
            'type': 'string', 'pattern': r'^(P|FN)[1-9][0-9]*$'}})),
        'query': {'type': 'string'}})
    if legal_indexes is not None:
        locators = need['properties']['locators']
        hashes = sorted({index['index_hash'] for index in legal_indexes})
        if hashes:
            locators['items']['properties']['index_hash'] = {**TEXT, 'enum': hashes}
        else:
            locators['maxItems'] = 0
    decision = result['$defs']['Decision']
    decision['properties']['context_needs'] = array(need)
    decision['required'].append('context_needs')
    return result


def validate(product, qid, value, ids, records):
    from jsonschema import validate as validate_schema
    validate_schema(value, schema(ids, legal_indexes=product.route.envelope.get('legal_indexes', [])))
    plain = deepcopy(value)
    for row in plain['analyses']:
        row['decision'].pop('context_needs')
    result = shared_decisions(product, plain, ids, records)
    table = {r['analysis_id']: r['decision']['context_needs'] for r in value['analyses']}
    indexes = {i['index_hash'] for i in product.route.envelope.get('legal_indexes', [])}
    for row in value['analyses']:
        decision = row['decision']
        require(decision['verdict'] != 'ACCEPT' or not decision['context_needs'],
                'Accepted review retains necessary context')
        for need in decision['context_needs']:
            if need['kind'] == 'SOURCE_TEXT':
                require(need['record_ids'] or need['locators'] or need['query'].strip(),
                        'Source need has no source identification or query')
                for rid in need['record_ids']:
                    record = product.route.records.get(rid)
                    require(record and record['kind'] == 'source' and
                            qid in product.acquisition_questions(record), 'Foreign source context request')
                require(all(r['index_hash'] in indexes for r in need['locators']), 'Foreign context document')
            else:
                require(not need['record_ids'] and not need['locators'],
                        'Client facts or absent external authority cannot be supplied by retained-source IDs')
    for identity, row in result.items():
        row['decision']['context_needs'] = deepcopy(table[row['analysis_id']])
    return result


def build(product, qid, question, answer, rows):
    ids = [r['id'] for r in rows]
    records = list({r['origin_id']: product.route.records[r['origin_id']] for r in rows}.values())
    payload = {'answer': answer, **factor(rows),
        'assignment': 'Individually review every source/dependency assignment against this answer. '
            'Each item must explicitly choose a rationale; share it only if reason, scope, verdict, '
            'evidence and context needs apply to each assigned item. Otherwise use separate rationales. '
            'Prior readings and follow-ups are proposals, not source authority. Preserve operative '
            'conditions, contrary sources, exceptions, supported rivals and source qualifications. '
            'Assess necessity within question_scope. A source absent from this window is not absent '
            'from the corpus or law. Return UNRESOLVED and identify necessary context when the '
            'relationship cannot be decided from jointly delivered text. Distinguish SOURCE_TEXT, '
            'CLIENT_FACT and EXTERNAL_AUTHORITY needs. Conditional consequences and specific factual '
            'needs can be a complete conditional answer; generic uncertainty is insufficient. '
            'context_needs means information necessary to judge whether the answer AS WRITTEN is '
            'warranted. It is not a wish list for resolving the ultimate case. If the supplied text '
            'suffices to verify the answer\'s conditional alternatives and its specific missing-authority '
            'limitation, ACCEPT may be appropriate with context_needs empty; explain the outstanding '
            'case information in reason. Do not ACCEPT if missing context prevents checking the '
            'answer\'s actual claims: return UNRESOLVED and identify that necessary context. '
            'Use assertion paths relative to each decision. Keep all rationales and assignments within '
            'the unchanged output limit; do not merge distinct issues to save space.'}
    projected, receipts = project_provider_events(payload)
    for sha, events in receipts.items():
        path = product.directory / 'provenance' / (sha + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            require(path.read_text() == events, 'Changed retained event log')
        else:
            path.write_text(events)
    request = product._request('AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', question, records,
                               payload=projected, expected=ids)
    cited = product.source_records(payload)
    request['review_scope'] = {'assigned_source_ids': [r['id'] for r in records],
        'cited_source_ids_outside_window': [r['id'] for r in cited if r not in records],
        'instruction': 'The full answer has independent exact-citation checks. Outside quotations '
            'are not jointly delivered legal context here. If necessary for this assignment, '
            'request the precise context; do not infer support or contradiction from absence.'}
    return request, schema(ids, legal_indexes=product.route.envelope.get('legal_indexes', []))


def plan(product, qid, question, answer, dependencies, *, prefix='', maximum_items=16):
    corpus = [r for r in product.route.records.values() if r['kind'] == 'source']
    product.citations({k: v for k, v in answer.items() if k != 'source_gaps'}, corpus)
    items = assignments(product, qid, dependencies)
    def measure(rows):
        request, response_schema = build(product, qid, question, answer, rows)
        try:
            return {'request_hash': digest(request), 'schema_hash': digest(response_schema),
                    'measurement': product.dispatch.measure(request, response_schema)}
        except LegalMathError as exc:
            if exc.code != 'E_RESOURCE_LIMIT':
                raise
            return None
    groups, blocked = pack_items(items, measure, maximum_items=maximum_items)
    calls, membership = [], {}
    for group in groups:
        rows = group['members']
        ids = [r['id'] for r in rows]
        request, response_schema = build(product, qid, question, answer, rows)
        require(digest(request) == group['measurement']['request_hash'] and
                digest(response_schema) == group['measurement']['schema_hash'], 'Changed grouped request')
        key = prefix + 'audit-group-' + qid + '-' + digest(ids)[:24]
        membership[key] = ids
        calls.append({'key': key, 'request': request, 'schema': response_schema,
            'validate': lambda value, ids=ids, records=request['records']:
                validate(product, qid, value, ids, records)})
    return calls, membership, blocked, items


def run(product, qid, question, answer, dependencies, *, implementation_identity, admit,
        prefix='', maximum_items=16, refresh=lambda _: None):
    calls, membership, blocked, items = plan(product, qid, question, answer, dependencies,
                                            prefix=prefix, maximum_items=maximum_items)
    phase = execute(product, prefix + 'source-dependency-' + qid, calls,
        implementation_identity=implementation_identity, admit=admit, refresh=refresh)
    results = {r['key']: r['result'] for r in phase['results']}
    requests = {r['key']: r['request'] for r in calls}
    reviews = []
    for key, ids in membership.items():
        result = results.get(key, phase.get('resource_refusal', {
            'status': 'FAILED', 'error': 'E_DEPENDENCY', 'reason': 'No completed group result'}))
        individual = validate(product, qid, result['value'], ids, requests[key]['records']) \
            if result['status'] == 'VALIDATED' else None
        for identity in ids:
            if individual is not None:
                decision = individual[identity]
                review = {k: deepcopy(v) for k, v in result.items() if k != 'value'}
                review['value'] = {**decision['decision'], 'considered': [identity]}
                review['group_evidence'] = {'key': key, 'member_id': identity,
                    'analysis_id': decision['analysis_id'], 'result_hash': digest(result)}
            else:
                review = {**deepcopy(result), 'assigned_ids': [identity]}
            reviews.append(review)
    reviews += [{'status': 'FAILED', 'error': 'E_RESOURCE_LIMIT',
        'reason': 'Complete individual review cannot fit', 'assigned_ids': [r['id']]} for r in blocked]
    observed = [identity for r in reviews for identity in
                (r['value']['considered'] if r['status'] == 'VALIDATED' else r['assigned_ids'])]
    require(len(observed) == len(set(observed)) and set(observed) == {r['id'] for r in items},
            'Lost mandatory source/dependency review member')
    from .evidence_store import save_exact
    save_exact(product.directory / (prefix + 'contextual-group-review-' + qid + '.json'),
        {'reviews': reviews, 'phase': phase, 'assigned_ids': [r['id'] for r in items],
         'scope': 'Individual source reviews. Live semantic qualification remains required.'})
    return reviews

