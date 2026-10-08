"""Build and execute one committed interpretation through either target."""
from pathlib import Path
import tempfile
from ..canonical import canonical,digest,loads,raw_digest
from ..errors import LegalMathError
from ..java.manifest import build_candidate,run_java
from . import ruleir, catala
from .model import validate,blockers,fail
from .policy import prepare


def translate(model,target):
    m,_=validate(model)
    if target not in ('ruleir','catala'): fail('E_UNSUPPORTED_PROFILE')
    module=ruleir if target=='ruleir' else catala
    capability=module.capabilities(m); reasons=blockers(m)
    result={'record_type':'RuleTranslation','version':'1','target':target,'model_hash':digest(m),
            'interpretation_hash':digest({'interpretations':m['interpretations'],'review':m['review']}),
            'policy':m['profile'],'capabilities':capability,'unresolved':reasons}
    if not capability['supported']: result['status']='UNSUPPORTED'
    elif reasons: result['status']='UNRESOLVED'
    else:
        result['status']='TRANSLATED'
        result['output']={'route':'ruleir','bundle':ruleir.lower(m)} if target=='ruleir' else catala.lower(m)
        if result['output']['route']!='native':result['output']['fact_names']=ruleir.fact_names(m)
    result['translation_hash']=digest(result)
    return result


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(value))


def build(model,target,out,jdk,*,catala_toolchain=None):
    m,_=validate(model);t=translate(m,target)
    if t['status']!='TRANSLATED': fail('E_UNSUPPORTED_PROFILE' if t['status']=='UNSUPPORTED' else 'E_RELEASE_BLOCKED',t)
    out=Path(out).resolve()
    if out.exists() and any(out.iterdir()): fail('E_JOB_STATE','Use a fresh build directory')
    out.mkdir(parents=True,exist_ok=True)
    write(out/'model.json',m);write(out/'translation.json',t)
    lower=t['output'];directory=out/'target'
    if lower['route']=='native':
        if not catala_toolchain: fail('E_NOT_FOUND','Explicit pinned Catala toolchain required')
        from ..catala.native.runtime import build as native_build
        native=native_build(lower['task'],lower['candidate'],directory,jdk,**catala_toolchain)
        identity={'kind':'native','build_hash':digest(native)}
    else:
        target_build=build_candidate(lower['bundle'],directory,jdk,backend='java' if target=='ruleir' else 'catala',
                                     catala_toolchain=catala_toolchain if target=='catala' else None)
        identity={'kind':'scalar','manifest_hash':target_build['manifest_hash'],
                  'jar':Path(target_build['jar']).name,'class_name':target_build['class_name']}
    manifest={'record_type':'TranslatedRuleBuild','version':'1','model_hash':digest(m),
              'translation_hash':t['translation_hash'],'target':target,'identity':identity,
              'review_authority':'DRAFT_ONLY; model source criticism is not legal or release approval'}
    write(out/'build.json',manifest)
    return manifest


def verify_build(directory,*,expected_hash=None):
    try:
        return _verify_build(directory,expected_hash=expected_hash)
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise LegalMathError('E_SCHEMA',details='Malformed translated build') from exc
    except OSError as exc:
        raise LegalMathError('E_NOT_FOUND',details='Translated build file is unavailable') from exc


def _verify_build(directory,*,expected_hash=None):
    out=Path(directory);m,_=validate(loads((out/'model.json').read_bytes()));t=loads((out/'translation.json').read_bytes());b=loads((out/'build.json').read_bytes())
    if expected_hash is not None and digest(b)!=expected_hash: fail('E_HASH_MISMATCH')
    if (set(b)!={'record_type','version','model_hash','translation_hash','target','identity','review_authority'}
            or b['record_type']!='TranslatedRuleBuild' or b['version']!='1'
            or b['review_authority']!='DRAFT_ONLY; model source criticism is not legal or release approval'): fail('E_SCHEMA')
    if b['model_hash']!=digest(m) or b['translation_hash']!=t.get('translation_hash') or t!=translate(m,b['target']): fail('E_INTEGRITY','Model or deterministic translation changed')
    identity=b['identity'];target=out/'target'
    if t['status']!='TRANSLATED' or ((t['output']['route']=='native') != (identity['kind']=='native')): fail('E_INTEGRITY')
    if identity['kind']=='native':
        if set(identity)!={'kind','build_hash'}: fail('E_SCHEMA')
        from ..catala.native.runtime import verify_build as native_verify
        task,candidate,manifest=native_verify(target,expected_hash=identity['build_hash'])
        if task!=t['output']['task'] or candidate!=t['output']['candidate']: fail('E_INTEGRITY')
    elif identity['kind']=='scalar':
        if set(identity)!={'kind','manifest_hash','jar','class_name'}: fail('E_SCHEMA')
        manifest=loads((target/'build-manifest.json').read_bytes())
        if (digest(manifest)!=identity['manifest_hash'] or manifest['bundle_hash']!=digest(t['output']['bundle'])
                or identity['jar']!=manifest['jar_sha256']+'.jar'
                or identity['class_name']!='hk.legalmath.Policy_'+manifest['bundle_hash'][:20]
                or raw_digest((target/identity['jar']).read_bytes())!=manifest['jar_sha256']): fail('E_INTEGRITY')
    else: fail('E_SCHEMA')
    return m,t,b


def execute(directory,snapshot,rule_id,valid_at,known_at,jdk,*,expected_hash=None):
    return _execute_selected(directory,snapshot,[rule_id],valid_at,known_at,jdk,
                             expected_hash=expected_hash)[rule_id]


