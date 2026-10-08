"""Independent cvc5 encoding of valid RuleIR status/type/value semantics.

Scope includes rule references, lazy branches, defaults, exact arithmetic,
dates and conflict preflight. Source interpretation, validation diagnostics,
trace/provenance and JVM behaviour are separate obligations.
"""
from datetime import date

from ...canonical import digest
from ...integer import parse as integer, decimal
from ...ir.typecheck import validate_bundle, validate_snapshot
from ...domain import timestamp

TAGS = {'UNKNOWN': 0, 'TRUE': 1, 'FALSE': 2, 'VALUE': 3,
        'OUT_OF_SCOPE': 4, 'CONFLICT': 5, 'ERROR': 6}
NAMES = {v: k for k, v in TAGS.items()}


def integer_value(term):
    """Read an exact solver numeral without Python's decimal conversion limit."""
    text = str(term)
    if text.startswith('(- ') and text.endswith(')'):
        text = '-' + text[3:-1]
    return integer(text)


class Encoder:
    def __init__(self, bundle, tm, variables):
        from cvc5 import Kind
        self.k, self.tm, self.variables = Kind, tm, variables
        self.rules = {r['id']: r for r in bundle['rules']}
        self.memo = {}

    def n(self, value): return self.tm.mkInteger(decimal(value) if type(value) is int else value)
    def op(self, kind, *args): return self.tm.mkTerm(kind, *args)
    def eq(self, a, b): return self.op(self.k.EQUAL, a, b)
    def ite(self, c, a, b): return self.op(self.k.ITE, c, a, b)
    def any(self, values):
        return self.tm.mkBoolean(False) if not values else values[0] if len(values) == 1 else self.op(self.k.OR, *values)
    def all(self, values):
        return self.tm.mkBoolean(True) if not values else values[0] if len(values) == 1 else self.op(self.k.AND, *values)
    def has(self, values, status): return self.any([self.eq(v[1], self.n(status)) for v in values])
    def precedence(self, values, status):
        return self.ite(self.has(values, 6), self.n(6), self.ite(self.has(values, 5), self.n(5), status))

    def expression(self, node):
        op = node['op']; k = self.k
        if op == 'fact': return self.variables[node['name']]
        if op == 'rule': return self.rule(node['name'])
        if op == 'literal':
            typ, value = node['type'], node['value']
            numeric = int(value) if typ == 'bool' else date.fromisoformat(value).toordinal() if typ == 'date' else value
            return typ, self.n((1 if value else 2) if typ == 'bool' else 3), self.n(numeric)
        if op in ('all', 'any'):
            values = [self.expression(a) for a in node['args']]
            target, other = (2, 1) if op == 'all' else (1, 2)
            status = self.ite(self.has(values, target), self.n(target),
                             self.ite(self.has(values, 0), self.n(0), self.n(other)))
            status = self.precedence(values, status)
            return 'bool', status, self.ite(self.eq(status, self.n(1)), self.n(1), self.n(0))
        if op == 'not':
            a = self.expression(node['arg'])
            status = self.ite(self.eq(a[1], self.n(1)), self.n(2),
                              self.ite(self.eq(a[1], self.n(2)), self.n(1), a[1]))
            return 'bool', status, self.ite(self.eq(status, self.n(1)), self.n(1), self.n(0))
        if op == 'if':
            c, a, b = [self.expression(node[key]) for key in ('condition', 'then', 'else')]
            status = self.ite(self.eq(c[1], self.n(1)), a[1],
                              self.ite(self.eq(c[1], self.n(2)), b[1], c[1]))
            return a[0], status, self.ite(self.eq(c[1], self.n(1)), a[2], b[2])
        if op == 'default':
            base = self.expression(node['base'])
            guards = [self.expression(e['guard']) for e in node['exceptions']]
            choices = [self.expression(e['value']) for e in node['exceptions']]
            status, value = base[1:]
            for g, choice in reversed(list(zip(guards, choices))):
                selected = self.eq(g[1], self.n(1))
                status, value = self.ite(selected, choice[1], status), self.ite(selected, choice[2], value)
            counts = [self.ite(self.eq(g[1], self.n(1)), self.n(1), self.n(0)) for g in guards]
            total = self.n(0) if not counts else counts[0] if len(counts) == 1 else self.op(k.ADD, *counts)
            status = self.ite(self.op(k.GT, total, self.n(1)), self.n(5),
                              self.ite(self.has(guards, 0), self.n(0), status))
            return base[0], self.precedence(guards, status), value
        if op == 'scale':
            a = self.expression(node['arg'])
            numerator, denominator = self.n(node['numerator']), self.n(node['denominator'])
            value = self.op(k.MULT, a[2], numerator)
            exact = self.eq(self.op(k.INTS_MODULUS, value, denominator), self.n(0))
            status = self.ite(self.eq(a[1], self.n(3)), self.ite(exact, self.n(3), self.n(6)), a[1])
            return a[0], status, self.op(k.INTS_DIVISION, value, denominator)
        a, b = self.expression(node['left']), self.expression(node['right'])
        known = self.all([self.eq(v[1], self.n(3)) for v in (a, b)])
        if op == 'compare':
            relation = self.op({'eq': k.EQUAL, 'gt': k.GT, 'ge': k.GEQ}[node['cmp']], a[2], b[2])
            status = self.ite(known, self.ite(relation, self.n(1), self.n(2)), self.n(0))
            return 'bool', self.precedence([a, b], status), self.ite(relation, self.n(1), self.n(0))
        if op not in ('add', 'sub'): raise ValueError('Unsupported operator: '+op)
        status = self.precedence([a, b], self.ite(known, self.n(3), self.n(0)))
        return a[0], status, self.op(k.ADD if op == 'add' else k.SUB, a[2], b[2])

    def rule(self, name):
        if name not in self.memo:
            rule = self.rules[name]
            scope, body = self.expression(rule['scope']), self.expression(rule['body'])
            status = self.ite(self.eq(scope[1], self.n(1)), body[1],
                self.ite(self.eq(scope[1], self.n(2)), self.n(4), scope[1]))
            self.memo[name] = rule['type'], status, body[2]
        return self.memo[name]

    def dependencies(self, name, seen=None):
        seen = set() if seen is None else seen
        if name in seen: return set()
        seen.add(name); found = set()
        def scan(value):
            if isinstance(value, dict):
                if value.get('op') == 'fact': found.add(value['name'])
                if value.get('op') == 'rule': found.update(self.dependencies(value['name'], seen))
                for child in value.values(): scan(child)
            elif isinstance(value, list):
                for child in value: scan(child)
        scan(self.rules[name]); return found

    def decision(self, name):
        typ, status, value = self.rule(name)
        conflict = self.any([self.eq(self.variables[f][1], self.n(5)) for f in self.dependencies(name)])
        return typ, self.ite(conflict, self.n(5), status), value


