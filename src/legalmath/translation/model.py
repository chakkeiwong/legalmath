"""Typed legal rule model independent of a target language or execution engine."""
from copy import deepcopy
from fractions import Fraction
import re
from typing import Literal, Annotated
from pydantic import Field
from ..canonical import canonical, digest, raw_digest
from ..domain import interval, scalar
from ..errors import LegalMathError
from ..interpretation.contracts import Strict, Id, Text, Packet, parse
from ..sources.anchors import make_span
from ..ir.load import validator as schema_validator
from ..interpretation.search.models import Reading, DimensionFinding, Disposition, validate_generation_metadata
from .expressions import expression

SCALARS = {'bool', 'integer', 'money_hkd', 'date', 'decimal'}
CORE_OPS = {'literal', 'fact', 'rule', 'all', 'any', 'not', 'compare', 'add', 'sub', 'scale', 'if', 'default'}
CORE_TYPES = SCALARS - {'decimal'}
FactName = Annotated[str,Field(pattern=r'^[a-z][a-zA-Z0-9_.:-]{0,127}$')]
ModelId = Annotated[str,Field(pattern=r'^[a-z][a-z0-9_.-]*$')]
OutputId = Annotated[str,Field(pattern=r'^[a-z][a-zA-Z0-9_.-]{0,127}$')]


class RetainedReading(Reading):
    formalization: dict


class TypeField(Strict):
    name: Annotated[str,Field(pattern=r'^[a-z][a-zA-Z0-9_]{0,63}$')]
    type: Text
    meaning: Text
    unit: Text


class VariantCase(Strict):
    name: Annotated[str,Field(pattern=r'^[A-Z][a-zA-Z0-9]{0,63}$')]
    type: Text | None


class TypeDefinition(Strict):
    name: Annotated[str,Field(pattern=r'^[A-Z][a-zA-Z0-9]{0,63}$')]
    kind: Literal['record','enum']
    fields: list[TypeField] = Field(max_length=40)
    cases: list[VariantCase] = Field(max_length=40)


class Bound(Strict):
    input: FactName
    minimum: Text | None
    maximum: Text | None
    unit_id: Id
    quote: Text


def fail(code='E_SCHEMA', details='Invalid shared rule model'):
    raise LegalMathError(code, details=details)


class Fact(Strict):
    name: FactName
    type: Text
    description: Text


class Rule(Strict):
    id: ModelId
    type: Text
    scope: dict
    body: dict
    interpretation_id: ModelId
    source_span_ids: list[ModelId]


class Model(Strict):
    record_type: Literal['LegalRuleModel']
    version: Literal['1']
    model_id: ModelId
    profile: Literal['ruleir.v1', 'complete.v1']
    valid_from: str
    valid_until: str | None
    types: list[TypeDefinition] = Field(max_length=30)
    bounds: list[Bound] = Field(default_factory=list, max_length=40)
    facts: list[Fact] = Field(max_length=10000)
    rules: list[Rule] = Field(min_length=1, max_length=1000)
    source_spans: list[dict]
    interpretations: list[dict]
    review: dict


class Parameter(Strict):
    name: Annotated[str, Field(pattern=r'^[a-z][a-z0-9_]{0,63}$')]
    type: Text


class Helper(Strict):
    name: ModelId
    parameters: list[Parameter] = Field(max_length=20)
    type: Text
    body: dict


class RuleV2(Rule):
    id: OutputId


class ModelV2(Model):
    version: Literal['2']
    profile: Literal['complete.v1', 'partial.v1']
    helpers: list[Helper] = Field(max_length=20)
    rules: list[RuleV2] = Field(min_length=1,max_length=40)


def inner(typ, constructor):
    prefix = constructor + '['
    return typ[len(prefix):-1] if typ.startswith(prefix) and typ.endswith(']') else None


def children(node):
    for key, value in node.items():
        if isinstance(value, dict) and 'op' in value:
            yield key, value
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict) and 'op' in item:
                    yield f'{key}/{i}', item
                elif isinstance(item, dict):
                    for sub, child in item.items():
                        if isinstance(child, dict) and 'op' in child:
                            yield f'{key}/{i}/{sub}', child


def walk(node, path=''):
    yield node, path
    for key, child in children(node):
        yield from walk(child, path + '/' + key)


def validate(value):
    try:
        return _validate(value)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        raise LegalMathError('E_SCHEMA', details='Malformed shared model') from exc
    except RecursionError as exc:
        raise LegalMathError('E_RESOURCE_LIMIT') from exc


