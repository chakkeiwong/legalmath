"""Authenticated reuse across the explicit capacity-policy transition.

Only identical substantive requests/schemas may reuse completed values. A
retained output rejected solely by size may be revalidated against the reviewed
new budget. The old failure and every transport file stay unchanged.
"""
import json
from copy import deepcopy
from jsonschema import validate
from legalmath.canonical import canonical, digest
from ..bounded_context import require
from ..integration_contract import read_evidence
from . import capacity_policy as policy

PROFILE = 'common-capacity-checkpoint.v1'

def same_schema(previous, current, request):
    """Allow only answer-path enum order after canonical answer round-trip."""
    if previous == current:
        return True
    if request.get('task') != 'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT':
        return False
    path=('properties','need_dispositions','items','properties','answer_evidence','properties','path','enum')
    left,right=deepcopy(previous),deepcopy(current)
    try:
        for key in path[:-1]:
            left=left[key];right=right[key]
        a,b=left[path[-1]],right[path[-1]]
    except (KeyError,TypeError):
        return False
    if not (isinstance(a,list) and isinstance(b,list) and all(isinstance(x,str) for x in a+b)
        and len(a)==len(set(a)) and len(b)==len(set(b)) and set(a)==set(b)):
        return False
    normalized=deepcopy(previous);field=normalized
    for key in path[:-1]:field=field[key]
    field[path[-1]]=b
    return normalized==current


