"""Current complete-answer binding and independent conditional certificates."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from legalmath.prospectus import basf_default_f_current as current
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_current_default_controls import profile_controls
from scripts.prospectus_default_f_scenarios import EXPECTED
from scripts.prospectus_default_verifier import cases, recertified

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'docs/implementation/prospectus-execution-authority/reviews/current-default-alternatives-257'
REFERENCE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/basf-meanings/attempt-013'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


@pytest.fixture(scope='module')
def case():
    products, ordinary = read(PREP / 'products.json.gz'), read(PREP / 'ordinary-answer.json.gz')
    profile = read(REFERENCE / 'profile.json')
    profile.pop('prior_sha256')
    profile.update(version=current.VERSION, products_sha256=digest(products),
                   ordinary_answer_sha256=digest(ordinary))
    additions = current.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile))
    body = {k: v for k, v in {**ordinary, **additions}.items() if k != 'report_sha256'}
    return products, ordinary, profile, {**body, 'report_sha256': digest(body)}


def test_full_ordinary_preserved_and_all_conditional_questions_verified(case):
    _, ordinary, profile, answer = case
    assert current.verify_answer(answer, ordinary, profile,
                                 expected_profile_sha256=digest(profile))['checked_answers'] == 192
    assert answer['questions'] == ordinary['questions']
    assert answer['basf_agents'] == ordinary['basf_agents']
    for row in answer['default_f_review']['scenarios']:
        observed = ([r['modeled_f_exercise']['status'] for r in row['readings'].values()],
                    [r['bc_quorum_condition_at_receipt']['status'] for r in row['readings'].values()])
        assert observed == EXPECTED[row['id']]


@pytest.mark.parametrize('name', ['english-governs', 'selected-reading', 'exhaustive-reading-set',
                                 'independent-legal-acceptance', 'exercise-notice', 'receipt-quorum',
                                 'premise-time', 'numeric-boolean', 'missing-profile-pin'])
def test_repinning_cannot_promote_or_change_hypotheses(case, name):
    products, ordinary, profile, _ = case
    _, changed, pin = next(row for row in profile_controls(profile) if row[0] == name)
    with pytest.raises(ValueError):
        current.evaluate(products, ordinary, changed, ROOT, expected_profile_sha256=pin)


@pytest.mark.parametrize('change', ['ordinary', 'decision', 'reading', 'scope', 'certificate',
                                   'verification', 'hash', 'foreign-profile'])
def test_complete_answer_checker_refuses_forgery_even_after_report_rehash(case, change):
    _, ordinary, profile, original = case
    answer = deepcopy(original)
    if change == 'ordinary': answer['may_execute_transaction'] = True
    elif change == 'decision':
        answer['default_f_review']['scenarios'][0]['readings']['both_conducts']['event_at_exercise']['status'] = 'YES'
    elif change == 'reading': answer['default_f_review']['scenarios'][0]['readings'].pop('both_conducts')
    elif change == 'scope': answer['default_f_review']['actual_default_established'] = True
    elif change == 'certificate': answer['default_f_reasoning_certificate']['certificates'].pop()
    elif change == 'verification': answer['default_f_reasoning_verification']['checked_answers'] = 1
    elif change == 'foreign-profile':
        profile = {**profile, 'ordinary_answer_sha256': '0' * 64}
    answer['report_sha256'] = '0' * 64 if change == 'hash' else digest({k: v for k, v in answer.items() if k != 'report_sha256'})
    with pytest.raises(ValueError):
        current.verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))


def test_certificate_context_covers_the_entire_answer_before_certificates(case):
    _, ordinary, profile, answer = case
    review = answer['default_f_review']
    assert review['ordinary_answer_sha256'] == digest(ordinary)
    assert review['unresolved_default_f']['status'] == 'UNRESOLVED'
    assert all(r['assembly_role'] == 'UNKNOWN' for r in review['groups']['german_f'])
    assert review['selected_reading'] is None
    assert review['candidate_set_exhaustive'] is False
    assert answer['default_f_reasoning_verification']['source_meaning_proved'] is False


@pytest.mark.parametrize('name,path,value', cases())
def test_explanatory_forgeries_refused_after_public_recertification(case, name, path, value):
    _, ordinary, profile, answer = case
    if name == 'numeric-scenario-flag':
        # The independent checker already rejects this exact Boolean-type defect.
        with pytest.raises(ValueError):
            recertified(answer, ordinary, profile, name, path, value)
        return
    changed = recertified(answer, ordinary, profile, name, path, value)
    assert changed['default_f_reasoning_verification']['checked_answers'] == 192
    with pytest.raises(ValueError):
        current.verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))


@pytest.mark.parametrize('mutation', ['reviewer-independence', 'reviewer-basis',
                                    'version', 'extra-profile-field'])
def test_verification_also_enforces_profile_policy_after_repin_and_recertification(case, mutation):
    products, ordinary, original, answer = case
    profile = deepcopy(original)
    if mutation == 'reviewer-independence': profile['reviewer']['independent'] = True
    elif mutation == 'reviewer-basis': profile['reviewer']['basis'] = 'LEGAL_ACCEPTANCE'
    elif mutation == 'version': profile['version'] = 'unreviewed.v2'
    else: profile['unconditional_legal_approval'] = True
    with pytest.raises(ValueError):
        current.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile))
    forged = deepcopy(answer)
    forged['default_f_review']['profile_sha256'] = digest(profile)
    forged['default_f_review']['reviewer'] = deepcopy(profile['reviewer'])
    # Public certificate regeneration succeeds, so refusal must occur at the
    # complete-answer policy boundary rather than through a stale certificate.
    changed = recertified(forged, ordinary, profile, 'repin', ['profile_sha256'], digest(profile))
    with pytest.raises(ValueError):
        current.verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))


def test_boolean_lookalikes_do_not_equal_unchanged_ordinary_or_verification(case):
    _, ordinary, profile, answer = case
    for key in ('ordinary', 'verification'):
        changed = deepcopy(answer)
        if key == 'ordinary':
            assert changed['may_execute_transaction'] is False
            changed['may_execute_transaction'] = 0
        else:
            changed['default_f_reasoning_verification']['source_meaning_proved'] = 0
        changed['report_sha256'] = digest({k: v for k, v in changed.items() if k != 'report_sha256'})
        with pytest.raises(ValueError):
            current.verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))
