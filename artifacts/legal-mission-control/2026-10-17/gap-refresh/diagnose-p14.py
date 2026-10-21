"""Read-only production comparison; no provider construction or dispatch."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.interpretation.search.schema import validate_output_schema

WORK = Path(__file__).resolve().parent
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
started = time.monotonic()


def pointer(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path.read_bytes()).hexdigest()}


def write(name, value):
    (WORK / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def diff(a, b, path=''):
    if type(a) is not type(b):
        return [{'path': path or '/', 'failed': a, 'neighbor': b}]
    if isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            child = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in a or key not in b:
                result.append({'path': child, 'failed_present': key in a,
                               'neighbor_present': key in b,
                               'failed': a.get(key), 'neighbor': b.get(key)})
            else:
                result.extend(diff(a[key], b[key], child))
        return result
    if isinstance(a, list):
        result = []
        for index in range(max(len(a), len(b))):
            child = path + '/' + str(index)
            if index >= len(a) or index >= len(b):
                result.append({'path': child, 'failed_present': index < len(a),
                               'neighbor_present': index < len(b),
                               'failed': a[index] if index < len(a) else None,
                               'neighbor': b[index] if index < len(b) else None})
            else:
                result.extend(diff(a[index], b[index], child))
        return result
    return [] if a == b else [{'path': path or '/', 'failed': a, 'neighbor': b}]


ledger_path = BASE / 'live-calls.json'
ledger_bytes = ledger_path.read_bytes()
ledger = json.loads(ledger_bytes)
write('p14-diagnostic-ledger.json', ledger)
rows, evidence, requests, schemas = [], [], {}, {}
for slot in range(2335, 2346):
    charge = ledger['calls'][slot - 1]
    folder = BASE / 'provider-evidence' / f"{slot:04}-{charge['request_hash'][:16]}"
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    assert manifest['allowance_slot'] == slot
    assert manifest['request_hash'] == charge['request_hash']
    evidence.append(pointer(folder / 'manifest.json'))
    for name, recorded in manifest['files'].items():
        path = folder / name
        actual = pointer(path)
        assert actual['sha256'] == recorded['retained_sha256'], (slot, name)
        assert len(path.read_bytes()) == recorded['bytes'], (slot, name)
        assert not recorded['redacted'], (slot, name, 'Cannot compare redacted original bytes')
        assert actual['sha256'] == recorded['original_sha256'], (slot, name)
        evidence.append(actual)
    assert pointer(folder / 'request.json')['sha256'] == charge['request_hash']
    request = requests[slot] = json.loads((folder / 'request.json').read_bytes())
    schema = schemas[slot] = json.loads((folder / 'schema.json').read_bytes())
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines() if line.strip()]
    try:
        schema_check = validate_output_schema(schema)
    except Exception as exc:
        schema_check = {'status': 'FAILED', 'error': type(exc).__name__,
                        'details': getattr(exc, 'details', str(exc))}
    rows.append({'slot': slot, 'receipt': pointer(folder / 'manifest.json'),
        'request': pointer(folder / 'request.json'), 'schema': pointer(folder / 'schema.json'),
        'request_bytes': (folder / 'request.json').stat().st_size,
        'task': request.get('task'), 'profiles': {k: v for k, v in request.items() if 'profile' in k},
        'root_fields': list(request), 'payload_items': len(request.get('payload', [])),
        'complete_output_present': manifest['complete_output_present'],
        'terminal_events': [e for e in events if e.get('type') in ('error', 'turn.failed', 'turn.completed')],
        'necessary_schema_check': schema_check})

comparisons = []
for slot in range(2335, 2346):
    if slot == 2341:
        continue
    schema_diff = diff(schemas[2341], schemas[slot])
    request_diff = diff(requests[2341], requests[slot])
    comparisons.append({'neighbor_slot': slot, 'schema_equal': not schema_diff,
        'schema_properties_equal': schemas[2341]['properties'] == schemas[slot]['properties'],
        'schema_differences': schema_diff, 'request_equal': not request_diff,
        'request_differences': request_diff})
write('p14-contract-differences.json', comparisons)
result = {'profile': 'p14-retained-request-diagnosis.v1',
    'failed_slot': 2341, 'slots': rows, 'evidence': evidence,
    'comparisons': pointer(WORK / 'p14-contract-differences.json'),
    'ledger_snapshot': pointer(WORK / 'p14-diagnostic-ledger.json'),
    'live_ledger_unchanged_during_diagnostic': ledger_path.read_bytes() == ledger_bytes,
    'all_receipts_authenticated': True,
    'local_necessary_schema_failure_reproduced': any(r['necessary_schema_check']['status'] == 'FAILED' for r in rows),
    'offending_parameter': None, 'raw_http_body_retained': False,
    'provider_calls': 0, 'p14_reopened': False, 'legal_acceptance': False,
    'decision': 'No parameter-specific cause established by retained evidence; do not retry invalid request.',
    'next_evidence': 'Gateway/provider trace naming the rejected parameter and actual wire body, or a locally reproducible contract violation.',
    'manifest': {'command': '.venv-context/bin/python artifacts/legal-mission-control/2026-10-17/gap-refresh/diagnose-p14.py',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'environment': '.venv-context; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        'plan': pointer(WORK / 'p14-diagnostic-plan.md'), 'implementation': pointer(Path(__file__).resolve()),
        'schema_validator': pointer(ROOT / 'src/legalmath/interpretation/search/schema.py'),
        'data_version': 'Authenticated charged slots 2335–2345', 'seeds': 'N/A: deterministic receipt comparison',
        'wall_seconds': time.monotonic() - started, 'finished_at_utc': datetime.now(timezone.utc).isoformat()}}
write('p14-diagnostic-result.json', result)
print(json.dumps({'receipts_authenticated': len(rows),
    'accepted_neighbors': sum(r['complete_output_present'] for r in rows if r['slot'] != 2341),
    'necessary_schema_failure': result['local_necessary_schema_failure_reproduced'],
    'schema_equal_neighbors': [r['neighbor_slot'] for r in comparisons if r['schema_equal']],
    'property_equal_neighbors': [r['neighbor_slot'] for r in comparisons if r['schema_properties_equal']],
    'offending_parameter': None, 'provider_calls': 0,
    'artifact': 'p14-diagnostic-result.json'}, indent=2))
