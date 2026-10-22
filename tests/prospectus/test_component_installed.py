"""Wrong import origins and altered complete records must fail installed checks."""
from hashlib import sha256
from types import SimpleNamespace
import pytest
from scripts.prospectus_component_installed_worker import identity
from scripts.prospectus_component_evidence import same, helper


def test_checkout_import_cannot_masquerade_as_identical_installed_file(tmp_path):
    package = tmp_path/'installed'; package.mkdir()
    outside = tmp_path/'checkout.py'; outside.write_text('x=1\n')
    inside = package/'__init__.py'; inside.write_bytes(outside.read_bytes())
    expected = {'__init__.py':sha256(inside.read_bytes()).hexdigest()}
    assert identity(package,expected,{'legalmath':SimpleNamespace(__file__=str(inside))})
    with pytest.raises(ValueError,match='outside installed target'):
        identity(package,expected,{'legalmath':SimpleNamespace(__file__=str(outside))})


def test_altered_installed_module_refused_even_at_correct_path(tmp_path):
    module = tmp_path/'__init__.py'; module.write_text('original')
    expected = {'__init__.py':sha256(module.read_bytes()).hexdigest()}
    module.write_text('changed')
    with pytest.raises(ValueError,match='bytes differ'):
        identity(tmp_path,expected,{'legalmath':SimpleNamespace(__file__=str(module))})


def test_equal_financial_value_does_not_hide_unrelated_answer_loss():
    before = {'Q5':{'amount':'10'},'Q1':{'unresolved':['missing source']}}
    with pytest.raises(ValueError,match='Complete retained evidence differs'):
        same({'Q5':before['Q5']},before,'entire answer')


def test_unknown_component_cannot_select_an_arbitrary_helper(tmp_path):
    with pytest.raises(ValueError,match='Unknown finite component'):
        helper(tmp_path,'unreviewed')


def test_component_selector_cannot_validate_another_task():
    from scripts.prospectus_component_revalidation import selector, BOUNDS, REL
    value = {'version':'current-installed-component.v1','kind':'comparative',
        'review':REL+'/reviews/declared','baseline':REL+'/attempts/source-bes-dep-06/attempt-010',
        'wheel_attempt':None,'bounds':BOUNDS}
    with pytest.raises(ValueError,match='Wrong component task'):
        selector({'id':'finance-conventions','current_component_validation':value})
