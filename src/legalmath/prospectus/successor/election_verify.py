"""Separate tables and truth-set evaluation for the declared election reading."""
from copy import deepcopy
from itertools import product

PRIOR_ALLOWED = {
    'SECTION2_13_1B': (True, True, False, False),
    'SECTION2_13_2': (True, True, True, False),
}
HISTORY = ('NO_PRIOR_OTHER', 'PRIOR_OTHER_ADMISSION_CEASED',
           'PRIOR_OTHER_CONTINUES_NO_CHOICE_WITHIN_THREE_YEARS',
           'PRIOR_OTHER_CONTINUES_CHOICE_WITHIN_THREE_YEARS')
ADMISSION = ('GERMANY_ONLY', 'GERMANY_AND_OTHER_EU_EEA', 'OTHER_EU_EEA_ONLY', 'NONE')


def truth(values, function):
    possible = {function(*v) for v in product(*[(False, True) if x is None else (x,) for x in values])}
    return True if possible == {True} else False if possible == {False} else None


def state(value):
    return 'UNKNOWN' if value is None else 'YES' if value else 'NO'


def expected(route, f):
    names = ('initial_permission', 'replacement_condition', 'choice_expired', 'continuing_german_route')
    missing = sorted(k for k, v in f.items() if v is None)
    conflicts = sorted(k for k, v in f.items() if v == 'conflict')
    if conflicts: return {'statuses': dict.fromkeys(names, 'CONFLICT'), 'missing': missing, 'conflicts': conflicts}
    choices = range(4) if f['prior_election_at_choice'] is None else (HISTORY.index(f['prior_election_at_choice']),)
    admissions = range(4) if f['admission_at_evaluation'] is None else (ADMISSION.index(f['admission_at_evaluation']),)
    by_case = []
    for prior, admission in product(choices, admissions):
        eligible = truth([f['category_satisfied']], lambda c: c and PRIOR_ALLOWED[route][prior])
        if route == 'SECTION2_13_1B':
            replace = (False, False, True, False)[admission]
            expired = truth([f['new_home_choice_made']], lambda new: admission == 3 or (admission == 2 and new))
        else:
            replace = (False, f['germany_choice_at_least_three_years'], True, False)[admission]
            expired = truth([f['category1_admitted_issuance'], f['new_home_choice_made'], replace],
                            lambda issued, new, allowed: issued or admission == 3 or (new and allowed))
        continuing = truth([eligible, f['germany_choice_made'], f['publication_under_section5'],
                            f['reading_applies'], expired], lambda a, b, c, d, e: a and b and c and d and not e)
        by_case.append((eligible, replace, expired, continuing))
    statuses = {}
    for i, name in enumerate(names):
        possible = set()
        for row in by_case: possible.update((False, True) if row[i] is None else (row[i],))
        statuses[name] = 'YES' if possible == {True} else 'NO' if possible == {False} else 'UNKNOWN'
    return {'statuses': statuses, 'missing': missing, 'conflicts': conflicts}


def verify(answer, ordinary, profile, products, root):
    from .contracts import digest
    from .election import KEY, metadata, policy, context
    from .issuer_qualification_verify import qualification, publication_decisions
    cases = policy(ordinary, profile, digest(profile))
    if profile['products_sha256'] != digest(products) or profile['context'] != context(ordinary, root):
        raise ValueError('Election profile product or source identity changed')
    body = {k: v for k, v in answer.items() if k != 'report_sha256'}
    if (answer.get('report_sha256') != digest(body) or
            digest({k: v for k, v in body.items() if k != KEY}) !=
            digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Complete preceding answer changed')
    review = answer.get(KEY, {})
    if digest({k: v for k, v in review.items() if k != 'scenarios'}) != digest(metadata(profile)):
        raise ValueError('Election source context or scope changed')
    rows = []
    for row in profile['scenarios']:
        route = expected(row['route'], row['facts']); base = cases[row['base_case']]
        status = route['statuses']['continuing_german_route']
        qfacts = deepcopy(base['qualification'])
        qfacts['home_state'] = {'YES': 'GERMANY', 'NO': None, 'UNKNOWN': None, 'CONFLICT': 'conflict'}[status]
        q = qualification(qfacts)
        derived = deepcopy(base['derived_publication_scenario']); derived['id'] = row['id']
        derived['premises']['inlandsemittent_qualified'] = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}[q['status']]
        decisions = publication_decisions(derived['premises'])
        rows.append({**row, 'route_result': route, 'derived_qualification': qfacts,
            'qualification_result': q, 'derived_publication_scenario': derived,
            'publication_decisions': decisions, 'baseline_decisions': base['publication_decisions'],
            'answer_changed': decisions != base['publication_decisions']})
    if digest(review.get('scenarios')) != digest(rows):
        raise ValueError('Election condition or downstream implication changed')
    return {'status': 'PASS', 'scenarios': len(rows),
            'changed_scenarios': sum(r['answer_changed'] for r in rows), 'complete_ordinary_preserved': True,
            'actual_home_state_established': False}
