"""Conditional automatic/provisional WpHG home-state routes, with open alternatives."""
from copy import deepcopy
from itertools import product

from .. import publication_routes as publication
from . import election, issuer_qualification as issuer
from .anchors import fields
from .contracts import digest

VERSION = 'basf-home-routes.v1'
KEY = 'home_routes_review'
ROUTES = ('SECTION2_13_1A', 'SECTION2_13_3')
INSTRUMENT = ('SECTION2_13_1_SECURITIES', 'OTHER_FINANCIAL_INSTRUMENTS')
SEAT = ('GERMANY', 'OTHER_EU_EEA', 'THIRD_COUNTRY')
ADMISSION = ('GERMANY_ONLY', 'GERMANY_AND_OTHER_EU_EEA', 'OTHER_EU_EEA_ONLY', 'NONE')
HISTORY = ('NO_PRIOR_OTHER', 'PRIOR_OTHER_ADMISSION_CEASED',
           'PRIOR_OTHER_CONTINUES_NO_CHOICE_WITHIN_THREE_YEARS',
           'PRIOR_OTHER_CONTINUES_CHOICE_WITHIN_THREE_YEARS')
CHOICE = ('NONE_EFFECTIVE', 'GERMANY_EFFECTIVE', 'OTHER_EU_EEA_EFFECTIVE')
ADMISSION_TO_ISSUER = dict(zip(ADMISSION,
    ('ONLY_GERMANY_ORGANISED', 'NEITHER_EXCLUSIVE', 'ONLY_OTHER_EU_EEA', 'NEITHER_EXCLUSIVE')))


def domains(route):
    if route not in ROUTES: raise ValueError('Explicit supported automatic/provisional route required')
    common = {'instrument_class': INSTRUMENT, 'seat': SEAT,
              'admission_at_evaluation': ADMISSION, 'reading_applies': (False, True)}
    if route == ROUTES[1]:
        common.update(prior_election_at_evaluation=HISTORY, effective_home_choice=CHOICE)
    return common


def world(route, facts):
    category1 = facts['instrument_class'] == INSTRUMENT[0]
    domestic = facts['seat'] == 'GERMANY'
    admission = facts['admission_at_evaluation']
    admitted_germany = admission in ADMISSION[:2]
    if route == ROUTES[0]:
        structural = category1 and domestic and admission != 'NONE'
        return {'category_and_admission': structural,
                'german_route': structural and facts['reading_applies']}
    route1b = category1 and facts['seat'] == 'THIRD_COUNTRY' and admitted_germany
    route2 = not category1 and ((domestic and admission != 'NONE') or (not domestic and admitted_germany))
    history = facts['prior_election_at_evaluation']
    permission = (route1b and history in HISTORY[:2]) or (route2 and history in HISTORY[:3])
    no_choice = facts['effective_home_choice'] == 'NONE_EFFECTIVE'
    return {'category_and_admission': route1b or route2, 'permission_to_choose': permission,
            'no_effective_choice': no_choice,
            'german_route': permission and admitted_germany and no_choice and facts['reading_applies']}


def analyze(route, facts):
    supported = domains(route); fields(facts, supported, supported)
    for key, values in supported.items():
        value = facts[key]
        if value is None or value == 'conflict': continue
        if key == 'reading_applies':
            if type(value) is not bool: raise ValueError('Applicability must be Boolean, unknown or conflict')
        elif not isinstance(value, str) or value not in values:
            raise ValueError('Explicit supported home-state category required')
    missing = sorted(k for k, v in facts.items() if v is None)
    conflicts = sorted(k for k, v in facts.items() if v == 'conflict')
    names = ('category_and_admission', 'german_route') if route == ROUTES[0] else (
        'category_and_admission', 'permission_to_choose', 'no_effective_choice', 'german_route')
    if conflicts:
        return {'statuses': dict.fromkeys(names, 'CONFLICT'), 'missing': missing, 'conflicts': conflicts}
    outcomes = {key: set() for key in names}
    for values in product(*(domain if facts[key] is None else (facts[key],)
                            for key, domain in supported.items())):
        for key, value in world(route, dict(zip(supported, values))).items(): outcomes[key].add(value)
    return {'statuses': {k: 'YES' if v == {True} else 'NO' if v == {False} else 'UNKNOWN'
                         for k, v in outcomes.items()}, 'missing': missing, 'conflicts': conflicts}


