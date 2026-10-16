"""Consolidated same-master storage, phase, and original-acquisition repair."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_canary_validation import WORK as PREVIOUS_WORK
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY

WORK = PREVIOUS_WORK / 'consolidated-repair'
REVIEW = PREVIOUS_WORK / 'consolidated-repair-review.md'
USER = 'Continue; repair the master program with better execution handling and close the blocks.'
REOPEN = ('current-binding', 'semantic-preflight', 'continuation-review')
ACQUIRE = tuple('acquire-' + q for q in QUESTIONS)


def archives(rows, *, mission=False):
    excluded = {str(STATE), str(BASE/'current-binding.json'), str(BASE/'live-calls.json'), str(DOC/'mission.json')}
    if not mission:
        excluded.add(str(PROGRAM))
    return {(r['previous']['path'], r['previous']['sha256']): r['archive']
            for r in rows if r['previous']['path'] not in excluded}


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value['phased_acquisition_repair'] = revision
    value['protected_evidence'] += [revision[k] for k in ('review','baseline','local_review','census','reconstructed','population')]
    value['protected_evidence'].append(plan_reference or ref(root,PLAN))
    for task in value['tasks']:
        if task['id'] in REOPEN:
            number = len(before['tasks'][task['id']]['attempts']) + 1
            task.update(maximum_attempts=number,deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
            task['inputs'] += [revision['review'],revision['local_review']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = 'New grouped review preserves remote exception, changed rule, missing authority and explicit context continuation; prior successful full controls retained.'
        if task['id'] in ACQUIRE:
            task['requires'] = list(dict.fromkeys(task['requires'] + ['current-binding']))
            task['acceptance'] = 'Same original source population recovered with exact inventory and retained failures; complete source-grounded preparation for this question.'
        if task['id'].startswith(('baseline-', 'tool-')):
            task['requires'] = list(dict.fromkeys(task['requires'] + ['semantic-preflight']))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision=program['phased_acquisition_repair']
    require(revision['profile']=='integration-phased-acquisition-repair.v1'
        and revision['prior_detours']==34 and revision['additional_consolidated_revision']==1
        and revision['live_calls_added']==0 and revision['attempts_reset'] is False
        and revision['reopened_nodes']==list(REOPEN) and revision['user_instruction']==USER
        and revision['service_recovery_policy']==SERVICE_CONTINUATION_POLICY, 'Unreviewed phased repair')
    for key in ('review','baseline','local_review','census','reconstructed','population',
                'prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root,revision[key])
    before=read(root/revision['prior_state']['path'])
    old=read(root/revision['prior_program']['path'])
    require(old.get('canary_validation_repair') and not old.get('phased_acquisition_repair')
        and before['program_hash']==digest(old) and not any(r['status']=='RUNNING' for r in before['tasks'].values()),
        'Unsettled repair baseline')
    require(len(read(root/revision['prior_ledger']['path'])['calls'])==1507,'Lost prior charges')
    baseline=read(root/revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed archived bytes')
        verify(root,row['archive'])
    projected=historical_projection(old,archives(baseline['archived']))
    validate_program(projected,root)
    require(program==expected_program(projected,before,revision,root,plan_reference=plan_reference),
        'Repair changed unrelated graph or resources')
    census=read(root/revision['census']['path'])
    require(census['dispatch_counts']=={'VALIDATED':160,'FAILED':203}
        and census['calls']==1507 and not census['supervisor_alive'],'Unsettled shared acquisition')
    population=read(root/revision['population']['path'])
    require(population['calls']==60 and population['provider_calls']==0,'Changed recovery population')
    local=read(root/revision['local_review']['path'])
    require(local['verdict']=='PASS' and local['provider_calls']==0,'Local repair not reviewed')
    for evidence in local['evidence']:
        verify(root,evidence)
    for tid in ACQUIRE:
        require(len(before['tasks'][tid]['attempts'])==3,'Acquisition attempts changed')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    from scripts.legal_integration_post_review import finish_transaction
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':
                finish_transaction(ROOT,journal)
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/WORK/'baseline.json')
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256']==refs[str(path)]['sha256'],'Baseline changed: '+str(path))
        old,state=read(ROOT/PROGRAM),read(ROOT/STATE)
        revision={'profile':'integration-phased-acquisition-repair.v1', 'prior_detours':34,
            'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
            'user_instruction':USER,'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'local_review':ref(ROOT,WORK/'local-review.json'),
            'census':ref(ROOT,PREVIOUS_WORK/'settled-acquisition/census.json'),
            'reconstructed':ref(ROOT,PREVIOUS_WORK/'settled-acquisition/reconstruction/result.json'),
            'population':ref(ROOT,WORK/'recovery-population.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN),'service_recovery_policy':SERVICE_CONTINUATION_POLICY,
            'semantic_stage_maximum':48,'semantic_case_calls':16,
            'shared_acquisition_failure_preserved':True,'acquisition_attempt_ceiling':4}
        program=expected_program(historical_projection(old,archives(baseline['archived'])),state,revision,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed exact acquisition and bounded phase repair')
            state['tasks'][tid].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'action':'REVIEWED_PHASED_ACQUISITION_REPAIR','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],
            'shared_acquisition_failure':revision['census'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives(baseline['archived'],mission=True))
        stage=ROOT/WORK/'registration-stage'
        save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        master=mission['integration_master']
        master.update(program=program_ref,plan=ref(ROOT,PLAN),phased_acquisition_repair=revision)
        for key in ('canary_validation_repair','retry_delay_repair','service_continuation','execution_recovery',
                    'prerequisite_repair','execution_refresh'):
            master[key]=program[key]
        reason='Qualify grouped review, recover exact original sources, then drain independent answer/tool phases; preserve all prior failures and calls.'
        mission['history'].append({'id':'integration-master-phased-acquisition-repair-2026-10-15',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Consolidated storage, acquisition recovery, phase accounting and review integration repair.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['census'],revision['local_review']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':35,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def verification(directory=None):
    program=read(ROOT/PROGRAM);validate_program(program,ROOT)
    revision=program['phased_acquisition_repair']
    state,before=read(ROOT/STATE),read(ROOT/revision['prior_state']['path'])
    ledger,old=read(ROOT/BASE/'live-calls.json'),read(ROOT/revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])]==old['calls'],'Prior calls changed')
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Prior attempts changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    result={'profile':'phased-acquisition-repair-verification.v1','calls':len(ledger['calls']),
        'detours':35,'prior_calls_preserved':True,'prior_attempts_preserved':True,
        'execution':view['execution'],'ready':view['ready'],'running':view['running'],'blocked':view['blocked'],
        'integration_complete':False,'tools_fully_evaluated':0,
        '_conclusion':'Consolidated repair and prior histories verified; actual answer and matched tool effects remain required.'}
    save((directory or ROOT/WORK)/'verification.json',result)
    return result
