"""Explicit time extensions preserve the original grant and cumulative ledger."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from legalmath.canonical import digest
from .bounded_context import require
from .integration_contract import read_evidence

PROFILE = 'integration-time-extension.v1'
USER = 'you have 48 hours more.  continue the execution'
CONTINUATION_PROFILE = 'integration-time-extension.v2'
CONTINUATION_USER = 'you have 72 hours more.'


def effective_deadline(root, directory, *, grant=None, binding=None):
    root, directory = Path(root), Path(directory)
    grant = grant if grant is not None else json.loads((directory/'live-grant.json').read_text())
    binding_path = directory/'current-binding.json'
    binding = binding if binding is not None else (json.loads(binding_path.read_text()) if binding_path.exists() else {})
    pointer = binding.get('time_extension')
    if pointer is None:
        require('effective_deadline_utc' not in binding, 'Unbound extended deadline', 'E_AUTHORITY')
        return grant['deadline_utc']
    extension = read_evidence(pointer, root)
    continuation = extension.get('profile') == CONTINUATION_PROFILE
    duration, instruction, program_key = ((259200, CONTINUATION_USER, 'time_continuation') if continuation
        else (172800, USER, 'synthesis_continuation'))
    require(extension.get('profile') in (PROFILE, CONTINUATION_PROFILE) and extension.get('approved') is True
        and extension.get('user_instruction') == instruction
        and extension.get('duration_seconds') == duration, 'Missing explicit time authority', 'E_AUTHORITY')
    original = read_evidence(extension['original_grant'], root)
    require(original == grant and extension['original_grant_hash'] == digest(grant)
        and extension['maximum_calls'] == grant['maximum_calls']
        and binding['grant_hash'] == digest(grant)
        and binding['deadline_utc'] == grant['deadline_utc'], 'Extension changed original authority', 'E_AUTHORITY')
    approved = datetime.fromisoformat(extension['approved_at_utc'])
    deadline = datetime.fromisoformat(extension['deadline_utc'])
    require(approved.tzinfo is not None and deadline.tzinfo is not None
        and deadline == approved + timedelta(seconds=duration)
        and deadline > datetime.fromisoformat(grant['deadline_utc'])
        and approved <= datetime.now(timezone.utc), 'Invalid extension clock', 'E_AUTHORITY')
    require(binding.get('effective_deadline_utc') == extension['deadline_utc']
        and binding.get('review') == extension['review'], 'Unbound extension review or deadline', 'E_AUTHORITY')
    read_evidence(extension['review'], root, json_value=False)
    program = read_evidence(binding['program'], root)
    require(program.get(program_key, {}).get('time_extension') == pointer
        and program['deadline_utc'] == extension['deadline_utc'], 'Extension differs from current program', 'E_AUTHORITY')
    before = read_evidence(extension['ledger_before'], root)
    current = json.loads((directory/'live-calls.json').read_text())
    require(before['grant_hash'] == current['grant_hash'] == digest(grant)
        and before['maximum'] == current['maximum'] == grant['maximum_calls']
        and len(before['calls']) == extension['prior_calls']
        and current['calls'][:len(before['calls'])] == before['calls']
        and len(current['calls']) <= current['maximum'], 'Extension lost cumulative charges', 'E_INTEGRITY')
    if continuation:
        previous = read_evidence(extension['previous_extension'], root)
        previous_binding = read_evidence(extension['prior_binding'], root)
        require(previous.get('profile') == PROFILE
            and previous_binding.get('time_extension') == extension['previous_extension']
            and previous_binding['program']['sha256'] == extension['prior_program']['sha256'],
            'Extension lost its approved predecessor', 'E_AUTHORITY')
        read_evidence(extension['prior_program'], root)
        previous_binding = dict(previous_binding, program=extension['prior_program'])
        prior_deadline = effective_deadline(root, directory, grant=grant, binding=previous_binding)
        require(extension['previous_deadline_utc'] == prior_deadline
            and deadline > datetime.fromisoformat(prior_deadline), 'Extension shortened or changed prior authority', 'E_AUTHORITY')
    return extension['deadline_utc']
