"""Deterministic lowering to the existing RuleIR contract."""
from copy import deepcopy
import re
from ..canonical import digest,raw_digest
from ..ir.typecheck import validate_bundle
from .model import CORE_OPS, CORE_TYPES, validate, walk, fail


def fact_names(model):
    names={f['name'] for f in model['facts']};result={}
    for i,f in enumerate(model['facts']):
        name=f['name'];alias=name
        if not re.fullmatch(r'[a-z][a-z0-9_.-]*',name):
            alias='sharedfact'+str(i)
            while alias in names:alias+='x'
        names.add(alias);result[name]=alias
    return result


def adapt_snapshot(snapshot,names):
    """Preserve opaque provenance IDs through the narrower scalar Java codec."""
    adapted=deepcopy(snapshot);mapping={}
    reserved={e for f in adapted['facts'].values() for e in f.get('evidence_ids',[])}
    for fact in adapted['facts'].values():
        if 'evidence_ids' not in fact:continue
        ids=[]
        for ident in fact['evidence_ids']:
            if re.fullmatch(r'[a-z][a-z0-9_.-]*',ident):ids.append(ident);continue
            if ident not in mapping:
                alias='e.'+raw_digest(ident.encode())
                while alias in reserved:alias+='x'
                reserved.add(alias);mapping[ident]=alias
            ids.append(mapping[ident])
        fact['evidence_ids']=ids
    if not re.fullmatch(r'[a-z][a-z0-9_.-]*',adapted['subject_id']):
        adapted['subject_id']='subject.'+raw_digest(adapted['subject_id'].encode())
    adapted['facts']={names[k]:v for k,v in adapted['facts'].items()}
    return adapted,{'facts':names,'evidence':mapping,'subject':adapted['subject_id']}


def capabilities(model):
    m, _ = validate(model); issues = []
    if m['profile']=='partial.v1': issues.append({'path':'/profile','reason':'RuleIR uses a static fact conflict veto; partial.v1 uses evaluated structured dependencies'})
    if m.get('helpers'): issues.append({'path':'/helpers','reason':'RuleIR has no typed helper calculations'})
    if m['types']: issues.append({'path':'/types','reason':'RuleIR has no record or enum declarations'})
    for i, f in enumerate(m['facts']):
        if f['type'] not in CORE_TYPES: issues.append({'path':f'/facts/{i}/type','reason':'Unsupported type: '+f['type']})
    for i, r in enumerate(m['rules']):
        if not re.fullmatch(r'[a-z][a-z0-9_.-]*',r['id']):
            issues.append({'path':f'/rules/{i}/id','reason':'RuleIR rule identifiers require lowercase names'})
        if r['type'] not in CORE_TYPES: issues.append({'path':f'/rules/{i}/type','reason':'Unsupported type: '+r['type']})
        for key in ('scope','body'):
            for n, path in walk(r[key],f'/rules/{i}/{key}'):
                if n['op'] not in CORE_OPS or n.get('type') == 'decimal':
                    issues.append({'path':path,'reason':'Unsupported construct: '+n['op']})
    return {'target':'ruleir','model_hash':digest(m),'supported':not issues,'issues':issues}


def lower(model):
    m, node_types = validate(model); report = capabilities(m)
    if not report['supported']: fail('E_UNSUPPORTED_PROFILE', report)
    b = {'spec_version':'0.1','bundle_id':m['model_id'],
         **{k:deepcopy(m[k]) for k in ('valid_from','valid_until','source_spans','interpretations','facts','rules')}}
    names=fact_names(m)
    used={n['node_id'] for r in b['rules'] for key in ('scope','body') for n,_ in walk(r[key])}
    def fresh(base):
        ident=base
        while ident in used:ident+='x'
        used.add(ident);return ident
    for f in b['facts']:f['name']=names[f['name']]
    for r in b['rules']:
        for field in ('scope','body'):
            for n,_ in walk(r[field]):
                if n['op']=='fact':n['name']=names[n['name']]
                if n['op']=='scale' and int(n['numerator'])<0:
                    # RuleIR's scale numerator is nonnegative. Exact negative
                    # scaling is 0 - scale(x, abs(n), d), with the same failure
                    # on indivisibility and the same factual dependencies.
                    ident=n['node_id'];arg=n['arg'];denominator=n['denominator']
                    numerator=str(-int(n['numerator']));typ=node_types[ident]
                    n.clear();n.update(node_id=ident,op='sub',
                        left={'node_id':fresh(ident+'.zero'),'op':'literal','type':typ,'value':'0'},
                        right={'node_id':fresh(ident+'.magnitude'),'op':'scale','arg':arg,
                               'numerator':numerator,'denominator':denominator})
    errors = validate_bundle(b)
    if errors: fail(errors[0]['code'], errors)
    return b
