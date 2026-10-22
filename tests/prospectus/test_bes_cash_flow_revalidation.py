"""Retained replay cannot silently replace any substantive old method."""
import pytest
from scripts.prospectus_bes_cash_flow_revalidation import verify_method_parity, ROUTER

def test_only_named_router_change_is_permitted():
    before={'consumer':'old','oracle':'old',ROUTER:'old'}
    verify_method_parity(before,{**before,ROUTER:'reviewed new routing'})

@pytest.mark.parametrize('name',['consumer','oracle','extra'])
def test_substantive_changes_or_missing_method_are_refused(name):
    before={'consumer':'old','oracle':'old',ROUTER:'old'}
    with pytest.raises(ValueError):verify_method_parity(before,{**before,name:'changed'})

def test_missing_protected_method_refused():
    with pytest.raises(ValueError):verify_method_parity({'consumer':'x',ROUTER:'x'},{ROUTER:'y'})
