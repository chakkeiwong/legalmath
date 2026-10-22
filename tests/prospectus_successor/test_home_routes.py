from itertools import product
import inspect
import pytest
from legalmath.prospectus.successor import home_routes as model, conditional_profiles, service
from legalmath.prospectus.successor.home_routes_verify import expected


def example(route=model.ROUTES[0]):
    facts = {'instrument_class': model.INSTRUMENT[0], 'seat': 'GERMANY',
             'admission_at_evaluation': 'GERMANY_ONLY', 'reading_applies': True}
    if route == model.ROUTES[1]:
        facts.update(seat='THIRD_COUNTRY', prior_election_at_evaluation='NO_PRIOR_OTHER',
                     effective_home_choice='NONE_EFFECTIVE')
    return facts


@pytest.mark.parametrize('route', model.ROUTES)
def test_all_complete_worlds_against_statutory_tables(route):
    domains = model.domains(route)
    for values in product(*domains.values()):
        facts = dict(zip(domains, values))
        assert model.analyze(route, facts) == expected(route, facts)


@pytest.mark.parametrize('route', model.ROUTES)
def test_missing_and_conflicting_categories(route):
    opened = dict.fromkeys(model.domains(route))
    assert model.analyze(route, opened) == expected(route, opened)
    for key, domain in model.domains(route).items():
        for value in (*domain, None, 'conflict'):
            for baseline in (opened, example(route)):
                facts = {**baseline, key: value}
                assert model.analyze(route, facts) == expected(route, facts)


@pytest.mark.parametrize('instrument', (*model.INSTRUMENT, None))
@pytest.mark.parametrize('seat', (*model.SEAT, None))
@pytest.mark.parametrize('admission', (*model.ADMISSION, None))
def test_uncertain_history_and_choice_preserve_structural_dependencies(instrument, seat, admission):
    facts = {**example(model.ROUTES[1]), 'instrument_class': instrument, 'seat': seat,
             'admission_at_evaluation': admission, 'prior_election_at_evaluation': None,
             'effective_home_choice': None}
    assert model.analyze(model.ROUTES[1], facts) == expected(model.ROUTES[1], facts)


def test_automatic_route_needs_no_choice_or_publication_input():
    facts = example()
    assert model.analyze(model.ROUTES[0], facts)['statuses']['german_route'] == 'YES'
    for extra in ('publication_under_section5', 'germany_choice_made', 'bafin_notified'):
        with pytest.raises(ValueError): model.analyze(model.ROUTES[0], {**facts, extra: False})
    facts['seat'] = 'OTHER_EU_EEA'
    assert model.analyze(model.ROUTES[0], facts)['statuses']['german_route'] == 'NO'


def test_category1_requires_third_country_for_provisional_route():
    facts = example(model.ROUTES[1])
    assert model.analyze(model.ROUTES[1], facts)['statuses']['german_route'] == 'YES'
    for seat in ('GERMANY', 'OTHER_EU_EEA'):
        assert model.analyze(model.ROUTES[1], {**facts, 'seat': seat})['statuses']['german_route'] == 'NO'


def test_foreign_only_admission_can_allow_choice_but_not_provisional_route():
    facts = {**example(model.ROUTES[1]), 'seat': 'GERMANY',
             'instrument_class': model.INSTRUMENT[1], 'admission_at_evaluation': 'OTHER_EU_EEA_ONLY'}
    result = model.analyze(model.ROUTES[1], facts)['statuses']
    assert result['permission_to_choose'] == 'YES' and result['german_route'] == 'NO'


def test_category1_and_category2_history_requirements_differ():
    facts = {**example(model.ROUTES[1]), 'prior_election_at_evaluation': model.HISTORY[2]}
    assert model.analyze(model.ROUTES[1], facts)['statuses']['german_route'] == 'NO'
    facts['instrument_class'] = model.INSTRUMENT[1]
    assert model.analyze(model.ROUTES[1], facts)['statuses']['german_route'] == 'YES'
    facts['prior_election_at_evaluation'] = model.HISTORY[3]
    assert model.analyze(model.ROUTES[1], facts)['statuses']['german_route'] == 'NO'


@pytest.mark.parametrize('choice', model.CHOICE[1:])
def test_any_effective_election_ends_provisional_route_without_negative_home_inference(choice):
    facts = {**example(model.ROUTES[1]), 'effective_home_choice': choice}
    result = model.analyze(model.ROUTES[1], facts)['statuses']
    assert result['german_route'] == 'NO' and model.election.derived_home(result['german_route']) is None


@pytest.mark.parametrize('value', [0, 1, '', [], {}, 'true'])
def test_implicit_boolean_rejected(value):
    with pytest.raises(ValueError): model.analyze(model.ROUTES[0], {**example(), 'reading_applies': value})


def test_unknown_category_wrong_route_and_history_time_rejected():
    with pytest.raises(ValueError): model.analyze('automatic', example())
    with pytest.raises(ValueError): model.analyze(model.ROUTES[0], {**example(), 'instrument_class': 'bond'})
    facts = example(model.ROUTES[1]); facts['prior_election_at_choice'] = facts.pop('prior_election_at_evaluation')
    with pytest.raises(ValueError): model.analyze(model.ROUTES[1], facts)


def test_admission_projection_is_shared_and_retains_uncertainty():
    assert model.derived_admission('OTHER_EU_EEA_ONLY') == 'ONLY_OTHER_EU_EEA'
    assert model.derived_admission('GERMANY_ONLY') == 'ONLY_GERMANY_ORGANISED'
    assert model.derived_admission(None) is None
    assert model.derived_admission('conflict') == 'conflict'


def test_optional_normal_consumer_and_order():
    assert 'home_routes_profile' in inspect.signature(service.consume).parameters
    assert conditional_profiles.ORDER.index('home_routes') > conditional_profiles.ORDER.index('election')
