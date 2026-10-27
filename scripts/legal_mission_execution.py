#!/usr/bin/env python3
"""Persisted dependency scheduling; local execution never grants live authority."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('docs/implementation/legal-mission-control')
PROGRAM = BASE / 'execution.json'
STATE = BASE / 'execution-state.json'
TERMINAL = {'SUCCEEDED', 'FAILED', 'BLOCKED', 'INTERRUPTED', 'INVALID', 'DEPENDENCY_BLOCKED', 'INACTIVE'}
_HISTORICAL_EVIDENCE = ContextVar('legal_historical_evidence', default=None)


class Refused(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Refused(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.writing')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def safe(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'Worktree-relative path required')
    require(not set(p.parts) & {'.git', '.codex', '.agents', '.aws', '.ssh'}, 'Protected path')
    target = (root / p).resolve()
    require(target.is_relative_to(root.resolve()), 'Path escapes worktree')
    return target


def ref(root, path):
    path = Path(path)
    if not path.is_absolute():
        path = safe(root, str(path))
    return {'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def verify(root, reference):
    archives = _HISTORICAL_EVIDENCE.get() or {}
    archived = archives.get((str(root.resolve()), reference['path'], reference['sha256']))
    expected = archived or reference
    require(ref(root, expected['path']) == expected, 'Changed evidence: ' + reference['path'])


@contextmanager
def historical_evidence(root, archives):
    """Resolve exact old references inside sealed reviews to identical archives.

    This scope is for predecessor validation only. It does not change reads,
    serialized documents, or verification of the current amendment's evidence.
    Every replacement is checked directly, without inherited resolution.
    """
    held = dict(_HISTORICAL_EVIDENCE.get() or {})
    root_key = str(root.resolve())
    for (path, sha256), archive in archives.items():
        safe(root, path)
        require(archive['sha256'] == sha256 and archive['path'] != path,
            'Historical evidence must preserve original bytes')
        require(ref(root, archive['path']) == archive,
            'Changed historical archive: ' + archive['path'])
        key = (root_key, path, sha256)
        require(key not in held or held[key] == archive,
            'Conflicting historical evidence archive: ' + path)
        held[key] = dict(archive)
    token = _HISTORICAL_EVIDENCE.set(held)
    try:
        yield
    finally:
        _HISTORICAL_EVIDENCE.reset(token)


def merged_historical_archives(root, archives):
    """Compose a predecessor's aliases with any enclosing validation scope.

    A later amendment can archive implementation bytes that an earlier
    amendment did not need to archive.  Nested predecessor validation must
    retain both sets of exact aliases; dropping the enclosing set makes an
    unchanged historical program look different merely because its reference
    points at the current path.  Conflicting aliases remain an integrity
    failure.
    """
    root_key = str(root.resolve())
    inherited = {
        (path, sha256): dict(archive)
        for (scope, path, sha256), archive in (_HISTORICAL_EVIDENCE.get() or {}).items()
        if scope == root_key
    }
    for key, archive in archives.items():
        require(key not in inherited or inherited[key] == archive,
            'Conflicting historical evidence archive: ' + key[0])
        inherited[key] = dict(archive)
    return inherited


def process_identity(pid):
    """Linux process start time prevents a recycled PID looking like our worker."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return None if fields[0] == 'Z' else {'pid': pid, 'start': fields[19]}
    except (OSError, IndexError):
        return None


def process_alive(identity):
    return bool(identity) and process_identity(identity['pid']) == identity


