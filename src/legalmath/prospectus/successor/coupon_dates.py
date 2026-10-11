"""Explicit coupon-date lattices; no convention is inferred from an endpoint."""
from calendar import monthrange
from datetime import date


def iso_date(value):
    if not isinstance(value, str):
        raise ValueError('Coupon dates require ISO date strings')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Coupon dates require canonical ISO dates')
    return parsed


def english_date(quote):
    months = 'January February March April May June July August September October November December'.split()
    tokens = quote.strip().split() if isinstance(quote, str) else []
    if len(tokens) != 3 or tokens[1] not in months:
        raise ValueError('Explicit English coupon anchor date required')
    return date(int(tokens[2]), months.index(tokens[1])+1, int(tokens[0])).isoformat()


def anchored_date(anchor, months, eom):
    """Advance from the declared original day, including across clamped months."""
    initial = iso_date(anchor)
    if type(months) is not int or type(eom) is not bool:
        raise ValueError('Integer month offset and explicit EOM rule required')
    index = initial.year*12 + initial.month-1 + months
    year, month = divmod(index, 12)
    month += 1
    last = monthrange(year, month)[1]
    day = last if eom and initial.day == monthrange(initial.year, initial.month)[1] else min(initial.day, last)
    return date(year, month, day)


def lattice_index(value, anchor, frequency, eom):
    """Return a date's coupon-step index, rejecting a date off this lattice."""
    if type(frequency) is not int or frequency not in {1,2,3,4,6,12}:
        raise ValueError('Explicit supported coupon frequency required')
    initial, value_date = iso_date(anchor), iso_date(value)
    months = (value_date.year-initial.year)*12 + value_date.month-initial.month
    step = 12//frequency
    if months % step or anchored_date(anchor, months, eom) != value_date:
        raise ValueError('Coupon date is not on the declared anchor lattice')
    return months//step
