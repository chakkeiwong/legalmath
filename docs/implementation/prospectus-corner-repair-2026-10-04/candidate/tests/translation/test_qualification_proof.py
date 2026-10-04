from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.canonical import canonical
from legalmath.errors import LegalMathError
from legalmath.qualification import proof
from .v2_support import fixture_v2, as_model


def integer_model():
    return as_model(*fixture_v2([('x','integer'),('flag','bool')],
        [('value','integer','true','(default (call offset x) (exception override (> x (integer 90)) (integer 100)))'),
         ('copy','integer','flag','(rule value)')],
        helpers=[{'name':'offset','parameters':[{'name':'n','type':'integer'}],
                  'result_type':'integer','body':'(+ n (integer 7))'}],
        text='Synthetic formal premises for constructor preservation.'))


def test_kernel_checks_arithmetic_helpers_defaults_and_references_for_all_contexts(tmp_path):
    m=integer_model(); c=proof.produce(m,tmp_path/'produce')
    assert c['status']=='KERNEL_CHECKED'
    assert 'every input context' in c['scope']['proved']
    assert proof.verify(c,m,tmp_path/'verify')==c
    assert c['legal_correctness']=='NOT_ESTABLISHED'
    assert not c['human_quality_evidence']


def test_wrong_lowering_is_rejected_by_kernel_not_by_an_answer_key(tmp_path):
    m=integer_model();formal=deepcopy(m['review']['reading']['formalization'])
    m['review'].update(origin='manual',reading=None)
    m['helpers'][0]['body']['op']='sub'
    with pytest.raises(LegalMathError):
        proof.produce(m,tmp_path,formalization=formal)
    assert 'error' in (tmp_path/'lean.log').read_text()


def test_imported_proof_and_scope_are_not_trusted(tmp_path):
    m=integer_model();c=proof.produce(m,tmp_path/'original')
    (tmp_path/'original/Translation.lean').write_text('axiom anything : False')
    assert proof.verify(c,m,tmp_path/'regenerated')==c
    c['scope']=deepcopy(c['scope']);c['scope']['excludes']=[]
    with pytest.raises(LegalMathError):proof.verify(c,m,tmp_path/'forged')


@pytest.mark.parametrize('text',['(integer 1) extra','(not true','())','(run_system cat)','(call x "evil")'])
def test_untrusted_syntax_never_becomes_lean_code(text):
    with pytest.raises(LegalMathError):
        proof.encode(proof.source_tree(proof.parse(text),[]))


def test_richer_semantics_remain_explicitly_outside_this_proof(tmp_path):
    m=as_model(*fixture_v2([('x','decimal')],[('value','integer','true','(round integer floor x)')],text='Exact fractional input.'))
    with pytest.raises(LegalMathError) as exc:proof.produce(m,tmp_path)
    assert exc.value.code=='E_UNSUPPORTED_PROFILE'
