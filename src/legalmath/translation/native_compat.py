"""Input adapters for the historical native CLI, not a separate interpretation path."""
from pathlib import Path
from ..canonical import loads,digest
from ..catala.native.contracts import validate_task
from .frontend import interpret
from .model import inner,fail
from .pipeline import build,execute


def shared_type(typ):
    for c in ('list','optional'):
        t=inner(typ,c)
        if t is not None: return c+'['+shared_type(t)+']'
    return {'boolean':'bool','money':'money_hkd'}.get(typ,typ)


def task(value, *, version=None):
    t=validate_task(value)
    if version is None: version='1' if len(t['outputs'])==1 else '2'
    if version not in ('1','2') or (version=='1' and len(t['outputs'])!=1): fail('E_UNSUPPORTED_PROFILE')
    definitions=[]
    for d in t['types']:
        definitions.append({**d,'fields':[{**f,'type':shared_type(f['type'])} for f in d['fields']],
            'cases':[{'name':c,'type':None} if isinstance(c,str) else {**c,'type':shared_type(c['type']) if c['type'] else None} for c in d['cases']]})
    units=[u['unit_id'] for u in t['packet']['units'] if u['normative']] or [t['packet']['units'][0]['unit_id']]
    result={'record_type':'RuleInterpretationTask','task_id':t['task_id'],'packet':t['packet'],'question':t['question'],
            'facts':[{'name':f['name'],'type':shared_type(f['type']),'meaning':f['meaning'],'unit':f['unit'],
                      'source_unit_ids':units,'requires_judgment':True} for f in t['inputs']],
            'types':definitions,'result_type':shared_type(t['outputs'][0]['type']),'profile':'complete.v1',
            'valid_from':t['valid_from'],'valid_until':t['valid_until'],'bounds':t.get('bounds',[])}
    if version=='2':
        result.pop('result_type')
        result.update(version='2',outputs=[{'id':f['name'],'result_type':shared_type(f['type'])} for f in t['outputs']])
    return result


def convert(value,output,provider,jdk,*,compiler,upstream,lock,resume=False,max_revisions=1,reading_id=None,shared_version=None):
    out=Path(output);front=out/'interpretation'
    state=interpret(task(value,version=shared_version),front,provider,resume=resume,max_revisions=max_revisions)
    result={'record_type':'ModularNativeConversion','frontend':state,'status':state['status']}
    if state['status']!='INTERPRETED': return result
    rows=state['models']
    if reading_id is None and (len(rows)!=1 or state['unrepresented_readings']):
        return {**result,'status':'AWAITING_SELECTION'}
    selected=next((r for r in rows if r['reading_id']==reading_id),None) if reading_id else rows[0]
    if selected is None: fail('E_REFERENCE','Select an existing reading_id')
    if selected['unresolved']: return {**result,'status':'UNRESOLVED_SOURCE','selected':selected}
    model=loads((front/selected['path']).read_bytes());target=out/('translated-'+selected['model_hash'])
    if (target/'build.json').exists():
        from .pipeline import verify_build
        existing,_,manifest=verify_build(target)
        if existing!=model: fail('E_INTEGRITY')
    else: manifest=build(model,'catala',target,jdk,catala_toolchain={'compiler':compiler,'upstream':upstream,'lock':lock})
    return {**result,'status':'READY_FOR_BEHAVIOR_CHECK','selected':selected,'build':manifest,'build_directory':target.name}


def snapshot(value,model):
    # Validate the original codec, including every field/item evidence path,
    # before adapting it. A missing leaf must not become complete evidence.
    from .catala import native_type
    from ..catala.native.boundary import prepare
    native={'record_type':'NativeCatalaTask','task_id':'adapter.snapshot','packet':model['review']['packet'],
            'question':model['model_id'],'entry_scope':'InputAdapter','native_profile':'legalmath.catala.native.v2',
            'valid_from':model['valid_from'],'valid_until':model['valid_until'],
            'types':[{**d,'fields':[{**f,'type':native_type(f['type'])} for f in d['fields']],
                      'cases':[{**c,'type':native_type(c['type']) if c['type'] else None} for c in d['cases']]} for d in model['types']],
            'inputs':[{'name':f['name'],'type':native_type(f['type']),'meaning':f['description'],'unit':'Shared declaration'} for f in model['facts']],
            'outputs':[{'name':'adapterOutput','type':native_type(model['rules'][0]['type']),'meaning':'Selected output','unit':'Shared declaration'}],
            'bounds':model['bounds']}
    prepare(native,value)
    facts={}
    if set(value['facts'])-{f['name'] for f in model['facts']}: fail('E_REFERENCE')
    for f in model['facts']:
        name=f['name'];v=value['facts'].get(name,{'status':'unknown','reason':'MISSING'})
        if v['status']=='known':
            facts[name]={**v,'type':f['type'],'evidence_ids':value['evidence'].get('/'+name,[])}
        elif v['status']=='conflict': facts[name]={'status':'conflict','type':f['type'],'evidence_ids':value['evidence'].get('/'+name,[])}
        else: facts[name]={'status':'unknown','type':f['type'],'reason':'MISSING'}
    return {'subject_id':value['subject_id'],'facts':facts,'evidence':value['evidence']}


def execute_native(directory,value,jdk,*,rule_id=None):
    model=loads((Path(directory)/'model.json').read_bytes())
    adapted=snapshot(value,model)
    if len(model['rules'])>1 and rule_id is None:
        results={r['id']:execute(directory,adapted,r['id'],value['valid_at'],value['known_at'],jdk) for r in model['rules']}
        complete=all(r['status'] in ('VALUE','TRUE','FALSE') for r in results.values())
        first=next(iter(results.values()))
        if any(r['model_hash']!=digest(model) or r['build_hash']!=first['build_hash'] for r in results.values()):
            fail('E_INTEGRITY','Build changed between output evaluations')
        abstain=all(r['status']=='ABSTAIN' for r in results.values())
        result={'record_type':'TranslatedRuleResults','model_hash':digest(model),'snapshot_hash':digest(adapted),
                'build_hash':first['build_hash'],'status':'VALUE' if complete else 'ABSTAIN' if abstain else 'PARTIAL_RESULTS',
                'reason':first['reason'] if abstain else None,
                'value':{k:r['value'] for k,r in results.items()} if complete else None,'results':results}
    else:
        result=execute(directory,adapted,rule_id or model['rules'][0]['id'],value['valid_at'],value['known_at'],jdk)
    result['native_snapshot_hash']=digest(value)
    result['result_hash']=digest({k:v for k,v in result.items() if k!='result_hash'})
    return result
