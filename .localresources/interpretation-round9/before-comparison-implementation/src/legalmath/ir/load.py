from functools import lru_cache
from importlib.resources import files
import json
from jsonschema import Draft202012Validator, FormatChecker

from ..errors import diagnostic


@lru_cache(maxsize=32)
def validator(name):
    schema = json.loads(files("legalmath").joinpath("schemas", name + ".schema.json").read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())


def schema_errors(name, value, prefix=""):
    errors = {prefix + "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in e.absolute_path)
              for e in validator(name).iter_errors(value)}
    return [diagnostic("E_SCHEMA", p) for p in sorted(errors)]


def source_span_errors(value):
    schema = validator("rule-bundle").schema["properties"]["source_spans"]["items"]
    return list(Draft202012Validator(schema).iter_errors(value))
