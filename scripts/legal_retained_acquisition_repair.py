"""Adopt the checked retained-acquisition correction in the existing master."""
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

KEY = 'retained_acquisition_repair'
WORK = Path('artifacts/legal-mission-control/2026-10-21/retained-acquisition-repair')
REVIEW = DOC/'results/retained-acquisition-capacity-repair-2026-10-21.md'
USER = 'refresh the master program.  git commit.  continue the execution to complete the task'
IMPLEMENTATION = {'scripts/legal_retained_acquisition_repair.py', 'scripts/legal_integration_master.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'src/legalmath/interpretation/assurance/phased/retained_acquisition.py'}
REOPEN = ['baseline-gatecoin']
REASON = 'Retained acquisition omits planned source or bridge requests'


def projection(baseline, *, mission=False, root=ROOT):
    allowed = IMPLEMENTATION | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in archive_rows(baseline, root) if r['previous']['path'] in allowed], mission=mission)


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
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-retained-acquisition-repair.v1'
        and revision['user_instruction'] == USER and revision['prior_detours'] == 60
        and revision['additional_consolidated_revision'] == 1
        and revision['additional_task_attempts'] == 1 and revision['reopened_nodes'] == REOPEN
        and revision['live_calls_added'] == revision['additional_transport_replacements'] == 0
        and revision['attempts_reset'] is False and revision['service_scope_reset'] is False,
        'Unreviewed retained acquisition correction')
    for key in ('baseline', 'review', 'result', 'prior_program', 'prior_state', 'prior_binding', 'prior_ledger', 'prior_grant'):
        verify(root, revision[key])
    require(set(revision['implementation']) == IMPLEMENTATION, 'Changed correction implementation scope')
    for pointer in revision['implementation'].values():
        verify(root, pointer)
    baseline = read(root/revision['baseline']['path'])
    require(baseline['calls'] == 3486 and baseline['prior_detours'] == 60
        and baseline['running_owners'] == 0, 'Changed correction baseline')
    held = {row['previous']['path']: row['archive'] for row in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed predecessor bytes')
        verify(root, row['archive'])
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE), ('prior_binding', BASE/'current-binding.json'),
                     ('prior_ledger', BASE/'live-calls.json'), ('prior_grant', BASE/'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost predecessor ' + key)
    old, before = read(root/revision['prior_program']['path']), read(root/revision['prior_state']['path'])
    require(old.get('time_continuation') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(row['status'] == 'RUNNING' for row in before['tasks'].values()), 'Wrong or active predecessor')
    require(before['tasks']['baseline-gatecoin']['status'] == 'FAILED'
        and len(before['tasks']['baseline-gatecoin']['attempts']) == 2
        and next(t['maximum_attempts'] for t in old['tasks'] if t['id'] == 'baseline-gatecoin') == 2,
        'Changed failed local owner')
    vetoes = revision['resolved_vetoes']
    require(len(vetoes) == 1 and vetoes[0] in before['continuation_vetoes']
        and vetoes[0]['code'] == 'E_INTEGRITY' and vetoes[0]['reason'] == REASON,
        'Foreign veto resolution')
    result = read(root/revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0
        and result['legal_acceptance'] is False and result['ledger_unchanged'], 'Correction checks did not pass')
    for pointer in result['evidence']:
        verify(root, pointer)
    require(set(result['production_entries']) == {'p10', 'p14', 'evidence', 'gatecoin'}
        and all(row['entry_result'] == 'VALIDATED' for row in result['production_entries'].values()),
        'Not every original entry point passed')
    mapping = projection(baseline, root=root)
    with historical_evidence(root, mapping):
        validate_program(old, root)
    expected = expected_program(historical_projection(old, mapping), revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference), 'Correction changed unrelated graph or authority')
    return {task['id']: task['maximum_attempts'] for task in program['tasks']}


def project_state(before, program, now):
    require(not any(row['status'] == 'RUNNING' for row in before['tasks'].values()), 'Running owner cannot migrate')
    value = deepcopy(before)
    revision = program[KEY]
    for tid in REOPEN:
        row = value['tasks'][tid]
        row.update(status='PENDING', reason='Checked capacity batching correction; reuse retained acquisition and completed calls')
        for key in ('result', 'dispatch_status', 'prerequisite_evidence', 'shared_scope'):
            row.pop(key, None)
    for veto in revision['resolved_vetoes']:
        value['continuation_vetoes'].remove(veto)
        value.setdefault('resolved_continuation_vetoes', []).append(dict(veto=veto, review=revision['review'],
            evidence=revision['result'], at_utc=now, attempts_reset=False, calls_added=0,
            basis='All four original entry points validate unchanged acquisition; complete parent requests and bridges retained.'))
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='REVIEWED_RETAINED_ACQUISITION_REPAIR', task_id=None, at_utc=now,
        review=revision['review'], attempts_reset=False, calls_added=0, additional_task_attempts=1))
    return value


