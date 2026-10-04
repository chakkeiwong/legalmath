"""Response contracts stay explicit, and resumptions preserve spent attempts."""
from pathlib import Path
import sys
import pytest
from pydantic import Field
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.contracts import Strict,parse
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.assurance.workflow import EvidenceJournal

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_live import checked_call


class Response(Strict):
    judgments:list[str]=Field(min_length=1)


class Provider:
    routing={'synthetic_fixture':True}
    def __init__(self):self.calls=[]
    def complete(self,request,schema,settings):
        self.calls.append(request)
        assert request['response_schema']==schema
        assert 'response_schema' in request['response_contract']
        return Completion({'judgments':['Controlled format result']},{'synthetic_fixture':True})


def seed(directory,request,provider,values):
    journal=EvidenceJournal(directory,{'request':digest(request),'schema':digest(Response.model_json_schema()),
        'route':provider.routing,'rendered_image':None},maximum_actions=3,maximum_per_issue=3,deadline_seconds=3600)
    for i,value in enumerate(values):
        journal.execute('judgment',{'request':request,'attempt':i},lambda w,v=value:v,issue='fixture')
    return journal


def test_explicit_schema_is_in_the_actual_prompt_and_reused_after_validation(tmp_path):
    p=Provider();request={'task':'CONTROLLED_FORMAT_FIXTURE'}
    first=checked_call(p,request,Response,lambda v:parse(Response,v),tmp_path,'fixture')
    second=checked_call(p,request,Response,lambda v:parse(Response,v),tmp_path,'fixture')
    assert len(p.calls)==1 and first['value']==second['value']
    assert second['reuse_receipt']['new_model_call'] is False


def test_legacy_valid_judgment_is_revalidated_without_redispatch(tmp_path):
    p=Provider();request={'task':'CONTROLLED_FORMAT_FIXTURE'}
    seed(tmp_path,request,p,[{'status':'VALIDATED_PROPOSAL','value':{'judgments':['Prior result']},'provenance':{'synthetic_fixture':True}}])
    value=checked_call(p,request,Response,lambda v:parse(Response,v),tmp_path,'fixture')
    assert not p.calls and value['value']['judgments']==['Prior result']


def test_old_format_failures_consume_the_original_three_attempt_ceiling(tmp_path):
    p=Provider();request={'task':'CONTROLLED_FORMAT_FIXTURE'}
    failed={'status':'REJECTED_RESPONSE','error':'E_SCHEMA','details':'Missing fixture field'}
    journal=seed(tmp_path,request,p,[failed,failed,failed]);before=journal.path.read_bytes()
    result=checked_call(p,request,Response,lambda v:parse(Response,v),tmp_path,'fixture')
    assert result['status']=='UNRESOLVED_AFTER_REPAIR_LIMIT' and not p.calls
    assert journal.path.read_bytes()==before


def test_a_repair_uses_only_the_remaining_attempt_and_includes_diagnostics(tmp_path):
    p=Provider();request={'task':'CONTROLLED_FORMAT_FIXTURE'}
    failed={'status':'REJECTED_RESPONSE','error':'E_SCHEMA','details':'Missing fixture field'}
    journal=seed(tmp_path,request,p,[failed,failed])
    result=checked_call(p,request,Response,lambda v:parse(Response,v),tmp_path,'fixture')
    assert result['status']=='VALIDATED_PROPOSAL' and len(p.calls)==1
    assert len(p.calls[0]['prior_response_diagnostics'])==2
    assert journal.report()['consumed_actions']==3


def test_stronger_validation_repairs_without_erasing_a_prior_accepted_action(tmp_path):
    p=Provider();request={'task':'CONTROLLED_FORMAT_FIXTURE'}
    prior={'status':'VALIDATED_PROPOSAL','value':{'judgments':['Wrong source identity']},'provenance':{}}
    journal=seed(tmp_path,request,p,[prior]);first=journal.report()['actions'][0]
    started=journal.report()['started_ms'];result_bytes=(tmp_path/first['result_file']).read_bytes()
    def validate(v):
        if v['judgments']==['Wrong source identity']:raise LegalMathError('E_STALE_REVIEW',details='Controlled source mismatch')
        return parse(Response,v)
    with pytest.raises(LegalMathError):checked_call(p,request,Response,validate,tmp_path,'fixture')
    result=checked_call(p,request,Response,validate,tmp_path,'fixture',repair_revalidated_response=True)
    assert result['status']=='VALIDATED_PROPOSAL' and len(p.calls)==1
    assert p.calls[0]['prior_response_diagnostics'][0]['original_record_preserved']
    assert journal.report()['actions'][0]==first and journal.report()['started_ms']==started
    assert (tmp_path/first['result_file']).read_bytes()==result_bytes
    assert journal.report()['consumed_actions']==2
