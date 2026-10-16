"""Reuse an explicitly shared, identical returned criticism with exact membership."""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require


def group(reviews):
    buckets = {}
    for index, review in enumerate(reviews):
        if review.get('status') != 'VALIDATED' or review['value']['verdict'] != 'REJECT':
            continue
        decision = deepcopy(review['value'])
        ids = decision.pop('considered')
        require(ids and len(ids) == len(set(ids)), 'Invalid original criticism assignments')
        evidence = review.get('group_evidence', {})
        shared = all(evidence.get(k) for k in ('key', 'result_hash', 'analysis_id'))
        identity = digest({k: evidence[k] for k in ('key', 'result_hash', 'analysis_id')}) if shared else str(index)
        if identity not in buckets:
            buckets[identity] = {'decision': decision, 'considered': [], 'originals': [],
                'shared_rationale': deepcopy(evidence) if shared else None}
        bucket = buckets[identity]
        require(bucket['decision'] == decision, 'Shared rationale has conflicting original decisions')
        require(not set(ids) & set(bucket['considered']), 'Repeated original criticism assignment')
        bucket['considered'].extend(ids)
        bucket['originals'].append({'index': index, 'sha256': digest(review), 'considered': ids})
    result = []
    for identity, bucket in buckets.items():
        result.append({'id': 'criticism-' + digest(identity)[:24],
            'review': {'status': 'VALIDATED',
                       'value': {**bucket['decision'], 'considered': bucket['considered']}},
            'originals': bucket['originals'], 'shared_rationale': bucket['shared_rationale']})
    expected = {i for i, r in enumerate(reviews)
                if r.get('status') == 'VALIDATED' and r['value']['verdict'] == 'REJECT'}
    actual = [r['index'] for b in result for r in b['originals']]
    require(len(actual) == len(set(actual)) and set(actual) == expected, 'Lost adverse review')
    return result

