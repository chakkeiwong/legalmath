"""Prepare and check current H1 wrapper bindings; no new source interpretation."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PROFILE_FILES = {
    'cash': BASE / 'attempt-007/cash-flow-profile.json',
    'risk': BASE / 'attempt-007/risk-profile.json',
    'scope': BASE / 'attempt-007/profile.json',
    'unit': AUTH / 'reviews/h1-unit-212/profile.json',
}
REVIEW_KEYS = {'cash': 'cash_flow_review', 'risk': 'risk_table_review',
               'scope': 'h1_scope_review', 'unit': 'h1_individual_unit_review'}
EXPLANATION_KEYS = {'cash': 'cash_flow_explanation', 'risk': 'risk_table_explanation',
                   'scope': 'h1_scope_explanation', 'unit': 'h1_individual_unit_explanation'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def modules():
    from legalmath.prospectus import h1_cash_flow, h1_risk_tables, h1_incorporation_scope, h1_unit_conflict
    return {'cash': h1_cash_flow, 'risk': h1_risk_tables,
            'scope': h1_incorporation_scope, 'unit': h1_unit_conflict}


def historical_components():
    old = read(BASE / 'attempt-007/scope-consumer.json.gz')
    old.update(read(BASE / 'attempt-017/answer-delta.json.gz'))
    return {key: old[key] for key in (*REVIEW_KEYS.values(), *EXPLANATION_KEYS.values())}


def substantive_review(value):
    # Only these two root fields describe changed preceding-answer bindings.
    # Graph identity, source, scope and every substantive/nested field must agree.
    return {key: child for key, child in value.items() if key not in ('prior_sha256', 'profile_sha256')}


def original_unit_input():
    return {**read(BASE / 'attempt-016/profile.json'),
            'full_units': read(BASE / 'attempt-016/source-units.json')}


def prepare_profiles(graph, inner):
    from legalmath.prospectus.successor.contracts import digest
    from scripts.prospectus_h1_unit_oracle import verify
    implementations = modules()
    old = historical_components()
    profiles = {}
    previous = inner
    proofs = []
    for name in ('cash', 'risk', 'scope', 'unit'):
        original = read(PROFILE_FILES[name])
        require(original['graph_sha256'] == digest(graph), 'Original wrapper graph changed: ' + name)
        profile = deepcopy(original)
        profile['prior_sha256'] = digest(previous)
        require({k: v for k, v in profile.items() if k != 'prior_sha256'} ==
                {k: v for k, v in original.items() if k != 'prior_sha256'},
                'Unexpected historical profile change: ' + name)
        require(profile['prior_sha256'] != original['prior_sha256'],
                'Expected actual current preceding-answer binding: ' + name)
        implementation = implementations[name]
        review = implementation.evaluate(graph, previous, profile, ROOT, expected_profile_sha256=digest(profile))
        explanation = implementation.explain(review)
        require(substantive_review(review) == substantive_review(old[REVIEW_KEYS[name]]),
                'Historical substantive component differs: ' + name)
        require(explanation == old[EXPLANATION_KEYS[name]], 'Historical explanation differs: ' + name)
        proof = {'component': name, 'prior_sha256': digest(previous),
                 'profile_sha256': digest(profile), 'historical_substantive_reading_preserved': True}
        if name == 'unit':
            proof['independent_dimensional_checker'] = verify(
                review, explanation, profile, graph, previous, original_unit_input(), ROOT)
        previous = ({'answer': previous} if name == 'cash' else previous) | {
            REVIEW_KEYS[name]: review, EXPLANATION_KEYS[name]: explanation}
        profiles[name] = profile
        proofs.append(proof)
    return profiles, previous, proofs


def consume(products, profiles, pins=None):
    from legalmath.prospectus import h1_incorporation_scope
    from legalmath.prospectus.successor.contracts import digest
    if pins is None:
        pins = {name: digest(value) for name, value in profiles.items()}
    return h1_incorporation_scope.consume(
        products, profiles['cash'], profiles['risk'], profiles['scope'], ROOT,
        expected_cash_profile_sha256=pins['cash'], expected_risk_profile_sha256=pins['risk'],
        expected_profile_sha256=pins['scope'], unit_profile=profiles['unit'],
        expected_unit_profile_sha256=pins['unit'])


def check_answer(answer, inner, graph, profiles, expected=None):
    from legalmath.prospectus.successor.contracts import digest
    from scripts.prospectus_h1_unit_oracle import verify
    keys = {'answer', *REVIEW_KEYS.values(), *EXPLANATION_KEYS.values()}
    require(set(answer) == keys, 'Complete combined wrapper field inventory required')
    require(answer['answer'] == inner, 'Complete current inner answer changed')
    if expected is not None:
        require(answer == expected, 'Actual public call differs from prepared component result')
    old = historical_components()
    previous = inner
    for name in ('cash', 'risk', 'scope', 'unit'):
        profile = profiles[name]
        review, explanation = answer[REVIEW_KEYS[name]], answer[EXPLANATION_KEYS[name]]
        require(profile['graph_sha256'] == digest(graph) and profile['prior_sha256'] == digest(previous),
                'Profile bound to wrong graph or preceding answer: ' + name)
        require(review['graph_sha256'] == digest(graph) and review['prior_sha256'] == digest(previous)
                and review['profile_sha256'] == digest(profile), 'Current review binding differs: ' + name)
        require(substantive_review(review) == substantive_review(old[REVIEW_KEYS[name]])
                and explanation == old[EXPLANATION_KEYS[name]], 'Retained component changed: ' + name)
        if name == 'unit':
            verify(review, explanation, profile, graph, previous, original_unit_input(), ROOT)
        previous = ({'answer': previous} if name == 'cash' else previous) | {
            REVIEW_KEYS[name]: review, EXPLANATION_KEYS[name]: explanation}
    require(previous == answer, 'Combined answer has unaccounted fields')
    require(not inner['may_execute_transaction'] and not inner['independent_legal_acceptance']
            and inner['questions']['Q3']['status'] == 'PARTIAL', 'Original answer limits changed')
    return {'complete_current_inner_preserved': True, 'all_four_current_bindings_verified': True,
        'historical_substantive_components_preserved': True, 'unit_dimensional_checker_passed': True,
        'all_fields_accounted_for': True, 'source_truth_established': False,
        'general_automatic_interpretation': False, 'original_task_complete': False}


CASES = ('stale-cash', 'stale-risk', 'stale-scope', 'stale-unit',
         'cash-unit', 'risk-validation', 'scope-selection', 'unit-column',
         'changed-scope-pin', 'missing-unit-profile')

REFUSALS = {
    'stale-cash': 'Pinned H1 profile, graph or complete previous answer changed',
    'stale-risk': 'Pinned risk profile, graph or complete previous consumer changed',
    'stale-scope': 'Pinned H1 scope profile, graph or complete prior consumer changed',
    'stale-unit': 'H1 unit profile, graph or full previous answer changed',
    'cash-unit': 'Original six-month periods and thousand-euro unit required',
    'risk-validation': 'Risk reading cannot validate accounts or select legal incorporation',
    'scope-selection': 'Conditional scope cannot establish legal selection, financial validation or source authority',
    'unit-column': 'Complete ordered original unit columns and headers required',
    'changed-scope-pin': 'Pinned H1 scope profile, graph or complete prior consumer changed',
    'missing-unit-profile': 'H1 unit profile missing for supplied identity',
}


def adverse_profiles(profiles, name):
    from legalmath.prospectus.successor.contracts import digest
    require(name in CASES, 'Unknown combined-consumer corruption')
    changed = deepcopy(profiles)
    pins = None
    if name.startswith('stale-'):
        key = name.removeprefix('stale-')
        changed[key] = read(PROFILE_FILES[key])
    elif name == 'cash-unit':
        require(changed['cash']['unit'] == 'thousand EUR', 'Existing cash unit required')
        changed['cash']['unit'] = 'million EUR'
    elif name == 'risk-validation':
        require(changed['risk']['financial_values_validated'] is False, 'Existing risk limitation required')
        changed['risk']['financial_values_validated'] = True
    elif name == 'scope-selection':
        require(changed['scope']['limits']['selected_reading'] is None, 'Existing unresolved scope required')
        changed['scope']['limits']['selected_reading'] = 'overall-range'
    elif name == 'unit-column':
        require(changed['unit']['pages'][0]['columns'][3] == '2009-06-30 net', 'Existing June comparative required')
        changed['unit']['pages'][0]['columns'][3] = '2009-12-31 net'
    elif name == 'changed-scope-pin':
        pins = {key: digest(value) for key, value in changed.items()}
        pins['scope'] = '0' * 64
    else:
        pins = {key: digest(value) for key, value in changed.items()}
        changed['unit'] = None
    require(changed != profiles or pins is not None, 'Actual corruption required')
    return changed, pins
