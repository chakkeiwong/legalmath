"""Zero-call deployment of the reviewed baseline/corpus repair."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os

from scripts.legal_integration_master import BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import (read, save, ref, verify, require, digest,
    safe, historical_evidence, process_alive)
from scripts.legal_integration_acceptance_revision import historical_projection

KEY = 'baseline_corpus_repair'
WORK = Path('artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment')
CANDIDATE = Path('artifacts/legal-mission-control/2026-10-26/baselines-corpus-repair')
REVIEW = Path('docs/plans/legal-baseline-corpus-local-deployment-2026-10-26.md')
OLD_WORK = Path('artifacts/legal-mission-control/2026-10-24/window-continuation/service-inheritance')
PROFILE = 'reviewed-baseline-corpus-repair.v1'
EVENT = 'baseline-corpus-local-deployment-2026-10-26'
PROFILES = dict(context_reference_profile='exact-context-answer-and-needs.v1',
    warrant_reference_profile='exact-warrant-answer-fields.v1',
    correction_input_profile='exact-correction-gap-occurrences.v1')

def now():
    return datetime.now(timezone.utc).isoformat()

def mapping(baseline, *, mission=False):
    allowed = set(baseline['changed_paths']) | {str(PLAN)}
    if mission:
        allowed.add(str(PROGRAM))
    return {(r['previous']['path'], r['previous']['sha256']): r['archive']
        for r in baseline['archived'] if r['previous']['path'] in allowed}

def expected_program(old, revision, root, plan_reference):
    baseline = read(Path(root) / revision['baseline']['path'])
    value = historical_projection(old, mapping(baseline))
    value[KEY] = deepcopy(revision)
    value['protected_evidence'] += [revision[k] for k in
        ('review', 'result', 'baseline', 'handover', 'candidate')]
    value['protected_evidence'] += list(revision['implementation'].values())
    value['protected_evidence'].append(plan_reference)
    return value

def project_state(before, program, timestamp):
    state = deepcopy(before)
    state['program_hash'] = digest(program)
    state['events'].append(dict(action='LOCAL_BASELINE_CORPUS_DEPLOYMENT',
        task_id=None, at_utc=timestamp, review=program[KEY]['review'],
        calls_added=0, attempts_added=0, replacements_added=0))
    return state

def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    root = Path(root)
    revision = program[KEY]
    require(revision['profile'] == PROFILE and revision['work'] == str(WORK)
        and revision['runtime'] == str(WORK / 'live')
        and revision['activation'] == 'HOLD_REQUIRES_REVIEWED_CONTINUATION'
        and revision['prior_detours'] == 66
        and revision['additional_consolidated_revision'] == 1
        and revision['calls_added'] == revision['attempts_added'] == revision['replacements_added'] == 0
        and revision['attempts_reset'] is False and revision['reopened_nodes'] == []
        and all(revision.get(k) == v for k, v in PROFILES.items()),
        'Unreviewed baseline/corpus deployment scope')
    for key in ('review', 'result', 'baseline', 'handover', 'candidate',
                'prior_program', 'prior_state', 'prior_binding'):
        verify(root, revision[key])
    baseline = read(root / revision['baseline']['path'])
    held = {r['previous']['path']: r['archive'] for r in baseline['archived']}
    require(len(held) == len(baseline['archived']), 'Repeated archived path')
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed historical bytes')
        verify(root, row['archive'])
    for key, path in (('prior_program', PROGRAM), ('prior_state', STATE),
                      ('prior_binding', BASE / 'current-binding.json')):
        require(revision[key] == held[str(path)], 'Wrong deployment predecessor')
    require(set(revision['implementation']) == set(baseline['changed_paths']),
        'Different implementation population')
    for pointer in revision['implementation'].values():
        verify(root, pointer)
    old = read(root / revision['prior_program']['path'])
    require(KEY not in old, 'Repeated deployment amendment')
    with historical_evidence(root, mapping(baseline)):
        validate_program(old, root)
    handover = read(root / revision['handover']['path'])
    require(handover['settled'] and handover['reserved_dispatches'] == 0
        and handover['supervisor_ended'] and handover['calls'] == baseline['calls'] == 6471
        and baseline['service_replacements'] == 288, 'Invalid deployment handover')
    result = read(root / revision['result']['path'])
    require(result['verdict'] == 'PASS' and result['provider_calls'] == 0
        and result['legal_acceptance'] is False, 'Deployment tests did not pass')
    for pointer in result['evidence']:
        verify(root, pointer)
    require(program == expected_program(old, revision, root, plan_reference),
        'Deployment changed graph, attempts, limits or unrelated content')
    return {t['id']: t['maximum_attempts'] for t in program['tasks']}

def validate_history(program, state, root):
    from scripts.legal_window_continuation import validate_state_history
    revision = program[KEY]
    before = read(Path(root) / revision['prior_state']['path'])
    previous = deepcopy(program)
    previous.pop(KEY)
    validate_state_history(previous, state, root)
    require(set(before['tasks']) == set(state['tasks'])
        and state['events'][:len(before['events'])] == before['events'], 'Lost deployment history')
    for tid, old in before['tasks'].items():
        current = state['tasks'][tid]
        require(len(current['attempts']) >= len(old['attempts']), 'Lost attempt: ' + tid)
        for a, b in zip(old['attempts'], current['attempts']):
            require(all(b.get(k) == v for k, v in a.items()), 'Changed attempt: ' + tid)
        if old['status'] not in ('RUNNING', 'PENDING'):
            require(old == current, 'Reopened settled owner: ' + tid)
        if old.get('service_checkpoint') and not old.get('service_resume'):
            require(old == current, 'Changed held service checkpoint: ' + tid)
    for key in ('continuation_vetoes', 'resolved_continuation_vetoes'):
        prior = before.get(key, [])
        require(state.get(key, [])[:len(prior)] == prior, 'Lost ' + key)

def finish_transaction(root, journal):
    """Caller holds deployment/mission/state locks; new targets are supported."""
    root = Path(root)
    value = read(root / journal)
    require(value['profile'] == 'baseline-corpus-deployment-transaction.v1', 'Wrong transaction')
    paths = [r['path'] for r in value['writes']]
    require(len(paths) == len(set(paths)), 'Repeated transaction target')
    for row in value['writes']:
        target = safe(root, row['path'])
        verify(root, row['replacement'])
        current = ref(root, target)['sha256'] if target.exists() else None
        before = row['before']['sha256'] if row['before'] else None
        require(current in (before, row['replacement']['sha256']),
            'Concurrent edit prevents deployment: ' + row['path'])
    for row in value['writes']:
        target = safe(root, row['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.deployment-writing')
        with temporary.open('wb') as stream:
            stream.write((root / row['replacement']['path']).read_bytes())
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    value['status'] = 'COMMITTED'
    value['committed_at_utc'] = now()
    save(root / journal, value)

def assert_unchanged(root, baseline):
    for row in baseline['archived']:
        verify(Path(root), row['previous'])
    for path in baseline['absent_paths']:
        require(not safe(Path(root), path).exists(), 'New target appeared: ' + path)

def lock_paths(root, binding, journals):
    service = Path(binding['phase_service_scope']['path']).parent
    return list(dict.fromkeys([WORK / 'deployment.lock', OLD_WORK / 'worker.lock',
        OLD_WORK.parent / 'worker.lock', OLD_WORK / 'live/supervisor.lock',
        STATE.with_suffix('.run.lock'), DOC / 'mission.execution.lock', STATE.with_suffix('.lock'),
        service / 'service-worker.lock', service / 'service-circuit.lock',
        (BASE / 'live-calls.json').with_suffix('.lock'),
        *[Path(p).with_name('dispatch.lock') for p in journals]]))

def acquire_locks(root, stack, paths):
    for path in paths:
        target = safe(Path(root), str(path))
        target.parent.mkdir(parents=True, exist_ok=True)
        stream = stack.enter_context(target.open('a'))
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

def stopped(root):
    worker = read(Path(root) / OLD_WORK / 'worker.json')
    finished = read(Path(root) / OLD_WORK / 'finished.json')
    require(not process_alive(worker['process']) and finished['integration_complete'] is False,
        'Worker is active or terminal receipt changed')
    return worker, finished
