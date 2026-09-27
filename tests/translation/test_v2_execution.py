from copy import deepcopy
import pytest
from legalmath.canonical import canonical,digest
from legalmath.errors import LegalMathError
from legalmath.translation.model import validate
from legalmath.translation.pipeline import build,execute,translate
from legalmath.translation.policy import prepare
from legalmath.translation.verification import verify_execution
from tests.catala.backend_support import JDK,TOOLCHAIN
from tests.catala.native.reference import q
from .support import AT,snapshot
from .v2_support import (numeric_fixture,library_fixture,structured_fixture,as_model,
                         observed,unknown,conflict,fixture_v2)


@pytest.fixture(scope='module')
def programs(tmp_path_factory):
    root=tmp_path_factory.mktemp('v2-programs');result={}
    for name,fixture in [('numeric',numeric_fixture),('library',library_fixture),('structured',structured_fixture)]:
        m=as_model(*fixture());out=root/name
        build(m,'catala',out,JDK,catala_toolchain=TOOLCHAIN);result[name]=(m,out)
    return result


def check(program,s,rule,status,value=None,**fields):
    _,out=program;r=execute(out,s,rule,AT,AT,JDK)
    expected={'status':status,'value':value,**fields}
    for k,v in expected.items(): assert r[k]==v,(rule,k,r[k],v)
    verified=verify_execution(out,s,r,expected,JDK,compiler=TOOLCHAIN['compiler'])
    if r['execution'] is not None: assert verified['plain_java_match'] and verified['interpreter']['exact_match']
    # These records also serve the retained replay when pytest's base directory
    # is under the task's artifact directory. Normal tests retain them in tmp.
    record={'model_hash':digest(program[0]),'snapshot':s,'rule_id':rule,'expected':expected,
            'result':r,'checks':verified}
    records=out.parent/'checks';records.mkdir(exist_ok=True)
    (records/(digest(record)+'.json')).write_bytes(canonical(record))
    return r


def numeric_snapshot(m,**overrides):
    return snapshot(m,{'gate':True,'left':False,'right':False,'cash':'100','ratio':q(3,2),**overrides})


def test_exact_scale_rounding_helpers_and_multiple_outputs(programs):
    p=programs['numeric'];s=numeric_snapshot(p[0])
    for rule,status,value in [('scoped','VALUE','50'),('exact','VALUE','50'),('rounded','VALUE','2'),
          ('floor','VALUE','1'),('ceiling','VALUE','2'),('truncate','VALUE','1'),('defaults','VALUE','1'),
          ('helper','VALUE',q(3)),('branch','VALUE','9')]: check(p,s,rule,status,value)
    s=numeric_snapshot(p[0],cash='101')
    check(p,s,'exact','ERROR',reason='E_INEXACT_SCALE')
    check(p,s,'rounded','VALUE','2')
    check(p,s,'rule.ref','ERROR',reason='E_INEXACT_SCALE')


@pytest.mark.parametrize('n,d,rounded,floor,ceiling,truncated',[
    (-3,2,'-2','-2','-1','-1'),(-1,2,'-1','-1','0','0'),(1,2,'1','0','1','0'),
    (-7,3,'-2','-3','-2','-2'),(6,1,'6','6','6','6')])
def test_rounding_signs_halves_and_integer_boundary(programs,n,d,rounded,floor,ceiling,truncated):
    p=programs['numeric'];s=numeric_snapshot(p[0],ratio=q(n,d))
    for rule,v in [('rounded',rounded),('floor',floor),('ceiling',ceiling),('truncate',truncated)]:check(p,s,rule,'VALUE',v)


def test_scope_lazy_body_and_explicit_partial_dependencies(programs):
    p=programs['numeric'];s=numeric_snapshot(p[0],gate=False,cash='101')
    check(p,s,'scoped','OUT_OF_SCOPE',missing_inputs=[],blocking_inputs=[])
    s['facts']['gate']=unknown('bool')
    check(p,s,'scoped','UNKNOWN',missing_inputs=['/gate'])
    s=numeric_snapshot(p[0]);replace(s,'cash',conflict('money_hkd'))
    # The unrelated exact output conflicts, but selected branch/scope remain usable.
    check(p,s,'branch','VALUE','9',blocking_inputs=[])
    check(p,s,'exact','CONFLICT',blocking_inputs=['/cash'])


