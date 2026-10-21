"""Reviewed completion-only account diagnosis, repair and finite repetition."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl, os, sys
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission

KEY = 'failure_recovery'
WORK = Path('artifacts/legal-mission-control/2026-10-19/failure-recovery')
REVIEW = Path('docs/plans/legal-integration-failure-recovery-2026-10-19.md')
USER = "why isn't there a diagnose-repair and repeat mechanism after failures?  We should have one.  we clealy know the problem and we should retry.   has the run finished?  if so, repair the program, and correct the problems."
REOPEN = ['acquire-p10']
IMPLEMENTATION = {
    'scripts/legal_integration_failure_recovery.py', 'scripts/legal_integration_master.py',
    'scripts/legal_integration_phased_live.py', 'scripts/legal_mission_execution.py',
    'scripts/legal_mission_control.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py',
    'src/legalmath/interpretation/assurance/phased/failure_recovery.py',
    'src/legalmath/interpretation/assurance/bounded_product.py'}


def projection(baseline, *, mission=False):
    allowed = IMPLEMENTATION | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        if task['id'] in REOPEN:
            task['maximum_attempts'] += 1
            task['deliverable'] = str(BASE/task['id']/f"attempt-{task['maximum_attempts']}"/'result.json')
            task['inputs'] += [revision['review'],revision['result']]
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result','recovery')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference or ref(root,PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    r=program[KEY]
    require(r['profile']=='integration-failure-recovery.v1' and r['user_instruction']==USER
        and r['prior_detours']==54 and r['additional_consolidated_revision']==1
        and r['additional_task_attempts']==1 and r['reopened_nodes']==REOPEN
        and r['maximum_passes']==2 and r['maximum_repairs_per_request']==1
        and r['live_calls_added']==0 and r['additional_transport_replacements']==0
        and r['attempts_reset'] is False and r['service_scope_reset'] is False, 'Unreviewed failure recovery')
    for k in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant','recovery'):
        verify(root,r[k])
    require(set(r['implementation'])==IMPLEMENTATION,'Changed failure recovery scope')
    for p in r['implementation'].values(): verify(root,p)
    baseline=read(root/r['baseline']['path'])
    require(baseline['calls']==3161 and baseline['running_owners']==0,'Changed final P10 comparator')
    held={x['previous']['path']:x['archive'] for x in baseline['archived']}
    for x in baseline['archived']:
        require(x['previous']['sha256']==x['archive']['sha256'],'Lost historical bytes')
        verify(root,x['archive'])
    for k,p in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
                ('prior_ledger',BASE/'live-calls.json'),('prior_grant',BASE/'live-grant.json')):
        require(r[k]==held[str(p)],'Changed predecessor '+k)
    old,before=read(root/r['prior_program']['path']),read(root/r['prior_state']['path'])
    require(not old.get(KEY) and before['program_hash']==digest(old)
        and before['tasks']['acquire-p10']['status']=='FAILED'
        and len(before['tasks']['acquire-p10']['attempts'])==9
        and not any(t['status']=='RUNNING' for t in before['tasks'].values()),'Unsettled P10 baseline')
    from legalmath.interpretation.assurance.phased import account_recovery
    checkpoint=read(root/r['recovery']['path'])
    account_recovery.load(root,r['recovery'],checkpoint['input_hash'])
    require(checkpoint['predecessor_recovery']==old['settled_recovery']['recoveries']['p10']
        and len(checkpoint['failure_recovery']['actions'])==7,'Changed initial repair population')
    result=read(root/r['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['ledger_unchanged']
        and result['production_replay'] and result['legal_acceptance'] is False,'Repair not locally validated')
    for p in result['evidence']:verify(root,p)
    mapping=projection(baseline); projected=historical_projection(old,mapping)
    with historical_evidence(root,mapping):validate_program(projected,root)
    require(program==project_retained_plan(expected_program(projected,r,root,plan_reference=plan_reference),root,plan_reference),
        'Failure recovery changed unrelated authority or graph')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def project_state(before,program,now):
    value=deepcopy(before)
    require(not any(t['status']=='RUNNING' for t in value['tasks'].values()),'Running owner cannot migrate')
    row=value['tasks']['acquire-p10']
    require(row['status']=='FAILED','Successful owner cannot be resampled')
    row.update(status='PENDING',reason='Reviewed bounded diagnosis, correction and repeat; exact successes retained')
    for k in ('result','dispatch_status','prerequisite_evidence','shared_scope'):row.pop(k,None)
    value['program_hash']=digest(program)
    value['events'].append(dict(action='REVIEWED_FAILURE_RECOVERY',task_id='acquire-p10',at_utc=now,
        review=program[KEY]['review'],attempts_reset=False,calls_added=0,additional_task_attempts=1))
    return value


def validate_state_history(program,state,root):
    before=read(root/program[KEY]['prior_state']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Lost prior attempts '+tid)
        if tid not in REOPEN and row['status']!='PENDING':require(state['tasks'][tid]==row,'Changed unrelated owner '+tid)
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])), 'Lost prior veto')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    from unittest.mock import patch
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        initial=read(ROOT/PROGRAM)
        for path in dict.fromkeys((active_live(initial)/'supervisor.lock',WORK/'live/supervisor.lock',LIVE/'supervisor.lock',
                    STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock'))):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            return dict(registered=True,resumed=True)
        baseline=read(ROOT/WORK/'baseline.json');held={x['previous']['path']:x['archive'] for x in baseline['archived']}
        for p in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,p)['sha256']==held[str(p)]['sha256'],'Changed frozen baseline '+str(p))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        r=dict(profile='integration-failure-recovery.v1',user_instruction=USER,work=str(WORK),
            prior_detours=54,additional_consolidated_revision=1,additional_task_attempts=1,reopened_nodes=REOPEN,
            maximum_passes=2,maximum_repairs_per_request=1,live_calls_added=0,additional_transport_replacements=0,
            attempts_reset=False,service_scope_reset=False,baseline=ref(ROOT,WORK/'baseline.json'),
            review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),recovery=ref(ROOT,WORK/'recovery-p10.json'),
            implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')],prior_grant=held[str(BASE/'live-grant.json')])
        program=expected_program(historical_projection(old,projection(baseline)),r,ROOT)
        validate_program(program,ROOT)
        now=datetime.now(timezone.utc).isoformat();state=project_state(before,program,now)
        stage=WORK/'registration-stage';save(ROOT/stage/'program.json',program);save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        from scripts.legal_integration_settled_recovery import candidate_binding
        # Use the established binding constructor with this amendment's references.
        adapted=deepcopy(program);adapted['settled_recovery']={**r,'recoveries':{'p10':r['recovery']}}
        binding=candidate_binding(adapted,pointer,baseline)
        binding.update(user_instruction=USER,review=r['review'])
        binding['bindings'] += [ref(ROOT,REVIEW),r['recovery']]
        save(ROOT/stage/'binding.json',binding)
        targets={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text,original_bytes=Path.read_text,Path.read_bytes
        def staged_text(path,*a,**kw):return original_text(targets.get(path,path),*a,**kw)
        def staged_bytes(path,*a,**kw):return original_bytes(targets.get(path,path),*a,**kw)
        with patch.object(Path,'read_text',staged_text),patch.object(Path,'read_bytes',staged_bytes):
            require(len(provider().check()['calls'])==baseline['calls'],'Staged binding changed charges')
        mission=historical_projection(read(ROOT/DOC/'mission.json'),projection(baseline,mission=True))
        master=mission['integration_master']
        for k in master:
            if k in program and isinstance(program[k],dict) and program[k].get('profile'):master[k]=deepcopy(program[k])
        master.update(program=pointer,plan=ref(ROOT,PLAN),**{KEY:r})
        reason='Run bounded P10 failure recovery, diagnose after every pass, and drain independently ready original nodes. Preserve all prior calls, source gaps, attempts and limits.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='integration-master-failure-recovery-2026-10-19',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision='User-authorized one reopened P10 attempt with two finite diagnosis/repair passes; no global resource reset.',
            next_task='product-contribution',next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,r['review'],r['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,55))
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name))
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,reopened_nodes=REOPEN,maximum_passes=2,calls_added=0)


def verification():
    p=read(ROOT/PROGRAM);validate_program(p,ROOT);state=read(ROOT/STATE);validate_state_history(p,state,ROOT)
    r=p[KEY];prior=read(ROOT/r['prior_ledger']['path']);current=read(ROOT/BASE/'live-calls.json')
    require(current['calls'][:len(prior['calls'])]==prior['calls'],'Lost prior charges')
    require(ref(ROOT,BASE/'live-grant.json')['sha256']==r['prior_grant']['sha256'],'Grant changed')
    binding=read(ROOT/BASE/'current-binding.json')
    require(binding['program']==ref(ROOT,PROGRAM) and binding['review']==r['review'],'Wrong active binding')
    for pointer in binding['bindings']:verify(ROOT,pointer)
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    result=dict(calls=len(current['calls']),prior_attempts_preserved=True,integration_complete=False,
        **{k:view[k] for k in ('execution','ready','running','blocked')})
    save(ROOT/WORK/'verification.json',result);return result


def completion():
    path=ROOT/WORK/'completion.json'
    if not path.exists():return None
    value=read(path)
    require(value['program']==ref(ROOT,PROGRAM),'Changed recovery completion program')
    verify(ROOT,value['preparation'])
    require(read(ROOT/value['preparation']['path'])['answers']['p10']['status']=='PREPARED','Incomplete recovery preparation')
    return value


def acquire(q,service):
    """Two durable passes in the same owner; diagnosis runs after failure."""
    from scripts import legal_integration_phased_live as live
    from legalmath.interpretation.assurance.phased import account_recovery, failure_recovery
    from legalmath.interpretation.assurance.phased.evidence_store import save_exact
    from legalmath.errors import LegalMathError
    require(q=='p10','Recovery owner is outside reviewed scope')
    r=read(ROOT/PROGRAM)[KEY]
    investigation=live.acquisition(service)
    require(investigation['question_acquisition_complete'][q],'Source recovery incomplete')
    progress_path=ROOT/WORK/'progress.json'
    progress=read(progress_path) if progress_path.exists() else dict(program=ref(ROOT,PROGRAM),passes=[])
    require(progress['program']==ref(ROOT,PROGRAM),'Recovery journal program changed')
    checkpoint=r['recovery']
    for index in range(r['maximum_passes']):
        folder=WORK/'live'/f'pass-{index+1}'
        context=dict(recovery=checkpoint,common_directory=str(folder/'product'),phase_directory=str(folder/'admission'))
        if index < len(progress['passes']):
            row=progress['passes'][index]
            verify(ROOT,row['diagnosis']);checkpoint=row['checkpoint']
            if row['prepared']:return read(ROOT/WORK/'completion.json')['value']
            continue
        diagnosis=read(ROOT/checkpoint['path'])['failure_recovery']
        if not diagnosis['actions']:
            break
        failure=None;result=None
        try:
            result=live.product_route(q,None,service,preparation_only=True,recovery_context=context)
        except Exception as exc:
            failure=dict(error=getattr(exc,'code',type(exc).__name__),reason=str(getattr(exc,'details',None) or exc))
            if isinstance(exc,LegalMathError) and exc.code in ('E_AUTHORITY','E_INTEGRITY'):
                save_exact(ROOT/folder/'continuation-veto.json',failure)
                raise
        directory=ROOT/context['common_directory']
        details_path=directory/'requirement-details.json'
        require(details_path.exists(),'No settled account census; inspect owner evidence')
        successor=account_recovery.build(ROOT,directory/'calls',read(details_path),predecessor=checkpoint,
            complete_details_path=ROOT/folder/'complete-details.json')
        successor=failure_recovery.diagnose(ROOT,successor,provider_directory=BASE,predecessor=checkpoint)
        path=folder/'next-checkpoint.json';save_exact(ROOT/path,successor);pointer=ref(ROOT,path)
        account_recovery.load(ROOT,pointer,successor['input_hash'])
        prepared=bool(result and result['answers'][q].get('status')=='PREPARED')
        report=dict(pass_number=index+1,prepared=prepared,failure=failure,next_actions=successor['failure_recovery'],
            checkpoint=pointer,legal_acceptance=False)
        save_exact(ROOT/folder/'diagnosis.json',report)
        progress['passes'].append(dict(diagnosis=ref(ROOT,folder/'diagnosis.json'),checkpoint=pointer,prepared=prepared))
        save(progress_path,progress);checkpoint=pointer
        save(ROOT/WORK/'next-actions.json',report)
        if prepared:
            value=dict(question=q,preparation=ref(ROOT,directory/'result.json'),
                acquisition=ref(ROOT,live.LIVE/'acquisition/investigation.json'))
            save_exact(ROOT/WORK/'completion.json',dict(program=ref(ROOT,PROGRAM),preparation=value['preparation'],
                common_directory=context['common_directory'],recovery=pointer,value=value))
            return value
    raise LegalMathError('E_DEPENDENCY',details='Bounded P10 recovery settled; exact next actions retained in '+str(WORK/'next-actions.json'))


def worker():
    """Keep the fixed master alive across editor disconnection; retain every gate."""
    import subprocess, os
    from scripts.legal_mission_execution import process_identity
    directory=ROOT/WORK/'execution';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(directory/'worker.json',dict(process=process_identity(os.getpid()),program=ref(ROOT,PROGRAM)))
        commands=[['.venv-context/bin/python','scripts/legal_integration_master.py','live'],
            ['.venv/bin/python','scripts/legal_mission_control.py','refresh'],
            ['.venv-context/bin/python','scripts/legal_integration_master.py','verify'],
            ['.venv/bin/python','scripts/legal_mission_control.py','status']]
        outcomes=[]
        for index,command in enumerate(commands):
            with (directory/f'{index}-stdout').open('w') as out,(directory/f'{index}-stderr').open('w') as err:
                child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err)
                save(directory/'active-command.json',dict(command=command,process=process_identity(child.pid)))
                code=child.wait()
            row=dict(command=command,exit_code=code,stdout=ref(ROOT,directory/f'{index}-stdout'),stderr=ref(ROOT,directory/f'{index}-stderr'))
            outcomes.append(row);save(directory/'steps.json',outcomes)
        save(directory/'result.json',dict(steps=outcomes,finished_at_utc=datetime.now(timezone.utc).isoformat(),
            integration_complete=False,legal_acceptance=False))


def arm():
    import os,subprocess
    from scripts.legal_mission_execution import process_identity,process_alive
    directory=ROOT/WORK/'execution';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (directory/'armed.json').exists():
            prior=read(directory/'armed.json')
            if process_alive(prior['process']):return prior
            require((directory/'result.json').exists(),'Detached worker outcome is unknown; reconcile before restart')
            return read(directory/'result.json')
        require(read(ROOT/PROGRAM).get(KEY),'Failure recovery is not registered')
        with (directory/'supervisor.log').open('ab') as log:
            child=subprocess.Popen(['.venv-context/bin/python','scripts/legal_integration_failure_recovery.py','_worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        result=dict(process=process_identity(child.pid),program=ref(ROOT,PROGRAM),started_at_utc=datetime.now(timezone.utc).isoformat())
        require(result['process'] is not None,'Detached worker did not start')
        save(directory/'armed.json',result);return result


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['arm','_worker'])
    args=parser.parse_args()
    result=arm() if args.action=='arm' else worker()
    print(json.dumps(result))
