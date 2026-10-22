from itertools import product
import inspect
import pytest
from legalmath.prospectus.successor import election as model, conditional_profiles, service
from legalmath.prospectus.successor.election_verify import expected


def example(route=model.ROUTES[0]):
    f = {k: False for k in model.domains(route)}
    for key in ('category_satisfied', 'germany_choice_made', 'publication_under_section5', 'reading_applies'):
        f[key] = True
    f.update(prior_election_at_choice='NO_PRIOR_OTHER', admission_at_evaluation='GERMANY_ONLY')
    return f


@pytest.mark.parametrize('route', model.ROUTES)
def test_all_complete_categorical_boolean_worlds(route):
    domains = model.domains(route)
    for values in product(*domains.values()):
        facts = dict(zip(domains, values))
        assert model.analyze(route, facts) == expected(route, facts)


@pytest.mark.parametrize('route', model.ROUTES)
def test_open_and_conflict_combinations(route):
    f = example(route)
    for values in product((False, True, None, 'conflict'), repeat=len(model.FLAGS)):
        f.update(zip(model.FLAGS, values))
        assert model.analyze(route, f) == expected(route, f)
    f = dict.fromkeys(model.domains(route))
    assert model.analyze(route, f) == expected(route, f)
    for key, domain in model.domains(route).items():
        for value in (*domain, 'conflict'):
            sample = {**f, key: value}
            assert model.analyze(route, sample) == expected(route, sample)


@pytest.mark.parametrize('route', model.ROUTES)
@pytest.mark.parametrize('admission', (*model.ADMISSION, None))
@pytest.mark.parametrize('history', (*model.PRIOR, None))
def test_categorical_uncertainty_composes_with_timing(route, admission, history):
    f = example(route); f.update(admission_at_evaluation=admission, prior_election_at_choice=history,
                                new_home_choice_made=None)
    if route == model.ROUTES[1]: f.update(germany_choice_at_least_three_years=None, category1_admitted_issuance=None)
    assert model.analyze(route, f) == expected(route, f)


def test_two_three_year_conditions_are_distinct():
    f = example(model.ROUTES[1])
    f.update(prior_election_at_choice=model.PRIOR[3], germany_choice_at_least_three_years=True)
    assert model.analyze(model.ROUTES[1], f)['statuses']['initial_permission'] == 'NO'
    f.update(prior_election_at_choice=model.PRIOR[2], germany_choice_at_least_three_years=False)
    assert model.analyze(model.ROUTES[1], f)['statuses']['initial_permission'] == 'YES'


def test_three_years_does_not_automatically_end_choice():
    f = example(model.ROUTES[1]); f.update(germany_choice_at_least_three_years=True,
                                         admission_at_evaluation='GERMANY_AND_OTHER_EU_EEA')
    result = model.analyze(model.ROUTES[1], f)['statuses']
    assert result['replacement_condition'] == 'YES' and result['choice_expired'] == 'NO'
    f['new_home_choice_made'] = True
    assert model.analyze(model.ROUTES[1], f)['statuses']['choice_expired'] == 'YES'


def test_german_delisting_still_needs_other_admission_and_new_choice():
    f = example(); f['admission_at_evaluation'] = 'OTHER_EU_EEA_ONLY'
    assert model.analyze(model.ROUTES[0], f)['statuses']['continuing_german_route'] == 'YES'
    f['new_home_choice_made'] = True
    assert model.analyze(model.ROUTES[0], f)['statuses']['continuing_german_route'] == 'NO'
    f.update(admission_at_evaluation='NONE', new_home_choice_made=False)
    assert model.analyze(model.ROUTES[0], f)['statuses']['choice_expired'] == 'YES'


def test_no_publication_never_becomes_effective_and_does_not_classify_other_routes():
    f = example(); f['publication_under_section5'] = False
    result = model.analyze(model.ROUTES[0], f)['statuses']
    assert result['initial_permission'] == 'YES' and result['continuing_german_route'] == 'NO'
    assert model.derived_home('NO') is None and model.derived_home('UNKNOWN') is None
    assert model.derived_home('CONFLICT') == 'conflict' and model.derived_home('YES') == 'GERMANY'


@pytest.mark.parametrize('value', [0, 1, '', [], {}, 'true'])
def test_implicit_boolean_rejected(value):
    f = example(); f['reading_applies'] = value
    with pytest.raises(ValueError): model.analyze(model.ROUTES[0], f)


def test_wrong_route_and_extra_notification_condition_rejected():
    with pytest.raises(ValueError): model.analyze('automatic', example())
    f = example(); f['bafin_notified'] = True
    with pytest.raises(ValueError): model.analyze(model.ROUTES[0], f)
    f = example(); f['admission_at_evaluation'] = 'German seat'
    with pytest.raises(ValueError): model.analyze(model.ROUTES[0], f)


def test_optional_normal_consumer_and_order():
    assert 'election_profile' in inspect.signature(service.consume).parameters
    assert conditional_profiles.ORDER.index('election') > conditional_profiles.ORDER.index('office_change')
