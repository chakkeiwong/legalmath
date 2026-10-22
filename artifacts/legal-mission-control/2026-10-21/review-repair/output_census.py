"""Describe retained wire sizes; never dispatch or certify semantic validity."""
from pathlib import Path
from collections import Counter
import json
import os
import statistics
import sys
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from legalmath.canonical import canonical
from legalmath.interpretation.assurance.bounded_context import tokenizer
from scripts.legal_integration_master import TOKENIZER
encode = tokenizer(ROOT/TOKENIZER)
base = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface/live'
rows = []
for path in sorted(base.rglob('wire-response.json')):
    parent = path.parent
    request = json.loads((parent/'request.json').read_text())
    if request['task'] != 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
        continue
    value = json.loads(path.read_text())['value']
    result = json.loads((parent/'result.json').read_text())
    data = canonical(value)
    rows.append(dict(path=str(parent.relative_to(ROOT)), items=len(request['required_considered']),
        rationales=len(value.get('analyses', [])), tokens=len(encode(data.decode())), bytes=len(data),
        status=result['status']))
tokens = [r['tokens'] for r in rows]
summary = dict(provider_calls=0, wire_outputs=len(rows), statuses=dict(Counter(r['status'] for r in rows)),
    items=dict(Counter(r['items'] for r in rows)), maximum_tokens=max(tokens, default=0),
    median_tokens=statistics.median(tokens) if tokens else 0,
    maximum_tokens_per_assignment=max((r['tokens']/r['items'] for r in rows), default=0),
    scope='Descriptive outputs from existing small groups. Does not establish large-group adequacy.', rows=rows)
(Path(__file__).parent/'output-census.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k != 'rows'}))