def derived_admission(value):
    if value is None or value == 'conflict': return value
    return ADMISSION_TO_ISSUER[value]


def context(ordinary, root):
    previous = ordinary.get(election.KEY)
    if not isinstance(previous, dict) or previous.get('version') != election.VERSION:
        raise ValueError('Complete preceding election answer required')
    checked = election.context(ordinary, root)
    if previous['context'] != checked: raise ValueError('Preceding election source context changed')
    source = checked['prior_issuer_context']
    return {'source_files': {**source['source_files'], **checked['source_files']},
        'complete_section2': source['complete_current_section2'],
        'complete_section4': checked['complete_section4'], 'complete_section5': checked['complete_section5'],
        'prior_election_context_sha256': digest(checked),
        'displayed_law_temporal_applicability': 'NOT_ESTABLISHED',
        'implementing_rules': 'NOT_RETRIEVED', 'actual_issuer_facts': 'NOT_ESTABLISHED',
        'instrument_class': 'Hypothetical issuer class: shares or debt below EUR1000/equivalent at issue versus other financial instruments; classification and FX not derived',
        'admission_scope': 'Same hypothetical issuer-wide organised-market category used for section2(13) and section2(14); foreign-only uses the same other state as its duty premise',
        'history_time': 'Prior history at evaluation for current ability to choose, not at an earlier German choice',
        'effective_choice': 'Hypothetical effective German or other EU/EEA choice at evaluation; foreign law and actual compliance not determined',
        'automatic_publication': 'Section5 publication duty is not modeled as constitutive for section2(13)1(a)',
        'route_failure': 'Other routes remain open; no NEITHER or foreign-state inference from failed German route'}


def metadata(profile):
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': profile['products_sha256'], 'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'context': deepcopy(profile['context']), 'selected_interpretation': None,
        'actual_home_state_established': False, 'historical_application_proved': False,
        'complete_legal_test': False,
        'scope': 'Conditional automatic/provisional German routes feeding issuer/publication analysis; unresolved alternative home states remain open'}


def policy(ordinary, profile, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['ordinary_answer_sha256'] != digest(ordinary) or KEY in ordinary
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Pinned complete prior answer and home-route profile required')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError('One to64 conditional home-route cases required')
    cases = {r['id']: r for r in ordinary[issuer.KEY]['scenarios']}
    ids = set()
    for row in rows:
        keys = {'id', 'kind', 'base_case', 'route', 'facts'}; fields(row, keys, keys)
        if (not isinstance(row['id'], str) or not row['id'] or row['id'] in ids
                or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT' or row['base_case'] not in cases):
            raise ValueError('Distinct hypothetical home-route case and existing issuer case required')
        ids.add(row['id']); analyze(row['route'], row['facts'])
    if (rows[0]['id'] != 'all-open' or rows[0]['base_case'] != 'all-open'
            or any(v is not None for v in rows[0]['facts'].values())):
        raise ValueError('All-open conditional home-route baseline required')
    return cases


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    cases = policy(ordinary, profile, expected_profile_sha256)
    if profile['products_sha256'] != digest(products) or profile['context'] != context(ordinary, root):
        raise ValueError('Complete products or home-route source context changed')
    rows = []
    for row in profile['scenarios']:
        route = analyze(row['route'], row['facts']); base = cases[row['base_case']]
        qualification = deepcopy(base['qualification'])
        qualification['home_state'] = election.derived_home(route['statuses']['german_route'])
        qualification['admission_scope'] = derived_admission(row['facts']['admission_at_evaluation'])
        q = issuer.qualify(qualification)
        derived = deepcopy(base['derived_publication_scenario']); derived['id'] = row['id']
        derived['premises']['inlandsemittent_qualified'] = publication.VALUE[q['status']]
        result = publication.analyze(derived, products['P1']['payload']['request']['bundle']['instrument_id'])
        decisions = issuer.decisions(result)
        rows.append({**deepcopy(row), 'route_result': route, 'derived_qualification': qualification,
            'qualification_result': q, 'derived_publication_scenario': derived,
            'publication_decisions': decisions, 'baseline_decisions': deepcopy(base['publication_decisions']),
            'answer_changed': decisions != base['publication_decisions']})
    return {KEY: {**metadata(profile), 'scenarios': rows}}
