"""One zero-call binding correction inside the existing execution repair."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_integration_execution_refresh import WORK as PARENT
from scripts.legal_integration_execution_repair import WORK as REPAIR_WORK
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, validate_task_graph
from scripts.legal_integration_acceptance_revision import historical_projection

WORK = REPAIR_WORK/'binding-fix'
REVIEW = WORK/'review.md'
REOPEN = ('current-binding',)


def expected_program(old, before, correction, root, *, plan_reference=None):
    result=deepcopy(old)
    result['execution_refresh']['post_review']['binding_fix']=correction
    result['protected_evidence'] += [correction['review'],correction['baseline'],plan_reference or ref(root,PLAN)]
    for task in result['tasks']:
        if task['id'] != 'current-binding': continue
        number=len(before['tasks'][task['id']]['attempts'])+1
        task.update(maximum_attempts=number,
            deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs']=[*task.get('inputs',[]),correction['review']]
        task['acceptance']='Corrected current implementation/source/provider binding after zero-call arity refusal; unchanged grant'
    return result


def validate_binding_fix(program, root, *, plan_reference=None):
    correction=program['execution_refresh']['post_review']['binding_fix']
    require(correction.get('profile')=='legal-execution-binding-fix.v1'
        and correction.get('prior_detours')==26
        and correction.get('additional_consolidated_revision')==1
        and correction.get('live_calls_added')==0
        and correction.get('attempts_reset') is False
        and set(correction.get('reopened_nodes',[]))==set(REOPEN), 'Unreviewed binding correction')
    for key in ('review','baseline','prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root,correction[key])
    old=read(root/correction['prior_program']['path']);before=read(root/correction['prior_state']['path'])
    require(old['execution_refresh']['post_review'].get('binding_fix') is None
            and before['program_hash']==digest(old),'Binding correction baseline changed')
    archives=read(root/correction['baseline']['path'])['archived']
    for row in archives:
        require(row['previous']['sha256']==row['archive']['sha256'],'Binding archive changed')
        verify(root,row['archive'])
    mapping={(r['previous']['path'],r['previous']['sha256']):r['archive']
             for r in archives if r['previous']['path'] != str(PLAN)}
    if plan_reference:
        mapping[(str(PLAN),plan_reference['sha256'])]=plan_reference
    projected=historical_projection(old,mapping)
    validate_program(projected,root)
    require(program==expected_program(projected,before,correction,root,
                                      plan_reference=plan_reference or ref(root,PLAN)),
            'Binding correction changed unrelated program fields')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/WORK/'baseline.json'); archives={(r['previous']['path'],r['previous']['sha256']):r['archive']
            for r in baseline['archived'] if r['previous']['path'] != str(PLAN)}
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for item in refs.values():verify(ROOT,item)
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256']==refs[str(path)]['sha256'],'Binding-fix baseline changed: '+str(path))
        old=read(ROOT/PROGRAM);state=read(ROOT/STATE)
        require(not any(t['status']=='RUNNING' for t in state['tasks'].values()),'Worker is running')
        correction={'profile':'legal-execution-binding-fix.v1','prior_detours':26,
            'additional_consolidated_revision':1,'attempts_reset':False,'live_calls_added':0,
            'user_instruction':'Correct the zero-call current binding arity refusal and continue the same master.',
            'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN)}
        program=expected_program(historical_projection(old,archives),state,correction,ROOT)
        validate_binding_fix(program,ROOT)
        state['tasks']['current-binding'].update(status='PENDING',reason='Reviewed zero-call binding correction; previous attempts retained')
        state['tasks']['current-binding'].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'task_id':None,'action':'REGISTERED_BINDING_FIX','at_utc':datetime.now(timezone.utc).isoformat(),
            'review':correction['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives)
        stage=ROOT/WORK/'registration-stage';save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),execution_refresh=program['execution_refresh'])
        reason='Rebind corrected current live code after a zero-call arity refusal; then resume semantic preflight and independent frontier.'
        mission['history'].append({'id':'integration-master-binding-fix-2026-10-14','task_id':'product-contribution',
            'kind':'product_evaluation','outcome':'no_advance','decision':'Corrected current-binding identity after a pre-dispatch zero-call refusal.',
            'next_task':'product-contribution','next_task_reason':reason,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,correction['review'],correction['baseline']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)} for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes});finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':27,'reopened_nodes':list(REOPEN),'live_calls_added':0}
