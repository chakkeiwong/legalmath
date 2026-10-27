"""Authenticated individual review reuse across an explicit contract repair.

The old population, failures and provider journals remain immutable. New work
is limited to a reviewed list of failed assignments. Valid adverse/uncertain
reviews are reused exactly; only later evidence-dependent stages may refine them.
"""
from copy import deepcopy
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import read_evidence
from . import group_review, capacity_policy, review_contract
from .context_table import expand

PROFILE = 'individual-review-continuation.v1'


def resume(product, qid, question, answer, dependencies, *, prefix='', refresh=lambda _: None):
    if prefix or product.capacity_checkpoint is None:
        return None
    outer = read_evidence(product.capacity_checkpoint, product.root)
    pointer = outer.get('individual_reviews')
    if pointer is None:
        return None
    from .source_review import assignments
    from .phase import execute
    from .review_repair import split_result, PROFILE as REPAIR
    from .evidence_store import save_exact
    checkpoint = read_evidence(pointer, product.root)
    require(checkpoint['profile'] == PROFILE and checkpoint['question_id'] == qid
        and checkpoint['input_hash'] == product.route.input_hash
        and checkpoint['answer_hash'] == digest(answer)
        and product.review_assignment_profile == review_contract.PROFILE,
        'Foreign individual review continuation', 'E_INTEGRITY')
    population = read_evidence(checkpoint['population'], product.root)
    items = assignments(product, qid, dependencies)
    table = {r['id']:r for r in items}
    require(population['assigned_ids'] == list(table), 'Changed review population', 'E_INTEGRITY')
    records = read_evidence(checkpoint['source_store'], product.root)
    require(all(product.route.records.get(k) == v for k,v in records.items()),
        'Changed retained source or requirement', 'E_INTEGRITY')
    verified = {}

    def checked_call(key):
        if key in verified:
            return verified[key]
        refs = checkpoint['calls'][key]
        request, schema, result, journal = [read_evidence(refs[n], product.root)
            for n in ('request', 'schema', 'result', 'dispatch')]
        row = journal['calls'][key]
        require(journal['input_hash'] == product.route.input_hash and row['status'] != 'RESERVED'
            and row['status'] == result['status'] and row['result_hash'] == digest(result)
            and row['identity'] == product.dispatch.request_identity(request, schema),
            'Changed or uncertain retained review dispatch', 'E_INTEGRITY')
        ids = request['required_considered']
        require(request['input_hash'] == product.route.input_hash
            and request['task'] == review_contract.TASK
            and request['payload']['answer'] == answer
            and request['question'] == question and len(ids) == len(set(ids))
            and set(ids) <= set(table), 'Changed retained review context', 'E_INTEGRITY')
        rows = expand(request['payload'])
        require(all(table.get(r['id']) == r for r in rows)
            and set(ids) <= {r['id'] for r in rows}
            and all(product.route.records.get(r['id']) == r for r in request['records']),
            'Changed retained assignment/source content', 'E_INTEGRITY')
        require(any(schema == group_review.schema(ids,
            legal_indexes=product.route.envelope.get('legal_indexes', []), repair_profile=p)
            for p in (None, REPAIR)), 'Unreviewed predecessor review schema', 'E_INTEGRITY')
        raw = read_evidence(refs['raw'], product.root)['value'] if refs.get('raw') else None
        valid, _ = split_result(product, qid, result, ids, request, raw)
        verified[key] = request, result, valid
        return verified[key]

    reviews, calls, failed = [], [], []
    for review in population['reviews']:
        if review['status'] == 'VALIDATED':
            identity, = review['value']['considered']
            evidence = review.get('group_evidence') or review['repair_evidence']
            _, result, valid = checked_call(evidence['key'])
            require(evidence['result_hash'] == digest(result) and identity in valid
                and review['value'] == {**valid[identity]['decision'], 'considered':[identity]},
                'Changed individual review decision', 'E_INTEGRITY')
            reviews.append(deepcopy(review))
            continue
        identity, = review['assigned_ids']
        failed.append(identity)
        prior = checkpoint['repairs'][identity]
        request, result, _ = checked_call(prior['key'])
        require(result == review or all(review.get(k) == v for k,v in result.items()),
            'Reviewed failure differs from predecessor', 'E_INTEGRITY')
        require(request['required_considered'] == [identity] and result['status'] == 'FAILED',
            'Cannot retry a settled success', 'E_AUTHORITY')
        request = deepcopy(request)
        request[review_contract.FIELD] = review_contract.PROFILE
        request['payload']['reviewed_contract_continuation'] = dict(
            predecessor=checkpoint['calls'][prior['key']]['result'],
            review=checkpoint['review'], maximum_attempts=1,
            instruction='Reassess this exact failed assignment with the explicit mapping. '
                'The predecessor is retained as failure evidence; do not seek a favorable verdict.')
        schema = group_review.schema([identity], legal_indexes=product.route.envelope.get('legal_indexes', []),
            repair_profile=REPAIR)
        calls.append(dict(key=prior['key']+'-contract-continuation', request=request, schema=schema,
            validate=lambda value, identity=identity, records=request['records']:
                group_review.validate(product, qid, value, [identity], records)))
    require(failed == checkpoint['failed_ids'] and len(reviews) == checkpoint['validated_count'],
        'Changed reviewed continuation scope', 'E_AUTHORITY')
    save_exact(product.directory/('review-import-validation-'+qid+'.json'), dict(
        checkpoint=pointer, answer_hash=digest(answer), validated_individuals=len(reviews),
        validated_original_calls=len(verified), failed_continuations=len(calls),
        provider_calls=0, legal_acceptance=False))
    # Qualify this actual contract first. If it fails, retain remaining work as
    # undispatched. A service deferral propagates without consuming an attempt.
    first = execute(product, 'review-contract-canary-'+qid, calls[:1],
        implementation_identity=product.phase_identity, admit=product.phase_admit, refresh=refresh)
    qualified = not calls or (bool(first['results']) and first['results'][0]['result']['status'] == 'VALIDATED')
    rest = (execute(product, 'review-contract-remainder-'+qid, calls[1:],
        implementation_identity=product.phase_identity, admit=product.phase_admit, refresh=refresh)
        if qualified else dict(results=[]))
    outcomes = {r['key']:r['result'] for r in first['results']+rest['results']}
    for call, identity in zip(calls, failed):
        result = outcomes.get(call['key'], dict(status='FAILED', error='E_DEPENDENCY',
            reason='Contract canary did not validate; continuation not dispatched'))
        if result['status'] == 'VALIDATED':
            value = group_review.validate(product, qid, result['value'], [identity], call['request']['records'])[identity]
            reviews.append(dict(status='VALIDATED', value={**value['decision'], 'considered':[identity]},
                repair_evidence=dict(key=call['key'], result_hash=digest(result), maximum_attempts=1),
                continuation_checkpoint=pointer))
        else:
            reviews.append({**deepcopy(result), 'assigned_ids':[identity], 'continuation_checkpoint':pointer})
    order = {identity:i for i,identity in enumerate(table)}
    reviews.sort(key=lambda r: order[(r['value']['considered'] if r['status']=='VALIDATED' else r['assigned_ids'])[0]])
    require(len(reviews)==len(table), 'Lost individual review', 'E_INTEGRITY')
    save_exact(product.directory/('contextual-group-review-'+qid+'.json'), dict(
        reviews=reviews, assigned_ids=list(table), predecessor=pointer,
        phase=first, repair_phase=rest, format_qualified=qualified,
        scope='Exact valid predecessors retained; only reviewed failed assignments receive one continuation.'))
    return reviews
