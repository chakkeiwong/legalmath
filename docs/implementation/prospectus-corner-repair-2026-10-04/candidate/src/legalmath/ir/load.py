from functools import lru_cache
from importlib.resources import files
import json
from jsonschema import Draft202012Validator, FormatChecker, validators

from ..errors import diagnostic


def _possible(branch, instance):
    """Prune only a logically impossible required string discriminator."""
    if not isinstance(branch, dict) or not isinstance(instance, dict):
        return True
    for key in ('op', 'type'):
        prop = branch.get('properties', {}).get(key, {})
        if key not in branch.get('required', []) or key not in instance:
            continue
        allowed = [prop['const']] if isinstance(prop.get('const'), str) else prop.get('enum')
        if (isinstance(allowed, list) and allowed and all(isinstance(x, str) for x in allowed)
                and instance[key] not in allowed):
            return False
    if 'oneOf' in branch and not any(_possible(b, instance) for b in branch['oneOf']):
        return False
    return True


def _discriminated_one_of(checker, alternatives, instance, schema):
    possible = [b for b in alternatives if _possible(b, instance)]
    yield from Draft202012Validator.VALIDATORS['oneOf'](checker, possible, instance, schema)


RuleValidator = validators.extend(Draft202012Validator, {'oneOf': _discriminated_one_of})


@lru_cache(maxsize=32)
def validator(name):
    schema = json.loads(files("legalmath").joinpath("schemas", name + ".schema.json").read_text())
    cls = RuleValidator if name == 'rule-bundle' else Draft202012Validator
    return cls(schema, format_checker=FormatChecker())


def schema_errors(name, value, prefix=""):
    errors = {prefix + "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in e.absolute_path)
              for e in validator(name).iter_errors(value)}
    return [diagnostic("E_SCHEMA", p) for p in sorted(errors)]


def source_span_errors(value):
    schema = validator("rule-bundle").schema["properties"]["source_spans"]["items"]
    return list(Draft202012Validator(schema).iter_errors(value))
