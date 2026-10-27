from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased import capacity_checkpoint as checkpoint
from legalmath.interpretation.assurance.phased.context_disposition import schema
from legalmath.interpretation.assurance.bounded_context import Limits

def shape(paths):
    return {'properties':{'need_dispositions':{'items':{'properties':{
        'answer_evidence':{'properties':{'path':{'type':'string','enum':paths}}}}}}}}

def test_only_identical_path_population_can_change_order():
    old=shape(['','/answer','/condition']);new=shape(['','/condition','/answer'])
    request={'task':'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT'}
    assert checkpoint.same_schema(old,new,request)
    assert not checkpoint.same_schema(old,new,{'task':'ANSWER_ORIGINAL_QUESTION'})
    assert not checkpoint.same_schema(old,shape(['','/condition','/different']),request)
    assert not checkpoint.same_schema(old,shape(['','/condition','/answer','/answer']),request)
    changed=deepcopy(new);changed['additionalProperties']=False
    assert not checkpoint.same_schema(old,changed,request)
    assert old==shape(['','/answer','/condition'])

def test_actual_failed_schema_and_retained_consumer():
    root=Path('/home/chakwong/python/legalmath')
    work=root/'artifacts/legal-mission-control/2026-10-26/product-closure'
    pointer={'path':str((work/'p14-checkpoint-v3.json').relative_to(root)),
        'sha256':__import__('hashlib').sha256((work/'p14-checkpoint-v3.json').read_bytes()).hexdigest()}
    value=json.loads((work/'p14-checkpoint-v3.json').read_text())
    key='corrected-audit-context-disposition-p14-87729a9bc4341f40700b2e11'
    row=value['calls'][key]
    request=json.loads((root/row['request']['path']).read_text())
    prior=json.loads((root/row['schema']['path']).read_text())
    current=schema(request['payload']['prior_needs'],request['payload']['answer'])
    assert prior!=current and checkpoint.same_schema(prior,current,request)
    checked=[]
    product=SimpleNamespace(root=root,capacity_checkpoint=pointer,
        route=SimpleNamespace(input_hash=value['input_hash'],limits=Limits(),encode=list))
    call=dict(key=key,request=request,schema=current,validate=lambda v:checked.append(v))
    result=checkpoint.retained(product,call)
    assert result['status']=='VALIDATED' and result['provenance']['new_provider_calls']==0
    assert checked==[result['value']]
    changed=deepcopy(current)
    changed['properties']['need_dispositions']['items']['properties']['answer_evidence']['properties']['path']['enum'].append('/invented')
    with pytest.raises(LegalMathError):checkpoint.retained(product,{**call,'schema':changed})
