"""Idempotent per-phase admission with exclusive stage charge accounting."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from legalmath.canonical import digest
from ..bounded_context import require
from ..integration_contract import evidence_file, read_evidence
from ..monitor import save


def admit(root, base, live, name, logical_calls, *, owner):
    root, base, live = Path(root), Path(base), Path(live)
    require(re.fullmatch(r'[a-zA-Z0-9_.-]+', name) and
            re.fullmatch(r'[a-zA-Z0-9_.-]+', owner), 'Unsafe phase identity', 'E_AUTHORITY')
    require(type(logical_calls) is int and logical_calls > 0, 'Invalid phase population')
    binding = json.loads((root / base / 'current-binding.json').read_text())
    grant = json.loads((root / base / 'live-grant.json').read_text())
    from ..time_authority import effective_deadline
    deadline = effective_deadline(root, root / base, grant=grant, binding=binding)
    ledger = json.loads((root / base / 'live-calls.json').read_text())
    from .branch_budget import check as check_budget
    check_budget(root, binding, ledger, owner, logical_calls)
    policy = binding['service_recovery_policy']
    maximum = logical_calls + min(policy['maximum_replacements'],
                                   logical_calls * policy['per_request_replacements'])
    folder = root / live / 'phases' / owner / name
    path = folder / 'stage.json'
    if path.exists():
        stage = json.loads(path.read_text())
        require(stage['binding_hash'] == digest(binding) and stage['maximum_calls'] == maximum
                and stage['logical_calls'] == logical_calls and stage['owner'] == owner,
                'Changed phase admission on resume', 'E_AUTHORITY')
    else:
        remaining = grant['maximum_calls'] - len(ledger['calls'])
        require(maximum <= remaining, 'Phase exceeds remaining global calls', 'E_RESOURCE_LIMIT')
        seconds = (datetime.fromisoformat(deadline) - datetime.now(timezone.utc)).total_seconds()
        replacements = maximum - logical_calls
        bound = maximum * policy['timeout_seconds'] + replacements * (
            max(max(policy['backoff_seconds']), policy.get('maximum_retry_after_seconds', 0))
            + policy.get('jitter_seconds', 0)) + 305
        from ..bounded_provider import delayed_policy
        if delayed_policy(policy):
            # Hourly outages are contingencies, not required work. Each actual
            # wait and retry separately checks the unchanged global deadline.
            bound = logical_calls * policy['timeout_seconds'] + 305
        require(bound <= seconds, 'Phase exceeds original global window', 'E_RESOURCE_LIMIT')
        save(folder / 'ledger-before.json', ledger)
        stage = {'profile': 'integration-current-stage.v2', 'name': name, 'owner': owner,
            'maximum_calls': maximum, 'logical_calls': logical_calls,
            'grant_hash': digest(grant), 'binding_hash': digest(binding),
            'ledger_before': evidence_file(folder / 'ledger-before.json', root),
            'deadline_utc': deadline, 'review': binding['review'],
            'service_recovery_policy': policy, 'service_recovery_maximum': policy['maximum_replacements'],
            'service_scope': binding['phase_service_scope']}
        save(path, stage)
    pointer = evidence_file(path, root)
    before = read_evidence(stage['ledger_before'], root)
    require(ledger['calls'][:len(before['calls'])] == before['calls'], 'Lost prior charges', 'E_INTEGRITY')
    used = sum(r.get('stage_hash') == pointer['sha256'] for r in ledger['calls'])
    require(used <= maximum, 'Phase charges exceed reservation', 'E_INTEGRITY')
    save(root / base / 'current-stage.json', pointer)
    return pointer