def execute_all(directory,snapshot,valid_at,known_at,jdk,*,expected_hash=None):
    """Evaluate every declared output against one verified build and snapshot."""
    results=_execute_selected(directory,snapshot,None,valid_at,known_at,jdk,expected_hash=expected_hash)
    first=next(iter(results.values()))
    complete=all(r['status'] in ('VALUE','TRUE','FALSE') for r in results.values())
    abstain=all(r['status']=='ABSTAIN' for r in results.values())
    result={'record_type':'TranslatedRuleResults','model_hash':first['model_hash'],
            'snapshot_hash':first['snapshot_hash'],'build_hash':first['build_hash'],
            'status':'VALUE' if complete else 'ABSTAIN' if abstain else 'PARTIAL_RESULTS',
            'reason':first['reason'] if abstain else None,
            'value':{k:r['value'] for k,r in results.items()} if complete else None,'results':results}
    result['result_hash']=digest(result)
    return result


def _execute_selected(directory,snapshot,rule_ids,valid_at,known_at,jdk,*,expected_hash=None):
    m,t,b=verify_build(directory,expected_hash=expected_hash)
    by_id={r['id']:r for r in m['rules']}
    if rule_ids is None: rule_ids=list(by_id)
    if any(k not in by_id for k in rule_ids): fail('E_REFERENCE')
    boundary=prepare(m,snapshot,valid_at,known_at)
    identity=b['identity'];output=t['output'];raw=None
    if not boundary['reason']:
        if identity['kind']=='scalar':
            adapted,mapping=ruleir.adapt_snapshot(boundary['snapshot'],output['fact_names'])
            requests=[{'bundle':output['bundle'],'snapshot':adapted,'rule_id':k,
                       'valid_at':valid_at,'known_at':known_at,'mode':'draft'} for k in rule_ids]
            jar_bytes=(Path(directory)/'target'/identity['jar']).read_bytes()
            if raw_digest(jar_bytes)+'.jar'!=identity['jar']: fail('E_HASH_MISMATCH')
            with tempfile.TemporaryDirectory(prefix='legalmath-shared-execute-') as temp:
                jar=Path(temp)/identity['jar'];jar.write_bytes(jar_bytes)
                rows=run_java(jar,requests,jdk,identity['class_name'])
            if len(rows)!=len(rule_ids): fail('E_INTEGRITY','Incomplete scalar batch')
            raw_by_id=dict(zip(rule_ids,rows))
            original={v:k for k,v in output['fact_names'].items()}
        elif output.get('encoding')=='structured.v1':
            from ..catala.native.runtime import execute_values
            from .structured import inputs,result_fields
            _,node_types=validate(m)
            encoded,provenance=inputs(m,node_types,output,boundary)
            raw=execute_values(Path(directory)/'target',encoded,jdk,expected_hash=identity['build_hash'])
            raw.update(record_type='StructuredCatalaExecution',encoding='structured.v1',
                       build_hash=identity['build_hash'],inputs_hash=digest(encoded),provenance=provenance)
        else:
            from ..catala.native.runtime import evaluate
            facts={};evidence={}
            for f in m['facts']:
                name=output['fact_names'][f['name']];v=boundary['snapshot']['facts'][f['name']]
                facts[name]={k:v[k] for k in ('status','value','valid_from','valid_until','recorded_at')};facts[name]['complete']=True
                for path,ids in boundary['evidence'].items():
                    root='/'+f['name']
                    if path==root or path.startswith(root+'/'): evidence['/'+name+path[len(root):]]=ids
            native={'record_type':'NativeFactSnapshot','subject_id':snapshot['subject_id'],'revision':'0',
                    'valid_at':valid_at,'known_at':known_at,'facts':facts,'evidence':evidence}
            raw=evaluate(Path(directory)/'target',native,jdk,expected_hash=identity['build_hash'])
    results={}
    for rule_id in rule_ids:
        r=by_id[rule_id]
        answer={'record_type':'TranslatedRuleResult','model_hash':digest(m),'build_hash':digest(b),
                'target':b['target'],'policy':m['profile'],'rule_id':rule_id,'type':r['type'],
                'snapshot_hash':digest(snapshot),'valid_at':valid_at,'known_at':known_at}
        if boundary['reason']:
            answer.update(status='ABSTAIN',value=None,reason=boundary['reason'],missing_inputs=boundary['missing_inputs'],
                          blocking_inputs=boundary['blocking_inputs'],invalid_inputs=boundary['invalid_inputs'],execution=None)
        elif identity['kind']=='scalar':
            row=raw_by_id[rule_id]
            answer['execution_identity_map']=mapping
            answer.update(status=row['status'],value=row.get('value'),reason=None,
                          missing_inputs=sorted(original.get(k,k) for k in row['missing_inputs']),
                          blocking_inputs=sorted(original.get(k,k) for k in row['blocking_inputs']),execution=row)
        elif output.get('encoding')=='structured.v1':
            answer.update(result_fields(m,node_types,r['type'],raw['value'][output['rule_names'][rule_id]],provenance),execution=raw)
        else:
            value=raw['value'][output['rule_names'][rule_id]] if raw['status']=='VALUE' else None
            status=('TRUE' if value else 'FALSE') if raw['status']=='VALUE' and r['type']=='bool' else raw['status']
            answer.update(status=status,value=value,reason=raw.get('reason'),missing_inputs=[],blocking_inputs=[],execution=raw)
        answer['result_hash']=digest(answer)
        results[rule_id]=answer
    return results


def project(result):
    return {k:result[k] for k in ('status','type','value')}
