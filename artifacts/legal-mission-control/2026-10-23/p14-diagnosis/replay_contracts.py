"""Reconstruct retained bindings and measure opt-in contracts, without dispatch."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import sys
import time
import importlib.util

ROOT = Path('/home/chakwong/python/legalmath')
CANDIDATE = Path('/tmp/legalmath-p14-repair-20261023')
OUT = Path(__file__).resolve().parent
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(CANDIDATE/'src'), str(CANDIDATE)]
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.bounded_context import tokenizer, Limits
from legalmath.interpretation.assurance.bounded_product import GUIDANCE
from legalmath.interpretation.assurance.phased import review_contract, capacity_policy, downstream_input
from legalmath.interpretation.assurance.phased.account_input import input_token_limit
from legalmath.interpretation.assurance.phased.account_encoding import expand as expand_encoding

spec = importlib.util.spec_from_file_location(
    'legalmath.interpretation.assurance._baseline_references',
    ROOT/'src/legalmath/interpretation/assurance/bounded_references.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

def ordered_schema(value):
    if isinstance(value, list):
        return [ordered_schema(v) for v in value]
    if not isinstance(value, dict):
        return value
    result = {k:ordered_schema(v) for k,v in value.items()}
    if 'properties' in result:
        props = result['properties']
        order = result.get('required', [])
        result['properties'] = {k:props[k] for k in order if k in props} | {
            k:v for k,v in props.items() if k not in order}
    return result

encode = tokenizer(ROOT/'.localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken')
start = time.monotonic()
census = json.loads((OUT/'census.json').read_text())
rows = []
for item in census['wire_contracts']:
    path = ROOT/item['binding']['path']
    data = path.read_bytes()
    assert sha256(data).hexdigest() == item['binding']['sha256']
    old = json.loads(data)
    request, shape = old['original_request'], old['original_schema']
    historical_reload = baseline.prepare(request, shape)
    assert bounded_references.prepare(request, shape) == historical_reload, 'Legacy behavior changed: '+item['key']
    revised = {**deepcopy(request), review_contract.FIELD: review_contract.PROFILE}
    new = bounded_references.prepare(revised, shape)
    reloaded = json.loads(json.dumps(new, sort_keys=True))
    assert bounded_references.prepare(reloaded['original_request'], reloaded['original_schema']) == new
    wire = new['request']
    targets = wire['response_assignment_targets']
    assert [t['response_key'] for t in targets] == request['required_considered']
    assert [t['assignment_id'] for t in targets] == wire['required_considered']
    assert all(new['aliases'][t['assignment_id']] == t['response_key'] for t in targets)
    assert new['schema'] == old['schema'] and new['original_schema'] == old['original_schema']
    assert new['original_request']['records'] == request['records']
    assert new['original_request']['payload'] == request['payload']
    # Compare the entire transmitted content except the explicitly revised
    # assignment instruction and new mapping/profile; no evidence is rewritten.
    restored = expand_encoding(dict(request=wire, response_schema=new['schema']))['request']
    old_wire = expand_encoding(dict(request=old['request'], response_schema=old['schema']))['request']
    restored.pop(review_contract.FIELD)
    restored.pop('response_assignment_targets')
    restored['payload']['assignment'] = old_wire['payload']['assignment']
    restored['response_reference_instructions'] = old_wire['response_reference_instructions']
    assert restored == old_wire, 'Unexpected wire change: '+item['key']
    body = canonical(dict(request=wire, response_schema=new['schema'],
        product_instructions=capacity_policy.guidance(GUIDANCE, capacity_policy.selected(revised))))
    max_bytes = downstream_input.input_byte_limit(revised, Limits())
    max_tokens = input_token_limit(revised, Limits())
    tokens = len(encode(body.decode()))
    rows.append(dict(key=item['key'], original_binding=item['binding'],
        revised_binding_hash=digest(new), targets=len(targets),
        context_assignments=len(wire['payload']['assignments']),
        visible_bytes=len(body), visible_local_tokens=tokens,
        maximum_bytes=max_bytes, maximum_local_tokens=max_tokens,
        fits=len(body) <= max_bytes and tokens <= max_tokens,
        unchanged_context=True, unchanged_legacy_behavior=True,
        baseline_sorted_reload_matches=historical_reload == old, candidate_sorted_reload_matches=True))
result = dict(at_utc=datetime.now(timezone.utc).isoformat(), candidate=str(CANDIDATE),
    count=len(rows), unchanged_legacy_behavior=len(rows), preserved_context=len(rows),
    baseline_sorted_reload_mismatches=sum(not r['baseline_sorted_reload_matches'] for r in rows),
    maximum_visible_bytes=max(r['visible_bytes'] for r in rows),
    maximum_visible_local_tokens=max(r['visible_local_tokens'] for r in rows),
    over_limit=[r['key'] for r in rows if not r['fits']], provider_calls=0,
    limitation='Product-visible measurement only; hidden provider framing and live model behavior untested.',
    legal_acceptance=False, seconds=time.monotonic()-start, bindings=rows)
(OUT/'contract-replay.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k != 'bindings'}, indent=2))
