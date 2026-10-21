"""Reassess an already-paid exact diagnostic response; never retry a refusal."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import validate
from legalmath.canonical import canonical, digest
from ..bounded_context import Limits, require, tokenizer
from ..bounded_references import prepare, resolve
from ..integration_contract import read_evidence
from .account_output import output_token_limit

PROFILE = 'exact-diagnostic-synthesis-reassessment.v1'


def checked(root, value, key):
    entry = value['diagnostic_reassessments'][key]
    require(entry.get('profile') == PROFILE and entry.get('provider_calls_authorized') == 0,
        'Unreviewed diagnostic reassessment', 'E_AUTHORITY')
    row = value['rows'][key]
    require(entry['original_result'] == row['result'] and entry['original_binding'] == row['reference_binding'],
        'Reassessment changed original failure', 'E_INTEGRITY')
    review = read_evidence(entry['review'], root)
    require(review.get('profile') == 'exact-diagnostic-synthesis-review.v1'
        and review.get('provider_calls_authorized') == 0 and review.get('verdict') == 'PASS'
        and review['approved'][key] == entry['diagnostic'], 'Missing diagnostic review', 'E_AUTHORITY')
    failed = read_evidence(row['result'], root)
    require(failed.get('status') == 'FAILED', 'Reassessment cannot replace a success', 'E_AUTHORITY')
    prepared = read_evidence(row['reference_binding'], root)
    from .synthesis_recovery import historical_request
    prepared['original_request'] = historical_request(prepared, reviewed=True)
    request = prepared['original_request']
    require(request == read_evidence(row['request'], root)
        and prepared['original_schema'] == read_evidence(row['schema'], root), 'Changed original request')
    manifest = read_evidence(entry['diagnostic'], root)
    authority = read_evidence(manifest['authority'], root)
    require(authority.get('profile') == 'integration-diagnostic-stage.v1',
        'Foreign diagnostic authority', 'E_AUTHORITY')
    files = {name:read_evidence(ref, root, json_value=False) for name,ref in manifest['files'].items()}
    require({'request.json','schema.json','result.json','events.jsonl','outcome.json','reservation.json'} <= set(files),
        'Incomplete diagnostic response', 'E_INTEGRITY')
    wire = json.loads(files['result.json'])
    require(json.loads(files['request.json']) == prepared['request']
        and json.loads(files['schema.json']) == prepared['schema'], 'Diagnostic changed wire contract')
    events = [json.loads(line) for line in files['events.jsonl'].splitlines() if line.strip()]
    require(any(e.get('type') == 'turn.completed' for e in events)
        and not any(e.get('type') == 'turn.failed' for e in events), 'Diagnostic turn did not complete')
    messages = [e['item'].get('text') for e in events
        if e.get('type') == 'item.completed' and e.get('item',{}).get('type') == 'agent_message']
    require(any(json.loads(t) == wire for t in messages if t), 'Diagnostic output differs from response')
    ledger = read_evidence(entry['ledger'], root)
    slot = manifest['global_slot']
    require(type(slot) is int and 1 <= slot <= len(ledger['calls'])
        and ledger['calls'][slot-1]['request_hash'] == digest(prepared['request'])
        and ledger['calls'][slot-1]['stage_hash'] == manifest['authority']['sha256']
        and ledger['grant_hash'] == authority['grant_hash']
        and digest(read_evidence(authority['grant'], root)) == authority['grant_hash']
        and entry['slot'] == slot, 'Diagnostic lacks original charge')
    require(any(arm.get('form') == 'original' and arm.get('request_hash') == digest(prepared['request'])
        and arm.get('schema_hash') == digest(prepared['schema']) for arm in authority.get('arms', [])),
        'Diagnostic was not the authorized original form', 'E_AUTHORITY')
    reservation, outcome = (json.loads(files[n]) for n in ('reservation.json','outcome.json'))
    require(reservation['global_slot'] == outcome['global_slot'] == slot
        and reservation['authority'] == manifest['authority'] and outcome['form'] == 'original'
        and outcome['classification'] == 'VALID_STRUCTURED_RESPONSE' and outcome['returncode'] == 0
        and outcome['completed_turn'] is True and outcome['output_present'] is True,
        'Diagnostic was not a complete successful original response', 'E_INTEGRITY')
    read_evidence(entry['tokenizer'], root, json_value=False)
    encode = tokenizer(Path(root)/entry['tokenizer']['path']); limits=Limits()
    validate(wire, prepared['schema'])
    require(len(canonical(wire)) <= limits.output_bytes
        and len(encode(canonical(wire).decode())) <= output_token_limit(request,limits), 'Diagnostic wire output too large')
    decoded=resolve(wire,prepare(request,prepared['original_schema']),maximum_bytes=limits.decoded_output_bytes)
    validate(decoded,prepared['original_schema'])
    require(len(encode(canonical(decoded).decode())) <= limits.decoded_output_tokens, 'Diagnostic decoded output too large')
    require(len(decoded['considered']) == len(set(decoded['considered']))
        and set(decoded['considered']) == set(request['required_considered'])
        and (decoded['support'] or decoded['unresolved']), 'Diagnostic omitted an input or has no supported disposition')
    from .downstream_instructions import validate_correction
    validate_correction(request, decoded)
    return {'status':'VALIDATED','value':decoded,'request_hash':digest(request),
        'provenance':{'allowance_slot':slot,'request_hash':digest(prepared['request']),
            'diagnostic_manifest':entry['diagnostic'],'original_failure':row['result'],
            'reassessment_review':entry['review'],'evidence_class':'EXACT_PAID_DIAGNOSTIC_REASSESSMENT'},
        'output_measurement':{'decoded_bytes':len(canonical(decoded)),
            'decoded_tokens':len(encode(canonical(decoded).decode())),'reference_expanded':True}}
