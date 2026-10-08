"""Regressions from the retained incomplete product executions."""
from copy import deepcopy
from pathlib import Path
import tempfile

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import scoped_investigation as scoped
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.optional_tools import ToolSession
from legalmath.interpretation.assurance.semantics import fidelity_request, validate_fidelity, representation
from legalmath.interpretation.assurance.workflow import CachedEvidenceProvider
from legalmath.interpretation.search.models import Settings
from tests.search.support import FunctionProvider
from .test_round16 import scoped_fixture, JDK, AT
from .test_integration import source, settings
from .test_successor_workflow import complete_responder


def unassessed(value):
    value=deepcopy(value)
    for row in value['checks']:
        for key in ('source_support','question_relation','executable_correspondence','authority'):
            row[key]['status']='UNASSESSED'
        row['source_support']['evidence']=[]
        row['question_relation']['evidence']=[]
        row['executable_correspondence']['representation_quotes']=[]
    return value


def test_declared_trigger_is_visible_but_cannot_supply_executable_evidence():
    p,claims,candidates,_,_=scoped_fixture()
    r=candidates['candidate']
    r['statement']='[TRUE_IS_SATISFIED] True means the demonstration duty is triggered, not fulfilled.'
    request=fidelity_request(p,claims,candidates)
    assert request['candidates'][0]['declared_meaning']['statement']==r['statement']
    assert r['statement'] not in representation(r)
    value={'checks':[{'claim_id':claims[0]['claim_id'],'candidate_id':'candidate',
        'label':'ENTAILED','source_evidence':claims[0]['evidence'],
        'representation_quotes':[r['statement']],'rationale':'Invalid prose anchor',
        'failing_stage':'NONE','question':None}],'additional_concerns':[]}
    with pytest.raises(LegalMathError) as error:
        validate_fidelity(value,p,claims,candidates)
    assert error.value.code=='E_REFERENCE'


@pytest.mark.parametrize('candidate_count', [0, 12])
def test_missing_candidate_and_impossible_capacity_block_question_calls(tmp_path, monkeypatch, candidate_count):
    from legalmath.interpretation.assurance.integrated import IntegratedInvestigation
    p,claims,candidates,_,_=scoped_fixture()
    location=tmp_path/'retained';location.mkdir()
    save(location/'packet.json',p)
    save(location/'candidates.json',{f'candidate.{i}':candidates['candidate'] for i in range(candidate_count)})
    save(location/'claims.json',[{**claims[0],'claim_id':f'claim.{i}'} for i in range(35)])
    monkeypatch.setattr(IntegratedInvestigation,'run',lambda *a,**k:{'interpretation':{
        'directory':str(location),'report':{'execution_complete':False}}})
    provider=FunctionProvider(lambda r: pytest.fail('Downstream provider called without prerequisites'))
    runner=CompleteInvestigation(tmp_path,tmp_path/'run',provider,JDK,AT,settings=settings(),maximum_scoped_actions=4)
    with pytest.raises(LegalMathError) as exc:
        runner.run([source()],'Original question')
    assert exc.value.details['stage']==('GENERATION' if not candidate_count else 'SCOPED_ADMISSION')
    state=loads((tmp_path/'run/current-state.json').read_bytes())
    if candidate_count:
        assert state['capacity']['required_pairs']==420 and state['capacity']['minimum_actions']==70
    else:
        assert state['failure']['new_downstream_calls']==0
    assert provider.requests==[]


def test_scoped_admission_preserves_all_420_pairs_without_calls(tmp_path):
    p,claims,candidates,questions,_=scoped_fixture()
    claims=[{**claims[0],'claim_id':f'claim.{i}'} for i in range(35)]
    candidates={f'candidate.{i}':candidates['candidate'] for i in range(12)}
    questions={cid:questions['candidate'] for cid in candidates}
    provider=FunctionProvider(lambda r: pytest.fail('Impossible full stage dispatched'))
    result=scoped.investigate(p,claims,candidates,questions,provider,tmp_path,maximum_actions=4)
    assert result['capacity']['minimum_actions']==70
    assert len(result['required_pairs'])==len(result['pending_pairs'])==420
    assert result['journal_actions']==0 and not scoped.execution_complete(result)
    assert result['pruned_pairs']==[]


@pytest.mark.parametrize('repair', [True, False])
def test_agreed_unassessed_dimensions_do_not_end_review_or_count_as_complete(tmp_path, repair):
    p,claims,candidates,questions,answer=scoped_fixture()
    provider=FunctionProvider(lambda r: answer if repair and r['investigation']['round']==2 else unassessed(answer))
    result=scoped.investigate(p,claims,candidates,questions,provider,tmp_path,maximum_rounds=2,maximum_actions=4)
    assert len(provider.requests)==4
    assert scoped.execution_complete(result) is repair
    assert result['stopped'] is None and not result['pending_pairs']


