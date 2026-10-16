"""Local scripted full-product qualification, explicitly no legal-answer evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from legalmath.canonical import digest, loads
from legalmath.interpretation.assurance import evidence_tables, source_references, source_context, dossier_answer
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.optional_tools import adapter_results
from legalmath.interpretation.assurance.route_admission import RouteBudgetProvider,workload
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from legalmath.interpretation.search.providers import Completion
from scripts.legal_integration_tools import ProductToolBackend

ROOT=Path(__file__).resolve().parents[1]


class LocalResponder:
    provider_id='test.local-route-evidence'; live=False

    def __init__(self):self.requests=[];self.wire_requests=[]

    def complete(self, wire, schema, settings):
        from tests.assurance.test_successor_workflow import complete_responder
        self.wire_requests.append(deepcopy(wire))
        # Test responder only: authenticity was independently checked by the
        # production encoder before this scripted provider received the wire.
        request=(evidence_tables.decode(wire,expected_request_hash=wire['request_hash'],
            expected_packet_hash=digest(wire['source_packet'])) if wire.get('evidence_profile')==evidence_tables.PROFILE else wire)
        self.requests.append(deepcopy(request))
        task=request['task'];packet=request['source_packet']
        units=[u['unit_id'] for u in packet['units']]
        if task in ('REVIEW_DOSSIER_EVIDENCE','REVIEW_DOSSIER_INTERACTIONS','SYNTHESIZE_WHOLE_DOSSIER_ANSWER'):
            from scripts.legal_mission_context_boundary import receipt
            value=receipt(request)
            if task=='SYNTHESIZE_WHOLE_DOSSIER_ANSWER':
                for row in value['tool_account']:
                    row['adapter_accounts']=[{'tool_id':a['tool_id'],'result_hash':a['result_hash'],
                        'disposition':'UNRESOLVED','question_ids':row['question_ids'],
                        'effect_on_answer':'Not evaluated: scripted response only.',
                        'limitation':'No substantive model consideration.'}
                        for a in request['tool_adapter_bindings'][row['key']]]
        elif task=='REVIEW_SOURCE_CLAIMS':
            value={'request_binding':request['request_binding'],'checked_unit_ids':units,
                'claims':[{'claim_id':c['claim_id'],'claim_hash':digest(c),'assessment':'RETAINED',
                    'source_reading':c['statement'],'support':c['evidence'],'contrary':[],
                    'qualifications':[],'missing_authorities':[],'nonlocal_claim_ids':[]}
                    for c in request['claims']], 'unresolved_questions':[]}
        elif task=='REVIEW_SOURCE_OMISSIONS':
            value={'checked_unit_ids':units,'issues':[],'unresolved_questions':[]}
        elif task=='REVIEW_SOURCE_INTERACTIONS':
            value={'request_binding':request['request_binding'],'checked_unit_ids':units,
                'checked_claim_ids':[c['claim_id'] for c in request['claims']],
                'checked_edges':[{'claim_id':a,'related_claim_id':b} for a,b in request['required_edges']],
                'issues':[],'unresolved_questions':[]}
        else:value=complete_responder(request)
        if 'source_references' in request:
            references=request['source_references'];by_unit={u['unit_id']:u['text'] for u in packet['units']}
            def convert(node):
                if isinstance(node,dict):
                    if set(node)=={'unit_id','quote'}:
                        assert node['quote']==by_unit[node['unit_id']], 'Fixture must select exact full-unit span'
                        span=next(s for s in references['spans'] if s['unit_id']==node['unit_id']
                            and s['start_codepoint']==0 and s['end_codepoint']==len(node['quote']))
                        return {'span_ids':[span['span_id']]}
                    return {k:convert(v) for k,v in node.items()}
                if isinstance(node,list):return [convert(v) for v in node]
                return node
            value=convert(value)
        return Completion(value,{'provider':self.provider_id,'synthetic':True,'new_live_invocation':False})


def qualify(work):
    from tests.assurance.test_integration import settings,source
    from tests.search.test_formal import AT
    work=Path(work);work.mkdir(parents=True,exist_ok=False)
    roots=[source()];question='Selected gift control'
    packet=packet_from_context(acquire_context(roots,max_depth=0),question)
    save(work/'packet.json',packet)
    qualification={'profile':'investigation-answer-source-qualification.v1','source_packet_hash':digest(packet),
        'limitations':['Scripted engineering fixture; no legal accuracy or full-target capacity established.'],
        'evidence':[evidence_file(work/'packet.json',ROOT)],'details':{'source_status':'Synthetic source'}}
    save(work/'qualification.json',qualification)
    context=source_context.prepare(ROOT,roots,packet,qualification)
    result={}
    for arm in ('baseline','candidate'):
        out=work/arm;provider=LocalResponder()
        declared=workload(pieces=1,reader_claims=[1,1],selected_claims=1,all_claims=1,
            candidates=1,formalized_candidates=1,source_batch=1,search_calls=3,abstraction_calls=0,
            dossier_groups=64,tool_enabled=arm=='candidate')
        budget=RouteBudgetProvider(provider,out/'route-budget',declared,declared['stages'],
            (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat())
        config=settings().model_copy(update={'total_model_calls':30,'inventory_piece_characters':20000,
            'incremental_fidelity_admission':True,
            'staged_source_review':True,'source_review_batch_size':1,
            'search':settings().search.model_copy(update={'max_input_bytes':200000,'max_output_bytes':200000,
                'max_logical_input_bytes':evidence_tables.MAXIMUM,'max_expanded_output_bytes':evidence_tables.MAXIMUM})})
        runner=CompleteInvestigation(ROOT,out/'product',budget,ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
            settings=config,maximum_scoped_actions=12,scoped_rounds=1,
            reference_protocol=source_references.PROTOCOL,input_profile=evidence_tables.PROFILE,
            optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)) if arm=='candidate' else None)
        dossier=runner.run(roots,question,source_context=context)
        assert dossier['execution_complete'],dossier['core']['interpretation']['report']
        ref=evidence_file(runner.directory/'revisions'/dossier['revision']/'dossier.json',ROOT)
        args={'investigation_directory':runner.directory,'expected_revision':dossier['revision'],
            'questions':[{'question_id':'gift','text':question}], 'qualification_ref':evidence_file(work/'qualification.json',ROOT)}
        investigation_calls=len(provider.requests)
        consumed=dossier_answer.propose(ROOT,ref,budget,out/'answer',**args)
        assert consumed['status']=='STRUCTURALLY_VALID_PROPOSAL',consumed
        save(out/'decoded-provider-requests.json',provider.requests)
        save(out/'encoded-provider-requests.json',provider.wire_requests)
        save(out/'answer-provider-requests.json',provider.requests[investigation_calls:])
        tasks=sorted({r['task'] for r in provider.requests})
        assert {'REVIEW_SOURCE_CLAIMS','REVIEW_SOURCE_OMISSIONS','GENERATE','SOURCE_FIDELITY','SCOPED_SOURCE_FIDELITY'}<=set(tasks)
        assert all(r.get('reviewed_source_evidence',{}).get('records') for r in provider.requests if r['task']=='GENERATE')
        assert all(r['source_qualification']==qualification for r in provider.requests)
        tool_ids=sorted({a['tool_id'] for check in dossier.get('optional_tools',{}).get('checks',[]) for a in adapter_results(check)})
        if arm=='candidate':assert tool_ids==sorted(ProductToolBackend.TOOL_IDS)
        result[arm]={'dossier':ref,'answer':consumed,'tasks':tasks,'tool_ids':tool_ids,
            'source_qualification_delivered':True,'provider_calls':investigation_calls,
            'answer_calls':len(provider.requests)-investigation_calls,'live_calls':0,
            'route_budget':evidence_file(budget.path,ROOT)}
    result.update(status='SCRIPTED_BOTH_ARMS_COMPLETE',fixture='synthetic gift rule',
        legal_quality_evaluated=False,full_target_capacity_qualified=False,tool_benefit_evaluated=False)
    save(work/'result.json',result)
    return result