def validate_program(program, root):
    require(program['profile'] == 'legal-mission-execution.v1', 'Unknown execution program')
    require(1 <= program['workers'] <= 4, 'Invalid worker ceiling')
    datetime.fromisoformat(program['deadline_utc'])
    for reference in program['protected_evidence']:
        verify(root, reference)
    tasks = {t['id']: t for t in program['tasks']}
    require(len(tasks) == len(program['tasks']) and tasks, 'Duplicate or empty task graph')
    if program.get('product_closure'):
        from scripts.legal_product_closure import validate
        reviewed = validate(program, root, program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('repaired_retry_continuation'):
        from scripts.legal_repaired_retry_continuation import validate
        reviewed = validate(program, root, program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('baseline_corpus_repair'):
        from scripts.legal_baseline_corpus_deployment import validate
        reviewed = validate(program, root, program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('window_continuation'):
        from scripts.legal_window_continuation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('review_repair'):
        from scripts.legal_review_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('retained_acquisition_repair'):
        from scripts.legal_retained_acquisition_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('time_continuation'):
        from scripts.legal_integration_time_continuation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('common_capacity'):
        from scripts.legal_integration_common_capacity import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('candidate_capacity_retry'):
        from scripts.legal_integration_candidate_retry import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('synthesis_resolution'):
        from scripts.legal_integration_synthesis_resolution import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('synthesis_continuation'):
        from scripts.legal_integration_synthesis_continuation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('gap_preservation'):
        from scripts.legal_integration_gap_preservation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('failure_recovery'):
        from scripts.legal_integration_failure_recovery import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('settled_recovery'):
        from scripts.legal_integration_settled_recovery import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('frontier_refresh'):
        from scripts.legal_integration_gap_refresh import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('delayed_service_recovery'):
        from scripts.legal_integration_delayed_service import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('local_refresh'):
        from scripts.legal_integration_repair_execution import validate_local_refresh
        reviewed = validate_local_refresh(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('repair_execution'):
        from scripts.legal_integration_repair_execution import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=41)
    if program.get('complete_account_capacity_repair'):
        from scripts.legal_integration_complete_account_capacity import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=21)
    if program.get('account_reconstruction_repair'):
        from scripts.legal_integration_account_reconstruction import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=20)
    if program.get('account_instruction_repair'):
        from scripts.legal_integration_account_instruction_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=19)
    if program.get('qualification_continuation'):
        from scripts.legal_integration_qualification_continuation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=18)
    if program.get('lossless_account_repair'):
        from scripts.legal_integration_lossless_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=17)
    if program.get('response_schema_repair'):
        from scripts.legal_integration_schema_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=16)
    if program.get('account_capacity_repair'):
        from scripts.legal_integration_account_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=15)
    if program.get('route_context_repair'):
        from scripts.legal_integration_route_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=14)
    if program.get('phased_acquisition_repair'):
        from scripts.legal_integration_phased_repair import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=13)
    if program.get('canary_validation_repair'):
        from scripts.legal_integration_canary_validation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=12)
    if program.get('retry_delay_repair'):
        from scripts.legal_integration_service_continuation import validate_delay_revision
        reviewed = validate_delay_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=11)
    if program.get('service_continuation'):
        from scripts.legal_integration_service_continuation import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=10)
    if program.get('execution_recovery'):
        from scripts.legal_integration_prerequisites import validate_recovery_revision
        reviewed = validate_recovery_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=9)
    if program.get('prerequisite_repair'):
        from scripts.legal_integration_prerequisites import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=8)
    if program.get('execution_refresh'):
        from scripts.legal_integration_execution_refresh import validate_revision
        reviewed = validate_revision(program, root, plan_reference=program['protected_evidence'][-1])
        account = program['execution_refresh'].get('post_review', {}).get('response_repair', {}).get('account_correction')
        return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=7 if account else 6)
    revision = program.get('acceptance_revision')
    if revision:
        require(revision.get('profile') == 'legal-acceptance-revision.v1'
                and revision.get('additional_consolidated_revision') == 1
                and revision.get('prior_detours') == 20
                and revision.get('live_calls_added') == 0
                and revision.get('user_instruction'), 'Unreviewed acceptance revision')
        for key in ('review', 'prior_program', 'prior_state'):
            verify(root, revision[key])
        old = read(safe(root, revision['prior_program']['path']))
        state = read(safe(root, revision['prior_state']['path']))
        require(state['program_hash'] == digest(old), 'Unbound revision baseline')
        require(program['deadline_utc'] == old['deadline_utc']
                and (set(state['tasks']) <= set(tasks) if program.get('substantive_continuation_revision')
                     else set(tasks) == set(state['tasks'])), 'Revision changed deadline or task population')
        ceilings = revision['attempt_ceilings']
        require(set(ceilings) == set(revision['reopened_nodes']), 'Revision ceiling scope differs')
        for tid, ceiling in ceilings.items():
            require(tid in tasks and not tid.startswith(('acquire-', 'baseline-', 'tool-', 'compare-'))
                    and tid != 'live-approval', 'Local revision cannot open live attempts')
            require(ceiling == len(state['tasks'][tid]['attempts']) + 1
                    and (program.get('remaining_work_revision') or tasks[tid]['maximum_attempts'] == ceiling),
                    'Revision must add exactly one local attempt')
    continuation = program.get('remaining_work_revision')
    if continuation:
        require(continuation.get('profile') == 'legal-remaining-work-revision.v1'
                and continuation.get('prior_detours') == 21
                and continuation.get('additional_consolidated_revision') == 1
                and continuation.get('live_calls_added') == 0
                and continuation.get('user_instruction'), 'Unreviewed remaining work revision')
        for key in ('review', 'prior_program', 'prior_state'): verify(root, continuation[key])
        previous = read(safe(root, continuation['prior_program']['path']))
        require(not previous.get('remaining_work_revision'), 'Remaining work revision cannot renew itself')
        from scripts.legal_integration_acceptance_revision import historical_projection
        archive_record = continuation.get('archives', [])
        if isinstance(archive_record, dict):
            verify(root, archive_record)
            archive_record = read(safe(root, archive_record['path']))['archived']
        archives = {(r['previous']['path'], r['previous']['sha256']): r['archive']
                    for r in archive_record}
        for archive in archives.values(): verify(root, archive)
        validate_program(historical_projection(previous, archives), root)
        prior_state = read(safe(root, continuation['prior_state']['path']))
        require(prior_state['program_hash'] == digest(previous), 'Unbound remaining work baseline')
        require(program['deadline_utc'] == previous['deadline_utc'] and
                (set(prior_state['tasks']) <= set(tasks) if program.get('substantive_continuation_revision')
                 else set(tasks) == set(prior_state['tasks'])),
                'Remaining work changed deadline or population')
        ceilings = continuation['attempt_ceilings']
        require(set(ceilings) == set(continuation['reopened_nodes']), 'Remaining work ceiling scope differs')
        prior_tasks = {t['id']: t for t in previous['tasks']}
        for tid, task in tasks.items():
            if tid not in prior_tasks and program.get('substantive_continuation_revision'):
                continue
            if tid in ceilings:
                require(not tid.startswith(('acquire-', 'baseline-', 'tool-', 'compare-')) and tid != 'live-approval',
                        'Local remaining work cannot open live attempts')
                require(ceilings[tid] == len(prior_state['tasks'][tid]['attempts']) + 1
                        and task['maximum_attempts'] == ceilings[tid], 'Remaining work must add one local attempt')
            else:
                require(task['maximum_attempts'] == prior_tasks[tid]['maximum_attempts'],
                        'Unreviewed remaining work attempt change')
    substantive = program.get('substantive_continuation_revision')
    if substantive:
        require(continuation and substantive.get('profile') == 'legal-substantive-continuation.v1'
                and substantive.get('prior_detours') == 22
                and substantive.get('additional_consolidated_revision') == 1
                and substantive.get('prior_charged_calls') == 232
                and substantive.get('live_calls_added') == 0
                and substantive.get('attempts_reset') is False
                and substantive.get('user_instruction'), 'Unreviewed substantive continuation')
        for key in ('plan', 'review', 'prior_program', 'prior_state', 'baseline'):
            verify(root, substantive[key])
        require(substantive['prior_program']['path'] != 'docs/implementation/legal-mission-control/integration-master.json',
                'Continuation baseline must be archived')
        old = read(safe(root, substantive['prior_program']['path']))
        prior = read(safe(root, substantive['prior_state']['path']))
        require(not old.get('substantive_continuation_revision') and prior['program_hash'] == digest(old),
                'Unbound or renewed substantive continuation baseline')
        require(program['deadline_utc'] == old['deadline_utc']
                and program.get('global_call_ceiling') == old.get('global_call_ceiling')
                and program.get('historical_charged_calls') == old.get('historical_charged_calls'),
                'Continuation changed shared limits')
        old_tasks = {t['id']: t for t in old['tasks']}
        new_ids = set(tasks) - set(old_tasks)
        require(set(old_tasks) == set(prior['tasks']) and new_ids == set(substantive['reopened_nodes'])
                and new_ids == set(substantive['attempt_ceilings']) and new_ids,
                'Continuation changed or omitted historical task population')
        require(all(tasks[tid] == old_tasks[tid] for tid in old_tasks),
                'Continuation edited a historical task')
        correction = substantive.get('post_review')
        corrected = {}
        if correction:
            require(correction.get('profile') == 'legal-substantive-correction.v1'
                    and correction.get('prior_detours') == 23
                    and correction.get('additional_consolidated_revision') == 1
                    and correction.get('live_calls_added') == 0,
                    'Unreviewed substantive correction')
            for key in ('review', 'baseline', 'prior_program', 'prior_state'):
                verify(root, correction[key])
            before = read(safe(root, correction['prior_program']['path']))
            before_state = read(safe(root, correction['prior_state']['path']))
            require(not before['substantive_continuation_revision'].get('post_review')
                    and before_state['program_hash'] == digest(before)
                    and set(before_state['tasks']) == set(tasks),
                    'Correction must preserve the task population and bound first results')
            corrected = correction['attempt_ceilings']
            require(set(corrected) <= new_ids and corrected, 'Correction may only repair continuation nodes')
            before_tasks = {t['id']:t for t in before['tasks']}
            for tid in new_ids:
                expected = dict(before_tasks[tid])
                expected['deliverable'] = str(Path(program['artifact_directory']) / tid /
                    ('attempt-' + str(corrected.get(tid, 1))) / 'result.json')
                if tid in corrected:
                    require(corrected[tid] == len(before_state['tasks'][tid]['attempts']) + 1 == 2,
                            'Correction allows exactly one additional local attempt')
                    expected['maximum_attempts'] = 2
                require(tasks[tid] == expected, 'Correction changed a dependency or unrelated task')
        for tid in new_ids:
            require(not tid.startswith(('acquire-', 'baseline-', 'tool-', 'compare-','live-'))
                    and tasks[tid]['executor'] == 'command'
                    and substantive['attempt_ceilings'][tid] == 1
                    and tasks[tid]['maximum_attempts'] == corrected.get(tid, 1)
                    and tasks[tid]['command'][:3] == ['.venv/bin/python', 'scripts/legal_integration_master.py', 'worker'],
                    'Continuation may add one bounded local attempt only')
    reviewed = {**program.get('acceptance_revision', {}).get('attempt_ceilings', {}),
                **program.get('remaining_work_revision', {}).get('attempt_ceilings', {})}
    return validate_task_graph(program, root, reviewed=reviewed, ceiling_limit=5 if continuation else 4)


