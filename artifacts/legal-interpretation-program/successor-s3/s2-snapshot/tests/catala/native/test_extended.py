from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.catala.native.boundary import make_snapshot
from legalmath.catala.native.runtime import build, evaluate, verify_cases, verify_result
from legalmath.errors import LegalMathError
from tests.catala.backend_support import TOOLCHAIN, JDK
from .reference import task, f, q, controls


def extended_control():
    t = task('optional', 'Selection', 'Select the greater of the Fixed amount (or zero for Empty) and a known optional rate. An absent rate leaves the amount unchanged.',
             [f('choice','Choice'), f('rate','optional[decimal]')],
             [f('amount','decimal'), f('echo','Choice'), f('optionalEcho','optional[decimal]')],
             [{'name':'Choice','kind':'enum','fields':[], 'cases':[{'name':'Fixed','type':'decimal'}, {'name':'Empty','type':None}]}])
    t.update(native_profile='legalmath.catala.native.v2', imports=['Decimal_en'])
    src='''```catala
scope Selection:
  definition amount equals
    let base equals match choice with pattern
      -- Fixed content amount: amount
      -- Empty: 0.0
    in
    match rate with pattern
      -- Present content amount: Decimal.max of base, amount
      -- Absent: base
  definition echo equals choice
  definition optionalEcho equals rate
```'''
    c={'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':src,
       'interpretation':t['packet']['selected_slice'],'assumptions':[],'unresolved':[],
       'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'],'code_excerpt':'scope Selection:'}]}
    rows=[({'case':'Empty','value':None},None,q(0)),
          ({'case':'Fixed','value':q(1,3)},None,q(1,3)),
          ({'case':'Fixed','value':q(1,3)},{'present':q(2,3)},q(2,3)),
          ({'case':'Fixed','value':q(1,3)},{'present':q(-2)},q(1,3))]
    cases=[{'id':str(i),'snapshot':make_snapshot(t,{'choice':choice,'rate':rate}),
            'expected':{'status':'VALUE','value':{'amount':amount,'echo':choice,'optionalEcho':rate}}}
           for i,(choice,rate,amount) in enumerate(rows)]
    return t,c,cases


@pytest.fixture(scope='module')
def extended(tmp_path_factory):
    t,c,cases=extended_control();out=tmp_path_factory.mktemp('extended')
    m=build(t,c,out,JDK,**TOOLCHAIN)
    return t,c,cases,out,m


def test_optional_payload_imports_exact_interpreter_and_plain_java(extended):
    t,c,cases,out,m=extended
    report=verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])
    assert report['passed']==4
    events=[e for row in report['records'] for e in row['result']['decisions']]
    assert {e['value'] for e in events if e['kind']=='enum'}=={'Fixed','Empty'}
    assert {e['value'] for e in events if e['kind']=='option'}=={'Present','Absent'}
    assert all(e['program_sha256']==m['source_sha256'] for e in events)


def test_absence_is_not_unknown_and_trace_location_forgery_fails(extended):
    t,c,cases,out,m=extended
    s=deepcopy(cases[0]['snapshot'])
    assert evaluate(out,s,JDK)['status']=='VALUE'
    s['facts']['rate']={'status':'unknown','reason':'No observation'}
    assert evaluate(out,s,JDK)['status']=='ABSTAIN'
    s=cases[0]['snapshot'];result=evaluate(out,s,JDK)
    result['decisions'][0]['start_line']+=1
    result['result_hash']=digest({k:v for k,v in result.items() if k!='result_hash'})
    with pytest.raises(LegalMathError):verify_result(out,s,result,JDK)


@pytest.mark.parametrize('index',range(6))
def test_compiler_trace_preserves_collections_dates_rounding_scopes_exceptions(tmp_path,index):
    t,c,cases=controls()[index]
    t['native_profile']='legalmath.catala.native.v2';c['task_hash']=digest(t)
    out=tmp_path/'build';build(t,c,out,JDK,**TOOLCHAIN)
    report=verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])
    assert report['passed']==len(cases)
    if index in (1,3,4,5):
        assert any(r['result']['decisions'] for r in report['records'])


def test_declared_library_closure_executes_in_all_three_backends(tmp_path):
    t=task('libraries','Libraries','Return exact minima, the last calendar day and a bounded list sequence.',
           [f('n','integer'),f('cash','money'),f('asOf','date')],
           [f('integerResult','integer'),f('moneyResult','money'),f('monthEnd','date'),f('numbers','list[integer]')])
    t.update(native_profile='legalmath.catala.native.v2',imports=['Integer_en','Money_en','Date_en','List_en'])
    c={'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':'''```catala
scope Libraries:
  definition integerResult equals Integer.min of n, 3
  definition moneyResult equals Money.min of cash, $1.00
  definition monthEnd equals Date.last_day_of_month of |2024-02-15|
  definition numbers equals List.sequence of 1, n
```''','interpretation':t['question'],'assumptions':[],'unresolved':[],
       'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'],'code_excerpt':'scope Libraries:'}]}
    cases=[{'id':'leap','snapshot':make_snapshot(t,{'n':'3','cash':'99','asOf':'2024-02-15'}),
            'expected':{'status':'VALUE','value':{'integerResult':'3','moneyResult':'99','monthEnd':'2024-02-29','numbers':['1','2']}}}]
    out=tmp_path/'libs';build(t,c,out,JDK,**TOOLCHAIN)
    assert verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])['passed']==1


def test_lazy_branch_trace_records_only_executed_source_choices(tmp_path):
    t=task('lazy','Lazy','Choose 1 if guard, otherwise 2 if inner, otherwise the reciprocal.',
           [f('guard','boolean'),f('inner','boolean'),f('denominator','decimal')],[f('result','decimal')])
    t['native_profile']='legalmath.catala.native.v2'
    c={'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':'''```catala
scope Lazy:
  definition result equals
    if guard then 1.0
    else if inner then 2.0
    else 1.0 / denominator
```''','interpretation':t['question'],'assumptions':[],'unresolved':[],
       'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'],'code_excerpt':'scope Lazy:'}]}
    cases=[{'id':'skip-danger','snapshot':make_snapshot(t,{'guard':True,'inner':False,'denominator':q(0)}),'expected':{'status':'VALUE','value':{'result':q(1)}}},
           {'id':'inner','snapshot':make_snapshot(t,{'guard':False,'inner':True,'denominator':q(0)}),'expected':{'status':'VALUE','value':{'result':q(2)}}},
           {'id':'reciprocal','snapshot':make_snapshot(t,{'guard':False,'inner':False,'denominator':q(2)}),'expected':{'status':'VALUE','value':{'result':q(1,2)}}}]
    out=tmp_path/'lazy';build(t,c,out,JDK,**TOOLCHAIN)
    report=verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])
    choices=[[e for e in r['result']['decisions'] if e['kind']=='branch'] for r in report['records']]
    assert [len(es) for es in choices]==[1,2,2]
    assert [e['value'] for e in choices[2]]==[False,False]
