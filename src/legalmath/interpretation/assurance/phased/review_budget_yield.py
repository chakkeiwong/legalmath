"""Yield an exhausted review branch without discarding any obligation."""
from copy import deepcopy

from ..bounded_context import require
from ..integration_contract import read_evidence
from .branch_budget import bucket

PROFILE = 'preserve-review-population-on-branch-exhaustion.v1'
FIELD = 'review_budget_yield_profile'
REASON = 'Phase would spend protected independent-question or service calls'


def enabled(product):
    pointer = getattr(product, 'capacity_checkpoint', None)
    outer = read_evidence(pointer, product.root) if pointer is not None else {}
    selected = outer.get(FIELD)
    runtime = getattr(product, 'review_budget_yield_profile', None)
    require(selected in (None, PROFILE) and runtime in (None, PROFILE),
            'Unknown review budget yield profile', 'E_AUTHORITY')
    return selected == PROFILE or runtime == PROFILE


def exhausted(result, qid):
    if result.get('status') != 'FAILED' or result.get('error') != 'E_RESOURCE_LIMIT':
        return False
    details = result.get('resource_details')
    if not isinstance(details, dict) or details.get('reason') != REASON:
        return False
    if not isinstance(details.get('owner'), str) or bucket(details['owner']) != qid:
        return False
    fields = ['remaining', 'requested', 'protected_other_calls']
    if not all(type(details.get(key)) is int and details[key] >= 0 for key in fields):
        return False
    return details['requested'] >= 1 and details['remaining'] < details['protected_other_calls'] + 1


def deferred(detail_id, refusal):
    return dict(status='FAILED', error='E_RESOURCE_LIMIT',
        reason='Detailed-account review deferred after proved branch-call exhaustion; not attempted.',
        assigned_ids=[detail_id], review_deferred=True, refusal=deepcopy(refusal))
