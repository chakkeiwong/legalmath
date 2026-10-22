"""Purpose and boundary counterexamples, independent of the source fixture."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import definition_bindings as module

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / 'docs/implementation/prospectus-execution-authority/reviews/definition-bindings-repair-331/synthetic-cases.json').read_text())
RULES = {
    'tax': {'id': 'tax', 'record': 'A', 'group': 'amount', 'extents': [[0, 20]],
            'meaning': {'relation': 'EQUAL'}, 'condition': 'Tax call only'},
    'makewhole': {'id': 'makewhole', 'record': 'B', 'group': 'amount', 'extents': [[30, 50]],
                  'meaning': {'relation': 'MAXIMUM'}, 'condition': 'Issuer option only'},
}
RECORDS = {'A': 'tax', 'B': 'makewhole'}


def application(rule, start, end):
    selected = RULES.get(rule)
    return {'id': 'amount:' + str(start), 'start': start, 'end': end, 'quote': 'Amount',
        'rule': rule, 'group': 'amount', 'role': 'OPERATIVE_USE' if selected else 'UNRESOLVED',
        'meaning': deepcopy(selected['meaning']) if selected else None,
        'condition': selected['condition'] if selected else None,
        'remaining': [] if selected else ['Purpose unresolved']}


@pytest.mark.parametrize('case', CASES)
def test_identical_words_require_the_correct_record_and_extent(case):
    app = None if case['rule'] == 'ABSENT' else application(case['rule'], case['start'], case['end'])
    args = (case['record'], app, RULES, RECORDS, case['start'], case['end'])
    if case['expected'] == 'REFUSE':
        with pytest.raises(ValueError):
            module._rule_binding(*args)
    else:
        disposition, binding, remaining = module._rule_binding(*args)
        assert disposition == case['expected']
        if disposition == 'BOUND_CONDITIONALLY':
            assert binding['record'] == case['record'] and binding['condition'] == RULES[case['rule']]['condition']
            assert remaining == []
        else:
            assert binding is None and remaining


@pytest.mark.parametrize('field,value', [
    ('group', 'holder'), ('meaning', {'relation': 'MAXIMUM'}), ('condition', ''),
    ('role', 'COMPOUND_COMPONENT'), ('remaining', ['Unresolved']), ('start', 9),
])
def test_application_metadata_cannot_select_another_purpose(field, value):
    app = application('tax', 10, 16)
    app[field] = value
    with pytest.raises(ValueError):
        module._rule_binding('A', app, RULES, RECORDS, 10, 16)


def test_application_identity_must_match_registered_record():
    with pytest.raises(ValueError):
        module._rule_binding('A', application('tax', 10, 16), RULES, {'A': 'makewhole', 'B': 'tax'}, 10, 16)


def test_false_resolution_is_not_a_valid_question_link():
    answer = {'questions': {q: {'unresolved': ['definition-source:A'], 'status': 'YES', 'value': True}
                            for q in ('Q1', 'Q2')}}
    with pytest.raises(ValueError):
        module._question_links(answer, [{'id': 'A'}], [])
