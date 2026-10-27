"""Finite, history-preserving deployment of the reviewed P14 contract fixes."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence, process_alive
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_review_receipt_correction import mapped

HERE = Path('artifacts/legal-mission-control/2026-10-23/p14-deployment')
WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
RUNTIME = HERE/'live'
REVIEW = Path('docs/plans/p14-deployment-and-decisions-2026-10-23.md')
USER = 'you have 200 service-recovery reserve more.   1. create a plan to test and deploy the local fixes.  2.  review the plan.  3. execute the plan.  4.  Analyze the 672 unresolved and 25 reject decisions thoroughly.  propose a plan to handle them.  Review the plan.  execute.'


def implementation(root):
    return read(Path(root)/HERE/'implementation-files.json')


def frozen(root):
    return read(Path(root)/HERE/'baseline.json')


def archives(root, revision):
    return (read(Path(root)/revision['baseline']['path'])['archived'] +
        read(Path(root)/revision['additional_baseline']['path'])['archived'])


def freeze():
    from scripts.legal_review_timeout_correction import verify_orphans
    require(not (ROOT/HERE/'baseline.json').exists(), 'Deployment predecessor already frozen')
    verify_orphans(ROOT, read(ROOT/STATE), ROOT/WORK)
    owner=read(ROOT/WORK/'worker.json')['process']
    require(not process_alive(owner), 'Previous worker remains alive')
    circuit=read(ROOT/WORK/'service/service-circuit.json')
    recovery=read(ROOT/WORK/'service/service-recovery.json')
    ledger=read(ROOT/BASE/'live-calls.json')
    require(circuit['open'] and not circuit.get('half_open_reserved')
        and len(recovery['charges'])==recovery['maximum']==88
        and len(ledger['calls'])==4027 and ledger['maximum']==8100, 'Changed deployment baseline')
    rows=[]
    paths=[p for p in implementation(ROOT) if (ROOT/p).exists()]
    paths += [str(p) for p in (PLAN,PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',
        BASE/'live-calls.json',BASE/'live-grant.json',WORK/'worker.json',
        WORK/'service/service-recovery.json',WORK/'service/service-circuit.json')]
    for relative in dict.fromkeys(paths):
        target=HERE/'before'/relative
        (ROOT/target).parent.mkdir(parents=True,exist_ok=True)
        with (ROOT/target).open('xb') as stream:
            stream.write((ROOT/relative).read_bytes())
        rows.append(dict(previous=ref(ROOT,relative),archive=ref(ROOT,target)))
    save(ROOT/HERE/'baseline.json',dict(settled=True,calls=4027,service_charges=88,
        worker=owner,archived=rows,at_utc=datetime.now(timezone.utc).isoformat()))
    save(ROOT/HERE/'authority.json',dict(profile='review-deployment-user-authority.v1',
        user_instruction=USER,additional_service_recoveries=200,cumulative_service_recoveries=288,
        prior_service_recoveries=88,global_calls_added=0,global_call_ceiling=8100,
        deadline_utc='2026-10-24T02:19:15Z',attempts_reset=False))
    return dict(frozen=True,calls=4027,service_charges=88)


def expected_program(old, revision, root, plan_reference):
    rows=archives(root, revision)
    value=historical_projection(old,mapped(rows))
    repair=value['review_repair']
    repair['deployment']=revision
    repair['service_policy']=revision['service_policy']
    repair['review_assignment_profile']=revision['review_assignment_profile']
    repair['service_prerequisite_profile']=revision['service_prerequisite_profile']
    task=next(t for t in value['tasks'] if t['id']=='baseline-p14')
    require(task['maximum_attempts']==4, 'Changed P14 attempt baseline')
    task.update(maximum_attempts=5,deliverable=str(BASE/'baseline-p14/attempt-5/result.json'))
    task['inputs'] += [revision['review'],revision['result']]
    value['protected_evidence'] += [revision[k] for k in ('review','result','baseline','additional_baseline','authority','budget','checkpoints','decision_plan')]
    value['protected_evidence'] += list(revision['implementation'].values())+[plan_reference]
    return value


def project_state(before, program, now):
    value=deepcopy(before)
    row=value['tasks']['baseline-p14']
    require(row['status']=='FAILED' and len(row['attempts'])==4, 'Changed P14 continuation baseline')
    row.update(status='PENDING',reason='Reviewed contract continuation; reuse 1699 valid reviews and preserve four prior attempts')
    row.pop('result',None)
    value['program_hash']=digest(program)
    value['events'].append(dict(action='REVIEW_CONTRACT_DEPLOYMENT',task_id='baseline-p14',at_utc=now,
        review=program['review_repair']['deployment']['review'],calls_added=0,attempt_additions=1,
        service_replacements_added=200,attempts_reset=False))
    return value


def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_REVIEW_DEPLOYMENT_POLICY
    from legalmath.interpretation.assurance.phased.review_contract import PROFILE as CONTRACT
    from legalmath.interpretation.assurance.phased.service_prerequisite import PROFILE as SERVICE
    root=Path(root)
    rev=program['review_repair']['deployment']
    runtime=RUNTIME
    if rev.get('context_isolation'):
        from scripts import legal_review_context_isolation as isolation
        isolation.validate(program,root)
        runtime=isolation.RUNTIME
    require(rev['profile']=='review-contract-deployment.v1' and rev['user_instruction']==USER
        and rev['runtime']==str(runtime) and rev['calls_added']==0 and rev['prior_detours']==62
        and rev['additional_consolidated_revision']==1 and rev['attempt_additions']=={'baseline-p14':1}
        and rev['service_replacements_added']==200 and rev['service_policy']==SERVICE_REVIEW_DEPLOYMENT_POLICY
        and rev['review_assignment_profile']==CONTRACT and rev['service_prerequisite_profile']==SERVICE,
        'Changed reviewed deployment scope')
    for key in ('review','result','baseline','additional_baseline','authority','budget','checkpoints','decision_plan','prior_program','prior_state','prior_binding'):
        verify(root,rev[key])
    require(set(rev['implementation'])==set(implementation(root)), 'Changed deployment implementation list')
    for pointer in rev['implementation'].values(): verify(root,pointer)
    baseline=read(root/rev['baseline']['path'])
    require(baseline['settled'] and baseline['calls']==4027 and baseline['service_charges']==88,
        'Changed deployment predecessor')
    rows=archives(root,rev)
    require(len({r['previous']['path'] for r in rows})==len(rows), 'Repeated deployment archive path')
    held={r['previous']['path']:r['archive'] for r in rows}
    for row in rows:
        require(row['previous']['sha256']==row['archive']['sha256'], 'Historical deployment bytes changed')
        verify(root,row['archive'])
    for key,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json')):
        require(rev[key]==held[str(path)], 'Wrong deployment predecessor '+key)
    old=read(root/rev['prior_program']['path'])
    require(not old['review_repair'].get('deployment'), 'Repeated deployment allowance')
    with historical_evidence(root,mapped(rows)):
        validate_program(old,root)
    authority=read(root/rev['authority']['path'])
    require(authority['user_instruction']==USER and authority['additional_service_recoveries']==200
        and authority['cumulative_service_recoveries']==288 and authority['prior_service_recoveries']==88
        and authority['global_call_ceiling']==8100 and authority['global_calls_added']==0
        and authority['deadline_utc']=='2026-10-24T02:19:15Z' and authority['attempts_reset'] is False,
        'Changed user recovery authority')
    result=read(root/rev['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and not result['legal_acceptance'],
        'Deployment tests did not pass')
    for pointer in result['evidence']: verify(root,pointer)
    budget=read(root/rev['budget']['path'])
    expected=deepcopy(read(root/old['review_repair']['budget']['path']))
    expected['protected_calls']['service']+=200
    expected['shared_pool']-=200
    expected['service_replacements_remaining']+=200
    expected['amendment']=rev['authority']
    require(budget==expected, 'Changed independent-question budgets')
    require(program==expected_program(old,rev,root,plan_reference), 'Unreviewed graph or authority change')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def validate_history(program,state,root):
    rev=program['review_repair']['deployment']
    if rev.get('context_isolation'):
        from scripts.legal_review_context_isolation import validate_history as check_isolation_history
        check_isolation_history(program,state,root)
    before=read(Path(root)/rev['prior_state']['path'])
    require(state['events'][:len(before['events'])]==before['events'], 'Lost deployment event history')
    for tid,row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']), 'Lost deployment attempt')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()), 'Changed predecessor attempt '+tid)
        if row['status']=='SUCCEEDED': require(current==row,'Successful owner resampled')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),
        'Lost unresolved continuation veto')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_repair_execution import validate_staged_mission
    from scripts.legal_review_timeout_correction import verify_orphans
    from legalmath.interpretation.assurance.bounded_provider import SERVICE_REVIEW_DEPLOYMENT_POLICY
    from legalmath.interpretation.assurance.phased.review_contract import PROFILE as CONTRACT
    from legalmath.interpretation.assurance.phased.service_prerequisite import PROFILE as SERVICE
    journal=HERE/'registration.json'
    with ExitStack() as stack:
        for path in (WORK/'worker.lock',HERE/'worker.lock',WORK/'service/service-worker.lock',
                WORK/'recovered-live/supervisor.lock',WORK/'continued-live/supervisor.lock',
                RUNTIME/'supervisor.lock',STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            finish_transaction(ROOT,journal)
            return dict(registered=True,resumed=True)
        baseline=frozen(ROOT)
        held={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'], 'Predecessor changed: '+str(path))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        verify_orphans(ROOT,before,ROOT/WORK)
        checkpoints=read(ROOT/HERE/'checkpoints.json')
        rev=dict(profile='review-contract-deployment.v1',user_instruction=USER,runtime=str(RUNTIME),
            calls_added=0,prior_detours=62,additional_consolidated_revision=1,attempt_additions={'baseline-p14':1},
            service_replacements_added=200,service_policy=SERVICE_REVIEW_DEPLOYMENT_POLICY,
            review_assignment_profile=CONTRACT,service_prerequisite_profile=SERVICE,
            review=ref(ROOT,REVIEW),result=ref(ROOT,HERE/'local-result.json'),baseline=ref(ROOT,HERE/'baseline.json'),
            additional_baseline=ref(ROOT,HERE/'additional-before.json'),
            decision_plan=ref(ROOT,Path('docs/plans/p14-decision-followup-2026-10-23.md')),
            authority=ref(ROOT,HERE/'authority.json'),budget=ref(ROOT,HERE/'budget.json'),
            checkpoints=ref(ROOT,HERE/'checkpoints.json'),arm_checkpoints=checkpoints['arm_checkpoints'],
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            implementation={p:ref(ROOT,p) for p in implementation(ROOT)})
        program=expected_program(old,rev,ROOT,ref(ROOT,PLAN))
        validate(program,ROOT,ref(ROOT,PLAN))
        now=datetime.now(timezone.utc).isoformat()
        state=project_state(before,program,now)
        validate_history(program,state,ROOT)
        stage=HERE/'registration-stage'
        save(ROOT/stage/'program.json',program)
        save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding=deepcopy(read(ROOT/BASE/'current-binding.json'))
        rows=archives(ROOT,rev)
        binding['bindings']=historical_projection(binding['bindings'],mapped(rows,mission=True))
        previous_service=held[str(WORK/'service/service-recovery.json')]
        previous_circuit=held[str(WORK/'service/service-circuit.json')]
        service=HERE/'service'
        scope=dict(profile='reviewed-shared-phase-service.v1',grant_hash=binding['grant_hash'],review=binding['review'],
            prior_scope=binding['phase_service_scope'],prior_replacements=previous_service,prior_circuit=previous_circuit,
            prior_replacement_count=88,maximum_replacements_including_prior=288,
            authority=rev['authority'],service_recovery_policy=SERVICE_REVIEW_DEPLOYMENT_POLICY)
        from legalmath.interpretation.assurance.phased.evidence_store import save_exact
        save_exact(ROOT/service/'scope.json',scope)
        scope_ref=ref(ROOT,service/'scope.json')
        save_exact(ROOT/service/'service-recovery.json',{**read(ROOT/previous_service['path']),
            'profile':SERVICE_REVIEW_DEPLOYMENT_POLICY['profile'],'maximum':288,
            'stage_hash':scope_ref['sha256'],'predecessor':previous_service})
        save_exact(ROOT/service/'service-circuit.json',{**read(ROOT/previous_circuit['path']),
            'stage_hash':scope_ref['sha256'],'predecessor':previous_circuit})
        binding.update(program=pointer,phase_service_scope=scope_ref,service_recovery_policy=SERVICE_REVIEW_DEPLOYMENT_POLICY,
            execution_budget=rev['budget'],review_deployment_service_predecessor=previous_service,
            review_deployment_authority=rev['authority'],predecessor=rev['prior_binding'])
        binding.pop('phase_service_predecessor',None)
        binding['bindings'] += [pointer,ref(ROOT,PLAN),scope_ref,previous_service,
            *[rev[k] for k in ('review','result','baseline','additional_baseline','authority','budget','checkpoints','decision_plan')],*rev['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in rows
            if (r['previous']['path'],r['previous']['sha256']) not in known]
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapped(rows,mission=True))
        master=mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'):
                master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),review_repair=program['review_repair'])
        reason='Deploy checked review mappings, resume only outstanding P14 reviews with 200 added service recoveries, and continue independent original owners; no legal acceptance claimed.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='p14-contract-deployment-2026-10-23',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,rev['review'],rev['result'],rev['authority']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/HERE/'registration-check.json',validate_staged_mission(ROOT,stage,mission,63))
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,calls_added=0,service_replacements_added=200,attempt_additions={'baseline-p14':1})


def worker_directory():
    if read(ROOT/PROGRAM)['review_repair'].get('optional_quote_validation'):
        from scripts.legal_optional_quote_validation import HERE as quotation
        return quotation
    if read(ROOT/PROGRAM)['review_repair']['deployment'].get('context_isolation'):
        from scripts.legal_review_context_isolation import HERE as successor
        return successor
    return HERE


def worker():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    from scripts.legal_review_repair import live
    directory=worker_directory()
    with (ROOT/directory/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(ROOT/directory/'worker.json',dict(process=process_identity(os.getpid()),started_at_utc=datetime.now(timezone.utc).isoformat()))
        try:
            save(ROOT/directory/'live-result.json',live())
        except BaseException as exc:
            save(ROOT/directory/'worker-error.json',dict(error=type(exc).__name__,reason=str(getattr(exc,'details',None) or exc)))
            raise
        finally:
            steps=[]
            for name,command in [('refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                    ('status',['.venv-context/bin/python','scripts/legal_integration_master.py','status'])]:
                with (ROOT/directory/(name+'.stdout')).open('w') as out,(ROOT/directory/(name+'.stderr')).open('w') as err:
                    code=subprocess.call(command,cwd=ROOT,stdout=out,stderr=err)
                steps.append(dict(command=command,exit_code=code))
            save(ROOT/directory/'finished.json',dict(steps=steps,ended_at_utc=datetime.now(timezone.utc).isoformat(),integration_complete=False))


def arm():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    directory=worker_directory()
    with (ROOT/directory/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=ROOT/directory/'armed.json'
        if path.exists():
            saved=read(path)
            require(process_alive(saved['process']), 'Previous deployment worker ended; inspect before restarting')
            return dict(already_running=True,**saved)
        require(read(ROOT/PROGRAM)['review_repair'].get('deployment'), 'Deployment not registered')
        from scripts.legal_integration_campaign import provider
        provider().check()
        with (ROOT/directory/'worker.log').open('a') as log:
            process=subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(Path(__file__).resolve()),'worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        identity=process_identity(process.pid)
        require(identity is not None,'Deployment worker exited at startup')
        saved=dict(process=identity,armed_at_utc=datetime.now(timezone.utc).isoformat())
        save(path,saved)
        return saved


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','register','arm','worker'])
    args=parser.parse_args()
    print(json.dumps(globals()[args.action](),indent=2))
