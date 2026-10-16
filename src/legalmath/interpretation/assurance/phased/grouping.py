"""Staged transport candidate; not imported by the running product.

Each dependency remains a distinct obligation to review. Grouping does not
deduplicate meanings, change question ownership or decide legal relevance.
"""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.bounded_product import obj, array, TEXT, QUOTE, SOURCE_GAP, ASSERTION


def decision_schema(ids):
    require(ids and len(ids) == len(set(ids)), 'Empty or duplicate dependency assignment')
    # Each keyed property is mandatory. Using an object prevents omissions or
    # duplicate IDs being disguised by a successful aggregate verdict.
    decision = obj({
        'verdict': {'type': 'string', 'enum': ['ACCEPT', 'REJECT', 'UNRESOLVED']},
        'reason': TEXT, 'support': array(QUOTE), 'issues': array(TEXT),
        'source_gaps': array(SOURCE_GAP), 'assertion_bindings': array(ASSERTION)})
    return obj({'decisions': obj({identity: deepcopy(decision) for identity in ids})})


def validate_decisions(product, value, ids, records):
    from jsonschema import validate
    validate(value, decision_schema(ids))
    require(set(value['decisions']) == set(ids), 'Incomplete dependency decisions')
    for identity in ids:
        decision = value['decisions'][identity]
        product.citations(decision, records)
        require(decision['verdict'] != 'ACCEPT' or (decision['support'] and
            not decision['issues'] and not decision['source_gaps']),
            'Accepted dependency has no support or retains defects')
    return deepcopy(value['decisions'])


def pack_items(items, measure, *, maximum_items):
    """Greedy grouping, failing closed if even one original item cannot fit.

    measure receives complete members and must check input and output bounds.
    It returns None for a resource refusal and a receipt for a fitting group.
    Exceptions other than an explicit resource refusal propagate.
    """
    require(type(maximum_items) is int and maximum_items > 0, 'Invalid item bound')
    identities = [item['id'] for item in items]
    require(len(identities) == len(set(identities)), 'Duplicate input identity')
    groups, blocked, batch, receipt = [], [], [], None
    for item in items:
        proposed = batch + [item]
        measured = measure(proposed) if len(proposed) <= maximum_items else None
        if measured is not None:
            batch, receipt = proposed, measured
            continue
        if batch:
            groups.append({'members': deepcopy(batch), 'measurement': receipt})
        batch, receipt = [], None
        measured = measure([item])
        if measured is None:
            blocked.append(deepcopy(item))
        else:
            batch, receipt = [item], measured
    if batch:
        groups.append({'members': deepcopy(batch), 'measurement': receipt})
    actual = [item for group in groups for item in group['members']] + blocked
    require(len(actual) == len(items) and {r['id']: digest(r) for r in actual} ==
        {r['id']: digest(r) for r in items}, 'Packing changed or lost an item')
    return groups, blocked
