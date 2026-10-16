"""Explicit exact transport and finite input bound for post-account consumers.

Only transport is lossless. Syntheses remain proposals checked against retained
original accounts and sources. The ordinary product limits are unchanged.
"""
from copy import deepcopy
from ..bounded_context import require
from . import account_input, account_encoding

PROFILE = 'exact-downstream-input-32k.v1'
INPUT_TOKENS = 32768
TASKS = frozenset({
    'SYNTHESIZE_FINDINGS', 'ANSWER_ORIGINAL_QUESTION',
    'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', 'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT',
    'AUDIT_ANSWER_AND_DETAILED_ACCOUNT', 'AUDIT_ANSWER_AGAINST_SOURCE',
    'AUDIT_WITHIN_QUESTION_DEPENDENCY', 'REVIEW_CROSS_QUESTION_DEPENDENCIES',
    'ASSESS_MATCHED_TOOL_EFFECT', 'CORRECT_REVIEWED_ANSWER',
    'ASSESS_REVIEW_WARRANT', 'CORRECT_REVIEWED_REQUIREMENT',
})


def validate(request):
    require(request.get('downstream_input_profile') == PROFILE
        and request.get('task') in TASKS
        and not any(k in request for k in ('account_contract', 'account_input_profile',
            'account_capacity_profile', 'account_output_profile')),
        'Downstream input profile outside its declared contract', 'E_AUTHORITY')


def apply(prepared):
    if prepared['original_request'].get('downstream_input_profile') is None:
        return prepared
    validate(prepared['original_request'])
    result = deepcopy(prepared)
    result['request'] = account_input.pack(prepared['request'])
    # Metadata observations keep their original shape. Source-only requests can
    # additionally use the exact record table and integer quotation selectors.
    records = result['request'].get('records', [])
    if all(r.get('kind') == 'source' for r in records):
        # Canonical JSON reload sorts object keys. Keep the established live
        # table-column order so retained downstream wire contracts stay exact.
        # Record order and every value are unchanged; ordinary accounts bypass
        # this optional profile. Unknown fields remain present.
        for i, record in enumerate(records):
            first = {k: record[k] for k in ('id', 'start', 'end', 'text') if k in record}
            records[i] = first | {k: record[k] for k in sorted(record) if k not in first}
        packed = account_encoding.pack({'request': result['request'], 'response_schema': result['schema']})
        result['request'], result['schema'] = packed['request'], packed['response_schema']
    return result


def input_token_limit(request, limits):
    validate(request)
    require(limits.input_tokens == 12000, 'Downstream capacity has a different baseline', 'E_AUTHORITY')
    return INPUT_TOKENS
