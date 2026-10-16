"""Reviewed finite migration and independent work in the existing master."""
from copy import deepcopy
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import subprocess

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = Path('artifacts/legal-mission-control/2026-10-14/execution-refresh')
REVIEW = Path('docs/plans/legal-integration-master-execution-refresh-2026-10-14.md')
REOPEN = ('ownership-2023', 'ownership-2025', 'ownership-handbook',
          'qualify-p10', 'qualify-p14', 'qualify-evidence', 'qualify-gatecoin',
          'current-binding', 'live-approval', 'acquire-p10', 'acquire-p14',
          'acquire-evidence', 'acquire-gatecoin', 'continuation-review')
NEW = tuple('inventory-' + q for q in QUESTIONS) + ('semantic-preflight',)
USER = ('Ensure repair and refresh after each part; continue independent parts after a blocker; '
        'use exact allow-listed commands; continue the existing program.')


def expected_tasks(old, state, review):
    tasks = deepcopy(old['tasks'])
    for task in tasks:
        tid = task['id']
        if tid not in REOPEN:
            continue
        number = len(state['tasks'][tid]['attempts']) + 1
        task.update(maximum_attempts=number,
                    deliverable=str(BASE/tid/f'attempt-{number}'/'result.json'))
        task['inputs'] = [*task.get('inputs', []), review]
        if tid.startswith('qualify-'):
            task['acceptance'] = 'Current source and provider-visible local capacity; acquisition separately requires semantic and service qualification'
        elif tid == 'current-binding':
            task.update(requires=['sources'], after=[],
                acceptance='Verified current code/source/provider binding and finite semantic stage under unchanged grant')
        elif tid == 'live-approval':
            task.update(requires=['current-binding', 'semantic-preflight'], after=[],
                acceptance='Existing grant verified; successful current semantic preflight; current canaries retained per question')
        elif tid == 'continuation-review':
            task.update(requires=[], after=[*('inventory-'+q for q in QUESTIONS),
                'ownership-2023','ownership-2025','ownership-handbook',
                *('qualify-'+q for q in QUESTIONS),'current-binding'])
    for tid in NEW:
        q = tid.removeprefix('inventory-')
        live = tid == 'semantic-preflight'
        tasks.append({'id':tid,'executor':'agent' if live else 'command',
            'kind':'product_evaluation','question_ids':list(QUESTIONS) if live else [q],
            'priority':5, 'requires':['current-binding'] if live else ['sources','account-'+q],
            'after':[], 'maximum_attempts':1, 'write_resources':[tid], 'inputs':[review],
            'acceptance':('Same-evidence actual-product remote and changed exception controls, fresh review, <=128 calls'
                if live else 'Every assigned original item mapped to source, conditional account, unresolved premises and exact evidence request'),
            'deliverable':str(BASE/tid/'attempt-1/result.json'),
            **({} if live else {'command':['.venv/bin/python','scripts/legal_integration_master.py','worker',tid],
                               'timeout_seconds':3600})})
    return tasks


