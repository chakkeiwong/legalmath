import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.arguments import evaluate_arguments


def test_mutual_attack_preserves_two_extensions_and_no_skeptical_winner():
    result=evaluate_arguments(['a','b'],[['a','b'],['b','a']])
    assert result['stable_extensions']==[['a'],['b']] and result['grounded']==[]
    assert result['skeptical_stable']==[] and not result['legal_premises_verified']


def test_odd_cycle_has_no_stable_extension_and_no_vacuous_acceptance():
    result=evaluate_arguments(['a','b','c'],[['a','b'],['b','c'],['c','a']])
    assert not result['stable_extension_exists'] and result['skeptical_stable']==[]


def test_defense_and_resource_bounds():
    result=evaluate_arguments(['a','b','c'],[['a','b'],['b','c']])
    assert result['grounded']==['a','c'] and result['stable_extensions']==[['a','c']]
    with pytest.raises(LegalMathError):evaluate_arguments(['a'],[['ghost','a']])
    with pytest.raises(LegalMathError):evaluate_arguments([str(i) for i in range(17)],[],maximum=16)
