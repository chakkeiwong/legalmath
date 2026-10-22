"""Integrated conditional reasoning evidence, with preserved original comparators."""
from pathlib import Path
from copy import deepcopy
import json

from scripts.prospectus_calendar_evidence import load, save, require
from scripts import prospectus_installed_reasoning_evidence as explanations
from scripts import prospectus_solver_corpus_v2 as solver

BASE = 'docs/implementation/prospectus-execution-authority'
SOLVER = BASE + '/attempts/reasoning-corpus/attempt-007'
EXPLANATIONS = BASE + '/attempts/reasoning-corpus/attempt-009'
FIXTURE = BASE + '/reviews/solver-corpus/fixture'
CONTROL_NAMES = {'checker-status', 'checker-witness-type', 'checker-witness-value',
                 'checker-core', 'permissive-checker-detected', 'changed-product',
                 'wrong-law-subject', 'construction-contradiction', 'changed-source',
                 'finite-unresolved-operative-clause'}


def same(actual, expected, label):
    # JSON distinguishes booleans, integers and floats; Python equality does not.
    encode = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    require(encode(actual) == encode(expected), 'Conditional acceptance mismatch: ' + label)


def files(folder):
    return {str(p.relative_to(folder)) for p in Path(folder).rglob('*') if p.is_file()}


def same_records(left, right):
    names = files(left)
    require(names and names == files(right), 'Complete reasoning file inventory differs')
    for name in sorted(names):
        actual, expected = load(Path(left) / name), load(Path(right) / name)
        if name == 'solver-record.json.gz':
            same_solver_records(actual, expected)
        else:
            same(actual, expected, name)


def same_solver_records(actual, expected):
    """Only independently valid case-level Z3 witnesses/cores may differ."""
    def checked(value):
        solver.check_record(value)
        result = deepcopy(value)
        for row in result['cases']:
            for field in ('witnesses', 'unsat_core'):
                if field in row['result']:
                    row['result'][field] = 'INDEPENDENTLY_VERIFIED_NONUNIQUE_CHOICE'
        return result
    same(checked(actual), checked(expected), 'solver inputs/consequences/products outside validated choices')


def solver_requirements(record, original):
    """Reject a self-consistent smaller or substituted corpus, not just bad totals."""
    solver.check_record(record)
    same([r['id'] for r in record['cases']], [r['id'] for r in original['cases']], 'solver case identities')
    for actual, expected in zip(record['cases'], original['cases']):
        for field in ('id', 'expression', 'observations', 'constraints', 'source_profile_sha256'):
            same(actual.get(field), expected.get(field), 'solver input ' + field)
        # Z3 may choose another valid witness/core. Independent enumeration,
        # witness truth and unsatisfiable-core checks above determine correctness.
        same(actual['expected'], expected['expected'], 'solver independent expected value')
    same([r['kind'] for r in record['products']], [r['kind'] for r in original['products']], 'product cases')
    same(sorted(r['case'] for r in record['controls']), sorted(CONTROL_NAMES), 'solver refusal identities')
    same(record['boundaries'], original['boundaries'], '256/257 variable boundary')
    same(record['injected_unknown'], original['injected_unknown'], 'typed solver-unknown responses')
    same(record['source_sha256'], original['source_sha256'], 'solver fixture source')
    same(record['source_profile_sha256'], original['source_profile_sha256'], 'original BASF profile')
    for actual, expected in zip(record['products'], original['products']):
        same(actual, expected, 'complete original solver product ' + actual['kind'])
    same(record['finite_domain_products'], original['finite_domain_products'], 'finite exhaustion products')


def evaluate(root, output):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    record = solver.run(root, root / FIXTURE)
    solver_requirements(record, load(root / SOLVER / 'source-record.json.gz'))
    save(output / 'solver-record.json.gz', record)
    for stage in explanations.STAGES:
        explanations.evaluate(root, output / 'explanations', stage)
    details = verify(root, output)
    return details


def verify(root, output):
    root, output = Path(root), Path(output)
    record = load(output / 'solver-record.json.gz')
    solver_requirements(record, load(root / SOLVER / 'source-record.json.gz'))
    checked = solver.check_record(record)
    checked.pop('complete_record_sha256')  # Witness choice is independently checked.
    proof = explanations.verify_retained(root, output / 'explanations')
    same_records(output / 'explanations', root / EXPLANATIONS / 'installed-results')
    return {'solver': checked, 'explanations': proof,
            'original_refusal_controls_preserved': True,
            'conditional_scope': 'DECLARED_BOOLEAN_GRAMMAR_AND_SOURCE_BOUND_PREMISES',
            'source_meaning_proved': False, 'whole_program_complete': False}
