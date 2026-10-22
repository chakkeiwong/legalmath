"""Authenticate a completed invalid wire review without interpreting its verdicts."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.integration_contract import evidence_file


def invalid_wire_reviews(product, key, result, ids, request, schema):
    """Return one explicit invalid record per assignment, or no eligible input.

    This path never decodes malformed references or infers a valid decision.
    Provider receipt bytes, the charged slot and the dispatch journal bind the
    exact ended request. New reassessments use the unchanged answer and sources.
    """
    directory = product.dispatch.directory/key
    path = directory/'wire-response.json'
    if result.get('status') != 'FAILED' or not path.exists() or (directory/'raw.json').exists():
        return {}
    if result.get('continuation_veto') or result.get('error') != 'ValidationError':
        return {}
    read = lambda name: json.loads((directory/name).read_text())
    require(read('request.json') == request and read('schema.json') == schema
        and read('result.json') == result and result.get('request_hash') == digest(request),
        'Invalid wire review changed its product contract', 'E_INTEGRITY')
    journal = json.loads((product.dispatch.directory/'dispatch.json').read_text())['calls'][key]
    require(journal['status'] == 'FAILED' and journal['result_hash'] == digest(result),
        'Invalid wire review is not a settled dispatch', 'E_INTEGRITY')
    require(ids == request['required_considered'] and len(ids) == len(set(ids)),
        'Invalid wire review changed its assigned population', 'E_INTEGRITY')
    wire, binding = read('wire-response.json'), read('reference-binding.json')
    require(binding['original_request'] == request and binding['original_schema'] == schema
        and binding['binding'] == digest(dict(protocol=binding['protocol'], request=request, schema=schema)),
        'Invalid wire review changed its reference binding', 'E_INTEGRITY')
    provenance = wire['provenance']
    allowance = getattr(product.provider, 'allowance', None)
    require(allowance is not None and getattr(allowance, 'path', None) is not None,
        'Completed wire repair requires its charged provider receipt', 'E_AUTHORITY')
    ledger_path = Path(allowance.path)
    ledger = json.loads(ledger_path.read_text())
    slot, rh = provenance.get('allowance_slot'), provenance.get('request_hash')
    require(type(slot) is int and 1 <= slot <= len(ledger['calls'])
        and ledger['calls'][slot-1]['request_hash'] == rh == digest(binding['request']),
        'Invalid wire review changed its charged request', 'E_INTEGRITY')
    folder = ledger_path.parent/'provider-evidence'/f'{slot}-{rh[:16]}'
    manifest = json.loads((folder/'manifest.json').read_text())
    require(manifest.get('allowance_slot') == slot and manifest.get('request_hash') == rh
        and manifest.get('complete_output_present') is True,
        'Invalid wire review has no complete receipt', 'E_INTEGRITY')
    names = {'request.json', 'schema.json', 'result.json', 'events.jsonl'}
    require(names <= set(manifest['files']), 'Incomplete invalid-review receipt', 'E_INTEGRITY')
    files = {}
    for name in names:
        identity, data = manifest['files'][name], (folder/name).read_bytes()
        require(not identity['redacted'] and len(data) == identity['bytes']
            and hashlib.sha256(data).hexdigest() == identity['original_sha256'] == identity['retained_sha256'],
            'Invalid wire review receipt changed', 'E_INTEGRITY')
        files[name] = data
    require(json.loads(files['request.json']) == binding['request']
        and json.loads(files['schema.json']) == binding['schema']
        and json.loads(files['result.json']) == wire['value']
        and provenance.get('response_hash') == digest(wire['value']),
        'Invalid wire review differs from the sent contract or completed response', 'E_INTEGRITY')
    events = [json.loads(line) for line in files['events.jsonl'].splitlines() if line.strip()]
    require(any(e.get('type') == 'turn.completed' for e in events)
        and not any(e.get('type') == 'turn.failed' for e in events),
        'Invalid wire review did not complete', 'E_INTEGRITY')
    messages = [e.get('item', {}).get('text') for e in events
        if e.get('type') == 'item.completed' and e.get('item', {}).get('type') == 'agent_message']
    decoded = []
    for text in messages:
        try:
            decoded.append(json.loads(text))
        except (TypeError, ValueError):
            continue
    require(wire['value'] in decoded,
        'Invalid wire review differs from the completed message', 'E_INTEGRITY')
    error = next(Draft202012Validator(binding['schema']).iter_errors(wire['value']), None)
    require(error is not None, 'Wire repair requires a reproduced invalid wire schema', 'E_INTEGRITY')
    retained = dict(kind='COMPLETED_INVALID_WIRE_REVIEW', interpreted=False,
        response_hash=digest(wire['value']),
        wire_response=evidence_file(path, product.root),
        provider_receipt=evidence_file(folder/'manifest.json', product.root),
        reference_binding=evidence_file(directory/'reference-binding.json', product.root))
    # Exact full invalid output remains in retained evidence. Inserting it into
    # each new prompt can exceed capacity and would introduce unbound aliases.
    reason = 'Completed wire review failed '+str(error.validator)+' validation at /'+ '/'.join(map(str,error.absolute_path))
    return {identity: dict(reason=reason, original=deepcopy(retained)) for identity in ids}
