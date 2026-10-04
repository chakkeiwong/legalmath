from copy import deepcopy

from jsonschema import Draft202012Validator, FormatChecker

from legalmath.ir.load import validator, RuleValidator
from legalmath.translation.expressions import expression
from tests.search.test_formal import AT
from legalmath.interpretation.search.formal import bundle
from tests.assurance.support import packet, reading


def test_discriminated_schema_agrees_with_original_on_structural_mutations():
    schema = validator('rule-bundle').schema
    old = Draft202012Validator(schema, format_checker=FormatChecker())
    new = RuleValidator(schema, format_checker=FormatChecker())
    b = bundle(reading(), packet(), AT)
    nodes = ['true', '(integer 1)', 'offer', '(not offer)', '(and offer gift)',
             '(+ (integer 2) (integer 3))', '(if true (integer 2) (integer 3))',
             '(> (+ (integer 1) (integer 2)) (integer 3))']
    for text in nodes:
        base = deepcopy(b); base['rules'][0]['body'] = expression(text, 'test')
        for field, value in [(None, None), ('op', 'invented'), ('op', None), ('op', 1),
                             ('type', 'unknown'), ('left', {}), ('extra', True), ('node_id', 7)]:
            v = deepcopy(base)
            if field: v['rules'][0]['body'][field] = value
            assert new.is_valid(v) == old.is_valid(v), (text, field, value)
        for field in list(base['rules'][0]['body']):
            v = deepcopy(base); del v['rules'][0]['body'][field]
            assert new.is_valid(v) == old.is_valid(v)


def test_optional_discriminators_and_overlapping_alternatives_are_not_pruned():
    schemas = [
        {'oneOf': [{'type': 'object', 'properties': {'op': {'const': 'a'}}}, {'type': 'object'}]},
        {'oneOf': [{'type': 'object', 'properties': {'op': {'const': 'a'}}, 'required': ['op']},
                   {'type': 'object', 'properties': {'op': {'enum': ['a', 'b']}}, 'required': ['op']}]},
    ]
    for schema in schemas:
        for value in ({}, {'op': 'a'}, {'op': 'b'}, {'op': None}, None):
            assert RuleValidator(schema).is_valid(value) == Draft202012Validator(schema).is_valid(value)
