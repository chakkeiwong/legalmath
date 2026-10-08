from copy import deepcopy
from pathlib import Path
import shutil
import pytest
from legalmath.canonical import canonical, digest, loads
from legalmath.catala.native.boundary import make_snapshot, prepare
from legalmath.catala.native.contracts import validate_candidate, validate_task, validate_value
from legalmath.catala.native.converter import convert
from legalmath.catala.native.host import NativeHost
from legalmath.catala.native.runtime import build, evaluate, execute_values, verify_build, verify_cases, verify_result
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import Completion
from tests.catala.backend_support import TOOLCHAIN, JDK
from .reference import controls, q, reference


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    base = tmp_path_factory.mktemp('native')
    result = []
    for task,candidate,cases in controls():
        out = base / task['task_id']
        manifest = build(task,candidate,out,JDK,**TOOLCHAIN)
        result.append((task,candidate,cases,out,manifest))
    return result


def test_six_families_exact_reference_and_instrumentation(built):
    for task,candidate,cases,out,manifest in built:
        report = verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])
        assert report['passed'] == len(cases)
        assert all(r['instrumentation_preserves_value'] for r in report['records'])
    # Independent hand calculations on the two rounding and calendar boundaries.
    assert reference('bands',{'amount':q(1,2),'threshold':q(10),'lowerRate':q(1,100),'upperRate':q(1,3)}) == {'charge':'1'}
    assert reference('deadline',{'start':'2024-02-29','months':'12','assessed':'2025-03-01'}) == {'due':'2025-02-28','late':True}


@pytest.mark.parametrize('mutation', ['unknown','conflict','incomplete','future','expired','missing'])
def test_missing_and_collection_completeness_abstain(built,mutation):
    task,_,cases,out,_ = built[0]
    s = deepcopy(cases[0]['snapshot'])
    fact = s['facts']['holdings']
    if mutation in ('unknown','conflict'):
        s['facts']['holdings'] = {'status':mutation,'reason':'SOURCE_UNAVAILABLE'}
    elif mutation == 'incomplete': fact['complete'] = False
    elif mutation == 'future': fact['recorded_at'] = '2027-01-01T00:00:00.000000Z'
    elif mutation == 'expired': fact['valid_until'] = '2021-01-01T00:00:00.000000Z'
    else: del s['facts']['holdings']
    result = evaluate(out,s,JDK)
    assert result['status']=='ABSTAIN' and result['value'] is None and result['trace']==[]
    assert result['reason']=='CONFLICTING_INPUTS' if mutation=='conflict' else result['reason']=='INCOMPLETE_INPUTS'


def test_exact_codec_rejects_floats_noncanonical_rationals_and_bad_dates():
    task,_,_ = controls()[0]
    for typ,value in [('decimal',0.1),('decimal',{'numerator':'2','denominator':'6'}),('decimal',{'numerator':'1','denominator':'0'}),('integer',42),('integer','-0'),('date','2023-02-29'),('boolean',1)]:
        with pytest.raises(LegalMathError): validate_value(task,typ,value)


def test_no_hidden_ir_or_computed_inputs_and_field_evidence():
    task,candidate,cases = controls()[0]
    assert [f['type'] for f in task['inputs']] == ['list[Holding]']
    assert 'RuleIR' not in candidate['source']
    s = deepcopy(cases[1]['snapshot'])
    del s['evidence']['/holdings/0/amount']
    with pytest.raises(LegalMathError): prepare(task,s)
    s = deepcopy(cases[1]['snapshot']); s['facts']['exposure'] = {'status':'unknown','reason':'MISSING'}
    with pytest.raises(LegalMathError): prepare(task,s)


@pytest.mark.parametrize('source', ['scope Portfolio:\n  definition exposure equals 0.0','> Include: /tmp/secret\n```catala\nscope Portfolio:\n definition exposure equals 0.0\n```','```catala\nscope Portfolio:\n definition exposure equals #[debug.print="x"] 0.0\n```'])
def test_candidate_rejects_vacuous_or_uncontrolled_source(source):
    task,candidate,_ = controls()[0]; candidate['source']=source
    with pytest.raises(LegalMathError): validate_candidate(task,candidate)


def test_source_quote_coverage_and_task_identity():
    task,candidate,_ = controls()[0]
    candidate['anchors'][0]['quote']='invented legal text'
    with pytest.raises(LegalMathError): validate_candidate(task,candidate)
    task,candidate,_ = controls()[0]; task['question']='Changed meaning'
    with pytest.raises(LegalMathError): validate_candidate(task,candidate)
    task,candidate,_ = controls()[0]
    task['types'][0]['fields'][0]['type']='Holding'
    with pytest.raises(LegalMathError): validate_task(task)