def session(timeout_ms=5000):
    import cvc5
    if type(timeout_ms) is not int or not 1 <= timeout_ms <= 30000: raise ValueError('Invalid solver budget')
    tm = cvc5.TermManager(); solver = cvc5.Solver(tm)
    solver.setLogic('QF_NIA'); solver.setOption('produce-models', 'true')
    solver.setOption('tlimit-per', str(timeout_ms))
    return tm, solver


def evaluate_snapshot(bundle, snapshot, rule_id, valid_at, known_at):
    """Concrete independent calculation, with shared structural validation disclosed."""
    timestamp(valid_at); timestamp(known_at)
    if validate_bundle(bundle) or validate_snapshot(bundle, snapshot):
        return {'status': 'UNSUPPORTED', 'reason': 'INVALID_INPUT'}
    tm, solver = session(); variables = {}
    for f in bundle['facts']:
        record = snapshot['facts'][f['name']]; typ = f['type']; value = 0
        status = 5 if record['status'] == 'conflict' else 0
        if (record['status'] == 'known' and record['valid_from'] <= valid_at and
            (record['valid_until'] is None or valid_at < record['valid_until']) and record['recorded_at'] <= known_at):
            raw = record['value']
            status = (1 if raw else 2) if typ == 'bool' else 3
            value = int(raw) if typ == 'bool' else date.fromisoformat(raw).toordinal() if typ == 'date' else raw
        variables[f['name']] = typ, tm.mkInteger(status), tm.mkInteger(str(value))
    encoder = Encoder(bundle, tm, variables)
    typ, state, value = encoder.decision(rule_id)
    if not (bundle['valid_from'] <= valid_at and (bundle['valid_until'] is None or valid_at < bundle['valid_until'])):
        state = tm.mkInteger(6)
    outcome = solver.checkSat()
    if not outcome.isSat():
        return {'status': 'CHECK_INCONCLUSIVE', 'reason': str(outcome)}
    status = solver.getValue(state).getIntegerValue()
    result = {'status': NAMES[status], 'type': typ}
    if status in (1, 2, 3):
        number = integer_value(solver.getValue(value))
        result['value'] = bool(number) if typ == 'bool' else date.fromordinal(number).isoformat() if typ == 'date' else decimal(number)
    return result


