"""Independent bitset certificates for bounded conditional Boolean inference.

This module deliberately does not import either production predicate evaluator.
It certifies consequences of supplied formulas, never the meaning of a source.
"""
from functools import lru_cache
from hashlib import sha256
import json
import re

POLICY = {'max_facts': 12, 'max_nodes': 4096, 'max_depth': 24,
          'explicit_relevant_conflict': 'DOMINATES', 'engine': 'finite'}
VERSION = 'finite-reasoning-certificate.v1'


def identity(value):
    return sha256(json.dumps(value, sort_keys=True,
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _program(expr):
    """Parse to postfix, with independent syntax/support/resource validation."""
    tokens, support = [], set()
    visited = 0

    def visit(node, depth):
        nonlocal visited
        visited += 1
        if visited > POLICY['max_nodes'] or depth > POLICY['max_depth']:
            raise ValueError('Certificate expression resource limit')
        if type(node) is bool:
            tokens.append(('constant', node))
        elif isinstance(node, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,127}', node):
            support.add(node)
            tokens.append(('fact', node))
        elif isinstance(node, dict) and len(node) == 1:
            operation, operands = next(iter(node.items()))
            if operation == 'not':
                visit(operands, depth + 1)
                tokens.append(('not', 1))
            elif (operation in {'all', 'any'} and isinstance(operands, list)
                  and 1 <= len(operands) <= 128):
                for operand in operands:
                    visit(operand, depth + 1)
                tokens.append((operation, len(operands)))
            else:
                raise ValueError('Unsupported certificate grammar')
        else:
            raise ValueError('Unsupported certificate grammar')

    visit(expr, 0)
    return tuple(sorted(support)), tuple(tokens)


@lru_cache(maxsize=256)
def _truth_table(serialized):
    support, tokens = _program(json.loads(serialized))
    if len(support) > POLICY['max_facts']:
        return support, None, None
    rows = 1 << len(support)
    universe = (1 << rows) - 1
    atoms = {name: sum(1 << row for row in range(rows) if row & (1 << index))
             for index, name in enumerate(support)}
    stack = []
    for op, value in tokens:
        if op == 'constant':
            stack.append(universe if value else 0)
        elif op == 'fact':
            stack.append(atoms[value])
        elif op == 'not':
            stack.append(universe ^ stack.pop())
        else:
            operands = stack[-value:]
            del stack[-value:]
            result = universe if op == 'all' else 0
            for operand in operands:
                result = result & operand if op == 'all' else result | operand
            stack.append(result)
    if len(stack) != 1:
        raise ValueError('Malformed certificate program')
    return support, stack[0], atoms


def expectation(expression, observations):
    """Exact counts from compatible valuation bitsets, not production iteration."""
    support, table, atoms = _truth_table(json.dumps(expression, sort_keys=True,
                                                   separators=(',', ':'), allow_nan=False))
    if not isinstance(observations, dict):
        raise ValueError('Facts must be a mapping')
    if table is None:
        return {'support': list(support), 'status': 'UNKNOWN', 'decision': 'UNDETERMINED',
                'reason': 'DOMAIN_LIMIT'}
    missing, conflicts = [], []
    compatible = (1 << (1 << len(support))) - 1
    for name in support:
        value = observations.get(name)
        if value is None:
            missing.append(name)
        elif value == 'conflict' and isinstance(value, str):
            conflicts.append(name)
        elif type(value) is bool:
            compatible &= atoms[name] if value else ~atoms[name]
        else:
            raise ValueError('Facts require Boolean, null or explicit conflict')
    yes = (compatible & table).bit_count() if not conflicts else 0
    no = (compatible & ~table).bit_count() if not conflicts else 0
    status = 'CONFLICT' if conflicts else 'UNKNOWN' if yes and no else 'YES' if yes else 'NO'
    return {'support': list(support), 'status': status,
            'decision': {'YES': 'TRUE', 'NO': 'FALSE', 'UNKNOWN': 'UNDETERMINED', 'CONFLICT': 'CONFLICT'}[status],
            'missing': missing, 'conflicts': conflicts, 'worlds': yes + no,
            'true_worlds': yes, 'false_worlds': no}


def check_result(expression, observations, result):
    expected = expectation(expression, observations)
    if expected.get('reason') == 'DOMAIN_LIMIT':
        exact = {'status': 'UNKNOWN', 'decision': 'UNDETERMINED', 'reason': 'DOMAIN_LIMIT',
                 'missing': expected['support'], 'witnesses': {},
                 'limits': {'max_facts': 12}, 'solver': 'finite'}
        if result != exact:
            raise ValueError('Unsupported-domain result was promoted or changed')
        return expected
    required = {'decision', 'status', 'missing', 'conflicts', 'worlds', 'witnesses', 'solver', 'limits'}
    if (not isinstance(result, dict) or set(result) != required
            or result['solver'] != 'finite' or result['limits'] != {'max_facts': 12}
            or type(result['limits']['max_facts']) is not int):
        raise ValueError('Finite result scope or fields changed')
    for name in ('decision', 'status', 'missing', 'conflicts', 'worlds'):
        if result[name] != expected[name] or (name == 'worlds' and type(result[name]) is not int):
            raise ValueError('Incorrect finite result: ' + name)
    witnesses = result['witnesses']
    labels = {value for value in ('true', 'false') if expected[value + '_worlds']}
    if not isinstance(witnesses, dict) or set(witnesses) != labels:
        raise ValueError('Missing or spurious finite witness')
    support, table, _ = _truth_table(json.dumps(expression, sort_keys=True, separators=(',', ':'), allow_nan=False))
    for label, world in witnesses.items():
        if (not isinstance(world, dict) or set(world) != set(support)
                or any(type(v) is not bool for v in world.values())):
            raise ValueError('Witness has incorrect fact support')
        if any(type(observations.get(k)) is bool and observations[k] != v for k, v in world.items()):
            raise ValueError('Witness contradicts observed evidence')
        row = sum(1 << index for index, name in enumerate(support) if world[name])
        if bool(table & (1 << row)) != (label == 'true'):
            raise ValueError('Witness does not support claimed value')
    return expected


def certify(expression, observations, result, *, context):
    return {'version': VERSION, 'policy': dict(POLICY), 'claim': 'FINITE_CONSEQUENCE_ONLY',
            'expression_sha256': identity(expression), 'facts_sha256': identity(observations),
            'result_sha256': identity(result), 'context_sha256': identity(context),
            'checked': check_result(expression, observations, result)}


def verify(certificate, expression, observations, result, *, expected_context):
    if identity(certificate) != identity(certify(expression, observations, result, context=expected_context)):
        raise ValueError('Certificate does not match independently checked expected inputs')
    return True
