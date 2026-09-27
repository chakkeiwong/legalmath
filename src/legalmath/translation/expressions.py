"""Target-independent expression syntax; parsing never invokes a model or runtime."""
import re
from ..errors import LegalMathError


def expression(text, prefix, *, parameters=(), interpretation_id='reading', source_span_ids=()):
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
        if op in ('fact', 'rule') and len(args) == 1:
            return {**n,'op':op,'name':atom(args[0])}
        if op in ('call', 'library') and args:
            return {**n, 'op':op, 'name':atom(args[0]), 'args':[node(a,bound) for a in args[1:]]}
        if op == 'record' and args:
            fields = []
            for field in args[1:]:
                if not isinstance(field,list) or len(field)!=2: raise LegalMathError('E_SCHEMA')
                fields.append({'name':atom(field[0]),'value':node(field[1],bound)})
            return {**n,'op':'record','type':atom(args[0]),'fields':fields}
        if op == 'scale' and len(args)==3 and all(isinstance(x,str) for x in args[1:]):
            return {**n,'op':'scale','arg':node(args[0],bound),'numerator':args[1],'denominator':args[2]}
        if op == 'round' and len(args)==3:
            return {**n,'op':'round','type':atom(args[0]),'mode':atom(args[1]),'arg':node(args[2],bound)}
        if op == 'default' and args:
            base=node(args[0],bound);exceptions=[]
            for ex in args[1:]:
                if not isinstance(ex,list) or len(ex)!=4 or ex[0]!='exception': raise LegalMathError('E_SCHEMA')
                exceptions.append({'exception_id':atom(ex[1]),'guard':node(ex[2],bound),'value':node(ex[3],bound),
                                   'interpretation_id':interpretation_id,'source_span_ids':list(source_span_ids)})
            return {**n,'op':'default','base':base,'exceptions':exceptions}
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

    return node(parsed, frozenset(parameters))
