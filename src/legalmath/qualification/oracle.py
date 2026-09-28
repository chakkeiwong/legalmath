"""Independent exact evaluator of formal proposals for generated challenges.

This evaluator consumes source expressions, never lowered model/target code or
expected legal answers. It covers complete factual values; other observations
remain unsupported evidence, not silently coerced truth values.
"""
import calendar
from datetime import date, timedelta
from fractions import Fraction

from ..errors import LegalMathError
from .proof import parse, unsupported


class Outcome(Exception):
    def __init__(self, status, reason=None):
        self.status, self.reason = status, reason


def unpack(typ, value, types):
    if typ in ('integer', 'money_hkd'):
        return int(value)
    if typ == 'decimal':
        return Fraction(int(value['numerator']), int(value['denominator']))
    if typ == 'bool':
        return value
    if typ == 'date':
        return date.fromisoformat(value)
    if typ.startswith('list['):
        return [unpack(typ[5:-1], x, types) for x in value]
    if typ.startswith('optional['):
        return None if value is None else {'present': unpack(typ[9:-1], value['present'], types)}
    d = types[typ]
    if d['kind'] == 'record':
        return {f['name']: unpack(f['type'], value[f['name']], types) for f in d['fields']}
    if isinstance(value, str):
        return value
    case = next(c for c in d['cases'] if c['name'] == value['case'])
    return {'case': value['case'], 'value': unpack(case['type'], value['value'], types) if case['type'] else None}


def pack(typ, value, types):
    if typ in ('integer', 'money_hkd'):
        return str(value)
    if typ == 'decimal':
        q = Fraction(value)
        return {'numerator': str(q.numerator), 'denominator': str(q.denominator)}
    if typ == 'bool':
        return value
    if typ == 'date':
        return value.isoformat()
    if typ.startswith('list['):
        return [pack(typ[5:-1], x, types) for x in value]
    if typ.startswith('optional['):
        return None if value is None else {'present': pack(typ[9:-1], value['present'], types)}
    d = types[typ]
    if d['kind'] == 'record':
        return {f['name']: pack(f['type'], value[f['name']], types) for f in d['fields']}
    if isinstance(value, str):
        return value
    case = next(c for c in d['cases'] if c['name'] == value['case'])
    return {'case': value['case'], 'value': pack(case['type'], value['value'], types) if case['type'] else None}


