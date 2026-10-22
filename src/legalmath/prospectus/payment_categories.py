"""Conditional unquoted payment inclusions, composed with the existing clock."""
from copy import deepcopy
from . import payment_deadline
from .causal_rating import boolean
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch

VERSION = 'basf-payment-category-review.v1'
KEY = 'payment_category_review'
PRINCIPAL_COMPONENTS = ('redemption_amount', 'early_redemption_amount',
    'call_redemption_amount', 'premium', 'other_amount_payable_in_respect_notes')
ADDITIONAL = 'section7_additional_amount'
CONDITIONS = ('classification_supported', 'terms_reference_applies', 'where_applicable')
TAX_POSITIVE = ('source_application_supported', 'specified_german_tax',
               'legally_required_withholding', 'additional_net_preservation_needed')
TAX_EXCLUSIONS = ('exception_a', 'exception_b', 'exception_c', 'exception_d',
                  'exception_e', 'flat_tax_or_solidarity')
VALUE = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}


def context(products):
    from .successor.basf_payment_terms import explain
    clauses = explain(products['P3']['payload']['clauses'],
                      products['P1']['payload']['graph'], products['P2']['payload']['assembly'])
    required = {'principal_definition', 'interest_definition', 'tax_withholding',
                'gross_up', 'german_flat_tax'}
    selected = [r for r in clauses if r['kind'] in required]
    if len(selected) != len(required) or {r['kind'] for r in selected} != required:
        raise ValueError('Complete principal, interest and section7 source context required')
    by_kind = {r['kind']: r for r in selected}
    if ('soweit anwendbar' not in ' '.join(by_kind['principal_definition']['quote'].split())
            or '§ 7' not in by_kind['interest_definition']['quote']
            or not all('(' + letter + ')' in by_kind['gross_up']['quote'] for letter in 'abcde')
            or 'Solidaritätszuschlag' not in by_kind['german_flat_tax']['quote']):
        raise ValueError('Source applicability or tax exclusions missing')
    return {'contract_readings': selected, 'payment_defaults': payment_deadline.context(products),
        'original_definition_records': ['U02-capital', 'U03-interest'],
        'interpretation': 'EXPRESS_SUFFICIENT_INCLUSION_ROUTES',
        'other_qualifying_routes': 'OPEN_UNLESS_SEPARATELY_STIPULATED',
        'historical_law_application': 'NOT_ESTABLISHED',
        'domain': 'One identified hypothetical payment; section7 evaluates one identified tax or charge',
        'overlap': 'Boolean qualification only; principal and interest inclusions are not disjoint amounts'}


def section7(tax):
    fields(tax, (*TAX_POSITIVE, *TAX_EXCLUSIONS), (*TAX_POSITIVE, *TAX_EXCLUSIONS))
    for value in tax.values():
        boolean(value)
    return dispatch({'all': [*TAX_POSITIVE, {'not': {'any': list(TAX_EXCLUSIONS)}}]}, tax)


def qualification(row):
    component = row['component']
    if not isinstance(component, str) or component not in (*PRINCIPAL_COMPONENTS, ADDITIONAL):
        raise ValueError('Explicit supported source inclusion required')
    conditions = row['conditions']
    fields(conditions, CONDITIONS, CONDITIONS)
    for value in (*conditions.values(), row['other_qualifying_note_payment']):
        boolean(value)
    tax = None
    if component == ADDITIONAL:
        if row['component_payable'] is not None:
            raise ValueError('Section7 payment cannot override its derived payable condition')
        tax = section7(row['tax'])
        payable = VALUE[tax['status']]
    else:
        if row['tax'] is not None:
            raise ValueError('Principal inclusion cannot carry section7 tax premises')
        boolean(row['component_payable'])
        payable = row['component_payable']
    inclusion = dispatch({'all': [*CONDITIONS, 'included_component_payable']},
        {**conditions, 'included_component_payable': payable})
    # These are separate primitive groups. No constraint or reused primitive is
    # discarded by composing their possible values (see the retained proof).
    qualified = dispatch({'any': ['express_inclusion', 'other_qualifying_note_payment']},
        {'express_inclusion': VALUE[inclusion['status']],
         'other_qualifying_note_payment': row['other_qualifying_note_payment']})
    return tax, inclusion, qualified


