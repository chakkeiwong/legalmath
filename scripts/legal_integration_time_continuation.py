"""Apply the explicit 72-hour time amendment without reopening or resetting work."""
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
from legalmath.interpretation.assurance.time_authority import CONTINUATION_PROFILE, CONTINUATION_USER, effective_deadline

KEY = 'time_continuation'
WORK = Path('artifacts/legal-mission-control/2026-10-21/capacity-time-continuation')
REVIEW = Path('docs/plans/legal-capacity-time-continuation-2026-10-21.md')
USER = CONTINUATION_USER
APPROVED = '2026-10-21T02:19:15+00:00'
DEADLINE = '2026-10-24T02:19:15+00:00'
IMPLEMENTATION = {'scripts/legal_integration_time_continuation.py',
    'scripts/legal_integration_master.py', 'scripts/legal_mission_execution.py',
    'scripts/legal_mission_control.py', 'src/legalmath/interpretation/assurance/time_authority.py'}


def projection(baseline, *, mission=False, root=ROOT):
    allowed = IMPLEMENTATION | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in archive_rows(baseline, root) if r['previous']['path'] in allowed], mission=mission)


def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    value['deadline_utc'] = DEADLINE
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline', 'review', 'result', 'time_extension')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-time-continuation.v1' and revision['user_instruction'] == USER
        and revision['prior_detours'] == 60 and revision['additional_consolidated_revision'] == 0
        and revision['additional_task_attempts'] == revision['live_calls_added'] == 0
        and revision['additional_transport_replacements'] == 0 and revision['reopened_nodes'] == []
        and revision['attempts_reset'] is False and revision['service_scope_reset'] is False,
        'Unreviewed time-only continuation')
    for key in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant','time_extension'):
        verify(root, revision[key])
    require(set(revision['implementation']) == IMPLEMENTATION, 'Changed time amendment implementation scope')
    for pointer in revision['implementation'].values():
        verify(root, pointer)
    baseline = read(root / revision['baseline']['path'])
    held = {row['previous']['path']:row['archive'] for row in baseline['archived']}
    require(baseline['calls'] == 3485 and baseline['prior_detours'] == 60 and baseline['running_owners'] == 0,
        'Changed time amendment baseline')
    verify(root, baseline['predecessor_result'])
    predecessor = read(root / baseline['predecessor_result']['path'])
    require(predecessor['status'] == 'CHECKPOINT', 'Unsettled deployment predecessor')
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    for key,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
                     ('prior_ledger',BASE/'live-calls.json'),('prior_grant',BASE/'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost predecessor ' + key)
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('common_capacity') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(row['status'] == 'RUNNING' for row in before['tasks'].values()), 'Wrong or active predecessor')
    extension = read(root / revision['time_extension']['path'])
    prior_binding = read(root / revision['prior_binding']['path'])
    grant = read(root / revision['prior_grant']['path'])
    require(extension == dict(profile=CONTINUATION_PROFILE, approved=True, user_instruction=USER,
        approved_at_utc=APPROVED, duration_seconds=259200, deadline_utc=DEADLINE,
        maximum_calls=8100, prior_calls=3485, original_grant=revision['prior_grant'], original_grant_hash=digest(grant),
        ledger_before=revision['prior_ledger'], review=revision['review'], previous_extension=prior_binding['time_extension'],
        previous_deadline_utc=old['deadline_utc'], prior_binding=revision['prior_binding'], prior_program=revision['prior_program']),
        'Changed explicit 72-hour authority')
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0 and result['legal_acceptance'] is False,
        'Time amendment tests did not pass')
    for pointer in result['evidence']:
        verify(root, pointer)
    mapping = projection(baseline, root=root)
    with historical_evidence(root, mapping):
        validate_program(old, root)
    expected = expected_program(historical_projection(old, mapping), revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference), 'Time amendment changed unrelated graph or limits')
    return {task['id']:task['maximum_attempts'] for task in program['tasks']}


def project_state(before, program, now):
    require(not any(row['status'] == 'RUNNING' for row in before['tasks'].values()), 'Running owner cannot migrate')
    value = deepcopy(before)
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='REVIEWED_TIME_CONTINUATION', task_id=None, at_utc=now,
        review=program[KEY]['review'], attempts_reset=False, calls_added=0, additional_task_attempts=0))
    return value


