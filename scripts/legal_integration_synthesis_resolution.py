"""Continue four settled synthesis owners without resampling completed work."""
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
from legalmath.interpretation.assurance.phased.evidence_store import save_exact

KEY = 'synthesis_resolution'
WORK = Path('artifacts/legal-mission-control/2026-10-19/synthesis-resolution')
REVIEW = Path('docs/plans/legal-synthesis-resolution-2026-10-19.md')
USER = 'you have 48 hours more.  continue the execution'
DEADLINE = '2026-10-20T18:55:16+00:00'
QUESTIONS = ('p10', 'evidence', 'p14', 'gatecoin')
REOPEN = ['acquire-' + q for q in QUESTIONS]
ATTEMPTS = dict(p10=12, evidence=7, p14=10, gatecoin=13)
PREDECESSORS = {
    'p10': 'artifacts/legal-mission-control/2026-10-19/synthesis-continuation/live/pass-1/product',
    'evidence': 'artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/live/common/evidence',
    'p14': 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-7/live/common/p14',
    'gatecoin': 'artifacts/legal-mission-control/2026-10-16/integration-repairs/round-6/live/common/gatecoin',
}
IMPLEMENTATION = {
    'scripts/legal_integration_synthesis_resolution.py', 'scripts/legal_integration_master.py',
    'scripts/legal_mission_control.py', 'scripts/legal_mission_execution.py',
    'scripts/legal_integration_phased_live.py', 'scripts/legal_product_completion.py',
    'src/legalmath/interpretation/assurance/bounded_product.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/assurance/phased/downstream_input.py',
    'src/legalmath/interpretation/assurance/phased/grouping.py',
    'src/legalmath/interpretation/assurance/phased/product.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_recovery.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_catalog.py',
    'src/legalmath/interpretation/assurance/phased/synthesis_reassessment.py',
}


def projection(baseline, *, mission=False):
    allowed = IMPLEMENTATION | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        if task['id'] in REOPEN:
            task['maximum_attempts'] += 1
            task['deliverable'] = str(BASE/task['id']/f"attempt-{task['maximum_attempts']}"/'result.json')
            task['inputs'] += [revision['review'], revision['result']]
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline', 'review', 'result')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'] += list(revision['recoveries'].values()) + list(revision['successors'].values())
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    from legalmath.interpretation.assurance.phased import account_recovery, synthesis_recovery, synthesis_catalog
    from legalmath.interpretation.assurance.phased.downstream_input import CAPACITY_PROFILE
    r = program[KEY]
    require(r['profile'] == 'integration-synthesis-resolution.v1' and r['user_instruction'] == USER
        and r['prior_detours'] == 57 and r['additional_consolidated_revision'] == 1
        and r['additional_task_attempts'] == 1 and r['reopened_nodes'] == REOPEN
        and r['maximum_passes'] == 1 and r['live_calls_added'] == 0
        and r['additional_transport_replacements'] == 0
        and r['attempts_reset'] is False and r['service_scope_reset'] is False
        and r['downstream_capacity_profile'] == CAPACITY_PROFILE, 'Unreviewed synthesis resolution')
    for k in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant'):
        verify(root, r[k])
    require(set(r['implementation']) == IMPLEMENTATION, 'Changed synthesis implementation scope')
    for p in r['implementation'].values(): verify(root, p)
    baseline = read(root/r['baseline']['path'])
    require(baseline['calls'] == 3311 and baseline['prior_detours'] == 57
        and baseline['running_owners'] == 0 and set(baseline['implementation']) == IMPLEMENTATION,
        'Changed settled baseline')
    held = {x['previous']['path']:x['archive'] for x in baseline['archived']}
    for x in baseline['archived']:
        require(x['previous']['sha256'] == x['archive']['sha256'], 'Lost historical bytes')
        verify(root, x['archive'])
    for k,p in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
                ('prior_ledger',BASE/'live-calls.json'),('prior_grant',BASE/'live-grant.json')):
        require(r[k] == held[str(p)], 'Changed predecessor '+k)
    old, before = read(root/r['prior_program']['path']), read(root/r['prior_state']['path'])
    require(old.get('synthesis_continuation') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(t['status'] == 'RUNNING' for t in before['tasks'].values()), 'Unsettled synthesis baseline')
    require(program['deadline_utc'] == old['deadline_utc'] == DEADLINE
        and program['synthesis_continuation']['time_extension'] == old['synthesis_continuation']['time_extension'],
        'Changed time authority')
    require(set(r['recoveries']) == set(r['successors']) == set(QUESTIONS), 'Changed successor scope')
    for q in QUESTIONS:
        owner = before['tasks']['acquire-'+q]
        require(owner['status'] == 'FAILED' and len(owner['attempts']) == ATTEMPTS[q], 'Changed settled owner '+q)
        checkpoint = read(root/r['recoveries'][q]['path'])
        account_recovery.load(root, r['recoveries'][q], checkpoint['input_hash'])
        require(not checkpoint['failure_recovery']['actions'], 'Successful accounts scheduled for new calls')
        details = read(root/checkpoint['account_recovery']['details']['path'])
        require(details == read(root/Path(PREDECESSORS[q])/'requirement-details.json')
            and all(x['result']['status'] == 'VALIDATED' for x in details), 'Completed accounts changed')
        successor = synthesis_recovery.composite(root, r['successors'][q], r['recoveries'][q], checkpoint['input_hash'])
        synthesis_catalog.load(root, successor['synthesis'], checkpoint['input_hash'])
    result = read(root/r['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0 and result['ledger_unchanged']
        and result['production_replay'] and result['legal_acceptance'] is False, 'Resolution not locally validated')
    for p in result['evidence']: verify(root,p)
    mapping = projection(baseline)
    with historical_evidence(root,mapping): validate_program(old,root)
    expected = expected_program(historical_projection(old,mapping),r,root,plan_reference=plan_reference)
    require(program == project_retained_plan(expected,root,plan_reference), 'Resolution changed unrelated authority or graph')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def project_state(before, program, now):
    value = deepcopy(before)
    require(not any(t['status'] == 'RUNNING' for t in value['tasks'].values()), 'Running owner cannot migrate')
    for tid in REOPEN:
        row = value['tasks'][tid]
        require(row['status'] == 'FAILED', 'Successful owner cannot be resampled')
        row.update(status='PENDING',reason='Reviewed synthesis resolution; retain every success and execute only missing work')
        for k in ('result','dispatch_status','prerequisite_evidence','shared_scope'): row.pop(k,None)
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='REVIEWED_SYNTHESIS_RESOLUTION',task_id=None,at_utc=now,
        review=program[KEY]['review'],attempts_reset=False,calls_added=0,additional_task_attempts=1))
    return value


