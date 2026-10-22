"""Explicit review repair: typed needs, individual validity and issue dependencies.

This profile does not relax legal acceptance. It permits independent repair
work while retaining every invalid, missing or unresolved decision.
"""
from copy import deepcopy
import json
from jsonschema import validate as validate_schema
from legalmath.canonical import digest
from ..bounded_context import require
from ..bounded_product import WARRANT
from ..monitor import save

PROFILE = 'source-review-repair.v1'
TASKS = {'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', 'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT',
    'AUDIT_ANSWER_AND_DETAILED_ACCOUNT', 'ASSESS_REVIEW_WARRANT',
    'CORRECT_REVIEWED_REQUIREMENT', 'CORRECT_REVIEWED_ANSWER'}


def validate_verdict(value):
    if value['verdict'] == 'REJECT':
        require(value['support'] and value['issues'], 'Rejected review lacks supported adverse issues')
    if value['verdict'] == 'ACCEPT':
        require(value['support'] and not value['issues'] and not value['source_gaps']
            and not value.get('context_needs'), 'Accepted review retains defects or lacks support')


def typed_schema(schema, profile):
    require(profile == PROFILE, 'Unknown typed review profile', 'E_AUTHORITY')
    result = deepcopy(schema)
    decision = result['$defs']['Decision']
    need = decision['properties']['context_needs']['items']
    variants = []
    for kind in ('SOURCE_TEXT', 'CLIENT_FACT', 'EXTERNAL_AUTHORITY'):
        variant = deepcopy(need)
        variant['properties']['kind']['enum'] = [kind]
        if kind != 'SOURCE_TEXT':
            variant['properties']['record_ids']['maxItems'] = 0
            variant['properties']['locators']['maxItems'] = 0
        variants.append(variant)
    decision['properties']['context_needs']['items'] = {'anyOf': variants}
    variants = []
    for verdict in ('ACCEPT', 'REJECT', 'UNRESOLVED'):
        variant = deepcopy(decision)
        variant['properties']['verdict']['enum'] = [verdict]
        if verdict in ('ACCEPT', 'REJECT'):
            variant['properties']['support']['minItems'] = 1
        if verdict == 'REJECT':
            variant['properties']['issues']['minItems'] = 1
        if verdict == 'ACCEPT':
            for name in ('issues', 'source_gaps', 'context_needs'):
                variant['properties'][name]['maxItems'] = 0
        variants.append(variant)
    result['$defs']['Decision'] = {'anyOf': variants}
    return result


def individual_decisions(product, qid, value, ids, records):
    """Check the common assignment map first, then isolate bad rationales."""
    from . import group_review
    require(isinstance(value, dict) and set(value) == {'analyses', 'assignments'},
        'Malformed review envelope')
    analyses, assignments = value['analyses'], value['assignments']
    require(isinstance(analyses, list) and isinstance(assignments, dict)
        and set(assignments) == set(ids), 'Missing individual review assignments')
    require(all(isinstance(r, dict) and set(r) == {'analysis_id', 'decision'}
        and isinstance(r['analysis_id'], str) for r in analyses), 'Malformed rationale envelope')
    table = {r['analysis_id']: r for r in analyses}
    require(len(table) == len(analyses) and all(isinstance(r, dict) and set(r) == {'analysis_id'}
        and r['analysis_id'] in table for r in assignments.values()), 'Invalid rationale membership')
    require({r['analysis_id'] for r in assignments.values()} == set(table), 'Unassigned rationale')
    valid, invalid = {}, {}
    for identity in ids:
        single = {'analyses': [table[assignments[identity]['analysis_id']]],
                  'assignments': {identity: assignments[identity]}}
        try:
            valid[identity] = group_review.validate(product, qid, single, [identity], records)[identity]
        except Exception as exc:
            invalid[identity] = {'reason': str(getattr(exc, 'details', None) or exc),
                'original': deepcopy(single)}
    return valid, invalid


def split_result(product, qid, result, ids, request, raw=None):
    value = result.get('value') if result.get('status') == 'VALIDATED' else raw
    if value is None:
        return {}, {}  # Transport failures are handled by the provider policy.
    try:
        return individual_decisions(product, qid, value, ids, request['records'])
    except Exception as exc:
        # A damaged common map cannot be guessed. Each exact assignment can
        # receive its one explicit repair under the retained original output.
        return {}, {identity: {'reason': str(getattr(exc, 'details', None) or exc),
            'original': deepcopy(value)} for identity in ids}


