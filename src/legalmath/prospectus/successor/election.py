"""Conditional continuing German-election route; no actual home-state finding."""
from copy import deepcopy
from itertools import product
import json

from .. import publication_routes as publication
from . import issuer_qualification as issuer
from .anchors import fields
from .contracts import bound_path, digest

VERSION = 'basf-election.v1'
KEY = 'election_review'
ROUTES = ('SECTION2_13_1B', 'SECTION2_13_2')
PRIOR = ('NO_PRIOR_OTHER', 'PRIOR_OTHER_ADMISSION_CEASED',
         'PRIOR_OTHER_CONTINUES_NO_CHOICE_WITHIN_THREE_YEARS',
         'PRIOR_OTHER_CONTINUES_CHOICE_WITHIN_THREE_YEARS')
ADMISSION = ('GERMANY_ONLY', 'GERMANY_AND_OTHER_EU_EEA', 'OTHER_EU_EEA_ONLY', 'NONE')
FLAGS = ('category_satisfied', 'germany_choice_made', 'publication_under_section5',
         'reading_applies', 'new_home_choice_made')
EXTRA = ('germany_choice_at_least_three_years', 'category1_admitted_issuance')
SOURCE = 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-102/'
FILES = {
    'requests/section4/body': '1df8e134eca069af252d522c3609f88587043530732478029a826bd73226771d',
    'requests/section4/receipt.json': 'd22e10d3ed82cb144c8d6d3d137dc774507e4c1df22637eed0116cb2748a3757',
    'local/section4/text.txt': '246941a3aefef985da4c548422b70980afd6576df33e51877774fc556d10f082',
    'requests/section5/body': '8f3b6bdcbfd051f474b3f182480e2832b89239bdafe4323eeb4a310ba2a29cff',
    'requests/section5/receipt.json': '64d7b6c1dd159aa2f938e98bd783b43355775568606aea06097dadbdb96e1d57',
    'local/section5/text.txt': 'f14488e3788f21d1a66d065fd9fb91615faa8059bd798d83fc789e557edd348a',
}


def domains(route):
    if route not in ROUTES: raise ValueError('Explicit supported section2(13) election route required')
    return {**{k: (False, True) for k in FLAGS + (EXTRA if route == ROUTES[1] else ())},
            'prior_election_at_choice': PRIOR, 'admission_at_evaluation': ADMISSION}


def world(route, f):
    permitted_history = f['prior_election_at_choice'] in PRIOR[:2 if route == ROUTES[0] else 3]
    eligible = f['category_satisfied'] and permitted_history
    admission = f['admission_at_evaluation']
    if route == ROUTES[0]:
        replacement = admission == 'OTHER_EU_EEA_ONLY'
        expired = admission == 'NONE' or (replacement and f['new_home_choice_made'])
    else:
        replacement = admission in ('GERMANY_AND_OTHER_EU_EEA', 'OTHER_EU_EEA_ONLY') and (
            admission == 'OTHER_EU_EEA_ONLY' or f['germany_choice_at_least_three_years'])
        expired = (f['category1_admitted_issuance'] or admission == 'NONE'
                   or (replacement and f['new_home_choice_made']))
    return {'initial_permission': eligible, 'replacement_condition': replacement,
            'choice_expired': expired,
            'continuing_german_route': eligible and f['germany_choice_made']
            and f['publication_under_section5'] and f['reading_applies'] and not expired}


def analyze(route, facts):
    supported = domains(route); fields(facts, supported, supported)
    for key, values in supported.items():
        value = facts[key]
        if value is None or value == 'conflict': continue
        if values == (False, True):
            if type(value) is not bool: raise ValueError('Election premise must be Boolean, unknown or conflict')
        elif not isinstance(value, str) or value not in values:
            raise ValueError('Explicit supported election category required')
    missing = sorted(k for k, v in facts.items() if v is None)
    conflicts = sorted(k for k, v in facts.items() if v == 'conflict')
    names = ('initial_permission', 'replacement_condition', 'choice_expired', 'continuing_german_route')
    if conflicts:
        return {'statuses': dict.fromkeys(names, 'CONFLICT'), 'missing': missing, 'conflicts': conflicts}
    outcomes = {k: set() for k in names}
    for values in product(*(d if facts[k] is None else (facts[k],) for k, d in supported.items())):
        for key, value in world(route, dict(zip(supported, values))).items(): outcomes[key].add(value)
    return {'statuses': {k: 'YES' if v == {True} else 'NO' if v == {False} else 'UNKNOWN'
                         for k, v in outcomes.items()}, 'missing': missing, 'conflicts': conflicts}