def test_trace_and_result_forgery_detected_by_java_replay(built):
    _,_,cases,out,_ = built[0]
    s = cases[1]['snapshot']; correct=evaluate(out,s,JDK)
    assert correct['trace'] and all(row['scope']=='Portfolio' for row in correct['trace'])
    for field in ('value','trace','source_map','evidence'):
        altered=deepcopy(correct)
        altered[field] = [] if field in ('trace','source_map') else {}
        altered['result_hash'] = digest({k:v for k,v in altered.items() if k!='result_hash'})
        with pytest.raises(LegalMathError): verify_result(out,s,altered,JDK)


def test_repeated_scope_trace_has_distinct_actual_values(built):
    _,_,cases,out,_=built[4]
    r=evaluate(out,cases[3]['snapshot'],JDK)
    values=[x['value'] for x in r['trace'] if x['scope']=='Entitlement' and x['field']=='amount']
    assert values==['0','20','30']
    assert r['value']=={'total':'50'}


def test_reproducible_and_tamper_evident_build(built,tmp_path):
    task,candidate,_,out,manifest=built[0]
    again=build(task,candidate,tmp_path/'again',JDK,**TOOLCHAIN)
    assert again==manifest
    damaged=tmp_path/'damaged'; shutil.copytree(out,damaged)
    with (damaged/'instrumented.jar').open('ab') as f: f.write(b'altered')
    with pytest.raises(LegalMathError): verify_build(damaged)


@pytest.mark.parametrize('index,old,new', [
 (0,'if h.eligible then h.amount else 0.0','h.amount'),
 (1,'money of (','money of (100.0 * ('),
 (2,'date round down','date round up'),
 (3,'base * 2','base * 3'),
 (4,'age >= 18','age > 18'),
 (5,'under condition suspended','under condition not suspended')])
def test_semantic_mutants_have_independent_witnesses(built,tmp_path,index,old,new):
    task,candidate,cases,_,_=built[index]
    mutant=deepcopy(candidate)
    mutant['source']=mutant['source'].replace(old,new)
    if index==1: mutant['source']=mutant['source'].replace('upperRate)','upperRate))')
    out=tmp_path/'mutant'
    build(task,mutant,out,JDK,**TOOLCHAIN)
    with pytest.raises(LegalMathError,match='integrity'):
        verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])


class RecordedProvider:
    provider_id='test.recorded.native'
    live=False
    def __init__(self,candidate,challenge=False):
        self.candidate=candidate; self.requests=[]; self.challenge=challenge
    def complete(self,request,schema,settings):
        self.requests.append(request)
        if request['operation']=='native_catala_generation': value=deepcopy(self.candidate)
        else: value={'verdict':'SUPPORTED','findings':['The calculation preserves the source qualifier.']}
        if self.challenge and len(self.requests)==2:
            value={'verdict':'CHALLENGED','findings':['Recheck the explicit complete inventory assumption.']}
        return Completion(value,{'provider':self.provider_id,'fixture_only':True})


def test_converter_repair_resume_no_hidden_answers_and_stale_context(tmp_path):
    task,candidate,cases=controls()[0]; provider=RecordedProvider(candidate,challenge=True)
    out=tmp_path/'conversion'
    state=convert(task,out,provider,JDK,**TOOLCHAIN)
    assert state['status']=='READY_FOR_BEHAVIOR_CHECK' and len(provider.requests)==4
    for request in provider.requests:
        assert '"expected":' not in canonical(request).decode() and 'snapshot' not in request
    resumed=convert(task,out,provider,JDK,resume=True,**TOOLCHAIN)
    assert resumed==state and len(provider.requests)==4
    altered=deepcopy(task); altered['question']='Different question'
    with pytest.raises(LegalMathError): convert(altered,out,provider,JDK,resume=True,**TOOLCHAIN)
    response=out/'attempt-0.generation.response.json'; data=loads(response.read_bytes()); data['value']['interpretation']='changed'
    response.write_bytes(canonical(data))
    with pytest.raises(LegalMathError): convert(task,out,provider,JDK,resume=True,**TOOLCHAIN)


def host(built,tmp_path):
    identities={'engineer':['engineering'],'lawyer':['legal'],'operator':['operations']}
    h=NativeHost(tmp_path/'host.sqlite',identities,JDK)
    task,candidate,cases,out,manifest=built[0]
    release=h.stage('engineer',out,cases[:1],compiler=TOOLCHAIN['compiler'])
    h.approve('engineer',release,'engineering'); h.approve('lawyer',release,'legal')
    h.activate('engineer',release,expected_active=None)
    h.set_revision('operator','synthetic','0',expected=None)
    return h,release


