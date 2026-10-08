"""Verify retained completion/stop and prove the next execute adds no calls."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, '/home/chakwong/python/legalmath')
from scripts.legal_integration_coverage import (
    OUT, ROOT, read, immutable, ref, collected, verify, raw_digest)

verified = verify()
assert verified['execution_complete'] or any(not r['complete'] for r in collected())
before = (OUT / 'allowance.json').read_bytes()
before_repairs = (OUT / 'repairs.json').read_bytes()
target = OUT / 'restart-check'
target.mkdir(exist_ok=True)
assert not (target / 'result.json').exists()
argv = ['.venv/bin/python', 'scripts/run_legal_integration_coverage.py', 'execute']
began = time.monotonic()
reply = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=120)
(target / 'stdout.json').write_text(reply.stdout)
(target / 'stderr.txt').write_text(reply.stderr)
assert reply.returncode == 0, reply.stderr
value = json.loads(reply.stdout)
assert (OUT / 'allowance.json').read_bytes() == before
assert (OUT / 'repairs.json').read_bytes() == before_repairs
if verified['execution_complete']:
    assert value['execution_complete']
else:
    assert value['status'] == 'REPAIR_REVIEW_REQUIRED'
immutable(target / 'result.json', {'status': 'PASS', 'command': argv,
    'wall_seconds': time.monotonic() - began, 'returncode': reply.returncode,
    'before_calls': len(json.loads(before)['calls']), 'new_calls': 0,
    'ledger_sha256': raw_digest(before), 'repairs_sha256': raw_digest(before_repairs),
    'execution_complete': verified['execution_complete'], 'response': value,
    'stdout': ref(target / 'stdout.json'), 'stderr': ref(target / 'stderr.txt')})
print(json.dumps({'status': 'PASS', 'new_calls': 0,
                  'execution_complete': verified['execution_complete']}))
