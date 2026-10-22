"""Independent integer calendar and manually transcribed default(b) oracle."""
from itertools import product
from scripts.prospectus_calendar_oracle import civil_number, instant_number

FACTS = ('default.notice', 'default.b.cured', 'default.quorum', 'default.other_at_receipt',
         'representative.b.entrusted', 'representative.b.express_permission')
QUALIFICATIONS = ('holder_notice_received', 'continuous_other_obligation_failure',
                  'counting_convention_supported')


def decision(values, formula):
    if any(v == 'conflict' for v in values):
        return 'CONFLICT'
    outcomes = {formula(*world) for world in product(*[(False, True) if v is None else (v,) for v in values])}
    return 'YES' if outcomes == {True} else 'NO' if outcomes == {False} else 'UNKNOWN'


def classify(row):
    interval = row['interval']
    above, exact = None, None
    if interval['start'] is not None and interval['end'] is not None:
        start, end = (interval[k]['value'] for k in ('start', 'end'))
        convention = interval['convention']
        if convention == 'ELAPSED_24_HOUR_DAYS':
            left, right, unit = instant_number(end) - instant_number(start), 30 * 86400000000, 'microseconds'
        else:
            gap = civil_number(end) - civil_number(start)
            left = gap if convention == 'CIVIL_DATE_GAP' else max(0, gap - 1)
            right, unit = 30, 'civil_days'
        above = left > right
        exact = {'left': str(left), 'right': str(right), 'operator': 'GT', 'unit': unit, 'convention': convention}
    derived = decision([above, *[row[k] for k in QUALIFICATIONS]], lambda *v: all(v))
    values = [row['other_facts'].get(k) for k in FACTS]
    values.append({'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}[derived])
    complete = decision(values, lambda notice, cured, quorum, other, entrusted, permission, timed:
                        notice and timed and not cured and (quorum or other) and (not entrusted or permission))
    return {'above': above, 'exact': exact, 'other30': derived, 'default_b': complete}


def projection(result):
    return {'above': result['duration_above_thirty_days'], 'exact': result['exact_duration'],
            'other30': result['derived_other30']['status'], 'default_b': result['complete_default_b']['status']}


def case(name, instrument='bond', start='2024-01-01', end='2024-02-01', convention='CIVIL_DATE_GAP'):
    return {'id': name, 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'interval': {
        'instrument_id': instrument, 'event_id': name, 'convention': convention,
        'start': None if start is None else {'value': start, 'role': 'fiscal_agent_holder_notice_receipt'},
        'end': None if end is None else {'value': end, 'role': 'assessment'}},
        **dict.fromkeys(QUALIFICATIONS, True),
        'other_facts': {**dict.fromkeys(FACTS, False), 'default.notice': True, 'default.quorum': True}}


def scenarios(instrument):
    rows = [case('all-open', instrument, None, None, None)]
    rows[0].update(**dict.fromkeys(QUALIFICATIONS, None), other_facts={})
    for name, start, end, convention in [
        ('civil-below', '2024-01-01', '2024-01-30', 'CIVIL_DATE_GAP'),
        ('civil-exact', '2024-01-01', '2024-01-31', 'CIVIL_DATE_GAP'),
        ('civil-above', '2024-01-01', '2024-02-01', 'CIVIL_DATE_GAP'),
        ('clear-exact', '2024-01-01', '2024-02-01', 'CLEAR_CIVIL_DAYS'),
        ('clear-above', '2024-01-01', '2024-02-02', 'CLEAR_CIVIL_DAYS'),
        ('leap-exact', '2024-02-01', '2024-03-02', 'CIVIL_DATE_GAP'),
        ('non-leap-exact', '1900-02-01', '1900-03-03', 'CIVIL_DATE_GAP'),
        ('year-crossing', '2023-12-15', '2024-01-15', 'CIVIL_DATE_GAP'),
        ('elapsed-below', '2024-01-01T00:00:00Z', '2024-01-30T23:59:59.999999Z', 'ELAPSED_24_HOUR_DAYS'),
        ('elapsed-exact', '2024-01-01T00:00:00Z', '2024-01-31T00:00:00Z', 'ELAPSED_24_HOUR_DAYS'),
        ('elapsed-above', '2024-01-01T00:00:00Z', '2024-01-31T00:00:00.000001Z', 'ELAPSED_24_HOUR_DAYS'),
        ('spring-offset', '2024-03-01T12:00:00+01:00', '2024-03-31T12:00:00+02:00', 'ELAPSED_24_HOUR_DAYS'),
        ('autumn-offset', '2024-10-01T12:00:00+02:00', '2024-10-31T12:00:00+01:00', 'ELAPSED_24_HOUR_DAYS'),
        ('equivalent-offset', '2024-01-01T08:00:00+08:00', '2024-01-31T00:00:00Z', 'ELAPSED_24_HOUR_DAYS'),
        ('missing-start', None, '2024-02-01', 'CIVIL_DATE_GAP'),
        ('missing-end', '2024-01-01', None, 'CIVIL_DATE_GAP')]:
        rows.append(case(name, instrument, start, end, convention))
    for field in QUALIFICATIONS:
        for suffix, value in [('missing', None), ('false', False), ('conflict', 'conflict')]:
            row = case(field + '-' + suffix, instrument)
            row[field] = value
            rows.append(row)
    for name, changed in [
        ('cured', {'default.b.cured': True}), ('no-exercise-notice', {'default.notice': False}),
        ('quorum-missing', {'default.quorum': None}), ('no-quorum', {'default.quorum': False}),
        ('other-at-receipt', {'default.quorum': False, 'default.other_at_receipt': True}),
        ('representative-restricted', {'representative.b.entrusted': True}),
        ('representative-permission', {'representative.b.entrusted': True, 'representative.b.express_permission': True})]:
        row = case(name, instrument)
        row['other_facts'].update(changed)
        rows.append(row)
    return rows