def test_native_host_approvals_replay_stale_and_idempotency(built,tmp_path):
    h,release=host(built,tmp_path); s=built[0][2][1]['snapshot']
    with pytest.raises(LegalMathError): h.approve('operator',release,'legal')
    r=h.transact('operator','event.1',s,expected_release=release)
    assert h.replay('operator','event.1')==r
    assert h.transact('operator','event.1',s,expected_release=release)==r
    other=deepcopy(s); other['subject_id']='changed'
    with pytest.raises(LegalMathError): h.transact('operator','event.1',other,expected_release=release)
    h.set_revision('operator','synthetic','1',expected='0')
    with pytest.raises(LegalMathError): h.transact('operator','event.2',s,expected_release=release)


def test_host_rechecks_concurrent_revision_before_commit(built,tmp_path,monkeypatch):
    h,release=host(built,tmp_path); s=built[0][2][1]['snapshot']
    from legalmath.catala.native import host as module
    original=module.evaluate
    def racing(*args,**kwargs):
        r=original(*args,**kwargs)
        h.set_revision('operator','synthetic','1',expected='0')
        return r
    monkeypatch.setattr(module,'evaluate',racing)
    with pytest.raises(LegalMathError): h.transact('operator','raced',s,expected_release=release)
    with h.connect() as db: assert db.execute('SELECT count(*) FROM receipts').fetchone()[0]==0


def test_release_replacement_does_not_change_historical_replay(built,tmp_path):
    h,release=host(built,tmp_path); s=built[0][2][1]['snapshot']
    original=h.transact('operator','event.1',s,expected_release=release)
    _,_,cases,out,_=built[1]
    replacement=h.stage('engineer',out,cases[:1],compiler=TOOLCHAIN['compiler'])
    with pytest.raises(LegalMathError): h.activate('engineer',replacement,expected_active=release)
    h.approve('engineer',replacement,'engineering'); h.approve('lawyer',replacement,'legal')
    h.activate('engineer',replacement,expected_active=release)
    assert h.replay('operator','event.1')==original
    with pytest.raises(LegalMathError): h.activate('engineer',release,expected_active=release)


def test_explicit_source_bounds_abstain_and_java_rejects(tmp_path):
    from .reference import bounded_control
    from legalmath.catala.native.runtime import run_command
    task,candidate,cases=bounded_control(*controls()[2])
    out=tmp_path/'bounded'
    build(task,candidate,out,JDK,**TOOLCHAIN)
    assert verify_cases(out,cases,JDK,compiler=TOOLCHAIN['compiler'])['passed']==len(cases)
    inputs={k:v['value'] for k,v in cases[-1]['snapshot']['facts'].items()}
    with pytest.raises(LegalMathError): execute_values(out,inputs,JDK)
    direct=run_command([JDK/'bin/java','-cp',str(out/'instrumented.jar'),'catala.stdlib.NativeBridge'],out,input_bytes=canonical(inputs),timeout=15)
    assert direct['exit_code']!=0 and 'outside declared domain' in direct['stderr']
    task['bounds'][0]['quote']='invented restriction'
    with pytest.raises(LegalMathError): validate_task(task)


def test_native_identical_consequences_and_distinct_conflict(tmp_path):
    from .reference import task,f
    t=task('nativeconflict','NativeConflict','Either exemption supplies the same value, without declared priority.',
           [f('first','boolean'),f('second','boolean')],[f('value','integer')])
    c={'record_type':'NativeCatalaCandidate','task_hash':digest(t),
       'source':'```catala\nscope NativeConflict:\n  label baseRule definition value equals 0\n  exception baseRule definition value under condition first consequence equals 1\n  exception baseRule definition value under condition second consequence equals 1\n```',
       'interpretation':'Two same-level exceptions, no invented priority.','assumptions':[],'unresolved':[],
       'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'],'code_excerpt':'scope NativeConflict:'}]}
    out=tmp_path/'samelevel';build(t,c,out,JDK,**TOOLCHAIN)
    # The pinned compiler coalesces identical literal consequences. This is
    # deliberately not RuleIR's multiple-true status policy.
    values={'first':True,'second':True}
    assert execute_values(out,values,JDK)['value']=={'value':'1'}
    from legalmath.catala.native.runtime import interpreter_check
    interpreter_check(t,c,values,{'value':'1'},compiler=TOOLCHAIN['compiler'])
    different=deepcopy(c)
    different['source']=different['source'].replace('condition second consequence equals 1','condition second consequence equals 2')
    second=tmp_path/'distinct';build(t,different,second,JDK,**TOOLCHAIN)
    with pytest.raises(LegalMathError): execute_values(second,values,JDK)
