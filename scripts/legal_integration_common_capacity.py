"""Register one reviewed common-capacity revision in the existing master.

The predecessor must be settled. This module preserves every charge, successful
owner, attempt, service reservation and deadline; it never creates live authority.
"""
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
from legalmath.interpretation.assurance.phased.capacity_policy import PROFILE as CAPACITY

KEY = 'common_capacity'
WORK = Path('artifacts/legal-mission-control/2026-10-20/common-capacity-interface')
REVIEW = Path('docs/plans/legal-common-capacity-interface-2026-10-20.md')
USER = 'create a plan to build this common capacity management interface and wire it up to all the stages.  ensure that we test this adequately.  review the plan thoroughly.   refresh the master program.   execute'
QUESTIONS = ('p10', 'p14', 'evidence', 'gatecoin')
DEADLINE = '2026-10-20T18:55:16+00:00'


def implementation(root):
    return set(read(root / WORK / 'implementation-files.json'))


def checkpoint_refs(revision):
    return list(revision['checkpoints'].values()) + [pointer
        for arms in revision.get('arm_checkpoints', {}).values() for pointer in arms.values()]


def projection(baseline, *, mission=False, root=ROOT):
    allowed = implementation(root) | {str(PLAN)} | ({str(PROGRAM)} if mission else set())
    return archives([r for r in archive_rows(baseline, root) if r['previous']['path'] in allowed], mission=mission)


def repair_targets(old, before):
    """One changed-contract attempt for failed original product owners only."""
    tasks = {t['id']: t for t in old['tasks']}
    targets = {}
    for tid, row in before['tasks'].items():
        if tid.startswith(('acquire-', 'baseline-', 'tool-', 'compare-')) and row['status'] in (
                'FAILED', 'BLOCKED', 'DEPENDENCY_BLOCKED', 'INTERRUPTED'):
            targets[tid] = int(len(row['attempts']) >= tasks[tid]['maximum_attempts'])
    return targets


def expected_program(old, before, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        tid = task['id']
        if tid in revision['attempt_additions']:
            task['maximum_attempts'] += revision['attempt_additions'][tid]
            task['deliverable'] = str(BASE / tid / f"attempt-{task['maximum_attempts']}" / 'result.json')
            task['inputs'] += [revision['review'], revision['result']]
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result')]
    value['protected_evidence'] += list(revision['implementation'].values()) + checkpoint_refs(revision)
    value['protected_evidence'].append(plan_reference or ref(root, PLAN))
    return value


def validate_revision(program, root, *, plan_reference=None):
    revision = program[KEY]
    require(revision['profile'] == 'integration-common-capacity.v1' and revision['user_instruction'] == USER
        and revision['capacity_profile'] == CAPACITY and revision['prior_detours'] == 59
        and revision['additional_consolidated_revision'] == 1 and revision['live_calls_added'] == 0
        and revision['additional_transport_replacements'] == 0 and revision['attempts_reset'] is False
        and revision['service_scope_reset'] is False, 'Unreviewed common capacity revision')
    for key in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant'):
        verify(root, revision[key])
    require(set(revision['implementation']) == implementation(root)
        and set(revision['checkpoints']) == set(QUESTIONS), 'Changed common capacity implementation scope')
    for item in [*revision['implementation'].values(), *checkpoint_refs(revision)]:
        verify(root, item)
    baseline = read(root / revision['baseline']['path'])
    require(baseline['running_owners'] == 0 and baseline['prior_detours'] == 59, 'Unsettled common capacity baseline')
    held = {r['previous']['path']:r['archive'] for r in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed predecessor bytes')
        verify(root, row['archive'])
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE), ('prior_binding', BASE/'current-binding.json'),
                     ('prior_ledger', BASE/'live-calls.json'), ('prior_grant', BASE/'live-grant.json')):
        require(revision[key] == held[str(path)], 'Lost common capacity predecessor ' + key)
    old, before = read(root / revision['prior_program']['path']), read(root / revision['prior_state']['path'])
    require(old.get('candidate_capacity_retry') and not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(r['status'] == 'RUNNING' for r in before['tasks'].values()), 'Wrong or active predecessor')
    require(revision['attempt_additions'] == repair_targets(old, before)
        and revision['reopened_nodes'] == sorted(revision['attempt_additions']), 'Changed reopening scope')
    require(program['deadline_utc'] == old['deadline_utc'] == DEADLINE
        and program['global_call_ceiling'] == old['global_call_ceiling'], 'Changed global authority')
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0 and result['legal_acceptance'] is False,
        'Common capacity validation did not pass')
    for item in result['evidence']:
        verify(root, item)
    require(read(root / WORK / 'production-replay.json')['verdict'] == 'PASS', 'Production replay failed')
    mapping = projection(baseline, root=root)
    with historical_evidence(root, mapping):
        validate_program(old, root)
    expected = expected_program(historical_projection(old, mapping), before, revision, root, plan_reference=plan_reference)
    require(program == project_retained_plan(expected, root, plan_reference), 'Changed unrelated master program')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def project_state(before, program, now):
    value = deepcopy(before)
    require(not any(r['status'] == 'RUNNING' for r in value['tasks'].values()), 'Running owner cannot migrate')
    for tid in program[KEY]['reopened_nodes']:
        row = value['tasks'][tid]
        require(row['status'] != 'SUCCEEDED', 'Completed owner cannot be resampled')
        row.update(status='PENDING', reason='Reviewed common capacity; retain completed preparations and outputs; retry missing work only')
        for key in ('result','dispatch_status','prerequisite_evidence','shared_scope'):
            row.pop(key, None)
    value['program_hash'] = digest(program)
    value['events'].append(dict(action='REVIEWED_COMMON_CAPACITY', task_id=None, at_utc=now,
        review=program[KEY]['review'], attempts_reset=False, calls_added=0))
    return value