def validate_state_history(program, state, root):
    revision = program[KEY]
    before = read(root/revision['prior_state']['path'])
    require(set(state['tasks']) == set(before['tasks']), 'Changed owner set')
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost attempts ' + tid)
        if tid not in REOPEN and row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Changed settled owner ' + tid)
    require(state['events'][:len(before['events'])] == before['events'], 'Lost event history')
    prior = before.get('resolved_continuation_vetoes', [])
    require(state.get('resolved_continuation_vetoes', [])[:len(prior)] == prior, 'Lost resolved veto history')
    for veto in revision['resolved_vetoes']:
        require(any(row['veto'] == veto and row['review'] == revision['review']
            and row['evidence'] == revision['result'] for row in state.get('resolved_continuation_vetoes', [])),
            'Unrecorded resolved veto')
    require(all(v in state.get('continuation_vetoes', []) for v in before.get('continuation_vetoes', [])
        if v not in revision['resolved_vetoes']), 'Lost independent veto')


def register():
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
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            require(read(ROOT/PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different correction registered')
            return dict(registered=True, resumed=True)
        baseline = read(ROOT/WORK/'baseline.json')
        held = {row['previous']['path']: row['archive'] for row in baseline['archived']}
        for path in (PROGRAM, STATE, DOC/'mission.json', BASE/'current-binding.json', BASE/'live-calls.json', BASE/'live-grant.json'):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Frozen predecessor changed: ' + str(path))
        before, prior_binding = read(ROOT/STATE), read(ROOT/BASE/'current-binding.json')
        revision = dict(profile='integration-retained-acquisition-repair.v1', user_instruction=USER, work=str(WORK),
            prior_detours=60, additional_consolidated_revision=1, additional_task_attempts=1, reopened_nodes=REOPEN,
            live_calls_added=0, additional_transport_replacements=0, attempts_reset=False, service_scope_reset=False,
            baseline=ref(ROOT, WORK/'baseline.json'), review=ref(ROOT, REVIEW), result=ref(ROOT, WORK/'local-result.json'),
            implementation={p: ref(ROOT, p) for p in sorted(IMPLEMENTATION)},
            resolved_vetoes=[v for v in before['continuation_vetoes'] if v['code'] == 'E_INTEGRITY' and v['reason'] == REASON],
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)], prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')], prior_grant=held[str(BASE/'live-grant.json')])
        program = expected_program(historical_projection(old, projection(baseline)), revision, ROOT)
        validate_program(program, ROOT)
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before, program, now)
        stage = WORK/'registration-stage'
        save(ROOT/stage/'program.json', program)
        save(ROOT/stage/'state.json', state)
        pointer = dict(path=str(PROGRAM), sha256=ref(ROOT, stage/'program.json')['sha256'])
        adapted = deepcopy(program)
        adapted['settled_recovery'] = dict(revision, recoveries={})
        binding = candidate_binding(adapted, pointer, {**baseline, 'archived': archive_rows(baseline)})
        binding.update(user_instruction=USER, review=prior_binding['review'], execution_review=revision['review'],
            time_extension=prior_binding['time_extension'], effective_deadline_utc=prior_binding['effective_deadline_utc'])
        binding['bindings'] += [revision['review'], binding['time_extension']]
        require(binding['phase_service_scope'] == prior_binding['phase_service_scope']
            and binding['service_recovery_policy'] == prior_binding['service_recovery_policy'], 'Changed service authority')
        save(ROOT/stage/'binding.json', binding)
        targets = {ROOT/PROGRAM: ROOT/stage/'program.json', ROOT/BASE/'current-binding.json': ROOT/stage/'binding.json'}
        original_text, original_bytes = Path.read_text, Path.read_bytes
        with patch.object(Path, 'read_text', lambda path,*a,**k: original_text(targets.get(path, path),*a,**k)), \
             patch.object(Path, 'read_bytes', lambda path,*a,**k: original_bytes(targets.get(path, path),*a,**k)):
            require(len(provider().check()['calls']) == baseline['calls'], 'Staged authority changed charges')
        mission = historical_projection(read(ROOT/DOC/'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), **{KEY: revision})
        reason = ('Validate retained readings against their complete original parent requests, preserving joint bridges; '
            'continue all independent original branches after the reproduced shared batching defect is repaired.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-retained-acquisition-repair-2026-10-21',
            task_id='product-contribution', kind='product_evaluation', outcome='no_advance', decision=reason,
            next_task='product-contribution', next_task_reason=reason, recorded_at_utc=now,
            result_evidence=[pointer, revision['review'], revision['result']]))
        save(ROOT/stage/'mission.json', mission)
        save(ROOT/WORK/'registration-check.json', validate_staged_mission(ROOT, stage, mission, 61))
        writes = [dict(path=str(path), before=ref(ROOT, path), replacement=ref(ROOT, stage/name)) for path, name in (
            (PROGRAM, 'program.json'), (STATE, 'state.json'), (BASE/'current-binding.json', 'binding.json'), (DOC/'mission.json', 'mission.json'))]
        save(ROOT/journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
    return dict(registered=True, calls_added=0, attempts_added=1)


def verification():
    program = read(ROOT/PROGRAM)
    runner = MasterExecution(ROOT, PROGRAM, STATE)
    validate_state_history(program, read(ROOT/STATE), ROOT)
    revision = program[KEY]
    current, previous = read(ROOT/BASE/'live-calls.json'), read(ROOT/revision['prior_ledger']['path'])
    require(current['calls'][:len(previous['calls'])] == previous['calls'], 'Lost old charges')
    require(ref(ROOT, BASE/'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Changed original grant')
    binding = read(ROOT/BASE/'current-binding.json')
    prior_binding = read(ROOT/revision['prior_binding']['path'])
    require(binding['program'] == ref(ROOT, PROGRAM) and binding['review'] == prior_binding['review']
        and binding['execution_review'] == revision['review'], 'Wrong current binding')
    for pointer in binding['bindings']:
        verify(ROOT, pointer)
    view = runner.summary()
    result = dict(calls=len(current['calls']), integration_complete=False,
        **{key: view[key] for key in ('execution', 'ready', 'running', 'blocked')})
    save(ROOT/WORK/'verification.json', result)
    return result


def live():
    """Keep the reviewed five-minute policy under the new, checked binding."""
    import importlib.util
    from unittest.mock import patch
    from scripts.legal_integration_phased_live import live as run
    from legalmath.interpretation.assurance import bounded_provider as bp
    from legalmath.interpretation.search import providers
    timing_path = ROOT/'artifacts/legal-mission-control/2026-10-21/five-minute-retry/five_minute_retry.py'
    spec = importlib.util.spec_from_file_location('retained_five_minute_timing', timing_path)
    timing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(timing)
    old_authority = timing.authority
    program = read(ROOT/PROGRAM)
    revision = program[KEY]
    expected_program_ref = ref(ROOT, PROGRAM)
    expected_binding_ref = ref(ROOT, BASE/'current-binding.json')
    historical = {(str(PROGRAM), revision['prior_program']['sha256']): revision['prior_program'],
        (str(BASE/'current-binding.json'), revision['prior_binding']['sha256']): revision['prior_binding']}

    def current_timing_authority():
        # Authenticate the unchanged user timing grant against its exact old
        # program/binding, then verify the separately reviewed current binding.
        verify(ROOT, expected_program_ref)
        verify(ROOT, expected_binding_ref)
        for pointer in revision['implementation'].values():
            verify(ROOT, pointer)
        verify(ROOT, revision['review'])
        verify(ROOT, revision['result'])
        with historical_evidence(ROOT, historical):
            return old_authority()

    current_timing_authority()
    with patch.object(timing, 'authority', current_timing_authority), \
            patch.object(bp, 'recovery_delay', timing.retry_delay), \
            patch.object(bp.CampaignAllowance, 'wait_service_recovery', timing.five_minute_wait), \
            patch.object(providers, 'transient_service_details', timing.resume.classify):
        return run()


def worker():
    import subprocess
    from scripts.legal_mission_execution import process_identity
    with (ROOT/WORK/'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(ROOT/WORK/'worker.json', dict(process=process_identity(os.getpid()),
            started_at_utc=datetime.now(timezone.utc).isoformat()))
        try:
            save(ROOT/WORK/'live-result.json', live())
        except BaseException as exc:
            save(ROOT/WORK/'worker-error.json', dict(error=type(exc).__name__,
                reason=str(getattr(exc, 'details', None) or exc)))
            raise
        finally:
            steps = []
            for action, command in (
                    ('refresh', ['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                    ('verify', ['.venv-context/bin/python','scripts/legal_integration_master.py','verify'])):
                with (ROOT/WORK/(action+'.stdout')).open('w') as out, (ROOT/WORK/(action+'.stderr')).open('w') as err:
                    code = subprocess.call(command, cwd=ROOT, stdout=out, stderr=err)
                steps.append(dict(command=command, exit_code=code))
            save(ROOT/WORK/'finished.json', dict(steps=steps, integration_complete=False,
                ended_at_utc=datetime.now(timezone.utc).isoformat()))


def arm():
    import subprocess
    from scripts.legal_mission_execution import process_identity, process_alive
    with (ROOT/WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = ROOT/WORK/'armed.json'
        if path.exists():
            saved = read(path)
            require(process_alive(saved['process']), 'Prior continuation ended; inspect retained outcome before another start')
            return dict(already_running=True, **saved)
        runner = MasterExecution(ROOT, PROGRAM, STATE)
        view = runner.summary()
        require(view['ready'] and not view['running'], 'No idle authorized ready frontier')
        from scripts.legal_integration_campaign import provider
        provider().check()
        with (ROOT/WORK/'worker.log').open('a') as log:
            process = subprocess.Popen([str(ROOT/'.venv-context/bin/python'), str(Path(__file__).resolve()), 'worker'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        identity = process_identity(process.pid)
        require(identity is not None, 'Continuation worker exited during startup')
        saved = dict(process=identity, armed_at_utc=datetime.now(timezone.utc).isoformat(),
            command=['.venv-context/bin/python','scripts/legal_retained_acquisition_repair.py','worker'])
        save(path, saved)
        return saved


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register', 'verify', 'arm', 'worker'])
    args = parser.parse_args()
    print(json.dumps({'register': register, 'verify': verification, 'arm': arm, 'worker': worker}[args.action](), indent=2))
