"""Exact answer-field references for explicitly targeted issue warrants."""
from copy import deepcopy
from ..bounded_context import require
from .context_references import selections, answer_evidence

PROFILE = 'exact-warrant-answer-fields.v1'
FIELD = 'warrant_reference_profile'

def enabled(request):
    profile = request.get(FIELD)
    if profile is None:
        return False
    require(profile == PROFILE and request.get('task') == 'ASSESS_REVIEW_WARRANT',
        'Warrant reference profile outside its task', 'E_AUTHORITY')
    return True

def apply(prepared):
    request = prepared['original_request']
    if not enabled(request):
        return prepared
    out = deepcopy(prepared)
    row = out['schema']['properties']['decisions']['items']
    require({'answer_evidence','correction_target'} <= set(row['properties']),
        'Exact warrant requires explicit answer targets', 'E_AUTHORITY')
    choices = selections(request)
    row['properties']['answer_evidence'] = {'type':'object', 'additionalProperties':False,
        'properties':{'answer_field':{'type':'string','enum':list(choices)}},
        'required':['answer_field']}
    issues = request['payload']['issues']
    ids = [i['id'] for i in issues]
    require(ids and len(ids) == len(set(ids)), 'Duplicate or empty warrant issues', 'E_INTEGRITY')
    row['properties']['issue_id']['enum'] = ids
    out['schema']['properties']['decisions'].update(minItems=len(ids), maxItems=len(ids))
    variants = []
    for disposition in ('WARRANTED','UNWARRANTED','UNRESOLVED'):
        variant = deepcopy(row)
        fields = variant['properties']
        fields['disposition']['enum'] = [disposition]
        if disposition != 'UNRESOLVED':
            fields['blocking_source_gaps']['maxItems'] = 0
            fields['correction_target']['enum'] = (['ANSWER_DEFECT'] if disposition == 'WARRANTED'
                else ['ANSWER_DEFECT','DEPENDENCY_ONLY'])
        if disposition == 'WARRANTED':
            fields['answer_evidence']['properties']['answer_field']['enum'] = [p for p in choices if p]
            fields['support']['minItems'] = 1
        variants.append(variant)
    out['schema']['properties']['decisions']['items'] = {'anyOf':variants}
    out['request']['warrant_answer_fields'] = [{'answer_field':p, 'quoted_codepoints':len(v['quote'])}
        for p,v in choices.items()]
    out['request']['response_reference_instructions'] += (
        ' For each answer_evidence choose answer_field from warrant_answer_fields. The decoder '
        'copies the entire exact string at that answer-relative pointer. Never retype a quote. '
        'Use the empty field only when no quotation is needed; WARRANTED requires an actual '
        'ANSWER_DEFECT and nonempty exact answer evidence. Each issue_id must occur exactly once. '
        'A selector establishes text identity, not support for the criticism. Preserve unresolved '
        'evidence and all contrary reasoning. Existing source and warrant checks remain binding.')
    return out
