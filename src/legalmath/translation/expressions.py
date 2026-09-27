"""Target-independent expression syntax; parsing never invokes a model or runtime."""
import re
from ..errors import LegalMathError


def expression(text, prefix):
    tokens = re.findall(r'\(|\)|[^\s()]+', text)
    if not tokens or len(tokens) > 1000:
        raise LegalMathError('E_RESOURCE_LIMIT')
    position = 0

    def tree(depth=0):
        nonlocal position
        if depth > 32 or position >= len(tokens):
            raise LegalMathError('E_SCHEMA')
        token = tokens[position]; position += 1
        if token != '(':
            if token == ')': raise LegalMathError('E_SCHEMA')
            return token
        result = []
        while position < len(tokens) and tokens[position] != ')':
            result.append(tree(depth + 1))
        if position >= len(tokens) or not result: raise LegalMathError('E_SCHEMA')
        position += 1
        return result

    parsed = tree()
    if position != len(tokens): raise LegalMathError('E_SCHEMA')
    count = 0

    def atom(value):
        if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.:\[\]-]*', value):
            raise LegalMathError('E_SCHEMA', details='Invalid expression identifier')
        return value

    def node(value, bound=frozenset()):
        nonlocal count
        count += 1
        n = {'node_id': f'{prefix}.{count}'}
        if isinstance(value, str):
            if value in ('true', 'false'):
                return {**n, 'op': 'literal', 'type': 'bool', 'value': value == 'true'}
            name = atom(value)
            if not re.fullmatch(r'[a-z][a-zA-Z0-9_.:-]*', name): raise LegalMathError('E_SCHEMA')
            return {**n, 'op': 'var' if name in bound else 'fact', 'name': name}
        op, *args = value
        if op == 'fact' and len(args) == 1:
            return {**n,'op':'fact','name':atom(args[0])}
        if op in ('integer', 'money_hkd', 'date') and len(args) == 1 and isinstance(args[0], str):
            return {**n, 'op': 'literal', 'type': op, 'value': args[0]}
        if op == 'decimal' and len(args) == 2 and all(isinstance(x, str) for x in args):
            return {**n, 'op': 'literal', 'type': 'decimal', 'value': {'numerator': args[0], 'denominator': args[1]}}
        if op in ('map', 'filter') and len(args) == 3:
            binding = atom(args[0])
            return {**n, 'op': op, 'arg': node(args[1], bound), 'binding': binding,
                    'body': node(args[2], bound | {binding})}
        if op == 'field' and len(args) == 2:
            return {**n, 'op': 'field', 'arg': node(args[0], bound), 'field': atom(args[1])}
        if op == 'list' and args:
            return {**n, 'op': 'list', 'type': atom(args[0]), 'args': [node(a, bound) for a in args[1:]]}
        if op == 'none' and len(args) == 1:
            return {**n, 'op': 'none', 'type': atom(args[0])}
        if op == 'option' and len(args) == 4:
            binding = atom(args[1])
            return {**n, 'op': 'option', 'arg': node(args[0], bound), 'binding': binding,
                    'present': node(args[2], bound | {binding}), 'absent': node(args[3], bound)}
        if op == 'variant' and len(args) in (2, 3):
            return {**n, 'op': 'variant', 'type': atom(args[0]), 'case': atom(args[1]),
                    'arg': node(args[2], bound) if len(args) == 3 else None}
        if op == 'match' and len(args) >= 2:
            arg = node(args[0], bound); arms = []
            for arm in args[1:]:
                if not isinstance(arm, list) or len(arm) != 3: raise LegalMathError('E_SCHEMA')
                case, binding, body = arm; binding = None if binding == '_' else atom(binding)
                arms.append({'case': atom(case), 'binding': binding,
                             'body': node(body, bound | ({binding} if binding else set()))})
            return {**n, 'op': 'match', 'arg': arg, 'arms': arms}
        children = [node(a, bound) for a in args]
        if op in ('and', 'or') and children:
            return {**n, 'op': 'all' if op == 'and' else 'any', 'args': children}
        if op in ('not', 'sum', 'some') and len(children) == 1:
            return {**n, 'op': op, 'arg': children[0]}
        if op == 'if' and len(children) == 3:
            return {**n, 'op': 'if', 'condition': children[0], 'then': children[1], 'else': children[2]}
        if op in ('=', '>', '>=', '+', '-', '*') and len(children) == 2:
            n.update(op='compare' if op in ('=', '>', '>=') else {'+': 'add', '-': 'sub', '*': 'mul'}[op],
                     left=children[0], right=children[1])
            if n['op'] == 'compare': n['cmp'] = {'=': 'eq', '>': 'gt', '>=': 'ge'}[op]
            return n
        raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Unsupported operator or arity: ' + str(op))

    return node(parsed)
