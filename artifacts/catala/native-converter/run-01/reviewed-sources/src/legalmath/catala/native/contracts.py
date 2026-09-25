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

Name = Annotated[str, Field(pattern=r'^[a-z][a-zA-Z0-9_]{0,63}$')]
TypeName = Annotated[str, Field(pattern=r'^[A-Z][a-zA-Z0-9]{0,63}$')]
SCALARS = {'boolean', 'integer', 'decimal', 'money', 'date'}


class Fact(Strict):
    name: Name
    type: str
    meaning: Text
    unit: Text


class DataType(Strict):
    name: TypeName
    kind: Literal['record', 'enum']
    fields: list[Fact] = Field(max_length=40)
    cases: list[TypeName] = Field(max_length=40)


class Task(Strict):
    record_type: Literal['NativeCatalaTask']
    task_id: Id
    packet: Packet
    question: Text
    entry_scope: TypeName
    types: list[DataType] = Field(max_length=30)
    inputs: list[Fact] = Field(min_length=1, max_length=40)
    outputs: list[Fact] = Field(min_length=1, max_length=40)
    valid_from: str
    valid_until: str | None


class Anchor(Strict):
    unit_id: Id
    quote: Text
    code_excerpt: Text


class Candidate(Strict):
    record_type: Literal['NativeCatalaCandidate']
    task_hash: Hash
    source: Annotated[str, Field(min_length=1, max_length=64000)]
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


def validate_task(value):
    t = parse(Task, value)
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
        unique(d['cases'])
    for name in defs:
        visit(name)
    unique([f['name'] for f in t['inputs'] + t['outputs']])
    for f in t['inputs'] + t['outputs']:
        visit(f['type'])
    return t


def catala_type(typ):
    sub = item_type(typ)
    return 'list of ' + catala_type(sub) if sub is not None else typ


def header(task):
    """Only declarations; all computations stay in the candidate's Catala source."""
    t = validate_task(task)
    lines = ['# Declared factual interface', '```catala']
    for d in t['types']:
        lines.append('declaration ' + ('structure ' if d['kind'] == 'record' else 'enumeration ') + d['name'] + ':')
        if d['kind'] == 'record':
            lines += [f"  data {f['name']} content {catala_type(f['type'])}" for f in d['fields']]
        else:
            lines += ['  -- ' + name for name in d['cases']]
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
        fail('E_SCHEMA', 'Missing or unclosed executable Catala fence')
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
            if value not in definition['cases']:
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
        return typ + '.' + value
    return typ + ' { ' + ' '.join('-- ' + f['name'] + ': ' + literal(task, f['type'], value[f['name']]) for f in d['fields']) + ' }'
