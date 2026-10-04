from copy import deepcopy
from legalmath.canonical import loads
from legalmath.ir.evaluate import evaluate
from legalmath.ir.typecheck import validate_bundle
from legalmath.translation.model import from_bundle
from legalmath.translation.ruleir import lower
from legalmath.translation.pipeline import build
from tests.catala.backend_support import JDK,TOOLCHAIN,ROOT
from tests.catala.native.reference import q
from .support import snapshot
from .v2_support import fixture_v2,as_model,ENTRY,observed,unknown
from .test_v2_execution import check,replace


def test_version_one_large_scale_coefficients_keep_original_contract():
    case=deepcopy(loads((ROOT/'docs/specs/v0.1/fixtures/decision-cases.json').read_bytes())['cases'][0])
    bundle=case['bundle'];rule=bundle['rules'][0]
    rule['type']='integer'
    rule['scope']={'op':'literal','node_id':'large.scope','type':'bool','value':True}
    rule['body']={'op':'scale','node_id':'large.scale','numerator':'1'+'0'*1000,'denominator':'1'+'0'*1000,
                  'arg':{'op':'literal','node_id':'large.one','type':'integer','value':'1'}}
    assert not validate_bundle(bundle)
    assert lower(from_bundle(bundle))==bundle
    result=evaluate(bundle,case['snapshot'],rule['id'],case['valid_at'],case['known_at'],'draft')
    assert result['status']=='VALUE' and result['value']=='1'


def test_rich_scope_defaults_helper_and_unknown_item_count(tmp_path):
    t,g=fixture_v2([('gate','bool'),('entry','Entry'),('entries','list[Entry]')],
        [('scoped','Entry','gate','(call make true (field entry amount))'),
         ('default','Entry','true','(default entry (exception override gate (call make false (decimal 2 3))))'),
         ('overlap','Entry','true','(default entry (exception a true entry) (exception b true entry))'),
         ('count','integer','true','(library list.length entries)')],types=[ENTRY],
        helpers=[{'name':'make','parameters':[{'name':'active','type':'bool'},{'name':'amount','type':'decimal'}],
                  'result_type':'Entry','body':'(record Entry (active active) (amount amount))'}],
        text='Synthetic controls: when gate holds, construct an active entry with the supplied entry amount. '
             'An independent default returns entry unless gate overrides it with an inactive entry of amount two-thirds. '
             'Two always-true overrides conflict even when both return entry. Count entries from complete membership '
             'even if individual entry contents are unavailable.')
    m=as_model(t,g);p=(m,tmp_path/'rich');build(m,'catala',p[1],JDK,catala_toolchain=TOOLCHAIN)
    s=snapshot(m,{'gate':True,'entry':{'active':True,'amount':q(1,3)},'entries':[]})
    check(p,s,'scoped','VALUE',{'active':True,'amount':q(1,3)})
    check(p,s,'default','VALUE',{'active':False,'amount':q(2,3)})
    check(p,s,'overlap','CONFLICT',reason='EXCEPTION_OVERLAP')
    replace(s,'entries',observed('list[Entry]',[unknown('Entry'),unknown('Entry')],structured=True))
    check(p,s,'count','VALUE','2',missing_inputs=[])
    s['facts']['gate']['value']=False
    replace(s,'entry',unknown('Entry'))
    result=check(p,s,'scoped','OUT_OF_SCOPE',missing_inputs=[])
    assert not any(row['scope'].startswith('Helper') for row in result['execution']['trace'])
    check(p,s,'default','UNKNOWN',missing_inputs=['/entry'])
