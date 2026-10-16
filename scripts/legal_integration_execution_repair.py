"""One failure-triggered correction inside the existing execution refresh."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_integration_execution_refresh import WORK as PARENT, USER
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = PARENT / 'post-review'
REVIEW = WORK / 'review.md'
REOPEN = ('current-binding', 'semantic-preflight', 'continuation-review')
SEMANTIC_CASE_CALLS = 256
SEMANTIC_STAGE_CALLS = 2 * (SEMANTIC_CASE_CALLS + 2)


def expected_program(old, before, correction, root, *, plan_reference=None):
    result = deepcopy(old)
    result['execution_refresh']['post_review'] = correction
    result['protected_evidence'] += [correction['review'], correction['baseline'], plan_reference or ref(root, PLAN)]
    for task in result['tasks']:
        if task['id'] not in REOPEN:
            continue
        number = len(before['tasks'][task['id']]['attempts']) + 1
        task.update(maximum_attempts=number,
            deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] = [*task.get('inputs', []), correction['review']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = 'Both unchanged synthetic controls, full source/dependency review, one correction; <=516 calls'
        elif task['id'] == 'continuation-review':
            # This is a completion dependency: a failed preflight still needs a
            # result assessment. It does not block the live control itself.
            task['after'] = list(dict.fromkeys([*task['after'], 'semantic-preflight']))
    return result


def validate_repair(program, root, *, plan_reference=None):
    if program['execution_refresh']['post_review'].get('response_repair'):
        from scripts.legal_integration_response_repair import validate_response_repair
        return validate_response_repair(program, root, plan_reference=plan_reference)
    if program['execution_refresh']['post_review'].get('binding_fix'):
        from scripts.legal_integration_binding_fix import validate_binding_fix
        return validate_binding_fix(program, root, plan_reference=plan_reference)
    correction = program['execution_refresh']['post_review']
    require(correction.get('profile') == 'legal-execution-refresh-repair.v1'
        and correction.get('prior_detours') == 25
        and correction.get('additional_consolidated_revision') == 1
        and correction.get('live_calls_added') == 0
        and correction.get('attempts_reset') is False
        and correction.get('semantic_stage_maximum') == SEMANTIC_STAGE_CALLS
        and set(correction.get('reopened_nodes', [])) == set(REOPEN), 'Unreviewed execution repair')
    for key in ('review', 'baseline', 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, correction[key])
    old = read(root/correction['prior_program']['path'])
    before = read(root/correction['prior_state']['path'])
    require(not old['execution_refresh'].get('post_review') and before['program_hash'] == digest(old),
            'Unbound or renewed repair baseline')
    require(before['tasks']['semantic-preflight']['status'] in ('BLOCKED', 'FAILED'),
            'Repair lacks a completed failing preflight')
    archives = read(root/correction['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, {(r['previous']['path'], r['previous']['sha256']):r['archive']
                                            for r in archives})
    from scripts.legal_integration_execution_refresh import validate_revision
    from scripts.legal_mission_execution import validate_task_graph
    # The archived, hash-verified program determines its own old plan bytes;
    # the repaired current plan is verified independently below.
    ceilings=validate_revision(projected, root, plan_reference=projected['protected_evidence'][-1])
    validate_task_graph(projected, root, reviewed=ceilings, ceiling_limit=6)
    require(program == expected_program(projected, before, correction, root,
                                        plan_reference=plan_reference),
            'Repair changed unrelated tasks, authority or attempt ceilings')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    if (ROOT/WORK/'binding-fix/baseline.json').exists():
        from scripts.legal_integration_binding_fix import register as register_binding_fix
        return register_binding_fix()
    from scripts.legal_integration_post_review import finish_transaction
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            return {'registered': True, 'resumed': True}
        baseline = read(ROOT/WORK/'baseline.json')
        archives = {(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
        refs = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for item in refs.values(): verify(ROOT,item)
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256'] == refs[str(path)]['sha256'], 'Repair baseline changed: '+str(path))
        old = read(ROOT/PROGRAM); state = read(ROOT/STATE)
        require(not any(t['status']=='RUNNING' for t in state['tasks'].values()), 'Worker is still running')
        correction = {'profile':'legal-execution-refresh-repair.v1', 'prior_detours':25,
            'additional_consolidated_revision':1, 'attempts_reset':False, 'live_calls_added':0,
            'user_instruction':USER, 'review':ref(ROOT,REVIEW), 'baseline':ref(ROOT,WORK/'baseline.json'),
            'prior_program':refs[str(PROGRAM)], 'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')], 'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN), 'semantic_stage_maximum':SEMANTIC_STAGE_CALLS}
        program = expected_program(historical_projection(old,archives),state,correction,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed failure-triggered repair; previous attempts retained')
            state['tasks'][tid].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'task_id':None,'action':'REVIEWED_EXECUTION_REFRESH_REPAIR',
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':correction['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage=ROOT/WORK/'registration-stage';save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),
            execution_refresh=program['execution_refresh'])
        reason='Execute the one reviewed citation/correction/capacity repair; preserve failures and continue independently admitted consumers.'
        mission['history'].append({'id':'integration-master-execution-refresh-repair-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Repair reproduced assertion-schema, correction activation and review-budget defects inside the same master.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['review'],correction['baseline']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
                for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':26,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def verification(directory=None):
    if read(ROOT/PROGRAM)['execution_refresh']['post_review'].get('response_repair'):
        from scripts.legal_integration_response_repair import verification as verify_response
        return verify_response(directory)
    program=read(ROOT/PROGRAM);validate_program(program,ROOT)
    correction=program['execution_refresh']['post_review']
    correction=correction.get('binding_fix',correction)
    before=read(ROOT/correction['prior_state']['path']);state=read(ROOT/STATE)
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'], 'Historical attempt changed')
    ledger=read(ROOT/BASE/'live-calls.json'); prior=read(ROOT/correction['prior_ledger']['path'])
    require(ledger['calls'][:len(prior['calls'])]==prior['calls'], 'Historical calls changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    value={'profile':'execution-refresh-repair-verification.v1','old_attempts_preserved':True,
        'old_calls_preserved':True,'calls':len(ledger['calls']),
        'detours':27 if program['execution_refresh']['post_review'].get('binding_fix') else 26,
        'execution':view['execution'],'ready':view['ready'],'running':view['running'],
        'task_counts':dict(Counter(r['status'] for r in view['tasks'].values())),
        'integration_complete':False,
        '_conclusion':'Repair execution and unchanged historical evidence verified; legal answers and matched effects remain separate criteria.'}
    save((directory or ROOT/WORK)/'verification.json',value)
    return value