def test_exception_overlap_unknown_guards_and_lazy_consequences(programs):
    p=programs['numeric'];s=numeric_snapshot(p[0],left=True,right=True)
    check(p,s,'defaults','CONFLICT',reason='EXCEPTION_OVERLAP')
    check(p,s,'distinct','CONFLICT',reason='EXCEPTION_OVERLAP')
    check(p,s,'guard.error','ERROR',reason='E_INEXACT_SCALE')
    check(p,s,'all.error','ERROR',reason='E_INEXACT_SCALE')
    check(p,s,'empty.default','VALUE','1')
    s=numeric_snapshot(p[0],left=True)
    check(p,s,'lazy','VALUE','7')
    s['facts']['right']=unknown('bool')
    check(p,s,'defaults','UNKNOWN',missing_inputs=['/right'])
    check(p,s,'overlap.unknown','CONFLICT',reason='EXCEPTION_OVERLAP',missing_inputs=['/right'])
    replace(s,'right',conflict('bool'))
    check(p,s,'defaults','CONFLICT',blocking_inputs=['/right'])


def test_strong_kleene_and_conflict_priority(programs):
    p=programs['numeric'];s=numeric_snapshot(p[0]);s['facts']['right']=unknown('bool')
    check(p,s,'and','FALSE',False,missing_inputs=['/right'])
    check(p,s,'or','UNKNOWN',missing_inputs=['/right'])
    s['facts']['left']['value']=True
    check(p,s,'or','TRUE',True,missing_inputs=['/right'])
    check(p,s,'and','UNKNOWN',missing_inputs=['/right'])
    replace(s,'right',conflict('bool'))
    check(p,s,'or','CONFLICT',blocking_inputs=['/right'])


def library_snapshot(m,**overrides):
    return snapshot(m,{'start':'2024-01-31','offset':'1','begin':'2','end':'5','x':q(1,3),'y':q(2,5),**overrides})


def test_library_operations_have_exact_references(programs):
    p=programs['library'];s=library_snapshot(p[0])
    for rule,value in [('months','2024-02-29'),('days','2024-02-01'),('month.end','2024-01-31'),
                       ('sequence',['2','3','4']),('length','3'),('min',q(1,3)),('max',q(2,5))]:check(p,s,rule,'VALUE',value)
    check(p,library_snapshot(p[0],start='2023-03-31',offset='-1'),'months','VALUE','2023-02-28')
    check(p,library_snapshot(p[0],start='2024-02-01'),'month.end','VALUE','2024-02-29')


def test_library_domains_do_not_wrap_native_integer_sizes(programs):
    p=programs['library']
    for overrides,rule,reason in [({'start':'9999-12-31'},'months','E_DATE_RANGE'),
                                ({'start':'0001-01-01','offset':'-1'},'days','E_DATE_RANGE'),
                                ({'offset':str(2**64)},'days','E_DATE_RANGE'),
                                ({'begin':'0','end':'10001'},'sequence','E_RESOURCE_LIMIT')]:
        check(p,library_snapshot(p[0],**overrides),rule,'ERROR',reason=reason)
    huge=2**100
    check(p,library_snapshot(p[0],begin=str(huge),end=str(huge+2)),'sequence','VALUE',[str(huge),str(huge+1)])
    check(p,library_snapshot(p[0],begin=str(2**40),end='0'),'sequence','VALUE',[])


def structured_snapshot(m):
    return snapshot(m,{'entry':{'active':True,'amount':q(1,3)},
        'entries':[{'active':True,'amount':q(1,3)},{'active':False,'amount':q(2,3)}],
        'rate':None,'choice':{'case':'Fixed','value':q(2,3)}})


def replace(s,name,obs):
    s['facts'][name]=obs
    s['evidence']={p:v for p,v in s['evidence'].items() if p!='/'+name and not p.startswith('/'+name+'/')}


def test_rich_values_constructed_and_projected(programs):
    p=programs['structured'];s=structured_snapshot(p[0])
    for rule,value in [('field',q(1,3)),('record',{'active':True,'amount':q(1,3)}),('sum',q(1)),
                       ('filtered',q(1,3)),('optional',q(0)),('choice',q(2,3)),
                       ('some',{'present':q(1,3)}),('variant',{'case':'Fixed','value':q(1,3)}),('empty',None)]:
        check(p,s,rule,'VALUE',value)


def test_field_partial_output_and_item_uncertainty(programs):
    p=programs['structured'];s=structured_snapshot(p[0])
    entry=observed('Entry',{'active':unknown('bool'),'amount':observed('decimal',q(1,3),path='amount')},structured=True)
    replace(s,'entry',entry)
    result=check(p,s,'field','VALUE',q(1,3),missing_inputs=[])
    assert result['used_evidence']=={'/entry':['evidence:fixture'],'/entry/amount':['evidence:amount']}
    r=check(p,s,'record','PARTIAL',missing_inputs=['/entry/active'])
    assert r['partial_value']['children']['amount']['value']==q(1,3)
    entries=observed('list[Entry]',[entry],structured=True)
    replace(s,'entries',entries)
    check(p,s,'sum','VALUE',q(1,3),missing_inputs=[])
    check(p,s,'filtered','UNKNOWN',missing_inputs=['/entries/0/active'])
    entry['value']['active']=observed('bool',False)
    entry['value']['amount']=conflict('decimal')
    replace(s,'entries',observed('list[Entry]',[entry],structured=True))
    check(p,s,'sum','CONFLICT',blocking_inputs=['/entries/0/amount'])
    check(p,s,'filtered','VALUE',q(0),blocking_inputs=[])


