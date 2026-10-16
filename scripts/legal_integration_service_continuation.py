"""One finite service-handling amendment in the existing integration master."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program
from scripts.legal_integration_acceptance_revision import historical_projection
from legalmath.interpretation.assurance.bounded_provider import SERVICE_CONTINUATION_POLICY

WORK = Path('artifacts/legal-mission-control/2026-10-14/execution-recovery/service-continuation')
REVIEW = WORK/'review.md'
PREVIOUS = WORK.parent
REOPEN = ('current-binding','semantic-preflight','continuation-review')
USER = 'repair the master program with a better execution handling and close the blocks.'
STAGE_CALLS = 822
MUTATED = {str(PLAN),
    'src/legalmath/interpretation/search/providers.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/bounded_checkpoint.py',
    'src/legalmath/interpretation/assurance/bounded_product.py',
    'scripts/legal_integration_reopening_live.py','scripts/legal_integration_current_live.py',
    'scripts/legal_mission_execution.py','scripts/legal_mission_control.py',
    'scripts/legal_integration_execution_refresh.py'}


def projection_archives(rows):
    # Immutable older revisions keep their original paths. Only changed live
    # source/plan references need a byte-identical historical projection.
    return {(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in rows if r['previous']['path'] in MUTATED}


def mission_archives(rows):
    result=projection_archives(rows)
    result.update({(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in rows if r['previous']['path']==str(PROGRAM)})
    return result


def finish_mission_references():
    """Idempotently finish exact historical pointers after a committed migration."""
    mission=read(ROOT/DOC/'mission.json')
    corrected=historical_projection(mission,mission_archives(read(ROOT/WORK/'baseline.json')['archived']))
    if corrected!=mission:
        save(ROOT/WORK/'mission-before-reference-finish.json',mission)
        save(ROOT/DOC/'mission.json',corrected)
        save(ROOT/WORK/'mission-reference-finish.json',{'profile':'service-registration-reference-finish.v1',
            'before':ref(ROOT,WORK/'mission-before-reference-finish.json'),'after':ref(ROOT,DOC/'mission.json'),
            'scope':'Exact older program hashes now point to byte-identical archived program; current program, attempts and grants unchanged.'})


def checkpoints(*, destination=WORK, predecessor=PREVIOUS, held_corrected=('changed-exception',)):
    from legalmath.interpretation.assurance.bounded_checkpoint import continuation_key, verify_no_output_receipts
    from legalmath.interpretation.assurance.bounded_references import prepare
    receipts = {}
    for path in (ROOT/BASE/'provider-evidence').glob('*/manifest.json'):
        value = read(path)
        if value['allowance_slot'] > 1019:
            receipts.setdefault(value['request_hash'],[]).append(ref(ROOT,path))
    output = {}; census = []
    for name in ('remote-exception','changed-exception','missing-incorporated-rule'):
        output[name] = {}
        for arm in ('unpartitioned','partitioned'):
            directory = predecessor/'live/semantic-control'/name/arm/'calls'
            dispatch = read(ROOT/directory/'dispatch.json')
            require(not any(r['status']=='RESERVED' for r in dispatch['calls'].values()),
                'Uncertain predecessor requires reconciliation')
            calls = {}; failures = {}; held = []
            for key,row in dispatch['calls'].items():
                require(continuation_key(key),'Unknown predecessor phase: '+key)
                references = {k:ref(ROOT,directory/key/(k+'.json')) for k in ('request','schema','result')}
                if row['status']=='VALIDATED':
                    calls[key]=references
                    continue
                require(row['status']=='FAILED','Unknown predecessor status')
                request,schema = (read(ROOT/references[k]['path']) for k in ('request','schema'))
                wire = prepare(request,schema)['request']
                matches = receipts.get(digest(wire),[])
                require(matches,'Failed request has no retained wire receipt: '+key)
                recovery = {'result':references['result'],'receipts':matches}
                verify_no_output_receipts(ROOT,recovery,request,schema)
                failures[key]=recovery
                if name in held_corrected and not key.startswith('corrected-'):
                    held.append(key);calls[key]=references
            manifest = {'profile':'bounded-full-checkpoint.v3','input_hash':dispatch['input_hash'],
                'dispatch':ref(ROOT,directory/'dispatch.json'),'calls':calls,
                'recoverable_failures':failures,'held_failures':held,
                'scope':'Exact settled results including corrections and adverse reviews; held failed inputs preserve completed correction population; not a fresh replication.'}
            target = destination/'checkpoints'/name/(arm+'.json')
            save(ROOT/target,manifest);output[name][arm]=ref(ROOT,target)
            census.append({'case':name,'arm':arm,'validated':sum(r['status']=='VALIDATED' for r in dispatch['calls'].values()),
                'held_failed':held,'recoverable_missing':[k for k in failures if k not in held]})
    save(ROOT/destination/'checkpoints.json',output)
    save(ROOT/destination/'checkpoint-census.json',census)
    return census


def expected_program(old,before,revision,root,*,plan_reference=None):
    result=deepcopy(old);result['service_continuation']=revision
    result['protected_evidence'] += [revision[k] for k in ('review','baseline','local_review','checkpoints')]
    result['protected_evidence'].append(plan_reference or ref(root,PLAN))
    for task in result['tasks']:
        if task['id'] not in REOPEN:continue
        number=len(before['tasks'][task['id']]['attempts'])+1
        task.update(maximum_attempts=number,deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] += [revision['review'],revision['local_review'],revision['checkpoints']]
        if task['id']=='semantic-preflight':
            task['acceptance']='All three unchanged controls and complete required reviews; exact retained corrections and adverse results; <=822 calls including <=48 replacements; persistent eight-failure outage circuit.'
    return result


def validate_revision(program,root,*,plan_reference=None):
    revision=program['service_continuation']
    require(revision.get('profile')=='integration-service-continuation.v1'
        and revision.get('prior_detours')==31 and revision.get('additional_consolidated_revision')==1
        and revision.get('live_calls_added')==0 and revision.get('attempts_reset') is False
        and revision.get('user_instruction')==USER and revision.get('reopened_nodes')==list(REOPEN)
        and revision.get('service_recovery_policy')==SERVICE_CONTINUATION_POLICY
        and revision.get('semantic_stage_maximum')==STAGE_CALLS, 'Unreviewed service continuation')
    for key in ('review','baseline','local_review','checkpoints','prior_program','prior_state','prior_binding','prior_ledger'):
        verify(root,revision[key])
    old=read(root/revision['prior_program']['path']);before=read(root/revision['prior_state']['path'])
    require(old.get('execution_recovery') and not old.get('service_continuation')
        and before['program_hash']==digest(old),'Wrong service continuation baseline')
    require(before['tasks']['semantic-preflight']['status']=='BLOCKED'
        and len(before['tasks']['semantic-preflight']['attempts'])==6
        and before['tasks']['continuation-review']['status']=='SUCCEEDED'
        and not any(r['status']=='RUNNING' for r in before['tasks'].values()),'Unsettled service baseline')
    require(len(read(root/revision['prior_ledger']['path'])['calls'])==1209,'Lost prior charges')
    archived=read(root/revision['baseline']['path'])['archived']
    for row in archived:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed historical bytes')
        verify(root,row['archive'])
    projected=historical_projection(old,projection_archives(archived))
    validate_program(projected,root)
    require(program==expected_program(projected,before,revision,root,plan_reference=plan_reference),
        'Service continuation changed unrelated owners or resources')
    local=read(root/revision['local_review']['path'])
    require(local.get('verdict')=='PASS' and local.get('provider_calls')==0,'Missing implementation review')
    for evidence in local['evidence']:verify(root,evidence)
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def register():
    if (ROOT/DELAY_WORK/'canary-validation/local-review.json').exists():
        from scripts.legal_integration_canary_validation import register as register_canary
        return register_canary()
    if (ROOT/DELAY_WORK/'local-review.json').exists():
        return register_delay()
    from scripts.legal_integration_post_review import finish_transaction
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            finish_mission_references()
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/WORK/'baseline.json')
        archives=projection_archives(baseline['archived'])
        refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json'):
            require(ref(ROOT,path)['sha256']==refs[str(path)]['sha256'],'Baseline changed: '+str(path))
        old,state=read(ROOT/PROGRAM),read(ROOT/STATE)
        revision={'profile':'integration-service-continuation.v1','prior_detours':31,'additional_consolidated_revision':1,
            'live_calls_added':0,'attempts_reset':False,'user_instruction':USER,
            'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
            'local_review':ref(ROOT,WORK/'local-review.json'),'checkpoints':ref(ROOT,WORK/'checkpoints.json'),
            'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
            'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
            'reopened_nodes':list(REOPEN),'semantic_stage_maximum':STAGE_CALLS,
            'service_recovery_policy':SERVICE_CONTINUATION_POLICY}
        program=expected_program(historical_projection(old,archives),state,revision,ROOT)
        validate_program(program,ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING',reason='Reviewed bounded service continuation; prior results preserved')
            state['tasks'][tid].pop('result',None)
        state['program_hash']=digest(program)
        state['events'].append({'action':'REVIEWED_SERVICE_CONTINUATION','task_id':None,
            'at_utc':datetime.now(timezone.utc).isoformat(),'review':revision['review'],'attempts_reset':False})
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mission_archives(baseline['archived']))
        stage=ROOT/WORK/'registration-stage'
        save(stage/'program.json',program);save(stage/'state.json',state)
        program_ref={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        mission['integration_master'].update(program=program_ref,plan=ref(ROOT,PLAN),
            prerequisite_repair=program['prerequisite_repair'],execution_refresh=program['execution_refresh'],
            execution_recovery=program['execution_recovery'],service_continuation=revision)
        reason='Resume missing service work with exact corrected checkpoints and bounded overload/outage handling; retain adverse results, refresh and continue independent consumers.'
        mission['history'].append({'id':'integration-master-service-continuation-2026-10-14',
            'task_id':'product-contribution','kind':'product_evaluation','outcome':'no_advance',
            'decision':'Reviewed bounded service continuation under the unchanged Sol grant.',
            'next_task':'product-contribution','next_task_reason':reason,
            'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
            'result_evidence':[program_ref,revision['review'],revision['baseline'],revision['local_review']]})
        mission['next_task_reason']=reason;save(stage/'mission.json',mission)
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,{'profile':'legal-master-registration-transaction.v1','status':'PREPARED','writes':writes})
        finish_transaction(ROOT,journal)
    MasterExecution(ROOT,PROGRAM,STATE).sync_mission()
    return {'registered':True,'detours':32,'reopened_nodes':list(REOPEN),'live_calls_added':0}


def verification(directory=None):
    if read(ROOT/PROGRAM).get('account_capacity_repair'):
        from scripts.legal_integration_account_repair import verification as verify_account
        return verify_account(directory)
    if read(ROOT/PROGRAM).get('route_context_repair'):
        from scripts.legal_integration_route_repair import verification as verify_route
        return verify_route(directory)
    if read(ROOT/PROGRAM).get('phased_acquisition_repair'):
        from scripts.legal_integration_phased_repair import verification as verify_phased
        return verify_phased(directory)
    if read(ROOT/PROGRAM).get('canary_validation_repair'):
        from scripts.legal_integration_canary_validation import verification as verify_canary
        return verify_canary(directory)
    if read(ROOT/PROGRAM).get('retry_delay_repair'):
        return verification_delay(directory)
    program=read(ROOT/PROGRAM);validate_program(program,ROOT)
    revision=program['service_continuation'];before=read(ROOT/revision['prior_state']['path'])
    state=read(ROOT/STATE);ledger=read(ROOT/BASE/'live-calls.json');prior=read(ROOT/revision['prior_ledger']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Historical attempts changed')
    require(ledger['calls'][:len(prior['calls'])]==prior['calls'],'Historical charges changed')
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    value={'profile':'service-continuation-verification.v1','old_attempts_preserved':True,'old_calls_preserved':True,
        'calls':len(ledger['calls']),'detours':32,'execution':view['execution'],'ready':view['ready'],
        'running':view['running'],'blocked':view['blocked'],'integration_complete':False,
        '_conclusion':'Exact history and service continuation verified; substantive integration acceptance remains separate.'}
    save((directory or ROOT/WORK)/'verification.json',value)
    return value


# The serializer repair is a finite amendment of this same master. Keep the
# predecessor implementation and every completed/adverse result byte-identical.
DELAY_WORK = WORK/'integer-delay-repair'
DELAY_REVIEW = DELAY_WORK/'review.md'
DELAY_MUTATED = {str(PLAN),
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/bounded_checkpoint.py',
    'scripts/legal_integration_service_continuation.py',
    'scripts/legal_integration_current_live.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py'}


def delay_archives(rows, *, mission=False):
    paths = DELAY_MUTATED | ({str(PROGRAM)} if mission else set())
    return {(r['previous']['path'], r['previous']['sha256']): r['archive']
            for r in rows if r['previous']['path'] in paths}


def delay_checkpoints():
    held = []
    for name in ('remote-exception', 'changed-exception', 'missing-incorporated-rule'):
        result = read(ROOT/WORK/'live/semantic-control'/name/'partitioned/result.json')
        if result['answers']['p14'].get('correction', {}).get('status') == 'REVIEWED':
            held.append(name)
    census = checkpoints(destination=DELAY_WORK, predecessor=WORK, held_corrected=held)
    references = read(ROOT/DELAY_WORK/'checkpoints.json')
    for arms in references.values():
        for arm, reference in arms.items():
            manifest = read(ROOT/reference['path'])
            manifest['missing_only'] = True
            save(ROOT/reference['path'], manifest)
            arms[arm] = ref(ROOT, reference['path'])
    save(ROOT/DELAY_WORK/'checkpoints.json', references)
    missing = sum(len(row['recoverable_missing']) for row in census)
    require(missing > 0, 'No missing request justifies a service continuation')
    require(all(key.startswith('corrected-audit-') for row in census
                for key in row['recoverable_missing']),
            'The narrow delay repair permits missing corrected reviews only')
    save(ROOT/DELAY_WORK/'resume-budget.json', {
        'missing_requests': missing,
        'semantic_stage_maximum': missing + SERVICE_CONTINUATION_POLICY['maximum_replacements'],
        'census': ref(ROOT, DELAY_WORK/'checkpoint-census.json'),
        'scope': 'Exact missing corrected reviews plus finite replacements; no completed response resampling.'})
    return census


def expected_delay_program(old, before, revision, root, *, plan_reference=None):
    result = deepcopy(old)
    result['retry_delay_repair'] = revision
    result['protected_evidence'] += [revision[k] for k in ('review', 'baseline', 'local_review', 'checkpoints', 'resume_budget')]
    result['protected_evidence'].append(plan_reference or ref(root, PLAN))
    for task in result['tasks']:
        if task['id'] not in REOPEN:
            continue
        number = len(before['tasks'][task['id']]['attempts']) + 1
        task.update(maximum_attempts=number,
                    deliverable=str(BASE/task['id']/f'attempt-{number}'/'result.json'))
        task['inputs'] += [revision['review'], revision['local_review'], revision['checkpoints']]
        if task['id'] == 'semantic-preflight':
            task['acceptance'] = ('All three unchanged controls and complete required reviews; retain exact '
                'completed/adverse results; resume only enumerated no-output corrected reviews; '
                f"at most {revision['semantic_stage_maximum']} calls including 48 replacements.")
    return result


def validate_delay_revision(program, root, *, plan_reference=None):
    revision = program['retry_delay_repair']
    require(revision.get('profile') == 'integration-retry-delay-repair.v1'
        and revision.get('prior_detours') == 32 and revision.get('additional_consolidated_revision') == 1
        and revision.get('live_calls_added') == 0 and revision.get('attempts_reset') is False
        and revision.get('user_instruction') == USER and revision.get('reopened_nodes') == list(REOPEN)
        and revision.get('service_recovery_policy') == SERVICE_CONTINUATION_POLICY,
        'Unreviewed retry-delay repair')
    for key in ('review', 'baseline', 'local_review', 'checkpoints', 'resume_budget',
                'prior_program', 'prior_state', 'prior_binding', 'prior_ledger'):
        verify(root, revision[key])
    old = read(root/revision['prior_program']['path'])
    before = read(root/revision['prior_state']['path'])
    baseline = read(root/revision['baseline']['path'])
    budget = read(root/revision['resume_budget']['path'])
    verify(root, budget['census'])
    census = read(root/budget['census']['path'])
    missing = sum(len(row['recoverable_missing']) for row in census)
    require(0 < missing == budget['missing_requests']
        and revision['semantic_stage_maximum'] == budget['semantic_stage_maximum'] == missing + 48
        and revision['semantic_stage_maximum'] <= STAGE_CALLS
        and all(key.startswith('corrected-audit-') for row in census for key in row['recoverable_missing']),
        'Retry continuation changed the enumerated work or stage ceiling')
    require(old.get('service_continuation') and not old.get('retry_delay_repair')
        and before['program_hash'] == digest(old), 'Wrong retry-delay baseline')
    require(before['tasks']['semantic-preflight']['status'] == 'BLOCKED'
        and len(before['tasks']['semantic-preflight']['attempts']) == 7
        and before['tasks']['continuation-review']['status'] == 'SUCCEEDED'
        and not any(row['status'] == 'RUNNING' for row in before['tasks'].values()),
        'Unsettled retry-delay baseline')
    require(len(read(root/revision['prior_ledger']['path'])['calls']) == baseline['calls']
        and baseline['calls'] >= 1209 and baseline['prior_detours'] == 32, 'Lost prior charges')
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    projected = historical_projection(old, delay_archives(baseline['archived']))
    validate_program(projected, root)
    require(program == expected_delay_program(projected, before, revision, root, plan_reference=plan_reference),
        'Retry-delay repair changed unrelated owners or resources')
    local = read(root/revision['local_review']['path'])
    require(local.get('verdict') == 'PASS' and local.get('provider_calls') == 0,
            'Missing retry-delay implementation review')
    for evidence in local['evidence']:
        verify(root, evidence)
    return {task['id']: task['maximum_attempts'] for task in program['tasks']}


def register_delay():
    from scripts.legal_integration_post_review import finish_transaction
    journal = DELAY_WORK/'registration.json'
    with ExitStack() as stack:
        for path in (DOC/'mission.execution.lock', STATE.with_suffix('.lock')):
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            return {'registered': True, 'resumed': True}
        baseline = read(ROOT/DELAY_WORK/'baseline.json')
        refs = {r['previous']['path']: r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC/'mission.json', BASE/'current-binding.json', BASE/'live-calls.json'):
            require(ref(ROOT, path)['sha256'] == refs[str(path)]['sha256'], 'Baseline changed: '+str(path))
        old, state = read(ROOT/PROGRAM), read(ROOT/STATE)
        budget = read(ROOT/DELAY_WORK/'resume-budget.json')
        revision = {'profile': 'integration-retry-delay-repair.v1', 'prior_detours': 32,
            'additional_consolidated_revision': 1, 'live_calls_added': 0, 'attempts_reset': False,
            'user_instruction': USER, 'review': ref(ROOT, DELAY_REVIEW),
            'baseline': ref(ROOT, DELAY_WORK/'baseline.json'),
            'local_review': ref(ROOT, DELAY_WORK/'local-review.json'),
            'checkpoints': ref(ROOT, DELAY_WORK/'checkpoints.json'),
            'resume_budget': ref(ROOT, DELAY_WORK/'resume-budget.json'),
            'prior_program': refs[str(PROGRAM)], 'prior_state': refs[str(STATE)],
            'prior_binding': refs[str(BASE/'current-binding.json')], 'prior_ledger': refs[str(BASE/'live-calls.json')],
            'reopened_nodes': list(REOPEN), 'semantic_stage_maximum': budget['semantic_stage_maximum'],
            'service_recovery_policy': SERVICE_CONTINUATION_POLICY}
        program = expected_delay_program(historical_projection(old, delay_archives(baseline['archived'])),
                                         state, revision, ROOT)
        validate_program(program, ROOT)
        for tid in REOPEN:
            state['tasks'][tid].update(status='PENDING', reason='Reviewed integer-delay repair; exact predecessor results retained')
            state['tasks'][tid].pop('result', None)
        state['program_hash'] = digest(program)
        state['events'].append({'action': 'REVIEWED_RETRY_DELAY_REPAIR', 'task_id': None,
            'at_utc': datetime.now(timezone.utc).isoformat(), 'review': revision['review'], 'attempts_reset': False})
        mission = historical_projection(read(ROOT/DOC/'mission.json'),
                                         delay_archives(baseline['archived'], mission=True))
        stage = ROOT/DELAY_WORK/'registration-stage'
        save(stage/'program.json', program)
        save(stage/'state.json', state)
        program_ref = {'path': str(PROGRAM), 'sha256': ref(ROOT, stage/'program.json')['sha256']}
        master = mission['integration_master']
        master.update(program=program_ref, plan=ref(ROOT, PLAN), retry_delay_repair=revision)
        for key in ('prerequisite_repair', 'execution_refresh', 'execution_recovery', 'service_continuation'):
            master[key] = program[key]
        reason = ('Resume only enumerated missing corrected reviews after integer-delay persistence repair; '
                  'preserve adverse results and continue existing independent descendants after refresh.')
        mission['history'].append({'id': 'integration-master-retry-delay-repair-2026-10-14',
            'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
            'decision': 'Reviewed finite serializer repair and exact service continuation under unchanged Sol grant.',
            'next_task': 'product-contribution', 'next_task_reason': reason,
            'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
            'result_evidence': [program_ref, revision['review'], revision['baseline'], revision['local_review']]})
        mission['next_task_reason'] = reason
        save(stage/'mission.json', mission)
        writes = [{'path': str(path), 'before': ref(ROOT, path), 'replacement': ref(ROOT, stage/name)}
            for path, name in ((PROGRAM, 'program.json'), (STATE, 'state.json'), (DOC/'mission.json', 'mission.json'))]
        save(ROOT/journal, {'profile': 'legal-master-registration-transaction.v1', 'status': 'PREPARED', 'writes': writes})
        finish_transaction(ROOT, journal)
    MasterExecution(ROOT, PROGRAM, STATE).sync_mission()
    return {'registered': True, 'detours': 33, 'reopened_nodes': list(REOPEN), 'live_calls_added': 0}


def verification_delay(directory=None):
    program = read(ROOT/PROGRAM)
    validate_program(program, ROOT)
    revision = program['retry_delay_repair']
    before, state = read(ROOT/revision['prior_state']['path']), read(ROOT/STATE)
    ledger, prior = read(ROOT/BASE/'live-calls.json'), read(ROOT/revision['prior_ledger']['path'])
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Historical attempts changed')
    require(ledger['calls'][:len(prior['calls'])] == prior['calls'], 'Historical charges changed')
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    value = {'profile': 'retry-delay-verification.v1', 'old_attempts_preserved': True,
        'old_calls_preserved': True, 'calls': len(ledger['calls']), 'detours': 33,
        'execution': view['execution'], 'ready': view['ready'], 'running': view['running'],
        'blocked': view['blocked'], 'integration_complete': False,
        '_conclusion': 'Exact histories and integer-delay amendment verified; substantive acceptance remains separate.'}
    save((directory or ROOT/DELAY_WORK)/'verification.json', value)
    return value
