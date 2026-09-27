"""Source commitments and an acyclic factual interface, not an executable IR."""
import re
from datetime import date
from fractions import Fraction
from typing import Annotated, Literal
from pydantic import Field
from ...canonical import canonical, digest
from ...domain import interval, timestamp
from ...errors import LegalMathError
from ...interpretation.contracts import Strict, Packet, Hash, Id, Text, parse
from .semantics import require_profile

Name = Annotated[str, Field(pattern=r'^[a-z][a-zA-Z0-9_]{0,63}$')]
TypeName = Annotated[str, Field(pattern=r'^[A-Z][a-zA-Z0-9]{0,63}$')]
SCALARS = {'boolean', 'integer', 'decimal', 'money', 'date'}


class Fact(Strict):
    name: Name
    type: str
    meaning: Text
    unit: Text


class EnumCase(Strict):
    name: TypeName
    type: str | None


class DataType(Strict):
    name: TypeName
    kind: Literal['record', 'enum']
    fields: list[Fact] = Field(max_length=40)
    cases: list[TypeName | EnumCase] = Field(max_length=40)


class Bound(Strict):
    input: Name
    minimum: str | None
    maximum: str | None
    unit_id: Id
    quote: Text


class Task(Strict):
    record_type: Literal['NativeCatalaTask']
    task_id: Id
    packet: Packet
    question: Text
    entry_scope: TypeName
    types: list[DataType] = Field(max_length=30)
    inputs: list[Fact] = Field(min_length=1, max_length=40)
    outputs: list[Fact] = Field(min_length=1, max_length=40)
    bounds: list[Bound] = Field(default_factory=list, max_length=40)
    valid_from: str
    valid_until: str | None
    native_profile: Literal['legalmath.catala.native.v2'] | None = None
    imports: list[Literal['Integer_en', 'Decimal_en', 'Money_en', 'Date_en', 'List_en']] = Field(default_factory=list, max_length=5)


class Anchor(Strict):
    unit_id: Id
    quote: Text
    code_excerpt: Text


class Candidate(Strict):
    record_type: Literal['NativeCatalaCandidate']
    task_hash: Hash
    source: Annotated[str, Field(
        min_length=1, max_length=64000,
        description='Executable Catala program text inside closed ```catala code fences. '
                    'Implement the task entry scope. This field contains code, not a source '
                    'identifier, citation, quotation, path, or the supplied interface declaration.')]
    interpretation: Text
    assumptions: list[Text] = Field(max_length=40)
    unresolved: list[Text] = Field(max_length=40)
    anchors: list[Anchor] = Field(min_length=1, max_length=100)


class Criticism(Strict):
    verdict: Literal['SUPPORTED', 'CHALLENGED', 'UNRESOLVED']
    findings: list[Text] = Field(max_length=40)


def fail(code='E_SCHEMA', detail='Invalid native profile'):
    raise LegalMathError(code, details=detail)


def unique(names):
    if len(names) != len(set(names)):
        fail('E_DUPLICATE_ID')


def item_type(typ):
    return typ[5:-1] if typ.startswith('list[') and typ.endswith(']') else None


def option_type(typ):
    return typ[9:-1] if typ.startswith('optional[') and typ.endswith(']') else None


def enum_cases(definition):
    return [({'name': c, 'type': None} if isinstance(c, str) else c) for c in definition['cases']]