def repair_diagnostic(invalid, *, product=None, key=None, identity=None):
    """Keep failed output as evidence, not duplicated source context.

    A 512-character excerpt is a convenience diagnostic, never a substitute for
    answer/source content. Every reassessment receives that complete content and
    exact identities of the full retained failure and original model output.
    """
    retained = {}
    if product is not None:
        from .evidence_store import save_exact, load_exact
        from ..integration_contract import evidence_file
        path = product.directory/'review-diagnostics'/key/(digest(identity)+'.json')
        if path.exists():
            require(load_exact(path) == invalid, 'Invalid review diagnostic changed', 'E_INTEGRITY')
        else:
            save_exact(path, invalid)
        retained['full_diagnostic'] = evidence_file(path, product.root)
    return {**retained, 'reason_excerpt': invalid['reason'][:512],
        'full_reason_sha256': digest(invalid['reason']),
        'original_review_sha256': digest(invalid['original']),
        'diagnostic_scope': 'Excerpt only; complete invalid response and reason retained as evidence. '
            'Reassess the exact assignment against the unchanged answer and full delivered sources.'}


def grouped_reviews(product, qid, question, answer, dependencies, *, implementation_identity,
                    admit, prefix='', refresh=lambda _: None):
    from . import group_review
    from .phase import execute
    from .evidence_store import save_exact
    retained_calls, retained_results = retained_groups(product, qid, question, answer, dependencies, prefix=prefix)
    held_ids = [identity for c in retained_calls for identity in c['request']['required_considered']]
    calls, membership, blocked, items = group_review.plan(product, qid, question, answer, dependencies,
        prefix=prefix, exclude_ids=held_ids)
    name = prefix+'source-dependency-'+qid
    # A larger format is a candidate until one complete actual batch validates.
    # Each arm/answer must qualify its own context. A failed first group still
    # reaches individual repair below, but cannot dispatch the other groups.
    first = execute(product, name+'-qualification', calls[:1],
        implementation_identity=implementation_identity, admit=admit, refresh=refresh)
    qualified = not calls or (bool(first['results']) and first['results'][0]['result']['status'] == 'VALIDATED')
    rest = (execute(product, name+'-qualified', calls[1:],
        implementation_identity=implementation_identity, admit=admit, refresh=refresh)
        if qualified else {'results': [], 'execution_complete': not calls[1:]})
    phase = {'phase': name, 'results': first['results'] + rest['results'],
        'execution_complete': first['execution_complete'] and rest['execution_complete'],
        'format_qualified': qualified, 'legal_acceptance': False}
    for outcome in (first, rest):
        if outcome.get('resource_refusal'):
            phase['resource_refusal'] = deepcopy(outcome['resource_refusal'])
    if not qualified and calls[1:]:
        phase.setdefault('resource_refusal', {'status': 'FAILED', 'error': 'E_DEPENDENCY',
            'reason': 'Larger review format did not qualify; remaining batches were not dispatched'}
        )
    save_exact(product.directory/(name+'-qualification.json'), {
        'first_group': calls[0]['key'] if calls else None, 'qualified': qualified,
        'first_result': first, 'withheld_groups': [] if qualified else [c['key'] for c in calls[1:]],
        'legal_acceptance': False})
    results = {r['key']: r['result'] for r in phase['results']}
    results.update(retained_results)
    membership.update({c['key']: c['request']['required_considered'] for c in retained_calls})
    calls = retained_calls + calls
    from .source_review import assignments
    items = assignments(product, qid, dependencies)
    table = {r['id']: r for r in items}
    reviews, repairs = [], []
    for call in calls:
        key, ids = call['key'], membership[call['key']]
        result = results.get(key, phase.get('resource_refusal', {
            'status': 'FAILED', 'error': 'E_DEPENDENCY', 'reason': 'No completed group result'}))
        raw = call.get('retained_raw')
        raw_path = product.dispatch.directory/key/'raw.json'
        if result['status'] != 'VALIDATED' and raw_path.exists():
            from .capacity_policy import annotate, measure_output
            request_path = raw_path.with_name('request.json')
            prepared_call = product.prepare_calls([call])[0]
            require(json.loads(request_path.read_text()) == annotate(prepared_call['request']),
                'Malformed review belongs to another request', 'E_INTEGRITY')
            require(json.loads(raw_path.with_name('result.json').read_text()) == result,
                'Malformed review result changed', 'E_INTEGRITY')
            raw = json.loads(raw_path.read_text())['value']
            measure_output(raw, annotate(call['request']), product.route.limits, product.route.encode, expanded=True)
        valid, invalid = split_result(product, qid, result, ids, call['request'], raw)
        if raw is None and result.get('status') == 'FAILED':
            from .review_receipts import invalid_wire_reviews
            from .capacity_policy import annotate
            prepared_call = product.prepare_calls([call])[0]
            invalid = invalid_wire_reviews(product, key, result, ids,
                annotate(prepared_call['request']), prepared_call['schema'])
        for identity in ids:
            if identity in valid:
                row = valid[identity]
                reviews.append({'status': 'VALIDATED', 'value': {**deepcopy(row['decision']), 'considered': [identity]},
                    'group_evidence': {'key': key, 'member_id': identity, 'analysis_id': row['analysis_id'],
                        'result_hash': digest(result)}, 'retained_group_result': deepcopy(result) if raw else None})
            elif identity in invalid:
                request = deepcopy(call['request'])
                request['required_considered'] = [identity]
                schema = group_review.schema([identity], legal_indexes=product.route.envelope.get('legal_indexes', []),
                    repair_profile=PROFILE)
                request['payload']['invalid_review_repair'] = {
                    'original_request_hash': digest(call['request']), 'original_result_hash': digest(result),
                    **repair_diagnostic(invalid[identity], product=product, key=key, identity=identity), 'maximum_attempts': 1,
                    'instruction': 'Repair the invalid review of this exact assignment. Reassess against the '
                        'same answer and sources. Do not relabel a verdict merely to pass validation. '
                        'REJECT needs a supported adverse issue; absent external authority/client facts '
                        'cannot carry retained-source identifiers. Preserve necessary uncertainty.'}
                repairs.append({'key': prefix+'repair-review-'+qid+'-'+digest(identity)[:24],
                    'request': request, 'schema': schema,
                    'validate': lambda value, identity=identity, records=request['records']:
                        group_review.validate(product, qid, value, [identity], records)})
            else:
                reviews.append({**deepcopy(result), 'assigned_ids': [identity]})
    repaired = execute(product, prefix+'invalid-reviews-'+qid, repairs,
        implementation_identity=implementation_identity, admit=admit, refresh=refresh) if repairs else None
    outcomes = {r['key']: r['result'] for r in repaired['results']} if repaired else {}
    for call in repairs:
        identity = call['request']['required_considered'][0]
        outcome = outcomes.get(call['key'], repaired.get('resource_refusal', {
            'status': 'FAILED', 'error': 'E_DEPENDENCY', 'reason': 'No completed invalid-review repair'}))
        if outcome['status'] == 'VALIDATED':
            row = group_review.validate(product, qid, outcome['value'], [identity], call['request']['records'])[identity]
            reviews.append({'status': 'VALIDATED', 'value': {**row['decision'], 'considered': [identity]},
                'repair_evidence': {'key': call['key'], 'result_hash': digest(outcome), 'maximum_attempts': 1}})
        else:
            reviews.append({**deepcopy(outcome), 'assigned_ids': [identity], 'invalid_review_repair_exhausted': True})
    reviews += [{'status': 'FAILED', 'error': 'E_RESOURCE_LIMIT',
        'reason': 'Complete individual review cannot fit', 'assigned_ids': [r['id']]} for r in blocked]
    order = {r['id']: i for i, r in enumerate(items)}
    def assigned(row):
        return row['value']['considered'] if row['status'] == 'VALIDATED' else row['assigned_ids']
    reviews.sort(key=lambda r: order[assigned(r)[0]])
    observed = [identity for r in reviews for identity in assigned(r)]
    require(len(observed) == len(set(observed)) and set(observed) == set(order), 'Lost mandatory review member')
    save_exact(product.directory/(prefix+'contextual-group-review-'+qid+'.json'),
        {'reviews': reviews, 'phase': phase, 'repair_phase': repaired, 'assigned_ids': list(order),
         'scope': 'Every individual assignment retained; malformed output has one explicit repair.'})
    return reviews


