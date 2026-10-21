"""One bounded candidate repair in the existing integration master."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, TOKENIZER, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission

KEY = 'candidate_capacity_retry'
WORK = Path('artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry')
REVIEW = Path('docs/plans/legal-candidate-capacity-retry-2026-10-20.md')
USER = 'you have 1 million tokens.  is that enough?  can we retry?'
DEADLINE = '2026-10-20T18:55:16+00:00'
QUESTIONS = ('p10','evidence','p14','gatecoin')
REOPEN = ['acquire-'+q for q in QUESTIONS]
ATTEMPTS = dict(p10=13,evidence=8,p14=11,gatecoin=14)
OLD = Path('artifacts/legal-mission-control/2026-10-19/synthesis-resolution/live')
IMPLEMENTATION = {
    'scripts/legal_integration_candidate_retry.py','scripts/legal_integration_master.py',
    'scripts/legal_integration_phased_live.py','scripts/legal_mission_control.py',
    'scripts/legal_mission_execution.py','scripts/legal_product_completion.py',
    'src/legalmath/interpretation/assurance/bounded_product.py',
    'src/legalmath/interpretation/assurance/phased/downstream_input.py',
    'src/legalmath/interpretation/assurance/phased/tool_input.py',
    'src/legalmath/interpretation/assurance/phased/product.py',
    'src/legalmath/interpretation/assurance/phased/preparation_diagnosis.py',
    'src/legalmath/interpretation/assurance/phased/prepared_checkpoint.py',
}


def archive_rows(baseline, root=ROOT):
    """Retain the established alias when identical bytes were archived before."""
    binding = next(r['archive'] for r in baseline['archived']
        if r['previous']['path'] == str(BASE/'current-binding.json'))
    verify(root, binding)
    known = {(r['previous']['path'],r['previous']['sha256']):r['archive']
        for r in read(root/binding['path'])['historical_archives']}
    rows = deepcopy(baseline['archived'])
    for row in rows:
        old = known.get((row['previous']['path'],row['previous']['sha256']))
        if old is not None:
            require(old['sha256']==row['archive']['sha256'], 'Historical alias changed bytes')
            verify(root, old)
            row['archive'] = old
    return rows


def projection(baseline, *, mission=False, root=ROOT):
    allowed=IMPLEMENTATION | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in archive_rows(baseline,root) if r['previous']['path'] in allowed],mission=mission)


def expected_program(old,revision,root,*,plan_reference=None):
    value=deepcopy(old)
    for task in value['tasks']:
        if task['id'] in REOPEN:
            task['maximum_attempts']+=1
            task['deliverable']=str(BASE/task['id']/f"attempt-{task['maximum_attempts']}"/'result.json')
            task['inputs'] += [revision['review'],revision['result']]
    value[KEY]=revision
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result')]
    value['protected_evidence'] += list(revision['implementation'].values())+list(revision['checkpoints'].values())
    value['protected_evidence'].append(plan_reference or ref(root,PLAN))
    return value


def validate_revision(program,root,*,plan_reference=None):
    r=program[KEY]
    require(r['profile']=='integration-candidate-capacity-retry.v1' and r['user_instruction']==USER
        and r['prior_detours']==58 and r['additional_consolidated_revision']==1
        and r['additional_task_attempts']==1 and r['reopened_nodes']==REOPEN
        and r['live_calls_added']==r['additional_transport_replacements']==0
        and r['attempts_reset'] is False and r['service_scope_reset'] is False,
        'Unreviewed candidate retry')
    for k in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant'):
        verify(root,r[k])
    require(set(r['implementation'])==IMPLEMENTATION and set(r['checkpoints'])==set(QUESTIONS),
        'Changed candidate retry scope')
    for p in [*r['implementation'].values(),*r['checkpoints'].values()]: verify(root,p)
    baseline=read(root/r['baseline']['path'])
    require(baseline['calls']==3447 and baseline['prior_detours']==58 and baseline['running_owners']==0,
        'Changed candidate baseline')
    held={x['previous']['path']:x['archive'] for x in baseline['archived']}
    for x in baseline['archived']:
        require(x['previous']['sha256']==x['archive']['sha256'],'Changed historical bytes')
        verify(root,x['archive'])
    for k,p in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
        ('prior_ledger',BASE/'live-calls.json'),('prior_grant',BASE/'live-grant.json')):
        require(r[k]==held[str(p)],'Lost candidate predecessor '+k)
    old,before=read(root/r['prior_program']['path']),read(root/r['prior_state']['path'])
    require(old.get('synthesis_resolution') and not old.get(KEY) and before['program_hash']==digest(old)
        and not any(t['status']=='RUNNING' for t in before['tasks'].values()),'Unsettled predecessor')
    require(program['deadline_utc']==old['deadline_utc']==DEADLINE
        and program['global_call_ceiling']==old['global_call_ceiling']
        and read(root/r['prior_grant']['path'])['maximum_calls']==8100,'Changed global authority')
    for q in QUESTIONS:
        row=before['tasks']['acquire-'+q]
        require(row['status']=='FAILED' and len(row['attempts'])==ATTEMPTS[q],'Changed exhausted owner')
        checkpoint=read(root/r['checkpoints'][q]['path'])
        require(checkpoint['question']==q and checkpoint['result']==ref(root,OLD/q/'product/result.json'),
            'Different completed preparation')
    result=read(root/r['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['ledger_unchanged']
        and result['legal_acceptance'] is False,'Candidate repair not validated')
    for p in result['evidence']: verify(root,p)
    for name in ('replay.json','checkpoint-replay.json','criticism-probe.json','run-manifest.json',
            'tests.xml','product-regressions.xml'):
        require(ref(root,WORK/name) in result['evidence'], 'Missing candidate repair evidence: '+name)
    candidates=read(root/WORK/'replay.json')
    prepared=read(root/WORK/'checkpoint-replay.json')
    require(candidates['verdict']==prepared['verdict']=='PASS'
        and candidates['provider_calls']==prepared['provider_calls']==0
        and set(candidates['reports'])==set(prepared['reports'])==set(QUESTIONS),
        'Incomplete production replay')
    for q in QUESTIONS:
        require(candidates['reports'][q]['fits'] and candidates['reports'][q]['lossless_roundtrip']
            and candidates['reports'][q]['actual_request_identity_matches']
            and prepared['reports'][q]['baseline_prepared'] and prepared['reports'][q]['findings_unchanged'],
            'Unvalidated original question: '+q)
    mapping=projection(baseline,root=root)
    with historical_evidence(root,mapping): validate_program(old,root)
    expected=expected_program(historical_projection(old,mapping),r,root,plan_reference=plan_reference)
    require(program==project_retained_plan(expected,root,plan_reference),'Changed unrelated program authority')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def project_state(before,program,now):
    value=deepcopy(before)
    require(not any(t['status']=='RUNNING' for t in value['tasks'].values()),'Running owner cannot migrate')
    for tid in REOPEN:
        row=value['tasks'][tid]
        require(row['status']=='FAILED','Successful owner cannot be resampled')
        row.update(status='PENDING',reason='Reuse completed preparation; retry only missing optional candidates and criticism')
        for k in ('result','dispatch_status','prerequisite_evidence','shared_scope'): row.pop(k,None)
    value['program_hash']=digest(program)
    value['events'].append(dict(action='REVIEWED_CANDIDATE_CAPACITY_RETRY',task_id=None,at_utc=now,
        review=program[KEY]['review'],attempts_reset=False,calls_added=0))
    return value


def validate_state_history(program,state,root):
    before=read(root/program[KEY]['prior_state']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'],'Lost prior attempt '+tid)
        if tid not in REOPEN and row['status']!='PENDING': require(state['tasks'][tid]==row,'Changed unrelated owner '+tid)
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])),
        'Lost prior veto')
    prior=before.get('resolved_continuation_vetoes',[])
    require(state.get('resolved_continuation_vetoes',[])[:len(prior)]==prior,'Lost prior resolved veto')


def build_checkpoints():
    from legalmath.interpretation.assurance.phased.prepared_checkpoint import PROFILE
    for q in QUESTIONS:
        source=OLD/q/'product'
        result=read(ROOT/source/'result.json')
        journal=read(ROOT/source/'calls/dispatch.json')
        value=dict(profile=PROFILE,question=q,input_hash=result['input_hash'],result=ref(ROOT,source/'result.json'),
            details=ref(ROOT,source/'requirement-details.json'),source_store=ref(ROOT,source/'source-store.json'),
            journal=ref(ROOT,source/'calls/dispatch.json'),
            representation=ref(ROOT,source/('synthesis-representation-'+q+'.json')),
            call_results={k:ref(ROOT,source/'calls'/k/'result.json') for k in journal['calls']},levels=[])
        levels=sorted((ROOT/source).glob('reduction-'+q+'-*-membership.json'),
            key=lambda p:int(p.name.removesuffix('-membership.json').rsplit('-',1)[1]))
        for p in levels:
            value['levels'].append(dict(membership=ref(ROOT,p),
                result=ref(ROOT,p.with_name(p.name.replace('-membership.json','.json')))))
        require(value['levels'],'No completed synthesis lineage')
        save(ROOT/WORK/'checkpoints'/(q+'.json'),value)
    return dict(checkpoints=4,provider_calls=0)


def acquire(q,service):
    from scripts import legal_integration_phased_live as live
    from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose
    folder=WORK/'live'/q
    result=live.product_route(q,None,service,preparation_only=True)
    diagnosis=diagnose(ROOT,ROOT/folder/'product',q,result=result)
    save(ROOT/folder/'diagnosis.json',diagnosis)
    require(diagnosis['prepared'],q+' required preparation failed; see retained diagnosis')
    return dict(question=q,preparation=ref(ROOT,folder/'product/result.json'),
        optional_failures=diagnosis['optional_incomplete_phases'],
        _conclusion='Completed synthesis reused; baseline ready; optional candidate failures remain explicit.')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live,LIVE
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_settled_recovery import candidate_binding
    from unittest.mock import patch
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        initial=read(ROOT/PROGRAM)
        for p in dict.fromkeys((active_live(initial)/'supervisor.lock',WORK/'live/supervisor.lock',LIVE/'supervisor.lock',
            STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock'))):
            (ROOT/p).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/p).open('a'));fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED':finish_transaction(ROOT,journal)
            require(read(ROOT/PROGRAM).get(KEY,{}).get('work')==str(WORK),'Different retry registered')
            return dict(registered=True,resumed=True)
        baseline=read(ROOT/WORK/'baseline.json')
        held={x['previous']['path']:x['archive'] for x in baseline['archived']}
        for p in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,p)['sha256']==held[str(p)]['sha256'],'Changed frozen baseline '+str(p))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        require(datetime.now(timezone.utc)<datetime.fromisoformat(DEADLINE),'Approved deadline expired')
        r=dict(profile='integration-candidate-capacity-retry.v1',user_instruction=USER,work=str(WORK),
            prior_detours=58,additional_consolidated_revision=1,additional_task_attempts=1,reopened_nodes=REOPEN,
            live_calls_added=0,additional_transport_replacements=0,attempts_reset=False,service_scope_reset=False,
            baseline=ref(ROOT,WORK/'baseline.json'),review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),
            checkpoints={q:ref(ROOT,WORK/'checkpoints'/(q+'.json')) for q in QUESTIONS},
            recoveries=old['synthesis_resolution']['recoveries'],
            implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')],prior_grant=held[str(BASE/'live-grant.json')])
        program=expected_program(historical_projection(old,projection(baseline)),r,ROOT)
        validate_program(program,ROOT)
        now=datetime.now(timezone.utc).isoformat();state=project_state(before,program,now)
        stage=WORK/'registration-stage'
        save(ROOT/stage/'program.json',program);save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        adapted=deepcopy(program);adapted['settled_recovery']=r
        binding=candidate_binding(adapted,pointer,{**baseline,'archived':archive_rows(baseline)})
        prior=read(ROOT/r['prior_binding']['path'])
        binding.update(user_instruction=USER,review=prior['review'],execution_review=r['review'],
            time_extension=prior['time_extension'],effective_deadline_utc=DEADLINE)
        binding['bindings'] += [r['review'],binding['time_extension']]+list(r['checkpoints'].values())
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
        reason=('Reuse all four completed syntheses; repair exact candidate/criticism input transport and '
            'optional tool dependencies. Retry only missing work, preserve failures, and continue each ready '
            'original baseline/tool branch under unchanged global calls, deadline and legal criteria.')
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='integration-master-candidate-retry-2026-10-20',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,r['review'],r['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,59))
        writes=[dict(path=str(p),before=ref(ROOT,p),replacement=ref(ROOT,stage/name)) for p,name in
            ((PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,reopened_nodes=REOPEN,calls_added=0,deadline_utc=DEADLINE)


def verification():
    from legalmath.interpretation.assurance.time_authority import effective_deadline
    program=read(ROOT/PROGRAM)
    validate_program(program,ROOT);validate_state_history(program,read(ROOT/STATE),ROOT)
    r=program[KEY]
    old,current=read(ROOT/r['prior_ledger']['path']),read(ROOT/BASE/'live-calls.json')
    require(current['calls'][:len(old['calls'])]==old['calls'],'Lost prior calls')
    require(ref(ROOT,BASE/'live-grant.json')['sha256']==r['prior_grant']['sha256'],'Changed original grant')
    binding=read(ROOT/BASE/'current-binding.json')
    require(binding['program']==ref(ROOT,PROGRAM) and binding['execution_review']==r['review'],'Wrong retry binding')
    require(effective_deadline(ROOT,ROOT/BASE)==DEADLINE,'Wrong deadline')
    for p in binding['bindings']:verify(ROOT,p)
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    return dict(calls=len(current['calls']),integration_complete=False,**{k:view[k] for k in ('execution','ready','running','blocked')})


def worker():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    directory=ROOT/WORK/'execution';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(directory/'worker.json',dict(process=process_identity(os.getpid()),program=ref(ROOT,PROGRAM)))
        commands=[['.venv-context/bin/python','scripts/legal_integration_master.py','live'],
            ['.venv-context/bin/python','scripts/legal_integration_master.py','run'],
            ['.venv/bin/python','scripts/legal_mission_control.py','refresh'],
            ['.venv-context/bin/python','scripts/legal_integration_master.py','verify']]
        outcomes=[]
        for i,command in enumerate(commands):
            with (directory/f'{i}-stdout').open('w') as out,(directory/f'{i}-stderr').open('w') as err:
                child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err)
                save(directory/'active-command.json',dict(command=command,process=process_identity(child.pid)))
                code=child.wait()
            outcomes.append(dict(command=command,exit_code=code,stdout=ref(ROOT,directory/f'{i}-stdout'),
                stderr=ref(ROOT,directory/f'{i}-stderr')))
        save(directory/'result.json',dict(ended_at_utc=datetime.now(timezone.utc).isoformat(),commands=outcomes))


def arm():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    directory=ROOT/WORK/'execution';directory.mkdir(parents=True,exist_ok=True)
    with (directory/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (directory/'armed.json').exists(),'Candidate continuation already armed')
        require(read(ROOT/PROGRAM).get(KEY,{}).get('work')==str(WORK),'Candidate retry not registered')
        require(datetime.now(timezone.utc)<datetime.fromisoformat(DEADLINE),'Retry deadline expired')
        from scripts.legal_integration_campaign import provider
        provider().check()
        with (directory/'supervisor.log').open('ab') as log:
            child=subprocess.Popen(['.venv-context/bin/python','scripts/legal_integration_candidate_retry.py','_worker'],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        value=dict(process=process_identity(child.pid),at_utc=datetime.now(timezone.utc).isoformat(),
            program=ref(ROOT,PROGRAM))
        save(directory/'armed.json',value)
        return value


if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['checkpoints','register','verify','arm','_worker'])
    action=parser.parse_args().action
    result={'checkpoints':build_checkpoints,'register':register,'verify':verification,'arm':arm,'_worker':worker}[action]()
    print(json.dumps(result,indent=2))