def validate_state_history(program, state, root):
    before = read(root / program[KEY]['prior_state']['path'])
    require(set(state['tasks']) == set(before['tasks']), 'Changed owner set')
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost attempts ' + tid)
        if row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Changed settled owner ' + tid)
    require(state['events'][:len(before['events'])] == before['events'], 'Lost event history')
    require(all(v in state.get('continuation_vetoes', []) for v in before.get('continuation_vetoes', [])), 'Lost prior veto')
    previous = before.get('resolved_continuation_vetoes', [])
    require(state.get('resolved_continuation_vetoes', [])[:len(previous)] == previous, 'Lost resolved veto history')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_settled_recovery import candidate_binding
    from legalmath.interpretation.assurance.phased.evidence_store import save_exact
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
            if read(ROOT/journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            require(read(ROOT/PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different continuation registered')
            return dict(registered=True, resumed=True)
        baseline = read(ROOT/WORK/'baseline.json')
        held = {row['previous']['path']:row['archive'] for row in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256'] == held[str(path)]['sha256'], 'Frozen predecessor changed: ' + str(path))
        before, prior_binding = read(ROOT/STATE), read(ROOT/BASE/'current-binding.json')
        require(datetime.now(timezone.utc) < datetime.fromisoformat(DEADLINE), 'Approved time window expired')
        extension = dict(profile=CONTINUATION_PROFILE, approved=True, user_instruction=USER,
            approved_at_utc=APPROVED, duration_seconds=259200, deadline_utc=DEADLINE, maximum_calls=8100, prior_calls=3485,
            original_grant=held[str(BASE/'live-grant.json')], original_grant_hash=digest(read(ROOT/BASE/'live-grant.json')),
            ledger_before=held[str(BASE/'live-calls.json')], review=ref(ROOT,REVIEW),
            previous_extension=prior_binding['time_extension'], previous_deadline_utc=old['deadline_utc'],
            prior_binding=held[str(BASE/'current-binding.json')], prior_program=held[str(PROGRAM)])
        save_exact(ROOT/WORK/'time-extension.json', extension)
        revision = dict(profile='integration-time-continuation.v1', user_instruction=USER, work=str(WORK),
            prior_detours=60, additional_consolidated_revision=0, additional_task_attempts=0, reopened_nodes=[],
            live_calls_added=0, additional_transport_replacements=0, attempts_reset=False, service_scope_reset=False,
            baseline=ref(ROOT,WORK/'baseline.json'), review=ref(ROOT,REVIEW), result=ref(ROOT,WORK/'local-result.json'),
            time_extension=ref(ROOT,WORK/'time-extension.json'), implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)], prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')], prior_grant=held[str(BASE/'live-grant.json')])
        program = expected_program(historical_projection(old, projection(baseline)), revision, ROOT)
        validate_program(program, ROOT)
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before, program, now)
        stage = WORK/'registration-stage'
        save(ROOT/stage/'program.json', program)
        save(ROOT/stage/'state.json', state)
        pointer = dict(path=str(PROGRAM), sha256=ref(ROOT,stage/'program.json')['sha256'])
        adapted = deepcopy(program)
        adapted['settled_recovery'] = dict(revision, recoveries={})
        binding = candidate_binding(adapted, pointer, {**baseline, 'archived':archive_rows(baseline)})
        binding.update(user_instruction=USER, review=revision['review'], execution_review=program['common_capacity']['review'],
            time_extension=revision['time_extension'], effective_deadline_utc=DEADLINE)
        binding['bindings'] += [revision['review'], revision['time_extension'], binding['execution_review']]
        require(binding['phase_service_scope'] == prior_binding['phase_service_scope']
            and binding['service_recovery_policy'] == prior_binding['service_recovery_policy'], 'Changed service authority')
        save(ROOT/stage/'binding.json', binding)
        targets = {ROOT/PROGRAM:ROOT/stage/'program.json', ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text, original_bytes = Path.read_text, Path.read_bytes
        with patch.object(Path,'read_text',lambda path,*a,**k: original_text(targets.get(path,path),*a,**k)), \
             patch.object(Path,'read_bytes',lambda path,*a,**k: original_bytes(targets.get(path,path),*a,**k)):
            require(len(provider().check()['calls']) == baseline['calls'], 'Staged authority changed charges')
        mission = historical_projection(read(ROOT/DOC/'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT,PLAN), **{KEY:revision})
        reason = ('Continue the installed common capacity interface under the user-approved 72-hour extension; '
            'preserve all 3485 charges, task attempts, service reservations and completed work; '
            'diagnose service prerequisites and drain independent ready original-answer/tool branches.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-time-continuation-2026-10-21', task_id='product-contribution',
            kind='product_evaluation', outcome='no_advance', decision=reason, next_task='product-contribution',
            next_task_reason=reason, recorded_at_utc=now, result_evidence=[pointer,revision['review'],revision['result'],revision['time_extension']]))
        save(ROOT/stage/'mission.json', mission)
        save(ROOT/WORK/'registration-check.json', validate_staged_mission(ROOT,stage,mission,60))
        writes = [dict(path=str(path), before=ref(ROOT,path), replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True, deadline_utc=DEADLINE, calls_added=0, attempts_added=0)


def verification():
    program = read(ROOT/PROGRAM)
    runner = MasterExecution(ROOT,PROGRAM,STATE)
    validate_state_history(program,read(ROOT/STATE),ROOT)
    revision = program[KEY]
    current, previous = read(ROOT/BASE/'live-calls.json'), read(ROOT/revision['prior_ledger']['path'])
    require(current['calls'][:len(previous['calls'])] == previous['calls'], 'Lost old charges')
    require(ref(ROOT,BASE/'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Changed original grant')
    binding = read(ROOT/BASE/'current-binding.json')
    require(binding['program'] == ref(ROOT,PROGRAM) and binding['review'] == revision['review'], 'Wrong current binding')
    require(effective_deadline(ROOT,ROOT/BASE) == DEADLINE, 'Wrong effective deadline')
    for pointer in binding['bindings']:
        verify(ROOT,pointer)
    view = runner.summary()
    result = dict(calls=len(current['calls']), integration_complete=False, deadline_utc=DEADLINE,
        **{key:view[key] for key in ('execution','ready','running','blocked')})
    save(ROOT/WORK/'verification.json',result)
    return result


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['register','verify'])
    args = parser.parse_args()
    print(json.dumps({'register':register,'verify':verification}[args.action](),indent=2))
