"""Versioned exact checkpoints, never new model samples or outcome selection."""
import json
import hashlib
from .bounded_context import require
from .integration_contract import read_evidence
from legalmath.canonical import digest


def initial_key(key):
    return key == 'same-evidence-answer' or key.startswith((
        'read-', 'dependency-', 'detail-', 'reduce-', 'candidates-', 'criticism-',
        'answer-', 'audit-'))


def continuation_key(key):
    return initial_key(key) or key.startswith(('warrant-', 'correction-', 'corrected-', 'interaction-'))


def verify_no_output_receipts(root, recovery, request, schema):
    from .bounded_references import prepare
    from legalmath.interpretation.search.providers import transient_service_details
    wire = prepare(request, schema)['request']
    require(recovery.get('receipts'), 'No retained recovery receipt', 'E_AUTHORITY')
    for reference in recovery['receipts']:
        receipt = read_evidence(reference, root)
        require(receipt.get('complete_output_present') is False and receipt.get('request_hash') == digest(wire),
            'Recovery receipt differs from request or has output', 'E_INTEGRITY')
        directory = root/reference['path']
        def retained(name):
            path = directory.parent/name
            data = path.read_bytes()
            require(hashlib.sha256(data).hexdigest() == receipt['files'][name]['retained_sha256'],
                'Recovery receipt bytes changed', 'E_INTEGRITY')
            return data
        events = [json.loads(line) for line in retained('events.jsonl').splitlines() if line.strip()]
        require(not any(e.get('type') == 'turn.completed' for e in events),
            'Completed request is not recoverable', 'E_AUTHORITY')
        if 'termination.json' in receipt['files']:
            ended = json.loads(retained('termination.json'))
            require(ended.get('process_terminated') is True and ended.get('returncode') is not None
                and not ended.get('complete_output_present') and not ended.get('completed_turn_present'),
                'Prior timeout was not terminated', 'E_AUTHORITY')
        else:
            require(transient_service_details(events, output_present=False) is not None,
                'Prior failure lacks classified service evidence', 'E_AUTHORITY')


def retained_response(root, reference, key, request, schema, identity, input_hash, *, limits=None, encode=None):
    manifest = read_evidence(reference, root)
    if manifest.get('profile') == 'bounded-phased-successor.v1':
        from .phased import synthesis_recovery
        require(manifest.get('input_hash') == input_hash,
            'Foreign phased successor input', 'E_INTEGRITY')
        if key.startswith('reduce-'):
            return synthesis_recovery.retained(root, manifest['synthesis'], key, request,
                schema, identity, input_hash, limits=limits)
        return retained_response(root, manifest['account'], key, request, schema,
            identity, input_hash, limits=limits, encode=encode)
    full = manifest.get('profile') == 'bounded-full-checkpoint.v3'
    partial = full or manifest.get('profile') == 'bounded-exact-checkpoint.v2'
    require(manifest.get('profile') in ('bounded-initial-checkpoint.v1', 'bounded-exact-checkpoint.v2', 'bounded-full-checkpoint.v3')
            and manifest.get('input_hash') == input_hash,
            'Retained checkpoint belongs to another input', 'E_INTEGRITY')
    calls = manifest.get('calls', {})
    allowed = continuation_key if full else initial_key
    require(all(allowed(k) for k in calls),
            'Retained checkpoint includes a correction or unsupported phase', 'E_INTEGRITY')
    if not allowed(key):
        return None
    if key in manifest.get('completed_account_receipts', {}):
        from .phased.account_receipt import retained
        return retained(root, manifest, reference, key, request, schema, limits=limits, encode=encode)
    if partial and key not in calls:
        dispatch = read_evidence(manifest.get('original_dispatches', {}).get(key, manifest['dispatch']), root)
        require(dispatch.get('input_hash') == input_hash, 'Checkpoint input changed', 'E_INTEGRITY')
        previous = dispatch.get('calls', {}).get(key)
        if manifest.get('missing_only'):
            require(previous is not None and previous.get('identity') == identity,
                'Missing-only continuation cannot introduce or change a request', 'E_AUTHORITY')
        if previous:
            require(previous.get('status') != 'RESERVED', 'Uncertain old request cannot be redispatched', 'E_AUTHORITY')
            if previous.get('identity') == identity:
                recovery = manifest.get('recoverable_failures', {}).get(key)
                require(previous.get('status') == 'FAILED' and recovery,
                    'Identical omitted request lacks reviewed recovery evidence', 'E_AUTHORITY')
                failed = read_evidence(recovery['result'], root)
                require(failed.get('status') == 'FAILED' and digest(failed) == previous.get('result_hash')
                    and recovery.get('receipts'), 'Failed checkpoint identity changed', 'E_INTEGRITY')
                for reference in recovery['receipts']:
                    receipt = read_evidence(reference, root)
                    require(receipt.get('complete_output_present') is False,
                        'Prior complete response cannot receive transport recovery', 'E_AUTHORITY')
                if full:
                    verify_no_output_receipts(root, recovery, request, schema)
        return None
    require(key in calls, 'Retained initial request is missing; new initial sampling is not authorized',
            'E_INTEGRITY')
    row = calls[key]
    dispatch = read_evidence(manifest.get('original_dispatches', {}).get(key, manifest['dispatch']), root)
    require(dispatch.get('input_hash') == input_hash and key in dispatch.get('calls', {}),
            'Retained checkpoint has no original reservation', 'E_INTEGRITY')
    prior = dispatch['calls'][key]
    held_failure = full and key in manifest.get('held_failures', [])
    require(prior.get('status') == ('FAILED' if held_failure else 'VALIDATED'),
            'Retained initial response is uncertain or failed', 'E_AUTHORITY')
    if partial and prior.get('identity') != identity:
        require(not manifest.get('missing_only'),
            'Missing-only continuation cannot resample a changed request', 'E_AUTHORITY')
        return None
    require(prior.get('identity') == identity,
            'Retained initial request or provider identity changed', 'E_INTEGRITY')
    require(read_evidence(row['request'], root) == request
            and read_evidence(row['schema'], root) == schema,
            'Retained initial request or schema changed', 'E_INTEGRITY')
    result = read_evidence(row['result'], root)
    require(result.get('status') == ('FAILED' if held_failure else 'VALIDATED') and digest(result) == prior.get('result_hash'),
            'Retained initial response changed', 'E_INTEGRITY')
    if held_failure:
        verify_no_output_receipts(root, manifest['recoverable_failures'][key], request, schema)
    return result, {'manifest': reference, 'result': row['result'],
                    'evidence_class': ('RETAINED_EXACT_CONTINUATION; NOT_A_NEW_MODEL_SAMPLE' if full
                        else 'RETAINED_INITIAL_RESPONSE; NOT_A_NEW_MODEL_SAMPLE')}
