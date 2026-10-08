from copy import deepcopy
import pytest
from legalmath.canonical import canonical,digest,loads
from legalmath.errors import LegalMathError
from legalmath.translation import pipeline
from legalmath.translation.verification import verify_executions
from legalmath.catala.native import runtime
from tests.catala.backend_support import JDK,TOOLCHAIN
from .support import AT,model,snapshot
from .v2_support import as_model,fixture_v2,ENTRY,observed,unknown,conflict
from .test_v2_execution import programs,numeric_snapshot,structured_snapshot,replace,q


@pytest.mark.parametrize('name',['numeric','structured','library'])
def test_batch_equals_individual_results_and_runs_once(programs,monkeypatch,name):
    from .test_v2_execution import library_snapshot
    m,out=programs[name]
    s={'numeric':numeric_snapshot,'structured':structured_snapshot,'library':library_snapshot}[name](m)
    if name=='numeric':
        s['facts']['right']=unknown('bool')
        replace(s,'cash',conflict('money_hkd'))
    if name=='structured':
        replace(s,'entry',observed('Entry',{'active':unknown('bool'),'amount':observed('decimal',q(1,3))},structured=True))
    calls=[];original=runtime.execute_values
    def counted(*args,**kwargs):
        calls.append(kwargs);return original(*args,**kwargs)
    monkeypatch.setattr(runtime,'execute_values',counted)
    result=pipeline.execute_all(out,s,AT,AT,JDK)
    assert len(calls)==1
    assert calls[0]['expected_hash']==loads((out/'build.json').read_bytes())['identity']['build_hash']
    for rule in m['rules']:
        assert result['results'][rule['id']]==pipeline.execute(out,s,rule['id'],AT,AT,JDK)
    assert result['result_hash']==digest({k:v for k,v in result.items() if k!='result_hash'})


def test_batch_abstention_does_not_execute(programs,monkeypatch):
    m,out=programs['numeric'];s=numeric_snapshot(m)
    def forbidden(*args,**kwargs): raise AssertionError('Abstention started a runtime')
    monkeypatch.setattr(runtime,'execute_values',forbidden)
    result=pipeline.execute_all(out,s,'2026-09-24T00:00:00.000000Z',AT,JDK)
    assert result['status']=='ABSTAIN' and result['reason']=='SOURCE_VERSION_TIME'
    assert all(r['execution'] is None for r in result['results'].values())


@pytest.mark.parametrize('target',['ruleir','catala'])
def test_scalar_batch_uses_one_jvm_and_original_reference(tmp_path,monkeypatch,target):
    m=model();m['review'].update(origin='manual',reading=None)
    m['rules'].append({**deepcopy(m['rules'][0]),'id':'second'})
    # Node identities are shared globally; give the copied expression fresh IDs.
    def rename(value):
        if isinstance(value,dict):
            if 'node_id' in value:value['node_id']+='second'
            for child in value.values():rename(child)
        elif isinstance(value,list):
            for child in value:rename(child)
    rename(m['rules'][1]);out=tmp_path/'scalar'
    pipeline.build(m,target,out,JDK,catala_toolchain=TOOLCHAIN)
    calls=[];original=pipeline.run_java
    def counted(*args,**kwargs):calls.append(len(args[1]));return original(*args,**kwargs)
    monkeypatch.setattr(pipeline,'run_java',counted)
    s=snapshot(m,{'months':'6'});result=pipeline.execute_all(out,s,AT,AT,JDK)
    assert calls==[2] and result['value']=={'selected.control':True,'second':True}
    checks=verify_executions(out,s,result,{k:{'status':'TRUE','value':True} for k in result['results']},JDK)
    assert all(c['original_ruleir_trace_match'] for c in checks.values())


def test_batch_rejects_forgery_missing_output_and_changed_build(programs):
    m,out=programs['structured'];s=structured_snapshot(m)
    good=pipeline.execute_all(out,s,AT,AT,JDK)
    expected={k:{'status':v['status'],'value':v['value']} for k,v in good['results'].items()}
    for mutation in ('value','remove','time'):
        bad=deepcopy(good)
        if mutation=='remove':bad['results'].pop('field')
        elif mutation=='value':bad['results']['field']['value']=q(9)
        else:bad['results']['field']['known_at']='2026-09-24T00:00:00.000000Z'
        bad['result_hash']=digest({k:v for k,v in bad.items() if k!='result_hash'})
        with pytest.raises(LegalMathError):verify_executions(out,s,bad,expected,JDK,compiler=TOOLCHAIN['compiler'])
    with pytest.raises(LegalMathError):pipeline.execute_all(out,s,AT,AT,JDK,expected_hash='0'*64)
    with pytest.raises(LegalMathError):runtime.execute_values(out/'target',{},JDK,expected_hash='0'*64)


def interaction_model():
    return as_model(*fixture_v2([('entries','list[Entry]'),('gate','bool'),('waive','bool')],
        [('rounded','integer','gate','(round integer nearest_away (call subtotal entries))'),
         ('selected','decimal','true','(default (call subtotal entries) (exception waived waive (decimal 0 1)))')],
        types=[ENTRY],helpers=[{'name':'subtotal','parameters':[{'name':'xs','type':'list[Entry]'}],
            'result_type':'decimal','body':'(sum (map e (filter e xs (field e active)) (field e amount)))'}],
        text='Sum amounts of active entries through a reusable calculation. Round the sum to the nearest integer with ties away from zero when gate holds. Independently return that sum, except waive selects zero.'))


def test_helper_collection_partial_exception_and_rounding_interaction(tmp_path):
    m=interaction_model();out=tmp_path/'interaction';pipeline.build(m,'catala',out,JDK,catala_toolchain=TOOLCHAIN)
    entry=lambda active,amount:observed('Entry',{'active':observed('bool',active),'amount':amount},structured=True)
    s=snapshot(m,{'entries':[],'gate':True,'waive':False})
    replace(s,'entries',observed('list[Entry]',[
        entry(True,observed('decimal',q(1,3))),entry(False,conflict('decimal')),
        entry(True,observed('decimal',q(7,6)))],structured=True))
    for waived,gate,expected in [
        (False,True,{'rounded':{'status':'VALUE','value':'2','blocking_inputs':[]},'selected':{'status':'VALUE','value':q(3,2)}}),
        (True,False,{'rounded':{'status':'OUT_OF_SCOPE','value':None},'selected':{'status':'VALUE','value':q(0)}})]:
        s['facts']['waive']['value']=waived;s['facts']['gate']['value']=gate
        result=pipeline.execute_all(out,s,AT,AT,JDK)
        checks=verify_executions(out,s,result,expected,JDK,compiler=TOOLCHAIN['compiler'])
        assert all(c['interpreter']['exact_match'] for c in checks.values())
        record={'snapshot':deepcopy(s),'expected':expected,'result':result,'checks':checks}
        (tmp_path/('interaction-'+str(waived)+'.json')).write_bytes(canonical(record))
    manifest=loads((out/'target/build.json').read_bytes())
    assert manifest['trace_invariant_check']=='original_and_instrumented'
    commands=loads((out/'target/build-commands.json').read_bytes())
    # Every Java compiler invocation, including the observed one, checks invariants.
    compiled=[row for row in commands if 'java' in row['command'] and '--output' in row['command']]
    assert len(compiled)>=2 and all('--check-invariants' in row['command'] for row in compiled)
