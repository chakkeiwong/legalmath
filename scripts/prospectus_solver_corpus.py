"""Independent deterministic solver corpus; supplied meanings remain conditional."""
from copy import deepcopy
from itertools import product
from pathlib import Path
import gzip
import hashlib
import json
import re

PROFILE = 'docs/implementation/prospectus-execution-authority/attempts/reasoning-corpus/attempt-003/candidate-profile.json'
SOURCE_TEXT = ('The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity. '
    'Upon a Trigger Event, the principal amount of the Notes shall be written down to zero.')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def names(expression):
    if type(expression) is bool:
        return set()
    if isinstance(expression, str):
        require(bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}', expression)), 'Invalid independent fact name')
        return {expression}
    require(isinstance(expression, dict) and len(expression) == 1, 'Invalid independent expression')
    op, args = next(iter(expression.items()))
    if op == 'not':
        return names(args)
    require(op in {'all', 'any'} and isinstance(args, list) and 1 <= len(args) <= 128, 'Invalid independent operator')
    return set().union(*(names(arg) for arg in args))

def truth(expression, world):
    if type(expression) is bool:
        return expression
    if isinstance(expression, str):
        return world[expression]
    op, args = next(iter(expression.items()))
    if op == 'not':
        return not truth(args, world)
    if op == 'all':
        for child in args:
            if not truth(child, world):
                return False
        return True
    for child in args:
        if truth(child, world):
            return True
    return False

def expectation(expression, observations, constraints=()):
    support = sorted(names(expression) | set().union(*(names(c['expression']) for c in constraints)))
    require(len(support) <= 16, 'Independent enumeration exceeds 16 variables')
    missing = [n for n in support if observations.get(n) is None]
    conflicts = [n for n in support if observations.get(n) == 'conflict']
    for n in support:
        require(observations.get(n) is None or observations.get(n) == 'conflict' or type(observations[n]) is bool, 'Invalid oracle observation')
    counts = {'true': 0, 'false': 0}
    if not conflicts:
        fixed = {n: observations[n] for n in support if type(observations.get(n)) is bool}
        for values in product((False, True), repeat=len(missing)):
            world = {**fixed, **dict(zip(missing, values))}
            if all(truth(c['expression'], world) for c in constraints):
                counts[str(truth(expression, world)).lower()] += 1
    status = ('CONFLICT' if conflicts or not sum(counts.values()) else
              'UNKNOWN' if all(counts.values()) else 'YES' if counts['true'] else 'NO')
    return {'support': support, 'missing': missing, 'conflicts': conflicts, 'counts': counts, 'status': status,
        'decision': {'YES': 'TRUE', 'NO': 'FALSE', 'UNKNOWN': 'UNDETERMINED', 'CONFLICT': 'CONFLICT'}[status]}

