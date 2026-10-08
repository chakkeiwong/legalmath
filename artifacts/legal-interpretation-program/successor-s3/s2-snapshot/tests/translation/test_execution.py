from copy import deepcopy
import pytest
from legalmath.canonical import digest,canonical,loads
from legalmath.errors import LegalMathError
from legalmath.translation.model import from_bundle
from legalmath.translation.pipeline import build,execute,translate,verify_build
from legalmath.translation.ruleir import lower
from legalmath.translation.verification import verify_execution
from tests.catala.backend_support import JDK,TOOLCHAIN,corpus_groups,interaction_cases
from tests.catala.native.reference import q
from .support import AT,model,snapshot,rich_model


def test_all_retained_ruleir_bundles_roundtrip():
    for group in corpus_groups()+[interaction_cases()]:
        b=group[0]['bundle']
        assert lower(from_bundle(b))==b


@pytest.fixture(scope='module')
def pair(tmp_path_factory):
    m=model();out=tmp_path_factory.mktemp('shared-pair')
    for target in ('ruleir','catala'):
        build(m,target,out/target,JDK,catala_toolchain=TOOLCHAIN)
    return m,out


def test_same_model_same_results_and_partial_policy(pair):
    m,out=pair
    a,b=(translate(m,t) for t in ('ruleir','catala'))
    assert a['model_hash']==b['model_hash'] and a['interpretation_hash']==b['interpretation_hash']
    s=snapshot(m,{'months':'6'})
    for fact,status,value in [(s['facts']['months'],'TRUE',True),
          ({'status':'unknown','type':'integer','reason':'MISSING'},'UNKNOWN',None),
          ({'status':'conflict','type':'integer','evidence_ids':['one','two']},'CONFLICT',None)]:
        s['facts']['months']=fact
        for target in ('ruleir','catala'):
            r=execute(out/target,s,'selected.control',AT,AT,JDK)
            assert (r['status'],r['value'])==(status,value)


def test_scalar_build_tampering_is_rejected(pair,tmp_path):
    import shutil
    m,out=pair;copy=tmp_path/'build';shutil.copytree(out/'ruleir',copy)
    expected=digest(loads((copy/'build.json').read_bytes()))
    t=loads((copy/'translation.json').read_bytes());t['policy']='complete.v1'
    (copy/'translation.json').write_bytes(canonical(t))
    with pytest.raises(LegalMathError):verify_build(copy,expected_hash=expected)


def test_outer_result_cannot_override_valid_scalar_trace(pair):
    m,out=pair;s=snapshot(m,{'months':'6'})
    result=execute(out/'ruleir',s,'selected.control',AT,AT,JDK)
    result.update(status='FALSE',value=False)
    result['result_hash']=digest({k:v for k,v in result.items() if k!='result_hash'})
    with pytest.raises(LegalMathError):verify_execution(out/'ruleir',s,result,{'status':'FALSE','value':False},JDK)
    result.update(status='ABSTAIN',value=None,execution=None)
    result['result_hash']=digest({k:v for k,v in result.items() if k!='result_hash'})
    with pytest.raises(LegalMathError):verify_execution(out/'ruleir',s,result,{'status':'ABSTAIN','value':None},JDK)


@pytest.mark.parametrize('field',['class_name','jar','model','jar_bytes'])
def test_changed_build_identity_or_bytes_fail(pair,tmp_path,field):
    import shutil
    m,out=pair;copy=tmp_path/'build';shutil.copytree(out/'ruleir',copy)
    b=loads((copy/'build.json').read_bytes())
    if field=='model':
        changed=loads((copy/'model.json').read_bytes());changed['review']['questions']=['Unresolved']
        (copy/'model.json').write_bytes(canonical(changed))
    elif field=='jar_bytes':
        jar=copy/'target'/b['identity']['jar'];jar.write_bytes(jar.read_bytes()+b'changed')
    else:
        b['identity'][field]='bad';(copy/'build.json').write_bytes(canonical(b))
    with pytest.raises(LegalMathError):verify_build(copy)


def test_rich_native_has_exact_values_and_explicit_ruleir_unsupported(tmp_path):
    m=rich_model();out=tmp_path/'rich'
    assert translate(m,'ruleir')['status']=='UNSUPPORTED'
    assert translate(m,'catala')['output']['route']=='native'
    build(m,'catala',out,JDK,catala_toolchain=TOOLCHAIN)
    s=snapshot(m,{'entries':[{'amount':q(1,3),'active':True},{'amount':q(9),'active':False}],
                  'rate':{'present':q(2,3)},'choice':{'case':'Fixed','value':q(7,5)}})
    for rule,value in [('selected.control',q(1)),('enum',q(7,5)),('optional',{'present':q(1,3)}),
                       ('none',None),('variant',{'case':'Fixed','value':q(2,3)}),('product',q(1,2)),('money','100')]:
        result=execute(out,s,rule,AT,AT,JDK)
        assert result['status']=='VALUE' and result['value']==value
        checks=verify_execution(out,s,result,{'status':'VALUE','value':value},JDK,compiler=TOOLCHAIN['compiler'])
        assert checks['interpreter']['exact_match'] and checks['plain_java_match']
    s['facts']['rate']['value']=None
    s['evidence'].pop('/rate/present')
    assert execute(out,s,'selected.control',AT,AT,JDK)['value']==q(1,3)
    s['facts']['rate']={'status':'unknown','type':'optional[decimal]','reason':'MISSING'}
    assert execute(out,s,'selected.control',AT,AT,JDK)['status']=='ABSTAIN'


def test_lazy_errors_exception_ties_and_partial_booleans(tmp_path):
    from legalmath.conformance import evaluate_case
    cases=interaction_cases();m=from_bundle(cases[0]['bundle'])
    selected=[c for c in cases if c['id'].endswith(('.0','.13','.26')) or c['id'] in ('negative.scale','date.compare','empty.default','many.guards')]
    for target in ('ruleir','catala'):
        out=tmp_path/target;build(m,target,out,JDK,catala_toolchain=TOOLCHAIN)
        for c in selected:
            reference=evaluate_case(c)
            result=execute(out,c['snapshot'],c['rule_id'],c['valid_at'],c['known_at'],JDK)
            expected={'status':reference['status'],'value':reference.get('value')}
            assert verify_execution(out,c['snapshot'],result,expected,JDK)['original_ruleir_trace_match']


def test_complete_policy_and_opaque_identifiers_agree_across_targets(tmp_path):
    m=model();m['review'].update(origin='manual',reading=None);m['profile']='complete.v1'
    m['facts'][0]['name']='historyMonths';m['rules'][0]['body']['left']['name']='historyMonths'
    for target in ('ruleir','catala'):
        out=tmp_path/target;build(m,target,out,JDK,catala_toolchain=TOOLCHAIN)
        s=snapshot(m,{'historyMonths':'6'});s['subject_id']='Funds/example A'
        result=execute(out,s,'selected.control',AT,AT,JDK)
        assert result['status']=='TRUE'
        assert result['execution_identity_map']['facts']['historyMonths']=='sharedfact0'
        assert verify_execution(out,s,result,{'status':'TRUE','value':True},JDK)['original_ruleir_trace_match']
        s['facts']['historyMonths']={'status':'unknown','type':'integer','reason':'MISSING'}
        result=execute(out,s,'selected.control',AT,AT,JDK)
        assert (result['status'],result['reason'],result['missing_inputs'])==('ABSTAIN','INCOMPLETE_INPUTS',['historyMonths'])
