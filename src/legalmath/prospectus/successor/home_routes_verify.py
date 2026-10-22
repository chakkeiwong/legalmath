"""Categorical statutory tables, independent of candidate route predicates."""
from copy import deepcopy
from itertools import product

INSTRUMENT = ('SECTION2_13_1_SECURITIES', 'OTHER_FINANCIAL_INSTRUMENTS')
SEAT = ('GERMANY', 'OTHER_EU_EEA', 'THIRD_COUNTRY')
ADMISSION = ('GERMANY_ONLY', 'GERMANY_AND_OTHER_EU_EEA', 'OTHER_EU_EEA_ONLY', 'NONE')
HISTORY = ('NO_PRIOR_OTHER', 'PRIOR_OTHER_ADMISSION_CEASED',
           'PRIOR_OTHER_CONTINUES_NO_CHOICE_WITHIN_THREE_YEARS',
           'PRIOR_OTHER_CONTINUES_CHOICE_WITHIN_THREE_YEARS')
CHOICE = ('NONE_EFFECTIVE', 'GERMANY_EFFECTIVE', 'OTHER_EU_EEA_EFFECTIVE')
# Rows: instrument class, seat; columns: admission. Entries identify the
# structural numbered category before applying section4 permission history.
STRUCTURE = {
    (0, 0): (None, None, None, None), (0, 1): (None, None, None, None),
    (0, 2): ('1b', '1b', None, None),
    (1, 0): ('2', '2', '2', None), (1, 1): ('2', '2', None, None),
    (1, 2): ('2', '2', None, None),
}
PERMITTED = {None: (False,) * 4, '1b': (True, True, False, False), '2': (True, True, True, False)}


def expected(route, facts):
    names = ('category_and_admission', 'german_route') if route == 'SECTION2_13_1A' else (
        'category_and_admission', 'permission_to_choose', 'no_effective_choice', 'german_route')
    missing = sorted(k for k, v in facts.items() if v is None)
    conflicts = sorted(k for k, v in facts.items() if v == 'conflict')
    if conflicts: return {'statuses': dict.fromkeys(names, 'CONFLICT'), 'missing': missing, 'conflicts': conflicts}
    domains = {'instrument_class': INSTRUMENT, 'seat': SEAT, 'admission_at_evaluation': ADMISSION,
               'reading_applies': (False, True)}
    if route == 'SECTION2_13_3':
        domains.update(prior_election_at_evaluation=HISTORY, effective_home_choice=CHOICE)
    outcomes = {key: set() for key in names}
    for values in product(*(range(len(d)) if facts[k] is None else (d.index(facts[k]),) for k, d in domains.items())):
        instrument, seat, admission, applies = values[:4]
        if route == 'SECTION2_13_1A':
            structural = (instrument, seat, admission) in {(0, 0, 0), (0, 0, 1), (0, 0, 2)}
            result = (structural, structural and applies == 1)
        else:
            history, choice = values[4:]
            category = STRUCTURE[instrument, seat][admission]
            permitted = PERMITTED[category][history]
            result = (category is not None, permitted, choice == 0,
                      all((permitted, admission in (0, 1), choice == 0, applies == 1)))
        for key, value in zip(names, result): outcomes[key].add(value)
    return {'statuses': {k: 'YES' if v == {True} else 'NO' if v == {False} else 'UNKNOWN'
                         for k, v in outcomes.items()}, 'missing': missing, 'conflicts': conflicts}


def verify(answer, ordinary, profile, products, root):
    from .contracts import digest
    from .home_routes import KEY, metadata, policy, context
    from .issuer_qualification_verify import qualification, publication_decisions
    cases = policy(ordinary, profile, digest(profile))
    if profile['products_sha256'] != digest(products) or profile['context'] != context(ordinary, root):
        raise ValueError('Home-route profile product or source identity changed')
    body = {k: v for k, v in answer.items() if k != 'report_sha256'}
    if (answer.get('report_sha256') != digest(body) or
            digest({k: v for k, v in body.items() if k != KEY}) !=
            digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Complete preceding answer changed')
    review = answer.get(KEY, {})
    if digest({k: v for k, v in review.items() if k != 'scenarios'}) != digest(metadata(profile)):
        raise ValueError('Home-route source context or scope changed')
    admission_table = dict(zip(ADMISSION, ('ONLY_GERMANY_ORGANISED', 'NEITHER_EXCLUSIVE',
                                         'ONLY_OTHER_EU_EEA', 'NEITHER_EXCLUSIVE')))
    rows = []
    for row in profile['scenarios']:
        route = expected(row['route'], row['facts']); base = cases[row['base_case']]
        qfacts = deepcopy(base['qualification'])
        qfacts['home_state'] = {'YES': 'GERMANY', 'NO': None, 'UNKNOWN': None,
                               'CONFLICT': 'conflict'}[route['statuses']['german_route']]
        admission = row['facts']['admission_at_evaluation']
        qfacts['admission_scope'] = admission_table.get(admission, admission)
        q = qualification(qfacts)
        derived = deepcopy(base['derived_publication_scenario']); derived['id'] = row['id']
        derived['premises']['inlandsemittent_qualified'] = {'YES': True, 'NO': False,
            'UNKNOWN': None, 'CONFLICT': 'conflict'}[q['status']]
        decisions = publication_decisions(derived['premises'])
        rows.append({**row, 'route_result': route, 'derived_qualification': qfacts,
            'qualification_result': q, 'derived_publication_scenario': derived,
            'publication_decisions': decisions, 'baseline_decisions': base['publication_decisions'],
            'answer_changed': decisions != base['publication_decisions']})
    if digest(review.get('scenarios')) != digest(rows):
        raise ValueError('Home-route condition or downstream implication changed')
    return {'status': 'PASS', 'scenarios': len(rows),
            'changed_scenarios': sum(r['answer_changed'] for r in rows), 'complete_ordinary_preserved': True,
            'actual_home_state_established': False}