def evaluate(formal, snapshot):
    types = {t['name']: t for t in formal.get('types', [])}
    facts = {}
    for f in formal['facts']:
        observed = snapshot['facts'][f['name']]
        if observed['status'] != 'known' or observed.get('complete', True) is not True:
            unsupported('Independent challenge evaluator requires complete known facts')
        facts[f['name']] = unpack(f['type'], observed['value'], types)
    outputs = formal.get('outputs', [{'id': 'selected.control', 'result_type': formal.get('result_type'),
                                    'scope': formal.get('scope'), 'result': formal.get('result')}])
    rules = {o['id']: o for o in outputs}; helpers = {h['name']: h for h in formal.get('helpers', [])}
    visits = 0

    def run(x, env, depth=0):
        nonlocal visits
        visits += 1
        if visits > 100000 or depth > 128:
            unsupported('Independent evaluator resource limit')
        if isinstance(x, str):
            return True if x == 'true' else False if x == 'false' else env[x]
        op, *args = x; go = lambda y: run(y, env, depth + 1)
        def strict(expressions):
            values=[]; failures=[]
            for expression in expressions:
                try: values.append(go(expression))
                except Outcome as exc: failures.append(exc)
            if failures:
                # All operands/guards are evaluated; a later arithmetic error
                # must not disappear behind an earlier default conflict.
                raise max(failures,key=lambda e:{'UNKNOWN':1,'CONFLICT':2,'ERROR':3,'OUT_OF_SCOPE':4}[e.status])
            return values
        def composite(expression, local=env):
            try: return run(expression,local,depth+1)
            except Outcome:
                unsupported('Nested partial/error values are outside the complete-value independent evaluator')
        if op in ('integer', 'money_hkd'):
            return int(args[0])
        if op == 'decimal':
            return Fraction(int(args[0]), int(args[1]))
        if op == 'date':
            return date.fromisoformat(args[0])
        if op == 'fact':
            return facts[args[0]]
        if op == 'rule':
            return rule(args[0], depth + 1)
        if op == 'call':
            h = helpers[args[0]]; values = strict(args[1:])
            return run(parse(h['body']), dict(zip([p['name'] for p in h['parameters']], values)), depth + 1)
        if op == 'if':
            return go(args[1] if go(args[0]) else args[2])
        if op == 'default':
            guards = strict([a[2] for a in args[1:]])
            selected = [a[3] for a,g in zip(args[1:],guards) if g]
            if len(selected) > 1:
                raise Outcome('CONFLICT', 'EXCEPTION_OVERLAP')
            return go(selected[0] if selected else args[0])
        if op in ('map', 'filter'):
            values = go(args[1]); result = []
            for value in values:
                item = composite(args[2], {**env, args[0]: value})
                if op == 'map': result.append(item)
                elif item: result.append(value)
            return result
        if op == 'record':
            return {a[0]: composite(a[1]) for a in args[1:]}
        if op == 'field':
            return go(args[0])[args[1]]
        if op == 'list':
            return [composite(a) for a in args[1:]]
        if op == 'none':
            return None
        if op == 'some':
            return {'present': composite(args[0])}
        if op == 'option':
            value = go(args[0])
            return go(args[3]) if value is None else run(args[2], {**env, args[1]: value['present']}, depth + 1)
        if op == 'variant':
            mixed = any(c['type'] for c in types[args[0]]['cases'])
            return {'case': args[1], 'value': composite(args[2]) if len(args) == 3 else None} if mixed else args[1]
        if op == 'match':
            value = go(args[0]); tag = value if isinstance(value, str) else value['case']
            arm = next(a for a in args[1:] if a[0] == tag)
            return run(arm[2], env if arm[1] == '_' else {**env, arm[1]: value['value']}, depth + 1)
        if op == 'scale':
            q = Fraction(go(args[0]) * int(args[1]), int(args[2]))
            if q.denominator != 1:
                raise Outcome('ERROR', 'E_INEXACT_SCALE')
            return q.numerator
        if op == 'round':
            q = Fraction(go(args[2])); mode = args[1]
            floor = q.numerator // q.denominator
            if mode == 'floor': return floor
            if mode == 'ceiling': return -((-q.numerator) // q.denominator)
            if mode == 'toward_zero': return int(q)
            if mode == 'nearest_away':
                magnitude = abs(q) + Fraction(1, 2)
                return (1 if q >= 0 else -1) * (magnitude.numerator // magnitude.denominator)
            unsupported('Unknown rounding policy')
        if op == 'library':
            name = args[0]; values = strict(args[1:])
            if name == 'numeric.min': return min(values)
            if name == 'numeric.max': return max(values)
            if name == 'list.length': return len(values[0])
            if name == 'list.sequence':
                if values[1] - values[0] > 10000: raise Outcome('ERROR', 'E_RESOURCE_LIMIT')
                return list(range(*values))
            try:
                d = values[0]
                if name == 'date.month_end': return d.replace(day=calendar.monthrange(d.year, d.month)[1])
                if name == 'date.add_days': return d + timedelta(days=values[1])
                if name == 'date.add_months_clamped':
                    year, month = divmod(d.year * 12 + d.month - 1 + values[1], 12); month += 1
                    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))
            except (ValueError, OverflowError):
                raise Outcome('ERROR', 'E_DATE_RANGE')
            unsupported('Unregistered library operation')
        values = strict(args)
        if op == 'and': return all(values)
        if op == 'or': return any(values)
        if op == 'not': return not values[0]
        if op == '+': return values[0] + values[1]
        if op == '-': return values[0] - values[1]
        if op == '*': return values[0] * values[1]
        if op == '=': return values[0] == values[1]
        if op == '>': return values[0] > values[1]
        if op == '>=': return values[0] >= values[1]
        if op == 'sum': return sum(values[0])
        unsupported('Unregistered independent evaluation operation: ' + str(op))

    def rule(name, depth=0):
        r = rules[name]
        if not run(parse(r['scope']), facts, depth + 1):
            raise Outcome('OUT_OF_SCOPE')
        return run(parse(r['result']), facts, depth + 1)

    results = {}
    for out in outputs:
        try:
            value = pack(out['result_type'], rule(out['id']), types)
            status = ('TRUE' if value else 'FALSE') if out['result_type'] == 'bool' else 'VALUE'
            results[out['id']] = {'status': status, 'type': out['result_type'], 'value': value, 'reason': None}
        except Outcome as exc:
            results[out['id']] = {'status': exc.status, 'type': out['result_type'], 'value': None, 'reason': exc.reason}
    return results
