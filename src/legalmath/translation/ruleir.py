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
    if m['types']: issues.append({'path':'/types','reason':'RuleIR has no record or enum declarations'})
    for i, f in enumerate(m['facts']):
        if f['type'] not in CORE_TYPES: issues.append({'path':f'/facts/{i}/type','reason':'Unsupported type: '+f['type']})
    for i, r in enumerate(m['rules']):
        if r['type'] not in CORE_TYPES: issues.append({'path':f'/rules/{i}/type','reason':'Unsupported type: '+r['type']})
        for key in ('scope','body'):
            for n, path in walk(r[key],f'/rules/{i}/{key}'):
                if n['op'] not in CORE_OPS or n.get('type') == 'decimal':
                    issues.append({'path':path,'reason':'Unsupported construct: '+n['op']})
    return {'target':'ruleir','model_hash':digest(m),'supported':not issues,'issues':issues}


def lower(model):
    m, _ = validate(model); report = capabilities(m)
    if not report['supported']: fail('E_UNSUPPORTED_PROFILE', report)
    b = {'spec_version':'0.1','bundle_id':m['model_id'],
         **{k:deepcopy(m[k]) for k in ('valid_from','valid_until','source_spans','interpretations','facts','rules')}}
    names=fact_names(m)
    for f in b['facts']:f['name']=names[f['name']]
    for r in b['rules']:
        for field in ('scope','body'):
            for n,_ in walk(r[field]):
                if n['op']=='fact':n['name']=names[n['name']]
    errors = validate_bundle(b)
    if errors: fail(errors[0]['code'], errors)
    return b