def test_full_product_and_verifier_reject_false_completion_of_unassessed_dimensions(tmp_path):
    root=Path(__file__).resolve().parents[2]
    def respond(r):
        value=complete_responder(r)
        return unassessed(value) if r['task']=='SCOPED_SOURCE_FIDELITY' else value
    with tempfile.TemporaryDirectory(prefix='unassessed-product-',dir=root/'artifacts') as path:
        runner=CompleteInvestigation(root,path,FunctionProvider(respond),JDK,AT,
            settings=settings(),maximum_scoped_actions=4,scoped_rounds=1)
        try:
            result=runner.run([source()],'Selected gift control')
        except Exception:
            import shutil
            shutil.copytree(path,tmp_path/'failed-product')
            raise
        assert result['core']['execution_complete'] and result['replay']
        assert result['scoped']['stopped'] is None and not result['scoped']['pending_pairs']
        assert not result['execution_complete'] and not verify(root,result)['execution_complete']
        result['execution_complete']=True
        with pytest.raises(LegalMathError):verify(root,result)


class Backend:
    def __init__(self):self.calls=[];self.revision=1;self.fail=False
    def identity(self):return {'fixture':True,'revision':self.revision}
    def retrieval(self,p,inputs,work):
        self.calls.append('retrieval')
        if self.fail:raise TimeoutError('controlled local tool interruption')
        return {'status':'PASS','tool':'retrieval','question':inputs['question']}
    def candidates(self,p,inputs,work):
        self.calls.append('candidates')
        return {'status':'PASS','tool':'candidates','candidate_ids':list(inputs)}


def test_durable_context_survives_unrelated_stages_restart_and_changed_source(tmp_path):
    p,_,candidates,_,_=scoped_fixture();backend=Backend()
    session=ToolSession(backend,tmp_path)
    session.candidates(p,candidates)
    request={'task':'questions','source_packet':p,'candidates':candidates}
    first=session.augment(request)
    assert {r['kind'] for r in first['external_tool_context']['checks']}=={'candidates','retrieval'}
    session.augment({'task':'fidelity','source_packet':p})
    before=list(backend.calls)
    restarted=ToolSession(backend,tmp_path)
    assert restarted.augment(request)==first and backend.calls==before
    changed=deepcopy(p);changed['units'][0]['text']+=' Changed source.'
    other=restarted.augment({'task':'questions','source_packet':changed})
    assert {r['kind'] for r in other['external_tool_context']['checks']}=={'retrieval'}
    assert other['external_tool_context']['packet_hash']!=first['external_tool_context']['packet_hash']
    backend.revision=2
    with pytest.raises(LegalMathError):restarted.augment(request)


def test_interrupted_optional_check_never_silently_retries(tmp_path):
    p,*_=scoped_fixture();backend=Backend();backend.fail=True
    session=ToolSession(backend,tmp_path);request={'task':'questions','source_packet':p}
    with pytest.raises(TimeoutError):session.augment(request)
    backend.fail=False
    with pytest.raises(LegalMathError):ToolSession(backend,tmp_path).augment(request)
    assert backend.calls==['retrieval']


def test_disconnected_model_retries_once_and_exact_success_is_reused_after_restart(tmp_path):
    count=[]
    def respond(request):
        count.append(1)
        if len(count)==1:raise LegalMathError('E_DEPENDENCY',details='stream disconnected')
        return {'status':'ready'}
    provider=FunctionProvider(respond)
    cache=CachedEvidenceProvider(provider,tmp_path,{},maximum_actions=4)
    args=({'task':'probe'},{'type':'object'},Settings())
    assert cache.complete(*args).value=={'status':'ready'}
    assert len(count)==2
    again=CachedEvidenceProvider(provider,tmp_path,{},maximum_actions=4).complete(*args)
    assert len(count)==2 and again.provenance['evidence_reused']


def test_unknown_provider_outcome_requires_explicit_recovery(tmp_path):
    def interrupted(r):raise KeyboardInterrupt('controlled process loss')
    provider=FunctionProvider(interrupted)
    cache=CachedEvidenceProvider(provider,tmp_path,{},maximum_actions=4)
    args=({'task':'probe'},{'type':'object'},Settings())
    with pytest.raises(KeyboardInterrupt):cache.complete(*args)
    before=len(provider.requests)
    with pytest.raises(LegalMathError) as error:
        CachedEvidenceProvider(provider,tmp_path,{},maximum_actions=4).complete(*args)
    assert error.value.code=='E_JOB_STATE'
    assert len(provider.requests)==before


