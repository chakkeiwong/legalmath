from copy import deepcopy
from itertools import product
import json
from pathlib import Path
import pytest
from legalmath.prospectus import payment_categories as module
from scripts import prospectus_payment_category_oracle as oracle

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/payment-categories-323'
CASES = json.loads((PREP / 'cases.json').read_text())['cases']
PROFILE = json.loads((PREP / 'profile.json').read_text())
INSTRUMENT = PROFILE['scenarios'][0]['identity']['instrument_id']


@pytest.mark.parametrize('number', range(len(CASES)), ids=[r['scenario']['id'] for r in CASES])
def test_independently_authored_whole_scenarios(number):
    row = PROFILE['scenarios'][number]
    actual = module.analyze(row, PROFILE['context'], INSTRUMENT)
    assert oracle.classify(row) == CASES[number]['expected']
    assert oracle.projection(actual) == CASES[number]['expected']
    assert actual['amount_computed'] is False
    assert actual['actual_default'] == 'NOT_ESTABLISHED'
    assert actual['historical_law_established'] is False
    assert actual['payment_analysis']['scenario']['qualified_note_payment'] == oracle.VALUE[
        CASES[number]['expected']['qualification']]


def test_section7_complete_boolean_domain_and_disjoint_composition():
    keys = (*oracle.POSITIVE, *oracle.NEGATIVE)
    for values in product((False, True), repeat=len(keys)):
        tax = dict(zip(keys, values))
        assert module.section7(tax)['status'] == oracle.worlds(tax, oracle.tax)
    row = deepcopy(PROFILE['scenarios'][1])
    # This complete 4^5 matrix exercises exact disjoint composition, including
    # partial information and conflicts, against a single unsplit formula.
    for values in product((False, True, None, 'conflict'), repeat=5):
        row['tax']['exception_b'] = values[0]
        row['conditions'] = dict(zip(oracle.CONDITIONS, values[1:4]))
        row['other_qualifying_note_payment'] = values[4]
        actual = module.qualification(row)
        assert tuple(None if r is None else r['status'] for r in actual) == oracle.classifications(row)


@pytest.mark.parametrize('kind', ['override', 'grossup-override', 'wrong-instrument',
    'wrong-event', 'no-obligation', 'no-tax-identity', 'lost-tax-exclusion', 'unexpected-amount',
    'foreign-route', 'tax-on-principal', 'missing-scope', 'actual-kind'])
def test_refuse_unjustified_category_or_event(kind):
    row = deepcopy(PROFILE['scenarios'][1])
    if kind == 'override': row['payment']['qualified_note_payment'] = True
    elif kind == 'grossup-override': row['component_payable'] = True
    elif kind == 'wrong-instrument': row['identity']['instrument_id'] = 'other'
    elif kind == 'wrong-event': row['payment']['clock']['event_id'] = 'other'
    elif kind == 'no-obligation': row['identity']['obligation_id'] = ''
    elif kind == 'no-tax-identity': row['identity']['tax_id'] = None
    elif kind == 'lost-tax-exclusion': row['tax'].pop('exception_c')
    elif kind == 'unexpected-amount': row['amount'] = '100'
    elif kind == 'foreign-route': row['payment']['route'] = 'c'
    elif kind == 'tax-on-principal': row['component'] = 'premium'; row['identity']['tax_id'] = None
    elif kind == 'missing-scope': row['conditions'].pop('terms_reference_applies')
    else: row['kind'] = 'ACTUAL_CLIENT_FACTS'
    with pytest.raises(ValueError):
        module.analyze(row, PROFILE['context'], INSTRUMENT)


def test_complete_source_context_retains_all_tax_exceptions():
    source = PROFILE['context']
    readings = {r['kind']: r for r in source['contract_readings']}
    assert set(readings) == {'principal_definition', 'interest_definition',
                            'tax_withholding', 'gross_up', 'german_flat_tax'}
    assert all('(' + letter + ')' in readings['gross_up']['quote'] for letter in 'abcde')
    assert all(r['sources'] and r['source_spans'] for r in readings.values())
    assert source['original_definition_records'] == ['U02-capital', 'U03-interest']
