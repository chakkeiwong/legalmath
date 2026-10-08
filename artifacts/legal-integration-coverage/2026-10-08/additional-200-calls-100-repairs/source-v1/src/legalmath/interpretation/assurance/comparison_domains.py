"""Explicit finite domains for conditional factual mappings, never inferred."""
import math
from typing import Literal

from pydantic import Field

from ...canonical import digest
from ...domain import scalar
from ...errors import LegalMathError
from ..contracts import Strict, Id, Text, Hash, parse
from ..search.models import Quote
from .semantics import check_quotes


class FactDomain(Strict):
    name: Id
    type: Literal['bool', 'integer', 'money_hkd', 'date']
    unit: Text
    values: list[bool | str] = Field(min_length=1, max_length=4096)
    origin: Literal['MATHEMATICAL_PROBE', 'SOURCE_PREMISE']
    justification: Text
    evidence: list[Quote] = Field(max_length=12)


class Domain(Strict):
    profile: Literal['legalmath.comparison-domain.v1']
    packet_hash: Hash
    mapping_hash: Hash
    scope: Literal['PROBE_SET', 'DECLARED_FINITE_DOMAIN']
    facts: list[FactDomain] = Field(min_length=1, max_length=30)


def validate(value, packet, mapping, *, maximum_cases=4096):
    v = parse(Domain, value)
    if type(maximum_cases) is not int or not 1 <= maximum_cases <= 4096: raise LegalMathError('E_RESOURCE_LIMIT')
    if v['packet_hash'] != digest(packet) or v['mapping_hash'] != digest(mapping): raise LegalMathError('E_STALE_REVIEW')
    facts = {f['name']: f for f in mapping['common_facts']}
    ids = [f['name'] for f in v['facts']]
    if len(ids) != len(facts) or set(ids) != set(facts): raise LegalMathError('E_REFERENCE')
    for row in v['facts']:
        fact = facts[row['name']]
        if row['type'] != fact['type'] or row['unit'] != fact['unit']: raise LegalMathError('E_TYPE')
        if len({digest(x) for x in row['values']}) != len(row['values']): raise LegalMathError('E_DUPLICATE_ID')
        if any(x not in ('UNKNOWN', 'CONFLICT') and not scalar(row['type'], x) for x in row['values']):
            raise LegalMathError('E_TYPE')
        check_quotes(row['evidence'], packet)
        if row['origin'] == 'SOURCE_PREMISE' and not row['evidence']: raise LegalMathError('E_REFERENCE')
    count = math.prod(len(f['values']) for f in v['facts'])
    if count > maximum_cases: raise LegalMathError('E_RESOURCE_LIMIT', details={'declared_cases': count})
    return v


def compare(left, right, packet, mapping, checker, record, *, maximum_cases=4096):
    from .repair import compare_derived
    value = validate(record, packet, mapping, maximum_cases=maximum_cases)
    result = compare_derived(left, right, packet, mapping, checker,
        domain={f['name']: f['values'] for f in value['facts']}, max_cases=maximum_cases)
    return {'profile': 'legalmath.declared-domain-comparison.v1', 'domain_record': value,
        'domain_hash': digest(value), 'comparison': result,
        'scope': value['scope'], 'equivalence_outside_listed_domain': 'NOT_ESTABLISHED',
        'source_premises_established': False, 'legal_equivalence_established': False,
        'interpretation': 'A difference is an executed conditional witness. Matching values establish only the recorded finite comparison; a probe set is not an exhaustive legal domain.'}
