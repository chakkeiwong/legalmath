"""Independent integer-decimal oracle; no production calculator imports."""
from itertools import product


def decimal_pair(value):
    if value is None:
        return None
    pieces = value.split('.')
    return int(''.join(pieces)), 10 ** (len(pieces[1]) if len(pieces) == 2 else 0)


def classify(row):
    votes, total = [decimal_pair(row['totals'][k]) for k in ('in_favor', 'participating')]
    simple = qualified = None
    if votes is not None and total is not None and total[0] != 0:
        left, right = votes[0] * total[1], total[0] * votes[1]
        simple, qualified = 2 * left > right, 4 * left >= 3 * right
    subject = row['subject']
    states = []
    for last in (8, 9):
        numbered = None if subject is None else subject != 'NONE' and subject <= last
        raw = [qualified, row['essential_change'], numbered, simple]
        if 'conflict' in raw:
            states.append('CONFLICT')
            continue
        outcomes = set()
        for q, essential, included, s in product(*[(False, True) if v is None else (v,) for v in raw]):
            outcomes.add(q or (not essential and not included and s))
        states.append('YES' if outcomes == {True} else 'NO' if outcomes == {False} else 'UNKNOWN')
    combined = ['CONFLICT' if s == 'CONFLICT' else True if s == 'YES' else False if s == 'NO' else None for s in states]
    combined += [row['eligible_totals'], row['readings_apply']]
    if any(x in ('conflict', 'CONFLICT') for x in combined):
        status = 'CONFLICT'
    elif False in combined:
        status = 'NO'
    elif None in combined:
        status = 'UNKNOWN'
    else:
        status = 'YES'
    return {'contract': states[0], 'statute': states[1], 'combined': status,
            'simple': simple, 'qualified': qualified}


def scenarios(instrument):
    def case(name, subject=None, essential=None, votes=None, total=None, eligible=None, applies=None):
        return {'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'subject': subject,
                'essential_change': essential, 'eligible_totals': eligible, 'readings_apply': applies,
                'totals': {'instrument_id': instrument, 'event_id': name,
                           'unit': 'eligible-participating-voting-weight',
                           'in_favor': votes, 'participating': total}}
    result = [case('all-open')]
    result.extend(case('number'+str(n)+'-below75', n, False, '60', '100', True, True) for n in range(1, 11))
    result.extend([
        case('number8-at75', 8, False, '75', '100', True, True),
        case('number9-at75', 9, False, '75', '100', True, True),
        case('number8-just-below75', 8, False, '74.999', '100', True, True),
        case('outside-numbered-tie', 'NONE', False, '50', '100', True, True),
        case('outside-numbered-abovehalf', 'NONE', False, '50.001', '100', True, True),
        case('essential-number10', 10, True, '60', '100', True, True),
        case('unknown-essential', 10, None, '60', '100', True, True),
        case('conflicting-essential', 10, 'conflict', '75', '100', True, True),
        case('unknown-subject', None, False, '60', '100', True, True),
        case('missing-applicability', 8, False, '75', '100', True, None),
        case('missing-eligibility', 8, False, '75', '100', None, True),
        case('ineligible-totals', 8, False, '75', '100', False, True),
        case('conflicting-applicability', 8, False, '75', '100', True, 'conflict'),
        case('missing-votes', 8, False, None, '100', True, True),
        case('missing-denominator', 8, False, '75', None, True, True),
        case('zero-denominator', 8, False, '0', '0', True, True),
        case('large-below75', 8, False, '2999999999999999999999999999999',
             '4000000000000000000000000000000', True, True),
    ])
    return result


def projection(actual):
    return {'contract': actual['contract']['status'], 'statute': actual['statute']['status'],
            'combined': actual['combined_necessary_majorities']['status'],
            'simple': actual['thresholds']['simple_majority'], 'qualified': actual['thresholds']['qualified75']}