def validate_task_graph(program, root, *, reviewed, ceiling_limit):
    tasks = {t['id']: t for t in program['tasks']}
    require(len(tasks) == len(program['tasks']) and tasks, 'Duplicate or empty task graph')
    for tid, task in tasks.items():
        require(tid and all(c.isalnum() or c in '-_' for c in tid), 'Invalid task ID')
        require(task['executor'] in {'agent', 'command'}, 'Unknown executor')
        ceiling = max(3, reviewed.get(tid, 3))
        require(1 <= task['maximum_attempts'] <= ceiling and ceiling <= ceiling_limit, 'Invalid finite attempt ceiling')
        if task['maximum_attempts'] > 3:
            require(task['maximum_attempts'] == reviewed.get(tid), 'Unreviewed attempt ceiling')
        require(task['question_ids'] and set(task['question_ids']) <= {'p10', 'p14', 'evidence', 'gatecoin'}, 'Lost original target')
        require(task['acceptance'] and task['deliverable'], 'Missing concrete acceptance/deliverable')
        require(len(task['write_resources']) == len(set(task['write_resources'])), 'Repeated write lock')
        for reference in task.get('inputs', []):
            # Existence/identity is a branch check during readiness, not a global veto.
            safe(root, reference['path'])
        deps = task.get('requires', []) + task.get('after', [])
        for group in task.get('any_success', []):
            require(bool(group), 'Empty alternative dependency')
            deps += group
        if task.get('when_failed'):
            deps.append(task['when_failed'])
        require(set(deps) <= tasks.keys() and tid not in deps, 'Unknown/self dependency')
        if task['executor'] == 'command':
            argv = task['command']
            require(isinstance(argv, list) and len(argv) > 1 and argv[0] == '.venv/bin/python', 'Only registered project Python commands')
            require(argv[1] not in {'-c', '-'} and not any('\x00' in x for x in argv), 'No arbitrary inline command')
            require(1 <= task['timeout_seconds'] <= 3600, 'Command timeout required')
        task_deps = list(dict.fromkeys(deps))
        tasks[tid] = {**task, '_dependencies': task_deps}
    visited, active = set(), set()
    def visit(tid):
        require(tid not in active, 'Cyclic task graph')
        if tid in visited:
            return
        active.add(tid)
        for dep in tasks[tid]['_dependencies']:
            visit(dep)
        active.remove(tid); visited.add(tid)
    for tid in tasks:
        visit(tid)
    return tasks