def verify(expression, observations, constraints, result, *, finite=False):
    expected = expectation(expression, observations, constraints)
    for key in ('status', 'decision', 'missing', 'conflicts'):
        require(result.get(key) == expected[key], 'Incorrect solver ' + key)
    labels = {k for k,v in expected['counts'].items() if v}
    witnesses = result.get('witnesses')
    require(isinstance(witnesses, dict) and set(witnesses) == labels, 'Incomplete solver witnesses')
    for label, world in witnesses.items():
        require(isinstance(world, dict) and set(world) == set(expected['support']) and all(type(v) is bool for v in world.values()), 'Wrong witness support/type')
        require(all(type(observations.get(n)) is not bool or observations[n] == world[n] for n in expected['support']), 'Witness contradicts observation')
        require(all(truth(c['expression'], world) for c in constraints), 'Witness violates named constraint')
        require(truth(expression, world) == (label == 'true'), 'Witness does not establish claimed truth')
    if finite:
        require(result['solver'] == 'finite' and type(result['worlds']) is int and result['worlds'] == sum(expected['counts'].values()), 'Wrong finite world count')
    else:
        require(result.get('constraints') == list(constraints), 'Constraint source metadata lost')
        if expected['conflicts']:
            require(result.get('reason') == 'EXPLICIT_CONFLICT', 'Explicit conflict lost')
        elif expected['status'] == 'CONFLICT':
            require(result.get('reason') == 'INCONSISTENT_PREMISES', 'Inconsistent premises became entailment')
            core = result.get('unsat_core')
            allowed = {'observation:' + n for n in expected['support'] if type(observations.get(n)) is bool}
            allowed |= {'constraint:' + c['id'] for c in constraints}
            require(isinstance(core, list) and core and len(core) == len(set(core)) and set(core) <= allowed, 'Invalid named unsatisfiable core')
            subset_facts = {n:v for n,v in observations.items() if 'observation:' + n in core}
            subset_constraints = [c for c in constraints if 'constraint:' + c['id'] in core]
            require(expectation(expression, subset_facts, subset_constraints)['status'] == 'CONFLICT', 'Reported core is satisfiable')
        else:
            require(result.get('reason') == ('OPEN_PREMISES' if expected['status'] == 'UNKNOWN' else 'ENTAILED'), 'Wrong solver evidence reason')
    return expected

