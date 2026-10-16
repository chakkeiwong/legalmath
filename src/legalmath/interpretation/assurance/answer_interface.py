"""Make supplied answer identities explicit in the provider's output schema.

These constraints prevent metadata drift; they do not decide legal meaning.
The caller must still validate identity pairs, quotations and source reasoning.
"""
from copy import deepcopy


ANSWER_INSTRUCTIONS = (
    "Output contract: premise_account has exactly one row per supplied case. "
    "Copy cases[].facts byte-for-byte into stated_facts; do not paraphrase, add "
    "explanations or move facts between case IDs. Put qualifications only in "
    "additional_assumptions and case reasoning. Cases are independent: do not "
    "import a named holder or other facts from one case into another. obligation_account has exactly "
    "one row per supplied acceptance obligation. Its answer_quote must be a "
    "nonempty contiguous quote from answers[].answer or from a case_assessments "
    "conclusion/reasons field, never from grounds, limitations or metadata. "
    "tool_account has exactly one row for each external_tool_context.checks[].key "
    "and no other key. If there are no such checks, return tool_account: []. "
    "Executor review, reader status and formalization_count are not tool checks. "
    "These formatting constraints do not establish source warrant."
)


def answer_schema(base, request):
    """Narrow actual IDs and values, leaving semantic review independent."""
    result = deepcopy(base)
    properties = result['properties']
    cases = request['cases']
    premises = properties['premise_account']
    premises['minItems'] = premises['maxItems'] = len(cases)
    fields = premises['items']['properties']
    fields['case_id'] = {**fields['case_id'], 'enum': [c['case_id'] for c in cases]}
    fields['stated_facts'] = {**fields['stated_facts'],
        'enum': [c['facts'] for c in cases],
        'description': 'Exact input facts for this case_id, copied without alteration.'}
    obligations = properties['obligation_account']
    obligations['minItems'] = obligations['maxItems'] = len(request['acceptance_obligations'])
    obligation_fields = obligations['items']['properties']
    obligation_fields['obligation_id'] = {**obligation_fields['obligation_id'],
        'enum': [row['id'] for row in request['acceptance_obligations']]}
    obligation_fields['answer_quote'] = {**obligation_fields['answer_quote'],
        'description': 'Exact contiguous nonempty substring of main answer or case conclusion/reasons; not grounds or metadata.'}
    checks = request.get('external_tool_context', {}).get('checks', [])
    account = properties['tool_account']
    account['minItems'] = account['maxItems'] = len(checks)
    if checks:
        field = account['items']['properties']['check_key']
        account['items']['properties']['check_key'] = {**field, 'enum': [c['key'] for c in checks]}
    account['description'] = 'Only delivered external_tool_context.checks; empty when no checks are supplied.'
    return result
