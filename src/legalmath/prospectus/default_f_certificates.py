"""Optional verification of the actual conditional BASF consumer.

The formulas below are a separate encoding of the disclosed hypotheses. Their
agreement with a source interpretation is not established by computation.
"""
from .reasoning_certificates import certify, verify, identity

VERSION = 'default-f-reasoning-certificate.v1'


def model(reading, question):
    """Independent temporal and causal specification; no production builder."""
    namespace = 'receipt' if question in {'event_at_receipt', 'bc_quorum_condition_at_receipt'} else 'exercise'

    def fact(name):
        return namespace + '.' + name

    joint = {'all': [fact('cessation'), fact('disposal'), fact('value_joint'), fact('risk_joint')]}
    cessation = {'all': [fact('cessation'), fact('value_cessation'), fact('risk_cessation')]}
    disposal = {'all': [fact('disposal'), fact('value_disposal'), fact('risk_disposal')]}
    events = {'both_conducts': joint, 'either_qualified_conduct': {'any': [cessation, disposal]},
              'cessation_or_qualified_disposal': {'any': [fact('cessation'), disposal]}}
    if reading not in events:
        raise ValueError('Unsupported interpretation candidate')
    event = events[reading]
    if question in {'event_at_exercise', 'event_at_receipt'}:
        return event
    if question == 'modeled_f_exercise':
        return {'all': [event, 'notice', {'not': 'cured_before_exercise'}]}
    if question == 'bc_quorum_condition_at_receipt':
        return {'any': ['quorum_at_receipt', 'other_eligible_at_receipt',
                        {'all': [event, 'f_other_eligibility_at_receipt']}]}
    raise ValueError('Unsupported conditional question')


READINGS = ('both_conducts', 'either_qualified_conduct', 'cessation_or_qualified_disposal')
QUESTIONS = ('event_at_exercise', 'event_at_receipt', 'modeled_f_exercise', 'bc_quorum_condition_at_receipt')


def context(consumer, profile, *, products_sha256, prior_profiles_sha256):
    return {'products_sha256': products_sha256, 'prior_profiles_sha256': prior_profiles_sha256,
            'profile_sha256': identity(profile), 'sources': profile['sources'],
            'complete_consumer_sha256': identity(consumer)}


def certificate(consumer, profile, *, expected_context):
    if (identity(consumer) != expected_context['complete_consumer_sha256']
            or identity(profile) != expected_context['profile_sha256']
            or profile['sources'] != expected_context['sources']):
        raise ValueError('Complete answer, profile or expected source identity changed')
    review = consumer['default_f_review']
    if (review['profile_sha256'] != identity(profile) or review['sources'] != profile['sources']
            or review['candidates'] != profile['candidates'] or review['groups'] != profile['groups']
            or review['premises'] != profile['premises'] or review['selected_reading'] is not None
            or review['governing_language'] != 'German'
            or any(review[k] is not False for k in ('candidate_set_exhaustive', 'source_meaning_promoted',
                                                  'actual_default_established', 'independent_legal_acceptance'))):
        raise ValueError('Source interpretation or factual scope was promoted')
    candidates = review['candidates']
    if (len(candidates) != len(READINGS) or [c['id'] for c in candidates] != list(READINGS)
            or any(c['expressions'] != {q: model(c['id'], q) for q in QUESTIONS} for c in candidates)):
        raise ValueError('A disclosed candidate or conditional formula changed')
    if len(review['scenarios']) != len(profile['scenarios']):
        raise ValueError('Scenario coverage changed')
    certificates = []
    for source, row in zip(profile['scenarios'], review['scenarios'], strict=True):
        if (any(row[k] != source[k] for k in ('id', 'kind', 'facts'))
                or row['selected_reading'] is not None or row['actual_event_established'] is not False
                or set(row['readings']) != set(READINGS)):
            raise ValueError('Conditional scenario or reading coverage changed')
        for reading in READINGS:
            if set(row['readings'][reading]) != set(QUESTIONS):
                raise ValueError('Conditional question coverage changed')
            for question in QUESTIONS:
                bound = {**expected_context, 'scenario': row['id'], 'reading': reading, 'question': question}
                certificates.append({'scenario': row['id'], 'reading': reading, 'question': question,
                    'certificate': certify(model(reading, question), source['facts'],
                                           row['readings'][reading][question], context=bound)})
        if row['input_conflicts'] != [k for k, v in source['facts'].items() if v == 'conflict']:
            raise ValueError('Input conflicts were lost')
        for question in QUESTIONS:
            values = {row['readings'][r][question]['status'] for r in READINGS}
            expected = ('CONFLICT_IN_ENUMERATED_READINGS' if 'CONFLICT' in values else
                        'ALL_ENUMERATED_YES' if values == {'YES'} else
                        'ALL_ENUMERATED_NO' if values == {'NO'} else
                        'UNRESOLVED_WITHIN_ENUMERATED_READINGS' if 'UNKNOWN' in values else
                        'DIFFERENT_ENUMERATED_DECISIONS')
            if row['comparison'][question] != expected:
                raise ValueError('Comparison concealed alternative outcomes')
    return {'version': VERSION, 'context_sha256': identity(expected_context),
            'conditional_only': True, 'candidate_set_exhaustive': False,
            'source_meaning_proved': False, 'certificates': certificates}


def verify_consumer(certified, profile, *, expected_context):
    if not isinstance(certified, dict) or 'reasoning_certificate' not in certified:
        raise ValueError('Reasoning certificate required')
    original = {k: v for k, v in certified.items() if k != 'reasoning_certificate'}
    actual = certified['reasoning_certificate']
    expected = certificate(original, profile, expected_context=expected_context)
    if identity(actual) != identity(expected):
        raise ValueError('Consumer certificate changed or coverage omitted')
    by_id = {r['id']: r for r in original['default_f_review']['scenarios']}
    for entry in actual['certificates']:
        row = by_id[entry['scenario']]
        reading, question = entry['reading'], entry['question']
        verify(entry['certificate'], model(reading, question), row['facts'], row['readings'][reading][question],
               expected_context={**expected_context, 'scenario': row['id'], 'reading': reading, 'question': question})
    return {'status': 'PASS', 'checked_answers': len(actual['certificates']),
            'source_meaning_proved': False, 'candidate_set_exhaustive': False}
