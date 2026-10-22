"""Deterministic amount quotations for the explicitly selected initial-coupon profile."""
import re
from ..semantics import exact


def quoted_amount(text, currency):
    """Read one complete number, with an optional matching code or pound symbol."""
    match = re.fullmatch(r'(?:(?P<code>[A-Z]{3})\s+|(?P<pound>£)\s*)?'
                         r'(?P<number>(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)', text.strip())
    if (not match or match['code'] not in (None, currency)
            or match['pound'] is not None and currency != 'GBP'):
        raise ValueError('Amount quotation requires one number and a matching currency')
    return exact(match['number'].replace(',', ''))


def initial_amounts(scenario, rate, fraction, rounding):
    """Check distinct printed regular/initial amounts; do not repair a mismatch."""
    for key in ('calculation_amount', 'fixed_coupon_amount', 'broken_coupon_amount'):
        if quoted_amount(scenario['evidence'][key]['source']['quote'], scenario['currency']) != exact(scenario[key]):
            raise ValueError('Amount differs from its source quotation: ' + key)
    amount = exact(scenario['calculation_amount'])
    if amount <= 0:
        raise ValueError('Positive calculation amount required')
    expected_regular = rounding(amount * rate / scenario['frequency'], scenario['rounding']['quantum'], scenario['rounding']['rule'])
    expected_initial = rounding(amount * rate * fraction, scenario['rounding']['quantum'], scenario['rounding']['rule'])
    if exact(scenario['fixed_coupon_amount']) != expected_regular:
        raise ValueError('Published regular amount disagrees with admitted rate/frequency')
    if exact(scenario['broken_coupon_amount']) != expected_initial:
        raise ValueError('Published initial broken amount disagrees with admitted ICMA fraction')
    return expected_initial
