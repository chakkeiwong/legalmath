"""Packaged monograph contracts and stricter untrusted request validation."""
from importlib.resources import files
import json
from functools import lru_cache
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from jsonschema import Draft202012Validator, FormatChecker
from ..canonical import canonical
from ..errors import LegalMathError
from ..domain import timestamp

V = "interpretation.v1"
Id = Annotated[str, Field(pattern=r'^[a-z][a-z0-9_.:-]{0,127}$')]
Hash = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Text = Annotated[str, Field(min_length=1, max_length=20000)]
TERMINAL = {"READY_FOR_REVIEW", "BLOCKED_UNRESOLVED", "CANCELLED", "FAILED_INTEGRITY"}

@lru_cache
def validator(kind):
    schema = json.loads(files('legalmath').joinpath('schemas',f'interpretation-{kind}.schema.json').read_text())
    return Draft202012Validator(schema, format_checker=FormatChecker())

def validate(kind, value):
    canonical(value)
    error = next(validator(kind).iter_errors(value), None)
    if error:
        raise LegalMathError('E_SCHEMA', '/'+'/'.join(map(str,error.absolute_path)))
    for name, spec in validator(kind).schema['properties'].items():
        if spec.get('format') == 'date-time' and value.get(name) is not None:
            timestamp(value[name])
    return value

def reference_policy():
    return json.loads(files('legalmath').joinpath('schemas','interpretation-reference-policy.json').read_text())

def policy(value):
    validate('policy', value)
    ref = reference_policy()
    if value['use'] != 'DETERMINISTIC_FIXTURE_ONLY' or any(value[x] is not None for x in ('token_cap','cost_cap_minor_units','billing_currency')):
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if value['required_initial_roles'] != ref['required_initial_roles'] or value['mandatory_checks'] != ref['mandatory_checks']:
        raise LegalMathError('E_SCHEMA')
    # Hard prototype ceilings keep caller-supplied fixture budgets finite in practice.
    ceilings = {k: max(v, 100) for k,v in ref.items() if type(v) is int}
    ceilings.update(run_deadline_seconds=600, action_timeout_seconds=30, max_candidates=64, max_argument_nodes=500)
    if any(value[k] > n for k,n in ceilings.items()):
        raise LegalMathError('E_RESOURCE_LIMIT')
    if value['max_initial_actions'] < len(ref['required_initial_roles']) or value['max_actions_total'] < value['max_initial_actions']:
        raise LegalMathError('E_SCHEMA')
    return value

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Unit(Strict):
    unit_id: Id
    locator: Text
    text: Text
    normative: bool
    span: dict | None

class Dependency(Strict):
    dependency_id: Id
    source_hash: Hash | None

class Packet(Strict):
    source_key: Id
    authority: Literal['SYNTHETIC_FIXTURE','RETAINED_SOURCE']
    selected_slice: Text
    units: list[Unit] = Field(min_length=1, max_length=500)
    dependencies: list[Dependency] = Field(max_length=100)
    family_ids: list[Id] = Field(min_length=1, max_length=64)

class Proposal(Strict):
    source_packet_hash: Hash
    source_unit_ids: list[Id] = Field(min_length=1, max_length=500)
    family_ids: list[Id] = Field(min_length=1, max_length=64)
    subject_unit: Text
    controlled_language: Text
    bundle_hash: Hash | None
    assumptions: list[dict] = Field(max_length=200)
    arguments: list[dict] = Field(max_length=500)
    parent_id: Id | None
    revision_reason: Text


def parse(model, value):
    canonical(value)
    try:
        return model.model_validate(value).model_dump()
    except ValidationError as exc:
        raise LegalMathError('E_SCHEMA') from exc