def retained_groups(product, qid, question, answer, dependencies, *, prefix=''):
    """Reuse only exact original groups with unchanged full answer and context.

    Input/output envelopes and the stricter validation may change; no source,
    assignment, legal instruction or answer may change. Invalid siblings are
    returned to the single-repair path, never silently accepted.
    """
    if product.capacity_checkpoint is None:
        return [], {}
    from ..integration_contract import read_evidence
    from . import group_review, downstream_instructions, capacity_policy
    from .source_review import assignments
    from .context_table import expand
    checkpoint = read_evidence(product.capacity_checkpoint, product.root)
    require(checkpoint['input_hash'] == product.route.input_hash, 'Foreign retained reviews', 'E_INTEGRITY')
    table = {r['id']: r for r in assignments(product, qid, dependencies)}
    calls, results, used = [], {}, set()
    for key, row in checkpoint.get('review_groups', {}).items():
        if not key.startswith(prefix+'audit-group-'+qid+'-'):
            continue
        request = read_evidence(row['request'], product.root)
        schema = read_evidence(row['schema'], product.root)
        result = read_evidence(row['result'], product.root)
        ids = request['required_considered']
        if request['payload']['answer'] != answer or not set(ids) <= set(table) or set(ids) & used:
            continue
        rows = expand(request['payload'])
        require(rows == [table[i] for i in ids], 'Retained assignment content changed', 'E_INTEGRITY')
        rebuilt, current_schema = group_review.build(product, qid, question, answer, rows)
        selected = product.review_repair_profile
        try:
            product.review_repair_profile = None
            legacy, legacy_schema = group_review.build(product, qid, question, answer, rows)
        finally:
            product.review_repair_profile = selected
        if product.downstream_instruction_profile is not None:
            rebuilt = downstream_instructions.annotate(rebuilt)
            legacy = downstream_instructions.annotate(legacy)
        require(capacity_policy.annotate(legacy) == capacity_policy.annotate(request),
            'Retained review changed substantive request', 'E_INTEGRITY')
        require(schema == legacy_schema,
            'Unreviewed retained review schema', 'E_INTEGRITY')
        if row.get('dispatch'):
            journal = read_evidence(row['dispatch'], product.root)
            require(journal['input_hash'] == product.route.input_hash and journal['calls'][key]['status'] != 'RESERVED'
                and journal['calls'][key]['result_hash'] == digest(result), 'Unsettled retained review', 'E_INTEGRITY')
        raw = read_evidence(row['raw'], product.root)['value'] if row.get('raw') else None
        require(result['status'] == 'VALIDATED' or raw is not None, 'Retained review has no output')
        calls.append(dict(key=key, request=rebuilt, schema=current_schema, retained_raw=raw))
        results[key] = deepcopy(result)
        used.update(ids)
    return calls, results