def analyze(row, source, instrument):
    keys = {'id', 'kind', 'identity', 'component', 'conditions', 'component_payable',
            'tax', 'other_qualifying_note_payment', 'payment'}
    fields(row, keys, keys)
    if not isinstance(row['id'], str) or not row['id'] or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical payment-category case required')
    identity = row['identity']
    fields(identity, {'instrument_id', 'obligation_id', 'tax_id'},
           {'instrument_id', 'obligation_id', 'tax_id'})
    if (identity['instrument_id'] != instrument
            or not isinstance(identity['obligation_id'], str) or not identity['obligation_id'].strip()):
        raise ValueError('Identified payment obligation in the selected instrument required')
    if row['component'] == ADDITIONAL:
        if not isinstance(identity['tax_id'], str) or not identity['tax_id'].strip():
            raise ValueError('One identified tax or charge required for section7')
    elif identity['tax_id'] is not None:
        raise ValueError('Tax identity only belongs to the section7 route')
    payment = row['payment']
    if (not isinstance(payment, dict) or 'qualified_note_payment' in payment
            or payment.get('id') != row['id'] or payment.get('route') != 'a'
            or payment.get('clock', {}).get('event_id') != row['id']):
        raise ValueError('Same-event default(a) payment input without qualification override required')
    tax, inclusion, qualified = qualification(row)
    derived = deepcopy(payment)
    derived['qualified_note_payment'] = VALUE[qualified['status']]
    full = payment_deadline.analyze(derived, source['payment_defaults'], instrument)
    return {'scenario': deepcopy(row), 'section7_route': tax, 'express_inclusion': inclusion,
        'qualified_note_payment': qualified, 'payment_analysis': full,
        'qualification_basis': 'CONDITIONAL_EXPRESS_INCLUSION_OR_SEPARATE_OTHER_ROUTE',
        'actual_payment_obligation': 'NOT_ESTABLISHED', 'actual_default': 'NOT_ESTABLISHED',
        'historical_law_established': False, 'amount_computed': False,
        'complete_legal_test': False, 'source_discovery_or_scope_inference': False}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios',
            'actual_event_established', 'historical_law_established', 'complete_legal_test'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['products_sha256'] != digest(products)
            or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned payment-category profile or complete baseline changed')
    if any(profile[k] is not False for k in
           ('actual_event_established', 'historical_law_established', 'complete_legal_test')):
        raise ValueError('Conditional payment categories cannot attest actual or complete legal status')
    source = context(products)
    if profile['context'] != source:
        raise ValueError('Complete payment-category source context changed')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 128 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Bounded nonempty payment-category scenarios required')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Distinct payment-category case identities required')
    first = rows[0]
    if (first.get('id') != 'all-open' or first.get('component') != ADDITIONAL
            or not isinstance(first.get('tax'), dict) or not isinstance(first.get('conditions'), dict)
            or any(v is not None for v in (*first['tax'].values(), *first['conditions'].values(),
                first.get('component_payable'), first.get('other_qualifying_note_payment')))):
        raise ValueError('All-open category baseline required')
    first_payment = first.get('payment')
    if (not isinstance(first_payment, dict) or first_payment.get('payment_state') != 'UNKNOWN'
            or first_payment.get('other_facts') != {}
            or any(first_payment.get(k) is not None for k in payment_deadline.QUALIFICATIONS)
            or not isinstance(first_payment.get('clock'), dict)
            or any(first_payment['clock'].get(k) is not None
                   for k in ('trigger', 'assessment', 'payment', 'convention', 'utc_offset'))):
        raise ValueError('All-open payment facts required')
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
        'context': source, 'scenarios': [analyze(r, source, instrument) for r in rows],
        'actual_event_established': False, 'historical_law_established': False,
        'complete_legal_test': False, 'original_definition_records_closed': False}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            or {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
            != {k: v for k, v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Payment categories changed the complete prior answer or its seal')
    if answer.get(KEY) != evaluate(products, ordinary, profile, root,
                                   expected_profile_sha256=expected_profile_sha256):
        raise ValueError('Payment-category answer differs from full source reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'scenarios': len(profile['scenarios'])}
