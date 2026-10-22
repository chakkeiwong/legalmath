"""Discriminate finite-consequence correctness from assertions and legal scope."""
from copy import deepcopy
from itertools import product

import pytest

from legalmath.prospectus.reasoning_certificates import (
    expectation, check_result, certify, verify,
)
from legalmath.prospectus.default_f_certificates import model, READINGS, QUESTIONS
from legalmath.prospectus.successor.predicates import dispatch


FORMULAS = [True, False, 'a', {'not': 'a'}, {'all': ['a', 'b', 'c']},
            {'any': ['a', 'b', 'c']}, {'any': ['a', {'not': 'a'}]},
            {'all': ['a', {'not': 'a'}]},
            {'any': [{'all': ['a', {'not': 'b'}]}, 'c']},
            {'not': {'all': ['a', {'any': ['b', 'c']}]}}]


@pytest.mark.parametrize('expression', FORMULAS)
def test_exhaustive_small_domain_and_null_absence(expression):
    for values in product((False, True, None, 'conflict'), repeat=3):
        facts = dict(zip(('a', 'b', 'c'), values))
        result = dispatch(expression, facts)
        expected = check_result(expression, facts, result)
        absent = {k: v for k, v in facts.items() if v is not None}
        assert expected == expectation(expression, absent)
        assert result == dispatch(expression, absent)


def test_independently_known_counts_and_relevant_conflict_policy():
    expected = expectation({'any': ['a', {'not': 'a'}]}, {})
    assert (expected['status'], expected['true_worlds'], expected['false_worlds']) == ('YES', 2, 0)
    assert expectation({'all': ['a', {'not': 'a'}]}, {})['status'] == 'NO'
    assert expectation('a', {})['status'] == 'UNKNOWN'
    assert expectation(True, {'irrelevant': 'conflict'})['status'] == 'YES'
    assert expectation({'any': ['a', {'not': 'a'}]}, {'a': 'conflict'})['status'] == 'CONFLICT'


def test_twelve_fact_boundary_and_thirteenth_fact_refusal():
    for count in (12, 13):
        expression = {'all': ['f' + str(i) for i in range(count)]}
        result = dispatch(expression, {})
        check_result(expression, {}, result)
        if count == 12:
            assert result['worlds'] == 4096
        else:
            assert result['reason'] == 'DOMAIN_LIMIT'
            forged = {**result, 'status': 'YES'}
            with pytest.raises(ValueError):
                check_result(expression, {}, forged)


@pytest.mark.parametrize('mutation', ['formula', 'facts', 'status', 'decision', 'worlds',
                                    'witness', 'context', 'certificate', 'scope'])
def test_certificate_rejects_tampering(mutation):
    expression, facts, context = {'all': ['a', 'b']}, {'a': True}, {'source': 'expected-original'}
    result = dispatch(expression, facts)
    certificate = certify(expression, facts, result, context=context)
    assert verify(certificate, expression, facts, result, expected_context=context)
    if mutation == 'formula':
        expression = {'any': ['a', 'b']}
    elif mutation == 'facts':
        facts['a'] = False
    elif mutation in {'status', 'decision'}:
        result[mutation] = 'YES' if mutation == 'status' else 'TRUE'
    elif mutation == 'worlds':
        result['worlds'] = 99
    elif mutation == 'witness':
        result['witnesses']['true']['a'] = False
    elif mutation == 'context':
        context['source'] = 'changed-source'
    elif mutation == 'certificate':
        certificate['checked']['true_worlds'] = 99
    else:
        result['limits']['max_facts'] = 99
    with pytest.raises(ValueError):
        verify(certificate, expression, facts, result, expected_context=context)


@pytest.mark.parametrize('expression', [{}, {'all': []}, {'any': ['a'] * 129},
                                       {'wrong': ['a']}, 'invalid space', 1])
def test_invalid_grammar_rejected(expression):
    with pytest.raises(ValueError):
        expectation(expression, {})


def test_explicit_resource_limits_and_bad_observations():
    expression = 'a'
    for _ in range(25):
        expression = {'not': expression}
    with pytest.raises(ValueError, match='limit'):
        expectation(expression, {})
    with pytest.raises(ValueError, match='Boolean'):
        expectation('a', {'a': 1})
    assert expectation('a', {'other': 1, 'a': True})['status'] == 'YES'


def test_closed_world_mutant_is_rejected():
    result = dispatch('a', {'a': False})
    with pytest.raises(ValueError):
        check_result('a', {}, result)


def test_separate_cause_readings_do_not_inherit_shared_cause_containment():
    joint = {'exercise.' + k: k in {'cessation', 'disposal', 'value_joint', 'risk_joint'}
             for k in ('cessation', 'disposal', 'value_joint', 'risk_joint',
                       'value_cessation', 'risk_cessation', 'value_disposal', 'risk_disposal')}
    statuses = [expectation(model(r, 'event_at_exercise'), joint)['status'] for r in READINGS]
    assert statuses == ['YES', 'NO', 'YES']
    single = {**joint, 'exercise.value_joint': False, 'exercise.value_cessation': True,
              'exercise.risk_cessation': True}
    assert [expectation(model(r, 'event_at_exercise'), single)['status'] for r in READINGS] == ['NO', 'YES', 'YES']


def test_independent_temporal_models_match_disclosed_production_hypotheses():
    from legalmath.prospectus.basf_default_f import expressions
    for reading in READINGS:
        assert {q: model(reading, q) for q in QUESTIONS} == expressions(reading)


def test_false_witness_and_irrelevant_conflict_are_distinguished():
    result = dispatch('a', {'a': True, 'unused': 'conflict'})
    check_result('a', {'a': True, 'unused': 'conflict'}, result)
    corrupted = deepcopy(result)
    corrupted['witnesses']['true']['a'] = False
    with pytest.raises(ValueError):
        check_result('a', {'a': True}, corrupted)
