"""Conditional majority arithmetic for the selected BASF source readings.

Eligible totals and legal classifications are explicit hypotheses. No result
attests an actual vote, an applicable historical edition, or effectiveness.
"""
from copy import deepcopy

from .successor.anchors import fields
from .successor.contracts import bound_path, digest
from .successor.predicates import dispatch
from .successor.ratio_facts import number

VERSION = 'basf-schvg-conditional-majority.v1'
KEY = 'schvg_majority_review'
KINDS = ('amendment_agreement', 'qualified_majority', 'simple_majority')
UNIT = 'eligible-participating-voting-weight'
EXPRESSION = {'any': ['qualified75', {'all': [
    {'not': 'essential_change'}, {'not': 'numbered_subject'}, 'simple_majority']}]}


def context(products, ordinary):
    report = products['P3']['payload'].get('statutory_references')
    if report is None or ordinary.get('statutory_references') != report:
        raise ValueError('Majority requires the complete current statutory report')
    rows = [r for r in report['records'] if r['id'] == 'H38']
    if len(rows) != 1 or rows[0]['availability'] != 'RETAINED_PRIMARY_READING':
        raise ValueError('Majority requires retained H38 source evidence')
    from .successor.statutory_references import specification
    registered = next(r for r in specification()['records'] if r['id'] == 'H38')
    if any(rows[0].get(k) != v for k, v in registered.items()):
        raise ValueError('Majority H38 reading differs from registered numbered source')
    governance = [r for r in ordinary.get('basf_governance_terms', []) if r['kind'] in KINDS]
    if [r['kind'] for r in governance] != list(KINDS):
        raise ValueError('Majority requires all three selected governance readings')
    return {'statutory_profile_sha256': report['profile_sha256'],
            'H38': deepcopy(rows[0]), 'selected_governance': deepcopy(governance)}


def validate_scenario(row, instrument_id):
    required = {'id', 'kind', 'subject', 'essential_change', 'eligible_totals',
                'readings_apply', 'totals'}
    fields(row, required, required)
    if (not isinstance(row['id'], str) or not row['id']
            or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT'):
        raise ValueError('Explicit hypothetical scenario identity required')
    subject = row['subject']
    if subject is not None and subject != 'NONE' and not (type(subject) is int and 1 <= subject <= 10):
        raise ValueError('Subject must be numbered1-10, NONE, or unknown')
    for key in ('essential_change', 'eligible_totals', 'readings_apply'):
        value = row[key]
        if value is not None and value != 'conflict' and type(value) is not bool:
            raise ValueError('Classification and applicability must be Boolean, unknown or conflict')
    total = row['totals']
    fields(total, {'instrument_id', 'event_id', 'unit', 'in_favor', 'participating'},
           {'instrument_id', 'event_id', 'unit', 'in_favor', 'participating'})
    if (total['instrument_id'] != instrument_id or total['event_id'] != row['id']
            or total['unit'] != UNIT):
        raise ValueError('Majority total identity or voting-weight unit mismatch')
    values = {k: number(total[k]) if total[k] is not None else None
              for k in ('in_favor', 'participating')}
    if all(v is not None for v in values.values()) and values['in_favor'] > values['participating']:
        raise ValueError('Favorable voting weight exceeds participating voting weight')
    return values


def analyze(row, instrument_id):
    values = validate_scenario(row, instrument_id)
    numerator, denominator = values['in_favor'], values['participating']
    reason, simple, qualified, exact = [], None, None, None
    if numerator is None:
        reason.append('Missing favorable eligible voting weight')
    if denominator is None:
        reason.append('Missing participating eligible voting weight')
    elif denominator == 0:
        reason.append('Zero participating denominator')
    if not reason:
        simple, qualified = 2 * numerator > denominator, 4 * numerator >= 3 * denominator
        exact = {'simple_left': str(2 * numerator), 'simple_right': str(denominator),
                 'qualified_left': str(4 * numerator), 'qualified_right': str(3 * denominator),
                 'method': 'exact rational cross multiplication'}
    subject = row['subject']
    outputs = {}
    for label, end in (('contract', 8), ('statute', 9)):
        within = None if subject is None else type(subject) is int and subject <= end
        observations = {'qualified75': qualified, 'simple_majority': simple,
                        'essential_change': row['essential_change'], 'numbered_subject': within}
        decision = dispatch(EXPRESSION, observations)
        outputs[label] = {**decision, 'premises': observations, 'numbered_range': [1, end]}
    status_to_fact = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}
    prerequisites = {'contract': status_to_fact[outputs['contract']['status']],
                     'statute': status_to_fact[outputs['statute']['status']],
                     'eligible_totals': row['eligible_totals'], 'readings_apply': row['readings_apply']}
    combined = dispatch({'all': list(prerequisites)}, prerequisites)
    return {'scenario': deepcopy(row), 'thresholds': {'simple_majority': simple,
            'qualified75': qualified, 'exact': exact, 'unresolved': reason},
            'contract': outputs['contract'], 'statute': outputs['statute'],
            'combined_necessary_majorities': combined,
            'actual_vote': 'NOT_ESTABLISHED', 'effective_amendment': 'NOT_ESTABLISHED',
            'quorum': 'NOT_EVALUATED', 'procedure_and_implementation': 'NOT_EVALUATED',
            'historical_applicability': 'NOT_ESTABLISHED',
            'meaning': 'Consequences of supplied classifications and eligible totals under the retained readings'}