def _validate(value):
    if len(canonical(value)) > 2_000_000: fail('E_RESOURCE_LIMIT')
    m = parse(ModelV2 if value.get('version')=='2' else Model, value)
    interval(m['valid_from'], m['valid_until'])
    for field in ('source_spans','interpretations'):
        schema = schema_validator('rule-bundle')
        if not schema.evolve(schema=schema.schema['properties'][field]).is_valid(m[field]): fail()
    definitions = {d.get('name'): d for d in m['types']}
    if len(definitions) != len(m['types']): fail('E_DUPLICATE_ID')
    type_visits=0

    def typ(t, stack=()):
        nonlocal type_visits
        type_visits+=1
        if m['version']=='2' and type_visits>10000: fail('E_RESOURCE_LIMIT','Expanded type validation budget')
        if not isinstance(t, str) or len(stack) > 12: fail('E_TYPE')
        if t in SCALARS: return
        if t in stack: fail('E_CYCLE')
        for constructor in ('list', 'optional'):
            child = inner(t, constructor)
            if child is not None:
                typ(child, stack + (t,)); return
        d = definitions.get(t)
        if d is None: fail('E_TYPE', 'Undeclared type: ' + t)
        if set(d) != {'name', 'kind', 'fields', 'cases'}: fail()
        if not re.fullmatch(r'[A-Z][A-Za-z0-9]{0,63}', t): fail('E_TYPE')
        if d['kind'] == 'record' and d['fields'] and not d['cases']:
            names = []
            for f in d['fields']:
                if set(f) != {'name', 'type', 'meaning', 'unit'}: fail()
                if not re.fullmatch(r'[a-z][A-Za-z0-9_]{0,63}', f['name']): fail('E_TYPE')
                names.append(f['name']); typ(f['type'], stack + (t,))
        elif d['kind'] == 'enum' and d['cases'] and not d['fields']:
            names = []
            for c in d['cases']:
                if set(c) != {'name', 'type'} or not re.fullmatch(r'[A-Z][A-Za-z0-9]{0,63}', c['name']): fail()
                names.append(c['name'])
                if c['type'] is not None: typ(c['type'], stack + (t,))
        else: fail('E_TYPE')
        if len(names) != len(set(names)) or len(names) > 40: fail('E_DUPLICATE_ID')

    for name in definitions: typ(name)
    facts = {f['name']: f['type'] for f in m['facts']}
    rules = {r['id']: r for r in m['rules']}
    helpers = {h['name']: h for h in m.get('helpers', [])}
    if len(helpers)!=len(m.get('helpers',[])): fail('E_DUPLICATE_ID')
    spans = {s.get('id') for s in m['source_spans']}
    readings = {r.get('id') for r in m['interpretations']}
    if len(facts) != len(m['facts']) or len(rules) != len(m['rules']) or len(spans) != len(m['source_spans']) or len(readings) != len(m['interpretations']): fail('E_DUPLICATE_ID')
    for t in facts.values(): typ(t)
    for s in m['source_spans']:
        if not isinstance(s.get('start'), int) or not isinstance(s.get('end'), int) or not 0 <= s['start'] < s['end']: fail('E_REFERENCE')
    for reading in m['interpretations']:
        if not set(reading.get('source_span_ids', [])) <= spans: fail('E_REFERENCE')
    seen = set(); node_types = {}; edges = {k: set() for k in rules}
    edges.update({'helper:'+k:set() for k in helpers})

    def infer(n, env, owner, depth=0):
        if depth > 128 or len(seen) >= 10000: fail('E_RESOURCE_LIMIT')
        if not isinstance(n, dict) or not isinstance(n.get('node_id'), str): fail()
        ident = n['node_id']
        if not re.fullmatch(r'[a-z][a-z0-9_.-]*',ident): fail()
        if ident in seen: fail('E_DUPLICATE_ID')
        seen.add(ident)
        op = n.get('op')
        def take(key, env=env): return infer(n[key], env, owner, depth + 1)
        fields = {
            'literal': {'type','value'}, 'fact': {'name'}, 'var': {'name'}, 'rule': {'name'},
            'all': {'args'}, 'any': {'args'}, 'not': {'arg'}, 'compare': {'cmp','left','right'},
            'add': {'left','right'}, 'sub': {'left','right'}, 'mul': {'left','right'},
            'scale': {'arg','numerator','denominator'}, 'if': {'condition','then','else'},
            'default': {'base','exceptions'}, 'field': {'arg','field'}, 'list': {'type','args'},
            'map': {'arg','binding','body'}, 'filter': {'arg','binding','body'}, 'sum': {'arg'},
            'some': {'arg'}, 'none': {'type'}, 'option': {'arg','binding','present','absent'},
            'variant': {'type','case','arg'}, 'match': {'arg','arms'}}
        if m['version']=='2':
            fields.update({'record':{'type','fields'}, 'call':{'name','args'},
                           'library':{'name','args'}, 'round':{'arg','type','mode'}})
        if op not in fields: fail('E_UNSUPPORTED_PROFILE', 'Unknown model operation: ' + str(op))
        if set(n) != {'op','node_id'} | fields[op]: fail('E_SCHEMA', 'Unexpected fields in ' + ident)
        if op == 'literal':
            t = n['type']; typ(t)
            if t == 'decimal':
                v = n['value']
                if not isinstance(v, dict) or set(v) != {'numerator','denominator'}: fail('E_TYPE')
                if not all(scalar('integer', s) and len(s) <= 1000 for s in v.values()): fail('E_TYPE')
                a, b = int(v['numerator']), int(v['denominator'])
                if b <= 0 or Fraction(a, b).denominator != b: fail('E_TYPE')
            elif t not in CORE_TYPES or not scalar(t, n['value']): fail('E_TYPE')
        elif op in ('fact', 'var', 'rule'):
            if owner.startswith('helper:') and op in ('fact','rule'):
                fail('E_REFERENCE','Helpers use explicit parameters, not hidden facts or rules')
            table = facts if op == 'fact' else env if op == 'var' else {k: v['type'] for k,v in rules.items()}
            if n['name'] not in table: fail('E_REFERENCE', 'Unknown ' + op + ': ' + n['name'])
            t = table[n['name']]
            if op == 'rule':
                edges[owner].add(n['name']); scope = rules[n['name']]['scope']
                if scope.get('op') != 'literal' or scope.get('type') != 'bool' or scope.get('value') is not True: fail('E_TYPE', 'Referenced rules need unconditional scope')
        elif op in ('all','any','not'):
            ts = [take('arg')] if op == 'not' else [infer(x, env, owner, depth + 1) for x in n['args']]
            if not ts or any(t != 'bool' for t in ts): fail('E_TYPE')
            t = 'bool'
        elif op in ('compare','add','sub','mul'):
            left, right = take('left'), take('right')
            if left != right or left not in ({'integer','money_hkd','date','decimal'} if op == 'compare' else {'integer','money_hkd','decimal'}): fail('E_TYPE')
            if op == 'mul' and left != 'decimal': fail('E_TYPE', 'Multiplication requires exact decimals')
            if op == 'compare' and n['cmp'] not in ('eq','ge','gt'): fail('E_TYPE')
            t = 'bool' if op == 'compare' else left
        elif op == 'scale':
            t = take('arg')
            if t not in ('integer','money_hkd') or not scalar('integer', n['numerator']) or not scalar('integer', n['denominator']) or int(n['denominator']) <= 0: fail('E_TYPE')
            if m['version']=='2' and max(len(n['numerator']),len(n['denominator']))>1000: fail('E_RESOURCE_LIMIT')
        elif op == 'round':
            from .operations import ROUNDING
            if take('arg')!='decimal' or n['type'] not in ('integer','money_hkd') or n['mode'] not in ROUNDING: fail('E_TYPE')
            t=n['type']
        elif op in ('call','library'):
            args=[infer(a,env,owner,depth+1) for a in n['args']]
            if op=='library':
                from .operations import result_type
                t=result_type(n['name'],args)
            else:
                h=helpers.get(n['name'])
                if h is None: fail('E_REFERENCE')
                if args!=[p['type'] for p in h['parameters']]: fail('E_TYPE')
                edges[owner].add('helper:'+n['name']);t=h['type']
        elif op == 'record':
            d=definitions.get(n['type'],{})
            if d.get('kind')!='record': fail('E_TYPE')
            if any(set(f)!={'name','value'} for f in n['fields']): fail()
            fields={f['name']:f['value'] for f in n['fields']}
            if len(fields)!=len(n['fields']) or set(fields)!={f['name'] for f in d['fields']}: fail('E_REFERENCE')
            for f in d['fields']:
                if infer(fields[f['name']],env,owner,depth+1)!=f['type']: fail('E_TYPE')
            t=n['type']
        elif op == 'if':
            condition, yes, no = take('condition'), take('then'), take('else')
            if condition != 'bool' or yes != no: fail('E_TYPE')
            t = yes
        elif op == 'default':
            t = take('base'); ids = set()
            for ex in n['exceptions']:
                if set(ex) != {'exception_id','guard','value','interpretation_id','source_span_ids'}: fail()
                if ex['exception_id'] in ids: fail('E_DUPLICATE_ID')
                ids.add(ex['exception_id'])
                if ex['interpretation_id'] not in readings or not set(ex['source_span_ids']) <= spans: fail('E_REFERENCE')
                if infer(ex['guard'],env,owner,depth+1) != 'bool' or infer(ex['value'],env,owner,depth+1) != t: fail('E_TYPE')
        elif op == 'field':
            record = definitions.get(take('arg'), {})
            candidates = {f['name']: f['type'] for f in record.get('fields', [])}
            if n['field'] not in candidates: fail('E_REFERENCE')
            t = candidates[n['field']]
        elif op == 'list':
            typ(n['type']); t = 'list[' + n['type'] + ']'
            if any(infer(x,env,owner,depth+1) != n['type'] for x in n['args']): fail('E_TYPE')
        elif op in ('map','filter'):
            item = inner(take('arg'), 'list')
            if item is None or not re.fullmatch(r'[a-z][a-z0-9_]*', n['binding']): fail('E_TYPE')
            body = take('body', {**env, n['binding']: item})
            if op == 'filter' and body != 'bool': fail('E_TYPE')
            t = 'list[' + (body if op == 'map' else item) + ']'
        elif op == 'sum':
            t = inner(take('arg'), 'list')
            if t not in ('integer','decimal','money_hkd'): fail('E_TYPE')
        elif op == 'some': t = 'optional[' + take('arg') + ']'
        elif op == 'none':
            typ(n['type']); t = 'optional[' + n['type'] + ']'
        elif op == 'option':
            item = inner(take('arg'), 'optional')
            if item is None or not re.fullmatch(r'[a-z][a-z0-9_]*', n['binding']): fail('E_TYPE')
            t = take('present', {**env,n['binding']:item})
            if take('absent') != t: fail('E_TYPE')
        elif op == 'variant':
            d = definitions.get(n['type'], {}); cases = {c['name']:c['type'] for c in d.get('cases',[])}
            if n['case'] not in cases: fail('E_REFERENCE')
            if (take('arg') if n['arg'] is not None else None) != cases[n['case']]: fail('E_TYPE')
            t = n['type']
        else:
            d = definitions.get(take('arg'), {}); cases = {c['name']:c['type'] for c in d.get('cases',[])}
            if not cases or len(n['arms']) != len(cases) or {a['case'] for a in n['arms']} != set(cases): fail('E_REFERENCE')
            ts = []
            for arm in n['arms']:
                if set(arm) != {'case','binding','body'}: fail()
                payload = cases[arm['case']]; binding = arm['binding']
                if (payload is None) != (binding is None): fail('E_TYPE')
                if binding is not None and not re.fullmatch(r'[a-z][a-z0-9_]*',binding): fail('E_TYPE')
                ts.append(infer(arm['body'],{**env,**({binding:payload} if binding else {})},owner,depth+1))
            if len(set(ts)) != 1: fail('E_TYPE')
            t = ts[0]
        node_types[ident] = t
        return t

    for rule in m['rules']:
        typ(rule['type'])
        if rule['interpretation_id'] not in readings or not set(rule['source_span_ids']) <= spans: fail('E_REFERENCE')
        if infer(rule['scope'],{},rule['id']) != 'bool' or infer(rule['body'],{},rule['id']) != rule['type']: fail('E_TYPE')
    for h in helpers.values():
        env={p['name']:p['type'] for p in h['parameters']}
        if len(env)!=len(h['parameters']): fail('E_DUPLICATE_ID')
        for t in [h['type'],*env.values()]: typ(t)
        if infer(h['body'],env,'helper:'+h['name'])!=h['type']: fail('E_TYPE')
    visited = set()
    def acyclic(name, trail=()):
        if name in trail: fail('E_CYCLE')
        if len(trail) > 100: fail('E_RESOURCE_LIMIT')
        if name not in visited:
            for target in edges[name]: acyclic(target, trail + (name,))
            visited.add(name)
    for name in edges: acyclic(name)
    review = m['review']
    if set(review) != {'origin','packet','reading','questions','coverage','dimensions','critic'}: fail()
    if review['origin'] not in ('ruleir.v1','interpretation','manual'): fail()
    if not isinstance(review['questions'],list) or any(not isinstance(q,str) or not q for q in review['questions']): fail()
    if not isinstance(review['coverage'],list) or not isinstance(review['dimensions'],list): fail()
    for row in review['coverage']: parse(Disposition,row)
    for row in review['dimensions']: parse(DimensionFinding,row)
    if review['critic'] is not None:
        c=review['critic']
        if (set(c)!={'verdict','findings'} or c['verdict'] not in ('SUPPORTED','CHALLENGED','UNRESOLVED')
                or not isinstance(c['findings'],list) or any(not isinstance(x,str) or not x for x in c['findings'])): fail()
    if review['packet'] is not None:
        packet=parse(Packet, review['packet'])
        if len({u['unit_id'] for u in packet['units']})!=len(packet['units']): fail('E_DUPLICATE_ID')
        for u in packet['units']:
            if u['span'] is not None:
                if u['span']['quote_sha256']!=raw_digest(u['text'].encode()): fail('E_HASH_MISMATCH')
    if review['reading'] is not None:
        r=parse(RetainedReading,review['reading']);f=r['formalization']
        if m['version']=='1':
            if set(f)-{'facts','types','scope','result','result_type'} or not {'facts','scope','result','result_type'}<=set(f): fail()
        elif set(f)!={'version','facts','types','outputs','helpers'} or f['version']!='2': fail()
        if review['packet'] is None: fail('E_REFERENCE')
        if review['coverage'] and review['dimensions']:
            validate_generation_metadata({'readings':[r],'coverage':review['coverage'],'dimensions':review['dimensions']},review['packet'])
        units={u['unit_id']:u for u in review['packet']['units']};expected_spans={}
        for c in r['citations']:
            u=units[c['unit_id']]
            if u['text'].count(c['quote'])!=1: fail('E_REFERENCE')
            span=u['span'] or make_span('s.'+u['unit_id'],'synthetic.'+review['packet']['source_key'],u['text'].encode(),u['text'],0,len(u['text']))
            expected_spans[span['id']]=span
        expected_facts=[{'name':x['name'],'type':x['type'],'description':x['meaning']+'; units: '+x['unit']} for x in f['facts']]
        expected_rules,expected_helpers=reading_program(f,list(expected_spans))
        expected_interpretations=[{'id':'reading','statement':'Unreviewed interpretation: '+r['statement'],
            'basis':'synthetic_test' if review['packet']['authority']=='SYNTHETIC_FIXTURE' else 'reviewer_interpretation',
            'source_span_ids':list(expected_spans),'issue_ids':[]}]
        if (m['facts']!=expected_facts or m['types']!=f.get('types',[]) or m['rules']!=expected_rules
                or m.get('helpers',[])!=expected_helpers
                or m['interpretations']!=expected_interpretations or m['source_spans']!=list(expected_spans.values())
                or not set(r['questions'])<=set(review['questions'])):
            fail('E_INTEGRITY','Retained interpretation and executable model differ')
    elif review['origin']=='interpretation': fail('E_REFERENCE')
    if len({b['input'] for b in m['bounds']})!=len(m['bounds']): fail('E_DUPLICATE_ID')
    for b in m['bounds']:
        if set(b)!={'input','minimum','maximum','unit_id','quote'} or b['input'] not in facts: fail('E_REFERENCE')
        if m['profile'] not in ('complete.v1','partial.v1') or facts[b['input']] not in ('integer','money_hkd','decimal'): fail('E_UNSUPPORTED_PROFILE')
        if review['packet'] is None: fail('E_REFERENCE')
        units={u['unit_id']:u for u in review['packet']['units']}
        if b['unit_id'] not in units or not b['quote'] or b['quote'] not in units[b['unit_id']]['text']: fail('E_REFERENCE')
        if b['minimum'] is None and b['maximum'] is None: fail('E_SCHEMA')
        for value in (b['minimum'],b['maximum']):
            if value is None: continue
            try: valid=isinstance(value,str) and len(value)<=1000 and str(Fraction(value))==value
            except (ValueError,ZeroDivisionError): valid=False
            if not valid: fail('E_TYPE','Bounds require canonical exact rational strings')
        lo=Fraction(b['minimum']) if b['minimum'] is not None else None
        hi=Fraction(b['maximum']) if b['maximum'] is not None else None
        if lo is not None and hi is not None and lo>hi: fail('E_TYPE')
    return m, node_types


