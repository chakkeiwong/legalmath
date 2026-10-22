"""Fresh Codex service calls bound to a separately approved master campaign."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import fcntl
import hashlib
import json
import time
import random
import math
import os

from legalmath.canonical import canonical, digest
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.providers import TerminalServiceFailure
from .bounded_context import require
from .monitor import save


SERVICE_RECOVERY_POLICY = {'profile':'counted-service-recovery.v2',
    'timeout_seconds':300, 'per_request_replacements':3, 'maximum_replacements':48,
    'backoff_seconds':[2, 8, 20]}

SERVICE_CONTINUATION_POLICY = {'profile':'counted-service-recovery.v3',
    'timeout_seconds':300, 'per_request_replacements':3, 'maximum_replacements':48,
    'backoff_seconds':[30, 60, 120], 'maximum_retry_after_seconds':120,
    'jitter_seconds':2, 'consecutive_failure_ceiling':8}

SERVICE_SINGLE_DISPATCH_POLICY = {'profile': 'counted-service-recovery.v4',
    'timeout_seconds': 300, 'per_request_replacements': 0, 'maximum_replacements': 48,
    'backoff_seconds': [30], 'maximum_retry_after_seconds': 120,
    'jitter_seconds': 0, 'consecutive_failure_ceiling': 1}

# New user-authorized hourly recovery has its own ledger. The historical
# 48-replacement reserve is retained, never replenished by this policy.
SERVICE_DELAYED_POLICY = {'profile': 'counted-service-recovery.v5',
    'timeout_seconds': 300, 'per_request_replacements': 24, 'maximum_replacements': 24,
    'backoff_seconds': [3600] + [7200] * 23,
    'maximum_retry_after_seconds': 7200, 'jitter_seconds': 0,
    'consecutive_failure_ceiling': 1}

# Explicit successor inside the original global grant. Its ledger must carry
# the exact 24 prior charges; no request's spent replacement count is reset.
SERVICE_REVIEW_REPAIR_POLICY = {'profile': 'counted-service-recovery.v6',
    'timeout_seconds': 300, 'per_request_replacements': 24, 'maximum_replacements': 88,
    'backoff_seconds': [300] * 88, 'maximum_retry_after_seconds': 7200,
    'jitter_seconds': 0, 'consecutive_failure_ceiling': 1}


def delayed_policy(policy):
    return policy in (SERVICE_DELAYED_POLICY, SERVICE_REVIEW_REPAIR_POLICY)

# A separately reviewed opt-in; v5's historical classification stays intact.
# It shares v5's spent ledger, cooldowns, exact-request checks and deadline.
TERMINAL_CANCELLATION_POLICY = {'profile': 'terminal-no-output-http499.v1',
    'requires_terminal_failed_turn': True, 'requires_no_model_output': True,
    'replacement_reserve': 'EXISTING_DELAYED_SERVICE_LEDGER', 'new_calls': 0}


def recovery_delay(policy, used, details):
    """Never shorten a requested wait to fit our finite recovery allowance."""
    delay = policy['backoff_seconds'][used]
    if delayed_policy(policy):
        require(not details.get('unparsed_retry_after'),
            'Explicit retry wait cannot be parsed; defer request', 'E_RESOURCE_LIMIT')
        requested = details.get('retry_after_seconds') or 0
        require(isinstance(requested, (int, float)) and math.isfinite(requested) and requested >= 0,
            'Invalid retry wait', 'E_RESOURCE_LIMIT')
        return math.ceil(max(delay, requested))
    if policy['profile'] == 'counted-service-recovery.v3':
        require(not details.get('unparsed_retry_after'),
            'Explicit retry wait cannot be parsed; defer request', 'E_RESOURCE_LIMIT')
        requested = details.get('retry_after_seconds') or 0
        require(requested <= policy['maximum_retry_after_seconds'],
            'Requested retry wait exceeds reviewed ceiling; defer request', 'E_RESOURCE_LIMIT')
        delay = math.ceil(max(delay, requested) + random.uniform(0, policy['jitter_seconds']))
    return delay


class CampaignAllowance:
    def __init__(self, directory, routing, *, root):
        self.root = Path(root).resolve()
        self.grant_path = Path(directory) / "live-grant.json"
        self.path = Path(directory) / "live-calls.json"
        self.routing = routing
        self.expected = None
        self.expected_schema = None

    def check(self):
        from .integration_contract import read_evidence as read_raw
        current_path = self.grant_path.with_name('current-binding.json')
        current = None
        historical = {}
        if current_path.exists():
            current = json.loads(current_path.read_text())
            require(current.get('profile') == 'integration-current-binding.v1'
                    and current.get('user_instruction'), 'Invalid current binding', 'E_AUTHORITY')
            read_raw(current['review'], self.root, json_value=False)
            for row in current['historical_archives']:
                old, archive = row['previous'], row['archive']
                key = (old['path'], old['sha256'])
                require(key not in historical and old['sha256'] == archive['sha256'],
                        'Current binding changed historical bytes', 'E_INTEGRITY')
                read_raw(archive, self.root, json_value=False)
                historical[key] = archive
            for reference in current['bindings']:
                read_raw(reference, self.root, json_value=False)
        def read_evidence(reference, root, **kwargs):
            # Historical approvals are verified against their exact retained
            # bytes; current implementation is independently verified above.
            return read_raw(historical.get((reference['path'], reference['sha256']), reference), root, **kwargs)
        grant = json.loads(self.grant_path.read_text())
        require(grant.get("profile") == "integration-master-live-grant.v1" and
                grant.get("approved") is True and grant.get("approval_text"),
                "Missing explicit campaign approval", "E_AUTHORITY")
        proposal = read_evidence(grant["proposal"], self.root)
        require(proposal.get("dispatch_ready") is True, "Campaign proposal is not dispatch-ready", "E_AUTHORITY")
        require(grant["maximum_calls"] == proposal["maximum_calls"] and
                grant["routing_hash"] == digest(self.routing) == proposal["routing_hash"],
                "Approved route or call ceiling changed", "E_AUTHORITY")
        if current is not None:
            require(current['grant_hash'] == digest(grant)
                    and current['maximum_calls'] == grant['maximum_calls']
                    and current['deadline_utc'] == grant['deadline_utc']
                    and current['routing_hash'] == grant['routing_hash'],
                    'Current binding changed grant resources', 'E_AUTHORITY')
        recovery = self.grant_path.with_name('recovery-approval.json')
        reopening_path = self.grant_path.with_name('reopening-binding.json')
        reopening = None
        archives = {}
        correction = None
        correction_archives = {}
        if reopening_path.exists():
            binding = json.loads(reopening_path.read_text())
            require(binding.get('profile') == 'integration-master-reopening-binding.v1'
                    and binding.get('user_instruction') and binding.get('grant_hash') == digest(grant),
                    'Invalid reviewed reopening binding', 'E_AUTHORITY')
            reopening = read_evidence(binding['proposal'], self.root)
            require(reopening['grant_hash'] == digest(grant)
                    and reopening['global_ceiling'] == grant['maximum_calls']
                    and reopening['deadline_utc'] == grant['deadline_utc'],
                    'Reopening changed approved resources', 'E_AUTHORITY')
            read_evidence(reopening['prior_recovery'], self.root)
            correction_path=self.grant_path.with_name('reopening-verification-correction.json')
            if correction_path.exists():
                correction=json.loads(correction_path.read_text())
                require(correction.get('profile')=='integration-master-verification-correction.v1'
                        and correction.get('grant_hash')==digest(grant)
                        and correction.get('prior_binding')=={
                            'path':str(reopening_path.relative_to(self.root)),
                            'sha256':__import__('hashlib').sha256(reopening_path.read_bytes()).hexdigest()},
                        'Invalid one-time verification correction','E_AUTHORITY')
                read_evidence(correction['review'],self.root,json_value=False)
                current_bindings={r['path']:r for r in reopening['bindings']}
                for row in correction['replacements']:
                    previous=row['previous']; key=(previous['path'],previous['sha256'])
                    require(key not in correction_archives and current_bindings.get(previous['path'])==previous
                            and row['archive']['sha256']==previous['sha256']
                            and row['current']['path']==previous['path'],
                            'Correction changed historical implementation','E_AUTHORITY')
                    read_evidence(row['archive'],self.root,json_value=False)
                    read_evidence(row['current'],self.root,json_value=False)
                    correction_archives[key]=row['archive']
            for row in reopening['historical_bindings']:
                key = (row['previous']['path'], row['previous']['sha256'])
                require(key not in archives and row['archive']['sha256'] == key[1],
                        'Invalid historical reopening archive')
                read_evidence(row['archive'], self.root, json_value=False)
                archives[key] = row['archive']
            for reference in reopening['bindings']:
                read_evidence(correction_archives.get((reference['path'],reference['sha256']),reference),
                              self.root, json_value=False)
        def verify_binding(reference):
            archived = archives.get((reference['path'], reference['sha256']), reference)
            read_evidence(archived, self.root, json_value=False)
        migration = None
        if recovery.exists():
            approval = json.loads(recovery.read_text())
            require(approval.get('profile') == 'integration-master-recovery-approval.v1' and
                    approval.get('approved') is True and approval.get('approval_text') and
                    approval.get('grant_hash') == digest(grant), 'Invalid recovery approval', 'E_AUTHORITY')
            migration = read_evidence(approval['proposal'], self.root)
            require(migration['grant_hash'] == digest(grant) and migration['global_ceiling'] == grant['maximum_calls']
                    and migration['deadline_utc'] == grant['deadline_utc'], 'Recovery changed authority', 'E_AUTHORITY')
            replacements = {row['previous']['path']: row for row in migration['replacements']}
            require(len(replacements) == len(migration['replacements']), 'Duplicate recovery replacement')
            for reference in proposal['bindings']:
                if reference['path'] in replacements:
                    row = replacements[reference['path']]
                    require(row['previous'] == reference and row['archive']['sha256'] == reference['sha256'] and
                            row['current']['path'] == reference['path'], 'Recovery archive differs from approved code')
                    read_evidence(row['archive'], self.root, json_value=False)
                    verify_binding(row['current'])
                else:
                    verify_binding(reference)
            for reference in migration['bindings']:
                verify_binding(reference)
        else:
            for reference in proposal["bindings"]:
                verify_binding(reference)
        from .time_authority import effective_deadline
        deadline = effective_deadline(self.root, self.grant_path.parent, grant=grant, binding=current)
        remaining = (datetime.fromisoformat(deadline) - datetime.now(timezone.utc)).total_seconds()
        require(remaining >= 305, "Insufficient approved deadline for one complete call", "E_AUTHORITY")
        require((datetime.fromisoformat(grant["deadline_utc"]) -
                 datetime.fromisoformat(grant["started_utc"])).total_seconds() <= proposal["window_seconds"],
                "Approved service window was extended", "E_AUTHORITY")
        require(datetime.fromisoformat(grant['started_utc']) <= datetime.now(timezone.utc),
                'Service window has not started', 'E_AUTHORITY')
        state = json.loads(self.path.read_text()) if self.path.exists() else {
            "grant_hash": digest(grant), "maximum": grant["maximum_calls"], "calls": []}
        require(state["grant_hash"] == digest(grant) and state["maximum"] == grant["maximum_calls"] and
                len(state["calls"]) <= state["maximum"], "Campaign ledger changed")
        if migration is not None:
            before = read_evidence(migration['ledger_before'], self.root)
            require(state['grant_hash'] == before['grant_hash'] and state['maximum'] == before['maximum'] and
                    state['calls'][:len(before['calls'])] == before['calls'], 'Recovery changed prior charges')
        if reopening is not None:
            before = read_evidence(reopening['ledger_before'], self.root)
            require(state['grant_hash'] == before['grant_hash'] and state['maximum'] == before['maximum']
                    and state['calls'][:len(before['calls'])] == before['calls'],
                    'Reopening changed prior charges')
        if correction is not None:
            before=read_evidence(correction['ledger_before'],self.root)
            require(state['grant_hash']==before['grant_hash'] and state['maximum']==before['maximum']
                    and state['calls'][:len(before['calls'])]==before['calls'],
                    'Verification correction changed prior charges')
        if current is not None:
            before = read_raw(current['ledger_before'], self.root)
            require(state['grant_hash'] == before['grant_hash'] and state['maximum'] == before['maximum']
                    and state['calls'][:len(before['calls'])] == before['calls'],
                    'Current binding changed prior charges', 'E_INTEGRITY')
        return state

    def reserve(self, request_hash):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = self.check()
            require(request_hash == self.expected, "Unbound service dispatch", "E_AUTHORITY")
            require(len(state["calls"]) < state["maximum"], "Approved campaign call ceiling", "E_RESOURCE_LIMIT")
            stage_hash = None
            budget_owner = None
            if self.grant_path.with_name('current-binding.json').exists():
                from .integration_contract import read_evidence
                pointer = json.loads(self.grant_path.with_name('current-stage.json').read_text())
                stage = read_evidence(pointer, self.root)
                require(stage['grant_hash'] == state['grant_hash']
                        and stage['binding_hash'] == digest(json.loads(self.grant_path.with_name('current-binding.json').read_text())),
                        'Unbound current stage', 'E_AUTHORITY')
                before = read_evidence(stage['ledger_before'], self.root)
                require(state['calls'][:len(before['calls'])] == before['calls'], 'Stage lost earlier charges', 'E_INTEGRITY')
                used = (sum(row.get('stage_hash') == pointer['sha256'] for row in state['calls'])
                    if stage.get('profile') == 'integration-current-stage.v2'
                    else len(state['calls']) - len(before['calls']))
                require(0 < stage['maximum_calls'] <= state['maximum'] - len(before['calls'])
                        and used < stage['maximum_calls'],
                        'Current stage call ceiling reached', 'E_RESOURCE_LIMIT')
                if stage.get('profile') == 'integration-current-stage.v2':
                    stage_hash = pointer['sha256']
                    if json.loads(self.grant_path.with_name('current-binding.json').read_text()).get('execution_budget'):
                        from .phased.branch_budget import check as check_budget
                        budget_owner = stage['owner']
                        check_budget(self.root, json.loads(self.grant_path.with_name('current-binding.json').read_text()),
                            state, budget_owner)
            self.service_circuit(reserving=True)
            state["calls"].append({"request_hash": request_hash, "issued_at_ns": str(time.time_ns()),
                **({'owner': budget_owner} if budget_owner else {}),
                **({'stage_hash': stage_hash} if stage_hash else {})})
            save(self.path, state)
            return len(state["calls"])

    def service_recovery_policy(self):
        from .integration_contract import read_evidence
        pointer = self.grant_path.with_name('current-stage.json')
        if not pointer.exists():
            return None
        stage = read_evidence(json.loads(pointer.read_text()), self.root)
        policy = stage.get('service_recovery_policy')
        if policy is None:
            return None
        binding = json.loads(self.grant_path.with_name('current-binding.json').read_text())
        require(policy == binding.get('service_recovery_policy') and
                policy in (SERVICE_RECOVERY_POLICY, SERVICE_CONTINUATION_POLICY,
                           SERVICE_SINGLE_DISPATCH_POLICY, SERVICE_DELAYED_POLICY, SERVICE_REVIEW_REPAIR_POLICY),
                'Unbound service recovery policy', 'E_AUTHORITY')
        require(stage.get('service_recovery_maximum') == policy['maximum_replacements'],
                'Unreviewed service replacement ceiling', 'E_AUTHORITY')
        return policy

    def terminal_cancellation_enabled(self):
        binding = json.loads(self.grant_path.with_name('current-binding.json').read_text())
        selected = binding.get('terminal_cancellation_recovery')
        if selected is None:
            return False
        require(selected == TERMINAL_CANCELLATION_POLICY
            and delayed_policy(binding.get('service_recovery_policy')),
            'Unreviewed terminal cancellation recovery', 'E_AUTHORITY')
        return True

    def service_scope(self):
        from .integration_contract import read_evidence
        pointer = json.loads(self.grant_path.with_name('current-stage.json').read_text())
        stage = read_evidence(pointer, self.root)
        scope = stage.get('service_scope')
        if scope is None:
            return pointer, (self.root / pointer['path']).parent, None
        binding = json.loads(self.grant_path.with_name('current-binding.json').read_text())
        require(scope == binding.get('phase_service_scope'), 'Unbound shared service scope', 'E_AUTHORITY')
        value = read_evidence(scope, self.root)
        scope_review = binding['review']
        ancestor = binding
        visited = set()
        while ancestor.get('phase_service_predecessor') is not None:
            inherited = ancestor['phase_service_predecessor']
            require(inherited == ancestor.get('predecessor'),
                    'Service scope predecessor is not the binding predecessor', 'E_AUTHORITY')
            identity = (inherited['path'], inherited['sha256'])
            require(identity not in visited, 'Cyclic service scope inheritance', 'E_INTEGRITY')
            visited.add(identity)
            previous = read_evidence(inherited, self.root)
            require(previous.get('phase_service_scope') == scope and
                    previous.get('grant_hash') == binding.get('grant_hash') == stage['grant_hash'],
                    'Inherited service scope changed grant or identity', 'E_AUTHORITY')
            scope_review = previous['review']
            ancestor = previous
        require(value['grant_hash'] == stage['grant_hash'] and value['review'] == scope_review,
                'Service scope changed authority', 'E_AUTHORITY')
        return scope, (self.root / scope['path']).parent, value

    def service_circuit(self, *, failure=None, success=False, reserving=False):
        """Persist an outage stop across provider forks and process reloads."""
        policy = self.service_recovery_policy()
        if not policy or policy.get('consecutive_failure_ceiling') is None:
            return
        pointer, directory, scope = self.service_scope()
        path = directory/'service-circuit.json'
        with (directory/'service-circuit.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = json.loads(path.read_text()) if path.exists() else {
                'stage_hash':pointer['sha256'], 'consecutive_failures':0,
                'failed_slots':[], 'open':False}
            require(state['stage_hash']==pointer['sha256'], 'Service circuit stage changed', 'E_INTEGRITY')
            if failure is not None:
                if failure.allowance_slot not in state['failed_slots']:
                    state['failed_slots'].append(failure.allowance_slot)
                    state['consecutive_failures'] += 1
                    state['open'] = state['open'] or state['consecutive_failures'] >= policy['consecutive_failure_ceiling']
                    state.pop('half_open_request_hash', None)
                    state.pop('half_open_schema_hash', None)
                    state.pop('half_open_reserved', None)
            elif success and not state['open']:
                state['consecutive_failures'] = 0
                state.pop('half_open_request_hash', None)
                state.pop('half_open_schema_hash', None)
                state.pop('half_open_reserved', None)
            if failure is not None or success:
                save(path, state)
            if success:
                return
            if failure is not None and delayed_policy(policy):
                return  # Persist the outage before scheduling its counted wait.
            require(not state['open'],
                'Shared service circuit open after repeated terminal failures; stage requires reviewed continuation',
                'E_RESOURCE_LIMIT')
            if state.get('half_open_request_hash'):
                require(state['half_open_request_hash'] == self.expected
                    and state.get('half_open_schema_hash') == self.expected_schema
                    and not state.get('half_open_reserved'),
                    'Only the scheduled service retry may probe the open circuit', 'E_RESOURCE_LIMIT')
                if reserving:
                    state['half_open_reserved'] = True
                    save(path, state)

    def reserve_service_recovery(self, failure):
        """Retain a finite replacement charge only for proved no-output failures."""
        from .integration_contract import read_evidence
        from legalmath.interpretation.search.providers import transient_service_details, TerminatedCallTimeout, retry_output_present
        policy = self.service_recovery_policy()
        require(policy is not None, 'Missing service recovery policy', 'E_AUTHORITY')
        stage_pointer = json.loads(self.grant_path.with_name('current-stage.json').read_text())
        stage = read_evidence(stage_pointer, self.root)
        pointer, recovery_directory, scope = self.service_scope()
        directory = self.path.parent/'provider-evidence'/f'{failure.allowance_slot:04}-{failure.request_hash[:16]}'
        manifest = json.loads((directory/'manifest.json').read_text())
        require(manifest['allowance_slot'] == failure.allowance_slot and
            manifest['request_hash'] == failure.request_hash and not manifest['complete_output_present'],
            'Service replacement lacks exact no-output receipt', 'E_INTEGRITY')
        def retained(name):
            data = (directory/name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == manifest['files'][name]['retained_sha256'],
                'Service receipt changed', 'E_INTEGRITY')
            return data
        events = [json.loads(line) for line in retained('events.jsonl').splitlines() if line.strip()]
        if policy == SERVICE_REVIEW_REPAIR_POLICY:
            require(not (directory/'result.json').exists() and 'result.json' not in manifest['files']
                and not retry_output_present(events, allow_blank_messages=True),
                'Ended failure contains output or ambiguous events; inspect before retry', 'E_AUTHORITY')
        require(not any(e.get('type') == 'turn.completed' for e in events),
            'Completed turn cannot receive no-output replacement', 'E_AUTHORITY')
        details = {}
        if isinstance(failure, TerminatedCallTimeout):
            ended = json.loads(retained('termination.json'))
            require(ended.get('reason') == 'LOCAL_DEADLINE' and ended.get('process_terminated') is True
                and ended.get('returncode') is not None and not ended.get('complete_output_present')
                and not ended.get('completed_turn_present'), 'Timeout termination not established', 'E_AUTHORITY')
            if delayed_policy(policy):
                require(not any(e.get('type') == 'error' or
                    (policy == SERVICE_REVIEW_REPAIR_POLICY and e.get('type') == 'turn.failed') for e in events)
                    or transient_service_details(events, output_present=False,
                        allow_terminal_499=self.terminal_cancellation_enabled(),
                        allow_terminal_timeout=policy == SERVICE_REVIEW_REPAIR_POLICY) is not None,
                    'Ended timeout also contains a nonservice error; inspect before retry', 'E_AUTHORITY')
                require(not retry_output_present(events,
                    allow_blank_messages=policy == SERVICE_REVIEW_REPAIR_POLICY),
                    'Ended timeout contains model output; inspect before retry', 'E_AUTHORITY')
        else:
            details = transient_service_details(events, output_present=False,
                allow_terminal_499=self.terminal_cancellation_enabled(),
                allow_terminal_timeout=policy == SERVICE_REVIEW_REPAIR_POLICY)
            require(details is not None,
                'Unclassified failure cannot receive replacement', 'E_AUTHORITY')
        ledger = recovery_directory/'service-recovery.json'
        with (recovery_directory/'service-recovery.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = json.loads(ledger.read_text()) if ledger.exists() else {
                'profile':policy['profile'], 'stage_hash':pointer['sha256'],
                'maximum':policy['maximum_replacements'], 'charges':[]}
            require(state.get('profile') == policy['profile'] and state['stage_hash'] == pointer['sha256'] and
                state['maximum'] == policy['maximum_replacements'], 'Recovery stage changed', 'E_INTEGRITY')
            if policy == SERVICE_REVIEW_REPAIR_POLICY:
                binding = json.loads(self.grant_path.with_name('current-binding.json').read_text())
                previous = read_evidence(binding['review_repair_service_predecessor'], self.root)
                require(previous['profile'] == SERVICE_DELAYED_POLICY['profile']
                    and len(previous['charges']) == previous['maximum'] == 24
                    and state['charges'][:24] == previous['charges'],
                    'Lost prior delayed recovery charges', 'E_INTEGRITY')
            require(len(state['charges']) < state['maximum'], 'Stage replacement reserve exhausted', 'E_RESOURCE_LIMIT')
            require(all(r['failed_slot'] != failure.allowance_slot for r in state['charges']),
                'Failure already received a replacement reservation', 'E_AUTHORITY')
            used = sum(r['request_hash'] == failure.request_hash for r in state['charges'])
            require(used < policy['per_request_replacements'], 'Request replacements exhausted', 'E_RESOURCE_LIMIT')
            # The hourly schedule is shared across this continuation, so moving
            # to another request does not reset subsequent waits to one hour.
            delay = recovery_delay(policy, len(state['charges']) if delayed_policy(policy) else used, details)
            charge = {'failed_slot':failure.allowance_slot, 'request_hash':failure.request_hash,
                'failure_kind':type(failure).__name__, 'backoff_seconds':delay,
                'evidence':str((directory/'manifest.json').relative_to(self.root))}
            if delayed_policy(policy):
                request_data, schema_data = retained('request.json'), retained('schema.json')
                require(digest(json.loads(request_data)) == failure.request_hash == self.expected
                    and digest(json.loads(schema_data)) == self.expected_schema,
                    'Delayed replacement changed its exact request or schema', 'E_INTEGRITY')
                now = datetime.now(timezone.utc)
                due = now + timedelta(seconds=delay)
                from .time_authority import effective_deadline
                deadline = datetime.fromisoformat(effective_deadline(self.root, self.grant_path.parent))
                require(due + timedelta(seconds=policy['timeout_seconds'] + 5) <= deadline,
                    'Delayed retry cannot finish within original grant deadline', 'E_AUTHORITY')
                charge.update(scheduled_at_utc=now.isoformat(), next_retry_at_utc=due.isoformat(),
                    schema_hash=self.expected_schema, stage=stage_pointer,
                    receipt_sha256=hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest(),
                    worker={'pid': os.getpid(),
                        'start': Path('/proc/self/stat').read_text().rsplit(') ', 1)[1].split()[19]})
            state['charges'].append(charge)
            save(ledger, state)
            return delay

    def wait_service_recovery(self, failure):
        """Wait on the retained UTC schedule, then admit one exact probe."""
        policy = self.service_recovery_policy()
        require(delayed_policy(policy),
            'Hourly wait lacks its bound policy', 'E_AUTHORITY')
        pointer, directory, _ = self.service_scope()
        ledger_path = directory / 'service-recovery.json'
        ledger = json.loads(ledger_path.read_text())
        require(ledger['profile'] == policy['profile']
            and ledger['stage_hash'] == pointer['sha256']
            and ledger['maximum'] == policy['maximum_replacements']
            and 0 < len(ledger['charges']) <= ledger['maximum'],
            'Delayed retry ledger changed', 'E_INTEGRITY')
        matches = [r for r in ledger['charges'] if r['failed_slot'] == failure.allowance_slot]
        require(len(matches) == 1 and matches[0]['request_hash'] == failure.request_hash == self.expected
            and matches[0]['schema_hash'] == self.expected_schema,
            'Delayed retry has no unique reservation', 'E_AUTHORITY')
        charge = matches[0]
        due = datetime.fromisoformat(charge['next_retry_at_utc'])
        scheduled = datetime.fromisoformat(charge['scheduled_at_utc'])
        require(due.tzinfo is not None and scheduled.tzinfo is not None
            and (due - scheduled).total_seconds() == charge['backoff_seconds']
            and charge['backoff_seconds'] >= policy['backoff_seconds'][ledger['charges'].index(charge)],
            'Delayed retry was shortened or lost its UTC schedule', 'E_INTEGRITY')
        def unchanged():
            require(json.loads(ledger_path.read_text()) == ledger
                and json.loads(self.grant_path.with_name('current-stage.json').read_text()) == charge['stage']
                and hashlib.sha256((self.root / charge['evidence']).read_bytes()).hexdigest() == charge['receipt_sha256'],
                'Delayed retry evidence changed during wait', 'E_INTEGRITY')
        while True:
            self.check()
            unchanged()
            remaining = (due - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(60, remaining))
        with (directory / 'service-circuit.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            path = directory / 'service-circuit.json'
            state = json.loads(path.read_text())
            unchanged()
            require(state['stage_hash'] == pointer['sha256'] and state['open']
                and state['failed_slots'][-1] == failure.allowance_slot,
                'Delayed retry circuit changed during wait', 'E_AUTHORITY')
            state.update(open=False, half_open_request_hash=failure.request_hash,
                half_open_schema_hash=self.expected_schema,
                half_open_reserved=False, resumed_after_slot=failure.allowance_slot,
                resumed_at_utc=datetime.now(timezone.utc).isoformat())
            save(path, state)

    def reserve_terminal_recovery(self, failure):
        """Spend one reviewed semantic-stage recovery after an archived terminal failure."""
        from .integration_contract import read_evidence
        from .bounded_context import require
        pointer_path = self.grant_path.with_name('current-stage.json')
        require(pointer_path.exists(), 'Terminal recovery has no bound stage', 'E_AUTHORITY')
        stage_ref = json.loads(pointer_path.read_text())
        stage = read_evidence(stage_ref, self.root)
        maximum = stage.get('terminal_recovery_maximum', 0)
        policy = stage.get('terminal_recovery_policy')
        if policy:
            binding = json.loads(self.grant_path.with_name('current-binding.json').read_text())
            require(policy == binding.get('terminal_recovery_policy') and
                policy == {'profile': 'scoped-terminal-recovery.v1', 'maximum_replacements': 12,
                           'per_request_replacements': 1, 'prior_replacements_retained': 2},
                'Unbound terminal recovery policy', 'E_AUTHORITY')
        require(stage.get('name') == 'semantic-preflight' and type(maximum) is int and
                0 < maximum <= (12 if policy else 2),
                'Terminal recovery is outside reviewed semantic stage', 'E_AUTHORITY')
        evidence = self.path.parent/'provider-evidence'/(
            f'{failure.allowance_slot:04}-{failure.request_hash[:16]}')
        manifest = json.loads((evidence/'manifest.json').read_text())
        require(manifest['allowance_slot'] == failure.allowance_slot and
                manifest['request_hash'] == failure.request_hash and
                not manifest['complete_output_present'] and
                'events.jsonl' in manifest['files'],
                'Terminal recovery lacks exact no-output evidence', 'E_INTEGRITY')
        require(hashlib.sha256((evidence/'events.jsonl').read_bytes()).hexdigest() ==
                manifest['files']['events.jsonl']['retained_sha256'],
                'Terminal event receipt changed', 'E_INTEGRITY')
        events = [json.loads(line) for line in (evidence/'events.jsonl').read_text().splitlines() if line.strip()]
        from legalmath.interpretation.search.providers import terminal_service_error
        require(terminal_service_error(events, output_present=False) is not None,
                'Prior failure is not a classified terminal service error', 'E_AUTHORITY')
        path = self.root/stage_ref['path']
        ledger = path.parent/'terminal-recovery.json'
        with (path.parent/'terminal-recovery.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = json.loads(ledger.read_text()) if ledger.exists() else {
                'profile':'semantic-terminal-recovery.v1',
                'stage_hash':stage_ref['sha256'],'maximum':maximum,'charges':[]}
            require(state['profile']=='semantic-terminal-recovery.v1' and
                    state['stage_hash']==stage_ref['sha256'] and state['maximum']==maximum,
                    'Terminal recovery record changed', 'E_INTEGRITY')
            require(len(state['charges']) < maximum, 'Terminal recovery allowance exhausted', 'E_RESOURCE_LIMIT')
            require(all(row['failed_slot'] != failure.allowance_slot for row in state['charges']),
                    'Terminal failure already granted recovery', 'E_AUTHORITY')
            # The global ledger is checked again by the next reserve. A crash
            # after this write consumes the recovery; it does not redispatch.
            state['charges'].append({'failed_slot':failure.allowance_slot,
                'request_hash':failure.request_hash,
                'evidence':str(evidence.relative_to(self.root))+'/manifest.json'})
            save(ledger, state)
            return len(state['charges'])

    def terminal_recovery_enabled(self):
        from .integration_contract import read_evidence
        pointer = self.grant_path.with_name('current-stage.json')
        if not pointer.exists():
            return False
        stage = read_evidence(json.loads(pointer.read_text()), self.root)
        return stage.get('name') == 'semantic-preflight' and stage.get('terminal_recovery_maximum', 0) > 0

    def terminal_recovery_attempts(self):
        from .integration_contract import read_evidence
        pointer = self.grant_path.with_name('current-stage.json')
        if not pointer.exists():
            return 0
        stage = read_evidence(json.loads(pointer.read_text()), self.root)
        return 1 if stage.get('terminal_recovery_policy') else 2


class BoundedCodexProvider(CodexProvider):
    bounded_authorized = True
    reference_transport = True

    def __init__(self, root, directory, encode, limits, *, routing_file=None):
        super().__init__(routing_file=routing_file)
        require(bool(self.routing["model"]), "Campaign must select an explicit model", "E_AUTHORITY")
        self.allowance = CampaignAllowance(directory, self.routing, root=root)
        self.encode, self.limits = encode, limits
        self._arguments = (root, directory, encode, limits)
        self._routing_file = routing_file
        self.acquisition_workers = 2
        binding = self.allowance.grant_path.with_name('current-binding.json')
        self.retry_terminal_499 = self.allowance.terminal_cancellation_enabled() if binding.exists() else False
        self.retry_terminal_timeout = (binding.exists() and
            json.loads(binding.read_text()).get('service_recovery_policy') == SERVICE_REVIEW_REPAIR_POLICY)
        if binding.exists() and delayed_policy(json.loads(binding.read_text()).get('service_recovery_policy')):
            self.acquisition_workers = 1

    def fork(self):
        return type(self)(*self._arguments, routing_file=self._routing_file)

    def check(self):
        state = self.allowance.check()
        require(len(state['calls']) < state['maximum'], 'Campaign exhausted', 'E_AUTHORITY')
        return state

    def measure(self, request, schema):
        command = self.command(Path("/tmp/legalmath-provider-measure"), Path("schema.json"), Path("result.json"))
        instructions = next(x for x in command if x.startswith("developer_instructions="))
        wire = canonical({"request": request, "response_schema": schema, "developer_instructions": instructions})
        result = {"bytes": len(wire), "local_tokens": len(self.encode(wire.decode())),
                  "service_framing": "CLI_INTERNALS_UNMEASURED; ACTUAL_USAGE_RETAINED"}
        from .phased.account_input import input_token_limit
        from .phased.downstream_input import input_byte_limit
        require(result["bytes"] <= input_byte_limit(request, self.limits) and
                result["local_tokens"] <= input_token_limit(request, self.limits),
                {"stage": "PROVIDER_VISIBLE_INPUT", **result}, "E_RESOURCE_LIMIT")
        return result

    def complete(self, request, schema, settings):
        policy = (self.allowance.service_recovery_policy()
            if hasattr(self.allowance, 'service_recovery_policy') else None)
        if delayed_policy(policy):
            # One live request owns an hourly wait. Independent local work can
            # continue, but a second process cannot steal its half-open probe.
            _, directory, _ = self.allowance.service_scope()
            with (directory / 'service-worker.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self._complete(request, schema, settings)
        return self._complete(request, schema, settings)

    def _complete(self, request, schema, settings):
        self.check()
        measurement = self.measure(request, schema)
        self.allowance.expected = digest(request)
        self.allowance.expected_schema = digest(schema)
        policy = (self.allowance.service_recovery_policy()
            if hasattr(self.allowance, 'service_recovery_policy') else None)
        timeout = policy['timeout_seconds'] if policy else 120
        replacements = (self.allowance.terminal_recovery_attempts()
            if hasattr(self.allowance, 'terminal_recovery_attempts') else 2)
        if policy:
            require(settings.timeout_seconds == timeout, 'Dispatch/provider timeout disagreement', 'E_INTEGRITY')
            replacements = policy['per_request_replacements']
        for attempt in range(replacements + 1):
            if hasattr(self.allowance, 'service_circuit'):
                self.allowance.service_circuit()
            try:
                response = super().complete(request, schema, settings.model_copy(update={'timeout_seconds': timeout}))
                if hasattr(self.allowance, 'service_circuit'):
                    self.allowance.service_circuit(success=True)
                break
            except TerminalServiceFailure as failure:
                if policy:
                    if hasattr(self.allowance, 'service_circuit'):
                        self.allowance.service_circuit(failure=failure)
                    if attempt == replacements:
                        raise
                    delay = self.allowance.reserve_service_recovery(failure)
                    self.check()
                    if delayed_policy(policy):
                        self.allowance.wait_service_recovery(failure)
                    else:
                        time.sleep(delay)
                    continue
                from legalmath.interpretation.search.providers import TerminatedCallTimeout
                if isinstance(failure, TerminatedCallTimeout):
                    raise
                if attempt == replacements or not self.allowance.terminal_recovery_enabled():
                    raise
                self.allowance.reserve_terminal_recovery(failure)
                self.check()
        from .phased.account_output import output_token_limit
        require(len(self.encode(canonical(response.value).decode())) <= output_token_limit(request, self.limits),
                "Actual provider output exceeds local token allowance", "E_RESOURCE_LIMIT")
        from legalmath.interpretation.search.providers import Completion
        return Completion(response.value, {**response.provenance, "visible_input_measurement": measurement,
            'effective_timeout_seconds':timeout, 'application_replacements':attempt,
            'transport_retry_policy':'COUNTED_BOUND_STAGE_REPLACEMENTS' if policy else 'LEGACY_TERMINAL_POLICY',
            "tokenizer_equivalence": "NOT_ESTABLISHED", "provider_framing_equivalence": "NOT_ESTABLISHED"})
