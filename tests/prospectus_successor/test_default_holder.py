"""Discriminating authority controls and independent finite consequence checks."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

import pytest
from legalmath.prospectus.successor import default_holder as candidate
from legalmath.prospectus.successor import default_holder_verify as oracle
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/default-holder-362'


def test_all_fully_specified_worlds_against_separate_boolean_encoding():
    names = sorted(candidate.premises())
    for values in product((False, True), repeat=len(names)):
        facts = dict(zip(names, values))
        row = candidate.analyze({'id': 'world', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': facts})
        assert row['readings'] == {k: oracle.consequence(k, facts) for k in oracle.EVENT_NAMES}


def test_declared_source_controls_and_four_valued_authority():
    profile = json.loads((PREP / 'profile.json').read_text())
    expected = json.loads((PREP / 'expected.json').read_text())['statuses']
    for case in profile['scenarios']:
        actual = candidate.analyze(case)
        assert [v['status'] for v in actual['readings'].values()] == expected[case['id']]
        assert actual['readings'] == {k: oracle.consequence(k, case['facts']) for k in oracle.EVENT_NAMES}


@pytest.mark.parametrize('value', [0, 1, 'yes', 'false', [], {}, 1.5])
def test_truthy_nonboolean_facts_refused(value):
    with pytest.raises(ValueError):
        candidate.analyze({'id': 'bad', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': {'entrusted': value}})


@pytest.mark.parametrize('key', ['notice', 'representative_appointed', 'actual_default', 'expected'])
def test_bundled_legacy_notice_and_appointment_are_not_authority_facts(key):
    with pytest.raises(ValueError):
        candidate.analyze({'id': 'bad', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'facts': {key: True}})


@pytest.fixture
def packet():
    profile = json.loads((PREP / 'profile.json').read_text())
    sources = deepcopy(profile['sources'])
    sources[0]['images'].pop()
    ordinary = {'question': 'Unresolved', 'default_f_review': {
        'selected_reading': None, 'candidate_set_exhaustive': False, 'governing_language': 'German',
        'source_meaning_promoted': False, 'sources': sources,
        'groups': {k: v for k, v in profile['groups'].items() if k != 'representative'}}}
    ordinary['report_sha256'] = digest(ordinary)
    profile['ordinary_answer_sha256'] = digest(ordinary)
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body[candidate.KEY] = {**candidate.metadata(profile),
        'scenarios': [candidate.analyze(s) for s in profile['scenarios']]}
    answer = {**body, 'report_sha256': digest(body)}
    return ordinary, profile, answer


def test_separate_verifier_preserves_complete_comparator(packet):
    ordinary, profile, answer = packet
    assert oracle.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))['status'] == 'PASS'


@pytest.mark.parametrize('kind', ['status', 'missing', 'conflict', 'scenario-drop', 'scenario-facts',
    'comparison', 'actual-authority', 'selection', 'exhaustive', 'source', 'ordinary', 'extra'])
def test_rehashed_corrupt_answers_refused(packet, kind):
    ordinary, profile, answer = packet
    review = answer[candidate.KEY]
    first = review['scenarios'][0]
    if kind == 'status': first['readings']['both_conducts']['status'] = 'YES'
    elif kind == 'missing': first['readings']['both_conducts']['missing'] = []
    elif kind == 'conflict': first['readings']['both_conducts']['conflicts'] = ['entrusted']
    elif kind == 'scenario-drop': review['scenarios'].pop()
    elif kind == 'scenario-facts': first['facts']['entrusted'] = False
    elif kind == 'comparison': first['comparison'] = 'ALL_ENUMERATED_YES'
    elif kind == 'actual-authority': review['actual_holder_authority_established'] = True
    elif kind == 'selection': review['selected_reading'] = 'both_conducts'
    elif kind == 'exhaustive': review['candidate_set_exhaustive'] = True
    elif kind == 'source': review['groups']['representative'][0]['selected_text'] += ' changed'
    elif kind == 'ordinary': answer['question'] = 'Established'
    else: review['unverified'] = True
    answer['report_sha256'] = digest({k: v for k, v in answer.items() if k != 'report_sha256'})
    with pytest.raises(ValueError):
        oracle.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))


@pytest.mark.parametrize('kind', ['expression', 'premise', 'source', 'image-page', 'image-missing',
    'source-missing', 'scenario-duplicate', 'too-many', 'actual-kind', 'baseline', 'role', 'extra'])
def test_rehashed_profile_tampering_refused(packet, kind):
    ordinary, profile, _ = packet
    if kind == 'expression': profile['expressions']['both_conducts'] = True
    elif kind == 'premise': profile['premises']['entrusted']['meaning'] = 'Representative appointed'
    elif kind == 'source': profile['groups']['german_f'][0]['source']['quote'] += ' altered'
    elif kind == 'image-page': profile['sources'][0]['images'][-1]['page'] = 128
    elif kind == 'image-missing': profile['sources'][0]['images'].pop()
    elif kind == 'source-missing': profile['sources'] = []
    elif kind == 'scenario-duplicate': profile['scenarios'].append(profile['scenarios'][0])
    elif kind == 'too-many': profile['scenarios'] *= 3
    elif kind == 'actual-kind': profile['scenarios'][0]['kind'] = 'ACTUAL'
    elif kind == 'baseline': profile['ordinary_answer_sha256'] = '0' * 64
    elif kind == 'role': profile['groups']['german_f'][0]['assembly_role'] = 'OPERATIVE'
    else: profile['actual_holder'] = True
    with pytest.raises(ValueError):
        candidate.policy(ordinary, profile, digest(profile))


def test_cli_loads_holder_profile_after_existing_options():
    from legalmath.prospectus.successor.conditional_profiles import load
    path = PREP / 'profiles.json'
    options = load(ROOT, str(path.relative_to(ROOT)), digest(path.read_bytes()))
    assert list(options)[-2:] == ['holder_authority_profile', 'expected_holder_authority_profile_sha256']
