"""Bounded repair cannot discard successes, source gaps or repeated failures."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from legalmath.interpretation.assurance.phased import account_contract,account_encoding,account_recovery,failure_recovery
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.search.providers import Completion
from legalmath.errors import LegalMathError
from tests.assurance.test_bounded_product import Scripted,envelope,limits

def put(root,name,value):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
    return evidence_file(p,root)

class Numbered(Scripted):
    def __init__(self, broken=True):
        super().__init__();self.broken=broken
    def complete(self,request,schema,settings):
        result=super().complete(request,schema,settings)
        if self.broken:result.value['unresolved']=['Paragraph 10 is not verified in these sources.']
        return result

def fixture(root):
    options=dict(limits=replace(limits(),input_tokens=12000),requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE)
    first=BoundedProduct(root,root/'first',Numbered(),envelope(),list,**options)
    q=envelope()['original_questions'][0]
    records=[r for r in first.route.records.values() if r['kind']=='source']
    outcome=first.note('detail-0','ASSESS_ORIGINAL_REQUIREMENT',q,records,{'assignment':'original'},['o1'])
    assert outcome['status']=='FAILED'
    details=[dict(id='o1',result=outcome)]
    put(root,'first/requirement-details.json',details)
    checkpoint=account_recovery.build(root,first.directory/'calls',details)
    checkpoint=failure_recovery.diagnose(root,checkpoint,provider_directory='unused')
    pointer=put(root,'recovery.json',checkpoint)
    return first,options,q,records,pointer

def test_correction_runs_and_preserves_exact_assignment(tmp_path):
    first,options,q,records,pointer=fixture(tmp_path)
    provider=Numbered(False)
    product=BoundedProduct(tmp_path,tmp_path/'second',provider,envelope(),list,requirement_account_recovery=pointer,**options)
    value=product.note('detail-0','ASSESS_ORIGINAL_REQUIREMENT',q,records,{'assignment':'original'},['o1'])
    assert value['status']=='VALIDATED' and len(provider.requests)==1
    assert provider.requests[0]['account_correction']['required_source_gaps']==[]
    assert json.loads((first.directory/'calls/detail-0/result.json').read_text())['status']=='FAILED'

def test_repeated_format_failure_is_held_without_new_call(tmp_path):
    first,options,q,records,pointer=fixture(tmp_path)
    second=BoundedProduct(tmp_path,tmp_path/'second',Numbered(),envelope(),list,requirement_account_recovery=pointer,**options)
    outcome=second.note('detail-0','ASSESS_ORIGINAL_REQUIREMENT',q,records,{'assignment':'original'},['o1'])
    put(tmp_path,'second/requirement-details.json',[dict(id='o1',result=outcome)])
    value=account_recovery.build(tmp_path,second.directory/'calls',[dict(id='o1',result=outcome)],predecessor=pointer)
    value=failure_recovery.diagnose(tmp_path,value,provider_directory='unused',predecessor=pointer)
    assert value['failure_recovery']['actions']=={} and value['account_recovery']['held_roots']==['detail-0']
    p=put(tmp_path,'next.json',value);provider=Numbered(False)
    third=BoundedProduct(tmp_path,tmp_path/'third',provider,envelope(),list,requirement_account_recovery=p,**options)
    assert third.note('detail-0','ASSESS_ORIGINAL_REQUIREMENT',q,records,{'assignment':'original'},['o1'])==outcome
    assert provider.requests==[]

def test_failure_policy_cannot_remove_hold_or_reset_spent_key(tmp_path):
    first,options,q,records,pointer=fixture(tmp_path)
    value=json.loads((tmp_path/pointer['path']).read_text())
    value['failure_recovery']['attempted_keys']=['detail-0']
    p=put(tmp_path,'changed.json',value)
    with pytest.raises(LegalMathError):account_recovery.load(tmp_path,p,value['input_hash'])

def test_wire_normalization_preserves_values_and_decoding():
    a={'account_identity_hashes':{'h0':'hash'},'x':{'identity_hash':'h0'},
        'account_record_table':{'metadata':{'u0':{'unit_id':'source'}},'columns':['id','text'],'rows':[['u0','r0','law']]}}
    b={'account_identity_hashes':{'h1':'hash'},'x':{'identity_hash':'h1'},
        'account_record_table':{'metadata':{'u0':{'unit_id':'source'}},'columns':['text','id'],'rows':[['u0','law','r0']]}}
    assert failure_recovery.normalized_wire(a)==failure_recovery.normalized_wire(b)
    b['account_record_table']['rows'][0][1]='different law'
    assert failure_recovery.normalized_wire(a)!=failure_recovery.normalized_wire(b)


def test_validated_root_reused_without_reconstructing_its_children(tmp_path):
    options=dict(limits=replace(limits(),input_tokens=12000),requirement_account_profile=account_contract.PROFILE,
        requirement_account_input_profile=account_encoding.PROFILE)
    first=BoundedProduct(tmp_path,tmp_path/'first',Numbered(False),envelope(),list,**options)
    details=first.requirement_details()
    value=account_recovery.build(tmp_path,first.directory/'calls',details)
    value=failure_recovery.diagnose(tmp_path,value,provider_directory='unused')
    pointer=put(tmp_path,'complete.json',value)
    provider=Numbered(False)
    fresh=BoundedProduct(tmp_path,tmp_path/'fresh',provider,envelope(),list,requirement_account_recovery=pointer,**options)
    fresh.note=lambda *a,**kw:pytest.fail('A validated root must not reconstruct or resample children')
    assert fresh.requirement_details()==details
    assert provider.requests==[]