def derived_home(status):
    if status not in ('YES', 'NO', 'UNKNOWN', 'CONFLICT'): raise ValueError('Supported route status required')
    # Other/default/automatic home-state routes remain unevaluated.
    return 'GERMANY' if status == 'YES' else 'conflict' if status == 'CONFLICT' else None


def context(ordinary, root):
    prior = ordinary.get(issuer.KEY)
    if not isinstance(prior, dict) or prior.get('version') != issuer.VERSION:
        raise ValueError('Existing complete issuer qualification required')
    if prior['context'] != issuer.source_context(ordinary, root):
        raise ValueError('Existing issuer source context changed')
    for name, checksum in FILES.items():
        if digest(bound_path(root, SOURCE + name).read_bytes()) != checksum:
            raise ValueError('Complete election source or acquisition receipt changed')
    for key in ('section4', 'section5'):
        receipt = json.loads(bound_path(root, SOURCE + 'requests/' + key + '/receipt.json').read_bytes())
        if receipt.get('curl_exit_code') != 0 or receipt.get('http_status') != 200 or receipt.get('status') != 'RETAINED':
            raise ValueError('Complete successful official election acquisition required')
    return {'source_files': {SOURCE + n: h for n, h in FILES.items()},
        'complete_section4': bound_path(root, SOURCE + 'local/section4/text.txt').read_text(),
        'complete_section5': bound_path(root, SOURCE + 'local/section5/text.txt').read_text(),
        'prior_issuer_context': deepcopy(prior['context']),
        'sections4_and5': 'COMPLETE_DISPLAYED_PROVISIONS_RETAINED_IN_SOURCE102',
        'displayed_law_temporal_applicability': 'NOT_ESTABLISHED',
        'implementing_rules': 'NOT_RETRIEVED', 'actual_issuer_facts': 'NOT_ESTABLISHED',
        'publication_premise': 'Hypothetical publication satisfying section5 and applicable detailed rules; additional notification duties not independently made effectiveness conditions',
        'prior_time': 'Prior history at the German choice; within-three-years classification is supplied',
        'evaluation_time': 'Admission and termination facts at the hypothetical evaluation time; no computed anniversary',
        'new_choice_premise': 'Qualifying new choice subject to the modeled section4 replacement conditions; other requirements supplied',
        'route_failure': 'No negative home-state inference: automatic/default and other-state routes remain open'}


def metadata(profile):
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': profile['products_sha256'], 'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'context': deepcopy(profile['context']), 'selected_interpretation': None,
        'actual_home_state_established': False, 'historical_application_proved': False,
        'complete_legal_test': False,
        'scope': 'Conditional section4 continuing German-election route feeds hypothetical issuer/publication analysis; no complete home-state classification'}


def policy(ordinary, profile, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['ordinary_answer_sha256'] != digest(ordinary) or KEY in ordinary
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Pinned complete prior answer and election profile required')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError('One to64 conditional election cases required')
    cases = {r['id']: r for r in ordinary[issuer.KEY]['scenarios']}
    ids = set()
    for row in rows:
        keys = {'id', 'kind', 'base_case', 'route', 'facts'}; fields(row, keys, keys)
        if (not isinstance(row['id'], str) or not row['id'] or row['id'] in ids
                or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT' or row['base_case'] not in cases):
            raise ValueError('Distinct hypothetical election case and existing issuer case required')
        ids.add(row['id']); analyze(row['route'], row['facts'])
    if (rows[0]['id'] != 'all-open' or rows[0]['base_case'] != 'all-open'
            or any(v is not None for v in rows[0]['facts'].values())):
        raise ValueError('All-open conditional election baseline required')
    return cases


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    cases = policy(ordinary, profile, expected_profile_sha256)
    if profile['products_sha256'] != digest(products) or profile['context'] != context(ordinary, root):
        raise ValueError('Complete election products or source context changed')
    rows = []
    for row in profile['scenarios']:
        route = analyze(row['route'], row['facts']); base = cases[row['base_case']]
        qualification = deepcopy(base['qualification'])
        qualification['home_state'] = derived_home(route['statuses']['continuing_german_route'])
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
