"""Debugging-only replay of the exact P14 candidate; never dispatch a model."""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, BoundDispatch
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.phased.synthesis_recovery import historical_request
from legalmath.interpretation.assurance.phased import downstream_input, account_input, account_encoding
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_master import TOKENIZER
from scripts.legal_integration_campaign import provider

WORK = Path(__file__).parent
SOURCE = ROOT / 'artifacts/legal-mission-control/2026-10-19/synthesis-resolution/live/p14/product'
program = read(ROOT / 'docs/implementation/legal-mission-control/integration-master.json')
envelope = read(ROOT / program['prerequisite_repair']['source']['path'])
route = ContextRoute(envelope, tokenizer(ROOT / TOKENIZER), limits=Limits())
require(route.records == read(SOURCE / 'source-store.json'), 'Reconstructed source store differs')
p = object.__new__(BoundedProduct)
p.root, p.directory, p.route = ROOT, WORK / 'p14-probe', route
p.selected_tools, p.active_questions = (), ('p14',)
captured = []
class Capture:
    def call(self, key, request, schema, validator):
        captured.append((key, request, schema))
        return {'status': 'FAILED', 'error': 'DEBUG_NO_DISPATCH'}
p.dispatch = Capture()
result = read(SOURCE / 'result.json')
# Restore the actual in-memory response field order from the retained provider
# event. Canonical JSON storage sorts keys, changing source_records traversal.
# Equality verifies every value against the validated result; no model is used.
for finding in result['answers']['p14']['findings']:
    folder = SOURCE / 'calls' / finding['id']
    raw = read(folder / 'raw.json')
    events = [json.loads(line) for line in raw['provenance']['events_jsonl'].splitlines() if line]
    messages = [e['item']['text'] for e in events if e.get('item', {}).get('type') == 'agent_message']
    require(len(messages) == 1, 'Ambiguous retained provider output')
    wire = read(folder / 'reference-binding.json')
    original_request = historical_request(wire, reviewed=True)
    def exact_saved(request, schema):
        require(request == original_request and schema == wire['original_schema'],
                'Decoder requested a different historical contract')
        return deepcopy(wire)
    with patch.object(bounded_references, 'prepare', exact_saved):
        restored_value = resolve(json.loads(messages[0]), wire,
                                 maximum_bytes=route.limits.decoded_output_bytes)
    require(restored_value == finding['value'] == read(folder / 'result.json')['value'],
            'Retained response values changed')
    finding['value'] = restored_value
question = next(q for q in envelope['original_questions'] if q['question_id'] == 'p14')
p.tools('p14', question, None, findings=result['answers']['p14']['findings'])
require(len(captured) == 1, 'Unexpected candidate construction count')
key, request, schema = captured[0]
service = provider()
dispatch = BoundDispatch(service, WORK / 'p14-probe/calls', route, maximum_calls=8100)
phase = read(SOURCE / 'phases/call-candidates-p14/phase.json')
require(key == 'candidates-p14' and dispatch.request_identity(request, schema) == phase['contract']['calls'][0]['identity'],
    'Probe does not reproduce the actual failed request')
try:
    dispatch.measure(request, schema)
except LegalMathError as exc:
    require(exc.code == 'E_RESOURCE_LIMIT', 'Different original failure')
    original_failure = {'error': exc.code, 'reason': str(exc.details or exc)}
else:
    raise AssertionError('Original failure did not reproduce')
plain = prepare(request, schema)
selected = deepcopy(request)
selected['downstream_input_profile'] = downstream_input.PROFILE
selected['downstream_capacity_profile'] = downstream_input.CAPACITY_PROFILE
# Test a proposed contract only inside this isolated process. No production
# file, active binding, selected default or provider call is changed.
with patch.object(downstream_input, 'TASKS', downstream_input.TASKS | {request['task']}):
    packed = prepare(selected, schema)
    expanded = account_encoding.expand({'request': packed['request'], 'response_schema': packed['schema']})
    restored = account_input.expand(expanded['request'])
    for field in ('downstream_input_profile', 'downstream_capacity_profile'):
        del restored[field]
    require(restored == plain['request'] and expanded['response_schema'] == plain['schema'],
        'Proposed candidate transport changes request or schema content')
    measured = dispatch.measure(selected, schema)
    provider_measured = service.measure(packed['request'], packed['schema'])
save(WORK / 'p14-capacity-reproduction.json', {
    'question': 'Does the actual P14 candidate fail locally and fit an explicitly proposed downstream contract?',
    'profile': 'debug-only-exact-candidate-capacity.v1',
    'baseline_phase': ref(ROOT, SOURCE / 'phases/call-candidates-p14/phase.json'),
    'baseline_result': ref(ROOT, SOURCE / 'result.json'),
    'request_identity_matches': True, 'original_failure': original_failure,
    'proposed_measurement': measured, 'proposed_provider_measurement': provider_measured,
    'expanded_request_and_schema_unchanged': True, 'provider_calls': 0,
    'production_sources_changed': False, 'cpu_only': True,
    'decision': 'Reproduced missing candidate capacity selection; proposed local transport fits.',
    'next_action': 'Review candidate and criticism contracts plus optional-phase dependency; freeze and register before live adoption.',
    'limits': 'No complete response decoding, provider acceptance, legal correctness, or production repair established.'})
print(json.dumps(read(WORK / 'p14-capacity-reproduction.json'), indent=2))
