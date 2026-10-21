"""Preserve required source gaps without suppressing additional uncertainty.

Reassessment authenticates a complete charged response; it never grants a new
sample or rewrites the failed dispatch. Ordinary product validation still runs.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from legalmath.canonical import canonical, digest
from ..bounded_context import Limits, require, tokenizer
from ..bounded_references import resolve
from ..integration_contract import read_evidence

PROFILE = 'completed-account-gap-reassessment.v1'
REJECTION = 'Account correction changed required document-qualified source gaps'


def preserve(required, actual):
    """Every required object remains exact; distinct additional gaps may remain."""
    require(isinstance(required, list) and isinstance(actual, list), 'Invalid source-gap population')
    require(len({digest(gap) for gap in actual}) == len(actual), 'Duplicate source gap')
    require(all(gap in actual for gap in required), REJECTION)
    return actual


def checked(root, checkpoint, key, entry):
    from .failure_recovery import checked_wire
    from .account_output import output_token_limit
    root = Path(root)
    config = checkpoint['account_recovery']
    require(entry.get('profile') == PROFILE and key in config['failed_calls']
        and entry['originals'] == config['originals'][key]
        and entry['dispatch'] == checkpoint.get('original_dispatches', {}).get(key, checkpoint['dispatch']),
        'Unbound gap-preservation receipt')
    review = read_evidence(entry['amendment'], root)
    require(review.get('profile') == 'account-gap-preservation-review.v1'
        and review.get('verdict') == 'PASS' and review.get('provider_calls_authorized') == 0
        and review.get('approved_receipts', {}).get(key) == entry['provider_manifest'],
        'Gap reassessment lacks its explicit review')
    old, schema, failed = (read_evidence(entry['originals'][name], root)
                          for name in ('request', 'schema', 'result'))
    dispatch = read_evidence(entry['dispatch'], root)['calls'][key]
    require(dispatch['status'] == failed.get('status') == 'FAILED'
        and digest(failed) == dispatch['result_hash'] and failed.get('request_hash') == digest(old)
        and failed.get('error') == 'E_INTEGRITY' and failed.get('reason') == REJECTION
        and old.get('account_correction'), 'Response failed for a different reason')
    folder = Path(entry['originals']['request']['path']).parent
    require(entry['reference_binding']['path'] == str(folder/'reference-binding.json')
        and entry['raw']['path'] == str(folder/'raw.json'), 'Foreign gap-reassessment files')
    prepared = checked_wire(root, entry['reference_binding'], old, schema)
    receipt = read_evidence(entry['provider_manifest'], root)
    ledger = read_evidence(entry['prior_ledger'], root)
    slot = entry['allowance_slot']
    require(type(slot) is int and 1 <= slot <= len(ledger['calls'])
        and receipt.get('allowance_slot') == slot and receipt.get('complete_output_present') is True
        and receipt.get('request_hash') == digest(prepared['request'])
        and ledger['calls'][slot-1]['request_hash'] == receipt['request_hash'],
        'Reassessment lacks its exact historical charge')
    files = {}
    directory = (root/entry['provider_manifest']['path']).parent
    require({'events.jsonl', 'request.json', 'result.json', 'schema.json'} <= set(receipt['files']),
        'Incomplete gap-reassessment receipt')
    for name, identity in receipt['files'].items():
        require(Path(name).name == name and not identity['redacted'], 'Unsafe or redacted receipt')
        data = (directory/name).read_bytes()
        require(len(data) == identity['bytes'] and hashlib.sha256(data).hexdigest()
            == identity['retained_sha256'] == identity['original_sha256'], 'Receipt bytes changed')
        files[name] = data
    require(json.loads(files['request.json']) == prepared['request']
        and json.loads(files['schema.json']) == prepared['schema'], 'Receipt contract changed')
    events = [json.loads(line) for line in files['events.jsonl'].splitlines() if line.strip()]
    require(any(e.get('type') == 'turn.completed' for e in events)
        and not any(e.get('type') == 'turn.failed' for e in events), 'Unsettled provider output')
    wire = json.loads(files['result.json'])
    texts = [e.get('item', {}).get('text') for e in events
        if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'agent_message']
    require(any(json.loads(t) == wire for t in texts if t), 'Response differs from completed turn')
    read_evidence(entry['tokenizer'], root, json_value=False)
    encode = tokenizer(root/entry['tokenizer']['path'])
    limits = Limits()
    require(len(canonical(wire)) <= limits.output_bytes
        and len(encode(canonical(wire).decode())) <= output_token_limit(old, limits),
        'Wire response exceeds unchanged bounds')
    from .account_receipt import historical_request
    prepared['original_request'] = historical_request(prepared)
    value = resolve(wire, prepared, maximum_bytes=limits.decoded_output_bytes)
    raw = read_evidence(entry['raw'], root)
    require(raw['value'] == value and raw['provenance']['allowance_slot'] == slot,
        'Retained raw response differs from authenticated wire output')
    preserve(old['account_correction']['required_source_gaps'], value['source_gaps'])
    measurement = dict(decoded_bytes=len(canonical(value)),
        decoded_tokens=len(encode(canonical(value).decode())), reference_expanded=True)
    require(measurement['decoded_bytes'] <= limits.decoded_output_bytes
        and measurement['decoded_tokens'] <= limits.decoded_output_tokens,
        'Decoded response exceeds unchanged bounds')
    return old, schema, value, measurement


def retained(root, checkpoint, reference, key, request, schema, *, limits=None, encode=None):
    entry = checkpoint['completed_account_receipts'][key]
    old, previous_schema, value, measurement = checked(root, checkpoint, key, entry)
    require(request == old and schema == previous_schema,
        'Gap reassessment changed request, sources, assignment or schema')
    limits = limits or Limits()
    require(measurement['decoded_bytes'] <= limits.decoded_output_bytes
        and measurement['decoded_tokens'] <= limits.decoded_output_tokens, 'Reassessment exceeds limits')
    provenance = dict(manifest=reference, prior_result=entry['originals']['result'],
        provider_manifest=entry['provider_manifest'], allowance_slot=entry['allowance_slot'],
        review=entry['amendment'], evidence_class='REASSESSED_GAP_PRESERVATION; NOT_A_NEW_MODEL_SAMPLE')
    return dict(status='VALIDATED', value=deepcopy(value), request_hash=digest(request),
        provenance=provenance, output_measurement=measurement), provenance
