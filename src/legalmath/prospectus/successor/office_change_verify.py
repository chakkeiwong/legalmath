"""Separate decision table for the declared office conjunction."""
from copy import deepcopy
from .contracts import digest

KEY = 'office_change_review'


def truth(values):
    if any(v == 'conflict' for v in values): return 'CONFLICT'
    if any(v is False for v in values): return 'NO'
    if any(v is None for v in values): return 'UNKNOWN'
    if all(v is True for v in values): return 'YES'
    raise ValueError('Unexpected truth-table input')


def expected(row, notice_status):
    a, b = row['original_country'], row['replacement_country']
    if 'conflict' in (a, b): country = 'conflict'
    elif a is None or b is None: country = None
    elif a == b: country = True
    else: country = False
    notice = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}[notice_status]
    return truth([notice, country, row['original_office_designated'],
                  row['replacement_office_designated'], row['reading_applies']])


def verify(answer, ordinary, profile, products, root):
    from . import office_change as model
    if (answer.get('report_sha256') != digest({k:v for k,v in answer.items() if k != 'report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY, 'report_sha256')}
            != {k:v for k,v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Office composition changed the complete prior answer')
    reconstructed = model.evaluate(products, ordinary, profile, root, expected_profile_sha256=digest(profile))[KEY]
    if answer.get(KEY) != reconstructed: raise ValueError('Office answer differs from complete source reconstruction')
    notices = {r['scenario']['id']: r for r in ordinary['notice_delivery_review']['scenarios']}
    changes = 0
    for row, result in zip(profile['scenarios'], answer[KEY]['scenarios']):
        status = notices[row['notice_case']]['notice']['conditional_notice_precondition']['status']
        actual = result['conditional_office_preconditions']['status']
        if actual != expected(row, status): raise ValueError('Office result differs from independent decision table')
        changes += actual != status
    if answer['basf_agents']['calculation_agent_office'] != 'UNRESOLVED':
        raise ValueError('Actual office designation was invented')
    return {'status': 'PASS', 'complete_baseline_preserved': True, 'scenarios': len(profile['scenarios']),
        'different_from_notice_alone': changes, 'actual_designation_established': False}