def validate_state_history(program, state, root):
    before = read(root / program[KEY]['prior_state']['path'])
    for tid, row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])] == row['attempts'], 'Lost prior attempt ' + tid)
        if tid not in program[KEY]['reopened_nodes'] and row['status'] != 'PENDING':
            require(state['tasks'][tid] == row, 'Changed completed/unrelated owner ' + tid)
    require(all(v in state.get('continuation_vetoes', []) for v in before.get('continuation_vetoes', [])), 'Lost prior veto')
    previous = before.get('resolved_continuation_vetoes', [])
    require(state.get('resolved_continuation_vetoes', [])[:len(previous)] == previous, 'Lost resolved veto history')


def acquire(question, service):
    from scripts import legal_integration_phased_live as live
    from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose
    folder = WORK/'live'/question/'product'
    result = live.product_route(question, None, service, preparation_only=True)
    diagnosis = diagnose(ROOT, ROOT/folder, question, result=result)
    save(ROOT/folder.parent/'diagnosis.json', diagnosis)
    require(diagnosis['prepared'], question + ' preparation failed; exact diagnosis retained')
    return dict(question=question, preparation=ref(ROOT, folder/'result.json'),
        optional_failures=diagnosis['optional_incomplete_phases'],
        _conclusion='Completed preparation reused; common-capacity optional work retained. Legal and tool-effect reviews remain mandatory.')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import LIVE
    from scripts.legal_integration_campaign import provider
    from scripts.legal_integration_settled_recovery import candidate_binding
    from unittest.mock import patch
    journal = WORK/'registration.json'
    with ExitStack() as stack:
        for path in (LIVE/'supervisor.lock', STATE.with_suffix('.run.lock'), DOC/'mission.execution.lock', STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status'] != 'COMMITTED':
                finish_transaction(ROOT, journal)
            require(read(ROOT/PROGRAM).get(KEY, {}).get('work') == str(WORK), 'Different revision registered')
            return dict(registered=True, resumed=True)
        baseline = read(ROOT/WORK/'baseline.json')
        held = {r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM, STATE, DOC/'mission.json', BASE/'current-binding.json', BASE/'live-calls.json', BASE/'live-grant.json'):
            require(ref(ROOT, path)['sha256'] == held[str(path)]['sha256'], 'Frozen predecessor changed: ' + str(path))
        old, before = read(ROOT/PROGRAM), read(ROOT/STATE)
        additions = repair_targets(old, before)
        revision = dict(profile='integration-common-capacity.v1', user_instruction=USER, work=str(WORK),
            capacity_profile=CAPACITY, prior_detours=59, additional_consolidated_revision=1,
            live_calls_added=0, additional_transport_replacements=0, attempts_reset=False, service_scope_reset=False,
            attempt_additions=additions, reopened_nodes=sorted(additions),
            baseline=ref(ROOT, WORK/'baseline.json'), review=ref(ROOT, REVIEW), result=ref(ROOT, WORK/'local-result.json'),
            implementation={p:ref(ROOT, p) for p in sorted(implementation(ROOT))},
            checkpoints={q:ref(ROOT, WORK/'checkpoints'/(q+'.json')) for q in QUESTIONS},
            arm_checkpoints={q:{p.stem:ref(ROOT,p) for p in sorted((ROOT/WORK/'checkpoints/arms'/q).glob('*.json'))}
                for q in QUESTIONS},
            recoveries=old['candidate_capacity_retry']['recoveries'],
            prior_program=held[str(PROGRAM)], prior_state=held[str(STATE)], prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')], prior_grant=held[str(BASE/'live-grant.json')])
        program = expected_program(historical_projection(old, projection(baseline)), before, revision, ROOT)
        validate_program(program, ROOT)
        now = datetime.now(timezone.utc).isoformat()
        state = project_state(before, program, now)
        stage = WORK/'registration-stage'
        save(ROOT/stage/'program.json', program)
        save(ROOT/stage/'state.json', state)
        pointer = dict(path=str(PROGRAM), sha256=ref(ROOT, stage/'program.json')['sha256'])
        adapted = deepcopy(program)
        adapted['settled_recovery'] = revision
        binding = candidate_binding(adapted, pointer, {**baseline, 'archived': archive_rows(baseline)})
        prior = read(ROOT/revision['prior_binding']['path'])
        binding.update(user_instruction=USER, review=prior['review'], execution_review=revision['review'],
            time_extension=prior['time_extension'], effective_deadline_utc=DEADLINE)
        binding['bindings'] += [revision['review'], binding['time_extension']] + checkpoint_refs(revision)
        save(ROOT/stage/'binding.json', binding)
        # Full provider authority validation is possible only before the existing
        # live deadline. Local registration after expiry grants no execution.
        if datetime.now(timezone.utc) < datetime.fromisoformat(DEADLINE):
            targets = {ROOT/PROGRAM:ROOT/stage/'program.json', ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
            original_text, original_bytes = Path.read_text, Path.read_bytes
            with patch.object(Path, 'read_text', lambda path,*a,**k: original_text(targets.get(path,path),*a,**k)), \
                 patch.object(Path, 'read_bytes', lambda path,*a,**k: original_bytes(targets.get(path,path),*a,**k)):
                require(len(provider().check()['calls']) == baseline['calls'], 'Staged authority changed charges')
        mission = historical_projection(read(ROOT/DOC/'mission.json'), projection(baseline, mission=True))
        master = mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key], dict) and program[key].get('profile'):
                master[key] = deepcopy(program[key])
        master.update(program=pointer, plan=ref(ROOT, PLAN), **{KEY:revision})
        reason = ('Run the common capacity interface for every active stage. Preserve completed source/account/synthesis '
            'work and revalidate retained output-size failures; continue independent original answer/tool tasks. '
            'Atomic semantic limits and the existing shared service circuit remain explicit; calls and deadline unchanged.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='integration-master-common-capacity-2026-10-20', task_id='product-contribution',
            kind='product_evaluation', outcome='no_advance', decision=reason, next_task='product-contribution',
            next_task_reason=reason, recorded_at_utc=now, result_evidence=[pointer, revision['review'], revision['result']]))
        save(ROOT/stage/'mission.json', mission)
        save(ROOT/WORK/'registration-check.json', validate_staged_mission(ROOT, stage, mission, 60))
        writes = [dict(path=str(path), before=ref(ROOT,path), replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'), (STATE,'state.json'), (BASE/'current-binding.json','binding.json'), (DOC/'mission.json','mission.json'))]
        save(ROOT/journal, dict(profile='legal-master-registration-transaction.v1', status='PREPARED', writes=writes))
        finish_transaction(ROOT, journal)
    return dict(registered=True, reopened_nodes=sorted(additions), calls_added=0, deadline_utc=DEADLINE)


def verification():
    program = read(ROOT/PROGRAM)
    validate_program(program, ROOT)
    validate_state_history(program, read(ROOT/STATE), ROOT)
    revision = program[KEY]
    previous, current = read(ROOT/revision['prior_ledger']['path']), read(ROOT/BASE/'live-calls.json')
    require(current['calls'][:len(previous['calls'])] == previous['calls'], 'Lost old model charges')
    require(ref(ROOT, BASE/'live-grant.json')['sha256'] == revision['prior_grant']['sha256'], 'Changed grant')
    binding = read(ROOT/BASE/'current-binding.json')
    require(binding['program'] == ref(ROOT, PROGRAM) and binding['execution_review'] == revision['review'], 'Wrong capacity binding')
    for item in binding['bindings']:
        verify(ROOT, item)
    view = MasterExecution(ROOT, PROGRAM, STATE).summary()
    return dict(calls=len(current['calls']), integration_complete=False, common_capacity_profile=CAPACITY,
        **{k:view[k] for k in ('execution','ready','running','blocked')})


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['register', 'verify'])
    args = parser.parse_args()
    print(json.dumps({'register':register, 'verify':verification}[args.action](), indent=2))
