"""Opt-in exact references for context continuation; no legal verdict changes."""
from copy import deepcopy

from legalmath.canonical import digest
from ..bounded_context import require

PROFILE = 'exact-context-answer-and-needs.v1'
FIELD = 'context_reference_profile'


def enabled(request):
    profile = request.get(FIELD)
    if profile is None:
        return False
    require(profile == PROFILE and request.get('task') == 'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT',
        'Unknown context-reference profile or task', 'E_AUTHORITY')
    return True


def selections(request):
    from .context_disposition import answer_paths
    answer = request['payload']['answer']
    result = {'': {'path': '', 'quote': ''}}
    for path in answer_paths(answer):
        node = answer
        for part in path[1:].split('/'):
            key = part.replace('~1', '/').replace('~0', '~')
            node = node[int(key)] if isinstance(node, list) else node[key]
        if node:
            result[path] = {'path': path, 'quote': node}
    return result


def apply(prepared):
    request = prepared['original_request']
    if not enabled(request):
        return prepared
    result = deepcopy(prepared)
    choices = selections(request)
    evidence = result['schema']['properties']['need_dispositions']['items']['properties']['answer_evidence']
    evidence.clear()
    evidence.update(type='object', additionalProperties=False,
        properties={'answer_field': {'type': 'string', 'enum': list(choices)}},
        required=['answer_field'])
    rows = request['payload']['prior_needs']
    require(len(rows) == len({r['need_id'] for r in rows}), 'Duplicate bound need identity')
    # Limit new requests to delivered source identities; outside text can still
    # be requested by query or a verified document locator. Missing facts and
    # external authority never masquerade as retained source identifiers.
    props = result['schema']['properties']
    template = props['context_needs']['items']
    # record_ids (plural) is deliberately not aliased by the existing input
    # encoder. Offer the original IDs that actually appear in prior needs.
    source_ids = [r['id'] for r in request['records'] if r['kind'] == 'source']
    # The decoder also accepts exact aliases. Retain both established forms,
    # but never offer aliases for dependency assignments or non-source rows.
    source_choices = source_ids + [k for k,v in result['aliases'].items() if v in source_ids]
    indexes = [i['index_hash'] for i in request.get('available_source_indexes', [])]
    variants = []
    for kind in ('SOURCE_TEXT', 'CLIENT_FACT', 'EXTERNAL_AUTHORITY'):
        variant = deepcopy(template)
        fields = variant['properties']
        fields['kind']['enum'] = [kind]
        if kind == 'SOURCE_TEXT':
            if source_ids:
                fields['record_ids']['items']['enum'] = source_choices
            else:
                fields['record_ids']['maxItems'] = 0
            if indexes:
                fields['locators']['items']['properties']['index_hash']['enum'] = indexes
            else:
                fields['locators']['maxItems'] = 0
        else:
            fields['record_ids']['maxItems'] = 0
            fields['locators']['maxItems'] = 0
        variants.append(variant)
    props['context_needs']['items'] = {'anyOf': variants}
    failures = request['payload']['source_delivery_failures']
    choices_by_need = []
    for row in rows:
        variant = deepcopy(props['need_dispositions']['items'])
        options = ['STILL_REQUIRED']
        if row['need_id'] not in failures:
            options.append('NOT_REQUIRED_FOR_CONDITIONAL_ANSWER')
            if row['route'] == 'SOURCE_TEXT': options.append('SUPPLIED_SOURCE')
            if row['route'] == 'ASSIGNMENT_MAPPING': options.append('MAPPING_CLARIFIED')
        variant['properties']['need_id']['enum'] = [row['need_id']]
        variant['properties']['disposition']['enum'] = options
        choices_by_need.append(variant)
    require(choices_by_need, 'No bound prior needs')
    props['need_dispositions']['items'] = {'anyOf': choices_by_need}
    result['context_reference_binding'] = digest({
        'request_binding': prepared['binding'], 'answer': request['payload']['answer'], 'needs': rows})
    result['request']['response_answer_fields'] = [
        {'answer_field': path, 'answer_relative_pointer': path,
         'quoted_codepoints': len(value['quote'])} for path, value in choices.items()]
    guidance = (
        'For answer_evidence choose answer_field from response_answer_fields. It selects the '
        'entire exact string at that answer-relative JSON Pointer, before input compaction. '
        'Use the empty selection when no quotation is needed. Do not invent or retype quotes. '
        'The exact answer is already supplied; selection establishes identity, not legal support. '
        'Account for each original need_id exactly once in need_dispositions. A STILL_REQUIRED '
        'typed original need is preserved verbatim by the decoder, including its reason, query '
        'and sources. context_needs contains only additional genuinely new needs, never a '
        'paraphrase of a retained need. No original need is merged by shared source or wording. '
        'Decoded context_needs lists retained original needs in original order, then new needs. '
        'For new SOURCE_TEXT needs choose only offered source IDs and document hashes. '
        'Use a precise query for other text; never use a dependency ID as a source record. '
        'CLIENT_FACT and EXTERNAL_AUTHORITY need empty record_ids and locators. '
        'Assertion paths address that expanded response. Failed delivery remains STILL_REQUIRED; '
        'missing facts or authority are not supplied by a source selector. Existing citation, '
        'verdict and conditional-waiver checks remain mandatory. '
    )
    result['request']['response_reference_instructions'] += ' ' + guidance
    result['request']['context_reference_instructions'] = guidance
    return result


def answer_evidence(node, request):
    choices = selections(request)
    require(set(node) == {'answer_field'} and node['answer_field'] in choices,
        'Unknown bound answer field')
    return deepcopy(choices[node['answer_field']])


def restore_needs(value, request):
    result = deepcopy(value)
    rows = request['payload']['prior_needs']
    dispositions = result['need_dispositions']
    require(len(dispositions) == len(rows) and
        {d['need_id'] for d in dispositions} == {r['need_id'] for r in rows},
        'Missing or duplicate prior-need dispositions')
    by_id = {d['need_id']: d for d in dispositions}
    preserved = [deepcopy(r['original_need']) for r in rows
        if by_id[r['need_id']]['disposition'] == 'STILL_REQUIRED'
        and r['route'] != 'REVIEW_QUESTION']
    result['context_needs'] = preserved + result['context_needs']
    return result
