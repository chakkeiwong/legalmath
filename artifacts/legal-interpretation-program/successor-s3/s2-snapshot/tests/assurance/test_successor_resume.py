from pathlib import Path
import sys
import pytest
from legalmath.canonical import digest,canonical,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import CodexProvider,Completion
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from .test_successor_grants import grant

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from assurance_successor_resume import ResumingCodex
from run_assurance_successor import save,read


def test_prior_revision_reuse_and_inventory_ceiling_do_not_refund(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance)
    directory=tmp_path/'ensemble';journal=EvidenceJournal(directory/'revisions/old/core/model-evidence',
        {'route':base.routing},maximum_actions=36,deadline_seconds=86400)
    request={'task':'SOURCE_INVENTORY','role':'qualification-reader','source_packet':{'units':[]}}
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    def action(req,value):
        def dispatch(work):
            slot=allowance.reserve(digest(req))
            return {'value':value,'provenance':{'allowance_slot':slot,'request_hash':digest(req)}}
        journal.execute('model',{'request':req,'schema':schema},dispatch)
    action(request,{'incomplete':1});repair={**request,'task':'REPAIR_OUTPUT','original_task':'SOURCE_INVENTORY','attempt':1}
    action(repair,{'incomplete':2});before=journal.path.read_bytes()
    calls=[]
    def real(self,req,schema,settings):
        calls.append(req);slot=self.allowance.reserve(digest(req));return Completion({'complete':True},{'allowance_slot':slot})
    monkeypatch.setattr(CodexProvider,'complete',real)
    resumed=ResumingCodex(allowance=allowance,prior_directory=directory)
    result=resumed.complete(request,schema,Settings())
    assert result.value=={'incomplete':1} and result.provenance['new_live_invocation'] is False
    assert not calls and allowance.verify()['used']==2
    resumed.complete({**repair,'attempt':2},schema,Settings())
    with pytest.raises(LegalMathError):resumed.complete({**repair,'attempt':3},schema,Settings())
    assert allowance.verify()['used']==3 and len(calls)==1 and journal.path.read_bytes()==before
    # A changed source has its own question, and cannot reuse the old answer.
    changed={**request,'source_packet':{'units':['changed source']}}
    resumed.complete(changed,schema,Settings());assert len(calls)==2


def test_failed_prior_dispatch_also_consumes_inventory_attempt(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance);directory=tmp_path/'ensemble'
    journal=EvidenceJournal(directory/'revisions/old/core/model-evidence',{'route':base.routing},maximum_actions=36)
    req={'task':'SOURCE_INVENTORY','role':'qualification-reader','source_packet':{}}
    for i in range(3):
        def fail(work):raise LegalMathError('E_RESOURCE_LIMIT',details='Controlled timeout')
        with pytest.raises(LegalMathError):journal.execute('model',{'request':req,'schema':{},'attempt':i},fail)
    resumed=ResumingCodex(allowance=allowance,prior_directory=directory)
    monkeypatch.setattr(CodexProvider,'complete',lambda *a:pytest.fail('Exhausted inventory must not dispatch'))
    with pytest.raises(LegalMathError):resumed.complete(req,{},Settings())


def transport(allowance,request,schema):
    slot=allowance.reserve(digest(request));directory=allowance.path.parent/'provider-evidence'/f'{slot:04}-{digest(request)[:16]}'
    directory.mkdir(parents=True);files={}
    for name,value in [('request.json',request),('schema.json',schema)]:
        raw=canonical(value);(directory/name).write_bytes(raw);files[name]={'retained_sha256':raw_digest(raw)}
    save(directory/'manifest.json',{'allowance_slot':slot,'request_hash':digest(request),'files':files,
        'complete_output_present':False})
    return slot


def test_inventory_split_carries_original_unit_attempts_and_does_not_block_other_units(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,10)
    req={'task':'SOURCE_INVENTORY','role':'atomic-reader','source_packet':{'source_key':'same',
        'selected_slice':'same question','units':[{'unit_id':'a','text':'A'},{'unit_id':'b','text':'B'}]}}
    for _ in range(2):transport(allowance,req,{})
    resumed=ResumingCodex(allowance=allowance,prior_directory=tmp_path/'absent');calls=[]
    def real(self,request,schema,settings):calls.append(request);return Completion({}, {})
    monkeypatch.setattr(CodexProvider,'complete',real)
    smaller={**req,'source_packet':{**req['source_packet'],'units':req['source_packet']['units'][:1]}}
    resumed.complete(smaller,{},Settings())
    with pytest.raises(LegalMathError) as exc:resumed.complete({**smaller,'piece':{'index':9}}, {},Settings())
    assert exc.value.code=='E_RESOURCE_LIMIT' and len(calls)==1
    other={**req,'source_packet':{**req['source_packet'],'units':req['source_packet']['units'][1:]}}
    resumed.complete(other,{},Settings());assert len(calls)==2


