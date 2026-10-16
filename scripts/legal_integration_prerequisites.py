"""One reviewed prerequisite revision of the existing integration master."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = Path('artifacts/legal-mission-control/2026-10-14/prerequisite-repair')
REVIEW = WORK/'review.md'
REOPEN = ('ownership-2023', 'ownership-2025', 'ownership-handbook',
          'current-binding', 'semantic-preflight', 'continuation-review')
POLICY = {'profile': 'scoped-terminal-recovery.v1', 'maximum_replacements': 12,
          'per_request_replacements': 1, 'prior_replacements_retained': 2}
CASE_CALLS = 256
STAGE_CALLS = 3*(CASE_CALLS+2)+POLICY['maximum_replacements']
USER = 'Repair the master program to tackle these prerequisites; review the program; execute.'
SOURCE = WORK/'complete-handbook-envelope.json'


def local_measurements():
    """Measure actual current wire requests without dispatching or spending calls."""
    from dataclasses import replace
    from scripts.legal_integration_master import TOKENIZER, RULES
    from scripts.legal_integration_reopening_live import fixture
    from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
    from legalmath.interpretation.assurance.bounded_product import BoundedProduct, NOTE
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    from legalmath.interpretation.assurance.bounded_references import prepare
    limits=Limits();encode=tokenizer(ROOT/TOKENIZER);rows=[]
    service=BoundedCodexProvider(ROOT,ROOT/BASE,encode,limits,routing_file=ROOT/BASE/'campaign-routing.toml')
    def product(name,envelope,selected_limits):
        return BoundedProduct(ROOT,ROOT/WORK/'measurement-requests'/name,service,envelope,
            encode,limits=selected_limits,maximum_calls=CASE_CALLS,maximum_corrections=1)
    def measure(owner,request,schema):
        result={'owner':owner,'task':request.get('task'),
            'request_hash':digest(request),'schema_hash':digest(schema),
            'measurement':active.dispatch.measure(request,schema)}
        wire=prepare(request,schema)
        target=WORK/'measurement-requests'/'complete-wire'/(str(len(rows))+'.json')
        save(ROOT/target,{'original_request':request,'original_schema':schema,
            'wire_request':wire['request'],'wire_schema':wire['schema']})
        result['request_evidence']=ref(ROOT,target);rows.append(result)
    envelope=read(ROOT/SOURCE);active=product('original-questions',envelope,limits)
    packets,blocked=active.reading_packets()
    require(not blocked,'Current source delivery blocked before registration')
    for packet in packets:measure('99-unit-original-source',packet['request'],packet['schema'])
    source_packets=len(packets)
    for mutation,missing,name in ((False,False,'remote-exception'),(True,False,'changed-exception'),
                                (False,True,'missing-incorporated-rule')):
        envelope=fixture(mutation,explicit_scope=True,missing_authority=missing)
        active=product(name,envelope,replace(limits,records_per_request=1))
        packets,blocked=active.reading_packets();require(not blocked,'Synthetic scope construction blocked')
        for packet in packets:measure(name,packet['request'],packet['schema'])
        question=envelope['original_questions'][0]
        records=[r for r in active.route.records.values() if r['kind']=='source']
        request=active.request('ANSWER_ORIGINAL_QUESTION',question,records,
            payload={'method':'Read all supplied evidence together.'},expected=[r['id'] for r in records])
        measure(name,request,NOTE)
        if not missing:
            old_path=Path('artifacts/legal-mission-control/2026-10-14/execution-refresh/post-review/response-repair/account-correction/live/semantic-control')/name/'partitioned/result.json'
            prior=read(ROOT/old_path)['answers']['p14'];correction=prior['correction']
            # Actual retained adverse payloads test capacity only. No old model
            # sample is replayed into a live result under changed question scope.
            def dry_call(key,request,schema,validator):
                measure(name+'-retained-adverse-payload',request,schema)
                return {'status':'MEASURED_ONLY'}
            active.dispatch.call=dry_call
            active.review_warrants('p14',question,correction.get('original_answer',prior['answer']),
                correction.get('original_reviews',prior['reviews']),correction.get('original_requirement_details',[]))
    installed=Path('/home/chakwong/.codex/rules/legalmath-integration-master.rules')
    require(installed.exists() and installed.read_bytes()==(ROOT/RULES).read_bytes(),'Installed exact-action rules differ')
    value={'profile':'prerequisite-request-capacity.v1','provider_calls':0,'source':ref(ROOT,SOURCE),
        'source_packets':source_packets,'requests':rows,
        'maximum_local_tokens':max(r['measurement']['local_tokens'] for r in rows),
        'maximum_provider_visible_tokens':max(r['measurement']['provider']['local_tokens'] for r in rows),
        'installed_rules_match':True,'rules':ref(ROOT,RULES),
        'scope':'Complete current reading requests, three unpartitioned controls and retained adverse payloads with new scope/warrant schema. Future generated requests remain checked at dispatch; hidden service framing unmeasured.'}
    save(ROOT/WORK/'capacity.json',value)
    return {k:v for k,v in value.items() if k!='requests'}


def prepare_source():
    """Complete already selected Handbook chapters without changing original items."""
    from scripts.legal_integration_accounts import SOURCE as PRIOR_SOURCE
    from legalmath.interpretation.assurance.legal_locators import build_index, retained_html
    from legalmath.interpretation.assurance.answer_acceptance import reading_quote_locations, validate_manifest
    original = read(ROOT/PRIOR_SOURCE); envelope = deepcopy(original)
    supplement = read(ROOT/BASE/'corpus-work/source-supplement.json')['handbook']
    verify(ROOT,supplement['current_pdf'])
    text_ref = ref(ROOT,BASE/'corpus-work/ut-handbook-current.txt')
    pages = (ROOT/text_ref['path']).read_text().split('\f')
    present = {u['unit_id'] for u in envelope['source_packet']['units']}; added=[]
    for number in list(range(7,19))+list(range(24,47)):
        uid = f'handbook.oct2024.page{number}'
        if uid in present: continue
        unit = {'unit_id':uid,'text':pages[number-1],
            'locator':f'SFC Handbook October 2024 fifth edition, PDF page {number}',
            'normative':True,'span':{}}
        envelope['source_packet']['units'].append(unit); added.append(number)
        envelope['source_question_ids'][uid] = list(('p10','p14','evidence','gatecoin'))
    envelope['source_qualification']['source_packet_hash'] = digest(envelope['source_packet'])
    envelope['source_qualification']['evidence'] += [ref(ROOT,PRIOR_SOURCE),text_ref,supplement['current_pdf']]
    envelope['source_qualification']['limitations'] += [
        'Current supplement supplies complete retained OPS chapters 1-7 and UT chapters 1-6 to avoid page-edge omissions. '
        'Historical excerpt limitations above remain provenance; applicability is conditional on product, actor, date and waivers.']
    envelope['legal_indexes'] = [build_index(envelope['source_packet'],retained_html(d['source'],ROOT),
        source_ref=d['source'],unit_ids=d['unit_ids'],root=ROOT,
        numbering_profile=d.get('numbering_profile','ordered-lists')) for d in envelope['answer_acceptance']['source_documents']]
    envelope['answer_acceptance']['current_quote_locations'] = reading_quote_locations(envelope['answer_acceptance'],envelope['source_packet'])
    envelope['binding'] = {'profile':'complete-handbook-source.v1','predecessor':ref(ROOT,PRIOR_SOURCE),
        'source_packet_hash':digest(envelope['source_packet']),'added_pdf_pages':added}
    envelope['binding_hash'] = digest(envelope['binding'])
    validate_manifest(envelope['answer_acceptance'],envelope['original_questions'],ROOT)
    for field in ('acceptance_obligations','original_readings','cases'):
        require(envelope['answer_acceptance'][field] == original['answer_acceptance'][field], 'Changed original demands')
    save(ROOT/SOURCE,envelope)
    return {'source':ref(ROOT,SOURCE),'added_pages':added,'source_units':len(envelope['source_packet']['units'])}


def expected_program(old, before, revision, root, *, plan_reference=None):
    result = deepcopy(old)
    result['prerequisite_repair'] = revision
    result['protected_evidence'] += [revision['review'], revision['baseline'],
        revision['local_review'], plan_reference or ref(root, PLAN)]
    for task in result['tasks']:
        if task['id'] not in REOPEN: continue
        number = len(before['tasks'][task['id']]['attempts'])+1
        task.update(maximum_attempts=number, deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] = [*task.get('inputs', []), revision['review'], revision['local_review']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = ('Fresh remote/changed exception and missing-incorporated-rule controls; '
                'scoped warrant decisions, complete fresh reviews; <=786 charged calls, <=12 terminal replacements')
        if task['id'].startswith('ownership-'):
            task['acceptance'] += '; full rendered passage, table and nested label verification; explicit edition/applicability limits'
    return result


def validate_revision(program, root, *, plan_reference=None):
    revision = program['prerequisite_repair']
    require(revision.get('profile') == 'integration-prerequisites.v1'
        and revision.get('prior_detours') == 29 and revision.get('additional_consolidated_revision') == 1
        and revision.get('live_calls_added') == 0 and revision.get('attempts_reset') is False
        and revision.get('terminal_recovery_policy') == POLICY
        and revision.get('semantic_stage_maximum') == STAGE_CALLS
        and revision.get('semantic_case_maximum') == CASE_CALLS
        and revision.get('user_instruction') == USER and revision.get('reopened_nodes') == list(REOPEN),
        'Unreviewed prerequisite revision')
    for key in ('review','baseline','local_review','prior_program','prior_state','prior_binding','prior_ledger','source'):
        verify(root, revision[key])
    old = read(root/revision['prior_program']['path']); before = read(root/revision['prior_state']['path'])
    require(not old.get('prerequisite_repair') and before['program_hash'] == digest(old), 'Wrong prerequisite baseline')
    require(before['tasks']['semantic-preflight']['status'] == 'BLOCKED'
        and len(before['tasks']['semantic-preflight']['attempts']) == 4
        and before['tasks']['continuation-review']['status'] == 'SUCCEEDED'
        and not any(r['status']=='RUNNING' for r in before['tasks'].values()), 'Unsettled prerequisite baseline')
    require(len(read(root/revision['prior_ledger']['path'])['calls']) == 781, 'Lost prior charges')
    archives = read(root/revision['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Prerequisite archive changed bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archives})
    validate_program(projected, root)
    require(program == expected_program(projected,before,revision,root,plan_reference=plan_reference),
        'Prerequisite revision changed unrelated tasks or authority')
    local = read(root/revision['local_review']['path'])
    require(local.get('verdict') == 'PASS' and local.get('provider_calls') == 0, 'Missing local implementation review')
    for reference in local['evidence']: verify(root, reference)
    return {t['id']: t['maximum_attempts'] for t in program['tasks']}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a')); fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline = read(ROOT/WORK/'baseline.json')
        archives = {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'], 'Prerequisite baseline changed: '+str(path))
        old, state = read(ROOT/PROGRAM), read(ROOT/STATE)
        revision = {'profile':'integration-prerequisites.v1','prior_detours':29,'additional_consolidated_revision':1,
            'live_calls_added':0,'attempts_reset':False,'user_instruction':USER,
            'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'local_review':ref(ROOT,WORK/'local-review.json'),
            'source':ref(ROOT,SOURCE),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN),'semantic_stage_maximum':STAGE_CALLS,
            'semantic_case_maximum':CASE_CALLS,'terminal_recovery_policy':POLICY}
        program = expected_program(historical_projection(old,archives),state,revision,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed prerequisite repair; previous attempts retained')
            state['tasks'][tid].pop('result',None)
        state['program_hash'] = digest(program)
        state['events'].append({'action':'REVIEWED_PREREQUISITE_REPAIR','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],'attempts_reset':False})
        mission = historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage = ROOT/WORK/'registration-stage'
        save(stage/'program.json',program); save(stage/'state.json',state)
        program_ref = {'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),
            execution_refresh=program['execution_refresh'],prerequisite_repair=revision)
        reason = 'Execute independent source fidelity, scoped semantic qualification and bounded service recovery; refresh each result.'
        mission['history'].append({'id':'integration-master-prerequisites-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Reviewed explicit scope/warrant repair, full source verification and bounded terminal recovery.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['baseline'],revision['local_review']]})
        mission['next_task_reason'] = reason; save(stage/'mission.json',mission)
        writes = [{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':30,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def verification(directory=None):
    program = read(ROOT/PROGRAM); validate_program(program,ROOT)
    revision = program['prerequisite_repair']; before = read(ROOT/revision['prior_state']['path'])
    state = read(ROOT/STATE)
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Historical attempt changed')
    ledger = read(ROOT/BASE/'live-calls.json'); prior = read(ROOT/revision['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Historical calls changed')
    view = MasterExecution(ROOT,PROGRAM,STATE).summary()
    value = {'profile':'prerequisite-repair-verification.v1','old_attempts_preserved':True,'old_calls_preserved':True,
        'calls':len(ledger['calls']),'detours':30,'execution':view['execution'],'ready':view['ready'],
        'running':view['running'],'task_counts':dict(Counter(r['status'] for r in view['tasks'].values())),
        'blocked':view['blocked'],'integration_complete':False,
        '_conclusion':'Prerequisite revision and previous charges/attempts verified; integration requires original-question effect evidence.'}
    save((directory or ROOT/WORK)/'verification.json',value)
    return value


# Current amendment stays in the same master and preserves the settled v1 owner
# and call histories. These constants are reviewed in RECOVERY_REVIEW.
RECOVERY_WORK = Path('artifacts/legal-mission-control/2026-10-14/execution-recovery')
RECOVERY_REVIEW = RECOVERY_WORK/'review.md'
RECOVERY_REOPEN = ('current-binding', 'semantic-preflight', 'continuation-review')
RECOVERY_USER = 'repair the master program with a better execution handling and close the blocks.'
RECOVERY_STAGE_CALLS = 3*(CASE_CALLS+2)+48


def recovery_checkpoints():
    from legalmath.interpretation.assurance.bounded_checkpoint import initial_key
    trace = read(ROOT/WORK/'transport-trace.json')
    result = {}
    for name in ('remote-exception','changed-exception','missing-incorporated-rule'):
        result[name] = {}
        for arm in ('unpartitioned','partitioned'):
            calls = WORK/'live/semantic-control'/name/arm/'calls'
            dispatch = read(ROOT/calls/'dispatch.json')
            require(not any(r['status']=='RESERVED' for r in dispatch['calls'].values()),
                'Uncertain retained call requires reconciliation')
            rows = {key:{field:ref(ROOT,calls/key/(field+'.json')) for field in ('request','schema','result')}
                for key,row in dispatch['calls'].items() if initial_key(key) and row['status']=='VALIDATED'}
            failures = {}
            for key,row in dispatch['calls'].items():
                if row['status'] != 'FAILED':continue
                evidence = ref(ROOT,calls/key/'result.json')
                matches = [r for r in trace['failures'] if r['logical_evidence'] == evidence]
                require(len(matches)==1 and matches[0]['provider_receipts'], 'Failed request lacks reviewed transport trace')
                receipts = [r['manifest'] for r in matches[0]['provider_receipts']]
                require(all(not read(ROOT/r['path'])['complete_output_present'] for r in receipts),
                    'Cannot recover a completed prior response')
                failures[key] = {'result':evidence,'receipts':receipts}
            manifest = {'profile':'bounded-exact-checkpoint.v2','input_hash':dispatch['input_hash'],
                'dispatch':ref(ROOT,calls/'dispatch.json'),'calls':rows,'recoverable_failures':failures,
                'scope':'Exact validated initial responses only; changed/missing requests execute under the new bounded stage. No fresh replication claim.'}
            target = RECOVERY_WORK/'checkpoints'/name/(arm+'.json')
            save(ROOT/target,manifest);result[name][arm]=ref(ROOT,target)
    save(ROOT/RECOVERY_WORK/'checkpoints.json',result)
    return result


def recovery_measurements():
    from dataclasses import replace
    from scripts.legal_integration_master import TOKENIZER,RULES
    from scripts.legal_integration_reopening_live import fixture
    from legalmath.interpretation.assurance.bounded_context import Limits,tokenizer
    from legalmath.interpretation.assurance.bounded_product import BoundedProduct,NOTE
    from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
    limits=Limits();encode=tokenizer(ROOT/TOKENIZER)
    provider=BoundedCodexProvider(ROOT,ROOT/BASE,encode,limits,routing_file=ROOT/BASE/'campaign-routing.toml')
    rows=[]
    envelopes=[('original',read(ROOT/SOURCE),limits)]
    for mutation,missing,name in ((False,False,'remote-exception'),(True,False,'changed-exception'),(False,True,'missing-incorporated-rule')):
        envelope=fixture(mutation,explicit_scope=True,missing_authority=missing)
        envelope['answer_acceptance']['acceptance_obligations']=[{'id':'synthetic-duty','question_ids':['p14'],
            'statement':('Resolve the requested applicable regime, preserving genuinely missing incorporated authority.'
                if missing else 'Resolve the stated transfer question under all supplied synthetic rules.')}]
        envelopes.append((name,envelope,replace(limits,records_per_request=1)))
    for name,envelope,bounds in envelopes:
        product=BoundedProduct(ROOT,ROOT/RECOVERY_WORK/'measurements'/name,provider,envelope,encode,
            limits=bounds,maximum_calls=CASE_CALLS,maximum_corrections=1)
        def measure(key,request,schema,validator=None):
            rows.append({'owner':name,'key':key,'request_hash':digest(request),
                'measurement':product.dispatch.measure(request,schema)})
            return {'status':'MEASURED_ONLY'}
        packets,blocked=product.reading_packets();require(not blocked,'Unbounded reading request')
        for i,p in enumerate(packets):measure('read-'+str(i),p['request'],p['schema'])
        if name!='original':
            product.dispatch.call=measure
            details=product.requirement_details()
            require(all(d['result']['status']=='MEASURED_ONLY' for d in details),'Requirement delivery capacity failed')
            records=[r for r in product.route.records.values() if r['kind']=='source']
            question=envelope['original_questions'][0]
            measure('comparator',product.request('ANSWER_ORIGINAL_QUESTION',question,records,
                payload={'method':'Read all supplied evidence together.'},expected=[r['id'] for r in records]),NOTE)
    installed=Path('/home/chakwong/.codex/rules/legalmath-integration-master.rules')
    require(installed.read_bytes()==(ROOT/RULES).read_bytes(),'Exact master rules differ')
    result={'profile':'execution-recovery-capacity.v1','provider_calls':0,'requests':rows,
        'maximum_local_tokens':max(r['measurement']['local_tokens'] for r in rows),
        'maximum_provider_visible_tokens':max(r['measurement']['provider']['local_tokens'] for r in rows),
        'installed_rules_match':True,'rules':ref(ROOT,RULES)}
    save(ROOT/RECOVERY_WORK/'capacity.json',result)
    return {k:v for k,v in result.items() if k!='requests'}


def expected_recovery_program(old,before,revision,root,*,plan_reference=None):
    result=deepcopy(old);result['execution_recovery']=revision
    result['protected_evidence'] += [revision[k] for k in ('review','baseline','local_review','checkpoints')]
    result['protected_evidence'].append(plan_reference or ref(root,PLAN))
    for task in result['tasks']:
        if task['id'] not in RECOVERY_REOPEN:continue
        number=len(before['tasks'][task['id']]['attempts'])+1
        task.update(maximum_attempts=number,deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] += [revision['review'],revision['local_review'],revision['checkpoints']]
        if task['id']=='semantic-preflight':
            task['acceptance']='All three unchanged semantic controls and complete reviews; exact retained responses, fresh changed/corrected requests, <=822 charged calls including <=48 service replacements.'
    return result


def validate_recovery_revision(program,root,*,plan_reference=None):
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_RECOVERY_POLICY
    revision=program['execution_recovery']
    require(revision.get('profile')=='integration-execution-recovery.v1'
        and revision.get('prior_detours')==30 and revision.get('additional_consolidated_revision')==1
        and revision.get('live_calls_added')==0 and revision.get('attempts_reset') is False
        and revision.get('user_instruction')==RECOVERY_USER and revision.get('reopened_nodes')==list(RECOVERY_REOPEN)
        and revision.get('service_recovery_policy')==SERVICE_RECOVERY_POLICY
        and revision.get('semantic_stage_maximum')==RECOVERY_STAGE_CALLS,
        'Unreviewed execution recovery revision')
    for key in ('review','baseline','local_review','checkpoints','prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root,revision[key])
    old=read(root/revision['prior_program']['path']);before=read(root/revision['prior_state']['path'])
    require(not old.get('execution_recovery') and before['program_hash']==digest(old),'Wrong recovery baseline')
    require(before['tasks']['semantic-preflight']['status']=='BLOCKED'
        and len(before['tasks']['semantic-preflight']['attempts'])==5
        and before['tasks']['continuation-review']['status']=='SUCCEEDED'
        and not any(r['status']=='RUNNING' for r in before['tasks'].values()),'Unsettled recovery baseline')
    require(len(read(root/revision['prior_ledger']['path'])['calls'])==1019,'Lost retained charges')
    archives=read(root/revision['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed archived bytes')
        verify(root,row['archive'])
    projected=historical_projection(old,{(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archives})
    validate_program(projected,root)
    require(program==expected_recovery_program(projected,before,revision,root,plan_reference=plan_reference),
        'Recovery changed unrelated owners, authority or criteria')
    local=read(root/revision['local_review']['path'])
    require(local.get('verdict')=='PASS' and local.get('provider_calls')==0,'Missing recovery implementation review')
    for evidence in local['evidence']:verify(root,evidence)
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def recovery_register():
    from scripts.legal_integration_post_review import finish_transaction
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_RECOVERY_POLICY
    journal=RECOVERY_WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/RECOVERY_WORK/'baseline.json')
        archives={(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256']==refs[str(path)]['sha256'],'Recovery baseline changed: '+str(path))
        old,state=read(ROOT/PROGRAM),read(ROOT/STATE)
        revision={'profile':'integration-execution-recovery.v1','prior_detours':30,'additional_consolidated_revision':1,
            'live_calls_added':0,'attempts_reset':False,'user_instruction':RECOVERY_USER,
            'review':ref(ROOT,RECOVERY_REVIEW),'baseline':ref(ROOT,RECOVERY_WORK/'baseline.json'),
            'local_review':ref(ROOT,RECOVERY_WORK/'local-review.json'),'checkpoints':ref(ROOT,RECOVERY_WORK/'checkpoints.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(RECOVERY_REOPEN),'semantic_stage_maximum':RECOVERY_STAGE_CALLS,
            'service_recovery_policy':SERVICE_RECOVERY_POLICY}
        program=expected_recovery_program(historical_projection(old,archives),state,revision,ROOT)
        validate_program(program,ROOT)
        for tid in RECOVERY_REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed execution recovery; prior attempts retained')
            state['tasks'][tid].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'action':'REVIEWED_EXECUTION_RECOVERY','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage=ROOT/RECOVERY_WORK/'registration-stage'
        save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),
            prerequisite_repair=program['prerequisite_repair'],execution_refresh=program['execution_refresh'],
            execution_recovery=revision)
        reason='Execute reviewed transport recovery, exact checkpoint reuse and independent source-complete correction; refresh each result and continue all ready consumers.'
        mission['history'].append({'id':'integration-master-execution-recovery-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Reviewed finite recovery and source/correction repairs under the unchanged Sol grant.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['baseline'],revision['local_review']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':31,'reopened_nodes':list(RECOVERY_REOPEN),'live_calls_added':0}


def recovery_verification(directory=None):
    program=read(ROOT/PROGRAM);validate_program(program,ROOT)
    revision=program['execution_recovery'];before=read(ROOT/revision['prior_state']['path'])
    state=read(ROOT/STATE);ledger=read(ROOT/BASE/'live-calls.json');prior=read(ROOT/revision['prior_ledger']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Historical attempts changed')
    require(ledger['calls'][:len(prior['calls'])]==prior['calls'],'Historical calls changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    value={'profile':'execution-recovery-verification.v1','old_attempts_preserved':True,'old_calls_preserved':True,
        'calls':len(ledger['calls']),'detours':31,'execution':view['execution'],'ready':view['ready'],
        'running':view['running'],'blocked':view['blocked'],'integration_complete':False,
        '_conclusion':'History and execution recovery verified; original-answer/tool effects still determine integration acceptance.'}
    save((directory or ROOT/RECOVERY_WORK)/'verification.json',value)
    return value
