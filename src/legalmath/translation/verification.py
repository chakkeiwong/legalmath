"""Exact development checks, separate from translation and execution."""
from copy import deepcopy
from pathlib import Path
from ..canonical import digest
from ..ir.evaluate import evaluate
from ..ir.trace import verify_result
from .model import fail
from .pipeline import verify_build,execute
from .policy import prepare
from .ruleir import adapt_snapshot


def verify_execution(directory, snapshot, result, expected, jdk, *, compiler=None):
    """Check an external reference plus the appropriate independent runtime.

    Never called by translators or by ordinary execution. Expected values do not
    enter front-end interpretation or generated target programs.
    """
    if result.get('result_hash')!=digest({k:v for k,v in result.items() if k!='result_hash'}): fail('E_HASH_MISMATCH')
    if result['snapshot_hash']!=digest(snapshot): fail('E_HASH_MISMATCH')
    for key,value in expected.items():
        if key not in ('status','type','value','reason','missing_inputs','blocking_inputs','invalid_inputs'):
            fail('E_SCHEMA','Unsupported expected result field')
        if result.get(key)!=value: fail('E_INTEGRITY','Reference mismatch: '+key)
    model,translation,manifest=verify_build(directory,expected_hash=result['build_hash'])
    if (result['model_hash']!=translation['model_hash'] or result['policy']!=model['profile']
            or result['target']!=translation['target']): fail('E_HASH_MISMATCH')
    rule=next((r for r in model['rules'] if r['id']==result['rule_id']),None)
    if rule is None or rule['type']!=result['type']: fail('E_TYPE')
    boundary=prepare(model,snapshot,result['valid_at'],result['known_at'])
    if result['execution'] is None:
        if (not boundary['reason'] or boundary['reason']!=result['reason'] or result['status']!='ABSTAIN'
                or result['value'] is not None or result['missing_inputs']!=boundary['missing_inputs']
                or result['blocking_inputs']!=boundary['blocking_inputs'] or result['invalid_inputs']!=boundary['invalid_inputs']): fail('E_INTEGRITY')
        return {'reference_match':True,'execution':'shared evidence abstention'}
    lower=translation['output'];raw=result['execution']
    if manifest['identity']['kind']=='scalar':
        if result['status']!=raw['status'] or result['value']!=raw.get('value') or result['reason'] is not None: fail('E_INTEGRITY')
        adapted,mapping=adapt_snapshot(boundary['snapshot'],lower['fact_names'])
        if mapping!=result['execution_identity_map']: fail('E_INTEGRITY')
        original={v:k for k,v in mapping['facts'].items()}
        if (result['missing_inputs']!=sorted(original.get(k,k) for k in raw['missing_inputs'])
                or result['blocking_inputs']!=sorted(original.get(k,k) for k in raw['blocking_inputs'])): fail('E_INTEGRITY')
        verify_result(lower['bundle'],adapted,result['rule_id'],raw)
        reference=evaluate(lower['bundle'],adapted,result['rule_id'],result['valid_at'],result['known_at'],'draft')
        if {k:v for k,v in raw.items() if k not in ('engine_version','result_hash')}!={k:v for k,v in reference.items() if k not in ('engine_version','result_hash')}:
            fail('E_INTEGRITY','Full scalar trace differs from original RuleIR evaluator')
        return {'reference_match':True,'execution':'compiled Java','original_ruleir_trace_match':True}
    if compiler is None: fail('E_NOT_FOUND','Native verification requires the pinned interpreter')
    if boundary['reason'] or raw['status']!='VALUE' or result['reason'] is not None: fail('E_INTEGRITY')
    value=raw['value'][lower['rule_names'][result['rule_id']]]
    status=('TRUE' if value else 'FALSE') if rule['type']=='bool' else 'VALUE'
    if result['status']!=status or result['value']!=value: fail('E_INTEGRITY')
    replay=execute(directory,snapshot,result['rule_id'],result['valid_at'],result['known_at'],jdk,expected_hash=result['build_hash'])
    if {k:v for k,v in replay.items() if k!='result_hash'}!={k:v for k,v in result.items() if k not in ('result_hash','native_snapshot_hash')}:
        fail('E_INTEGRITY','Native result or provenance changed on replay')
    from ..catala.native.runtime import execute_values,interpreter_check
    inputs={lower['fact_names'][k]:v['value'] for k,v in boundary['snapshot']['facts'].items()}
    target=Path(directory)/'target'
    plain=execute_values(target,inputs,jdk,instrumented=False)
    if plain['value']!=raw['value']: fail('E_INTEGRITY','Instrumentation changed values')
    required=deepcopy(raw['value'])
    required[lower['rule_names'][result['rule_id']]]=expected['value']
    return {'reference_match':True,'plain_java_match':True,
            'interpreter':interpreter_check(lower['task'],lower['candidate'],inputs,required,compiler=compiler,directory=target)}
