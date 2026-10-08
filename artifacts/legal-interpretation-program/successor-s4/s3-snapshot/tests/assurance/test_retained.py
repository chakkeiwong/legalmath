from pathlib import Path
import pytest
from legalmath.canonical import canonical,digest,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.journal import RetainedProvider
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.search.models import Settings


class Provider:
    provider_id='counted.fixture';live=True;routing={}
    def __init__(self):self.calls=[]
    def complete(self,request,schema,settings):
        self.calls.append(request);return Completion({'fresh':True},{})


def retained(tmp_path,failed=False):
    base=tmp_path/'retained';call=base/'calls/call-000';call.mkdir(parents=True)
    request={'task':'SOURCE_INVENTORY','source':'version1'};schema={'type':'object'}
    response={'value':{'claims':[]},'provenance':{'allowance_slot':1}}
    status={'status':'FAILED' if failed else 'RETURNED_UNVALIDATED','request_hash':digest(request)}
    if failed:status.update(error='E_DEPENDENCY',details='Original counted timeout')
    else:status['response_hash']=digest(response['value'])
    records={'request.json':request,'schema.json':schema,'status.json':status}
    if not failed:records['response.json']=response
    for name,value in records.items():(call/name).write_bytes(canonical(value))
    report={'status':'UNRESOLVED','release_eligible':False};(base/'report.json').write_bytes(canonical(report))
    manifest={'report_hash':digest(report),'files':{str(p.relative_to(base)):raw_digest(p.read_bytes()) for p in base.rglob('*.json')}}
    (base/'manifest.json').write_bytes(canonical(manifest))
    allowance=tmp_path/'allowance.json';allowance.write_bytes(canonical({'maximum':100,'calls':[{'request_hash':digest(request)}]}))
    return base,allowance,request,schema


def test_exact_replay_preserves_original_reservation_without_new_vote(tmp_path):
    base,allowance,request,schema=retained(tmp_path);provider=Provider()
    replay=RetainedProvider(provider,base,allowance,new_tasks={'STRUCTURED_CRITICISM'})
    before=allowance.read_bytes()
    with pytest.raises(LegalMathError):replay.complete(request,{'type':'array'},Settings())
    answer=replay.complete(request,schema,Settings())
    assert answer.provenance['allowance_slot']==1 and answer.provenance['new_live_invocation'] is False
    assert not provider.calls and allowance.read_bytes()==before
    with pytest.raises(LegalMathError):replay.complete(request,schema,Settings())
    replay.complete({'task':'STRUCTURED_CRITICISM'},schema,Settings())
    assert len(provider.calls)==1


def test_retained_failure_stays_failed_without_a_new_remote_call(tmp_path):
    base,allowance,request,schema=retained(tmp_path,True);provider=Provider()
    replay=RetainedProvider(provider,base,allowance)
    with pytest.raises(LegalMathError) as exc:replay.complete(request,schema,Settings())
    assert exc.value.code=='E_DEPENDENCY'
    assert exc.value.details['retained_failure']['allowance_slot']==1
    assert not provider.calls


def test_changed_retained_response_is_rejected_before_replay(tmp_path):
    base,allowance,request,schema=retained(tmp_path)
    (base/'calls/call-000/response.json').write_bytes(canonical({'changed':True}))
    with pytest.raises(LegalMathError):RetainedProvider(Provider(),base,allowance)


def test_excluded_task_cannot_replay_or_dispatch_and_still_requires_intact_manifest(tmp_path):
    base,allowance,request,schema=retained(tmp_path,failed=True)
    # An unused transport failure can have the same request hash as a different
    # counted invocation. No reservation may be guessed to replay that failure.
    allowance.write_bytes(canonical({'maximum':100,'calls':[{'request_hash':digest(request)}]*2}))
    provider=Provider()
    with pytest.raises(LegalMathError):RetainedProvider(provider,base,allowance)
    replay=RetainedProvider(provider,base,allowance,exclude_tasks={'SOURCE_INVENTORY'})
    with pytest.raises(LegalMathError) as error:replay.complete(request,schema,Settings())
    assert error.value.code=='E_IDEMPOTENCY' and not provider.calls
    (base/'calls/call-000/status.json').write_bytes(canonical({'changed':True}))
    with pytest.raises(LegalMathError) as error:
        RetainedProvider(provider,base,allowance,exclude_tasks={'SOURCE_INVENTORY'})
    assert error.value.code=='E_INTEGRITY'
