"""Separate Boolean enumeration for the explicit holder-authority answer.

This checker does not use the candidate predicate tree or predicate evaluator.
Shared metadata validation establishes provenance, not the consequence proof.
"""
from itertools import product

EVENT_NAMES = {
    'both_conducts': ('cessation', 'disposal', 'value_joint', 'risk_joint'),
    'either_qualified_conduct': ('cessation', 'value_cessation', 'risk_cessation',
                               'disposal', 'value_disposal', 'risk_disposal'),
    'cessation_or_qualified_disposal': ('cessation', 'disposal', 'value_disposal', 'risk_disposal'),
}
AUTHORITY_NAMES = ('holder', 'notice_form_delivery', 'cured', 'entrusted', 'express_permission')


def consequence(reading, facts):
    required = sorted(EVENT_NAMES[reading] + AUTHORITY_NAMES)
    missing = [k for k in required if facts.get(k) is None]
    conflicts = [k for k in required if facts.get(k) == 'conflict']
    outcomes = set()
    if not conflicts:
        for values in product((False, True), repeat=len(missing)):
            w = {**facts, **dict(zip(missing, values))}
            if reading == 'both_conducts':
                event = w['cessation'] and w['disposal'] and w['value_joint'] and w['risk_joint']
            elif reading == 'either_qualified_conduct':
                event = ((w['cessation'] and w['value_cessation'] and w['risk_cessation'])
                         or (w['disposal'] and w['value_disposal'] and w['risk_disposal']))
            else:
                event = w['cessation'] or (w['disposal'] and w['value_disposal'] and w['risk_disposal'])
            outcomes.add(bool(event and w['holder'] and w['notice_form_delivery'] and not w['cured']
                              and (not w['entrusted'] or w['express_permission'])))
    status = 'CONFLICT' if conflicts else 'YES' if outcomes == {True} else 'NO' if outcomes == {False} else 'UNKNOWN'
    return {'status': status, 'missing': missing, 'conflicts': conflicts}


def comparison(values):
    values = set(values)
    if 'CONFLICT' in values:
        return 'CONFLICT_IN_ENUMERATED_READINGS'
    if values == {'YES'}:
        return 'ALL_ENUMERATED_YES'
    if values == {'NO'}:
        return 'ALL_ENUMERATED_NO'
    if 'UNKNOWN' in values:
        return 'UNRESOLVED_WITHIN_ENUMERATED_READINGS'
    return 'DIFFERENT_ENUMERATED_DECISIONS'


def verify_answer(answer, ordinary, profile, *, expected_profile_sha256):
    from .contracts import digest
    from .default_holder import KEY, metadata, policy
    policy(ordinary, profile, expected_profile_sha256)
    body = {k: v for k, v in answer.items() if k != 'report_sha256'}
    previous = {k: v for k, v in body.items() if k != KEY}
    if (answer.get('report_sha256') != digest(body)
            or digest(previous) != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Complete ordinary answer was not preserved')
    review = answer.get(KEY, {})
    if digest({k: v for k, v in review.items() if k != 'scenarios'}) != digest(metadata(profile)):
        raise ValueError('Holder explanation, source or scope changed')
    expected = []
    for case in profile['scenarios']:
        decisions = {r: consequence(r, case['facts']) for r in EVENT_NAMES}
        expected.append({**case, 'readings': decisions,
                         'comparison': comparison(d['status'] for d in decisions.values())})
    if digest(review.get('scenarios')) != digest(expected):
        raise ValueError('Holder consequences or complete scenario coverage changed')
    return {'status': 'PASS', 'checked_decisions': 3 * len(expected),
            'complete_ordinary_preserved': True, 'interpretation_proved': False}