def retained(product, call):
    pointer = product.capacity_checkpoint
    if pointer is None:
        return None
    checkpoint = read_evidence(pointer, product.root)
    require(checkpoint['profile'] == PROFILE and checkpoint['input_hash'] == product.route.input_hash,
        'Foreign capacity checkpoint', 'E_INTEGRITY')
    wanted = policy.annotate(call['request'])
    keys = ([call['key']] if call['key'] in checkpoint['calls'] else []) + [
        k for k in checkpoint['calls'] if k != call['key']]
    row = None
    for key in keys:
        candidate = checkpoint['calls'][key]
        request = read_evidence(candidate['request'], product.root)
        from .retry_checkpoint import equivalent
        if not equivalent(request, wanted, checkpoint, candidate, product.root):
            # Answer reuse is mandatory. Changed review populations may create
            # new decisions, but cannot silently buy a new successful answer.
            require(key != call['key'] or wanted['task'] != 'ANSWER_ORIGINAL_QUESTION',
                'Capacity reuse changed substantive answer request', 'E_INTEGRITY')
            continue
        schema = read_evidence(candidate['schema'], product.root)
        require(same_schema(schema,call['schema'],wanted),
            'Capacity reuse changed substantive schema', 'E_INTEGRITY')
        row, original_key = candidate, key
        break
    if row is None:
        return None
    prior = read_evidence(row['result'], product.root)
    require(not prior.get('continuation_veto'), 'Retained capacity continuation veto: '+str(prior.get('reason')), 'E_AUTHORITY')
    if row.get('dispatch'):
        journal = read_evidence(row['dispatch'], product.root)
        recorded = journal['calls'][row.get('dispatch_key', original_key)]
        require(journal['input_hash'] == product.route.input_hash and recorded['status'] != 'RESERVED'
            and recorded['result_hash'] == digest(prior), 'Unsettled or changed predecessor call', 'E_INTEGRITY')
    if row['mode'] == 'REVIEWED_FAILURE_RETRY':
        from .retry_checkpoint import retryable
        retryable(checkpoint, row, request, prior, product.root)
        return None
    if row['mode'] == 'RETAINED_FAILURE':
        require(prior['status'] == 'FAILED', 'Cannot import a success as a failure', 'E_INTEGRITY')
        return deepcopy(prior)
    if row['mode'] == 'VALIDATED':
        require(prior['status'] == 'VALIDATED', 'Cannot import incomplete capacity checkpoint', 'E_INTEGRITY')
        value = deepcopy(prior['value'])
    else:
        require(row['mode'] == 'OUTPUT_BUDGET_REVALIDATION' and prior['status'] == 'FAILED'
            and prior['error'] == 'E_RESOURCE_LIMIT' and any(message in prior['reason'] for message in
                ('output byte cap', 'output exceeds', 'Output exceeds', 'Wire output exceeds')),
            'Only an identified output-budget failure may be revalidated', 'E_AUTHORITY')
        prepared = read_evidence(row['reference_binding'], product.root)
        require(prepared['original_request'] == request and prepared['original_schema'] == schema,
            'Retained decoding contract changed', 'E_INTEGRITY')
        manifest = read_evidence(row['transport_manifest'], product.root)
        parent = (product.root / row['transport_manifest']['path']).parent
        for name, item in manifest['files'].items():
            data = (parent / name).read_bytes()
            from hashlib import sha256
            require(sha256(data).hexdigest() == item['retained_sha256'] and len(data) == item['bytes'],
                'Retained transport changed', 'E_INTEGRITY')
        wire_request = json.loads((parent/'request.json').read_text())
        wire_schema = json.loads((parent/'schema.json').read_text())
        require(wire_request == prepared['request'] and wire_schema == prepared['schema']
            and digest(wire_request) == manifest['request_hash'], 'Transport request differs', 'E_INTEGRITY')
        events = [json.loads(line) for line in (parent/'events.jsonl').read_text().splitlines() if line.strip()]
        require(any(e.get('type') == 'turn.completed' for e in events) and not any(
            e.get('item', {}).get('type') in {'command_execution','mcp_tool_call','web_search','file_change'}
            for e in events), 'Retained transport is incomplete or used tools', 'E_AUTHORITY')
        raw = (parent/'result.json').read_bytes()
        require(len(raw) <= policy.output_bytes(call['request'], product.route.limits),
            'Retained raw response still exceeds capacity', 'E_RESOURCE_LIMIT')
        wire_value = json.loads(raw)
        policy.measure_output(wire_value, policy.annotate(call['request']), product.route.limits, product.route.encode)
        validate(wire_value, prepared['schema'])
        from ..bounded_references import resolve
        value = resolve(wire_value, prepared, maximum_bytes=product.route.limits.decoded_output_bytes)
    policy.measure_output(value, policy.annotate(call['request']), product.route.limits, product.route.encode, expanded=True)
    validate(value, call['schema'])
    call['validate'](value)
    return dict(status='VALIDATED', value=value, request_hash=digest(policy.annotate(call['request'])),
        provenance=dict(capacity_checkpoint=pointer, original_key=original_key, original_result=row['result'], mode=row['mode'],
            new_provider_calls=0, legal_acceptance=False))


def native(product, binding):
    """Keep exact native outputs (including evidence paths) in resumed arms."""
    if product.capacity_checkpoint is None:
        return None
    checkpoint = read_evidence(product.capacity_checkpoint, product.root)
    require(checkpoint['profile'] == PROFILE and checkpoint['input_hash'] == product.route.input_hash,
        'Foreign native capacity checkpoint', 'E_INTEGRITY')
    prior_binding = {k:v for k,v in binding.items() if k != 'capacity'}
    rows = [row for row in checkpoint.get('native', []) if row['kind'] == binding['kind']]
    require(len(rows) <= 1, 'Ambiguous native capacity checkpoint', 'E_INTEGRITY')
    if not rows:
        return None
    row = rows[0]
    previous = read_evidence(row['binding'], product.root)
    require(previous['binding'] == prior_binding and previous['status'] == 'COMPLETED',
        'Changed or unsettled retained native input', 'E_INTEGRITY')
    value = read_evidence(row['result'], product.root)
    require(digest(value) == previous['result_hash'], 'Changed retained native result', 'E_INTEGRITY')
    def verify_refs(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256'}:
                read_evidence(value, product.root, json_value=False)
            else:
                for child in value.values(): verify_refs(child)
        elif isinstance(value, list):
            for child in value: verify_refs(child)
    verify_refs(value)
    return deepcopy(value)
