from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.formal import bundle
from legalmath.interpretation.assurance import proof_certificate as proof
from .support import packet,reading
from tests.search.test_formal import AT


def test_lean_kernel_and_all_boolean_states_of_real_java(root,tmp_path):
    r=reading();b=bundle(r,packet(),AT);jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    c=proof.produce(r,b,AT,tmp_path/'produce',jdk)
    assert c['kernel']['status']=='KERNEL_CHECKED'
    assert c['runtime']['cases']==16
    assert proof.verify(c,r,b,tmp_path/'verify',jdk)['status']=='VERIFIED'
    assert not c['legal_correctness_established']


def test_lean_rejects_false_lowering_even_if_bundle_is_well_typed(tmp_path):
    r=reading();b=bundle(r,packet(),AT)
    b['rules'][0]['body']['args'][1]=b['rules'][0]['body']['args'][1]['arg']
    with pytest.raises(LegalMathError):proof.kernel(r,b,tmp_path)
    assert 'error' in (tmp_path/'lean.log').read_text()


def test_checker_does_not_trust_forged_proof_scope_or_changed_target(root,tmp_path):
    r=reading();b=bundle(r,packet(),AT);jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    c=proof.produce(r,b,AT,tmp_path/'produce',jdk)
    fake=deepcopy(c);fake['kernel']['excludes']=[]
    with pytest.raises(LegalMathError):proof.verify(fake,r,b,tmp_path/'false-claim',jdk)
    fake=deepcopy(c);fake['runtime']['cases']=1
    with pytest.raises(LegalMathError):proof.verify(fake,r,b,tmp_path/'partial-domain',jdk)
    fake=deepcopy(c);fake['reading_hash']='0'*64
    with pytest.raises(LegalMathError):proof.verify(fake,r,b,tmp_path/'target',jdk)


def test_conflict_in_unused_fact_is_not_falsely_treated_as_dependency(root,tmp_path):
    r=reading();r['formalization']['result']='gift';b=bundle(r,packet(),AT)
    c=proof.produce(r,b,AT,tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1')
    assert c['runtime']['cases']==16


@pytest.mark.parametrize('expression',['(> gift false)','(and gift)','(not gift) extra','(= gift false)','(__import__ os)','(date 2026-01-01)'])
def test_unsupported_syntax_does_not_enter_lean(expression):
    with pytest.raises(LegalMathError):proof.parse_source(expression,['gift'])


def test_kernel_failure_is_not_a_certificate(tmp_path,monkeypatch):
    r=reading();b=bundle(r,packet(),AT)
    monkeypatch.setattr(proof,'LEAN',Path('/missing/lean'))
    with pytest.raises(FileNotFoundError):proof.kernel(r,b,tmp_path)


def test_large_supported_boolean_domain_reports_the_limit_without_codec_failure(tmp_path):
    from legalmath.canonical import canonical,loads
    r=reading();template=deepcopy(r['formalization']['facts'][0])
    r['formalization']['facts']=[{**template,'name':'fact.'+str(i)} for i in range(30)]
    r['formalization']['result']='fact.0'
    b=bundle(r,packet(),AT)
    result=proof.enumerate_java(r,b,AT,tmp_path,Path('/deliberately-unused-jdk'))
    assert result['status']=='NOT_RUN_DOMAIN_LIMIT'
    assert result['required_cases']==str(4**30)
    assert loads(canonical(result))==result
