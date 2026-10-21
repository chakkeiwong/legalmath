"""Review/apply one retained P10 veto scope; never dispatch or reopen a task."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import (
    read, save, ref, verify, require, process_alive, digest,
)
from scripts.legal_integration_master import BASE, PROGRAM, STATE, MasterExecution
from scripts.legal_integration_campaign import provider, live_consumers
from scripts.legal_integration_phased_live import LIVE, active_live
from scripts.legal_integration_gap_refresh import validate_state_history

WORK = Path(__file__).resolve().parent
REVIEW = WORK / 'reviewed-veto-scope.md'
REPORT = WORK / 'veto-scope-review.json'
BEFORE = WORK / 'veto-scope-before-state.json'
APPLIED = WORK / 'veto-scope-applied.json'
ACTION = sys.argv[1]
require(ACTION in ('review', 'apply'), 'Expected review or apply')
began = time.monotonic()
execution = MasterExecution(ROOT, PROGRAM, STATE)
program = execution.program
diagnostic = read(WORK / 'p10-phase-diagnostic-result.json')


def proof(state):
    require(diagnostic['verdict'] == 'PASS' and diagnostic['actual_constructor']
        and diagnostic['actual_phase_guard'] and diagnostic['provider_calls'] == 0
        and diagnostic['all_other_contract_fields_equal']
        and [r['field'] for r in diagnostic['differences']] == ['implementation_identity'],
        'Missing actual phase mismatch proof')
    for name in ('ledger', 'program', 'binding', 'grant', 'retained_phase', 'source', 'plan'):
        verify(ROOT, diagnostic[name])
    require(diagnostic['differences'][0]['previous'] == program['frontier_refresh']['prior_binding']['sha256']
        and diagnostic['differences'][0]['current'] == diagnostic['binding']['sha256'],
        'Unexpected phase identity transition')
    service = provider()
    service.complete = lambda *a, **k: (_ for _ in ()).throw(AssertionError('No dispatch'))
    service.allowance.reserve = service.complete
    ledger = service.check()
    require(len(ledger['calls']) == 2369, 'Changed settled call comparator')
    require(not any(row['status'] == 'RUNNING' for row in state['tasks'].values()), 'Running owner')
    baseline = read(WORK / 'baseline.json')
    held = {r['previous']['path']: r['previous'] for r in baseline['archived']}
    census = []
    for path in baseline['dispatch_census']:
        verify(ROOT, held[path])
        journal = read(ROOT / path)
        require(not any(r['status'] == 'RESERVED' for r in journal['calls'].values()), 'Uncertain dispatch')
        census.append(held[path])
    common = ROOT / program['repair_execution']['common_directories']['evidence']
    require(not common.exists(), 'Evidence has preexisting current common state; review it separately')
    evidence = state['tasks']['acquire-evidence']
    task = execution.tasks['acquire-evidence']
    require(evidence['status'] == 'PENDING' and len(evidence['attempts']) == 5
        and task['maximum_attempts'] == 6, 'Evidence allocation changed')
    p10 = state['tasks']['acquire-p10']
    require(p10['status'] == 'FAILED' and len(p10['attempts']) == 8
        and execution.tasks['acquire-p10']['maximum_attempts'] == 8,
        'P10 exhausted outcome changed')
    targets = [v for v in state.get('continuation_vetoes', [])
        if v['code'] == 'E_INTEGRITY' and v['reason'] == 'Changed phase on resume'
        and v['evidence'] == [ref(ROOT, BASE / 'acquire-p10/attempt-8/evidence.json')]]
    require(len(targets) == 1, 'Missing exact P10 phase veto')
    target = targets[0]
    require(set(target['scope']) == set(live_consumers(execution)), 'Unexpected original veto scope')
    consumers = {'acquire-p10'}
    while True:
        next_consumers = consumers | {tid for tid, t in execution.tasks.items()
            if (set(t.get('requires', [])) | {d for g in t.get('any_success', []) for d in g}) & consumers}
        if next_consumers == consumers:
            break
        consumers = next_consumers
    scope = sorted(consumers & set(live_consumers(execution)))
    require(len(scope) == 14 and 'acquire-evidence' not in scope, 'Unexpected P10 consumers')
    narrowed = {**deepcopy(target), 'scope': scope}
    candidate = deepcopy(state)
    candidate['continuation_vetoes'].remove(target)
    candidate['continuation_vetoes'].append(narrowed)
    candidate.setdefault('resolved_continuation_vetoes', []).append(dict(
        veto=deepcopy(target), review=ref(ROOT, REVIEW),
        evidence=ref(ROOT, WORK / 'p10-phase-diagnostic-result.json'),
        retained_veto=deepcopy(narrowed), basis='Authenticated branch phase mismatch; shared authority and journals intact.',
        at_utc=datetime.now(timezone.utc).isoformat(), attempts_reset=False, calls_added=0))
    validate_state_history(program, candidate, ROOT)
    old_classes, new_classes = execution.classify(state), execution.classify(candidate)
    changes = {tid: {'before': old_classes[tid], 'after': row} for tid, row in new_classes.items()
        if row != old_classes[tid]}
    if set(changes) != {'acquire-evidence'}:
        rejected = WORK / 'veto-scope-review-rejected.json'
        require(not rejected.exists(), 'Do not overwrite rejected review evidence')
        save(rejected, dict(verdict='REJECTED',
            reason='Original review required exactly one changed classifier row.',
            classifier_changes=changes, provider_calls=0, state_mutated=False,
            state=ref(ROOT, STATE), program=ref(ROOT, PROGRAM),
            diagnostic=ref(ROOT, WORK / 'p10-phase-diagnostic-result.json'),
            source=ref(ROOT, Path(__file__)),
            at_utc=datetime.now(timezone.utc).isoformat()))
        print(json.dumps(changes, indent=2), flush=True)
    require(set(changes) == {'acquire-evidence'}
        and changes['acquire-evidence']['before']['status'] == 'BLOCKED'
        and changes['acquire-evidence']['after']['status'] == 'READY',
        'Scope adjustment changed an unexpected consumer')
    require(candidate['tasks'] == state['tasks'] and candidate['events'] == state['events'],
        'Scope adjustment changed tasks or original events')
    return dict(target=target, narrowed=narrowed, classifier_changes=changes,
        dispatch_census=census, current_shared_authority_valid=True,
        evidence_current_common_absent=True), candidate


if ACTION == 'review':
    require(not REPORT.exists(), 'Do not overwrite a retained review')
    with execution.locked() as state:
        snapshot = deepcopy(state)
    before_ref = ref(ROOT, STATE)
    result, _ = proof(snapshot)
    require(ref(ROOT, STATE) == before_ref, 'State changed during review')
    result.update(verdict='PASS', state=before_ref, review=ref(ROOT, REVIEW),
        diagnostic=ref(ROOT, WORK / 'p10-phase-diagnostic-result.json'),
        program=ref(ROOT, PROGRAM), binding=ref(ROOT, BASE / 'current-binding.json'),
        grant=ref(ROOT, BASE / 'live-grant.json'), ledger=ref(ROOT, BASE / 'live-calls.json'),
        source=ref(ROOT, Path(__file__)), provider_calls=0, tasks_reopened=0,
        additional_attempts=0, repair_allowance_added=0, legal_acceptance=False,
        command='.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)) + ' review',
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=sys.executable, devices='CPU only; CUDA_VISIBLE_DEVICES=-1',
        seeds='N/A: deterministic identity/dependency review',
        wall_seconds=time.monotonic()-began, at_utc=datetime.now(timezone.utc).isoformat())
    save(REPORT, result)
    print(json.dumps({k: result[k] for k in ('verdict', 'classifier_changes', 'provider_calls', 'wall_seconds')}, indent=2))
else:
    require(not APPLIED.exists() and not BEFORE.exists(), 'Do not repeat a retained correction')
    report = read(REPORT)
    require(report['verdict'] == 'PASS', 'Missing passing scope review')
    for name in ('review', 'diagnostic', 'program', 'binding', 'grant', 'ledger', 'source'):
        verify(ROOT, report[name])
    worker = read(WORK / 'worker-result.json')
    require(worker['live_exit_code'] == 0 and all(r.get('exit_code') == 0 for r in worker['checks']),
        'Original worker checks did not settle successfully')
    require(not process_alive(read(WORK / 'worker-start.json')['process'])
        and not process_alive(read(WORK / 'worker-live-process.json')['process']), 'Original worker survives')
    with ExitStack() as stack:
        for path in dict.fromkeys((ROOT / LIVE / 'supervisor.lock',
                ROOT / active_live(program) / 'supervisor.lock', (ROOT / STATE).with_suffix('.run.lock'))):
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with execution.locked() as state:
            require(ref(ROOT, STATE) == report['state'], 'State changed after scope review')
            result, candidate = proof(state)
            require(result == {k: report[k] for k in result}, 'Scope evidence changed after review')
            save(BEFORE, state)
            candidate['events'].append(dict(task_id=None, action='REVIEWED_CONTINUATION_VETO_SCOPE',
                at_utc=datetime.now(timezone.utc).isoformat(), original_veto=result['target'],
                retained_veto=result['narrowed'], review=ref(ROOT, REVIEW), evidence=ref(ROOT, REPORT),
                attempts_reset=False, tasks_reopened=0, calls_added=0))
            validate_state_history(program, candidate, ROOT)
            save(ROOT / STATE, candidate)
            require(candidate['tasks'] == state['tasks'] and candidate['events'][:-1] == state['events'],
                'Scope correction lost task or event history')
            save(APPLIED, dict(verdict='PASS', before=ref(ROOT, BEFORE), after=ref(ROOT, STATE),
                review=ref(ROOT, REVIEW), evidence=ref(ROOT, REPORT),
                classifier_changes=result['classifier_changes'], provider_calls=0, tasks_reopened=0,
                additional_attempts=0, repair_allowance_added=0, legal_acceptance=False,
                command='.venv-context/bin/python ' + str(Path(__file__).relative_to(ROOT)) + ' apply',
                environment=sys.executable, wall_seconds=time.monotonic()-began,
                at_utc=datetime.now(timezone.utc).isoformat()))
    print(json.dumps(read(APPLIED), indent=2))
