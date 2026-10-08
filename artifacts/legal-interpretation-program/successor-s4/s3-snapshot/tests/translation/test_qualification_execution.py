from copy import deepcopy
import random
import shutil
import pytest
from legalmath.canonical import canonical,digest,loads
from legalmath.errors import LegalMathError
from legalmath.qualification import assurance, oracle
from tests.catala.backend_support import JDK,TOOLCHAIN
from .support import AT,snapshot,model
from .v2_support import fixture_v2,as_model


def cases(m, values):
    return [{'id':str(i),'snapshot':snapshot(m,v),'valid_at':AT,'known_at':AT} for i,v in enumerate(values)]


@pytest.fixture(scope='module')
def reports(tmp_path_factory):
    out=tmp_path_factory.mktemp('qualification');rng=random.Random(20260928)
    scalar=model()
    rich=as_model(*fixture_v2([('xs','list[decimal]'),('gate','bool')],
        [('sum','decimal','true','(sum xs)'),
         ('rounded','integer','gate','(round integer nearest_away (sum xs))')],
        text='Synthetic exact sum and explicit rounding with a scoped output.'))
    values=[{'months':str(rng.randrange(-1000,1000))} for _ in range(3)]
    rows=cases(scalar,values)
    a=assurance.run(scalar,rows,out/'scalar',JDK,toolchain=TOOLCHAIN)
    amounts=[{'numerator':str(n),'denominator':'3'} for n in (1,2,4)]
    rows2=cases(rich,[{'xs':amounts,'gate':True},{'xs':[],'gate':False}])
    b=assurance.run(rich,rows2,out/'rich',JDK,toolchain=TOOLCHAIN)
    return out,scalar,rich,a,b


def test_real_both_backend_checks_and_direct_rich_native_route(reports):
    out,scalar,rich,a,b=reports
    assert a['summary']['status']=='QUALIFIED',a
    assert a['proof']['status']=='KERNEL_CHECKED'
    assert a['summary']['independent_formal_matches']==6
    assert b['targets']['ruleir']['status']=='UNSUPPORTED'
    assert b['targets']['catala']['route']=='native'
    assert b['summary']['independent_formal_matches']==2,b
    assert b['proof']['status']=='UNSUPPORTED'
    for m,name in ((scalar,'scalar'),(rich,'rich')):
        result=assurance.verify(out/name,m,JDK,compiler=TOOLCHAIN['compiler'])
        assert result['summary']['unknown_future_legal_generalization']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('field',['source','method','policy','model'])
def test_source_or_method_change_invalidates_active_evidence(reports,field):
    out,m,_,_,_=reports;changed=deepcopy(m)
    if field=='source':changed['review']['packet']['source_key']='new.source'
    elif field=='model':changed['model_id']='new.model'
    elif field=='policy':changed['review']['questions'].append('An amendment changes applicability')
    else:changed['review']['critic']={'verdict':'UNRESOLVED','findings':['New machine finding']}
    with pytest.raises(LegalMathError):assurance.verify(out/'scalar',changed,JDK,compiler=TOOLCHAIN['compiler'])


@pytest.mark.parametrize('mutation',['claim','proof','value','omit','target'])
def test_forged_claims_and_evidence_fail_even_with_recomputed_report_hash(reports,tmp_path,mutation):
    out,m,_,_,_=reports;d=tmp_path/'forged';shutil.copytree(out/'scalar',d)
    path=d/'qualification.json';r=loads(path.read_bytes())
    if mutation=='claim':r['summary']['legal_correctness']='PROVED'
    elif mutation=='proof':r['proof']['scope']['excludes']=[]
    elif mutation=='value':r['targets']['ruleir']['cases'][0]['result']['results']['selected.control']['value']='forged'
    elif mutation=='omit':r['targets']['ruleir']['cases'].pop()
    else:del r['targets']['catala']
    r['report_hash']=digest({k:v for k,v in r.items() if k!='report_hash'});path.write_bytes(canonical(r))
    with pytest.raises(LegalMathError):assurance.verify(d,m,JDK,compiler=TOOLCHAIN['compiler'])


@pytest.mark.parametrize('field',['expected','human_label','reviewer','rating','approval'])
def test_no_answer_key_or_human_quality_data_can_enter_execution(field):
    m=model();c=cases(m,[{'months':'7'}]);c[0][field]=True
    with pytest.raises(LegalMathError):assurance.check_cases(c)


def test_generated_negative_scale_preserves_exactness_on_both_backends(tmp_path):
    m=as_model(*fixture_v2([('x','integer')],
        [('negative','integer','true','(scale x -3 2)'),
         ('nested','integer','true','(scale (scale x -2 1) -3 1)')],
        profile='complete.v1',text='Synthetic exact negative scaling, including nested signs.'))
    c=cases(m,[{'x':str(x)} for x in (0,2,-2,3,10**40)])
    result=assurance.run(m,c,tmp_path/'negative',JDK,toolchain=TOOLCHAIN)
    assert result['summary']['status']=='QUALIFIED',result
    assert result['summary']['independent_formal_matches']==2*len(c)
    assert assurance.verify(tmp_path/'negative',m,JDK,compiler=TOOLCHAIN['compiler'])==result