def from_bundle(bundle):
    from ..ir.typecheck import validate_bundle
    errors = validate_bundle(bundle)
    if errors: fail(errors[0]['code'], errors)
    m = {'record_type':'LegalRuleModel','version':'1','model_id':bundle['bundle_id'],
         'profile':'ruleir.v1','types':[],
         **{k:deepcopy(bundle[k]) for k in ('valid_from','valid_until','facts','rules','source_spans','interpretations')},
         'review':{'origin':'ruleir.v1','packet':None,'reading':None,'questions':[], 'coverage':[], 'dimensions':[], 'critic':None}}
    return validate(m)[0]


def from_reading(reading, packet, at, *, until=None, profile='ruleir.v1', coverage=(), dimensions=(), questions=(), critic=None, bounds=()):
    if reading['formalization'] is None: fail('E_UNSUPPORTED_PROFILE')
    p = parse(Packet,packet); f = reading['formalization']; units = {u['unit_id']:u for u in p['units']}; spans = {}
    for citation in reading['citations']:
        unit = units.get(citation['unit_id'])
        if unit is None or unit['text'].count(citation['quote']) != 1: fail('E_REFERENCE')
        span = unit['span'] or make_span('s.'+unit['unit_id'],'synthetic.'+p['source_key'],unit['text'].encode(),unit['text'],0,len(unit['text']))
        spans[span['id']] = span
    retained={'local_id':'selected','family':'scope','subject':'Selected control',
              'distinction':'Retained legacy formalization','assumptions':[],'questions':[],**deepcopy(reading)}
    m = {'record_type':'LegalRuleModel','version':'1','model_id':'search.'+digest(reading)[:20],
         'profile':profile,'valid_from':at,'valid_until':until,'types':deepcopy(f.get('types',[])),'bounds':deepcopy(list(bounds)),
         'source_spans':list(spans.values()),
         'interpretations':[{'id':'reading','statement':'Unreviewed interpretation: '+reading['statement'],
                            'basis':'synthetic_test' if p['authority']=='SYNTHETIC_FIXTURE' else 'reviewer_interpretation',
                            'source_span_ids':list(spans),'issue_ids':[]}],
         'facts':[{'name':x['name'],'type':x['type'],'description':x['meaning']+'; units: '+x['unit']} for x in f['facts']],
         'rules':reading_program(f,list(spans))[0],
         'review':{'origin':'interpretation','packet':p,'reading':retained,
                   'questions':list(dict.fromkeys([*questions,*retained['questions']])),
                   'coverage':deepcopy(list(coverage)),'dimensions':deepcopy(list(dimensions)),'critic':deepcopy(critic)}}
    if f.get('version')=='2':
        m.update(version='2',helpers=reading_program(f,list(spans))[1])
    return validate(m)[0]


