"""Reject complete, rehashed corrupt financial evidence and failed stage claims."""
from copy import deepcopy
import json
from pathlib import Path
import zipfile
import pytest
from scripts import prospectus_fixed_finance_verify as v
from legalmath.prospectus import execution_acceptance


def task(**changes):
    return {'id':'finance-conventions','handler':'agent','stream':'assisted',
            'validator':'conditional-fixed-finance.v1', **changes}


def test_fixed_finance_validator_is_bound_to_the_assisted_task():
    execution_acceptance.check_task(task())
    for changes in ({'id':'other'}, {'stream':'engineering'}, {'handler':'external'}, {'validator':[]}):
        with pytest.raises(ValueError):execution_acceptance.check_task(task(**changes))


@pytest.fixture(scope='module')
def case():
    name='global-coupon-only'  # Principal entitlement is False: 0 must differ.
    return (v.read(v.ORIGINAL/(name+'-packet.json.gz')),
            v.read(v.BASE/'ordinary'/(name+'-answer.json.gz')),
            v.read(v.BASE/'ordinary'/(name+'-P5.json.gz')))


def test_complete_original_passes_independent_and_exact_checks(case):
    packet,answer,p5=case
    assert v.check_answer(answer,packet,answer)['cash_flows']==10
    v.check_p5(p5,p5,answer)


@pytest.mark.parametrize('defect',['amount','false-zero','legal','settlement','applicability',
                                   'source','unrelated','coupon','input','event'])
def test_rehashed_corruption_refused(case,defect):
    packet,original,_=case
    bad=deepcopy(original); value=bad['questions']['Q5']['value']
    if defect=='amount':value['cash_flows'][0]['amount']='0'
    elif defect=='false-zero':value['redemption']['principal_entitlements'][0]['principal_entitled']=0
    elif defect=='legal':value['legal_entitlement_established']=True
    elif defect=='settlement':value['full_settlement_supported']=True
    elif defect=='applicability':value['redemption']['source_applicability_established']=True
    elif defect=='source':value['redemption']['source_profile']['groups'].pop('interest_cessation')
    elif defect=='unrelated':bad['questions']['Q1']={'value':'invented'}
    elif defect=='coupon':value['coupons']['calculations'].pop()
    elif defect=='input':value['calculation_inputs']['redemption']['assumptions']['unamended_terms']=1
    else:value['cash_flows'][0]['payment_event']='unobserved'
    bad['report_sha256']=v.digest({k:x for k,x in bad.items() if k!='report_sha256'})
    assert bad['report_sha256']==v.digest({k:x for k,x in bad.items() if k!='report_sha256'})
    with pytest.raises((ValueError,AssertionError,KeyError)):v.check_answer(bad,packet,original)


def test_p5_mutation_refused(case):
    _,answer,original=case
    bad=deepcopy(original); bad['payload']['question']['value']['full_settlement_supported']=0
    bad['sha256']=v.digest({k:x for k,x in bad.items() if k!='sha256'})
    with pytest.raises(ValueError):v.check_p5(bad,original,answer)


@pytest.mark.parametrize('defect',['case','input','answer-control','legacy','boolean'])
def test_missing_case_or_control_refused(defect):
    data=v.read(v.BASE/'ordinary-summary.json')
    if defect=='case':data['cases'].pop()
    elif defect=='input':data['cases'][0]['input_refusals'].pop()
    elif defect=='answer-control':data['cases'][0]['corrupt_answer_refusals'].pop()
    elif defect=='legacy':data['legacy_complete_answers_equal'].pop()
    else:data['installed_ordinary_equal']=0
    with pytest.raises(ValueError):v.summary_check(data,'ordinary')


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value))


def test_failed_stage_cannot_be_pass(tmp_path):
    folder=tmp_path/'stages/ordinary'
    put(folder/'started.json',{'pid':1}); put(folder/'result.json',{'status':'PASS'})
    v.checked_stages(tmp_path,('ordinary',))
    put(folder/'failure.json',{'status':'FAIL'})
    with pytest.raises(ValueError,match='Failed stage'):v.checked_stages(tmp_path,('ordinary',))


def test_missing_source_refused(tmp_path):
    source=tmp_path/'source.txt'; source.write_text('original')
    bindings={'source.txt':v.sha(source)}; v.verify_files(tmp_path,bindings)
    source.unlink()
    with pytest.raises(ValueError,match='Missing or changed'):v.verify_files(tmp_path,bindings)


def package_fixture(tmp_path):
    name='prospectus/successor/service.py'; source=v.ROOT/'src/legalmath'/name
    production={name:v.sha(source)}; wheel=tmp_path/'wheel/check.whl'; wheel.parent.mkdir()
    with zipfile.ZipFile(wheel,'w') as archive:archive.writestr('legalmath/'+name,source.read_bytes())
    installed=tmp_path/'installed/legalmath'/name; installed.parent.mkdir(parents=True); installed.write_bytes(source.read_bytes())
    put(tmp_path/'package.json',{'files':production,'wheel_sha256':v.sha(wheel)})
    for mode,path in (('ordinary',source),('installed',installed)):
        put(tmp_path/(mode+'-imports.json'),{'legalmath.prospectus.successor.service':str(path)})
        put(tmp_path/(mode+'-summary.json'),{'import_count':1})
    return production,installed


@pytest.mark.parametrize('defect',['installed','wheel','origin','manifest'])
def test_package_drift_refused(tmp_path,defect):
    production,installed=package_fixture(tmp_path)
    assert v._check_package(tmp_path,production)['source_files']==1
    if defect=='installed':installed.write_text('changed')
    elif defect=='wheel':(tmp_path/'wheel/check.whl').write_bytes(b'changed')
    elif defect=='origin':put(tmp_path/'installed-imports.json',{'legalmath.prospectus.successor.service':str(v.ROOT/'src/legalmath/prospectus/successor/service.py')})
    else:put(tmp_path/'package.json',{'files':{},'wheel_sha256':v.sha(tmp_path/'wheel/check.whl')})
    with pytest.raises(ValueError):v._check_package(tmp_path,production)


def test_retained_complete_quantlib_records_and_source_arithmetic():
    result=v.quantlib_evidence()
    assert result['Shell_fractions']==['457/366']+['1']*9
    assert result['actual_adverse_inputs']==16


def test_reconcile_waits_for_completion_and_failure_blocks_dependents(tmp_path,monkeypatch):
    from scripts import prospectus_fixed_finance_acceptance as runner
    monkeypatch.setattr(runner,'HERE',tmp_path)
    assert set(runner.status()['ready'])=={'tests','ordinary','package'}
    put(tmp_path/'stages/ordinary/started.json',{'pid':1})
    put(tmp_path/'stages/ordinary/failure.json',{'status':'FAIL'})
    assert runner.status()['stages']['installed']=='BLOCKED'
    assert 'reconcile' not in runner.status()['ready']
    for name in ('tests','package'):
        put(tmp_path/'stages'/name/'started.json',{'pid':1})
        put(tmp_path/'stages'/name/'result.json',{'status':'PASS'})
    assert runner.status()['ready']==['reconcile']
