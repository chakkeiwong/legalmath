"""Independent retained-source integer check; no legalmath/kernel imports."""
from datetime import date, timedelta
from fractions import Fraction
from hashlib import sha256
import re


SOURCES = {
    'danske-dkk-at1-2026-final-complete-pages.txt': '751cf0ed3e49094f78d6aa03798e9f9d14c1c5277ecb86f512d79911cb2d68f5',
    'danske-at1-2026-base-complete-pages.txt': '9a48dceec0052f4ea74a27cf2235a989d830e13e58b5eda4a906b708c20629f2',
}
# Hand-enumerated from Supplement4: first payment through first reset inclusive.
COUPONS = ['2026-11-25', '2027-11-25', '2028-11-25', '2029-11-25', '2030-11-25', '2031-11-25']


def source_check(folder):
    documents = {}
    for name, expected in SOURCES.items():
        raw = (folder / name).read_bytes()
        assert sha256(raw).hexdigest() == expected, name
        documents[name] = [' '.join(p.split()) for p in raw.decode().split('\f')]
    supplement, base = documents.values()
    assert 'DKK 1,250,000,000' in supplement[2]
    assert '25 August 2026' in supplement[3]
    assert re.search(r'5\.100 per cent\. Fixed Rate from, and including, the Issue Date to, but excluding, 25 November 2031', supplement[3])
    assert '25 November in each year from, and including, 25 November 2026 to, and including, the First Reset Date' in supplement[3]
    assert 'short first coupon' in supplement[3] and 'Day Count Fraction: 30/360' in supplement[3]
    assert 'VP Systems Notes' in supplement[5]
    assert 'unless such number is 31, in which case D1 will be 30' in base[70]
    assert 'unless such number would be 31 and D1 is greater than 29, in which case D2 will be 30' in base[70]
    assert 'next succeeding VP Systems Notes payment day' in base[126]
    assert 'any further interest or other payment in respect of any such delay' in base[126]
    return {'text_sources': SOURCES, 'source_reading': 'SUPPLEMENT3,4,6; BASE71(v),127(15.3-15.4)',
            'automatic_legal_interpretation': False, 'external_opinion_required': False}


def numerator(start, end):
    y1, m1, d1 = map(int, start.split('-'))
    y2, m2, d2 = map(int, end.split('-'))
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 > 29:
        d2 = 30
    return 360 * (y2 - y1) + 30 * (m2 - m1) + d2 - d1


def expected(*, holiday=False, excluded=False):
    result = []
    starts = ['2026-08-25', *COUPONS[:-1]]
    for start, due in zip(starts, COUPONS):
        day = date.fromisoformat(due)
        while day.weekday() in {5, 6} or holiday and day.isoformat() == '2026-11-25':
            day += timedelta(days=1)
        count = numerator(start, due)
        unrounded = Fraction(1000000 * 51 * count, 1000 * 360)
        # Explicit numerical HALF_UP, quantum1; independent integer rounding.
        q, r = divmod(unrounded.numerator, unrounded.denominator)
        amount = q + int(2 * r >= unrounded.denominator)
        result.append({'start': start, 'end': due, 'payment': day.isoformat(),
                       'numerator': count, 'fraction': str(Fraction(count, 360)),
                       'unrounded': str(unrounded), 'amount': str(amount), 'excluded': excluded})
    return result


def check_value(value, *, holiday=False, excluded=False):
    rows = expected(holiday=holiday, excluded=excluded)
    assert value['version'] == 'conditional-fixed-phase.v1'
    assert len(value['calculations']) == len(value['coupon_schedule']) == len(rows) == 6
    assert value['fixed_phase_end'] == '2031-11-25' and value['accrual_end_exclusive'] is True
    assert value['note_form'] == 'VP_SYSTEMS' and value['redemption_inferred'] is False
    assert value['floating_phase'] == 'NOT_MODELLED' and value['actual_event'] == 'NOT_ESTABLISHED'
    assert value['full_settlement_supported'] is False and 'maturity_date' not in value['contract_terms']['terms']
    assert set(value['phase_assumptions']) == {'no_call', 'no_cancellation', 'no_conversion', 'no_principal_reduction', 'no_tax'}
    assert all(v is True for v in value['phase_assumptions'].values())
    for row, period, calculation in zip(rows, value['coupon_schedule'], value['calculations']):
        assert period == {'accrual_start': row['start'], 'accrual_end': row['end'], 'due_date': row['end'],
                          'stub': 'SHORT_FIRST' if row is rows[0] else 'REGULAR'}
        assert calculation['day_fraction'] == row['fraction'] and calculation['payment_date'] == row['payment']
        assert calculation['actual_event'] == 'NOT_ESTABLISHED' and not calculation['full_settlement_supported']
        assert not calculation['entitlement_basis']['legal_entitlement_established']
        if excluded:
            assert calculation['transfers'] == []
        else:
            assert len(calculation['transfers']) == 1
            transfer = calculation['transfers'][0]
            assert transfer['currency'] == 'DKK' and transfer['amount'] == row['amount']
            assert transfer['unrounded'] == row['unrounded']
    total = sum(Fraction(c['transfers'][0]['amount']) for c in value['calculations']) if not excluded else Fraction()
    assert total == (0 if excluded else 267750)
    return {'rows': rows, 'total': str(total), 'criterion': 'SOURCE_INTEGER_ARITHMETIC_AND_ALL_SIX_DATES',
            'printed_definitive_amounts_used': False, 'actual_payment_forecast': False}
