from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased.account_recovery import restore_record_order

def pair():
    old={'records':[{'id':'a','text':'first'},{'id':'b','text':'second'}],
        'verified_locator_bindings':[{'record_id':'a','index_hash':'idx','quote_ranges':[{'start':0,'end':5}]},
        {'record_id':'b','index_hash':'idx','quote_ranges':[{'start':0,'end':6}]}],
        'payload':{'assignment':'unchanged'},'question':'original'}
    new=deepcopy(old); new['records'].reverse(); new['verified_locator_bindings'].reverse()
    return old,new

def test_exact_complete_record_and_locator_permutation_is_restored():
    old,new=pair(); snapshot=deepcopy(new)
    assert restore_record_order(old,new)==old
    assert new==snapshot

@pytest.mark.parametrize('mutation',['quote','text','index','duplicate','missing','foreign','assignment','question'])
def test_semantic_or_population_changes_remain_rejected(mutation):
    old,new=pair()
    if mutation=='quote':new['verified_locator_bindings'][0]['quote_ranges'][0]['end']+=1
    elif mutation=='text':new['records'][0]['text']='changed'
    elif mutation=='index':new['verified_locator_bindings'][0]['index_hash']='foreign'
    elif mutation=='duplicate':new['verified_locator_bindings'].append(deepcopy(new['verified_locator_bindings'][0]))
    elif mutation=='missing':new['verified_locator_bindings'].pop()
    elif mutation=='foreign':new['verified_locator_bindings'][0]['record_id']='foreign'
    elif mutation=='assignment':new['payload']['assignment']='changed'
    else:new['question']='changed'
    with pytest.raises(LegalMathError):restore_record_order(old,new)
