"""Material sign, missing-value and displayed-arithmetic distinctions."""
import pytest
from legalmath.prospectus.basf_statement import integer_millions, arithmetic, ROWS


@pytest.mark.parametrize('raw,value', [('–391', -391), ('−15', -15), ('-455', -455),
                                      ('5,982', 5982), ('0', 0), ('10,655', 10655)])
def test_printed_sign_and_grouping(raw, value):
    assert integer_millions(raw) == {'literal': raw, 'status': 'PRINTED_INTEGER', 'integer_millions': value}


def test_standalone_dash_does_not_mean_zero():
    assert integer_millions('–')['integer_millions'] is None
    assert integer_millions('0')['integer_millions'] == 0


@pytest.mark.parametrize('raw', ['1,20', '01', '3.794', ' 10', '10 ', '€10', '+3', '–', ''])
def test_non_integer_not_silently_normalized(raw):
    if raw == '–':
        assert integer_millions(raw)['status'] == 'PRINTED_DASH_UNKNOWN'
    else:
        with pytest.raises(ValueError):
            integer_millions(raw)


def test_residual_is_reported_and_unknown_component_is_not_imputed():
    rows = [{'id': k, 'cells': {y: integer_millions('0') for y in ('2022', '2021')}} for k in ROWS]
    indexed = {r['id']: r for r in rows}
    for key, literal in [('pensions', '3,758'), ('pension_tax', '–1,256'), ('equity_nonrec', '83'), ('nonrec', '2,586')]:
        indexed[key]['cells']['2022'] = integer_millions(literal)
    indexed['currency_reclass']['cells']['2022'] = integer_millions('–')
    results = {(r['group'], r['year']): r for r in arithmetic(rows)}
    assert results['nonrec', '2022']['printed_minus_sum'] == 1
    assert results['nonrec', '2022']['status'] == 'PRINTED_RESIDUAL'
    assert results['rec', '2022']['sum_of_printed_components'] is None
    assert results['rec', '2022']['status'] == 'UNKNOWN_COMPONENT'
    assert all(r['role'] == 'EXPLANATORY_ONLY' for r in results.values())
