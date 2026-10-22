"""Boundary,eligibility and full control/rating/exercise composition checks."""
from itertools import product
import pytest
from legalmath.prospectus import control_votes as module
from scripts import prospectus_votes_oracle as oracle
NODE = {'conditions': {'all': ['control_put.control', 'control_put.rating', 'control_put.event_notice',
    'control_put.timely_exercise', 'control_put.valid_declaration', 'control_put.delivery', 'control_put.payment_day',
    {'any': [{'not': 'representative.put.entrusted'}, 'representative.put.express_permission']}]},
    'exceptions': 'control_put.earlier_tax_notice'}


@pytest.mark.parametrize('row', oracle.scenarios('bond'), ids=lambda r: r['id'])
def test_exact_votes_and_source_formula_match_independent_oracle(row):
    assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)


def test_finite_qualification_and_complete_formula_cases():
    count = 0
    for eligible in ('49', '50', '51'):
        for values in product((False, True), repeat=4):
            row = oracle.case('qualifications', eligible=eligible)
            row.update(zip(oracle.QUALIFICATIONS, values))
            assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)
            count += 1
    for values in product((False, True), repeat=9):
        row = oracle.case('full'); row['other_facts'] = dict(zip(oracle.FACTS, values))
        assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)
        count += 1
    assert count == 560


@pytest.mark.parametrize('kind', ['instrument', 'issuer', 'operand-event', 'empty-event',
    'shares', 'participating-denominator', 'principal-denominator', 'negative', 'float',
    'precision', 'exceeds', 'qualification', 'control-override', 'rating-override',
    'nested-override', 'nested-event', 'nested-instrument', 'nested-id', 'cutoff-override'])
def test_unbound_or_malformed_inputs_refuse(kind):
    row = oracle.case('bad')
    if kind == 'instrument': row['votes']['instrument_id'] = 'other'
    elif kind == 'issuer': row['votes']['issuer'] = 'other'
    elif kind == 'operand-event': row['votes']['eligible']['control_event_id'] = 'other'
    elif kind == 'empty-event': row['votes']['control_event_id'] = ''
    elif kind == 'shares': row['votes']['eligible']['unit'] = 'SHARES'
    elif kind == 'participating-denominator': row['votes']['total']['basis'] = 'PARTICIPATING_VOTING_RIGHTS'
    elif kind == 'principal-denominator': row['votes']['total']['basis'] = 'OUTSTANDING_NOTE_PRINCIPAL'
    elif kind == 'negative': row['votes']['eligible']['value'] = '-1'
    elif kind == 'float': row['votes']['eligible']['value'] = 51.0
    elif kind == 'precision': row['votes']['eligible']['value'] = '0.' + '1' * 129
    elif kind == 'exceeds': row['votes']['eligible']['value'] = '101'
    elif kind == 'qualification': row['eligible_scope_supported'] = 1
    elif kind == 'control-override': row['other_facts']['control_put.control'] = True
    else:
        row = next(r for r in oracle.scenarios('bond') if r['id'] == 'composed-timely')
        if kind == 'rating-override': row['other_facts']['control_put.rating'] = True
        elif kind == 'nested-override': row['rating_scenario']['other_facts'] = {'control_put.control': True}
        elif kind == 'nested-event': row['rating_scenario']['events']['control_event_id'] = 'other'
        elif kind == 'nested-instrument': row['rating_scenario']['events']['instrument_id'] = 'other'
        elif kind == 'nested-id': row['rating_scenario']['id'] = 'other'
        else: row['other_facts']['control_put.timely_exercise'] = True
    with pytest.raises(ValueError):
        module.analyze(row, NODE, 'bond')


def test_exact_half_and_statutory_thirty_do_not_trigger_contract():
    for eligible in ('30', '50'):
        result = module.analyze(oracle.case('threshold', eligible=eligible), NODE, 'bond')
        assert result['derived_control']['status'] == 'NO'
        assert result['complete_control_put']['status'] == 'NO'
    row = oracle.case('unknown-scope'); row['eligible_scope_supported'] = None
    result = module.analyze(row, NODE, 'bond')
    assert result['voting_rights_above_half'] is True
    assert result['derived_control']['status'] == 'UNKNOWN'


def test_composition_preserves_each_independent_condition():
    rows = {r['id']: r for r in oracle.scenarios('bond')}
    expected = {'composed-timely': 'YES', 'composed-late': 'NO',
                'composed-causal-unknown': 'UNKNOWN', 'composed-exact-half': 'NO',
                'composed-ownership-unknown': 'UNKNOWN'}
    for name, status in expected.items():
        assert module.analyze(rows[name], NODE, 'bond')['complete_control_put']['status'] == status
