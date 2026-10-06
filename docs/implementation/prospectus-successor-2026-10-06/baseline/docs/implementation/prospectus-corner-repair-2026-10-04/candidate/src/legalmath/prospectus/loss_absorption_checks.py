"""Independent finite/SMT obligations and the two native language routes."""
from copy import deepcopy
from itertools import product
from pathlib import Path

import z3

from .common import JDK, TOOLCHAIN, sha, write
from .loss_absorption import FACTS, decide, specification
from .models import AT, make_model
from .checks import symbolic


def reference(values):
    debt, write_down, convert, covered = values
    if 'conflict' in values:
        return None
    unknown = [i for i, v in enumerate(values) if v is None]
    answers = set()
    for completion in product((False, True), repeat=len(unknown)):
        row = list(values)
        for i, v in zip(unknown, completion):
            row[i] = v
        d, w, c, f = row
        answers.add('yes' if d and (w or c) else 'no' if d and f and not (w or c) else 'unresolved')
    return True if answers == {'yes'} else False if answers == {'no'} else None


def prove(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    model = make_model('loss_absorption', specification())
    variables = dict(zip(FACTS, z3.Bools(' '.join(FACTS))))
    d, w, c, f = (variables[k] for k in FACTS)
    independent = {'positive': z3.And(d, z3.Sum(z3.If(w, 1, 0), z3.If(c, 1, 0)) > 0),
                   'negative': z3.Not(z3.Or(z3.Not(d), z3.Not(f), w, c))}
    obligations = []
    for rule in model['rules']:
        solver = z3.Solver(); solver.set(timeout=10000)
        solver.add(symbolic(rule['body'], variables) != independent[rule['id']])
        path = directory / (rule['id'] + '.smt2'); path.write_text(solver.to_smt2())
        if solver.check() != z3.unsat:
            raise ValueError('Unproved formal rule: ' + rule['id'])
        obligations.append({'rule': rule['id'], 'result': 'UNSAT', 'sha256': sha(path.read_bytes())})
    count = 0
    for values in product((False, True, None, 'conflict'), repeat=len(FACTS)):
        result = decide(dict(zip(FACTS, values)))
        if result['answer'] is not reference(values):
            raise ValueError('Partial/conflict decision differs from independent completion specification')
        count += 1
    mutants = {
        'write_down_omitted': z3.And(d, c),
        'conversion_omitted': z3.And(d, w),
        'debt_scope_omitted': z3.Or(w, c),
        'missing_coverage_still_negative': z3.And(d, z3.Not(w), z3.Not(c)),
    }
    witnesses = []
    for name, expression in mutants.items():
        target = independent['negative' if 'negative' in name else 'positive']
        solver = z3.Solver(); solver.set(timeout=10000); solver.add(expression != target)
        if solver.check() != z3.sat:
            raise ValueError('Mutant was not distinguished: ' + name)
        witnesses.append({'mutant': name, 'witness': str(solver.model())})
    report = {'formal_obligations': obligations, 'finite_partial_conflict_states': count,
              'detected_mutants': witnesses, 'solver': z3.get_version_string(),
              'scope': 'Explicit formal premises; no natural-language correctness claim', 'human_quality_labels': False}
    write(directory / 'proofs.json', report)
    return report


def native(directory, source_results=()):
    from ..qualification import assurance
    cases = []
    for index, row in enumerate(product((False, True), repeat=len(FACTS))):
        values = dict(zip(FACTS, row))
        evidence = {'/' + k: ['declared-formal-input:' + str(index) + ':' + k] for k in FACTS}
        facts = {k: {'type': 'bool', 'status': 'known', 'value': v, 'evidence_ids': evidence['/' + k],
                     'complete': True, 'valid_from': AT, 'valid_until': None, 'recorded_at': AT} for k, v in values.items()}
        cases.append({'id': 'complete.' + str(index), 'snapshot': {'subject_id': 'formal-feature-case', 'evidence': evidence, 'facts': facts},
                      'valid_at': AT, 'known_at': AT})
    for status, name in product(('unknown', 'conflict'), FACTS):
        case = deepcopy(cases[-1]); case['id'] = status + '.' + name
        case['snapshot']['facts'][name] = {'type': 'bool', 'status': status,
            **({'reason': 'MISSING'} if status == 'unknown' else {'evidence_ids': ['a', 'b']})}
        if status == 'conflict': case['snapshot']['evidence']['/' + name] = ['a', 'b']
        cases.append(case)
    for row in source_results:
        evidence, facts = {}, {}
        for key, value in row['facts'].items():
            ids = [e['id'] for e in row['evidence'] if e['kind'] == key and e['disposition'] == 'applicable']
            # Negative/coverage facts remain qualified source-analysis premises.
            ids = ids or ['qualified-source-analysis:' + row['id'] + ':' + key]
            evidence['/' + key] = ids
            facts[key] = ({'type': 'bool', 'status': 'known', 'value': value, 'evidence_ids': ids,
                           'complete': True, 'valid_from': AT, 'valid_until': None, 'recorded_at': AT}
                          if type(value) is bool else {'type': 'bool', 'status': 'unknown', 'reason': 'MISSING'}
                          if value is None else {'type': 'bool', 'status': 'conflict', 'evidence_ids': ids})
        cases.append({'id': 'source.' + row['id'], 'snapshot': {'subject_id': row['id'], 'evidence': evidence, 'facts': facts},
                      'valid_at': AT, 'known_at': AT})
    result = assurance.run(make_model('loss_absorption', specification()), cases, Path(directory), JDK, toolchain=TOOLCHAIN)
    if any(v['status'] != 'CHECKED' for v in result['targets'].values()) or result['proof']['status'] != 'KERNEL_CHECKED':
        raise ValueError('Native backend or proof check failed; inspect qualification.json')
    if result['summary']['executed_target_cases'] != 2 * len(cases):
        raise ValueError('Missing native cases')
    return result['summary']