def validate_task(value):
    t = parse(Task, value)
    # Preserve commitments of earlier tasks whose interface had no declared bounds.
    if 'bounds' not in value:
        t.pop('bounds')
    for key in ('native_profile', 'imports'):
        if key not in value:
            t.pop(key)
    if 'native_profile' in t and t['native_profile'] is None:
        fail('E_SCHEMA')
    if t.get('imports'):
        require_profile(t)
        unique(t['imports'])
    interval(t['valid_from'], t['valid_until'])
    names = [x['name'] for x in t['types']]
    unique(names + [t['entry_scope'], 'Native', 'NativeCheck'])
    unique([u['unit_id'] for u in t['packet']['units']])
    defs = {d['name']: d for d in t['types']}

    def visit(typ, trail=()):
        if len(trail) > 12:
            fail('E_RESOURCE_LIMIT', 'Type depth exceeds 12')
        if typ in SCALARS:
            return
        optional = option_type(typ)
        if optional is not None:
            require_profile(t)
            visit(optional, trail + (typ,))
            return
        sub = item_type(typ)
        if sub is not None:
            visit(sub, trail + (typ,))
            return
        if typ in trail:
            fail('E_CYCLE')
        if typ not in defs:
            fail('E_TYPE', 'Undeclared type: ' + typ)
        d = defs[typ]
        if d['kind'] == 'record':
            if not d['fields'] or d['cases']:
                fail()
            unique([f['name'] for f in d['fields']])
            for f in d['fields']:
                visit(f['type'], trail + (typ,))
        elif not d['cases'] or d['fields']:
            fail()
        unique([c['name'] for c in enum_cases(d)])
        for c in enum_cases(d):
            if c['type'] is not None:
                require_profile(t)
                visit(c['type'], trail + (typ,))
    for name in defs:
        visit(name)
    unique([f['name'] for f in t['inputs'] + t['outputs']])
    for f in t['inputs'] + t['outputs']:
        visit(f['type'])
    unique([b['input'] for b in t.get('bounds', [])])
    inputs = {f['name']: f for f in t['inputs']}
    units = {u['unit_id']: u['text'] for u in t['packet']['units']}
    for b in t.get('bounds', []):
        if b['input'] not in inputs or inputs[b['input']]['type'] not in ('integer', 'decimal', 'money'):
            fail('E_TYPE', 'Bounds require a declared numeric input')
        if b['unit_id'] not in units or b['quote'] not in units[b['unit_id']]:
            fail('E_REFERENCE', 'Input bounds require an exact source quotation')
        if b['minimum'] is None and b['maximum'] is None:
            fail('E_SCHEMA', 'Empty input bound')
        for bound in (b['minimum'], b['maximum']):
            if bound is None:
                continue
            try:
                valid = len(bound) <= 1000 and str(Fraction(bound)) == bound
            except (ValueError, ZeroDivisionError):
                valid = False
            if not valid:
                fail('E_TYPE', 'Bounds require canonical exact rational strings')
        if b['minimum'] is not None and b['maximum'] is not None and Fraction(b['minimum']) > Fraction(b['maximum']):
            fail('E_SCHEMA', 'Reversed input bounds')
    return t


def outside_domain(task, inputs):
    invalid = []
    for b in task.get('bounds', []):
        if b['input'] not in inputs:
            continue
        value = inputs[b['input']]
        n = Fraction(int(value['numerator']), int(value['denominator'])) if isinstance(value, dict) else Fraction(value)
        if ((b['minimum'] is not None and n < Fraction(b['minimum'])) or
                (b['maximum'] is not None and n > Fraction(b['maximum']))):
            invalid.append(b['input'])
    return sorted(invalid)


def catala_type(typ):
    optional = option_type(typ)
    if optional is not None:
        return 'optional of ' + catala_type(optional)
    sub = item_type(typ)
    return 'list of ' + catala_type(sub) if sub is not None else typ


def header(task):
    """Only declarations; all computations stay in the candidate's Catala source."""
    t = validate_task(task)
    lines = ['# Declared factual interface']
    lines += ['> Using ' + name + ' as ' + name.removesuffix('_en') for name in t.get('imports', [])]
    lines.append('```catala')
    for d in t['types']:
        lines.append('declaration ' + ('structure ' if d['kind'] == 'record' else 'enumeration ') + d['name'] + ':')
        if d['kind'] == 'record':
            lines += [f"  data {f['name']} content {catala_type(f['type'])}" for f in d['fields']]
        else:
            lines += ['  -- ' + c['name'] + (' content ' + catala_type(c['type']) if c['type'] else '') for c in enum_cases(d)]
        lines.append('')
    lines.append('declaration scope ' + t['entry_scope'] + ':')
    for direction in ('input', 'output'):
        lines += [f"  {direction} {f['name']} content {catala_type(f['type'])}" for f in t[direction + 's']]
    return '\n'.join(lines + ['```', ''])


def validate_candidate(task, value):
    t = validate_task(task)
    c = parse(Candidate, value)
    if c['task_hash'] != digest(t):
        fail('E_HASH_MISMATCH', 'Candidate task commitment')
    if len(c['source'].encode()) > 64000:
        fail('E_RESOURCE_LIMIT')
    # Model-controlled imports, plugins and file inclusion are outside this profile.
    code = []
    inside = False
    for line in c['source'].splitlines():
        if line.startswith('```'):
            if line == '```catala' and not inside:
                inside = True
            elif line == '```' and inside:
                inside = False
            else:
                fail('E_UNSUPPORTED_PROFILE', 'Only closed catala code fences are supported')
        elif inside:
            if '#[' in line or re.match(r'\s*>', line):
                fail('E_UNSUPPORTED_PROFILE', 'Attributes and directives are not allowed')
            code.append(line)
        elif re.match(r'\s*>', line):
            fail('E_UNSUPPORTED_PROFILE', 'Imports and includes require a separately pinned profile')
    if inside or not code:
        fail('E_SCHEMA', 'Candidate.source must contain executable scope definitions inside '
             'closed ```catala fences; a source citation is not executable code')
    joined = '\n'.join(code)
    if not re.search(r'^scope\s+' + re.escape(t['entry_scope']) + r'\s*:', joined, re.M):
        fail('E_REFERENCE', 'Missing entry scope implementation')
    units = {u['unit_id']: u for u in t['packet']['units']}
    covered = set()
    for a in c['anchors']:
        unit = units.get(a['unit_id'])
        if unit is None or a['quote'] not in unit['text'] or a['code_excerpt'] not in joined:
            fail('E_REFERENCE', 'Source anchor must quote retained text and executable code')
        covered.add(a['unit_id'])
    if {u['unit_id'] for u in units.values() if u['normative']} - covered:
        fail('E_REFERENCE', 'Normative source units lack a disposition')
    return c


