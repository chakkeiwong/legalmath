"""One reviewed response/scope repair in the existing integration master."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_integration_execution_repair import WORK as PARENT, REOPEN, SEMANTIC_STAGE_CALLS
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = PARENT/'response-repair'
REVIEW = PARENT/'response-review-repair.md'
ACCOUNT = WORK/'account-correction'
ACCOUNT_REVIEW = WORK/'account-correction-review.md'


def expected_program(old, before, correction, root, *, plan_reference=None):
    result = deepcopy(old)
    result['execution_refresh']['post_review']['response_repair'] = correction
    result['protected_evidence'] += [correction['review'], correction['baseline'],
        correction['local_review'], plan_reference or ref(root, PLAN)]
    for task in result['tasks']:
        if task['id'] not in REOPEN:
            continue
        number = len(before['tasks'][task['id']]['attempts']) + 1
        task.update(maximum_attempts=number,
            deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] = [*task.get('inputs', []), correction['review'], correction['local_review']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = 'Both unchanged controls, full scoped source/dependency review, one correction; <=516 charged calls including <=2 terminal-service recoveries'
    return result


def validate_response_repair(program, root, *, plan_reference=None):
    if program['execution_refresh']['post_review']['response_repair'].get('account_correction'):
        return validate_account_correction(program, root, plan_reference=plan_reference)
    correction = program['execution_refresh']['post_review']['response_repair']
    require(correction.get('profile') == 'legal-execution-response-repair.v1'
        and correction.get('prior_detours') == 27
        and correction.get('additional_consolidated_revision') == 1
        and correction.get('live_calls_added') == 0
        and correction.get('attempts_reset') is False
        and correction.get('semantic_stage_maximum') == SEMANTIC_STAGE_CALLS
        and correction.get('terminal_recovery_maximum') == 2
        and set(correction.get('reopened_nodes', [])) == set(REOPEN), 'Unreviewed response repair')
    for key in ('review','baseline','local_review','prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root, correction[key])
    old = read(root/correction['prior_program']['path'])
    before = read(root/correction['prior_state']['path'])
    require(not old['execution_refresh']['post_review'].get('response_repair')
        and before['program_hash'] == digest(old), 'Response repair baseline changed')
    require(before['tasks']['semantic-preflight']['status'] in ('BLOCKED','FAILED')
        and len(before['tasks']['semantic-preflight']['attempts']) == 2
        and before['tasks']['continuation-review']['status'] == 'SUCCEEDED',
        'Response repair requires settled second preflight and completion review')
    archives = read(root/correction['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Response archive changed bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archives})
    validate_program(projected, root)
    require(program == expected_program(projected, before, correction, root, plan_reference=plan_reference),
        'Response repair changed unrelated owners, attempts or authority')
    local = read(root/correction['local_review']['path'])
    require(local.get('verdict') == 'PASS' and local.get('provider_calls') == 0,
            'Response repair lacks local review')
    for reference in local['evidence']:
        verify(root, reference)
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    if (ROOT/ACCOUNT/'local-review.json').exists():
        return register_account_correction()
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline = read(ROOT/WORK/'baseline.json')
        archives = {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'], 'Response baseline changed: '+str(path))
        old = read(ROOT/PROGRAM); state = read(ROOT/STATE)
        require(not any(t['status']=='RUNNING' for t in state['tasks'].values()), 'Worker is still running')
        correction = {'profile':'legal-execution-response-repair.v1','prior_detours':27,
            'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
            'user_instruction':'Repair and refresh the current master after each part; continue independent work.',
            'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'local_review':ref(ROOT,WORK/'local-review.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN),'semantic_stage_maximum':SEMANTIC_STAGE_CALLS,
            'terminal_recovery_maximum':2}
        program = expected_program(historical_projection(old,archives),state,correction,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed response/scope repair; earlier attempts retained')
            state['tasks'][tid].pop('result',None)
        state['program_hash'] = digest(program)
        state['events'].append({'task_id':None,'action':'REVIEWED_RESPONSE_REPAIR',
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':correction['review'],'attempts_reset':False})
        mission = historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage = ROOT/WORK/'registration-stage'
        save(stage/'program.json',program); save(stage/'state.json',state)
        program_ref = {'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),execution_refresh=program['execution_refresh'])
        reason = 'Execute the reviewed response/scope correction and one semantic preflight; refresh every result and continue independent ready owners.'
        mission['history'].append({'id':'integration-master-response-repair-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Repaired mandatory response IDs, review scope, repeated event payloads and terminal-service recovery.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['review'],correction['baseline'],correction['local_review']]})
        mission['next_task_reason']=reason; save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':28,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def verification(directory=None):
    program=read(ROOT/PROGRAM); validate_program(program,ROOT)
    correction=program['execution_refresh']['post_review']['response_repair']
    account = correction.get('account_correction')
    if account:
        correction = account
    before=read(ROOT/correction['prior_state']['path']); state=read(ROOT/STATE)
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'], 'Historical attempt changed')
    ledger=read(ROOT/BASE/'live-calls.json'); prior=read(ROOT/correction['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])]==prior['calls'], 'Historical calls changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    value={'profile':'response-repair-verification.v1','old_attempts_preserved':True,'old_calls_preserved':True,
        'calls':len(ledger['calls']),'detours':29 if account else 28,'execution':view['execution'],'ready':view['ready'],
        'running':view['running'],'task_counts':dict(Counter(r['status'] for r in view['tasks'].values())),
        'integration_complete':False,
        '_conclusion':'Current response repair and preserved prior attempts verified; semantic answers and matched effects require separate evidence.'}
    save((directory or ROOT/(ACCOUNT if account else WORK))/'verification.json',value)
    return value


def expected_account_program(old, before, correction, root, *, plan_reference=None):
    result = deepcopy(old)
    result['execution_refresh']['post_review']['response_repair']['account_correction'] = correction
    result['protected_evidence'] += [correction['review'], correction['baseline'],
        correction['local_review'], correction['checkpoints'], plan_reference or ref(root, PLAN)]
    for task in result['tasks']:
        if task['id'] not in REOPEN:
            continue
        number = len(before['tasks'][task['id']]['attempts']) + 1
        task.update(maximum_attempts=number,
            deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] = [*task.get('inputs', []), correction['review'], correction['local_review']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = ('Both unchanged controls; exact retained initial responses; one account/answer '
                'correction and complete fresh review; <=516 charged calls, <=1 remaining terminal recovery')
    return result


def validate_account_correction(program, root, *, plan_reference=None):
    correction = program['execution_refresh']['post_review']['response_repair']['account_correction']
    require(correction.get('profile') == 'legal-requirement-account-correction.v1'
        and correction.get('prior_detours') == 28
        and correction.get('additional_consolidated_revision') == 1
        and correction.get('live_calls_added') == 0
        and correction.get('attempts_reset') is False
        and correction.get('semantic_stage_maximum') == SEMANTIC_STAGE_CALLS
        and correction.get('terminal_recovery_maximum') == 1
        and correction.get('terminal_recovery_used_before') == 1
        and set(correction.get('reopened_nodes', [])) == set(REOPEN), 'Unreviewed account correction')
    for key in ('review','baseline','local_review','prior_program','prior_state','prior_binding',
                'prior_ledger','checkpoints','prior_terminal_recovery'):
        verify(root, correction[key])
    old = read(root/correction['prior_program']['path'])
    before = read(root/correction['prior_state']['path'])
    require(not old['execution_refresh']['post_review']['response_repair'].get('account_correction')
        and before['program_hash'] == digest(old), 'Account correction baseline changed')
    require(before['tasks']['semantic-preflight']['status'] in ('BLOCKED','FAILED')
        and len(before['tasks']['semantic-preflight']['attempts']) == 3
        and before['tasks']['continuation-review']['status'] == 'SUCCEEDED'
        and not any(r['status']=='RUNNING' for r in before['tasks'].values()),
        'Account correction requires settled third preflight and completion review')
    require(len(read(root/correction['prior_ledger']['path'])['calls']) == 739
        and len(read(root/correction['prior_terminal_recovery']['path'])['charges']) == 1,
        'Account correction lost previous charges')
    archives = read(root/correction['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Account archive changed bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in archives})
    validate_program(projected, root)
    require(program == expected_account_program(projected, before, correction, root, plan_reference=plan_reference),
        'Account correction changed unrelated owners, attempts or authority')
    local = read(root/correction['local_review']['path'])
    require(local.get('verdict') == 'PASS' and local.get('provider_calls') == 0,
            'Account correction lacks local review')
    for reference in local['evidence']:
        verify(root, reference)
    checkpoints = read(root/correction['checkpoints']['path'])
    require(set(checkpoints) == {'remote-exception','changed-exception'}, 'Missing original semantic control')
    from legalmath.interpretation.assurance.bounded_checkpoint import retained_response
    for arms in checkpoints.values():
        require(set(arms) == {'partitioned','unpartitioned'}, 'Unmatched retained control arms')
        for reference in arms.values():
            verify(root, reference)
            manifest = read(root/reference['path'])
            dispatch = read(root/manifest['dispatch']['path'])
            for key, row in manifest['calls'].items():
                retained_response(root, reference, key, read(root/row['request']['path']),
                    read(root/row['schema']['path']), dispatch['calls'][key]['identity'], manifest['input_hash'])
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register_account_correction():
    from scripts.legal_integration_post_review import finish_transaction
    journal = ACCOUNT/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline = read(ROOT/ACCOUNT/'baseline.json')
        archives = {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'], 'Account baseline changed: '+str(path))
        old = read(ROOT/PROGRAM); state = read(ROOT/STATE)
        require(not any(t['status']=='RUNNING' for t in state['tasks'].values()), 'Worker is still running')
        correction = {'profile':'legal-requirement-account-correction.v1','prior_detours':28,
            'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
            'user_instruction':'Repair and refresh the current master after each part; continue independent work.',
            'review':ref(ROOT,ACCOUNT_REVIEW),'baseline':ref(ROOT,ACCOUNT/'baseline.json'),
            'local_review':ref(ROOT,ACCOUNT/'local-review.json'),'checkpoints':ref(ROOT,ACCOUNT/'checkpoints.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'prior_terminal_recovery':ref(ROOT,WORK/'live/stages/semantic-preflight/terminal-recovery.json'),
            'reopened_nodes':list(REOPEN),'semantic_stage_maximum':SEMANTIC_STAGE_CALLS,
            'terminal_recovery_maximum':1,'terminal_recovery_used_before':1}
        program = expected_account_program(historical_projection(old,archives),state,correction,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed account correction; earlier attempts retained')
            state['tasks'][tid].pop('result',None)
        state['program_hash'] = digest(program)
        state['events'].append({'task_id':None,'action':'REVIEWED_ACCOUNT_CORRECTION',
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':correction['review'],'attempts_reset':False})
        mission = historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage = ROOT/ACCOUNT/'registration-stage'
        save(stage/'program.json',program); save(stage/'state.json',state)
        program_ref = {'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),execution_refresh=program['execution_refresh'])
        reason = ('Execute the reviewed requirement-account and bounded answer correction from exact retained '
            'initial evidence; refresh every result and continue independent ready owners.')
        mission['history'].append({'id':'integration-master-account-correction-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Repair the rejected account, keep only adverse reviews in correction payload, preserve complete fresh review.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['review'],correction['baseline'],correction['local_review']]})
        mission['next_task_reason']=reason; save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':29,'reopened_nodes':list(REOPEN),'live_calls_added':0}
