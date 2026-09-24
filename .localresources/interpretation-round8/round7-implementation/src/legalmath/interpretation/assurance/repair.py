"""Stage-specific repair bookkeeping and explicitly conditional fact comparisons."""
from copy import deepcopy
from itertools import product
import math
from typing import Literal
from pydantic import Field
from ...canonical import digest
from ...errors import LegalMathError
from ...ir.evaluate import evaluate
from ...java.manifest import run_java
from ..contracts import Strict, Id, Hash, Text, parse
from ..search.models import FactDefinition, Quote, commitment, generation_request
from ..search.formal import bundle, RULE, project
from .semantics import check_quotes

STAGES = ('DEPENDENCY', 'EXTRACTION', 'INTERPRETATION', 'FORMALIZATION', 'JAVA')


class RepairBudget:
    """Reserve before dispatch; failed or interrupted attempts still consume budget."""
    def __init__(self, maximum=2, attempts=()):
        if type(maximum) is not int or not 0 <= maximum <= 6:
            raise LegalMathError('E_SCHEMA')
        self.maximum = maximum
        self.attempts = deepcopy(list(attempts))

    def reserve(self, issue_key, stage, evidence):
        if stage not in STAGES:
            raise LegalMathError('E_SCHEMA')
        key = digest({'issue': issue_key, 'stage': stage, 'evidence': evidence})
        if any(a['action_key'] == key for a in self.attempts):
            return {'status': 'NO_NEW_EVIDENCE', 'action_key': key}
        if sum(a['issue_key'] == issue_key for a in self.attempts) >= self.maximum:
            return {'status': 'ISSUE_REPAIR_LIMIT', 'action_key': key}
        record = {'status': 'RESERVED', 'action_key': key, 'issue_key': issue_key, 'stage': stage}
        self.attempts.append(record)
        return record


class StageHistory:
    def __init__(self, records=()):
        self.records = deepcopy(list(records))

    def record(self, stage, inputs, result):
        if stage not in STAGES:
            raise LegalMathError('E_SCHEMA')
        record = {'stage': stage, 'input_hash': digest(inputs), 'result_hash': digest(result),
                  'result': deepcopy(result), 'valid': True, 'sequence': len(self.records)}
        self.records.append(record)
        return record

    def invalidate(self, stage, reason):
        if stage not in STAGES:
            raise LegalMathError('E_SCHEMA')
        invalidated = []
        for record in self.records:
            if record['valid'] and STAGES.index(record['stage']) >= STAGES.index(stage):
                record['valid'] = False; record['invalidated_by'] = reason; invalidated.append(record['sequence'])
        return invalidated


def repair_request(packet, reading, findings):
    stages = [f['stage'] for f in findings if f.get('stage') in STAGES]
    stage = min(stages, key=STAGES.index) if stages else 'INTERPRETATION'
    if stage in ('DEPENDENCY', 'EXTRACTION'):
        raise LegalMathError('E_DEPENDENCY', details='Repair context/inventory before generating another rule')
    request = generation_request(packet, 'adversarial-investigator', parent=reading,
                                 diagnostics=findings, move='repair-' + stage.lower())
    request.update(task='SEMANTIC_REPAIR', failed_stage=stage,
                   repair_instruction='Fix the diagnosed source-to-meaning error, retaining supported alternatives. '
                   'A repair must change the implicated meaning or supply evidence resolving the issue. '
                   'Do not simply mark the issue resolved. All downstream checks will run again.')
    return request


class DerivedMapping(Strict):
    source_packet_hash: Hash
    left_commitment: Hash
    right_commitment: Hash
    common_facts: list[FactDefinition] = Field(min_length=1, max_length=8)
    left: dict[Id, Text]
    right: dict[Id, Text]
    left_output: Literal['TRUE_IS_PROHIBITED', 'TRUE_IS_COMPLIANT']
    right_output: Literal['TRUE_IS_PROHIBITED', 'TRUE_IS_COMPLIANT']
    assumptions: list[Text] = Field(min_length=1, max_length=20)
    evidence: list[Quote] = Field(min_length=1, max_length=12)


def normalized_result(result, convention):
    result = project(result)
    if convention not in ('TRUE_IS_COMPLIANT', 'TRUE_IS_PROHIBITED'):
        raise LegalMathError('E_SCHEMA')
    if result['type'] != 'bool':
        raise LegalMathError('E_UNSUPPORTED_PROFILE')
    if result['status'] in ('TRUE', 'FALSE'):
        value = result['value'] if convention == 'TRUE_IS_PROHIBITED' else not result['value']
        return {'status': 'TRUE' if value else 'FALSE', 'type': 'bool', 'value': value}
    return result  # UNKNOWN, CONFLICT and OUT_OF_SCOPE are never negated or filled.