class Execution:
    def __init__(self, root=ROOT, program_path=PROGRAM, state_path=STATE):
        self.root = Path(root).resolve()
        if program_path == PROGRAM and (self.root / BASE / 'mission.json').exists():
            registered = read(self.root / BASE / 'mission.json').get('execution_program')
            if registered:
                verify(self.root, registered)
                program_path = registered['path']
        self.program_path = safe(self.root, str(program_path))
        self.state_path = safe(self.root, str(state_path))
        self.program = read(self.program_path)
        self.tasks = validate_program(self.program, self.root)

    @contextmanager
    def locked(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = read(self.state_path) if self.state_path.exists() else {
                'profile': 'legal-mission-execution-state.v1', 'program_hash': digest(self.program),
                'tasks': {tid: {'status': 'PENDING', 'attempts': []} for tid in self.tasks}, 'events': []}
            require(state['program_hash'] == digest(self.program), 'Program changed; reviewed migration required')
            require(set(state['tasks']) == set(self.tasks), 'State task set changed')
            if self.program.get('product_closure'):
                from scripts.legal_product_closure import validate_history
                validate_history(self.program, state, self.root)
            elif self.program.get('repaired_retry_continuation'):
                from scripts.legal_repaired_retry_continuation import validate_history
                validate_history(self.program, state, self.root)
            elif self.program.get('baseline_corpus_repair'):
                from scripts.legal_baseline_corpus_deployment import validate_history
                validate_history(self.program, state, self.root)
            elif self.program.get('window_continuation'):
                from scripts.legal_window_continuation import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('review_repair'):
                from scripts.legal_review_repair import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('retained_acquisition_repair'):
                from scripts.legal_retained_acquisition_repair import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('time_continuation'):
                from scripts.legal_integration_time_continuation import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('common_capacity'):
                from scripts.legal_integration_common_capacity import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('candidate_capacity_retry'):
                from scripts.legal_integration_candidate_retry import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('synthesis_resolution'):
                from scripts.legal_integration_synthesis_resolution import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('synthesis_continuation'):
                from scripts.legal_integration_synthesis_continuation import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('gap_preservation'):
                from scripts.legal_integration_gap_preservation import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('failure_recovery'):
                from scripts.legal_integration_failure_recovery import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('settled_recovery'):
                from scripts.legal_integration_settled_recovery import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('frontier_refresh'):
                from scripts.legal_integration_gap_refresh import validate_state_history
                validate_state_history(self.program, state, self.root)
            elif self.program.get('delayed_service_recovery'):
                from scripts.legal_integration_delayed_service import validate_state_history
                validate_state_history(self.program, state, self.root)
            for revision in (self.program.get('acceptance_revision'), self.program.get('remaining_work_revision'),
                             self.program.get('substantive_continuation_revision'),
                             self.program.get('substantive_continuation_revision', {}).get('post_review'),
                             self.program.get('execution_refresh'),
                             self.program.get('execution_refresh', {}).get('post_review'),
                             self.program.get('execution_refresh', {}).get('post_review', {}).get('binding_fix'),
                             self.program.get('execution_refresh', {}).get('post_review', {}).get('response_repair'),
                             self.program.get('execution_refresh', {}).get('post_review', {}).get('response_repair', {}).get('account_correction'),
                             self.program.get('prerequisite_repair'), self.program.get('execution_recovery'),
                             self.program.get('service_continuation'), self.program.get('retry_delay_repair'),
                             self.program.get('canary_validation_repair'),
                             self.program.get('phased_acquisition_repair'),
                             self.program.get('route_context_repair'),
                             self.program.get('account_capacity_repair'),
                             self.program.get('response_schema_repair'),
                             self.program.get('lossless_account_repair'),
                             self.program.get('qualification_continuation'),
                             self.program.get('account_instruction_repair'),
                             self.program.get('account_reconstruction_repair'),
                             self.program.get('complete_account_capacity_repair'), self.program.get('repair_execution')):
                if not revision: continue
                prior = read(safe(self.root, revision['prior_state']['path']))
                for tid, row in prior['tasks'].items():
                    attempts = state['tasks'][tid]['attempts']
                    require(attempts[:len(row['attempts'])] == row['attempts'],
                            'Historical attempts changed: ' + tid)
                    require(len(attempts) <= self.tasks[tid]['maximum_attempts'],
                            'Recorded attempt ceiling exceeded: ' + tid)
                    if revision is self.program.get('substantive_continuation_revision') and not self.program.get('execution_refresh'):
                        require({k: state['tasks'][tid].get(k) for k in ('status','result','reason')} ==
                                {k: row.get(k) for k in ('status','result','reason')},
                                'Historical task outcome changed: ' + tid)
                    if (revision is self.program.get('execution_refresh') or
                            revision is self.program.get('execution_refresh', {}).get('post_review') or
                            revision is self.program.get('execution_refresh', {}).get('post_review', {}).get('binding_fix') or
                            revision is self.program.get('execution_refresh', {}).get('post_review', {}).get('response_repair') or
                            revision is self.program.get('execution_refresh', {}).get('post_review', {}).get('response_repair', {}).get('account_correction') or
                            revision is self.program.get('prerequisite_repair') or
                            revision is self.program.get('execution_recovery') or
                            revision is self.program.get('service_continuation') or
                            revision is self.program.get('retry_delay_repair') or
                            revision is self.program.get('canary_validation_repair') or
                            revision is self.program.get('phased_acquisition_repair') or
                            revision is self.program.get('route_context_repair') or
                            revision is self.program.get('account_capacity_repair') or
                            revision is self.program.get('response_schema_repair') or revision is self.program.get('lossless_account_repair') or revision is self.program.get('qualification_continuation') or revision is self.program.get('account_instruction_repair') or revision is self.program.get('account_reconstruction_repair') or revision is self.program.get('complete_account_capacity_repair') or revision is self.program.get('repair_execution')) and tid not in revision['reopened_nodes'] and tid not in self.program.get('prerequisite_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('execution_recovery', {}).get('reopened_nodes', []) and tid not in self.program.get('service_continuation', {}).get('reopened_nodes', []) and tid not in self.program.get('retry_delay_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('canary_validation_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('phased_acquisition_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('route_context_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('account_capacity_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('response_schema_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('lossless_account_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('qualification_continuation', {}).get('reopened_nodes', []) and tid not in self.program.get('account_instruction_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('account_reconstruction_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('complete_account_capacity_repair', {}).get('reopened_nodes', []) and tid not in self.program.get('repair_execution', {}).get('reopened_nodes', []):
                        require(attempts == row['attempts'] or row['status'] == 'PENDING',
                                'Unreviewed historical task rerun: ' + tid)
                        if row['status'] != 'PENDING':
                            require(state['tasks'][tid] == row, 'Unreviewed historical outcome changed: ' + tid)
            yield state

    def event(self, state, tid, action, **details):
        state['events'].append({'task_id': tid, 'action': action,
            'at_utc': datetime.now(timezone.utc).isoformat(), **details})
        save(self.state_path, state)

    def classify(self, state):
        result = {}
        refresh = self.program.get('execution_refresh')
        refresh = refresh.get('post_review', refresh) if refresh else None
        refresh = refresh.get('response_repair', refresh.get('binding_fix', refresh)) if refresh else None
        refresh = refresh.get('account_correction', refresh) if refresh else None
        refresh = self.program.get('prerequisite_repair', refresh)
        refresh = self.program.get('execution_recovery', refresh)
        refresh = self.program.get('service_continuation', refresh)
        refresh = self.program.get('retry_delay_repair', refresh)
        refresh = self.program.get('canary_validation_repair', refresh)
        refresh = self.program.get('phased_acquisition_repair', refresh)
        refresh = self.program.get('route_context_repair', refresh)
        refresh = self.program.get('account_capacity_repair', refresh)
        refresh = self.program.get('response_schema_repair', refresh)
        refresh = self.program.get('lossless_account_repair', refresh)
        refresh = self.program.get('qualification_continuation', refresh)
        refresh = self.program.get('account_instruction_repair', refresh)
        refresh = self.program.get('account_reconstruction_repair', refresh)
        refresh = self.program.get('complete_account_capacity_repair', refresh)
        refresh = self.program.get('repair_execution', refresh)
        refresh = self.program.get('delayed_service_recovery', refresh)
        refresh = self.program.get('frontier_refresh', refresh)
        refresh = self.program.get('settled_recovery', refresh)
        refresh = self.program.get('failure_recovery', refresh)
        refresh = self.program.get('gap_preservation', refresh)
        refresh = self.program.get('synthesis_continuation', refresh)
        refresh = self.program.get('synthesis_resolution', refresh)
        refresh = self.program.get('candidate_capacity_retry', refresh)
        refresh = self.program.get('common_capacity', refresh)
        refresh = self.program.get('retained_acquisition_repair', refresh)
        refresh = self.program.get('review_repair', refresh)
        historical = read(safe(self.root, refresh['prior_state']['path']))['tasks'] if refresh else {}
        def verify_dependencies(value):
            if isinstance(value, dict):
                if 'path' in value and 'sha256' in value:
                    verify(self.root, value)
                else:
                    for child in value.values(): verify_dependencies(child)
            elif isinstance(value, list):
                for child in value: verify_dependencies(child)
        def classify(tid):
            if tid in result:
                return result[tid]
            task, saved = self.tasks[tid], state['tasks'][tid]
            deps = {dep: classify(dep) for dep in task['_dependencies']}
            status = saved['status']; reason = saved.get('reason', '')
            if saved.get('service_checkpoint') and not saved.get('service_resume'):
                from scripts.legal_review_service_checkpoint import checked
                checked(self.root, tid, saved)
                status, reason = 'WAITING', 'Provider service prerequisite; current attempt checkpoint retained'
            try:
                for reference in task.get('inputs', []):
                    verify(self.root, reference)
            except (Refused, OSError, KeyError) as exc:
                status, reason = 'INVALID', str(exc)
            if saved.get('dispatch_status') == 'NOT_DISPATCHED':
                try:
                    require(saved.get('prerequisite_evidence'), 'Missing prerequisite evidence')
                    for reference in saved['prerequisite_evidence']:
                        verify(self.root, reference)
                except (Refused, OSError, KeyError) as exc:
                    status, reason = 'INVALID', str(exc)
            if status in {'SUCCEEDED', 'FAILED', 'BLOCKED'} and saved.get('result'):
                try:
                    verify(self.root, saved['result'])
                    for reference in read(safe(self.root, saved['result']['path']))['evidence']:
                        verify(self.root, reference)
                    if status == 'SUCCEEDED':
                        retained = (refresh and tid not in refresh.get('round_reopened_nodes', refresh['reopened_nodes'])
                                    and saved == historical.get(tid))
                        if retained:
                            # A retained assessment describes its recorded
                            # dependency snapshot. A newly reopened completion
                            # dependency does not rewrite that assessment.
                            verify_dependencies(saved['attempts'][-1]['dependencies'])
                        else:
                            require(saved['attempts'][-1]['dependencies'] == self.bind_dependencies(task, state, result), 'Dependency result changed')
                except (Refused, OSError, KeyError) as exc:
                    status, reason = 'INVALID', str(exc)
            if status == 'PENDING':
                trigger = task.get('when_failed')
                if trigger and deps[trigger]['status'] in {'SUCCEEDED', 'INACTIVE'}:
                    status, reason = 'INACTIVE', 'Recovery not needed'
                elif trigger and (deps[trigger]['status'] not in TERMINAL or state['tasks'][trigger]['status']=='RUNNING'):
                    status, reason = 'WAITING', 'Waiting for failure result: ' + trigger
                else:
                    need = [d for d in task.get('requires', []) if deps[d]['status'] != 'SUCCEEDED']
                    groups = [g for g in task.get('any_success', []) if not any(deps[d]['status'] == 'SUCCEEDED' for d in g)]
                    after = [d for d in task.get('after', []) if deps[d]['status'] not in TERMINAL
                             or state['tasks'][d]['status']=='RUNNING']
                    dead = [d for d in need if deps[d]['status'] in TERMINAL]
                    dead += [','.join(g) for g in groups if all(deps[d]['status'] in TERMINAL for d in g)]
                    if dead:
                        status, reason = 'DEPENDENCY_BLOCKED', 'Unmet successful inputs: ' + '; '.join(dead)
                    elif need or groups or after:
                        status, reason = 'WAITING', 'Waiting for prerequisites'
                    else:
                        status, reason = 'READY', ''
            for veto in state.get('continuation_vetoes', []):
                if tid in veto['scope'] and status == 'READY':
                    try:
                        for reference in veto['evidence']:
                            verify(self.root, reference)
                        status, reason = 'BLOCKED', veto['reason']
                    except (Refused, OSError, KeyError) as exc:
                        status, reason = 'INVALID', str(exc)
            result[tid] = {'status': status, 'reason': reason, 'executor': task['executor'],
                'attempts_used': len(saved['attempts']), 'maximum_attempts': task['maximum_attempts']}
            return result[tid]
        for tid in self.tasks:
            classify(tid)
        return result

    def bind_dependencies(self, task, state, classes):
        chosen = list(task.get('requires', []))
        for group in task.get('any_success', []):
            matches = [d for d in group if classes[d]['status'] == 'SUCCEEDED']
            require(matches, 'No successful alternative')
            chosen.append(matches[0])
        require(all(classes[d]['status'] == 'SUCCEEDED' for d in chosen), 'Stale successful prerequisite')
        bindings = {d: state['tasks'][d].get('result') for d in chosen}
        completion = list(task.get('after', []))
        if task.get('when_failed'):
            completion.append(task['when_failed'])
        if completion:
            def outcome(d):
                return {'status': classes[d]['status'], 'reason': classes[d]['reason'],
                        'result': state['tasks'][d].get('result'),
                        'attempts': len(state['tasks'][d]['attempts']),
                        'parents': {p: outcome(p) for p in self.tasks[d]['_dependencies']}}
            bindings['_completed'] = {d: outcome(d) for d in completion}
        return bindings

    def summary(self):
        with self.locked() as state:
            classes = self.classify(state)
            ready = sorted((t for t, row in classes.items() if row['status'] == 'READY'),
                           key=lambda t: (self.tasks[t]['priority'], t))
            running = [t for t, row in state['tasks'].items() if row['status'] == 'RUNNING'
                and (not row.get('service_checkpoint') or row.get('service_resume'))]
            paused = [t for t, row in state['tasks'].items() if row.get('service_checkpoint')
                and not row.get('service_resume')]
            recovered = {task['when_failed']: tid for tid, task in self.tasks.items()
                         if task.get('when_failed') and classes[tid]['status'] == 'SUCCEEDED'}
            blocked = {t: row['reason'] for t, row in classes.items()
                       if row['status'] in TERMINAL - {'SUCCEEDED', 'INACTIVE'} and t not in recovered}
            blocked.update({t: classes[t]['reason'] for t in paused})
            complete = all(row['status'] in {'SUCCEEDED', 'INACTIVE'} or t in recovered for t, row in classes.items())
            expired = datetime.now(timezone.utc) >= datetime.fromisoformat(self.program['deadline_utc'])
            sync_pending=bool(state.get('mission_sync_error'))
            status = ('COMPLETE' if complete and not sync_pending else 'DEADLINE_REACHED' if expired else
                'WORK_REMAINS' if ready or running or sync_pending else 'BLOCKED')
            return {'execution': status, 'ready': ready, 'running': running, 'blocked': blocked, 'recovered': recovered,
                'tasks': classes, 'mission_complete': False,
                'mission_sync_error': state.get('mission_sync_error'),
                'engineering_attempts': sum(len(state['tasks'][t]['attempts']) for t in self.tasks if self.tasks[t]['kind'] == 'engineering')}

    def start(self, tid):
        require(tid in self.tasks, 'Unknown task')
        with self.locked() as state:
            validate_program(self.program, self.root)
            require(datetime.now(timezone.utc) < datetime.fromisoformat(self.program['deadline_utc']), 'Original execution deadline reached')
            classes = self.classify(state)
            require(classes[tid]['status'] == 'READY', 'Task is not ready: ' + str(classes[tid]))
            task, saved = self.tasks[tid], state['tasks'][tid]
            require(len(saved['attempts']) < task['maximum_attempts'], 'Task attempt ceiling exhausted')
            busy = {r for other, row in state['tasks'].items() if row['status'] == 'RUNNING' for r in self.tasks[other]['write_resources']}
            require(not busy.intersection(task['write_resources']), 'Write resource busy')
            saved['attempts'].append({'number': len(saved['attempts']) + 1,
                'started_at_utc': datetime.now(timezone.utc).isoformat(),
                'dependencies': self.bind_dependencies(task, state, classes), 'inputs': task.get('inputs', [])})
            if task['executor'] == 'command':
                saved['attempts'][-1]['supervisor'] = process_identity(os.getpid())
            saved.pop('dispatch_status', None)
            saved.pop('prerequisite_evidence', None)
            saved['status'] = 'RUNNING'
            self.event(state, tid, 'STARTED', attempt=len(saved['attempts']))
            return len(saved['attempts'])

    def block_before_dispatch(self, tid, reason, evidence, *, shared_scope=()):
        """Retain an unmet prerequisite without pretending the node executed."""
        require(tid in self.tasks and reason and evidence, 'Unsubstantiated prerequisite block')
        for item in evidence:
            verify(self.root, item)
        with self.locked() as state:
            require(self.classify(state)[tid]['status'] == 'READY', 'Only ready unstarted work can be blocked')
            saved = state['tasks'][tid]
            saved.update(status='BLOCKED', reason=reason, dispatch_status='NOT_DISPATCHED',
                         prerequisite_evidence=evidence)
            saved.pop('result', None)
            self.event(state, tid, 'PREREQUISITE_BLOCKED', reason=reason, evidence=evidence,
                       attempt_consumed=False, shared_scope=list(shared_scope))
        return self.summary()

    def block_before_dispatch_many(self, tids, reason, evidence, *, shared_scope=()):
        """One durable prerequisite observation for independent ready owners."""
        require(tids and len(tids) == len(set(tids)) and set(tids) <= set(self.tasks)
            and reason and evidence, 'Unsubstantiated prerequisite blocks')
        for item in evidence:
            verify(self.root, item)
        with self.locked() as state:
            classes = self.classify(state)
            require(all(classes[tid]['status'] == 'READY' for tid in tids),
                'Only ready unstarted work can be blocked')
            for tid in tids:
                saved = state['tasks'][tid]
                saved.update(status='BLOCKED', reason=reason, dispatch_status='NOT_DISPATCHED',
                    prerequisite_evidence=evidence)
                saved.pop('result', None)
                self.event(state, tid, 'PREREQUISITE_BLOCKED', reason=reason, evidence=evidence,
                    attempt_consumed=False, shared_scope=list(shared_scope))
        return list(tids)

    def record_continuation_veto(self, code, reason, evidence, scope):
        """Persist an authority/integrity stop for its exact consumers."""
        require(code in {'E_AUTHORITY', 'E_INTEGRITY'} and reason and evidence and scope,
                'Invalid shared continuation veto')
        require(set(scope) <= set(self.tasks), 'Unknown veto consumer')
        for item in evidence:
            verify(self.root, item)
        with self.locked() as state:
            veto = {'code': code, 'reason': reason, 'evidence': evidence, 'scope': sorted(set(scope))}
            if veto not in state.setdefault('continuation_vetoes', []):
                state['continuation_vetoes'].append(veto)
                self.event(state, None, 'CONTINUATION_VETO', **veto)

    def finish(self, tid, result_path):
        reference = ref(self.root, result_path)
        value = read(safe(self.root, reference['path']))
        require(value['task_id'] == tid and value['status'] in {'SUCCEEDED', 'FAILED', 'BLOCKED'}, 'Invalid task result identity/status')
        require(value['conclusion'] and value['next_action'] and value['evidence'], 'Unsubstantiated result')
        for evidence in value['evidence']:
            verify(self.root, evidence)
        with self.locked() as state:
            saved = state['tasks'][tid]
            require(saved['status'] == 'RUNNING', 'No active task reservation')
            classes = self.classify(state)
            if value['status'] == 'SUCCEEDED':
                for item in saved['attempts'][-1]['inputs']:
                    verify(self.root, item)
                require(saved['attempts'][-1]['dependencies'] == self.bind_dependencies(self.tasks[tid], state, classes), 'Dependency changed during execution')
            saved.update(status=value['status'], result=reference, reason=value['conclusion'])
            saved['attempts'][-1].update(finished_at_utc=datetime.now(timezone.utc).isoformat(), result=reference)
            self.event(state, tid, value['status'], result=reference)
        if self.root == ROOT.resolve():
            try:
                self.sync_mission()
            except Exception as exc:
                # The task's durable result is already committed. Never overwrite
                # it with a worker failure merely because mission refresh failed.
                with self.locked() as state:
                    state['mission_sync_error'] = str(exc)
                    self.event(state, tid, 'MISSION_SYNC_FAILED', reason=str(exc))

    def sync_mission(self):
        """Append package results, then execute the required mission refresh."""
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        from scripts import legal_mission_control as control
        mission_path = self.root / BASE / 'mission.json'
        with mission_path.with_suffix('.execution.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            mission = read(mission_path)
            require(mission.get('execution_program') == ref(self.root, self.program_path), 'Program is not registered')
            with self.locked() as state:
                completed = [(tid, a) for tid, row in state['tasks'].items() for a in row['attempts'] if 'result' in a]
            completed.sort(key=lambda item: item[1]['finished_at_utc'])
            recorded = {(r.get('execution_node'), r.get('execution_attempt')) for r in mission['history']}
            reason = 'Continue the ready dependency frontier; a blocked item blocks only its dependants. Read execution status for exact ready tasks and branch blockers.'
            changed = False
            for tid, attempt in completed:
                if (tid, attempt['number']) in recorded:
                    continue
                value = read(safe(self.root, attempt['result']['path']))
                mission['history'].append({'id': 'continuous-' + tid + '-' + str(attempt['number']),
                    'task_id': 'product-contribution', 'kind': 'product_evaluation', 'outcome': 'no_advance',
                    'execution_node': tid, 'execution_attempt': attempt['number'],
                    'decision': value['conclusion'], 'next_task': 'product-contribution',
                    'next_task_reason': reason, 'recorded_at_utc': attempt['finished_at_utc'],
                    'result_evidence': [ref(self.root, self.program_path), attempt['result']],
                    'legal_progress_not_established_by_execution': True})
                changed = True
            if changed:
                mission['next_task_reason'] = reason
                control.validate(mission, read(self.root / BASE / 'tools.json'), self.root)
                save(mission_path, mission)
        # Exact argv, bounded output to a local log; no shell or provider dispatch.
        folder = safe(self.root, self.program['artifact_directory']); folder.mkdir(parents=True, exist_ok=True)
        with (folder / 'latest-mission-refresh.json').open('w') as output:
            proc = subprocess.run(['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh'],
                cwd=self.root, stdout=output, stderr=subprocess.STDOUT, timeout=60)
        require(proc.returncode == 0, 'Mission refresh failed; inspect retained refresh output')
        with self.locked() as state:
            if state.pop('mission_sync_error', None):
                self.event(state, None, 'MISSION_SYNC_RECOVERED')

    def retry(self, tid, reason):
        require(reason.strip(), 'Reviewed retry reason required')
        with self.locked() as state:
            saved = state['tasks'][tid]
            require(self.classify(state)[tid]['status'] in {'FAILED', 'BLOCKED', 'INTERRUPTED', 'INVALID'}, 'Retry requires an actual blocker')
            require(len(saved['attempts']) < self.tasks[tid]['maximum_attempts'], 'Task attempt ceiling exhausted')
            saved.update(status='PENDING', reason=reason)
            self.event(state, tid, 'REVIEWED_RETRY', reason=reason)

    def interrupt(self, tid, reason):
        with self.locked() as state:
            require(state['tasks'][tid]['status'] == 'RUNNING', 'No active reservation')
            state['tasks'][tid].update(status='INTERRUPTED', reason=reason)
            self.event(state, tid, 'INTERRUPTED', reason=reason)

    def command(self, tid, attempt):
        task = self.tasks[tid]
        folder = safe(self.root, self.program['artifact_directory']) / tid / ('attempt-' + str(attempt))
        output, log = folder / 'result.json', folder / 'command.log'
        argv = [x.replace('{result}', str(output)) for x in task['command']]
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(self.root / 'src') + os.pathsep + str(self.root)}
        try:
            folder.mkdir(parents=True, exist_ok=False)
            remaining = (datetime.fromisoformat(self.program['deadline_utc']) - datetime.now(timezone.utc)).total_seconds()
            with log.open('w') as stream:
                with subprocess.Popen(argv, cwd=self.root, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                      start_new_session=True) as proc:
                    with self.locked() as state:
                        state['tasks'][tid]['attempts'][-1]['worker'] = process_identity(proc.pid)
                        self.event(state, tid, 'WORKER_STARTED', pid=proc.pid)
                    try:
                        proc.wait(timeout=max(.01, min(task['timeout_seconds'], remaining)))
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
                        raise
            require(proc.returncode == 0, 'Command failed with exit ' + str(proc.returncode))
            require(output.is_file(), 'Command returned without its required result')
            self.finish(tid, output)
        except Exception as exc:
            # A setup exception must not escape before the branch result exists.
            # Keep any pre-existing attempt directory intact for inspection.
            if not log.exists():
                folder = safe(self.root, self.program['artifact_directory']) / (tid + '-attempt-' + str(attempt) + '-failure')
                folder.mkdir(parents=True, exist_ok=True)
                output, log = folder / 'result.json', folder / 'command.log'
            if output.exists():
                output.rename(folder / 'rejected-result.json')
            if not log.exists():
                log.write_text(str(exc))
            save(output, {'task_id': tid, 'status': 'FAILED', 'conclusion': str(exc),
                'next_action': 'Inspect the retained failure; execute declared recovery or a reviewed remaining attempt.',
                'evidence': [ref(self.root, log)], 'nonclaims': ['A command failure does not invalidate independent work.']})
            self.finish(tid, output)

    def recover_commands(self):
        """Adopt a finished orphan result; never redispatch an unknown live child."""
        with self.locked() as state:
            pending = [(tid, row['attempts'][-1]) for tid, row in state['tasks'].items()
                       if row['status'] == 'RUNNING' and self.tasks[tid]['executor'] == 'command']
        for tid, attempt in pending:
            if process_alive(attempt.get('supervisor')) or process_alive(attempt.get('worker')):
                continue
            output = safe(self.root, self.program['artifact_directory']) / tid / ('attempt-' + str(attempt['number'])) / 'result.json'
            try:
                self.finish(tid, output)
            except (Refused, OSError, ValueError, KeyError) as exc:
                self.interrupt(tid, 'Supervisor and worker ended without an admissible result; review before retry: ' + str(exc))

    def run(self):
        # A second supervisor must not race the same command queue.
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.with_suffix('.run.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Refused('Another command supervisor is active')
            self.recover_sync()
            self.recover_commands()
            with ThreadPoolExecutor(max_workers=self.program['workers']) as pool:
                running = {}
                while True:
                    view = self.summary()
                    if view['execution'] == 'DEADLINE_REACHED':
                        break
                    for tid in view['ready']:
                        if self.tasks[tid]['executor'] != 'command' or len(running) >= self.program['workers']:
                            continue
                        try:
                            attempt = self.start(tid)
                        except Refused as exc:
                            if str(exc) == 'Write resource busy':
                                continue
                            raise
                        running[pool.submit(self.command, tid, attempt)] = tid
                    if not running:
                        break
                    done, _ = wait(running, return_when=FIRST_COMPLETED)
                    for future in done:
                        tid = running.pop(future)
                        try:
                            future.result()
                        except Exception as exc:
                            # Last-resort isolation, including failure to retain a
                            # worker receipt. Independent futures still drain.
                            with self.locked() as state:
                                if state['tasks'][tid]['status'] == 'RUNNING':
                                    state['tasks'][tid].update(status='INTERRUPTED', reason=str(exc))
                                    self.event(state, tid, 'WORKER_EXCEPTION', reason=str(exc))
            return self.summary()

    def recover_sync(self):
        with self.locked() as state:
            pending=bool(state.get('mission_sync_error'))
        if pending:
            try:
                self.sync_mission()
            except Exception as exc:
                with self.locked() as state:
                    state['mission_sync_error']=str(exc)
                    self.event(state,None,'MISSION_SYNC_RETRY_FAILED',reason=str(exc))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'run', 'start', 'finish', 'retry', 'interrupt', 'settle'])
    parser.add_argument('task', nargs='?')
    parser.add_argument('--result')
    parser.add_argument('--reason')
    args = parser.parse_args(argv)
    try:
        execution = Execution()
        if args.action == 'start':
            execution.start(args.task)
        elif args.action == 'finish':
            execution.finish(args.task, args.result)
        elif args.action == 'retry':
            execution.retry(args.task, args.reason or '')
        elif args.action == 'interrupt':
            execution.interrupt(args.task, args.reason or 'Interrupted; no blind redispatch')
        if args.action == 'settle':
            execution.recover_sync()
        view = execution.run() if args.action == 'run' else execution.summary()
        print(json.dumps(view, indent=2))
        return 3 if args.action == 'settle' and view['execution'] == 'WORK_REMAINS' else 0
    except (Refused, KeyError, ValueError, OSError) as exc:
        print(json.dumps({'execution': 'REFUSED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
