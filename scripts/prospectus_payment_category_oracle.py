"""Independent flat Boolean worlds; no production category/predicate imports."""
from copy import deepcopy
from itertools import product
from scripts import prospectus_payment_oracle as payment

POSITIVE = ('source_application_supported', 'specified_german_tax',
            'legally_required_withholding', 'additional_net_preservation_needed')
NEGATIVE = ('exception_a', 'exception_b', 'exception_c', 'exception_d',
            'exception_e', 'flat_tax_or_solidarity')
CONDITIONS = ('classification_supported', 'terms_reference_applies', 'where_applicable')
VALUE = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}


def worlds(facts, formula):
    if any(v == 'conflict' for v in facts.values()):
        return 'CONFLICT'
    unknown = [k for k, v in facts.items() if v is None]
    outcomes = set()
    for choices in product((False, True), repeat=len(unknown)):
        outcomes.add(formula({**facts, **dict(zip(unknown, choices))}))
    return 'UNKNOWN' if len(outcomes) == 2 else 'YES' if True in outcomes else 'NO'


def tax(world):
    return all(world[k] for k in POSITIVE) and not any(world[k] for k in NEGATIVE)


def classifications(row):
    extra = row['component'] == 'section7_additional_amount'
    primitives = dict(row['tax']) if extra else {'component_payable': row['component_payable']}
    base = lambda w: tax(w) if extra else w['component_payable']
    section7 = worlds(primitives, tax) if extra else None
    primitives.update(row['conditions'])
    inclusion_fn = lambda w: base(w) and all(w[k] for k in CONDITIONS)
    inclusion = worlds(primitives, inclusion_fn)
    primitives['other_qualifying_note_payment'] = row['other_qualifying_note_payment']
    qualification = worlds(primitives, lambda w: inclusion_fn(w) or w['other_qualifying_note_payment'])
    return section7, inclusion, qualification


def classify(row):
    section7, inclusion, qualification = classifications(row)
    clock_input = deepcopy(row['payment'])
    clock_input['qualified_note_payment'] = VALUE[qualification]
    result = payment.classify(clock_input)
    return {'section7': section7, 'inclusion': inclusion, 'qualification': qualification,
            'payment_premise': result['premise'], 'complete_default': result['complete']}


def projection(result):
    return {'section7': None if result['section7_route'] is None else result['section7_route']['status'],
        'inclusion': result['express_inclusion']['status'],
        'qualification': result['qualified_note_payment']['status'],
        'payment_premise': result['payment_analysis']['derived_source_payment_premise']['status'],
        'complete_default': result['payment_analysis']['complete_default']['status']}