def program(task, candidate):
    c = validate_candidate(task, candidate)
    return header(task) + '\n' + c['source'] + '\n'


def source_map(task, candidate):
    source = program(task, candidate)
    result = []
    for a in candidate['anchors']:
        # Every occurrence is retained; source coordinates are calculated, not model supplied.
        starts = [m.start() for m in re.finditer(re.escape(a['code_excerpt']), source)]
        result.append({**a, 'lines': [source.count('\n', 0, p) + 1 for p in starts]})
    return result


def validate_value(task, typ, value, depth=0):
    if depth > 12:
        fail('E_RESOURCE_LIMIT')
    optional = option_type(typ)
    if optional is not None:
        if value is None:
            return value
        if type(value) is not dict or set(value) != {'present'}:
            fail('E_TYPE', 'Option requires null or a present wrapper')
        validate_value(task, optional, value['present'], depth + 1)
        return value
    sub = item_type(typ)
    if sub is not None:
        if type(value) is not list:
            fail('E_TYPE')
        if len(value) > 10000:
            fail('E_RESOURCE_LIMIT')
        return [validate_value(task, sub, v, depth + 1) for v in value]
    if typ == 'boolean':
        if type(value) is not bool:
            fail('E_TYPE')
    elif typ in ('integer', 'money'):
        if type(value) is not str or not re.fullmatch(r'0|-?[1-9][0-9]{0,999}', value):
            fail('E_TYPE', 'Integer and money minor units require canonical integer strings')
    elif typ == 'decimal':
        if type(value) is not dict or set(value) != {'numerator', 'denominator'}:
            fail('E_TYPE', 'Decimals require exact numerator/denominator strings')
        for key in value:
            validate_value(task, 'integer', value[key])
        n, d = int(value['numerator']), int(value['denominator'])
        if d <= 0 or Fraction(n, d).denominator != d or Fraction(n, d).numerator != n:
            fail('E_TYPE', 'Rationals must be reduced with positive denominator')
    elif typ == 'date':
        if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            fail('E_TYPE')
        try:
            date.fromisoformat(value)
        except ValueError:
            fail('E_TYPE')
    else:
        definition = next(d for d in task['types'] if d['name'] == typ)
        if definition['kind'] == 'enum':
            cases = enum_cases(definition)
            if any(c['type'] for c in cases):
                if type(value) is not dict or set(value) != {'case', 'value'}:
                    fail('E_TYPE')
                case = next((c for c in cases if c['name'] == value['case']), None)
                if case is None:
                    fail('E_TYPE')
                if case['type'] is None:
                    if value['value'] is not None:
                        fail('E_TYPE')
                else:
                    validate_value(task, case['type'], value['value'], depth + 1)
            elif value not in [c['name'] for c in cases]:
                fail('E_TYPE')
        else:
            fields = definition['fields']
            if type(value) is not dict or set(value) != {f['name'] for f in fields}:
                fail('E_TYPE')
            for f in fields:
                validate_value(task, f['type'], value[f['name']], depth + 1)
    return value


def literal(task, typ, value):
    validate_value(task, typ, value)
    optional = option_type(typ)
    if optional is not None:
        return 'Absent' if value is None else '(Present content ' + literal(task, optional, value['present']) + ')'
    sub = item_type(typ)
    if sub is not None:
        return '[' + '; '.join(literal(task, sub, v) for v in value) + ']'
    if typ == 'boolean':
        return 'true' if value else 'false'
    if typ == 'integer':
        return '(' + value + ')'
    if typ == 'decimal':
        return '(' + value['numerator'] + '.0 / ' + value['denominator'] + '.0)'
    if typ == 'money':
        n = int(value)
        return ('(-' if n < 0 else '(') + '$' + str(abs(n)//100) + '.' + f'{abs(n)%100:02d}' + ')'
    if typ == 'date':
        return '|' + value + '|'
    d = next(d for d in task['types'] if d['name'] == typ)
    if d['kind'] == 'enum':
        if isinstance(value, str):
            return typ + '.' + value
        case = next(c for c in enum_cases(d) if c['name'] == value['case'])
        return '(' + typ + '.' + case['name'] + (' content ' + literal(task, case['type'], value['value']) if case['type'] else '') + ')'
    return typ + ' { ' + ' '.join('-- ' + f['name'] + ': ' + literal(task, f['type'], value[f['name']]) for f in d['fields']) + ' }'
