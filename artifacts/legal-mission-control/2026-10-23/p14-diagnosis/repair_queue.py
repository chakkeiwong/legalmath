"""Identify exact retained failures for a reviewed continuation; never reset them."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json
import sys

ROOT = Path('/home/chakwong/python/legalmath')
sys.path.insert(0, str(ROOT/'src'))
from legalmath.canonical import digest
OUT = Path(__file__).resolve().parent
census = json.loads((OUT/'census.json').read_text())
ledger = json.loads((ROOT/'artifacts/legal-mission-control/2026-10-13/master/live-calls.json').read_text())
slots = {}
for i, row in enumerate(ledger['calls'], 1):
    slots.setdefault(row['request_hash'], []).append(i)
def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha256(path.read_bytes()).hexdigest())
rows = []
for row in census['calls']:
    if row['status'] != 'FAILED' or row['family'] == 'audit-group-':
        continue
    folder = (ROOT/row['result']['path']).parent
    assert ref(folder/'result.json') == row['result']
    request = json.loads((folder/'request.json').read_text())
    binding = json.loads((folder/'reference-binding.json').read_text())
    counted = slots.get(digest(binding['request']), [])
    circuit = row['reason'].startswith('Shared service circuit open')
    if circuit:
        assert not counted and not (folder/'wire-response.json').exists() and not (folder/'raw.json').exists()
    rows.append(dict(key=row['key'], family=row['family'], assigned_ids=request['required_considered'],
        cause=row['reason'], error=row['error'], request=ref(folder/'request.json'),
        schema=ref(folder/'schema.json'), old_result=row['result'], binding=ref(folder/'reference-binding.json'),
        charged_slots=counted,
        disposition='UNSTARTED_SERVICE_WORK' if circuit else 'REVIEWED_REPAIR_REQUIRED',
        authorized_for_redispatch=False))
value = dict(profile='p14-retained-failure-continuation-proposal.v1',
    dispositions=dict(Counter(r['disposition'] for r in rows)),
    count=len(rows), provider_calls=0, old_attempts_unchanged=True, legal_acceptance=False, rows=rows)
(OUT/'repair-queue.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k != 'rows'},indent=2))
