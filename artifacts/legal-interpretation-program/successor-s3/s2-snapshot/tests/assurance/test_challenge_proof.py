from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import challenge_proof as proof
from legalmath.interpretation.assurance.diversity import save


def test_conditional_and_partition_rules_are_checked_by_lean(tmp_path):
    value=proof.kernel(tmp_path)
    assert value==proof.verify(tmp_path) and len(value['theorems'])==3
    assert 'English entailment' in value['excludes']
    assert 'Python-to-Lean implementation equivalence' in value['excludes']


@pytest.mark.parametrize('defect',['source','receipt','log'])
def test_changed_proof_or_receipt_rejected(tmp_path,defect):
    value=proof.kernel(tmp_path)
    if defect=='source':(tmp_path/'ChallengeRules.lean').write_text('theorem fraud : False := by sorry')
    elif defect=='receipt':
        value['status']='APPROVED';save(tmp_path/'certificate.json',value)
    else:(tmp_path/'lean.log').write_text('KERNEL_CHECKED')
    with pytest.raises(LegalMathError):proof.verify(tmp_path)


def test_unproved_false_theorem_cannot_be_added(tmp_path,monkeypatch):
    bad=tmp_path/'bad.lean';bad.write_text(proof.PRELUDE.read_text()+'\ntheorem fraud : False := by sorry\n#print axioms fraud\n')
    monkeypatch.setattr(proof,'PRELUDE',bad)
    with pytest.raises(LegalMathError):proof.kernel(tmp_path/'run')