def test_inventory_split_preserves_earliest_deadline(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,10)
    req={'task':'SOURCE_INVENTORY','role':'atomic-reader','source_packet':{'units':[{'unit_id':'a','text':'A'}]}}
    transport(allowance,req,{})
    resumed=ResumingCodex(allowance=allowance,prior_directory=tmp_path/'absent')
    import assurance_successor_resume as module
    monkeypatch.setattr(module.time,'time',lambda:max(resumed.inventory_unit_started.values())+86401)
    monkeypatch.setattr(CodexProvider,'complete',lambda *args:pytest.fail('Expired source question must not dispatch'))
    with pytest.raises(LegalMathError):resumed.complete({**req,'piece':{'index':2}},{},Settings())


def test_legacy_fidelity_repartition_cannot_refund_failed_pairs(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,10)
    req={'task':'SOURCE_FIDELITY','source_packet':{},'claims':[{'claim_id':'a'},{'claim_id':'b'}],
        'candidates':[{'candidate_id':'r','representation':'unchanged rule'}],
        'required_pairs':[{'claim_id':'a','candidate_id':'r'},{'claim_id':'b','candidate_id':'r'}]}
    for _ in range(4):transport(allowance,req,{})
    resumed=ResumingCodex(allowance=allowance,prior_directory=tmp_path/'absent')
    smaller={**req,'claims':req['claims'][:1],'required_pairs':req['required_pairs'][:1]}
    monkeypatch.setattr(CodexProvider,'complete',lambda *a:pytest.fail('Spent pair must not dispatch'))
    with pytest.raises(LegalMathError):resumed.complete(smaller,{},Settings())


def test_exact_outer_question_is_reused_but_changed_question_is_not(tmp_path,monkeypatch):
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance);directory=tmp_path/'ensemble'
    journal=EvidenceJournal(directory/'revisions/old/actions',{},maximum_actions=32)
    req={'task':'DEFINE_EXACT_QUESTIONS','source_packet':{'question':'Original question'}}
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    slot=transport(allowance,req,schema)
    response={'value':{'original':'proposal'},'provenance':{'allowance_slot':slot,
        'request_hash':digest(req),'provider_route_hash':digest(base.routing)}}
    def propose(work):
        save(work/'raw.json',response);return {'status':'VALIDATED','value':response['value']}
    journal.execute('question-proposal',{'request':req},propose)
    calls=[]
    def real(self,request,schema,settings):calls.append(request);return Completion({}, {})
    monkeypatch.setattr(CodexProvider,'complete',real)
    resumed=ResumingCodex(allowance=allowance,prior_directory=directory)
    got=resumed.complete(req,schema,Settings())
    assert got.value==response['value'] and got.provenance['new_live_invocation'] is False and not calls
    resumed.complete({**req,'source_packet':{'question':'Changed question'}},schema,Settings())
    assert len(calls)==1


@pytest.mark.parametrize('reason',['attempts','deadline'])
def test_scoped_repartition_carries_timeouts_and_earliest_deadline(tmp_path,monkeypatch,reason):
    allowance,_=grant(tmp_path,10)
    req={'task':'SCOPED_SOURCE_FIDELITY','source_packet':{},'claims':[{'claim_id':'a'},{'claim_id':'b'}],
        'candidates':[{'candidate_id':'r','question_hash':'x','representation':'same original program'}],
        'required_pairs':[{'claim_id':'a','candidate_id':'r'},{'claim_id':'b','candidate_id':'r'}],
        'investigation':{'perspective':'source-first','batch':0,'round':1}}
    for _ in range(6 if reason=='attempts' else 1):transport(allowance,req,{})
    resumed=ResumingCodex(allowance=allowance,prior_directory=tmp_path/'absent')
    if reason=='deadline':
        import assurance_successor_resume as module
        monkeypatch.setattr(module.time,'time',lambda:max(resumed.scoped_started.values())+86401)
    smaller={**req,'claims':req['claims'][:1],'required_pairs':req['required_pairs'][:1],
        'investigation':{**req['investigation'],'batch':1}}
    monkeypatch.setattr(CodexProvider,'complete',lambda *args:pytest.fail('Spent bound cannot be replenished by partitioning'))
    with pytest.raises(LegalMathError) as caught:resumed.complete(smaller,{},Settings())
    assert caught.value.code=='E_RESOURCE_LIMIT'