def fact_entry(result, at):
    if result['status'] in ('TRUE', 'FALSE', 'VALUE'):
        return {'type': result['type'], 'status': 'known', 'value': result['value'],
                'evidence_ids': ['conditional.mapping'], 'valid_from': at, 'valid_until': None, 'recorded_at': at}
    if result['status'] == 'UNKNOWN':
        return {'type': result['type'], 'status': 'unknown', 'reason': 'MISSING'}
    if result['status'] == 'CONFLICT':
        # These are the two opposed evidence entries of the declared synthetic
        # conflict probe, not fabricated bank evidence or a single unknown value.
        return {'type': result['type'], 'status': 'conflict',
                'evidence_ids': ['conditional.mapping.conflict.a', 'conditional.mapping.conflict.b']}
    raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Derived fact evaluated to ' + result['status'])


def compare_derived(left, right, packet, mapping, checker, *, domain=None, max_cases=4096):
    """Exhaust a declared finite common domain and replay original generated Java.

    Mappings are assumptions. Exhaustive enumeration verifies behavior only under
    those assumptions; domain values are never inferred for dates or numerics.
    """
    mapping = parse(DerivedMapping, mapping)
    if (mapping['source_packet_hash'] != digest(packet) or mapping['left_commitment'] != commitment(left)
            or mapping['right_commitment'] != commitment(right)):
        raise LegalMathError('E_HASH_MISMATCH')
    check_quotes(mapping['evidence'], packet)
    facts = mapping['common_facts']; names = [f['name'] for f in facts]
    if len(names) != len(set(names)) or not 1 <= max_cases <= 4096:
        raise LegalMathError('E_SCHEMA')
    if any(not set(f['source_unit_ids']) <= {u['unit_id'] for u in packet['units']} for f in facts):
        raise LegalMathError('E_REFERENCE')
    if domain is None:
        if any(f['type'] != 'bool' for f in facts):
            raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Date/numeric common facts require a declared domain')
        domain = {f['name']: [False, True, 'UNKNOWN', 'CONFLICT'] for f in facts}
    if set(domain) != set(names) or any(not isinstance(v, list) or not v for v in domain.values()):
        raise LegalMathError('E_SCHEMA')
    count = math.prod(len(v) for v in domain.values())
    if count > max_cases:
        return {'status': 'MAPPING_DOMAIN_LIMIT', 'declared_cases': count, 'release_eligible': False}
    originals, helpers = {}, {}
    for side, reading in (('left', left), ('right', right)):
        originals[side] = bundle(reading, packet, checker.at)
        if reading['formalization']['result_type'] != 'bool':
            raise LegalMathError('E_UNSUPPORTED_PROFILE')
        targets = {f['name']: f for f in reading['formalization']['facts']}
        if set(mapping[side]) != set(targets):
            raise LegalMathError('E_REFERENCE', details='Every original fact needs exactly one derived binding')
        helpers[side] = {}
        for name, formula in mapping[side].items():
            r = deepcopy(reading)
            r['formalization'] = {'facts': facts, 'scope': 'true', 'result': formula, 'result_type': targets[name]['type']}
            helpers[side][name] = bundle(r, packet, checker.at)
    rows, java_cases = [], {'left': [], 'right': []}
    for i, values in enumerate(product(*(domain[n] for n in names))):
        common = {'subject_id': 'conditional.common', 'facts': {}}
        for fact, val in zip(facts, values):
            status = val if isinstance(val, str) and val in ('UNKNOWN', 'CONFLICT') else 'VALUE'
            common['facts'][fact['name']] = fact_entry({'status': status, 'type': fact['type'], 'value': val}, checker.at)
        row = {'common_snapshot': common}
        for side in ('left', 'right'):
            mapped = {name: fact_entry(evaluate(helper, common, RULE, checker.at, checker.at), checker.at)
                      for name, helper in helpers[side].items()}
            snap = {'subject_id': 'conditional.' + side, 'facts': mapped}
            result = evaluate(originals[side], snap, RULE, checker.at, checker.at)
            if result['status'] == 'ERROR':
                raise LegalMathError('E_TYPE', details=result['diagnostics'])
            row[side] = {'snapshot': snap, 'python': project(result),
                         'normalized': normalized_result(result, mapping[side + '_output'])}
            java_cases[side].append({'id': 'mapped.' + str(i), 'bundle': originals[side], 'snapshot': snap,
                                    'rule_id': RULE, 'valid_at': checker.at, 'known_at': checker.at})
        rows.append(row)
    manifests = {}
    for side in ('left', 'right'):
        build = checker.build(originals[side]); manifests[side] = build['manifest']
        java = run_java(build['jar'], java_cases[side], checker.jdk, build['class_name'])
        if len(java) != len(rows):
            raise LegalMathError('E_INTEGRITY')
        for row, actual in zip(rows, java):
            if project(actual) != row[side]['python']:
                raise LegalMathError('E_INTEGRITY', details='Original Java differs on derived snapshot')
            row[side]['java'] = project(actual)
    differences = [row for row in rows if row['left']['normalized'] != row['right']['normalized']]
    return {'status': 'CONDITIONAL_DIFFERENCE' if differences else 'CONDITIONAL_EQUIVALENT_IN_DECLARED_DOMAIN',
            'mapping': mapping, 'domain': domain, 'cases': count, 'rows': rows,
            'witness': differences[0] if differences else None, 'build_manifests': manifests,
            'legal_source_commitment_resolved': False, 'release_eligible': False}