def validate_state_history(program,state,root):
    before = read(root/program[KEY]['prior_state']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost prior attempts '+tid)
        if tid not in REOPEN and row['status'] != 'PENDING': require(state['tasks'][tid] == row, 'Changed unrelated owner '+tid)
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])), 'Lost prior veto')
    prior = before.get('resolved_continuation_vetoes', [])
    require(state.get('resolved_continuation_vetoes', [])[:len(prior)] == prior, 'Lost resolved veto history')


def build_checkpoints():
    """No model use. Authenticate account roots, every synthesis level, and saved diagnostics."""
    from scripts.legal_integration_campaign import provider
    from legalmath.interpretation.assurance.bounded_product import BoundDispatch
    from legalmath.interpretation.assurance.phased import (account_recovery, failure_recovery,
        synthesis_recovery, synthesis_catalog, synthesis_reassessment, downstream_instructions)
    from legalmath.interpretation.assurance.integration_contract import read_evidence
    from legalmath.interpretation.assurance.bounded_context import Limits
    from types import SimpleNamespace
    service = provider()
    binding = BoundDispatch(service,ROOT/WORK/'identity',SimpleNamespace(limits=Limits())).provider_binding
    baseline = read(ROOT/WORK/'baseline.json')
    ledger = next(x['archive'] for x in baseline['archived'] if x['previous']['path'] == str(BASE/'live-calls.json'))
    reports = {}
    for q in QUESTIONS:
        folder, old = WORK/'checkpoints'/q, Path(PREDECESSORS[q])
        identity = read(ROOT/old/'identity.json')
        checkpoint = account_recovery.build(ROOT,ROOT/old/'calls',read(ROOT/old/'requirement-details.json'),
            predecessor=identity['requirement_account_recovery'])
        checkpoint = failure_recovery.diagnose(ROOT,checkpoint,provider_directory=BASE,
            predecessor=identity['requirement_account_recovery'])
        require(not checkpoint['failure_recovery']['actions'], 'Completed roots require unexpected repair')
        save_exact(ROOT/folder/'accounts.json',checkpoint)
        accounts = ref(ROOT,folder/'accounts.json')
        manifests = []
        for phase_path in sorted((ROOT/old/'phases').glob('reduction-*/phase.json'),
                key=lambda p:int(p.parent.name.rsplit('-',1)[1])):
            manifest = synthesis_recovery.build(ROOT,ref(ROOT,phase_path),ref(ROOT,old/'calls/dispatch.json'),
                ledger,binding,BASE/'provider-evidence',instruction_profile=downstream_instructions.PROFILE,
                profile=synthesis_recovery.REVIEWED)
            if q in ('p14','gatecoin'):
                key, slot = ('reduce-p14-0-6',3097) if q == 'p14' else ('reduce-gatecoin-0-69',3099)
                diagnostic = ref(ROOT,Path('artifacts/legal-mission-control/2026-10-18/request-variants')/q/'original/manifest.json')
                review = dict(profile='exact-diagnostic-synthesis-review.v1',verdict='PASS',
                    provider_calls_authorized=0,approved={key:diagnostic},plan=ref(ROOT,REVIEW),
                    validation=ref(ROOT,Path('artifacts/legal-mission-control/2026-10-19/synthesis-continuation/diagnostic-response-validation.json')),
                    reason='Unchanged paid original-form response; preserve original failure/refusal and ordinary validators')
                save_exact(ROOT/folder/'diagnostic-review.json',review)
                manifest['diagnostic_reassessments'] = {key:dict(profile=synthesis_reassessment.PROFILE,
                    provider_calls_authorized=0,original_result=manifest['rows'][key]['result'],
                    original_binding=manifest['rows'][key]['reference_binding'],diagnostic=diagnostic,
                    review=ref(ROOT,folder/'diagnostic-review.json'),ledger=ledger,slot=slot,tokenizer=ref(ROOT,TOKENIZER))}
            if q == 'p14':
                keys = ['reduce-p14-0-21','reduce-p14-0-23']
                save_exact(ROOT/folder/'terminal-service-review.json',dict(profile='exact-terminal-synthesis-review.v1',
                    verdict='PASS',provider_calls_authorized=0,maximum_successor_attempts_per_key=1,
                    plan=ref(ROOT,REVIEW),approved={k:manifest['rows'][k]['result'] for k in keys}))
                manifest.update(terminal_499_replays=keys,terminal_service_review=ref(ROOT,folder/'terminal-service-review.json'))
            target = folder/(phase_path.parent.name+'.json')
            save_exact(ROOT/target,manifest)
            pointer = ref(ROOT,target)
            synthesis_recovery.load(ROOT,pointer,checkpoint['input_hash'],provider_binding=binding)
            manifests.append(pointer)
        catalog = dict(profile=synthesis_catalog.PROFILE,input_hash=checkpoint['input_hash'],
            phases=manifests,rows={k:p for p in manifests for k in read(ROOT/p['path'])['rows']},
            instruction_profile=downstream_instructions.PROFILE,
            first_level_instructions=read_evidence(identity['retained_initial'],ROOT).get('profile') != synthesis_recovery.PROFILE)
        save_exact(ROOT/folder/'catalog.json',catalog)
        save_exact(ROOT/folder/'successor.json',dict(profile=synthesis_recovery.PROFILE,
            input_hash=checkpoint['input_hash'],account=accounts,synthesis=ref(ROOT,folder/'catalog.json')))
        reports[q] = dict(accounts=accounts,successor=ref(ROOT,folder/'successor.json'),
            roots=len(read(ROOT/old/'requirement-details.json')),synthesis_calls=len(catalog['rows']))
    save_exact(ROOT/WORK/'checkpoints.json',reports)
    return reports