def compare_bundles(left, right, rule_id, domain, valid_at, known_at, *, timeout_ms=5000):
    from cvc5 import Kind as K
    timestamp(valid_at); timestamp(known_at)
    base = {'target': 'status/type/value', 'solver': 'cvc5', 'left_hash': digest(left),
            'right_hash': digest(right), 'domain': domain, 'proof_certificate_checked': False,
            'shared_dependencies': ['RuleIR structural validator', 'declared fact meanings'],
            'legal_correctness_established': False, 'release_eligible': False}
    if validate_bundle(left) or validate_bundle(right):
        return {**base, 'status': 'UNSUPPORTED', 'reason': 'INVALID_BUNDLE'}
    if left['facts'] != right['facts'] or set(domain) != {f['name'] for f in left['facts']}:
        return {**base, 'status': 'INCOMPARABLE_FACT_BINDINGS'}
    if any(not (b['valid_from'] <= valid_at and (b['valid_until'] is None or valid_at < b['valid_until'])) for b in (left, right)):
        return {**base, 'status': 'UNSUPPORTED', 'reason': 'VERSION_TIME'}
    tm, solver = session(timeout_ms); variables = {}
    e = Encoder(left, tm, variables)
    for i, fact in enumerate(left['facts']):
        name, typ = fact['name'], fact['type']; d = domain[name]
        s, v = (tm.mkConst(tm.getIntegerSort(), f'f{i}.{suffix}') for suffix in ('state', 'value'))
        allowed = {'T': 1, 'F': 2, 'U': 0, 'C': 5} if typ == 'bool' else {'V': 3, 'U': 0, 'C': 5}
        if not d.get('states') or not set(d['states']) <= set(allowed): raise ValueError('Invalid state domain')
        solver.assertFormula(e.any([e.eq(s, e.n(allowed[t])) for t in d['states']]))
        if typ == 'bool':
            solver.assertFormula(e.eq(v, e.ite(e.eq(s, e.n(1)), e.n(1), e.n(0))))
        else:
            lo, hi = (date.fromisoformat(d[t]).toordinal() if typ == 'date' else d[t] for t in ('min', 'max'))
            bounds = e.all([e.op(K.GEQ, v, e.n(lo)), e.op(K.LEQ, v, e.n(hi))])
            solver.assertFormula(e.op(K.IMPLIES, e.eq(s, e.n(3)), bounds))
        variables[name] = typ, s, v
    domain_check = solver.checkSat()
    if not domain_check.isSat():
        return {**base, 'status': 'INCONSISTENT_DOMAIN' if domain_check.isUnsat() else 'UNKNOWN'}
    a, b = e.decision(rule_id), Encoder(right, tm, variables).decision(rule_id)
    known = e.any([e.eq(a[1], e.n(n)) for n in (1, 2, 3)])
    difference = tm.mkBoolean(True) if a[0] != b[0] else e.any([
        e.op(K.DISTINCT, a[1], b[1]), e.all([known, e.op(K.DISTINCT, a[2], b[2])])])
    solver.assertFormula(difference); outcome = solver.checkSat()
    result = {**base, 'status': 'EQUIVALENT_WITHIN_DOMAIN' if outcome.isUnsat() else 'DIFFERENT' if outcome.isSat() else 'UNKNOWN',
              'difference_formula': str(difference), 'witness': None}
    if outcome.isSat():
        snapshot = {'subject_id': 'synthetic.cvc5', 'facts': {}}
        for name, (typ, s, v) in variables.items():
            state = solver.getValue(s).getIntegerValue()
            row = {'type': typ, 'status': 'unknown', 'reason': 'MISSING'}
            if state == 5: row = {'type': typ, 'status': 'conflict', 'evidence_ids': ['cvc5.a', 'cvc5.b']}
            elif state in (1, 2, 3):
                number = integer_value(solver.getValue(v))
                value = bool(number) if typ == 'bool' else date.fromordinal(number).isoformat() if typ == 'date' else decimal(number)
                row = {'type': typ, 'status': 'known', 'value': value, 'valid_from': valid_at,
                       'valid_until': None, 'recorded_at': known_at, 'evidence_ids': ['cvc5.witness']}
            snapshot['facts'][name] = row
        result['witness'] = snapshot
    return result
