"""Harness refusal checks are separate from actual installed repair results."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from scripts.prospectus_input_repair_evidence import same,validate_record,DENOMINATORS
from scripts.prospectus_component_installed_worker import identity

def test_complete_comparator_rejects_false_as_zero():
    with pytest.raises(ValueError,match='differs'):same({'amount':False},{'amount':0},'typed amount')

def test_complete_comparator_rejects_unrelated_answer_loss():
    with pytest.raises(ValueError):same({'Q4':'YES'},{'Q4':'YES','unknowns':['source']},'answer')

def test_record_requires_every_case_and_family():
    record={family:{group:[{'checked':True} for _ in range(n)] for group,n in groups.items()} for family,groups in DENOMINATORS.items()}
    assert validate_record(record)==DENOMINATORS
    for family,groups in DENOMINATORS.items():
        for group in groups:
            bad=deepcopy(record);bad[family][group].pop()
            with pytest.raises(ValueError,match='Missing cases'):validate_record(bad)
    record.pop('law')
    with pytest.raises(ValueError,match='Missing repair family'):validate_record(record)

def test_installed_identity_rejects_checkout_module(tmp_path):
    package=tmp_path/'installed/legalmath';package.mkdir(parents=True)
    source=tmp_path/'src/legalmath/__init__.py';source.parent.mkdir(parents=True);source.write_text('')
    with pytest.raises(ValueError,match='outside installed target'):
        identity(package,{}, {'legalmath':SimpleNamespace(__file__=str(source))})