def reading_program(formalization, spans):
    """Reconstruct the entire executable program from its retained reading."""
    f=formalization
    if f.get('version')!='2':
        return ([{'id':'selected.control','type':f['result_type'],'scope':expression(f['scope'],'scope'),
                  'body':expression(f['result'],'body'),'interpretation_id':'reading','source_span_ids':spans}],[])
    from .frontend import FormalizationV2
    f=parse(FormalizationV2,f)
    rules=[{'id':o['id'],'type':o['result_type'],
            'scope':expression(o['scope'],'output.'+str(i)+'.scope',source_span_ids=spans),
            'body':expression(o['result'],'output.'+str(i)+'.body',source_span_ids=spans),
            'interpretation_id':'reading','source_span_ids':spans} for i,o in enumerate(f['outputs'])]
    helpers=[{'name':h['name'],'parameters':h['parameters'],'type':h['result_type'],
              'body':expression(h['body'],'helper.'+h['name'],parameters=[p['name'] for p in h['parameters']],
                                source_span_ids=spans)} for h in f['helpers']]
    return rules,helpers


def blockers(model):
    review = model['review']; reasons = list(review['questions'])
    reasons += ['Source unit '+r['unit_id']+' is '+r['status'] for r in review['coverage'] if r['status'] in ('UNCERTAIN','DEFERRED')]
    reasons += ['Ambiguous interpretation dimension: '+d['dimension'] for d in review['dimensions'] if d['status']=='AMBIGUOUS']
    if review['packet']:
        reasons += ['Unresolved dependency '+d['dependency_id'] for d in review['packet']['dependencies'] if d['source_hash'] is None]
    if review['critic'] is not None and review['critic']['verdict'] != 'SUPPORTED': reasons.append('Source criticism: '+review['critic']['verdict'])
    return sorted(set(reasons))