def validate_revision(program, root, *, plan_reference=None):
    if program['execution_refresh'].get('post_review'):
        from scripts.legal_integration_execution_repair import validate_repair
        return validate_repair(program, root, plan_reference=plan_reference)
    revision = program['execution_refresh']
    require(revision.get('profile') == 'legal-execution-refresh.v1'
        and revision.get('prior_detours') == 24 and revision.get('additional_consolidated_revision') == 1
        and revision.get('prior_charged_calls') == 232 and revision.get('live_calls_added') == 0
        and revision.get('attempts_reset') is False and revision.get('user_instruction'), 'Unreviewed execution refresh')
    for key in ('review','baseline','prior_program','prior_state'): verify(root, revision[key])
    old = read(root/revision['prior_program']['path'])
    state = read(root/revision['prior_state']['path'])
    require(not old.get('execution_refresh') and state['program_hash'] == digest(old),
            'Unbound or renewed execution refresh')
    archives = read(root/revision['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Historical archive changed bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archives})
    validate_program(projected, root)
    require(set(revision['reopened_nodes']) == set(REOPEN) and set(revision['new_nodes']) == set(NEW),
            'Unreviewed refresh scope')
    require(program['tasks'] == expected_tasks(old, state, revision['review']),
            'Refresh changed an unrelated task, dependency or attempt ceiling')
    expected = deepcopy(projected)
    expected.update(tasks=program['tasks'],execution_refresh=revision)
    expected['protected_evidence'] += [revision['review'],revision['baseline'],plan_reference or ref(root, PLAN)]
    require(program == expected, 'Refresh changed shared resources or historical program fields')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    from scripts.legal_integration_service_continuation import WORK as SERVICE_WORK,register as service_register
    if (ROOT/SERVICE_WORK/'local-review.json').exists():
        return service_register()
    from scripts.legal_integration_prerequisites import RECOVERY_WORK,recovery_register
    if (ROOT/RECOVERY_WORK/'local-review.json').exists():
        return recovery_register()
    from scripts.legal_integration_prerequisites import WORK as PREREQUISITES
    if (ROOT/PREREQUISITES/'local-review.json').exists():
        from scripts.legal_integration_prerequisites import register as register_prerequisites
        return register_prerequisites()
    if (ROOT/WORK/'post-review/response-repair/local-review.json').exists():
        from scripts.legal_integration_response_repair import register as register_response
        return register_response()
    if (ROOT/WORK/'post-review/binding-fix/baseline.json').exists():
        from scripts.legal_integration_binding_fix import register as register_binding_fix
        return register_binding_fix()
    if (ROOT/WORK/'post-review/baseline.json').exists():
        from scripts.legal_integration_execution_repair import register as register_repair
        return register_repair()
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a')); fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/WORK/'baseline.json')
        archives={(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'], 'Baseline changed during refresh')
        old=read(ROOT/PROGRAM); state=read(ROOT/STATE)
        require(not any(r['status']=='RUNNING' for r in state['tasks'].values()),'Worker running')
        revision={'profile':'legal-execution-refresh.v1','prior_detours':24,
            'additional_consolidated_revision':1,'prior_charged_calls':232,'live_calls_added':0,
            'attempts_reset':False,'user_instruction':USER,'review':ref(ROOT,REVIEW),
            'baseline':ref(ROOT,WORK/'baseline.json'),'prior_program':refs[str(PROGRAM)],
            'prior_state':refs[str(STATE)],'reopened_nodes':list(REOPEN),'new_nodes':list(NEW)}
        program=historical_projection(deepcopy(old),archives)
        program.update(execution_refresh=revision,tasks=expected_tasks(old,state,revision['review']))
        program['protected_evidence'] += [revision['review'],revision['baseline'],ref(ROOT,PLAN)]
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed bounded execution refresh; earlier attempts retained')
            state['tasks'][tid].pop('result',None)
        for tid in NEW: state['tasks'][tid]={'status':'PENDING','attempts':[]}
        state['program_hash']=digest(program)
        state['events'].append({'action':'REVIEWED_EXECUTION_REFRESH','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage=ROOT/WORK/'registration-stage'
        save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),execution_refresh=revision)
        reason='Execute independent source and item-specific legal work; bind current finite preflight before live consumers.'
        mission['history'].append({'id':'integration-master-execution-refresh-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Reviewed the same master; preserved all attempts and limits; separated preflight from acquisition.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['baseline']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return MasterExecution(ROOT,PROGRAM,STATE).summary()


def inventory(qid, directory):
    from scripts.legal_integration_accounts import SOURCE
    envelope=read(ROOT/SOURCE); manifest=envelope['answer_acceptance']
    account_path=BASE/('account-'+qid)/'attempt-2/account.json'
    account=read(ROOT/account_path)
    units={u['unit_id']:u for u in envelope['source_packet']['units']}
    locations={(r['reading_id'],r['citation_index']):r for r in manifest['current_quote_locations']['citations']}
    rows=[]
    for kind,field in (('obligation','acceptance_obligations'),('reading','original_readings'),('case','cases')):
        for item in manifest[field]:
            if qid not in item.get('question_ids',QUESTIONS): continue
            identifier=item.get('id',item.get('case_id')); quotes=[]; failures=[]
            if kind=='reading':
                for index,citation in enumerate(item['citations']):
                    loc=locations[(identifier,index)]
                    if len(loc['locations'])!=1:
                        failures.append('Ambiguous current source location');continue
                    span=loc['locations'][0]; unit=units[span['unit_id']]
                    text=unit['text'][span['start']:span['end']]
                    require(' '.join(text.split())==' '.join(citation['quote'].split()),'Changed original reading quotation')
                    quotes.append({**span,'quote':text,'unit_hash':digest(unit['text'])})
            premises=[p['statement'] for p in item.get('missing_premises',[])]
            rows.append({'kind':kind,'id':identifier,'original':item,'current_quotes':quotes,
                'source_location_failures':failures,'unresolved_premises':premises,
                'conditional_account':ref(ROOT,account_path),
                'conditional_results':account['conditions'],
                'evidence_requests':premises or account['facts_required'],
                'fulfillment':'OPEN', 'warrant_review':'PENDING_ITEM_SPECIFIC_ENTAILMENT_REVIEW',
                'reason':item.get('first_unresolved_step') or item.get('must_preserve') or item['statement']})
    require(rows,'Empty original-question review')
    value={'profile':'original-question-inventory.v1','question':qid,'source':ref(ROOT,SOURCE),
        'records':rows,'counts':dict(Counter(r['kind'] for r in rows)),
        'original_inventory_fulfilled':False,'actual_product_answer':False,
        'source_location_failures':sum(len(r['source_location_failures']) for r in rows),
        'scope':'Individual original demands and quotation locations linked to retained conditional analysis; semantic fulfillment remains open.'}
    save(directory/'inventory.json',value)
    return {'inventory':ref(ROOT,directory/'inventory.json'),'counts':value['counts'],
        '_conclusion':qid+': original demands and exact quotations retained individually with conditional account and unmet premises; no fulfillment inferred.'}


def worker(tid,directory):
    from scripts.legal_integration_accounts import SOURCE
    if read(ROOT/PROGRAM).get('prerequisite_repair'):
        SOURCE = Path(read(ROOT/PROGRAM)['prerequisite_repair']['source']['path'])
    if tid.startswith('inventory-'):return inventory(tid[10:],directory)
    if tid.startswith('ownership-'):
        from scripts.legal_integration_source_ownership import assess
        return assess(tid,read(ROOT/SOURCE),directory)
    if tid.startswith('qualify-'):
        from scripts.legal_integration_substantive import qualify
        value=qualify(tid[8:],read(ROOT/SOURCE),directory)
        capacity=read(ROOT/value['capacity']['path'])
        require(not capacity['construction_blocks'] and not capacity['request_failures'],'Current local capacity failed')
        value.update(_node_status='SUCCEEDED',_conclusion=tid[8:]+': current local construction and capacity pass; semantic and own-question service controls remain separate prerequisites.')
        return value
    if tid=='current-binding':
        from scripts.legal_integration_current_live import prepare
        return prepare(directory)
    if tid=='continuation-review':return verification(directory)
    raise ValueError('No execution refresh worker: '+tid)


def verification(directory=None):
    if read(ROOT/PROGRAM).get('service_continuation'):
        from scripts.legal_integration_service_continuation import verification as service_verification
        return service_verification(directory)
    if read(ROOT/PROGRAM).get('execution_recovery'):
        from scripts.legal_integration_prerequisites import recovery_verification
        return recovery_verification(directory)
    if read(ROOT/PROGRAM).get('prerequisite_repair'):
        from scripts.legal_integration_prerequisites import verification as verify_prerequisites
        return verify_prerequisites(directory)
    if read(ROOT/PROGRAM)['execution_refresh'].get('post_review'):
        from scripts.legal_integration_execution_repair import verification as verify_repair
        return verify_repair(directory)
    program=read(ROOT/PROGRAM); validate_program(program,ROOT)
    state=read(ROOT/STATE); before=read(ROOT/program['execution_refresh']['prior_state']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Historical attempt changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    result={'profile':'execution-refresh-verification.v1','old_attempts_preserved':True,
        'execution':view['execution'],'ready':view['ready'],'running':view['running'],
        'task_counts':dict(Counter(r['status'] for r in view['tasks'].values())),
        'calls':len(read(ROOT/BASE/'live-calls.json')['calls']),'detours':25,'integration_complete':False,
        '_conclusion':'Current frontier and immutable prior attempts verified; legal answers and matched effects require separate evidence.'}
    target=directory or ROOT/WORK
    target.mkdir(parents=True,exist_ok=True);save(target/'verification.json',result)
    return result
