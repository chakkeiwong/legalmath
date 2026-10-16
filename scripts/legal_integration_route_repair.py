"""Same-master route/context repair; preserves settled work and service scope."""
from copy import deepcopy
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import WORK as PRIOR_WORK, archives
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY

WORK = PRIOR_WORK/'route-context-repair'
REVIEW = WORK/'review.md'
USER = 'Continue; repair the master program with better execution handling and close the blocks.'
REOPEN = ('current-binding','semantic-preflight','continuation-review')


def expected_program(old,before,revision,root,*,plan_reference=None):
    value=deepcopy(old)
    value['route_context_repair']=revision
    value['protected_evidence'] += [revision[k] for k in ('review','baseline','local_review','settled','qualification_replay')]
    value['protected_evidence'].append(plan_reference or ref(root,PLAN))
    for task in value['tasks']:
        if task['id'] in revision['reopened_nodes']:
            number=len(before['tasks'][task['id']]['attempts'])+1
            task.update(maximum_attempts=number,deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
            task['inputs'] += [revision['review'],revision['local_review']]
        if task['id']=='semantic-preflight':
            task['acceptance']='Exact retained grouped controls and adverse responses revalidated; complete conditional missing-authority reference accepted after one changed-input request.'
    return value


def validate_revision(program,root,*,plan_reference=None):
    revision=program['route_context_repair']
    require(revision['profile']=='integration-route-context-repair.v1' and
        revision['prior_detours']==35 and revision['additional_consolidated_revision']==1 and
        revision['live_calls_added']==0 and revision['attempts_reset'] is False and
        revision['user_instruction']==USER and revision['reopened_nodes']==list(REOPEN) and
        revision['service_recovery_policy']==SERVICE_CONTINUATION_POLICY and
        revision['new_qualification_logical_calls']==1 and revision['service_scope_reset'] is False,
        'Unreviewed route/context repair')
    for key in ('review','baseline','local_review','settled','qualification_replay',
                'prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root,revision[key])
    before=read(root/revision['prior_state']['path']);old=read(root/revision['prior_program']['path'])
    require(old.get('phased_acquisition_repair') and not old.get('route_context_repair') and
        before['program_hash']==digest(old) and not any(r['status']=='RUNNING' for r in before['tasks'].values()),
        'Unsettled route/context baseline')
    baseline=read(root/revision['baseline']['path'])
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed archive bytes')
        verify(root,row['archive'])
    projected=historical_projection(old,archives(baseline['archived']))
    validate_program(projected,root)
    require(program==expected_program(projected,before,revision,root,plan_reference=plan_reference),
        'Route repair changed unrelated graph or resources')
    settled=read(root/revision['settled']['path'])
    require(settled['supervisor_alive'] is False and settled['reserved_dispatches']==0 and
        settled['charged_calls']==len(read(root/revision['prior_ledger']['path'])['calls']),
        'Unsettled route/context source execution')
    local=read(root/revision['local_review']['path'])
    require(local['verdict']=='PASS' and local['provider_calls']==0,'Local route repair unreviewed')
    for evidence in local['evidence']:verify(root,evidence)
    replay=read(root/revision['qualification_replay']['path'])
    require(replay['valid'] and replay['new_provider_calls']==0 and
        replay['missing_supported_remains_rejected'] and replay['unsupported_rejected'],
        'Retained control decisions changed')
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
        baseline=read(ROOT/WORK/'baseline.json')
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256']==refs[str(path)]['sha256'],'Baseline changed: '+str(path))
        old,state=read(ROOT/PROGRAM),read(ROOT/STATE)
        revision={'profile':'integration-route-context-repair.v1','prior_detours':35,
            'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
            'user_instruction':USER,'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'local_review':ref(ROOT,WORK/'local-review.json'),'settled':ref(ROOT,WORK/'settled.json'),
            'qualification_replay':ref(ROOT,WORK/'qualification-replay.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN),'service_recovery_policy':SERVICE_CONTINUATION_POLICY,
            'new_qualification_logical_calls':1,'service_scope_reset':False}
        program=expected_program(historical_projection(old,archives(baseline['archived'])),state,revision,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed response identity and actual product delegation repair')
            state['tasks'][tid].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'action':'REVIEWED_ROUTE_CONTEXT_REPAIR','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),archives(baseline['archived'],mission=True))
        stage=ROOT/WORK/'registration-stage';save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        master=mission['integration_master'];master.update(program=program_ref,plan=ref(ROOT,PLAN),route_context_repair=revision)
        for key in ('phased_acquisition_repair','canary_validation_repair','retry_delay_repair','service_continuation',
                    'execution_recovery','prerequisite_repair','execution_refresh'):
            master[key]=program[key]
        reason='Preserve completed source work; qualify complete conditional control and run original answers through the actual product entry point.'
        mission['history'].append({'id':'integration-master-route-context-repair-2026-10-15',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Repair plural response identities, incomplete control reference and direct product bypass within the existing master.',
            'next_task':'product-contribution','next_task_reason':reason,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['settled'],revision['local_review']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':36,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def prepare(directory):
    from scripts.legal_integration_campaign import provider
    revision=read(ROOT/PROGRAM)['route_context_repair']
    prior=read(ROOT/revision['prior_binding']['path'])
    require(ref(ROOT,BASE/'current-binding.json')['sha256']==revision['prior_binding']['sha256'],
        'Current binding is not the reviewed predecessor')
    binding=deepcopy(prior);baseline=read(ROOT/revision['baseline']['path'])
    save(directory/'ledger-before.json',read(ROOT/BASE/'live-calls.json'))
    binding.update(user_instruction=USER,review=revision['review'],predecessor=revision['prior_binding'],
        phase_service_predecessor=revision['prior_binding'],
        ledger_before=ref(ROOT,directory/'ledger-before.json'),program=ref(ROOT,PROGRAM),preflight_stage_maximum=4)
    binding['bindings']=[ref(ROOT,p) for p in sorted((ROOT/'src/legalmath').rglob('*.py'))]
    binding['bindings'] += [ref(ROOT,p) for p in sorted((ROOT/'scripts').glob('legal_*.py'))]
    binding['bindings'] += [ref(ROOT,p) for p in (PROGRAM,PLAN,REVIEW,
        Path(read(ROOT/PROGRAM)['prerequisite_repair']['source']['path']),
        BASE/'campaign-routing.toml',Path('requirements-context.lock'),Path('pyproject.toml'))]
    binding['bindings'] += [revision[k] for k in ('baseline','local_review','settled','qualification_replay')]
    binding['bindings'] += [prior['phase_service_scope']]
    old={(r['previous']['path'],r['previous']['sha256']):r for r in prior['historical_archives']}
    for row in baseline['archived']:old[(row['previous']['path'],row['previous']['sha256'])]=row
    binding['historical_archives']=list(old.values())
    # Keep the existing mutable circuit and replacement ledger in place. Neither
    # a new directory nor a new binding reopens a provider outage.
    save(ROOT/BASE/'current-binding.json',binding);provider().check()
    return {'binding':ref(ROOT,BASE/'current-binding.json'),'service_scope_preserved':True,
        '_conclusion':'Actual product route and response repair bound; source work, grant, clock and shared service scope preserved.'}


def verification(directory=None):
    program=read(ROOT/PROGRAM);validate_program(program,ROOT);revision=program['route_context_repair']
    state,before=read(ROOT/STATE),read(ROOT/revision['prior_state']['path'])
    ledger,old=read(ROOT/BASE/'live-calls.json'),read(ROOT/revision['prior_ledger']['path'])
    require(ledger['calls'][:len(old['calls'])]==old['calls'],'Prior charges changed')
    require(all(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts']
        for tid,row in before['tasks'].items()),'Prior attempts changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    result={'profile':'route-context-repair-verification.v1','calls':len(ledger['calls']),
        'detours':36,'prior_calls_preserved':True,'prior_attempts_preserved':True,
        'execution':view['execution'],'ready':view['ready'],'running':view['running'],'blocked':view['blocked'],
        'integration_complete':False,'tools_fully_evaluated':0,
        '_conclusion':'Route repair and historical accounting checked; original matched effects still required.'}
    save((directory or ROOT/WORK)/'verification.json',result)
    return result
