"""Read-only transport diagnosis; never adopt or redispatch the saved response."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'src'))
from jsonschema import validate
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_references import resolve
from legalmath.interpretation.assurance.arguments import evaluate_criticism

WORK = ROOT / 'artifacts/legal-mission-control/2026-10-20/candidate-capacity-retry'
TRANSPORT = ROOT / 'artifacts/legal-mission-control/2026-10-13/master/provider-evidence/3449-38a69a1728a57217'
CALL = WORK / 'live/p14/product/calls/criticism-p14'

def read(path):
    return json.loads(path.read_text())

def reference(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path.read_bytes()).hexdigest()}

def main():
    manifest = read(TRANSPORT / 'manifest.json')
    for name, row in manifest['files'].items():
        path = TRANSPORT / name
        assert path.stat().st_size == row['bytes'], name
        assert reference(path)['sha256'] == row['retained_sha256'], name
    prepared = read(CALL / 'reference-binding.json')
    assert prepared['request'] == read(TRANSPORT / 'request.json')
    assert prepared['schema'] == read(TRANSPORT / 'schema.json')
    assert manifest['request_hash'] == reference(TRANSPORT / 'request.json')['sha256']
    original = read(CALL / 'request.json')
    assert original == prepared['original_request']
    assert prepared['original_schema'] == read(CALL / 'schema.json')

    value = read(TRANSPORT / 'result.json')
    encoded = canonical(value)
    encode = tokenizer(ROOT / '.localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken')
    limits = Limits()
    events = [json.loads(line) for line in (TRANSPORT / 'events.jsonl').read_text().splitlines() if line.strip()]
    result = {
        'observed_at_utc': datetime.now(timezone.utc).isoformat(),
        'mode': 'DEBUGGING_ONLY_NO_PROVIDER_CALLS_NO_ADOPTION',
        'device': 'CPU_ONLY_GPU_INTENTIONALLY_HIDDEN',
        'provider_calls': 0,
        'production_result_changed': False,
        'legal_acceptance': False,
        'transport_manifest': reference(TRANSPORT / 'manifest.json'),
        'reference_binding': reference(CALL / 'reference-binding.json'),
        'original_failure': reference(CALL / 'result.json'),
        'raw_output_bytes': (TRANSPORT / 'result.json').stat().st_size,
        'canonical_output_bytes': len(encoded),
        'canonical_output_tokens': len(encode(encoded.decode())),
        'wire_byte_limit': limits.output_bytes,
        'wire_token_limit': limits.output_tokens,
        'completed_turn_present': any(e.get('type') == 'turn.completed' for e in events),
        'forbidden_tool_event_present': any(e.get('item', {}).get('type') in
            {'command_execution', 'mcp_tool_call', 'web_search', 'file_change'} for e in events),
    }
    result['canonical_wire_within_limits'] = (
        result['canonical_output_bytes'] <= limits.output_bytes
        and result['canonical_output_tokens'] <= limits.output_tokens)
    try:
        validate(value, prepared['schema'])
        result['wire_schema'] = 'PASS'
        expanded = resolve(value, prepared, maximum_bytes=limits.decoded_output_bytes)
        validate(expanded, prepared['original_schema'])
        result['normal_reference_expansion'] = 'PASS'
        result['expanded_bytes'] = len(canonical(expanded))
        result['expanded_tokens'] = len(encode(canonical(expanded).decode()))
        evaluation = evaluate_criticism(expanded, original['source_packet'], list(original['candidates']))
        result['normal_criticism_validation'] = 'PASS'
        result['criticism_evaluation'] = {
            'status': evaluation['status'],
            'questions': len(evaluation['questions']),
            'blocked_arguments': evaluation['blocked_arguments'],
            'conditional_arguments': evaluation['conditional_arguments'],
            'candidate_pruning_authorized': evaluation['candidate_pruning_authorized'],
            'legal_premises_verified': evaluation['legal_premises_verified'],
        }
    except Exception as exc:
        result['validation_failure'] = {'code': getattr(exc, 'code', type(exc).__name__),
            'details': getattr(exc, 'details', None) or str(exc)}
    with (WORK / 'p14-output-diagnostic.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
