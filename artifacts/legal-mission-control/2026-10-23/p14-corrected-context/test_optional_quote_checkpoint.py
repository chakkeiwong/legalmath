from copy import deepcopy
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import capacity_checkpoint, capacity_policy, context_disposition as context
from tests.assurance.test_context_need_disposition import setup

def test_bad_retained_quote_does_not_cancel_valid_independent_request(tmp_path):
    args=setup(tmp_path,('SOURCE_TEXT',))
    p,item,answer,initial,request,shape,rows,failures,valid=args
    invalid=deepcopy(valid)
    invalid['need_dispositions'][0]['answer_evidence']['quote']='This text is invented.'
    calls=[];checkpoint={}
    for key,value in [('bad',invalid),('good',valid)]:
        req=deepcopy(request);req['diagnostic_case']=key
        folder=tmp_path/'retained'/key
        for name,data in [('request',capacity_policy.annotate(req)),('schema',shape),('result',dict(status='VALIDATED',value=value))]:
            save(folder/(name+'.json'),data)
        checkpoint[key]={**{name:evidence_file(folder/(name+'.json'),tmp_path) for name in ('request','schema','result')},'mode':'VALIDATED'}
        calls.append(dict(key=key,request=req,schema=shape,validate=lambda v:context.validate(
            p,'p14',v,answer,item,rows,request['records'],failures)))
    save(tmp_path/'checkpoint.json',dict(profile=capacity_checkpoint.PROFILE,input_hash=p.route.input_hash,calls=checkpoint))
    p.capacity_checkpoint=evidence_file(tmp_path/'checkpoint.json',tmp_path)
    with pytest.raises(LegalMathError) as error:
        calls[0]['validate'](invalid)
    assert error.value.code=='E_SCHEMA'
    output=p.run_phase('optional-quotation-replay',calls)
    assert [r['result']['status'] for r in output['results']]==['FAILED','VALIDATED']
    assert output['results'][0]['result']['error']=='E_SCHEMA'
    assert output['results'][1]['result']['value']==valid
    assert not p.provider.requests
    assert not (p.directory/'calls/dispatch.json').exists() or not __import__('json').loads((p.directory/'calls/dispatch.json').read_text())['calls']
    # A false optional quote is response evidence; the saved predecessor is untouched.
    assert __import__('json').loads((tmp_path/'retained/bad/result.json').read_text())['value']==invalid

def test_changed_shared_checkpoint_still_has_integrity_veto(tmp_path):
    args=setup(tmp_path,('SOURCE_TEXT',))
    p,item,answer,initial,request,shape,rows,failures,value=args
    save(tmp_path/'checkpoint.json',dict(profile=capacity_checkpoint.PROFILE,input_hash='foreign',calls={}))
    p.capacity_checkpoint=evidence_file(tmp_path/'checkpoint.json',tmp_path)
    with pytest.raises(LegalMathError) as error:
        p.run_phase('wrong-shared-input',[dict(key='one',request=request,schema=shape,validate=lambda _:None)])
    assert error.value.code=='E_INTEGRITY' and not p.provider.requests
