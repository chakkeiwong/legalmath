"""Evidence decisions shared across targets; never an arithmetic evaluator."""
from fractions import Fraction
from ..canonical import canonical
from ..domain import eligible, interval, scalar, timestamp
from ..errors import LegalMathError
from .model import inner, fail


def evidence_paths(model, typ, value, path):
    yield path
    item, option=inner(typ,'list'),inner(typ,'optional')
    if item is not None:
        for i,x in enumerate(value): yield from evidence_paths(model,item,x,path+'/'+str(i))
    elif option is not None:
        if value is not None: yield from evidence_paths(model,option,value['present'],path+'/present')
    elif typ not in ('bool','integer','money_hkd','date','decimal'):
        d=next(d for d in model['types'] if d['name']==typ)
        if d['kind']=='record':
            for f in d['fields']: yield from evidence_paths(model,f['type'],value[f['name']],path+'/'+f['name'])
        elif isinstance(value,dict):
            c=next(c for c in d['cases'] if c['name']==value['case'])
            if c['type']: yield from evidence_paths(model,c['type'],value['value'],path+'/value')


def validate_value(model, typ, value, depth=0):
    if depth > 12: fail('E_RESOURCE_LIMIT')
    item = inner(typ,'list'); option = inner(typ,'optional')
    if item is not None:
        if type(value) is not list or len(value)>10000: fail('E_TYPE')
        for x in value: validate_value(model,item,x,depth+1)
    elif option is not None:
        if value is not None:
            if type(value) is not dict or set(value)!={'present'}: fail('E_TYPE')
            validate_value(model,option,value['present'],depth+1)
    elif typ == 'decimal':
        if type(value) is not dict or set(value)!={'numerator','denominator'}: fail('E_TYPE')
        if not all(scalar('integer',s) and len(s)<=1000 for s in value.values()): fail('E_TYPE')
        a,b=int(value['numerator']),int(value['denominator'])
        if b<=0 or Fraction(a,b).denominator!=b: fail('E_TYPE')
    elif typ in ('bool','integer','money_hkd','date'):
        if not scalar(typ,value): fail('E_TYPE')
    else:
        d=next((d for d in model['types'] if d['name']==typ),None)
        if d is None: fail('E_TYPE')
        if d['kind']=='record':
            if type(value) is not dict or set(value)!={f['name'] for f in d['fields']}: fail('E_TYPE')
            for f in d['fields']: validate_value(model,f['type'],value[f['name']],depth+1)
        elif any(c['type'] is not None for c in d['cases']):
            if type(value) is not dict or set(value)!={'case','value'}: fail('E_TYPE')
            c=next((c for c in d['cases'] if c['name']==value['case']),None)
            if c is None: fail('E_TYPE')
            if c['type'] is None:
                if value['value'] is not None: fail('E_TYPE')
            else: validate_value(model,c['type'],value['value'],depth+1)
        elif value not in [c['name'] for c in d['cases']]: fail('E_TYPE')


def prepare(model, snapshot, valid_at, known_at):
    try:
        return _prepare(model,snapshot,valid_at,known_at)
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise LegalMathError('E_SCHEMA',details='Malformed shared snapshot') from exc


def _prepare(model, snapshot, valid_at, known_at):
    timestamp(valid_at);timestamp(known_at)
    if len(canonical(snapshot))>1_000_000: fail('E_RESOURCE_LIMIT')
    if not {'subject_id','facts'}<=set(snapshot) or set(snapshot)-{'subject_id','facts','evidence'} or not isinstance(snapshot['subject_id'],str) or not snapshot['subject_id']: fail()
    if type(snapshot['facts']) is not dict or set(snapshot['facts'])!={f['name'] for f in model['facts']}: fail('E_REFERENCE')
    evidence=dict(snapshot.get('evidence',{}));used=set()
    for path,ids in evidence.items():
        if (not isinstance(path,str) or not path.startswith('/') or type(ids)is not list or not ids
                or any(type(x)is not str or not x for x in ids) or len(set(ids))!=len(ids)): fail()
    normalized={};missing=[];conflicts=[]
    for f in model['facts']:
        name=f['name'];v=snapshot['facts'][name]
        if type(v) is not dict or v.get('type')!=f['type']: fail('E_TYPE')
        status=v.get('status')
        if status=='known':
            required={'status','type','value','evidence_ids','valid_from','valid_until','recorded_at'}
            if not required<=set(v) or set(v)-required-{'complete'}: fail()
            if 'complete' in v and type(v['complete']) is not bool: fail()
            interval(v['valid_from'],v['valid_until']);timestamp(v['recorded_at'])
            validate_value(model,f['type'],v['value'])
            ids=v['evidence_ids']
            if type(ids) is not list or not ids or any(type(x)is not str or not x for x in ids) or len(set(ids))!=len(ids): fail()
            root='/'+name
            if root in evidence and evidence[root]!=ids: fail('E_INTEGRITY','Top-level evidence differs')
            evidence[root]=ids
            required=set(evidence_paths(model,f['type'],v['value'],root))
            if required-evidence.keys(): fail('E_REFERENCE','Field/item evidence is missing')
            used.update(required)
            complete=v.get('complete',f['type'] in ('bool','integer','money_hkd','date','decimal'))
            if not complete:
                normalized[name]={'status':'unknown','type':f['type'],'reason':'MISSING'};missing.append(name)
            else:
                normalized[name]={k:x for k,x in v.items() if k!='complete'}
                if not eligible(v['valid_from'],v['valid_until'],valid_at) or v['recorded_at']>known_at: missing.append(name)
        elif status in ('unknown','conflict'):
            allowed={'status','type','reason'} if status=='unknown' else {'status','type','evidence_ids'}
            if set(v)!=allowed: fail()
            if status=='unknown' and v['reason'] not in ('MISSING','STALE','UNREVIEWED_ASSESSMENT','ORDER_UNRESOLVED'): fail('E_TYPE')
            if status=='conflict' and (type(v['evidence_ids'])is not list or any(type(x)is not str or not x for x in v['evidence_ids']) or len(set(v['evidence_ids']))!=len(v['evidence_ids'])): fail()
            if status=='conflict' and model['profile']=='ruleir.v1' and len(v['evidence_ids'])<2: fail()
            normalized[name]=v.copy()
            (missing if status=='unknown' else conflicts).append(name)
        else: fail()
    if evidence.keys()-used-{'/'+f['name'] for f in model['facts']}: fail('E_REFERENCE')
    reason=None
    invalid=[]
    for b in model['bounds']:
        v=normalized[b['input']]
        if v['status']!='known' or b['input'] in missing: continue
        raw=v['value'];number=Fraction(int(raw['numerator']),int(raw['denominator'])) if v['type']=='decimal' else int(raw)
        if ((b['minimum'] is not None and number<Fraction(b['minimum']))
                or (b['maximum'] is not None and number>Fraction(b['maximum']))): invalid.append(b['input'])
    if model['profile']=='complete.v1':
        if not eligible(model['valid_from'],model['valid_until'],valid_at): reason='SOURCE_VERSION_TIME'
        elif conflicts: reason='CONFLICTING_INPUTS'
        elif missing: reason='INCOMPLETE_INPUTS'
        elif invalid: reason='OUTSIDE_DECLARED_DOMAIN'
    return {'snapshot':{'subject_id':snapshot['subject_id'],'facts':normalized},
            'evidence':evidence,'reason':reason,'missing_inputs':sorted(missing),'blocking_inputs':sorted(conflicts),'invalid_inputs':sorted(invalid)}