def test_absence_unknown_and_incomplete_membership_are_distinct(programs):
    p=programs['structured'];s=structured_snapshot(p[0])
    check(p,s,'optional','VALUE',q(0))
    replace(s,'rate',unknown('optional[decimal]'))
    check(p,s,'optional','UNKNOWN',missing_inputs=['/rate'])
    replace(s,'rate',observed('optional[decimal]',{'present':unknown('decimal')},structured=True))
    check(p,s,'optional','UNKNOWN',missing_inputs=['/rate/present'])
    replace(s,'entries',observed('list[Entry]',[],structured=True))
    check(p,s,'sum','VALUE',q(0))
    s['facts']['entries']['complete']=False
    check(p,s,'sum','UNKNOWN',missing_inputs=['/entries'])


def test_stale_nested_evidence_and_source_time(programs):
    p=programs['structured'];s=structured_snapshot(p[0])
    amount=observed('decimal',q(1,3));amount['recorded_at']='2026-09-26T00:00:00.000000Z'
    replace(s,'entry',observed('Entry',{'active':observed('bool',True),'amount':amount},structured=True))
    check(p,s,'field','UNKNOWN',missing_inputs=['/entry/amount'])
    out=p[1];r=execute(out,s,'field','2026-09-24T00:00:00.000000Z',AT,JDK)
    assert r['status']=='ABSTAIN' and r['reason']=='SOURCE_VERSION_TIME'
    assert verify_execution(out,s,r,{'status':'ABSTAIN','value':None},JDK)


def test_structured_result_and_evidence_tampering_rejected(programs):
    m,out=programs['structured'];s=structured_snapshot(m)
    original=execute(out,s,'field',AT,AT,JDK)
    for key in ('value','used_evidence','execution'):
        r=deepcopy(original)
        if key=='value':r[key]=q(2,3)
        elif key=='used_evidence':r[key]={}
        else:r[key]['provenance']['0']['path']='/forged'
        r['result_hash']=digest({k:v for k,v in r.items() if k!='result_hash'})
        with pytest.raises(LegalMathError):verify_execution(out,s,r,{},JDK,compiler=TOOLCHAIN['compiler'])


def test_complete_policy_still_requires_all_inputs_and_strict_evidence():
    t,g=structured_fixture();t['profile']='complete.v1';m=as_model(t,g);s=structured_snapshot(m)
    s['facts']['rate']=unknown('optional[decimal]')
    assert prepare(m,s,AT,AT)['reason']=='INCOMPLETE_INPUTS'
    s=structured_snapshot(m);s['evidence'].pop('/entry/amount')
    with pytest.raises(LegalMathError):prepare(m,s,AT,AT)
    s=structured_snapshot(m);replace(s,'entry',observed('Entry',{},structured=True))
    with pytest.raises(LegalMathError):prepare(m,s,AT,AT)


def test_v2_complete_core_fragment_agrees_with_ruleir(tmp_path):
    t,g=fixture_v2([('n','integer')],[('half','integer','true','(scale n 1 2)'),
        ('default','integer','true','(default (integer 1) (exception high (> n (integer 4)) (integer 2)))')],
        profile='complete.v1',text='Synthetic controls: halve n exactly, and independently use one unless n exceeds four, then use two.')
    m=as_model(t,g);translations=[translate(m,target) for target in ('ruleir','catala')]
    assert translations[0]['interpretation_hash']==translations[1]['interpretation_hash']
    for target in ('ruleir','catala'):
        out=tmp_path/target;build(m,target,out,JDK,catala_toolchain=TOOLCHAIN)
        s=snapshot(m,{'n':'6'})
        for rule,value in [('half','3'),('default','2')]:
            r=execute(out,s,rule,AT,AT,JDK)
            assert verify_execution(out,s,r,{'status':'VALUE','value':value},JDK,compiler=TOOLCHAIN['compiler'])
        s['facts']['n']=unknown('integer')
        r=execute(out,s,'half',AT,AT,JDK)
        assert r['status']=='ABSTAIN' and r['reason']=='INCOMPLETE_INPUTS'
