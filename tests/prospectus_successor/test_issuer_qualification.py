from itertools import product
import inspect
import pytest
from legalmath.prospectus.successor import issuer_qualification as model
from legalmath.prospectus.successor.issuer_qualification_verify import qualification, publication_decisions
from legalmath.prospectus import publication_routes


def test_all_one_hundred_categorical_and_open_inputs():
    count = 0
    for h, a, d in product((*model.HOME, None, 'conflict'),
                          (*model.ADMISSION, None, 'conflict'), (False, True, None, 'conflict')):
        row = dict(zip(model.FACTS, (h, a, d)))
        assert model.qualify(row) == qualification(row)
        count += 1
    assert count == 100


@pytest.mark.parametrize('home,admission,duty,expected', [
    ('GERMANY', 'ONLY_OTHER_EU_EEA', True, 'NO'),
    ('GERMANY', 'ONLY_OTHER_EU_EEA', False, 'YES'),
    ('GERMANY', 'ONLY_OTHER_EU_EEA', None, 'UNKNOWN'),
    ('GERMANY', 'NEITHER_EXCLUSIVE', None, 'YES'),
    ('OTHER_EU_EEA', 'ONLY_GERMANY_ORGANISED', None, 'YES'),
    ('OTHER_EU_EEA', 'NEITHER_EXCLUSIVE', False, 'NO'),
    ('NEITHER', None, None, 'NO'),
    (None, 'ONLY_GERMANY_ORGANISED', False, 'UNKNOWN'),
    ('NEITHER', 'ONLY_GERMANY_ORGANISED', 'conflict', 'CONFLICT'),
])
def test_source_specific_cases(home, admission, duty, expected):
    assert model.qualify(dict(zip(model.FACTS, (home, admission, duty))))['status'] == expected


@pytest.mark.parametrize('key,value', [('home_state', True), ('home_state', 'German seat'),
    ('admission_scope', []), ('admission_scope', 'ONLY_MTF'), ('foreign_transparency_duties', 1),
    ('foreign_transparency_duties', 'yes')])
def test_invalid_inputs_refused(key, value):
    facts = dict.fromkeys(model.FACTS); facts[key] = value
    with pytest.raises(ValueError): model.qualify(facts)


def test_extra_or_missing_fact_refused():
    with pytest.raises(ValueError): model.qualify({})
    with pytest.raises(ValueError): model.qualify({**dict.fromkeys(model.FACTS), 'german_seat': True})


def test_publication_independent_logic_matches_staged_consumer():
    base = dict.fromkeys(publication_routes.PREMISES, True)
    base.update(bundesanzeiger_publication=False, nonshare_terms_change_affecting_rights=False,
                relevant_third_country_information=False)
    for qualified, notice, implementing in product((True, False, None, 'conflict'), repeat=3):
        p = {**base, 'inlandsemittent_qualified': qualified, 'section13_notice_satisfied': notice,
             'implementing_rules_satisfied': implementing}
        row = {'id': 'conditional', 'kind': 'HYPOTHETICAL_DEVELOPMENT',
            'identity': {'instrument_id': 'i', 'issuer': 'issuer', 'resolution_id': 'r',
                         'security_kind': 'NONSHARE_BOND'}, 'premises': p}
        assert model.decisions(publication_routes.analyze(row, 'i')) == publication_decisions(p)


def test_optional_profile_reaches_existing_service_and_loader():
    from legalmath.prospectus.successor import service, conditional_profiles
    assert 'issuer_qualification_profile' in inspect.signature(service.consume).parameters
    assert 'issuer_qualification' in conditional_profiles.ORDER
    assert conditional_profiles.ORDER.index('holder_authority') < conditional_profiles.ORDER.index('issuer_qualification')
