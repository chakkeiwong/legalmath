"""Version-2 observation validation and encoding preparation, without arithmetic."""
from fractions import Fraction
from ..canonical import canonical
from ..domain import eligible, interval, timestamp
from .model import SCALARS, inner, fail
from .policy import validate_value


def prepare(model, snapshot, valid_at, known_at):
    timestamp(valid_at);timestamp(known_at)
    if len(canonical(snapshot))>1_000_000: fail('E_RESOURCE_LIMIT')
    if (type(snapshot)is not dict or not {'subject_id','facts'}<=set(snapshot)
            or set(snapshot)-{'subject_id','facts','evidence'} or not isinstance(snapshot['subject_id'],str)
            or not snapshot['subject_id']): fail()
    if type(snapshot['facts'])is not dict or set(snapshot['facts'])!={f['name'] for f in model['facts']}: fail('E_REFERENCE')
    evidence=snapshot.get('evidence',{})
    if type(evidence)is not dict: fail()
    defs={d['name']:d for d in model['types']};observations={};used=set()

    def ids(value, minimum=1):
        if (type(value)is not list or len(value)<minimum or len(set(value))!=len(value)
                or any(type(s)is not str or not s for s in value)): fail('E_SCHEMA','Invalid evidence identifiers')
        return value

    for path,value in evidence.items():
        if not isinstance(path,str) or not path.startswith('/'): fail()
        ids(value)

    def observe(typ, obs, path, depth=0):
        if depth>12 or len(observations)>=10000: fail('E_RESOURCE_LIMIT')
        if type(obs)is not dict or obs.get('type')!=typ: fail('E_TYPE')
        status=obs.get('status')
        if status in ('unknown','conflict'):
            key='reason' if status=='unknown' else 'evidence_ids'
            if set(obs)!={'status','type',key}: fail()
            if status=='unknown' and obs['reason'] not in ('MISSING','STALE','UNREVIEWED_ASSESSMENT','ORDER_UNRESOLVED'): fail('E_TYPE')
            ev=[] if status=='unknown' else ids(obs['evidence_ids'],2 if model['profile']=='partial.v1' else 0)
            if path in evidence:
                if status=='conflict' and evidence[path]!=ev: fail('E_INTEGRITY')
                # Evidence for an unknown node must live in the original snapshot,
                # not be mistaken for evidence of a known value.
                used.add(path)
            observations[path]={'status':status,'evidence_ids':ev,'reason':obs.get('reason')}
            return obs.copy()
        if status not in ('known','structured'): fail()
        required={'status','type','value','evidence_ids','valid_from','valid_until','recorded_at'}
        if not required<=set(obs) or set(obs)-required-{'complete'}: fail()
        if 'complete' in obs and type(obs['complete'])is not bool: fail()
        if status=='structured' and (model['profile']!='partial.v1' or typ in SCALARS): fail('E_UNSUPPORTED_PROFILE')
        interval(obs['valid_from'],obs['valid_until']);timestamp(obs['recorded_at'])
        ev=ids(obs['evidence_ids'])
        if path in evidence:
            if evidence[path]!=ev: fail('E_INTEGRITY')
            used.add(path)
        item,option=inner(typ,'list'),inner(typ,'optional')
        value=obs['value']
        if status=='known': validate_value(model,typ,value)

        def child(t,v,p):
            if status=='structured': return observe(t,v,p,depth+1)
            if p not in evidence: fail('E_REFERENCE','Field/item evidence is missing: '+p)
            return observe(t,{'status':'known','type':t,'value':v,'evidence_ids':evidence[p],
                              'valid_from':obs['valid_from'],'valid_until':obs['valid_until'],
                              'recorded_at':obs['recorded_at'],'complete':True},p,depth+1)

        if item is not None:
            if type(value)is not list or len(value)>10000: fail('E_TYPE')
            value=[child(item,v,path+'/'+str(i)) for i,v in enumerate(value)]
        elif option is not None:
            if value is not None:
                if type(value)is not dict or set(value)!={'present'}: fail('E_TYPE')
                value={'present':child(option,value['present'],path+'/present')}
        elif typ not in SCALARS:
            d=defs[typ]
            if d['kind']=='record':
                if type(value)is not dict or set(value)!={f['name'] for f in d['fields']}: fail('E_TYPE')
                value={f['name']:child(f['type'],value[f['name']],path+'/'+f['name']) for f in d['fields']}
            elif any(c['type'] for c in d['cases']):
                if type(value)is not dict or set(value)!={'case','value'}: fail('E_TYPE')
                c=next((c for c in d['cases'] if c['name']==value['case']),None)
                if c is None or (c['type'] is None and value['value'] is not None): fail('E_TYPE')
                value={'case':c['name'],'value':child(c['type'],value['value'],path+'/value') if c['type'] else None}
            elif value not in [c['name'] for c in d['cases']]: fail('E_TYPE')
        complete=obs.get('complete',typ in SCALARS)
        reason=('STALE' if not eligible(obs['valid_from'],obs['valid_until'],valid_at) or obs['recorded_at']>known_at
                else 'MISSING' if not complete else None)
        observations[path]={'status':'unknown' if reason else 'known','evidence_ids':ev,'reason':reason}
        return ({'status':'unknown','type':typ,'reason':reason} if reason else
                {'status':'known','type':typ,'value':value,'evidence_ids':ev,
                 **{k:obs[k] for k in ('valid_from','valid_until','recorded_at')}})

    facts={f['name']:observe(f['type'],snapshot['facts'][f['name']],'/'+f['name']) for f in model['facts']}
    if set(evidence)-used: fail('E_REFERENCE','Evidence path does not describe an input observation')
    missing=sorted(p for p,o in observations.items() if o['status']=='unknown')
    conflicts=sorted(p for p,o in observations.items() if o['status']=='conflict')
    invalid=[]
    for b in model['bounds']:
        v=facts[b['input']]
        if v['status']!='known': continue
        raw=v['value'];n=Fraction(int(raw['numerator']),int(raw['denominator'])) if v['type']=='decimal' else int(raw)
        if (b['minimum'] is not None and n<Fraction(b['minimum'])) or (b['maximum'] is not None and n>Fraction(b['maximum'])):
            invalid.append('/'+b['input'])
    reason=None
    if not eligible(model['valid_from'],model['valid_until'],valid_at): reason='SOURCE_VERSION_TIME'
    elif model['profile']=='complete.v1' and conflicts: reason='CONFLICTING_INPUTS'
    elif model['profile']=='complete.v1' and missing: reason='INCOMPLETE_INPUTS'
    elif invalid: reason='OUTSIDE_DECLARED_DOMAIN'
    return {'snapshot':{'subject_id':snapshot['subject_id'],'facts':facts},'observations':observations,
            'evidence':{p:o['evidence_ids'] for p,o in observations.items() if o['evidence_ids']},
            'reason':reason,'missing_inputs':missing,'blocking_inputs':conflicts,'invalid_inputs':sorted(invalid)}
