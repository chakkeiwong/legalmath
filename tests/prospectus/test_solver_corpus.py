from copy import deepcopy
import pytest
from scripts.prospectus_solver_corpus import expectation, verify, refusal

def result():
    return {'status': 'YES', 'decision': 'TRUE', 'missing': [], 'conflicts': [],
        'witnesses': {'true': {'a': True}}, 'reason': 'ENTAILED', 'constraints': []}

def test_independent_oracle_preserves_missing_and_conflicting_facts():
    assert expectation('a', {})['counts'] == {'true': 1, 'false': 1}
    assert expectation({'any': ['a', {'not': 'a'}]}, {})['status'] == 'YES'
    assert expectation({'any': ['a', {'not': 'a'}]}, {'a': 'conflict'})['status'] == 'CONFLICT'
    assert expectation('a', {'a': False}, [{'expression': 'a'}])['status'] == 'CONFLICT'

@pytest.mark.parametrize('mutation', ['status', 'type', 'value', 'missing'])
def test_changed_solver_outputs_are_rejected(mutation):
    value = result()
    verify('a', {'a': True}, [], value)
    if mutation == 'status': value['status'] = 'NO'
    elif mutation == 'type': value['witnesses']['true']['a'] = 1
    elif mutation == 'value': value['witnesses']['true']['a'] = False
    else: value['missing'] = ['a']
    with pytest.raises(ValueError): verify('a', {'a': True}, [], value)

def test_core_must_itself_be_inconsistent():
    constraints = [{'id': 'positive', 'expression': 'a'}, {'id': 'negative', 'expression': {'not': 'a'}}]
    value = {'status': 'CONFLICT', 'decision': 'CONFLICT', 'missing': ['a'], 'conflicts': [],
        'witnesses': {}, 'reason': 'INCONSISTENT_PREMISES', 'constraints': constraints,
        'unsat_core': ['constraint:positive', 'constraint:negative']}
    verify('a', {}, constraints, value)
    value['unsat_core'] = ['constraint:positive']
    with pytest.raises(ValueError, match='satisfiable'): verify('a', {}, constraints, value)

def test_permissive_checker_cannot_pass_refusal_contract():
    with pytest.raises(ValueError, match='Required refusal missing'):
        refusal('permissive', lambda: True)
