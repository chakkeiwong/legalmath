"""Opt-in, explicit correspondence between review targets and schema keys.

Keep original response keys and the strict decoder. Full batch context remains
available to an individual repair, but only the named targets require decisions.
"""
from copy import deepcopy
from ..bounded_context import require

PROFILE = 'explicit-review-assignment-contract.v1'
TASK = 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS'
FIELD = 'review_assignment_profile'


def apply(prepared):
    original = prepared['original_request']
    if original.get(FIELD) is None:
        return prepared
    require(original[FIELD] == PROFILE and original.get('task') == TASK,
        'Unknown review assignment contract', 'E_AUTHORITY')
    result = deepcopy(prepared)
    wire = result['request']
    target_ids = original['required_considered']
    assignments = result['schema']['properties']['assignments']
    require(len(target_ids) == len(set(target_ids)) and target_ids and
        set(target_ids) == set(assignments['properties']) == set(assignments['required']) and
        assignments.get('additionalProperties') is False,
        'Response assignment population differs from requested targets', 'E_INTEGRITY')
    reverse = {identity: alias for alias, identity in prepared['aliases'].items()}
    rows = wire['payload']['assignments']
    row_ids = [row['id'] for row in rows]
    require(len(row_ids) == len(set(row_ids)) and
        wire['required_considered'] == [reverse[i] for i in target_ids] and
        set(wire['required_considered']) <= set(row_ids),
        'Requested assignment has no unique delivered context', 'E_INTEGRITY')
    wire['response_assignment_targets'] = [
        {'response_key': identity, 'assignment_id': reverse[identity]} for identity in target_ids]
    guidance = (
        'Review exactly the targets in response_assignment_targets. Each response_key is an '
        'exact key in the response assignments object; its assignment_id identifies the '
        'corresponding payload.assignments item. Do not infer correspondence from ordering '
        'or put short assignment_id values in response object keys. Other payload assignments '
        'and origin readings are jointly delivered context, not additional review targets. '
        'Return analyses and assignments only. Each analyses entry has analysis_id and decision. '
        'Inside decision, put verdict, issues and support inside review; put reason, source_gaps, '
        'assertion_bindings and context_needs alongside review as specified by the final schema. '
        'Every target must reference an existing analysis_id, and every analysis must be used '
        'by at least one target. Share a rationale only when its full reasoning applies to each '
        'assigned target. Never add an unassigned rationale. Source selectors establish exact '
        'text identity, not legal support. Preserve supported adverse issues and uncertainty; '
        'do not change a verdict to satisfy the schema. Assertion paths are relative to the '
        'expanded individual decision: /reason or /issues/0, never /analyses/0/decision/reason '
        'or /review/issues/0. Every numbered proposition still needs its exact document and '
        'proposition binding. Follow the citation and prose rules in the response guidance. ')
    assignment = wire['payload']['assignment']
    lead = 'Individually review every source/dependency assignment against this answer. '
    require(assignment.startswith(lead), 'Unreviewed assignment instruction', 'E_INTEGRITY')
    wire['payload']['assignment'] = guidance + assignment[len(lead):]
    wire['response_reference_instructions'] += ' ' + guidance
    return result