def warrant_schema():
    result = deepcopy(WARRANT)
    row = result['properties']['decisions']['items']
    row['properties']['blocking_source_gaps'] = deepcopy(result['properties']['source_gaps'])
    row['required'].append('blocking_source_gaps')
    return result


def review_warrants(product, qid, question, answer, reviews, details):
    assessed, warranted = [], []
    for i, review in enumerate(reviews):
        if review.get('status') != 'VALIDATED' or review['value']['verdict'] != 'REJECT':
            continue
        value = review['value']
        issues = [{'id': f'issue-{j}', 'text': text} for j, text in enumerate(value['issues'])]
        payload = {'answer': answer['value'], 'review': value, 'issues': issues,
            'requirement_accounts': [r for r in details if r['id'] in value['considered']],
            'assignment': 'Assess each adverse issue independently against the supplied sources and question_scope. '
                'WARRANTED means a supported defect; UNWARRANTED means the objection does not follow; '
                'UNRESOLVED means the evidence cannot decide. Record only missing sources necessary to decide '
                'this particular issue in its blocking_source_gaps. Any such gap requires UNRESOLVED. '
                'Keep unrelated missing authority in the overall source_gaps without using it to stop '
                'independent supported corrections. A quotation alone does not prove the inference.'}
        request = product.request('ASSESS_REVIEW_WARRANT', question, product.source_records(payload),
            payload=payload, expected=[f'review-{i}'])
        def check(result, issues=issues, i=i, records=request['records']):
            rows = result['decisions']
            require(result['considered'] == [f'review-{i}'] and len(rows) == len(issues)
                and {r['issue_id'] for r in rows} == {r['id'] for r in issues}, 'Incomplete review-warrant decisions')
            product.citations(result, records)
            for row in rows:
                # Issue-specific gaps have the same locator and delivery
                # contract as overall gaps. They are evaluated separately so
                # an unrelated overall gap does not veto an independent issue.
                product.citations({'source_gaps': row['blocking_source_gaps']}, records)
                require(not row['blocking_source_gaps'] or row['disposition'] == 'UNRESOLVED',
                    'Issue with necessary missing evidence cannot be settled')
                require(row['disposition'] != 'WARRANTED' or row['support'], 'Unsupported correction warrant')
                require(row['disposition'] != 'UNWARRANTED' or row['support'] or row['basis'] == 'QUESTION_SCOPE',
                    'Discarded criticism lacks source or question-scope reasoning')
        try:
            result = product.dispatch.call(f'warrant-{qid}-{i}', request, warrant_schema(), check)
        except Exception as exc:
            result = product.failure(exc)
        assessed.append({'review_index': i, 'original_review_hash': digest(review), 'result': result})
        if result['status'] == 'VALIDATED':
            ids = {r['issue_id'] for r in result['value']['decisions'] if r['disposition'] == 'WARRANTED'}
            if ids:
                warranted.append({**deepcopy(value), 'issues': [r['text'] for r in issues if r['id'] in ids]})
    save(product.directory/f'correction-{qid}-warrants.json', assessed)
    settled = bool(assessed) and all(r['result']['status'] == 'VALIDATED' and all(
        d['disposition'] != 'UNRESOLVED' for d in r['result']['value']['decisions']) for r in assessed)
    return assessed, warranted, settled


def correct_answer(product, *args):
    from ..bounded_product import BoundedProduct
    return BoundedProduct.correct_answer(product, *args)
