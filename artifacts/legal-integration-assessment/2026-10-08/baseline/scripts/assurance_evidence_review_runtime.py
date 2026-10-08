"""Isolated, explicitly authorized review spending over the retained checkpoint."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import fcntl
from pathlib import Path
import re
import time

import assurance_evidence_core as c
import assurance_evidence_extension as ex
import assurance_evidence_current_review as packets
import assurance_evidence_protocol as protocol
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError

RUN = ex.RUN/packets.SUBDIR
AUTHORIZATION = RUN/'authorization.json'


def authorization(root):
    path = root/AUTHORIZATION
    if not path.exists():
        c.fail('E_AUTHORITY', 'Explicit numerical amendment has not been approved')
    grant = c.read(path)
    folder = packets.verified(root, ex)
    if (grant.get('status') != 'APPROVED_BY_USER' or not isinstance(grant.get('approval_text'), str)
            or not grant['approval_text'].strip() or folder is None
            or grant.get('proposal') != c.receipt(folder/'proposed-amendment.json', root)
            or grant.get('prepared') != c.receipt(folder/'completion-receipt.json', root)):
        c.fail('E_AUTHORITY', 'Missing or detached approval of the prepared amendment')
    proposal = c.read(c.checked(grant['proposal'], root))
    expected = {'status': 'PROPOSED_NOT_APPROVED', 'requested_window_hours': 48, 'maximum': 100, 'repair_maximum': 50,
        'final_disposition_limit': 50, 'other_final_issue_limit': 50, 'attempts_per_task': 2,
        'old_unused_calls_carried': 0, 'count_all_current_review_calls_as_repairs': True}
    if any(proposal.get(k) != v for k, v in expected.items()):
        c.fail('E_AUTHORITY', 'Unexpected numerical amendment limits')
    if any(grant.get(k) != v for k, v in expected.items() if k != 'status'):
        c.fail('E_AUTHORITY', 'Approval limits differ from prepared limits')
    if 'approval_source' in grant:
        source = c.read(c.checked(grant['approval_source'], root))
        if any(grant.get(k) != v for k, v in source.items()):
            c.fail('E_AUTHORITY', 'Approval differs from the recorded user instruction')
    before = ex.Allowance(root)
    if (before.verify() != proposal['baseline'] or before.ledger() != proposal['baseline_calls']
            or proposal['ends_at'] != before.grant['ends_at']
            or not before.grant['starts_at'] <= grant.get('approved_at', '')):
        c.fail('E_INTEGRITY', 'Original allowance or approval window changed')
    try:
        approved = datetime.fromisoformat(grant['approved_at'])
        end = datetime.fromisoformat(grant['ends_at'])
        if (approved.utcoffset() != timedelta(0) or end.utcoffset() != timedelta(0)
                or end != approved+timedelta(hours=48) or grant.get('window_renewal') is not True):
            c.fail('E_AUTHORITY', 'Explicit 48-hour renewal is missing or inconsistent')
    except (KeyError, TypeError, ValueError):
        c.fail('E_AUTHORITY', 'Explicit renewal timestamps are required')
    pre = c.read(c.checked(proposal['preflight'], root))
    if pre['status'] != 'PREFLIGHT_PASSED':
        c.fail('E_AUTHORITY', 'Prepared review did not pass capacity preflight')
    return grant, proposal


class Allowance:
    maximum = 100

    def __init__(self, root, task=None, correction=False):
        self.root, self.task = Path(root), task
        self.path = self.root/RUN/'allowance.json'
        self.grant_path = self.root/AUTHORIZATION
        self.grant, self.proposal = authorization(self.root)
        self.grant_bytes = self.grant_path.read_bytes()
        self.verify()

    def definitions(self):
        return {t['id']: t for t in c.read(c.checked(self.proposal['tasks'], self.root))}

    def ledger(self):
        previous, calls = raw_digest(self.grant_bytes), []
        start = self.proposal['baseline']['combined_used']+1
        for slot, path in enumerate(sorted((self.root/RUN/'reservations').glob('*.json')), start):
            row = c.read(path)
            if path.name != f'{slot:04}.json' or row['previous_hash'] != previous or row['call']['slot'] != slot:
                c.fail('E_INTEGRITY', 'Current review reservation chain changed')
            previous = digest(row)
            calls.append(row['call'])
        if self.path.exists():
            saved = c.read(self.path)
            if (saved['authorization_hash'] != raw_digest(self.grant_bytes)
                    or len(saved['calls']) > len(calls) or saved['calls'] != calls[:len(saved['calls'])]):
                c.fail('E_INTEGRITY', 'Current review projection changed')
        return calls

    def verify(self):
        grant, proposal = authorization(self.root)
        if grant != self.grant or proposal != self.proposal or self.grant_path.read_bytes() != self.grant_bytes:
            c.fail('E_INTEGRITY', 'Current review authorization changed')
        baseline = proposal['baseline']
        issues = Counter(baseline['new_issue_spending'])
        tasks, definitions = Counter(), self.definitions()
        calls = self.ledger()
        for call in calls:
            task = definitions.get(call['task'])
            if (task is None or call['phase'] != 'final' or call['repair'] is not True
                    or call['issues'] != task['issues'] or call['predecessors'] != task['predecessors']
                    or not re.fullmatch('[0-9a-f]{64}', call['request_hash'])
                    or not grant['approved_at'] <= call['issued_at'] < grant['ends_at']):
                c.fail('E_INTEGRITY', 'Invalid current review reservation')
            tasks.update([call['task']])
            issues.update(call['issues'])
        if (baseline['used']+len(calls) > proposal['maximum']
                or baseline['repair_calls']+len(calls) > proposal['repair_maximum']
                or any(n > 2 for n in tasks.values())
                or any(n > (50 if i.startswith('final.') else 4)
                    for i, n in issues.items())):
            c.fail('E_INTEGRITY', 'Current review cumulative quota exceeded')
        pre = c.read(c.checked(proposal['preflight'], self.root))
        corrections = len(calls)-len(tasks)
        if corrections > pre['shared_correction_maximum'] or len(calls) > pre['worst_case_calls']:
            c.fail('E_INTEGRITY', 'Shared review correction pool exceeded')
        combined = Counter(baseline['combined_issue_spending'])
        combined.update(i for call in calls for i in call['issues'])
        return {**baseline, 'used': baseline['used']+len(calls), 'remaining': baseline['remaining']-len(calls),
            'combined_used': baseline['combined_used']+len(calls), 'repair_maximum': 50,
            'repair_calls': baseline['repair_calls']+len(calls),
            'repair_remaining': 50-baseline['repair_calls']-len(calls),
            'review_calls': len(calls), 'correction_calls': corrections,
            'correction_remaining': pre['shared_correction_maximum']-corrections, 'ends_at': grant['ends_at'], 'prior_ends_at': proposal['ends_at'], 'new_issue_spending': dict(issues),
            'combined_issue_spending': dict(combined), 'task_spending': dict(tasks)}

    def reserve(self, request_hash):
        task = self.task
        if task is None:
            c.fail('E_AUTHORITY', 'No declared current review task')
        original = self.definitions().get(task['id'])
        check = deepcopy(task)
        check['request'].pop('correction', None)
        if original != packets.rebind(check) or task.get('counted_repair') is not True:
            c.fail('E_AUTHORITY', 'Current review task differs from approved definitions')
        wire, _, _ = protocol.transport(task)
        if request_hash != digest(wire):
            c.fail('E_INTEGRITY', 'Current review request does not match reservation')
        with (self.root/ex.RUN/'allowance.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = self.verify()
            if not self.grant['approved_at'] <= c.now() < self.grant['ends_at'] or state['remaining'] <= 2 or not state['repair_remaining']:
                c.fail('E_RESOURCE_LIMIT', 'Current review budget, two-call reserve or window exhausted')
            if state['task_spending'].get(task['id'], 0) >= 2:
                c.fail('E_RESOURCE_LIMIT', 'Two attempts exhausted for the current packet')
            if any(state['new_issue_spending'].get(i, 0) >= 50 for i in task['issues']):
                c.fail('E_RESOURCE_LIMIT', 'Cumulative current review issue cap exhausted')
            if state['task_spending'].get(task['id'], 0):
                pending_initial = len(self.definitions())-len(state['task_spending'])
                if (state['correction_remaining'] <= 0 or state['repair_remaining'] <= pending_initial
                        or state['remaining']-2 <= pending_initial):
                    c.fail('E_RESOURCE_LIMIT', 'Shared corrections exhausted; initial coverage remains reserved')
            calls = self.ledger()
            if any(r['task'] == task['id'] and r['request_hash'] == request_hash for r in calls):
                c.fail('E_INTEGRITY', 'Duplicate current review request')
            slot = state['combined_used']+1
            journal = self.root/RUN/'reservations'
            journal.mkdir(exist_ok=True)
            previous = digest(c.read(journal/f'{slot-1:04}.json')) if calls else raw_digest(self.grant_bytes)
            call = {'slot': slot, 'task': task['id'], 'phase': 'final', 'issues': task['issues'],
                'predecessors': task['predecessors'], 'repair': True, 'request_hash': request_hash, 'issued_at': c.now()}
            ex.immutable(journal/f'{slot:04}.json', {'previous_hash': previous, 'call': call})
            c.save(self.path, {'authorization_hash': raw_digest(self.grant_bytes), 'calls': self.ledger()})
            return slot


def engine():
    runtime = ex.engine()
    runtime.RUN, runtime.Allowance = RUN, Allowance
    return runtime


def failure_streak(root):
    rows = [*ex.engine().task_rows(root), *engine().task_rows(root)]
    streak = 0
    for row in sorted((r for r in rows if r.get('allowance_slot')), key=lambda r: r['allowance_slot']):
        streak = streak+1 if ex.master.dependency_failure(row) else 0
    return streak



def dispatchable_tasks(tasks, state, latest, phase_state, streak, active_window):
    if phase_state['halt'] or streak >= 2 or not active_window or state['remaining'] <= 2 or state['repair_remaining'] <= 0:
        return []
    pending = sum(t['id'] not in state['task_spending'] for t in tasks)
    eligible = []
    for task in tasks:
        if phase_state['phases'].get(task['review_phase'], {}).get('status') == 'COMPLETED':
            continue
        spent = state['task_spending'].get(task['id'], 0)
        if spent >= 2 or any(state['new_issue_spending'].get(i, 0) >= 50 for i in task['issues']):
            continue
        if spent == 0:
            eligible.append(task['id'])
        elif (state['correction_remaining'] > 0 and state['repair_remaining'] > pending
                and state['remaining']-2 > pending and latest.get(task['id'], {}).get('status') == 'FAILED'
                and latest[task['id']].get('error') in ('E_REFERENCE', 'E_SCHEMA', 'E_UNSUPPORTED_PROFILE')):
            eligible.append(task['id'])
    return eligible

def summary(root):
    prepared = packets.summary(root, ex)
    if not (root/AUTHORIZATION).exists() and any((root/RUN/'reservations').glob('*.json')):
        c.fail('E_INTEGRITY', 'Current review spending exists without its authorization')
    if prepared is None or not (root/AUTHORIZATION).exists():
        return prepared
    allowance = Allowance(root)
    runtime = engine()
    rows = runtime.task_rows(root)
    calls = {r['slot']: r for r in allowance.ledger()}
    for row in rows:
        task = c.read(root/RUN/'tasks'/row['task']/f"attempt-{row['attempt']:02}"/'task.json')
        wire, schema, reverse = protocol.transport(task)
        call = calls.get(row.get('allowance_slot'))
        if call and (call['task'] != row['task'] or call['request_hash'] != digest(wire)):
            c.fail('E_INTEGRITY', 'Review response detached from charged request')
        if row['status'] == 'VALIDATED':
            folder = runtime.provider_folder(root, call, wire, schema) if call else None
            if folder is None or protocol.validate(c.read(folder/'result.json'), task, reverse) != row['value']:
                c.fail('E_INTEGRITY', 'Review response lacks retained validated provider output')
    state = runtime.state(root)
    latest = {r['task']: r for r in sorted(rows, key=lambda r: r['attempt'])}
    done = all(state['phases'].get(p, {}).get('status') == 'COMPLETED' for p in ('engineering', 'dispositions'))
    current_allowance = allowance.verify()
    eligible = dispatchable_tasks(list(allowance.definitions().values()), current_allowance,
        latest, state, failure_streak(root), allowance.grant['approved_at'] <= c.now() < allowance.grant['ends_at'])
    return {**prepared, 'status': 'HALTED' if state['halt'] else 'COMPLETED_WITH_OPEN_EVIDENCE' if done else 'AUTHORIZED',
        'dispatch_authorized': bool(eligible), 'dispatchable_tasks': eligible,
        'state': state, 'allowance': allowance.verify(), 'attempted_tasks': len(latest),
        'structurally_validated_tasks': sum(r['status'] == 'VALIDATED' for r in latest.values()),
        'unaccounted_slots': sorted(set(calls)-{r['allowance_slot'] for r in rows if r.get('allowance_slot')}),
        'findings': [{'task': r['task'], **f} for r in latest.values() if r['status'] == 'VALIDATED' for f in r['value']['findings']],
        'accepted_substantive_repairs': 0, 'original_obligations_open': 46, 'release_eligible': False}


def refresh(root, reason):
    report = {**summary(root), 'reason': reason, 'refreshed_at': c.now(),
        'next_action': 'Repair concrete reviewer findings; obtain actual assessment period, applicable authority, interpretation and case evidence. No legal closure is inferred.'}
    history = root/RUN/'plan-history'
    history.mkdir(exist_ok=True)
    ex.immutable(history/f'{len(list(history.glob("*.json")))+1:04}.json', report)
    c.save(root/RUN/'next-phase-plan.json', report)
    c.write_text(root/RUN/'next-phase-plan.md', '# Current evidence next phase\n\n'+reason+'\n\n'+report['next_action']+'\n')
    return report


def run(root):
    if not (root/AUTHORIZATION).exists():
        summary(root)
        return None
    started = time.monotonic()
    manifest = ex.verify(root)
    if Path(__file__).resolve().parents[1] != (root/manifest['frozen_root']).resolve():
        c.fail('E_AUTHORITY', 'Current review must execute reviewed frozen code')
    folder = packets.verified(root, ex)
    runtime = engine()
    Allowance(root).verify()
    if runtime.state(root)['halt']:
        return refresh(root, 'Retained stop requires a causal repair')
    complete = all(runtime.state(root)['phases'].get(p, {}).get('status') == 'COMPLETED'
        for p in ('engineering', 'dispositions'))
    if complete:
        return refresh(root, 'Completed provider review retained; later local fixes are separate candidates')
    reviewed = c.read(folder/'run-manifest.json')['frozen_root']
    if reviewed != manifest['frozen_root']:
        c.fail('E_AUTHORITY', 'Incomplete review cannot switch its approved execution revision')
    try:
        tasks = c.read(folder/'task-definitions.json')
        for phase in ('engineering', 'dispositions'):
            if runtime.state(root)['phases'].get(phase, {}).get('status') == 'COMPLETED':
                continue
            refresh(root, phase+' starting from reviewed current inputs')
            for task in (t for t in tasks if t['review_phase'] == phase):
                if failure_streak(root) >= 2:
                    c.fail('E_DEPENDENCY', 'Two consecutive provider failures; no dispatch')
                saved = root/RUN/'tasks'/task['id']/'attempt-02/task.json'
                if saved.exists():
                    row = runtime.attempt(root, c.read(saved), number=2)
                else:
                    row = runtime.attempt(root, task)
                    if (row['status'] != 'VALIDATED' and row.get('allowance_slot')
                            and row.get('error') in ('E_REFERENCE', 'E_SCHEMA', 'E_UNSUPPORTED_PROFILE')
                            and failure_streak(root) < 2 and Allowance(root).verify()['correction_remaining'] > 0):
                        correction = {**row, 'rejected_value': None, 'details': str(row.get('details', ''))[:1800]}
                        row = runtime.attempt(root, task, number=2, correction=correction)
                if row['status'] != 'VALIDATED' and not row.get('allowance_slot'):
                    c.fail(row.get('error', 'E_DEPENDENCY'), row.get('details', 'Uncharged attempt failed before dispatch'))
                refresh(root, 'Retained current review outcome: '+task['id'])
                ex.master.output({'current_review_task': task['id'], 'status': row['status'],
                    'allowance': {k: v for k, v in Allowance(root).verify().items() if k in ('used', 'repair_calls', 'remaining')}})
                if failure_streak(root) >= 2:
                    c.fail('E_DEPENDENCY', 'Two consecutive provider failures; no further dispatch')
            state = runtime.state(root)
            state['phases'][phase] = {'status': 'COMPLETED'}
            c.save(root/RUN/'state.json', state)
            refresh(root, phase+' completed; next phase refreshed from retained findings')
    except (LegalMathError, ValueError, KeyError) as exc:
        state = runtime.state(root)
        state['halt'] = {'error': getattr(exc, 'code', type(exc).__name__), 'details': str(getattr(exc, 'details', exc))[:2500]}
        c.save(root/RUN/'state.json', state)
    report = refresh(root, 'Current review execution checkpoint saved')
    report['wall_seconds'] = round(time.monotonic()-started, 3)
    c.save(root/RUN/'result.json', report)
    return report