def _policy(profile, pin, ordinary):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios',
            'actual_event_established', 'historical_application_proved', 'complete_legal_test'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != pin
            or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned majority profile or complete baseline answer changed')
    if any(profile[k] is not False for k in ('actual_event_established', 'historical_application_proved', 'complete_legal_test')):
        raise ValueError('Conditional majority cannot establish an actual or complete legal event')
    scenarios = profile['scenarios']
    if not isinstance(scenarios, list) or not scenarios or len(scenarios) > 128:
        raise ValueError('One to128 bounded hypothetical scenarios required')
    ids = [r.get('id') for r in scenarios if isinstance(r, dict)]
    if len(ids) != len(scenarios) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Distinct hypothetical scenario identities required')
    first = scenarios[0]
    if first['id'] != 'all-open' or any(first[k] is not None for k in ('subject', 'essential_change', 'eligible_totals', 'readings_apply')):
        raise ValueError('Explicit all-open baseline required')
    if first['totals']['in_favor'] is not None or first['totals']['participating'] is not None:
        raise ValueError('All-open baseline cannot supply vote totals')


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    _policy(profile, expected_profile_sha256, ordinary)
    if profile['products_sha256'] != digest(products):
        raise ValueError('Current majority products changed')
    actual_context = context(products, ordinary)
    if profile['context'] != actual_context:
        raise ValueError('Complete majority source context changed')
    for source in actual_context['H38']['legal_sources']:
        raw = bound_path(root, source['text_path']).read_bytes()
        if digest(raw) != source['text_sha256']:
            raise ValueError('Majority primary source edition changed')
        text = raw.decode('utf-8')
        for excerpt in source['excerpts']:
            if text[excerpt['start']:excerpt['end']] != excerpt['quote']:
                raise ValueError('Majority primary source quote changed')
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version': VERSION, 'profile_sha256': digest(profile),
            'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
            'context': actual_context, 'instrument_id': instrument,
            'scenarios': [analyze(s, instrument) for s in profile['scenarios']],
            'classification': 'SUPPLIED_CONDITIONAL_LEGAL_READING',
            'actual_event_established': False, 'historical_application_proved': False,
            'complete_legal_test': False}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            or {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
                != {k: v for k, v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Complete majority answer changed its baseline or digest')
    expected = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY) != expected:
        raise ValueError('Conditional majority result differs from source-bound reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'scenarios': len(expected['scenarios'])}