@pytest.mark.parametrize('explicit_journal',[False,True])
def test_completed_scoped_response_reuses_its_original_reservation(tmp_path,monkeypatch,explicit_journal):
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance);directory=tmp_path/'ensemble'
    journal=EvidenceJournal(tmp_path/'continuation/scoped/model' if explicit_journal else directory/'revisions/old/scoped/model',
                            {'route':base.routing},maximum_actions=128)
    req={'task':'SCOPED_SOURCE_FIDELITY','source_packet':{},'claims':[{'claim_id':'a'}],
        'candidates':[{'candidate_id':'r','question_hash':'x','representation':'original'}],
        'required_pairs':[{'claim_id':'a','candidate_id':'r'}],
        'investigation':{'perspective':'source-first','batch':0,'round':1}}
    schema={'type':'object','properties':{},'required':[],'additionalProperties':False}
    slot=transport(allowance,req,schema)
    response={'value':{'controlled':'response'},'provenance':{'allowance_slot':slot,'provider_route_hash':digest(base.routing)}}
    def dispatch(work):
        save(work/'wire-request.json',req);save(work/'raw-response.json',response)
        return {'status':'VALIDATED_PROPOSAL',**response}
    journal.execute('scoped-fidelity',{'request':req,'schema':schema},dispatch)
    before=journal.path.read_bytes();resumed=ResumingCodex(allowance=allowance,prior_directory=directory,
        additional_scoped_journals=[journal.path] if explicit_journal else [])
    calls=[]
    monkeypatch.setattr(CodexProvider,'complete',lambda *args:(calls.append(args),Completion({},{}))[1])
    r=resumed.complete(req,schema,Settings())
    assert r.value==response['value'] and not calls and r.provenance['new_live_invocation'] is False
    assert list(resumed.scoped_spent.values())==[1] and journal.path.read_bytes()==before
    changed={**req,'candidates':[{**req['candidates'][0],'question_hash':'changed'}]}
    resumed.complete(changed,schema,Settings());assert len(calls)==1


def test_interrupted_scoped_request_needs_stopped_worker_receipt_and_remains_spent(tmp_path):
    from legalmath.interpretation.assurance.diversity import identity,save as saved_journal
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance);directory=tmp_path/'ensemble'
    journal=EvidenceJournal(directory/'revisions/old/scoped/model',{'route':base.routing},maximum_actions=128)
    req={'task':'SCOPED_SOURCE_FIDELITY','source_packet':{},'claims':[{'claim_id':'a'}],
        'candidates':[{'candidate_id':'r','question_hash':'x','representation':'original'}],
        'required_pairs':[{'claim_id':'a','candidate_id':'r'}],
        'investigation':{'perspective':'source-first','batch':0,'round':1}}
    allowance.reserve(digest(req))  # Interrupted before transport receipt creation.
    def interrupt(work):
        save(work/'wire-request.json',req);raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):journal.execute('scoped-fidelity',{'request':req,'schema':{}},interrupt)
    state=read(journal.path)['value'];state['actions'][0]['status']='RESERVED'
    saved_journal(journal.path,{'value':state,'sha256':identity(state)})
    with pytest.raises(LegalMathError):ResumingCodex(allowance=allowance,prior_directory=directory)
    phase=tmp_path/'stopped.json';save(phase,{'status':'FAILED'})
    save(journal.directory/'verified-interruption.json',{'journal_sha256':__import__('run_assurance_successor').sha(journal.path),
        'failed_phase_manifest':str(phase),'failed_phase_sha256':__import__('run_assurance_successor').sha(phase)})
    resumed=ResumingCodex(allowance=allowance,prior_directory=directory)
    assert list(resumed.scoped_spent.values())==[1] and not resumed.records


def test_interrupted_core_fidelity_carries_reservation_without_transport_manifest(tmp_path):
    from legalmath.interpretation.assurance.diversity import identity,save as saved_journal
    allowance,_=grant(tmp_path,8);base=CodexProvider(allowance=allowance);directory=tmp_path/'ensemble'
    journal=EvidenceJournal(directory/'revisions/old/core/model-evidence',{'route':base.routing},maximum_actions=36)
    req={'task':'SOURCE_FIDELITY','source_packet':{},'claims':[{'claim_id':'a'}],
        'candidates':[{'candidate_id':'r','representation':'original'}],
        'required_pairs':[{'claim_id':'a','candidate_id':'r'}]}
    allowance.reserve(digest(req))
    def interrupt(work):raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):journal.execute('model',{'request':req,'schema':{}},interrupt)
    state=read(journal.path)['value'];state['actions'][0]['status']='RESERVED'
    saved_journal(journal.path,{'value':state,'sha256':identity(state)})
    with pytest.raises(LegalMathError):ResumingCodex(allowance=allowance,prior_directory=directory)
    phase=tmp_path/'stopped.json';save(phase,{'status':'FAILED'})
    module=__import__('run_assurance_successor')
    save(journal.directory/'verified-interruption.json',{'journal_sha256':module.sha(journal.path),
        'failed_phase_manifest':str(phase),'failed_phase_sha256':module.sha(phase)})
    resumed=ResumingCodex(allowance=allowance,prior_directory=directory)
    assert list(resumed.fidelity_spent.values())==[1] and not resumed.records
