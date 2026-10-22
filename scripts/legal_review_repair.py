"""Adopt and execute the reviewed source-review repair in the existing master."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission
from scripts.legal_integration_candidate_retry import archive_rows
from scripts.legal_integration_common_capacity import repair_targets, checkpoint_refs
from legalmath.interpretation.assurance.phased.review_repair import PROFILE as REVIEW_PROFILE
from legalmath.interpretation.assurance.bounded_provider import SERVICE_REVIEW_REPAIR_POLICY as SERVICE_POLICY

KEY = 'review_repair'
WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
REVIEW = Path('docs/plans/legal-review-repair-2026-10-21.md')
USER = 'review the repair plan.  refresh the master program.  execute the repair plan and continue with the remaining work.'
QUESTIONS = ('p10', 'p14', 'evidence', 'gatecoin')


def validate_budget(budget, prior_ledger, root):
    require(budget['profile'] == 'reviewed-original-question-reserves.v1'
        and budget['ledger_before'] == prior_ledger and budget['launch_authorized'] is True,
        'Budget changed predecessor or authorization')
    ledger = read(root/prior_ledger['path'])
    require(budget['global_remaining'] == ledger['maximum']-len(ledger['calls']) == 4561
        and budget['prior_service_replacements'] == 24
        and budget['service_replacements_remaining'] == 64,
        'Budget changed cumulative allowance')
    require(budget['protected_calls'] == dict(p10=600, p14=600, evidence=600,
        gatecoin=800, service=64, comparisons=144)
        and budget['shared_pool'] == 1753
        and sum(budget['protected_calls'].values())+budget['shared_pool'] == budget['global_remaining']
        and budget['full_matrix_completion_guaranteed'] is False,
        'Budget differs from reviewed independent reserves')


def implementation(root=ROOT):
    return set(read(root/WORK/'implementation-files.json'))


def revision_archives(baseline, root=ROOT):
    extra = read(root/WORK/'supplemental-test-archives.json')
    expected = {
        'tests/tooling/test_outage_refresh_continuation.py': 'a133db8f7af092afa141a80f82bd44112ce039ea428b94bc694cd2952cde33f5',
        'tests/tooling/test_settled_recovery_registration.py': '6e4a60d7c67fab50f2bf5526cc1b18fa0c5a14dcd75c20b6702c173a455b1103',
    }
    require(extra['source_commit'] == '3c3e462acabfde8c62285f4274f0f8c62b90a790'
        and len(extra['archived']) == len(expected)
        and {r['previous']['path']:r['previous']['sha256'] for r in extra['archived']} == expected,
        'Supplemental archive changed predecessor fixture identities')
    for row in extra['archived']:
        require(row['archive']['sha256'] == row['previous']['sha256'], 'Supplement changed fixture bytes')
        verify(root, row['archive'])
    return archive_rows(baseline, root)+extra['archived']


def projection(baseline, *, mission=False, root=ROOT):
    allowed = implementation(root) | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in revision_archives(baseline, root) if r['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        if task['id'] in revision['attempt_additions']:
            task['maximum_attempts'] += revision['attempt_additions'][task['id']]
            task['deliverable'] = str(BASE/task['id']/f"attempt-{task['maximum_attempts']}"/'result.json')
            task['inputs'] += [revision['review'], revision['result']]
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result','budget','supplemental_test_archives')]
    value['protected_evidence'] += list(revision['implementation'].values()) + checkpoint_refs(revision)
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    if revision.get('timeout_correction'):
        from scripts.legal_review_timeout_correction import validate
        return validate(program, root, plan_reference)
    if revision.get('receipt_correction'):
        from scripts.legal_review_receipt_correction import validate
        return validate(program, root, plan_reference)
    require(revision['profile'] == 'integration-source-review-repair.v1' and revision['user_instruction'] == USER
        and revision['review_profile'] == REVIEW_PROFILE and revision['service_policy'] == SERVICE_POLICY
        and revision['prior_detours'] == 61 and revision['additional_consolidated_revision'] == 1
        and revision['live_calls_added'] == 0 and revision['additional_transport_replacements'] == 64
        and revision['attempts_reset'] is False and revision['service_scope_reset'] is False,
        'Unreviewed source-review repair')
    for key in ('baseline','review','result','budget','supplemental_test_archives',
            'prior_program','prior_state','prior_binding','prior_ledger','prior_grant'):
        verify(root, revision[key])
    require(revision['supplemental_test_archives'] == ref(root, WORK/'supplemental-test-archives.json'),
        'Different supplemental fixture archive')
    require(set(revision['implementation']) == implementation(root)
        and set(revision['checkpoints']) == set(QUESTIONS), 'Changed source-review implementation scope')
    for item in [*revision['implementation'].values(), *checkpoint_refs(revision)]: verify(root, item)
    baseline = read(root/revision['baseline']['path'])
    require(baseline['calls'] == 3539 and baseline['prior_detours'] == 61 and baseline['running_owners'] == 0,
        'Changed source-review baseline')
    held = {r['previous']['path']:r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed predecessor bytes')
        verify(root, row['archive'])
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE), ('prior_binding', BASE/'current-binding.json'),
                     ('prior_ledger', BASE/'live-calls.json'), ('prior_grant', BASE/'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost predecessor '+key)
    old, before = read(root/revision['prior_program']['path']), read(root/revision['prior_state']['path'])
    require(old.get('retained_acquisition_repair') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Wrong or active predecessor')
    require(revision['attempt_additions'] == repair_targets(old, before)
        and revision['reopened_nodes'] == sorted(revision['attempt_additions']), 'Changed repair reopening scope')
    require(program['deadline_utc'] == old['deadline_utc'] and program['global_call_ceiling'] == old['global_call_ceiling'],
        'Changed global execution authority')
    result = read(root/revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0 and not result['legal_acceptance'],
        'Repair validation did not pass')
    for item in result['evidence']: verify(root, item)
    budget = read(root/revision['budget']['path'])
    validate_budget(budget, revision['prior_ledger'], root)
    mapping = projection(baseline, root=root)
    with historical_evidence(root, mapping): validate_program(old, root)
    expected = expected_program(historical_projection(old, mapping), revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference), 'Repair changed unrelated graph or authority')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def project_state(before, program, now):
    require(not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Running owner cannot migrate')
    value = deepcopy(before)
    for tid in program[KEY]['reopened_nodes']:
        row = value['tasks'][tid]
        require(row['status'] != 'SUCCEEDED', 'Successful owner cannot be resampled')
        row.update(status='PENDING', reason='Reviewed source-review repair; reuse completed answers and valid decisions')
        for key in ('result','dispatch_status','prerequisite_evidence','shared_scope'): row.pop(key, None)
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='REVIEWED_SOURCE_REVIEW_REPAIR', task_id=None, at_utc=now,
        review=program[KEY]['review'], attempts_reset=False, calls_added=0))
    return value


def validate_state_history(program, state, root):
    if program[KEY].get('timeout_correction'):
        from scripts.legal_review_timeout_correction import validate_history
        validate_history(program, state, root)
    if program[KEY].get('receipt_correction'):
        from scripts.legal_review_receipt_correction import validate_history
        validate_history(program, state, root)
    before = read(root/program[KEY]['prior_state']['path'])
    require(set(state['tasks']) == set(before['tasks']), 'Changed owner set')
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost old attempts '+tid)
        if tid not in program[KEY]['reopened_nodes'] and row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Changed settled owner '+tid)
    require(state['events'][:len(before['events'])] == before['events'], 'Lost event history')
    require(all(v in state.get('continuation_vetoes', []) for v in before.get('continuation_vetoes', [])), 'Lost prior veto')
    prior = before.get('resolved_continuation_vetoes', [])
    require(state.get('resolved_continuation_vetoes', [])[:len(prior)] == prior, 'Lost resolved veto history')


def service_successor(baseline, review):
    held = {r['previous']['path']:r['archive'] for r in baseline['archived']}
    previous = read(ROOT/held[str(BASE/'current-binding.json')]['path'])
    folder = Path(previous['phase_service_scope']['path']).parent
    prior_recovery = held[str(folder/'service-recovery.json')]
    prior_circuit = held[str(folder/'service-circuit.json')]
    recovery, circuit = read(ROOT/prior_recovery['path']), read(ROOT/prior_circuit['path'])
    require(len(recovery['charges']) == recovery['maximum'] == 24 and circuit['open']
        and not circuit.get('half_open_reserved'), 'Unsettled service predecessor')
    service = WORK/'service'
    scope = dict(profile='reviewed-shared-phase-service.v1', grant_hash=previous['grant_hash'], review=review,
        prior_scope=previous['phase_service_scope'], prior_replacements=prior_recovery, prior_circuit=prior_circuit,
        prior_replacement_count=24, maximum_replacements_including_prior=88,
        service_recovery_policy=SERVICE_POLICY, requalification='Exact ended failure, five-minute minimum; no reset.')
    from legalmath.interpretation.assurance.phased.evidence_store import save_exact
    save_exact(ROOT/service/'scope.json', scope)
    pointer = ref(ROOT, service/'scope.json')
    save_exact(ROOT/service/'service-recovery.json', {**recovery, 'profile':SERVICE_POLICY['profile'],
        'maximum':88, 'stage_hash':pointer['sha256'], 'predecessor':prior_recovery})
    save_exact(ROOT/service/'service-circuit.json', {**circuit, 'stage_hash':pointer['sha256'], 'predecessor':prior_circuit})
    return pointer, prior_recovery


def register():
    if read(ROOT/PROGRAM).get(KEY) and (ROOT/WORK/'timeout-correction/result.json').exists():
        from scripts.legal_review_timeout_correction import register as correct
        return correct()
    if read(ROOT/PROGRAM).get(KEY) and (ROOT/WORK/'candidate/result.json').exists():
        from scripts.legal_review_receipt_correction import register as correct
        return correct()
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_settled_recovery import candidate_binding
    from unittest.mock import patch
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        old = read(ROOT/PROGRAM)
        for path in dict.fromkeys((active_live(old)/'supervisor.lock', LIVE/'supervisor.lock',
                STATE.with_suffix('.run.lock'), DOC/'mission.execution.lock', STATE.with_suffix('.lock'))):
            (ROOT/path).parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED': finish_transaction(ROOT, journal)
            require(read(ROOT/PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different repair registered')
            return dict(registered=True, resumed=True)
        baseline = read(ROOT/WORK/'baseline.json')
        held = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC/'mission.json', BASE/'current-binding.json', BASE/'live-calls.json', BASE/'live-grant.json'):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Frozen predecessor changed: '+str(path))
        before = read(ROOT/STATE)
        additions = repair_targets(old, before)
        revision = dict(profile='integration-source-review-repair.v1', user_instruction=USER, work=str(WORK),
            review_profile=REVIEW_PROFILE, service_policy=SERVICE_POLICY, prior_detours=61,
            additional_consolidated_revision=1, live_calls_added=0, additional_transport_replacements=64,
            attempts_reset=False, service_scope_reset=False, attempt_additions=additions, reopened_nodes=sorted(additions),
            baseline=ref(ROOT, WORK/'baseline.json'), review=ref(ROOT, REVIEW), result=ref(ROOT, WORK/'local-result.json'),
            supplemental_test_archives=ref(ROOT, WORK/'supplemental-test-archives.json'),
            budget=ref(ROOT, WORK/'budget.json'), implementation={p:ref(ROOT,p) for p in sorted(implementation())},
            checkpoints={q:ref(ROOT, WORK/'checkpoints'/(q+'.json')) for q in QUESTIONS},
            arm_checkpoints={q:{p.stem:ref(ROOT,p) for p in sorted((ROOT/WORK/'checkpoints/arms'/q).glob('*.json'))} for q in QUESTIONS},
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)], prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')], prior_grant=held[str(BASE/'live-grant.json')])
        program = expected_program(historical_projection(old, projection(baseline)), revision, ROOT)
        validate_program(program, ROOT)
        now = datetime.now(timezone.utc).isoformat()
        stage = WORK/'registration-stage'
        save(ROOT/stage/'program.json', program)
        save(ROOT/stage/'state.json', project_state(before, program, now))
        pointer = dict(path=str(PROGRAM), sha256=ref(ROOT, stage/'program.json')['sha256'])
        adapted = deepcopy(program)
        adapted['settled_recovery'] = dict(revision, recoveries={})
        binding = candidate_binding(adapted, pointer, {**baseline, 'archived':revision_archives(baseline)})
        prior = read(ROOT/revision['prior_binding']['path'])
        scope, predecessor = service_successor(baseline, prior['review'])
        binding.update(user_instruction=USER, review=prior['review'], execution_review=revision['review'],
            time_extension=prior['time_extension'], effective_deadline_utc=prior['effective_deadline_utc'],
            phase_service_scope=scope, service_recovery_policy=SERVICE_POLICY, review_repair_service_predecessor=predecessor)
        binding['execution_budget'] = revision['budget']
        binding.pop('phase_service_predecessor', None)
        binding['bindings'] += [revision['review'], revision['budget'], binding['time_extension'], scope, predecessor] + checkpoint_refs(revision)
        save(ROOT/stage/'binding.json', binding)
        targets = {ROOT/PROGRAM:ROOT/stage/'program.json', ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text, original_bytes = Path.read_text, Path.read_bytes
        with patch.object(Path, 'read_text', lambda path,*a,**k: original_text(targets.get(path,path),*a,**k)), \
             patch.object(Path, 'read_bytes', lambda path,*a,**k: original_bytes(targets.get(path,path),*a,**k)):
            require(len(provider().check()['calls']) == baseline['calls'], 'Staged authority changed charges')
        mission = historical_projection(read(ROOT/DOC/'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'): master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), **{KEY:revision})
        reason = ('Repair source review capacity, invalid verdicts and issue-specific corrections; retain exact answers, '
            'qualify bounded batches and resume original independent work after authenticated service recovery.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-review-repair-2026-10-21', task_id='product-contribution',
            kind='product_evaluation', outcome='no_advance', decision=reason, next_task='product-contribution',
            next_task_reason=reason, recorded_at_utc=now, result_evidence=[pointer,revision['review'],revision['result']]))
        save(ROOT/stage/'mission.json', mission)
        save(ROOT/WORK/'registration-check.json', validate_staged_mission(ROOT, stage, mission, 62))
        writes = [dict(path=str(path), before=ref(ROOT,path), replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'), (STATE,'state.json'), (BASE/'current-binding.json','binding.json'), (DOC/'mission.json','mission.json'))]
        save(ROOT/journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
    return dict(registered=True, calls_added=0, reopened_nodes=sorted(additions), service_replacements_added=64)


def verification():
    program = read(ROOT/PROGRAM)
    runner = MasterExecution(ROOT, PROGRAM, STATE)
    validate_state_history(program, read(ROOT/STATE), ROOT)
    revision = program[KEY]
    previous, current = read(ROOT/revision['prior_ledger']['path']), read(ROOT/BASE/'live-calls.json')
    require(current['calls'][:len(previous['calls'])] == previous['calls'], 'Lost prior charges')
    require(ref(ROOT, BASE/'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Changed original grant')
    binding = read(ROOT/BASE/'current-binding.json')
    require(binding['program'] == ref(ROOT,PROGRAM) and binding['execution_review'] == revision['review']
        and binding['service_recovery_policy'] == SERVICE_POLICY, 'Wrong repair binding')
    for pointer in binding['bindings']: verify(ROOT, pointer)
    prior_service = read(ROOT/binding['review_repair_service_predecessor']['path'])
    current_service = read(ROOT/WORK/'service/service-recovery.json')
    require(current_service['charges'][:24] == prior_service['charges'], 'Lost delayed recovery history')
    view = runner.summary()
    result = dict(calls=len(current['calls']), integration_complete=False,
        **{k:view[k] for k in ('execution','ready','running','blocked')})
    save(ROOT/WORK/'verification.json', result)
    return result


def live():
    from scripts.legal_review_repair_service import recover
    from scripts.legal_integration_phased_live import live as run
    # Drain independent local commands before waiting on service. A returned
    # product failure is a checkpoint, not an implicit end of the program.
    while True:
        execution = MasterExecution(ROOT, PROGRAM, STATE)
        execution.run()
        try:
            state = read(ROOT/STATE)
            running = [r for r in state['tasks'].values() if r['status'] == 'RUNNING']
            if running:
                from scripts.legal_mission_execution import process_alive
                require(execution.program[KEY].get('receipt_correction') and all(
                    r.get('master_live') and not process_alive(r.get('live_supervisor')) for r in running),
                    'A running reservation still has an owner or lacks the reviewed continuation')
                binding = read(ROOT/BASE/'current-binding.json')
                circuit = read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-circuit.json')
                if execution.program[KEY].get('timeout_correction'):
                    recover()
                else:
                    require(not circuit['open'] and not circuit.get('half_open_reserved'),
                        'Orphan product requires settled service recovery before continuation')
            else:
                recover()
        except Exception:
            # A spent service reserve still must not cancel ready local work.
            from scripts.legal_integration_phased_live import defer_open_service
            ready = execution.summary()['ready']
            live_ready = [t for t in ready if t.startswith(('acquire-','baseline-','tool-','compare-'))]
            if live_ready:
                defer_open_service(execution, live_ready[0])
            execution.run()
            raise
        before = digest(read(ROOT/STATE))
        result = run()
        execution = MasterExecution(ROOT, PROGRAM, STATE)
        execution.run()
        binding = read(ROOT/BASE/'current-binding.json')
        circuit = read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-circuit.json')
        if circuit['open']:
            # recover() checks the same cumulative replacement ledger and
            # rejects exhausted/uncertain dispatch; no scope or count resets.
            continue
        view = execution.summary()
        if not view['ready'] and not view['running']:
            return view
        require(digest(read(ROOT/STATE)) != before,
            'Ready frontier made no progress; exact agent prerequisites require diagnosis')


def worker():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    with (ROOT/WORK/'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(ROOT/WORK/'worker.json', dict(process=process_identity(os.getpid()), started_at_utc=datetime.now(timezone.utc).isoformat()))
        try:
            save(ROOT/WORK/'live-result.json', live())
        except BaseException as exc:
            save(ROOT/WORK/'worker-error.json', dict(error=type(exc).__name__, reason=str(getattr(exc,'details',None) or exc)))
            raise
        finally:
            steps = []
            for name, command in (('refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                    ('verify',['.venv-context/bin/python','scripts/legal_integration_master.py','verify'])):
                with (ROOT/WORK/(name+'.stdout')).open('w') as out, (ROOT/WORK/(name+'.stderr')).open('w') as err:
                    code = subprocess.call(command, cwd=ROOT, stdout=out, stderr=err)
                steps.append(dict(command=command, exit_code=code))
            save(ROOT/WORK/'finished.json', dict(steps=steps, ended_at_utc=datetime.now(timezone.utc).isoformat(), integration_complete=False))


def arm():
    import subprocess
    from scripts.legal_mission_execution import process_identity, process_alive
    with (ROOT/WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = ROOT/WORK/'armed.json'
        if path.exists():
            saved = read(path)
            require(process_alive(saved['process']), 'Previous worker ended; inspect retained result before restart')
            return dict(already_running=True, **saved)
        view = verification()
        require(view['ready'] and not view['running'], 'No idle ready repair work')
        from scripts.legal_integration_campaign import provider
        provider().check()
        with (ROOT/WORK/'worker.log').open('a') as log:
            process = subprocess.Popen([str(ROOT/'.venv-context/bin/python'),str(Path(__file__).resolve()),'worker'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        identity = process_identity(process.pid)
        require(identity is not None, 'Repair worker exited during startup')
        saved = dict(process=identity, armed_at_utc=datetime.now(timezone.utc).isoformat())
        save(path, saved)
        return saved


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register','verify','arm','worker'])
    args = parser.parse_args()
    print(json.dumps(dict(register=register,verify=verification,arm=arm,worker=worker)[args.action](), indent=2))