def completion(q):
    path = ROOT/WORK/'live'/q/'completion.json'
    if not path.exists(): return None
    value = read(path)
    require(value['program'] == ref(ROOT,PROGRAM), 'Changed synthesis completion program')
    verify(ROOT,value['preparation'])
    require(read(ROOT/value['preparation']['path'])['answers'][q]['status'] == 'PREPARED', 'Incomplete synthesis preparation')
    return value


def acquire(q, service):
    from scripts import legal_integration_phased_live as live
    from legalmath.interpretation.assurance.phased import preparation_diagnosis
    require(q in QUESTIONS, 'Owner outside reviewed scope')
    done = completion(q)
    if done is not None: return done['value']
    r = read(ROOT/PROGRAM)[KEY]
    investigation = live.acquisition(service)
    require(investigation['question_acquisition_complete'][q], 'Source acquisition incomplete')
    folder = WORK/'live'/q
    result = None
    failure = None
    try:
        result = live.product_route(q,None,service,preparation_only=True)
    except Exception as exc:
        failure = exc
    diagnosis = preparation_diagnosis.diagnose(ROOT,ROOT/folder/'product',q,result=result,exception=failure)
    save_exact(ROOT/folder/'diagnosis.json',diagnosis)
    save(ROOT/WORK/('next-actions-'+q+'.json'),diagnosis)
    if failure is not None: raise failure
    require(diagnosis['prepared'], q+' synthesis not prepared; retained diagnosis identifies missing work')
    require(read(ROOT/folder/'product/requirement-details.json') ==
        read(ROOT/Path(PREDECESSORS[q])/'requirement-details.json'), 'Completed accounts changed during synthesis')
    value = dict(question=q,preparation=ref(ROOT,folder/'product/result.json'),
        acquisition=ref(ROOT,live.LIVE/'acquisition/investigation.json'))
    save_exact(ROOT/folder/'completion.json',dict(program=ref(ROOT,PROGRAM),preparation=value['preparation'],
        common_directory=str(folder/'product'),recovery=r['recoveries'][q],value=value,legal_acceptance=False))
    return value


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_settled_recovery import candidate_binding
    from legalmath.interpretation.assurance.phased.downstream_input import CAPACITY_PROFILE
    from unittest.mock import patch
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        initial = read(ROOT/PROGRAM)
        for path in dict.fromkeys((active_live(initial)/'supervisor.lock',WORK/'live/supervisor.lock',LIVE/'supervisor.lock',
                    STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock'))):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT,journal)
            require(read(ROOT/PROGRAM).get(KEY,{}).get('work') == str(WORK), 'Different resolution registered')
            return dict(registered=True,resumed=True)
        baseline = read(ROOT/WORK/'baseline.json')
        held = {x['previous']['path']:x['archive'] for x in baseline['archived']}
        for p in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,p)['sha256'] == held[str(p)]['sha256'], 'Changed frozen baseline '+str(p))
        old,before = read(ROOT/PROGRAM),read(ROOT/STATE)
        require(datetime.now(timezone.utc) < datetime.fromisoformat(DEADLINE), 'Approved extension has expired')
        checkpoints = read(ROOT/WORK/'checkpoints.json')
        r = dict(profile='integration-synthesis-resolution.v1',user_instruction=USER,work=str(WORK),
            prior_detours=57,additional_consolidated_revision=1,additional_task_attempts=1,reopened_nodes=REOPEN,
            maximum_passes=1,live_calls_added=0,additional_transport_replacements=0,attempts_reset=False,service_scope_reset=False,
            downstream_capacity_profile=CAPACITY_PROFILE,
            baseline=ref(ROOT,WORK/'baseline.json'),review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),
            recoveries={q:checkpoints[q]['accounts'] for q in QUESTIONS},
            successors={q:checkpoints[q]['successor'] for q in QUESTIONS},
            implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')],prior_grant=held[str(BASE/'live-grant.json')])
        program = expected_program(historical_projection(old,projection(baseline)),r,ROOT)
        validate_program(program,ROOT)
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before,program,now)
        stage = WORK/'registration-stage'
        save(ROOT/stage/'program.json',program)
        save(ROOT/stage/'state.json',state)
        pointer = dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        adapted = deepcopy(program)
        adapted['settled_recovery'] = r
        binding = candidate_binding(adapted,pointer,baseline)
        old_binding = read(ROOT/r['prior_binding']['path'])
        binding.update(user_instruction=USER,review=old_binding['review'],execution_review=r['review'],
            time_extension=old_binding['time_extension'],effective_deadline_utc=DEADLINE)
        binding['bindings'] += [r['review'],binding['time_extension']] + list(r['successors'].values())
        save(ROOT/stage/'binding.json',binding)
        targets = {ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text,original_bytes = Path.read_text,Path.read_bytes
        def staged_text(path,*a,**kw): return original_text(targets.get(path,path),*a,**kw)
        def staged_bytes(path,*a,**kw): return original_bytes(targets.get(path,path),*a,**kw)
        with patch.object(Path,'read_text',staged_text),patch.object(Path,'read_bytes',staged_bytes):
            require(len(provider().check()['calls']) == baseline['calls'], 'Staged binding changed charges')
        mission = historical_projection(read(ROOT/DOC/'mission.json'),projection(baseline,mission=True))
        master = mission['integration_master']
        for k in master:
            if k in program and isinstance(program[k],dict) and program[k].get('profile'):
                master[k] = deepcopy(program[k])
        master.update(program=pointer,plan=ref(ROOT,PLAN),**{KEY:r})
        reason = ('Resume all four pending synthesis owners independently; retain completed accounts and levels, '
            'adopt authenticated paid diagnostics, use finite pair search and the requested 70k/250k downstream bound. '
            'Diagnose and refresh after settlement; unchanged call ceiling, deadline and original product criteria.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-synthesis-resolution-2026-10-19',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,r['review'],r['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,58))
        writes = [dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name))
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,reopened_nodes=REOPEN,deadline_utc=DEADLINE,calls_added=0)


def verification():
    from legalmath.interpretation.assurance.time_authority import effective_deadline
    p = read(ROOT/PROGRAM)
    validate_program(p,ROOT)
    validate_state_history(p,read(ROOT/STATE),ROOT)
    r = p[KEY]
    prior,current = (read(ROOT/x) for x in (r['prior_ledger']['path'],BASE/'live-calls.json'))
    require(current['calls'][:len(prior['calls'])] == prior['calls'], 'Lost prior charges')
    require(ref(ROOT,BASE/'live-grant.json')['sha256'] == r['prior_grant']['sha256'], 'Original grant changed')
    binding = read(ROOT/BASE/'current-binding.json')
    require(binding['program'] == ref(ROOT,PROGRAM) and binding['execution_review'] == r['review'], 'Wrong active binding')
    require(effective_deadline(ROOT,ROOT/BASE) == DEADLINE, 'Wrong effective deadline')
    for pointer in binding['bindings']: verify(ROOT,pointer)
    view = MasterExecution(ROOT,PROGRAM,STATE).summary()
    result = dict(calls=len(current['calls']),prior_attempts_preserved=True,integration_complete=False,deadline_utc=DEADLINE,
        **{k:view[k] for k in ('execution','ready','running','blocked')})
    save(ROOT/WORK/'verification.json',result)
    return result


def worker():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    directory = ROOT/WORK/'execution'
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(directory/'worker.json',dict(process=process_identity(os.getpid()),program=ref(ROOT,PROGRAM)))
        commands = [['.venv-context/bin/python','scripts/legal_integration_master.py','live'],
            ['.venv/bin/python','scripts/legal_mission_control.py','refresh'],
            ['.venv-context/bin/python','scripts/legal_integration_master.py','verify'],
            ['.venv/bin/python','scripts/legal_mission_control.py','status']]
        outcomes = []
        for index,command in enumerate(commands):
            with (directory/f'{index}-stdout').open('w') as out,(directory/f'{index}-stderr').open('w') as err:
                child = subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err)
                save(directory/'active-command.json',dict(command=command,process=process_identity(child.pid)))
                code = child.wait()
            outcomes.append(dict(command=command,exit_code=code,stdout=ref(ROOT,directory/f'{index}-stdout'),stderr=ref(ROOT,directory/f'{index}-stderr')))
            save(directory/'steps.json',outcomes)
        save(directory/'result.json',dict(steps=outcomes,finished_at_utc=datetime.now(timezone.utc).isoformat(),integration_complete=False,legal_acceptance=False))


def arm():
    import subprocess
    from scripts.legal_mission_execution import process_identity,process_alive
    directory = ROOT/WORK/'execution'
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (directory/'armed.json').exists():
            prior = read(directory/'armed.json')
            if process_alive(prior['process']): return prior
            require((directory/'result.json').exists(), 'Worker outcome unknown; reconcile before restart')
            return read(directory/'result.json')
        verification()
        with (directory/'supervisor.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python','scripts/legal_integration_synthesis_resolution.py','_worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        result = dict(process=process_identity(child.pid),program=ref(ROOT,PROGRAM),started_at_utc=datetime.now(timezone.utc).isoformat())
        require(result['process'] is not None, 'Detached worker did not start')
        save(directory/'armed.json',result)
        return result


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['checkpoints','arm','_worker'])
    args = parser.parse_args()
    print(json.dumps({'checkpoints':build_checkpoints,'arm':arm,'_worker':worker}[args.action]()))