def test_effective_graph_preserves_blocking_inheritance_and_unaccepted_priority():
    from scripts.legal_integration_tools import effective_graph
    from .test_arguments import argument,value,premise
    from .support import packet
    from legalmath.interpretation.assurance.arguments import evaluate_criticism
    a,b,c,d=argument(),argument('b','applicable.rule.a',True,'STRICT'),argument('c','child'),argument('d','other')
    c['parents']=['a'];d['premises']=[premise('ORDINARY','QUESTIONED')]
    v=value(a,b,c,d)
    v['attacks']=[{'attacker':'b','target':'a','kind':'UNDERCUT','target_component':'rule.a','rationale':'Controlled attack'}]
    v['preferences']=[{'preferred':'a','over':'b','evidence':a['evidence'],'rationale':'Unaccepted preference'}]
    graph=effective_graph(v,evaluate_criticism(v,packet(),['candidate']))
    assert graph['ids']==['a','b','c']
    assert graph['attacks']==[['b','a'],['b','c']]


def test_live_accounting_matches_augmented_provider_hashes(tmp_path):
    from .test_successor_grants import grant
    from legalmath.interpretation.search.providers import CodexProvider,Completion
    p,claims,candidates,questions,answer=scoped_fixture()
    allowance,_=grant(tmp_path,4)
    class Augmenting(CodexProvider):
        provider_id='controlled.augmented';routing={'fixture':True}
        def __init__(self):self.allowance=allowance
        def complete(self,request,schema,settings):
            augmented={**request,'external_context':{'controlled':True}}
            actual=digest(augmented)
            slot=self.allowance.reserve(actual)
            return Completion(deepcopy(answer),{'request_hash':actual,'allowance_slot':slot})
    # Earlier stages may have issued exactly the same request hashes. Those
    # reservations must not inflate the count for a later diagnostic.
    from legalmath.interpretation.assurance.fidelity_v2 import request as scoped_request
    from legalmath.interpretation.assurance.decomposition import compact_request
    base=scoped_request(p,claims,candidates,questions)
    for role in scoped.PERSPECTIVES:
        r=deepcopy(base)
        r['investigation']={'batch':0,'round':1,'perspective':role,'prior_round_evidence':None,
            'instruction':'Investigate source support and question relation separately. Retain conflicting explanations; do not force agreement or a known answer. Use prior diagnostics to repair response shape without manufacturing support.'}
        allowance.reserve(digest({**compact_request(r,profile='v2'),'external_context':{'controlled':True}}))
    result=scoped.investigate(p,claims,candidates,questions,Augmenting(),tmp_path/'scoped',
                             maximum_rounds=1,maximum_actions=2)
    assert result['live_calls']==result['new_live_calls']==2 and allowance.verify()['used']==4


def test_complete_coverage_cannot_shrink_the_required_matrix(tmp_path):
    p,claims,candidates,questions,answer=scoped_fixture()
    result=scoped.investigate(p,claims,candidates,questions,FunctionProvider(lambda r:answer),tmp_path,
                             maximum_rounds=1,maximum_actions=2)
    assert scoped.execution_complete(result)
    assert not scoped.execution_complete(result,expected_pairs=[(claims[0]['claim_id'],'candidate'),('missing.claim','candidate')])


def test_scoped_tools_use_typed_questions_and_exclude_old_broad_retrieval(tmp_path):
    from legalmath.interpretation.assurance.fidelity_v2 import request as scoped_request
    from legalmath.interpretation.assurance import source_references,readable_tables
    from legalmath.interpretation.assurance.fidelity_v2 import FidelityV2
    p,claims,candidates,questions,_=scoped_fixture();backend=Backend();session=ToolSession(backend,tmp_path)
    broad=session.augment({'task':'inventory','source_packet':p})
    request=scoped_request(p,claims,candidates,questions)
    exact=session.augment(request)
    context=exact['external_tool_context']
    assert context['retrieval_targets']==[{'candidate_id':'candidate','question_hash':digest(questions['candidate']),
                                         'question':questions['candidate']['question']}]
    retrieval=[r for r in context['checks'] if r['kind']=='retrieval']
    assert len(retrieval)==1 and retrieval[0]['question']==questions['candidate']['question']
    assert retrieval[0]['question']!=broad['external_tool_context']['checks'][0]['question']
    assert exact['source_packet']==p and exact['required_pairs']==request['required_pairs']
    wire,_,_=source_references.prepare(exact,FidelityV2.model_json_schema())
    assert readable_tables.decode(readable_tables.encode(wire),expected_request_hash=digest(wire))==wire
    bad=deepcopy(request);bad['candidates'][0]['question_hash']='0'*64
    with pytest.raises(LegalMathError):session.augment(bad)


def test_status_reads_while_execution_lock_is_held():
    import fcntl,subprocess,json
    from scripts.legal_integration_repair import OUT,ROOT
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        process=subprocess.run([str(ROOT/'.venv/bin/python'),'scripts/run_legal_integration_repair.py','status'],
                               cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert process.returncode==0,process.stderr
    assert 'budgets' in json.loads(process.stdout)
