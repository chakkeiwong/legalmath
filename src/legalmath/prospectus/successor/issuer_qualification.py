"""Conditional WpHG2(14) issuer status feeding the existing publication analysis."""
from copy import deepcopy
from itertools import product
import json

from .. import publication_routes as publication
from .anchors import fields
from .contracts import bound_path, digest

VERSION = 'basf-issuer-qualification.v1'
KEY = 'issuer_qualification_review'
HOME = ('GERMANY', 'OTHER_EU_EEA', 'NEITHER')
ADMISSION = ('ONLY_GERMANY_ORGANISED', 'ONLY_OTHER_EU_EEA', 'NEITHER_EXCLUSIVE')
SOURCE = 'docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-098/'
FILES = {
    'requests/issuer-definition/body': '407a90f6bc28654a7ebef0c761dfaca98b2fc80766e20998e33118e93b87f0b8',
    'requests/issuer-definition/receipt.json': '4505ad9cc8c501ccd8a4ae58d798b3246924718892f0875b378cc7c866c2a8c6',
    'local/issuer-definition/text.txt': '627dc7a42f6c703f0507df1507e98a00a53ba8d7441bf0aa12cba66be4191888',
}
FACTS = ('home_state', 'admission_scope', 'foreign_transparency_duties')


def qualify(facts):
    fields(facts, FACTS, FACTS)
    for key, domain in (('home_state', HOME), ('admission_scope', ADMISSION)):
        if facts[key] is not None and facts[key] not in (*domain, 'conflict'):
            raise ValueError('Explicit supported issuer category required')
    value = facts['foreign_transparency_duties']
    if value is not None and value != 'conflict' and type(value) is not bool:
        raise ValueError('Foreign transparency duty is Boolean, unknown or conflict')
    missing = [k for k in FACTS if facts[k] is None]
    conflicts = [k for k in FACTS if facts[k] == 'conflict']
    if conflicts: return {'status': 'CONFLICT', 'missing': missing, 'conflicts': conflicts}
    domains = (HOME, ADMISSION, (False, True))
    outcomes = set()
    for home, admission, duty in product(*(d if facts[k] is None else (facts[k],) for k, d in zip(FACTS, domains))):
        german_route = home == 'GERMANY' and not (admission == 'ONLY_OTHER_EU_EEA' and duty)
        other_route = home == 'OTHER_EU_EEA' and admission == 'ONLY_GERMANY_ORGANISED'
        outcomes.add(german_route or other_route)
    status = 'YES' if outcomes == {True} else 'NO' if outcomes == {False} else 'UNKNOWN'
    return {'status': status, 'missing': missing, 'conflicts': conflicts}


def source_context(ordinary, root):
    previous = ordinary.get('publication_routes_review')
    if not isinstance(previous, dict) or previous.get('version') != publication.VERSION:
        raise ValueError('Existing complete publication review required')
    context = previous['context']
    if context.get('historical_application') != 'NOT_ESTABLISHED' or context.get('implementing_rules') != 'NOT_RETRIEVED':
        raise ValueError('Retained publication source uncertainties required')
    for name, checksum in FILES.items():
        if digest(bound_path(root, SOURCE + name).read_bytes()) != checksum:
            raise ValueError('Pinned complete issuer source changed')
    for item in context['source_files'].values():
        if digest(bound_path(root, item['path']).read_bytes()) != item['sha256']:
            raise ValueError('Retained section50 source changed')
    receipt = json.loads(bound_path(root, SOURCE + 'requests/issuer-definition/receipt.json').read_bytes())
    if receipt.get('http_status') != 200 or receipt.get('status') != 'RETAINED':
        raise ValueError('Retained complete official definition response required')
    text = bound_path(root, SOURCE + 'local/issuer-definition/text.txt').read_text()
    if '(14) Inlandsemittenten sind 1.' not in text or '(13) Emittenten' not in text:
        raise ValueError('Complete definition and home-state dependencies required')
    return {'source_files': {SOURCE + n: h for n, h in FILES.items()},
        'complete_current_section2': text, 'retained_publication_context': deepcopy(context),
        'historical_application': 'NOT_ESTABLISHED', 'election_effectiveness': 'NOT_ESTABLISHED',
        'sections4_and5': 'UNAVAILABLE_IN_SOURCE099', 'implementing_rules': 'NOT_RETRIEVED',
        'issuer_admission_scope': 'All issuer securities relevant to section2(14); not merely this issue',
        'foreign_duty_scope': 'Publication and notification duties under Directive2004/109/EC in the same other EU/EEA state',
        'home_state_scope': 'Supplied hypothetical category; section2(13), sections4/5 and foreign election rules are not resolved',
        'admission_scope': 'ONLY_OTHER_EU_EEA includes no German admission; NEITHER_EXCLUSIVE includes mixed admission and asserts neither exclusive case'}


def policy(ordinary, profile, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['ordinary_answer_sha256'] != digest(ordinary) or KEY in ordinary
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})):
        raise ValueError('Pinned complete prior answer and issuer profile required')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError('One to64 conditional issuer cases required')
    cases = {r['scenario']['id']: r['scenario'] for r in ordinary['publication_routes_review']['scenarios']}
    ids = set()
    for row in rows:
        fields(row, {'id', 'base_case', 'qualification'}, {'id', 'base_case', 'qualification'})
        if not isinstance(row['id'], str) or not row['id'] or row['id'] in ids or row['base_case'] not in cases:
            raise ValueError('Distinct issuer case and existing publication case required')
        ids.add(row['id']); qualify(row['qualification'])
    if (rows[0]['id'] != 'all-open' or rows[0]['base_case'] != 'all-open'
            or any(v is not None for v in rows[0]['qualification'].values())):
        raise ValueError('All-open conditional baseline required')
    return cases


def decisions(result):
    return {'qualified_information': result['qualified_information']['status'],
        'statutory_conditions': result['statutory_conditions']['status'],
        'german_seat_routes': {k: v['status'] for k, v in result['german_seat_routes'].items()},
        'conditional_contract_readings': {k: v['status'] for k, v in result['conditional_contract_readings'].items()}}


def metadata(profile):
    return {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': profile['products_sha256'], 'ordinary_answer_sha256': profile['ordinary_answer_sha256'],
        'context': deepcopy(profile['context']), 'selected_interpretation': None,
        'actual_issuer_qualification_established': False, 'historical_application_proved': False,
        'complete_legal_test': False,
        'scope': 'Hypothetical section2(14) qualification feeds existing conditional publication readings; no election-law or actual issuer determination'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    cases = policy(ordinary, profile, expected_profile_sha256)
    if profile['products_sha256'] != digest(products) or profile['context'] != source_context(ordinary, root):
        raise ValueError('Bound complete products or issuer sources changed')
    rows = []
    for row in profile['scenarios']:
        q = qualify(row['qualification']); base = cases[row['base_case']]
        derived = deepcopy(base); derived['id'] = row['id']
        derived['premises']['inlandsemittent_qualified'] = publication.VALUE[q['status']]
        result = publication.analyze(derived, products['P1']['payload']['request']['bundle']['instrument_id'])
        old = publication.analyze(base, products['P1']['payload']['request']['bundle']['instrument_id'])
        rows.append({**deepcopy(row), 'qualification_result': q, 'derived_publication_scenario': derived,
            'publication_decisions': decisions(result), 'baseline_decisions': decisions(old),
            'answer_changed': decisions(result) != decisions(old)})
    return {KEY: {**metadata(profile), 'scenarios': rows}}
