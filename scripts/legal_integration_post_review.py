"""One reviewed correction of existing nodes, with restartable registration."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from contextlib import ExitStack
import fcntl
import hashlib
import math

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, TOOLS, TOKENIZER, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = BASE / 'substantive-continuation/post-review'
REVIEW = WORK / 'review.md'
REPAIRED = ('account-p10','account-p14','account-evidence','account-gatecoin',
            'graph-p14','graph-gatecoin','current-binding','continuation-review')


def finish_transaction(root, journal):
    """Caller holds mission then state locks. Refuse a third-party mutation."""
    value = read(root / journal)
    for row in value['writes']:
        verify(root, row['replacement'])
        current = ref(root, row['path'])
        require(current['sha256'] in (row['before']['sha256'], row['replacement']['sha256']),
                'Concurrent edit prevents transaction recovery: ' + row['path'])
    for row in value['writes']:
        path = root / row['path']
        temporary = path.with_name(path.name + '.transaction-writing')
        temporary.write_bytes((root / row['replacement']['path']).read_bytes())
        temporary.replace(path)
    value['status'] = 'COMMITTED'
    save(root / journal, value)


def register():
    journal = WORK / 'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            return {'registered':True, 'resumed':True}
        baseline = read(ROOT/WORK/'baseline.json')
        refs = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        archives = {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        for item in refs.values(): verify(ROOT,item)
        old = read(ROOT/PROGRAM); state = read(ROOT/STATE); mission = read(ROOT/DOC/'mission.json')
        for path in (PROGRAM,STATE,DOC/'mission.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'],
                    'Execution changed since the preserved correction baseline')
        require(not any(t['status']=='RUNNING' for t in state['tasks'].values()), 'Worker is running')
        program = historical_projection(deepcopy(old),archives)
        correction = {'profile':'legal-substantive-correction.v1','prior_detours':23,
            'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
            'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'attempt_ceilings':{tid:2 for tid in REPAIRED}}
        program['substantive_continuation_revision']['post_review'] = correction
        program['protected_evidence'] += [ref(ROOT,REVIEW),ref(ROOT,PLAN),ref(ROOT,WORK/'baseline.json')]
        for task in program['tasks']:
            if task['id'] in program['substantive_continuation_revision']['reopened_nodes']:
                number = 2 if task['id'] in REPAIRED else 1
                task['maximum_attempts'] = number
                task['deliverable'] = str(BASE/task['id']/('attempt-'+str(number))/'result.json')
            if task['id'] in REPAIRED:
                saved = state['tasks'][task['id']]
                require(len(saved['attempts']) == 1, 'Unexpected correction attempt baseline')
                saved.update(status='PENDING', reason='Reviewed source/warrant/routing correction')
                saved.pop('result',None)
        validate_program(program,ROOT)
        state['program_hash'] = digest(program)
        state['events'].append({'task_id':None,'action':'REGISTERED_SUBSTANTIVE_CORRECTION',
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':correction['review'],
            'attempts_added':{tid:1 for tid in REPAIRED},'live_calls_added':0})
        mission = historical_projection(mission,archives)
        # References to the new program are computed from staged bytes before any
        # authoritative file is replaced. The write-ahead journal can roll forward.
        stage = ROOT/WORK/'registration-stage'
        save(stage/'program.json',program); save(stage/'state.json',state)
        program_ref = {'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref, plan=ref(ROOT,PLAN),
            substantive_continuation_revision=program['substantive_continuation_revision'])
        mission['history'].append({'id':'integration-master-substantive-correction-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Correct first-pass source, warrant, proposal and command-routing defects in the existing nodes.',
            'next_task':'product-contribution','next_task_reason':'Drain each independent corrected account/graph; binding and review depend on completed assessments.',
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['review'],correction['baseline']]})
        mission['next_task_reason']=mission['history'][-1]['next_task_reason']
        save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
                for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    return {'registered':True,'correction_attempts':list(REPAIRED),'detours':24,'live_calls_added':0}


def binding_proposal(directory):
    """Calculate a proposal on current inputs; no model process is launched."""
    from dataclasses import asdict
    from legalmath.interpretation.assurance.bounded_product import BoundedProduct
    from legalmath.interpretation.assurance.bounded_context import tokenizer, Limits
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    from scripts.legal_integration_accounts import SOURCE
    envelope=read(ROOT/SOURCE); grant=read(ROOT/BASE/'live-grant.json'); ledger=read(ROOT/BASE/'live-calls.json')
    limits=Limits(); encode=tokenizer(ROOT/TOKENIZER)
    service=BoundedCodexProvider(ROOT,ROOT/BASE,encode,limits,routing_file=ROOT/BASE/'campaign-routing.toml')
    populations={}; packet_ids=set(); failures=[]
    for q in QUESTIONS:
        product=BoundedProduct(ROOT,directory/('resource-'+q),service,envelope,encode,
                               active_questions=[q],maximum_corrections=1)
        packets,blocks=product.reading_packets()
        measurements=[]
        for packet in packets:
            if not any(q in product.acquisition_questions(r) for r in packet['request']['records']):continue
            packet_ids.add(digest(packet['request']))
            try:measurements.append(product.dispatch.measure(packet['request'],packet['schema']))
            except Exception as exc:failures.append({'question':q,'reason':str(getattr(exc,'details',None) or exc)})
        requirements=sum(r['kind'] in ('obligation','reading','case') and product.applicable(r,q)
                         for r in product.route.records.values())
        sources=sum(r['kind']=='source' and q in product.acquisition_questions(r)
                    for r in product.route.records.values())
        populations[q]={'reading_requests':len(measurements),'construction_blocks':blocks,
            'maximum_provider_visible_tokens':max((m['provider']['local_tokens'] for m in measurements),default=0),
            'maximum_product_wire_tokens':max((m['local_tokens'] for m in measurements),default=0),
            'requirements':requirements,'source_chunks':sources,
            'common_cap':640,'answer_and_one_correction_cap':2*(requirements+sources+32),
            'comparison_cap':6,'arms':['baseline',*TOOLS]}
    # These are explicit upper bounds for the proposal, not claims about generated
    # review populations. The actual population still requires admission at run time.
    scope={'semantic_controls':128,'question_canaries':8,'acquisition':len(packet_ids),
        'common_preparation':sum(p['common_cap'] for p in populations.values()),
        'answers_including_one_correction':7*sum(p['answer_and_one_correction_cap'] for p in populations.values()),
        'matched_comparisons':24*6,'cross_question_review':42}
    proposed=sum(scope.values()); remaining=grant['maximum_calls']-len(ledger['calls'])
    remaining_seconds=(datetime.fromisoformat(grant['deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
    blockers=[{'id':'live-binding','kind':'implementation','detail':'Campaign live() still rejects acceptance_revision and consumes the historical envelope. A current semantic-preflight binding is required before dispatch.'},
        {'id':'live-semantic','kind':'qualification','detail':'Current code has no successful actual-product remote/changed-exception control. This must gate acquisition, not the ability to run the control itself.'},
        {'id':'source-scope','kind':'qualification','detail':'Scoped answer passages are reviewed; whole-document judgment/Handbook locators and generated final-answer review remain unqualified.'},
        {'id':'acquisition-attempt','kind':'program','detail':'The four original acquisition nodes have each used 3/3 attempts. A finite current continuation must preserve those attempts and explicitly record any additional one.'}]
    if failures or any(p['construction_blocks'] for p in populations.values()):
        blockers.append({'id':'provider-visible-capacity','kind':'implementation','detail':'Current provider-visible request construction failed; see measurements.'})
    if proposed>remaining:
        blockers.append({'id':'full-worst-case-budget','kind':'resource','detail':f'All-arm worst-case demand with a correction for every arm is {proposed} calls; {remaining} remain. Stage admission or a smaller justified demand must precede a promise to complete every branch.'})
    implementation=[ref(ROOT,p) for p in sorted((ROOT/'src/legalmath').rglob('*.py'))]
    implementation += [ref(ROOT,p) for p in sorted((ROOT/'scripts').glob('legal_*.py'))]
    implementation += [ref(ROOT,p) for p in ('requirements-context.lock','pyproject.toml')]
    path=directory/'proposal.json'
    save(directory/'program-at-preparation.json',read(ROOT/PROGRAM))
    save(directory/'ledger-before.json',ledger)
    proposal={'profile':'current-integration-binding-proposal.v1','dispatch_ready':False,
        'source':ref(ROOT,SOURCE),'program':ref(ROOT,directory/'program-at-preparation.json'),
        'task_graph_hash':digest(read(ROOT/PROGRAM)['tasks']),'plan':ref(ROOT,PLAN),
        'implementation':implementation,'grant':ref(ROOT,BASE/'live-grant.json'),
        'ledger_before':ref(ROOT,directory/'ledger-before.json'),'routing':service.routing,
        'routing_file':ref(ROOT,BASE/'campaign-routing.toml'),'limits':asdict(limits),
        'prior_calls':len(ledger['calls']),'maximum_calls':grant['maximum_calls'],
        'remaining_calls':remaining,'deadline_utc':grant['deadline_utc'],
        'remaining_seconds_at_preparation':int(remaining_seconds),'scope':scope,'populations':populations,
        'all_branch_maximum':proposed,'all_branch_seconds_at_120s_two_workers':math.ceil(proposed*120/2),
        'request_failures':failures,'blockers':blockers,
        'measurement_profile':'Actual Dispatch.measure reference framing, product guidance and provider instructions; no model call.',
        'next_execution':{'first':'Bind and run one current actual-product semantic control, maximum 128 calls, under the existing grant.',
            'independent':'Finish scoped source ownership and individual conditional legal accounts; these do not depend on provider availability.',
            'on_pass':'Admit own-question canary/acquisition and budget actual generated populations before answer/tool descendants.',
            'on_failure':'Retain exact stage and candidate failure; stop consumers, continue independent source/question work.'},
        'command':'.venv-context/bin/python scripts/legal_integration_master.py live',
        'resume_command':'.venv-context/bin/python scripts/legal_integration_master.py live',
        'host_approval':'Existing route/account/model/ceiling/window; no new host allowance is inferred by this local proposal.',
        'live_calls_added':0,'integration_complete':False}
    save(path,proposal)
    return {'proposal':ref(ROOT,path),'provider_binding':'PROPOSAL_ONLY','live_dispatch':'VETOED',
        'blockers':blockers,'_conclusion':'Current source, provider-visible requests, implementation and finite demand bound; exact dispatch blockers retained.'}


def latest_evidence(tid):
    state=read(ROOT/STATE)
    record=state['tasks'][tid]['attempts'][-1]
    require('result' in record, 'Missing completed result: '+tid)
    result=read(ROOT/record['result']['path'])
    require(result['status']=='SUCCEEDED', 'Latest task did not succeed: '+tid)
    evidence=next(r for r in result['evidence'] if r['path'].endswith('/evidence.json'))
    verify(ROOT,evidence)
    return read(ROOT/evidence['path'])


def approval_packet():
    revision=read(ROOT/PROGRAM).get('substantive_continuation_revision',{}).get('post_review',{})
    value={'proposal':revision['final_binding']} if revision.get('final_binding') else latest_evidence('current-binding')
    verify(ROOT,value['proposal'])
    proposal=read(ROOT/value['proposal']['path'])
    for item in proposal['implementation']:verify(ROOT,item)
    for key in ('program','plan','source','routing_file','ledger_before','grant'):verify(ROOT,proposal[key])
    if proposal.get('task_graph_hash'):
        require(proposal['task_graph_hash']==digest(read(ROOT/PROGRAM)['tasks']), 'Current proposal task graph changed')
        before=read(ROOT/proposal['ledger_before']['path'])
        current=read(ROOT/BASE/'live-calls.json')
        require(current['calls'][:len(before['calls'])]==before['calls'], 'Historical call charges changed')
    return {**proposal,'proposal':value['proposal']}


def finalize():
    """Finish the same charged correction; no task attempt or live grant added."""
    final=WORK/'finalization'; journal=final/'registration.json'
    if (ROOT/journal).exists():
        with ExitStack() as stack:
            for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
                handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX)
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
        return
    program=read(ROOT/PROGRAM)
    if program['substantive_continuation_revision']['post_review'].get('final_binding'):
        return
    proposal_path=ROOT/final/'binding/proposal.json'
    if not proposal_path.exists():
        binding_proposal(proposal_path.parent)
    proposal=read(proposal_path)
    for item in proposal['implementation']:verify(ROOT,item)
    from scripts.legal_integration_acceptance import current_register,validate_applicability
    matrix=deepcopy(read(ROOT/current_register(program,'applicability')['path']))
    for row in matrix['pairs']:
        qid,tool=row['question'],row['tool']
        if qid not in ('p14','gatecoin') or tool not in ('pyarg','carneades','clingo'):continue
        evidence=latest_evidence('graph-'+qid)
        row.update(decision='applicable',reviewed=True,
            reason='The corrected source-warranted conditional graph executed on this adapter; complete-answer effect remains unmeasured.',
            question_impact=('Retain competing request readings and unknown facts.' if qid=='p14' else
                             'Represent the defeasible default and contrary-access undercut without proving the opposite classification.'),
            prepared_target_scope='Restricted declared reading and hypothetical premises; no authoritative interpretation or client facts inferred.',
            actual_answer_effect='NOT_EVALUATED',evidence=[evidence['targets'],ref(ROOT,REVIEW)],
            target_evidence=[evidence['targets']],warrant_review=[ref(ROOT,REVIEW),
                latest_evidence('account-'+qid)['account']])
    validate_applicability(matrix,ROOT)
    save(ROOT/final/'applicability.json',matrix)
    baseline=read(ROOT/final/'baseline.json')
    archives={(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
    prior={r['previous']['path']:r['archive'] for r in baseline['archived']}
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            return
        for path in (PROGRAM,STATE,DOC/'mission.json'):
            require(ref(ROOT,path)['sha256']==prior[str(path)]['sha256'], 'Execution changed during finalization')
        program=historical_projection(read(ROOT/PROGRAM),archives)
        correction=program['substantive_continuation_revision']['post_review']
        correction.update(final_binding=ref(ROOT,proposal_path),applicability=ref(ROOT,final/'applicability.json'),
            finalization_review=ref(ROOT,final/'review.md'),finalization_baseline=ref(ROOT,final/'baseline.json'))
        for issue in program['remaining_work']:
            if issue['id']=='R11':
                issue.update(status='TARGETS_PREPARED; MATCHED_EFFECTS_OPEN',
                    finding='24 restricted question/tool targets prepared with native evidence; no complete matched answer effect established.')
        program['protected_evidence'] += [correction['final_binding'],correction['applicability'],correction['finalization_review']]
        validate_program(program,ROOT)
        state=read(ROOT/STATE);state['program_hash']=digest(program)
        state['events'].append({'task_id':None,'action':'FINALIZED_SAME_SUBSTANTIVE_CORRECTION',
            'at_utc':datetime.now(timezone.utc).isoformat(),'task_attempts_added':0,'live_calls_added':0})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage=ROOT/final/'registration-stage'
        save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,substantive_continuation_revision=program['substantive_continuation_revision'])
        mission['history'].append({'id':'integration-master-substantive-finalization-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Corrected accounts and 24 restricted native targets retained; actual Dispatch framing measured; complete original answers and matched effects remain open.',
            'next_task':'product-contribution','next_task_reason':'Current semantic preflight needs an executable binding under the existing grant; independent source qualification and fulfillment review remain open. Prior service failures are inconclusive about semantics.',
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['final_binding'],correction['applicability'],correction['finalization_review']]})
        mission['next_task_reason']=mission['history'][-1]['next_task_reason']
        save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)


def settle():
    from scripts.legal_integration_substantive_verify import check
    return check()
