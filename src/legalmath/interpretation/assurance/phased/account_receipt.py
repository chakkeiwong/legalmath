"""Explicit reassessment of a complete, charged account rejected only for size.

The rejected dispatch stays rejected. This path grants no new model sample.
Normal product validation still checks the decoded account and its citations.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from legalmath.canonical import canonical, digest
from ..bounded_context import Limits, require, tokenizer
from ..integration_contract import read_evidence
from ..bounded_references import prepare, resolve
from .account_output import PROFILE as OUTPUT_PROFILE, output_token_limit

PROFILE = 'completed-account-output-reassessment.v1'
REJECTION = 'Actual provider output exceeds local token allowance'


def historical_request(prepared):
    """Restore table-column order lost by canonical JSON, then prove equality."""
    request = deepcopy(prepared['original_request'])
    columns = prepared['request'].get('account_record_table', {}).get('columns', [])
    require(len(columns) == len(set(columns)), 'Duplicate historical account columns')
    if columns:
        for i, row in enumerate(request['records']):
            require(set(columns) <= set(row), 'Historical account columns changed')
            request['records'][i] = {**{k: v for k, v in row.items() if k not in columns},
                                      **{k: row[k] for k in columns}}
    require(prepare(request, prepared['original_schema']) == prepared,
            'Historical wire contract changed')
    return request


def checked(root, checkpoint, key, entry):
    """Authenticate a reviewed receipt against the frozen failed-call census."""
    from . import account_gap_preservation
    if entry.get('profile') == account_gap_preservation.PROFILE:
        return account_gap_preservation.checked(root, checkpoint, key, entry)
    config = checkpoint['account_recovery']
    require(entry.get('profile') == PROFILE and key in config['failed_calls']
            and entry['originals'] == config['originals'][key]
            and entry['dispatch'] == checkpoint.get('original_dispatches', {}).get(key, checkpoint['dispatch']),
            'Unbound complete account receipt')
    amendment = read_evidence(entry['amendment'], root)
    require(amendment.get('profile') == 'completed-account-receipt-review.v1'
            and amendment.get('verdict') == 'PASS'
            and amendment.get('provider_calls_authorized') == 0
            and amendment.get('output_profile') == OUTPUT_PROFILE
            and amendment.get('approved_receipts', {}).get(key) == entry['provider_manifest'],
            'Complete account receipt lacks explicit policy review')
    old, schema, failed = (read_evidence(entry['originals'][name], root)
                           for name in ('request', 'schema', 'result'))
    dispatch = read_evidence(entry['dispatch'], root)
    prior = dispatch['calls'][key]
    require(prior['status'] == failed.get('status') == 'FAILED'
            and digest(failed) == prior['result_hash']
            and failed.get('request_hash') == digest(old)
            and failed.get('error') == 'E_RESOURCE_LIMIT' and failed.get('reason') == REJECTION,
            'Receipt was not rejected solely by the original output allowance')
    binding_path = Path(entry['originals']['request']['path']).parent / 'reference-binding.json'
    require(entry['reference_binding']['path'] == str(binding_path), 'Foreign account wire binding')
    prepared = read_evidence(entry['reference_binding'], root)
    original = historical_request(prepared)
    require(original == old and prepared['original_schema'] == schema,
            'Complete receipt changed its original request or schema')
    receipt = read_evidence(entry['provider_manifest'], root)
    slot = entry['allowance_slot']
    ledger = read_evidence(entry['prior_ledger'], root)
    require(type(slot) is int and 1 <= slot <= len(ledger['calls'])
            and receipt.get('allowance_slot') == slot
            and receipt.get('complete_output_present') is True
            and receipt.get('request_hash') == digest(prepared['request'])
            and ledger['calls'][slot - 1]['request_hash'] == receipt['request_hash'],
            'Receipt lacks its exact historical allowance charge')
    directory = (Path(root) / entry['provider_manifest']['path']).parent
    files = {}
    require({'events.jsonl', 'request.json', 'result.json', 'schema.json'} <= set(receipt['files']),
            'Incomplete account provider receipt')
    for name, identity in receipt['files'].items():
        require(Path(name).name == name and not identity['redacted'], 'Foreign or redacted receipt file')
        data = (directory / name).read_bytes()
        require(len(data) == identity['bytes'] and hashlib.sha256(data).hexdigest()
                == identity['retained_sha256'] == identity['original_sha256'],
                'Complete account receipt bytes changed')
        files[name] = data
    require(json.loads(files['request.json']) == prepared['request']
            and json.loads(files['schema.json']) == prepared['schema'], 'Foreign provider contract')
    events = [json.loads(line) for line in files['events.jsonl'].splitlines() if line.strip()]
    require(any(e.get('type') == 'turn.completed' for e in events)
            and not any(e.get('type') == 'turn.failed' for e in events), 'Account turn did not complete')
    wire = json.loads(files['result.json'])
    texts = [e.get('item', {}).get('text') for e in events
             if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'agent_message']
    require(any(json.loads(t) == wire for t in texts if t), 'Receipt result differs from completed response')
    encode = tokenizer(Path(root) / entry['tokenizer']['path'])
    read_evidence(entry['tokenizer'], root, json_value=False)
    tokens, size = len(encode(canonical(wire).decode())), len(canonical(wire))
    limits = Limits()
    require(limits.output_tokens < tokens <= 4096 and size <= limits.output_bytes,
            'Complete account is outside the reviewed output reassessment')
    prepared['original_request'] = original
    value = resolve(wire, prepared, maximum_bytes=limits.decoded_output_bytes)
    require(len(canonical(value)) <= limits.decoded_output_bytes
            and len(encode(canonical(value).decode())) <= limits.decoded_output_tokens,
            'Complete account exceeds unchanged decoded bounds')
    return original, schema, value, {'wire_tokens': tokens, 'wire_bytes': size,
        'decoded_bytes': len(canonical(value)), 'decoded_tokens': len(encode(canonical(value).decode())),
        'reference_expanded': True}


def retained(root, checkpoint, reference, key, request, schema, *, limits=None, encode=None):
    entry = checkpoint.get('completed_account_receipts', {}).get(key)
    if entry is None:
        return None
    from . import account_gap_preservation
    if entry.get('profile') == account_gap_preservation.PROFILE:
        return account_gap_preservation.retained(root, checkpoint, reference, key, request, schema,
            limits=limits, encode=encode)
    old, old_schema, value, measurement = checked(root, checkpoint, key, entry)
    limits = limits or Limits()
    require(request.get('account_output_profile') == OUTPUT_PROFILE
            and output_token_limit(request, limits) == 4096, 'Receipt requires its explicit output profile')
    current, previous = deepcopy(request), deepcopy(old)
    for name in ('account_output_profile', 'account_capacity_profile'):
        current.pop(name, None)
        previous.pop(name, None)
    require(current == previous and schema == old_schema,
            'Receipt reuse changed source, assignment, instructions or response schema')
    if encode is not None:
        require(len(encode(canonical(value).decode())) <= limits.decoded_output_tokens,
                'Receipt exceeds current decoded token bound')
    require(measurement['wire_bytes'] <= limits.output_bytes
            and measurement['decoded_bytes'] <= limits.decoded_output_bytes,
            'Receipt exceeds current byte bounds')
    provenance = {'manifest': reference, 'prior_result': entry['originals']['result'],
        'provider_manifest': entry['provider_manifest'], 'allowance_slot': entry['allowance_slot'],
        'review': entry['amendment'], 'evidence_class': 'REASSESSED_COMPLETE_ACCOUNT; NOT_A_NEW_MODEL_SAMPLE'}
    return {'status': 'VALIDATED', 'value': value, 'request_hash': digest(request),
            'provenance': provenance, 'output_measurement': measurement}, provenance