def formula_family(count):
    atoms = ['f' + str(i) for i in range(count)]
    all_of, any_of = {'all': atoms}, {'any': atoms}
    alternating = {'any': [{'all': atoms[:count//2]}, {'all': [{'not': x} for x in atoms[count//2:]]}]}
    return [('all', all_of), ('any', any_of), ('alternating', alternating),
            ('tautology', {'any': [all_of, {'not': all_of}]}),
            ('contradiction', {'all': [all_of, {'not': all_of}]})]

def corpus_cases(root, anchor):
    profile = json.loads((Path(root) / PROFILE).read_text())
    for source in profile['sources']:
        require(hashlib.sha256((Path(root) / source['path']).read_bytes()).hexdigest() == source['sha256'], 'Retained BASF source changed')
        for image in source.get('images', []):
            require(hashlib.sha256((Path(root) / image['path']).read_bytes()).hexdigest() == image['sha256'], 'Retained BASF image changed')
    rows = []
    for scenario in profile['scenarios']:
        for candidate in profile['candidates']:
            for question, expression in candidate['expressions'].items():
                rows.append({'id': 'basf/' + scenario['id'] + '/' + candidate['id'] + '/' + question,
                    'expression': expression, 'observations': scenario['facts'], 'constraints': [], 'source_profile_sha256': identity(profile)})
    for count in (3, 12, 13, 16):
        atoms = ['f' + str(i) for i in range(count)]
        conditions = [('open', {}), ('true', dict.fromkeys(atoms, True)), ('false', dict.fromkeys(atoms, False)),
                      ('partial', {'f0': True}), ('conflict', {'f0': 'conflict'})]
        for name, expression in formula_family(count):
            for state, observations in conditions:
                rows.append({'id': f'synthetic/{count}/{name}/{state}', 'expression': expression,
                    'observations': observations, 'constraints': []})
        query = {'all': atoms}
        specs = [('equal', {'any': [{'all': atoms}, {'all': [{'not': n} for n in atoms]}]}, {}),
                 ('forced-true', query, {}), ('contradiction', {'all': [query, {'not': query}]}, {}),
                 ('observed-conflict', query, {'f0': False})]
        for name, expression, observations in specs:
            rows.append({'id': f'constrained/{count}/{name}', 'expression': query, 'observations': observations,
                'constraints': [{'id': 'declared-correlation', 'expression': expression, 'source': anchor,
                    'reason': 'Explicit synthetic Boolean premise; not issuer interpretation'}]})
    return rows

def products_for(request, root):
    from legalmath.prospectus.successor import service
    p1 = service.source_product(request, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}

def product_case(base, graph, anchor, kind):
    from legalmath.prospectus.successor import contract_assembly, clause_graph
    from scripts.prospectus_closure_fixtures import TIME
    req = deepcopy(base)
    atoms = ['f' + str(i) for i in range(13)]
    query = {'all': atoms}
    observations = ({n: True for n in atoms} if kind == 'true' else {'f0': False} if kind == 'false' else
                    {'f0': 'conflict'} if kind == 'conflict' else {})
    req['predicate_engine'] = 'z3'
    req['observations'] = observations
    constraints = []
    if kind in {'correlated', 'inconsistent'}:
        constraints = [{'id': 'all-true', 'expression': query, 'source': anchor, 'reason': 'Synthetic simultaneous condition'}]
        if kind == 'inconsistent':
            constraints.append({'id': 'all-not', 'expression': {'not': query}, 'source': anchor, 'reason': 'Deliberate inconsistent premise'})
    req['predicate_constraints'] = constraints
    req['assembly']['ast'] = {'version': 'contract-ast.v2', 'root': 'text',
        'nodes': [{'id': 'text', 'kind': 'Text', 'source': anchor}],
        'constraints': [{'any': [query, {'not': query}]}]}
    assembly = contract_assembly.assemble(graph, req['assembly'], predicate_engine='z3')
    req['clauses'] = clause_graph.build(assembly)['nodes']
    next(n for n in req['clauses'] if n['effect'] == 'principal_loss')['conditions'] = query
    req['law_bases'] = [{'id': 'synthetic-law', 'authority': 'Synthetic development premise', 'jurisdiction': 'X', 'edition': '1',
        'source': anchor, 'instrument_id': req['bundle']['instrument_id'], 'valid_from': TIME, 'known_from': TIME, 'premises': query}]
    req['facts'] = []
    for name, value in observations.items():
        for actual in ((False, True) if value == 'conflict' else (value,)):
            req['facts'].append({'name': name, 'basis_id': 'synthetic-law', 'instrument_id': req['bundle']['instrument_id'],
                'jurisdiction': 'X', 'source': anchor, 'value': actual, 'valid_from': TIME, 'known_from': TIME, 'observed_at': TIME})
    if kind == 'future':
        req['facts'] = [{'name': n, 'basis_id': 'synthetic-law', 'instrument_id': req['bundle']['instrument_id'],
            'jurisdiction': 'X', 'source': anchor, 'value': True, 'valid_from': TIME, 'known_from': TIME,
            'observed_at': '2027-01-01T00:00:00Z'} for n in atoms]
    return req

def check_product(row):
    from legalmath.prospectus.successor import service
    req, products, answer = row['request'], row['products'], row['answer']
    for phase, value in products.items():
        service.verify(value, phase)
    clause = products['P3']['payload']['questions']['Q1']
    for reasoning in clause['reasoning']:
        verify(reasoning['expression'], req.get('observations', {}), req.get('predicate_constraints', []), reasoning['result'])
    require(answer['questions']['Q1'] == clause, 'Clause evidence lost downstream')
    law = products['P4']['payload']['question']
    for item in law['value']:
        verify(item['expression'], item['premises'], [], item['reasoning'])
        require(item['actual_exercise'] == 'NOT_ESTABLISHED', 'Synthetic facts promoted')
    require(answer['questions']['Q4'] == law, 'Law evidence lost downstream')
    for item in products['P2']['payload']['assembly']['rendered_ast']['reasoning']:
        verify(item['expression'], {}, [], item['result'])
    if row['kind'] == 'future':
        require(len(law['value'][0]['excluded_facts']) == 13 and law['status'] == 'UNKNOWN', 'Future facts became currently known')
    return {'kind': row['kind'], 'q1': clause['status'], 'q4': law['status'],
        'complete_products_sha256': identity(products), 'complete_answer_sha256': identity(answer)}

def refusal(name, action):
    try:
        action()
    except ValueError as exc:
        return {'case': name, 'rejected': True, 'error': str(exc)}
    raise ValueError('Required refusal missing: ' + name)

def run(root, source_root):
    import z3
    from legalmath.prospectus.successor import predicates, service, source_graph, occurrences
    source_root = Path(source_root)
    base = json.loads((source_root / 'request.json').read_text())
    graph = source_graph.build(base['bundle'], source_root)
    anchor = occurrences.anchor(graph['units'][0])
    cases, results, controls = corpus_cases(root, anchor), [], []
    for case in cases:
        result = predicates.dispatch(case['expression'], case['observations'], engine='z3', constraints=case['constraints'], graph=graph)
        expected = verify(case['expression'], case['observations'], case['constraints'], result)
        row = {**case, 'result': result, 'expected': expected}
        if not case['constraints'] and len(expected['support']) <= 12:
            finite = predicates.dispatch(case['expression'], case['observations'])
            verify(case['expression'], case['observations'], [], finite, finite=True)
            row['finite'] = finite
        results.append(row)
    require(len(results) == 404, 'Incomplete declared corpus')
    for kind in ('status', 'witness-type', 'witness-value', 'core'):
        row = deepcopy(next(r for r in results if (r['result'].get('reason') == 'INCONSISTENT_PREMISES' if kind == 'core' else r['id'] == 'synthetic/13/all/true')))
        if kind == 'status':
            row['result']['status'] = 'NO'
        elif kind == 'witness-type':
            row['result']['witnesses']['true']['f0'] = 1
        elif kind == 'witness-value':
            row['result']['witnesses']['true']['f0'] = False
        else:
            row['result']['unsat_core'] = ['constraint:missing']
        controls.append(refusal('checker-' + kind, lambda r=row: verify(r['expression'],r['observations'],r['constraints'],r['result'])))
    controls.append(refusal('permissive-checker-detected', lambda: refusal('permissive', lambda: True)))
    product_rows = []
    for kind in ('true', 'false', 'open', 'conflict', 'correlated', 'inconsistent', 'future'):
        req = product_case(base, graph, anchor, kind)
        ps = products_for(req, source_root)
        answer = service.consume(ps, source_root, include_artifacts=True)
        # Current validation exercises the consumer's reconstruction and bindings.
        current = service.consume(ps, source_root, include_artifacts=True, mode='current')
        require(answer['assessment_mode'] == 'frozen' and current['assessment_mode'] == 'current', 'Wrong explicit consumer mode')
        substantive = lambda value: {k:v for k,v in value.items() if k not in {'assessment_mode', 'report_sha256'}}
        require(substantive(current) == substantive(answer), 'Frozen/current complete substantive consumer differs')
        row = {'kind': kind, 'request': req, 'products': ps, 'answer': answer, 'current_answer': current}
        row['checked'] = check_product(row)
        product_rows.append(row)
    original = product_rows[0]
    bad = deepcopy(original['products']); bad['P3']['payload']['questions']['Q1']['status'] = 'NO'
    controls.append(refusal('changed-product', lambda: service.consume(bad, source_root)))
    wrong = deepcopy(original['request']); wrong['facts'][0]['instrument_id'] = 'foreign'
    controls.append(refusal('wrong-law-subject', lambda: products_for(wrong, source_root)))
    wrong = deepcopy(original['request']); wrong['assembly']['ast']['constraints'] = [{'all': ['f0', {'not': 'f0'}]}]
    controls.append(refusal('construction-contradiction', lambda: products_for(wrong, source_root)))
    wrong = deepcopy(original['request']); wrong['bundle']['documents'][0]['sha256'] = '0' * 64
    controls.append(refusal('changed-source', lambda: products_for(wrong, source_root)))
    finite_req = deepcopy(original['request']); finite_req['predicate_engine'] = 'finite'
    finite_ps = products_for(finite_req, source_root)
    require(finite_ps['P4']['payload']['question']['value'][0]['reasoning']['reason'] == 'DOMAIN_LIMIT', 'Finite large-domain law fallback lost')
    require(finite_ps['P2']['payload']['assembly']['rendered_ast']['reasoning'][0]['result']['reason'] == 'DOMAIN_LIMIT', 'Finite construction limit lost')
    boundaries = []
    for count in (256, 257):
        atoms = ['b' + str(i) for i in range(count)]
        query = {'all': [{'all': atoms[i:i+128]} for i in range(0, count, 128)]}
        result = predicates.solve(query, {})
        require(result['status'] == 'UNKNOWN' and result['reason'] == ('OPEN_PREMISES' if count == 256 else 'DOMAIN_LIMIT'), 'Wrong solver domain boundary')
        if count == 256:
            for label, world in result['witnesses'].items():
                require(set(world) == set(atoms) and all(type(v) is bool for v in world.values()) and truth(query, world) == (label == 'true'), 'Invalid large-boundary witness')
        boundaries.append({'facts': count, 'result': result})
    unknown = []
    for call in (1, 2, 3):
        class InjectedUnknown:
            def __init__(self): self.solver, self.calls = z3.Solver(), 0
            def __getattr__(self, key): return getattr(self.solver, key)
            def check(self):
                self.calls += 1
                return z3.unknown if self.calls == call else self.solver.check()
            def reason_unknown(self): return 'injected-interface-control'
        result = predicates.solve('a', {}, solver_factory=InjectedUnknown)
        require(result['status'] == 'UNKNOWN' and result['reason'] == 'SOLVER_UNKNOWN' and result['solver_reason'] == 'injected-interface-control', 'Unknown solver response promoted')
        for label, world in result['witnesses'].items():
            require(set(world) == {'a'} and type(world['a']) is bool and world['a'] == (label == 'true'), 'Wrong partial unknown witness')
        unknown.append({'injected_at_check': call, 'result': result, 'actual_timeout': False})
    return {'version': 'solver-corpus.v1', 'z3_version': z3.get_version_string(), 'source_sha256': hashlib.sha256((source_root/'source.txt').read_bytes()).hexdigest(),
        'source_profile_sha256': hashlib.sha256((Path(root)/PROFILE).read_bytes()).hexdigest(),
        'cases': results, 'products': product_rows, 'controls': controls, 'boundaries': boundaries, 'injected_unknown': unknown,
        'finite_domain_products': finite_ps, 'whole_task_complete': False, 'source_meaning_proved': False}

def check_record(record):
    require(record['version'] == 'solver-corpus.v1' and len(record['cases']) == 404 and len(record['products']) == 7, 'Wrong retained corpus denominator')
    for row in record['cases']:
        require(verify(row['expression'], row['observations'], row['constraints'], row['result']) == row['expected'], 'Retained oracle disagreement')
        if 'finite' in row:
            verify(row['expression'], row['observations'], [], row['finite'], finite=True)
    for row in record['products']:
        require(check_product(row) == row['checked'], 'Retained downstream product differs')
        for key in ('answer', 'current_answer'):
            value = row[key]
            require(value['report_sha256'] == identity({k:v for k,v in value.items() if k != 'report_sha256'}), 'Complete report checksum differs')
        require({k:v for k,v in row['answer'].items() if k not in {'assessment_mode','report_sha256'}} ==
                {k:v for k,v in row['current_answer'].items() if k not in {'assessment_mode','report_sha256'}}, 'Current/frozen substantive comparison changed')
    require(len(record['controls']) == 9 and all(r['rejected'] for r in record['controls']), 'Missing adverse controls')
    require(record['whole_task_complete'] is False and record['source_meaning_proved'] is False, 'Broader scope promoted')
    return {'cases': len(record['cases']), 'basf_cases': sum(r['id'].startswith('basf/') for r in record['cases']),
        'large_cases': sum(len(r['expected']['support']) > 12 for r in record['cases']),
        'products': len(record['products']), 'controls': len(record['controls']), 'complete_record_sha256': identity(record)}
