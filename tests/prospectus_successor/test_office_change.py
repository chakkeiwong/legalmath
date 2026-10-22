from copy import deepcopy
from itertools import product
import inspect
import pytest
from legalmath.prospectus import notice_delivery
from legalmath.prospectus.successor import office_change as model, service, conditional_profiles
from legalmath.prospectus.successor.office_change_verify import truth


def inputs(insolvency=False):
    identity = {'instrument_id': 'i', 'agent_id': 'a', 'change_event_id': 'e', 'notice_id': 'n'}
    notice = {'id': 'n-case', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'identity': identity,
        'route': 'PUBLICATION', 'convention': 'CIVIL_DATE_GAP',
        'event': {**identity, 'role': 'PUBLICATION_ON_LUX_EXCHANGE', 'value': '2026-01-01'},
        'proposed_change': {k:v for k,v in identity.items() if k != 'notice_id'},
        'premises': {'listed_in_lux': True, 'valid_route_event': True,
            'exchange_rules_permit': None, 'issuer_elects_substitution': None},
        'insolvency': insolvency, 'reading_applies': True}
    notice['proposed_change'].update(role='PROPOSED_CHANGE', value='2026-02-03')
    row = {'id': 'office', 'kind': 'HYPOTHETICAL_DEVELOPMENT', 'change_kind': 'OFFICE_REPLACEMENT',
        'identity': identity, 'notice_case': notice['id'], 'country_namespace': model.NAMESPACE,
        'original_country': 'COUNTRY_A', 'replacement_country': 'COUNTRY_A',
        'original_office_designated': True, 'replacement_office_designated': True, 'reading_applies': True}
    return row, notice_delivery.analyze(notice, 'i')


def test_full_five_premise_four_state_truth_table():
    names = ('notice', 'same_country', *model.FLAGS)
    for values in product((False, True, None, 'conflict'), repeat=5):
        assert model.conjunction(dict(zip(names, values)))['status'] == truth(values)


@pytest.mark.parametrize('a,b,expected', [
    ('A', 'A', True), ('A', 'B', False), (None, 'A', None), ('A', None, None),
    (None, None, None), ('conflict', None, 'conflict'), ('A', 'conflict', 'conflict')])
def test_country_identity(a, b, expected):
    assert model.same_country(a, b) == expected


@pytest.mark.parametrize('value', [True, False, 1, [], {}, '', ' A', 'A ', 'two countries'])
def test_invalid_country_identity(value):
    with pytest.raises(ValueError): model.same_country(value, 'A')


@pytest.mark.parametrize('country,expected', [('COUNTRY_A', 'YES'), ('COUNTRY_B', 'NO'),
                                            (None, 'UNKNOWN'), ('conflict', 'CONFLICT')])
@pytest.mark.parametrize('insolvency', [False, True])
def test_notice_success_does_not_waive_country(country, expected, insolvency):
    row, notice = inputs(insolvency); row['replacement_country'] = country
    result = model.analyze(row, notice, 'i')
    assert result['notice_precondition'] == 'YES'
    assert result['conditional_office_preconditions']['status'] == expected
    assert result['actual_change_effective'] == result['actual_office_designation'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize('key', model.FLAGS)
@pytest.mark.parametrize('value,expected', [(False, 'NO'), (None, 'UNKNOWN'), ('conflict', 'CONFLICT')])
def test_designation_and_reading_remain_explicit(key, value, expected):
    row, notice = inputs(); row[key] = value
    assert model.analyze(row, notice, 'i')['conditional_office_preconditions']['status'] == expected


@pytest.mark.parametrize('key', tuple(sorted(model.IDENTITY)))
def test_notice_identity_mismatch(key):
    row, notice = inputs(); row = deepcopy(row); row['identity'][key] = 'other'
    with pytest.raises(ValueError, match='identities differ'): model.analyze(row, notice, 'i')


@pytest.mark.parametrize('key,value', [('kind', 'ACTUAL'), ('change_kind', 'AGENT_APPOINTMENT'),
    ('country_namespace', 'inferred-country'), ('original_office_designated', 1), ('notice_case', 'other')])
def test_unsupported_or_implicit_premise_refused(key, value):
    row, notice = inputs(); row[key] = value
    with pytest.raises(ValueError): model.analyze(row, notice, 'i')


def test_changed_notice_result_is_reconstructed():
    row, notice = inputs(); notice['notice']['conditional_notice_precondition']['status'] = 'NO'
    with pytest.raises(ValueError, match='differs from its supplied scenario'): model.analyze(row, notice, 'i')


def test_extra_actual_address_is_not_admitted():
    row, notice = inputs(); row['actual_address'] = 'A dealer address'
    with pytest.raises(ValueError): model.analyze(row, notice, 'i')


def test_optional_api_and_cli_order():
    assert 'office_change_profile' in inspect.signature(service.consume).parameters
    assert 'office_change' in conditional_profiles.ORDER
    assert conditional_profiles.ORDER.index('issuer_qualification') < conditional_profiles.ORDER.index('office_change')
