from copy import deepcopy
from pathlib import Path
import sys
import pytest
from legalmath.canonical import digest,canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.models import Generation
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.assurance.workflow import EvidenceJournal

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_study import proposal_history,single_call


class Provider:
    routing={'synthetic':True}
    def __init__(self):self.calls=[]
    def complete(self,request,schema,settings):
        self.calls.append(request)
        return Completion({'controlled':'answer'},{'synthetic':True})


def request(history):return {'task':'SINGLE_READER_INTERPRETATION','source_packet':{'units':[]},
    'question':'Controlled question','round':2,'previous_own_proposals':history}


def seed(directory,provider,original,result=None):
    journal=EvidenceJournal(directory,{'request':digest(original),'schema':digest(Generation.model_json_schema()),
        'route':provider.routing,'rendered_image':None},maximum_actions=3,maximum_per_issue=3,deadline_seconds=3600)
    wire={**original,'response_schema':Generation.model_json_schema(),'response_contract':'Controlled wire'}
    def callback(work):
        if result is None:raise LegalMathError('E_RESOURCE_LIMIT',details='Input byte cap')
        return result
    try:journal.execute('judgment',{'request':wire,'attempt':0},callback,issue='single.2')
    except LegalMathError:pass
    return journal


def test_transport_provenance_does_not_expand_model_history():
    answers=[]
    for i in range(4):
        answers.append({'status':'VALIDATED_PROPOSAL','value':{'text':'substantive '+str(i)},
                        'provenance':{'compact_request':{'previous':deepcopy(answers),'schema':'x'*10000}}})
    projected=proposal_history(answers)
    assert [r['value'] for r in projected]==[r['value'] for r in answers]
    assert len(canonical(projected))<1000 and len(canonical(answers))>100000


def test_accepted_old_request_reuses_exact_substance_without_another_call(tmp_path):
    p=Provider();history=[{'status':'VALIDATED_PROPOSAL','value':{'reading':'earlier'},'provenance':{'large':'local'}}]
    result={'status':'VALIDATED_PROPOSAL','value':{'controlled':'prior'},'provenance':{'synthetic':True}}
    journal=seed(tmp_path,p,request(history),result);before=journal.path.read_bytes()
    response=single_call(p,request(proposal_history(history)),lambda v:v,tmp_path,'single.2')
    assert not p.calls and response['value']==result['value']
    assert response['reuse_receipt']['new_model_call'] is False and journal.path.read_bytes()==before
    changed=request(proposal_history(history));changed['question']='Different question'
    with pytest.raises(LegalMathError):single_call(p,changed,lambda v:v,tmp_path,'single.2')


def test_failed_history_migration_keeps_spent_action_and_deadline(tmp_path):
    p=Provider();history=[{'status':'VALIDATED_PROPOSAL','value':{'reading':'earlier'},'provenance':{'large':'local'}}]
    directory=tmp_path/'round-2';journal=seed(directory,p,request(history));before=journal.path.read_bytes()
    req=request(proposal_history(history));response=single_call(p,req,lambda v:v,directory,'single.2')
    assert response['status']=='VALIDATED_PROPOSAL' and len(p.calls)==1
    target=tmp_path/'round-2-content-history'
    from assurance_successor_audit import journal_receipt
    _,state=journal_receipt(target/'journal.json')
    assert state['started_ms']==journal.report()['started_ms']
    assert len(state['actions'])==2 and state['actions'][0]==journal.report()['actions'][0]
    single_call(p,req,lambda v:v,directory,'single.2')
    assert len(p.calls)==1 and journal.path.read_bytes()==before
