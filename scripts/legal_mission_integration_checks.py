"""Local qualifications for the new candidate, separate from spent runners."""
from copy import deepcopy
from pathlib import Path
from legalmath.canonical import canonical, digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import dossier_answer as consumer
from legalmath.interpretation.assurance.integration_contract import evidence_file, read_evidence
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_gap_program import ROOT, read

def qualify(work, guard):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_source_context import preparation
    from tests.assurance.test_integration import source, settings
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.search.test_formal import AT
    from scripts.legal_integration_tools import ProductToolBackend
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from legalmath.interpretation.assurance.optional_tools import ToolSession
    from scripts.legal_mission_context_boundary import receipt
    roots=[source()]; question='Selected gift control'
    context,packet=preparation(ROOT,work/'source',roots)
    save(work/'qualification.json',context['qualification'])
    def respond(req):guard();return complete_responder(req)
    provider=FunctionProvider(respond)
    assert provider.live is False
    runner=CompleteInvestigation(ROOT,work/'product',provider,
        ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings=settings(),
        maximum_scoped_actions=12,scoped_rounds=1,
        optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)))
    dossier=runner.run(roots,question,source_context=context)
    args={'investigation_directory':runner.directory,'expected_revision':dossier['revision'],
          'questions':[{'question_id':'gift','text':question}],
          'qualification_ref':evidence_file(work/'qualification.json',ROOT)}
    dossier_ref=evidence_file(runner.directory/'revisions'/dossier['revision']/'dossier.json',ROOT)
    sink=FunctionProvider(receipt)
    consumed=consumer.propose(ROOT,dossier_ref,sink,work/'consumer',dispatch_guard=guard,**args)
    assert consumed['status']=='STRUCTURALLY_VALID_PROPOSAL',consumed
    original=read(work/'consumer/original-request.json')
    assert consumer.restore(read(work/'consumer/partition.json')['registry'])==original
    packet=original['source_packet'];candidates=original['candidates'];criticism=original['source_criticism']
    proposal=criticism['proposal']
    individual={}
    for tool in sorted(ProductToolBackend.TOOL_IDS):
        guard()
        session=ToolSession(ProductToolBackend([tool]),work/'individual'/tool)
        if tool in ('legalruleml','logical-english'):result=session.candidates(packet,candidates)
        elif tool=='bm25':
            delivered=session.augment({'task':'CHECK_LOCAL_TOOL_DELIVERY','source_packet':packet,
                                       'candidates':candidates,'question':question})
            result=delivered['external_tool_context']['checks'][-1]
        else:result=session.criticism(packet,candidates,proposal)
        delivered=session.augment({'task':'CHECK_LOCAL_TOOL_DELIVERY','source_packet':packet,
                                   'candidates':candidates,'question':question})
        assert delivered['external_tool_context']['checks']
        save(work/'individual'/tool/'delivered.json',delivered)
        individual[tool]={'status':result['status'],'selected_tools':session.identity['selected_tools'],
                         'delivered':evidence_file(work/'individual'/tool/'delivered.json',ROOT)}
    save(work/'provider-requests.json',provider.requests)
    save(work/'consumer-requests.json',sink.requests)
    save(work/'individual-tools.json',individual)
    checks=dossier['optional_tools']['checks']
    assert any(c.get('tool')=='Candidate tools' and any(r.get('tool')=='Logical English'
        for r in c.get('results',[])) for c in checks)
    assert any(set(c.get('checks',{})) >= {'pyarg','carneades','clingo'} for c in checks)
    assert any('external_tool_context' in r for r in provider.requests)
    return {'status':'OFFLINE_PRODUCT_PATH_QUALIFIED','dossier':dossier_ref,
            'consumer':consumed,'individual_tools':individual,'new_live_calls':0,
            'source_qualification_delivered':all(r.get('source_qualification')==context['qualification'] for r in provider.requests),
            'archive_reconstructs':True,'six_tool_configuration_connected':True,
            'limit':'Installed engines and actual product path on synthetic source/provider; legally empty answer is not legal benefit.'}

def capacity(work, guard):
    guard()
    previous=ROOT/'artifacts/legal-mission-control/2026-10-10/context-boundary/capacity/retained-stream-request.json'
    original=read(previous)
    # The retained original is the exact historical stream already screened;
    # evaluate only the new candidate, never rerun an old program action.
    expected='artifacts/legal-mission-control/2026-10-10/context-boundary/capacity/failure-context-inputs.json'
    attribution=read(ROOT/expected)
    save(work/'historical-input-binding.json',{'original':evidence_file(previous,ROOT),
          'attribution':evidence_file(ROOT/expected,ROOT),
          'limit':'Historical inputs and question, separate from full target.'})
    prepared=consumer.partition(original)
    save(work/'partition.json',prepared)
    assert consumer.restore(prepared['registry'])==original
    result={'status':'PACKING_QUALIFIED','groups':len(prepared['batches']),
        'occurrences':len(prepared['registry']['records']),'shared_contents':len(prepared['registry']['contents']),
        'maximum_review_bytes':max(prepared['wire_bytes']), 'new_live_calls':0,
        'original_reconstructed':True,'full_target_dossier_feasibility':False}
    try:
        budget=consumer.capacity_budget(original,prepared)
        save(work/'aggregate-budget.json',budget);result.update(status='HISTORICAL_AGGREGATE_QUALIFIED',budget=budget)
    except LegalMathError as exc:
        result.update(status='AGGREGATE_UNDER_CAPACITY',error=exc.code,details=exc.details)
    source_dir=ROOT/'artifacts/legal-mission-control/2026-10-09/answer-preparation/source'
    packet=read(source_dir/'packet.json');qualification=read(source_dir/'qualification.json')
    for ref in qualification['evidence']:read_evidence(ref,ROOT,json_value=False)
    result['full_prepared_source']={'packet':evidence_file(source_dir/'packet.json',ROOT),
        'qualification':evidence_file(source_dir/'qualification.json',ROOT),
        'units':len(packet['units']),'source_only_bytes':len(canonical(read(source_dir/'source-capacity-wire.json'))),
        'scope':'Source identity only. Historical partition is not a full-target generated dossier.'}
    return result
