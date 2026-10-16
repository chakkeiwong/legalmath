"""Offline hybrid-fixture workload screen; no product or provider execution."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.legal_mission_evidence_route_design import (
    RUN, OUT, WIRE_LIMIT, decode, encode, read, ref, require, save,
)
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance import fidelity_v2, source_references
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.semantics import merge_inventories
from legalmath.interpretation.assurance.source_context import augment, check_envelope
from legalmath.interpretation.assurance.scoped_investigation import capacity

PLAN = ROOT / 'docs/implementation/legal-mission-control/staged-method-review.md'


def main():
    start = time.monotonic()
    require(not (OUT / 'staged-capacity.json').exists(), 'retained result exists')
    packet_path = Path(read(RUN / 'baseline/result.json')['details']['interpretation_directory']) / 'packet.json'
    packet, context = read(packet_path), read(RUN / 'qualified-source-context.json')
    retained_wire = read(OUT / 'requests/retained-partial-cross.json')
    wire = retained_wire['wire']
    original = decode(wire, expected_request_hash=retained_wire['prepared_hash'],
                      expected_packet_hash=context['compact_packet_hash'])
    claims = merge_inventories({'atomic-reader': original['inventory']})
    require(len(claims) == 78, 'partial claim count changed')
    history_path = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/inputs.json'
    historical = read(history_path)
    require(ref(history_path)['sha256'] == '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf',
            'historical input changed')
    mapping = {}
    for old in historical['packet']['units']:
        matches = [u for u in packet['units'] if u['text'].count(old['text']) == 1]
        require(len(matches) == 1, 'ambiguous historical source mapping')
        mapping[old['unit_id']] = matches[0]['unit_id']

    def remap(node):
        if isinstance(node, dict):
            return {k: mapping[v] if k == 'unit_id' and v in mapping else
                    [mapping.get(x, x) for x in v] if k == 'source_unit_ids' else remap(v)
                    for k, v in node.items()}
        if isinstance(node, list):
            return [remap(v) for v in node]
        return deepcopy(node)

    candidates, questions = remap(historical['candidates']), remap(historical['questions'])
    require(len(candidates) == 12 and set(questions) == set(candidates), 'historical population changed')
    pairs = sorted((c['claim_id'], cid) for c in claims for cid in candidates)
    results = []
    for batch_size in (12, 32, 48, 64):
        rows, accounted = [], []
        for start_pair in range(0, len(pairs), batch_size):
            assigned = pairs[start_pair:start_pair + batch_size]
            claim_ids, candidate_ids = {c for c, _ in assigned}, {r for _, r in assigned}
            request = fidelity_v2.request(packet, [c for c in claims if c['claim_id'] in claim_ids],
                {k: v for k, v in candidates.items() if k in candidate_ids},
                {k: v for k, v in questions.items() if k in candidate_ids}, assigned)
            request['investigation'] = {'batch': len(rows), 'round': 1,
                'perspective': 'qualification-first', 'prior_round_evidence': None,
                'instruction': 'HYBRID ENGINEERING FIXTURE: no actual legal review.'}
            qualified = augment(request, context)
            prepared, schema, _ = source_references.prepare(
                compact_request(qualified, profile='v2'), fidelity_v2.FidelityV2.model_json_schema())
            wire, quote_count = encode(prepared)
            check_envelope(decode(wire, expected_request_hash=digest(prepared),
                                  expected_packet_hash=context['compact_packet_hash']), context)
            rows.append({'batch': len(rows), 'pairs': len(assigned),
                'request_hash': digest(qualified), 'prepared_hash': digest(prepared),
                'wire_hash': digest(wire), 'wire_bytes': len(canonical(wire)),
                'schema_bytes_separate': len(canonical(schema)), 'quote_occurrences': quote_count})
            accounted.extend(assigned)
        require(accounted == pairs, 'missing, duplicated or reordered pair')
        results.append({'batch_size': batch_size, **capacity(len(pairs), batch_size, 82),
            'full_pair_assignment': True, 'minimum_wire_bytes': min(r['wire_bytes'] for r in rows),
            'maximum_wire_bytes': max(r['wire_bytes'] for r in rows),
            'all_inputs_fit': all(r['wire_bytes'] <= WIRE_LIMIT for r in rows), 'batches_measured': rows,
            'output_quality_latency_qualified': False})
    # Preserve both fidelity stages and all original sources. No putative
    # savings from deleting the core matrix are credited.
    scenarios = []
    for count in (78, 156, 200, 558, 800):
        for n in (12, 20):
            for size in (12, 32, 48, 64):
                pairs_n = count * n
                scoped = capacity(pairs_n, size, 82)
                # All relevant claims/all executable candidates is an explicit
                # pressure assumption, not an assertion about actual readings.
                core_matrix = (pairs_n + 31) // 32
                scenarios.append({'claims': count, 'candidates': n, 'scoped_batch_size': size,
                    'pairs': pairs_n, 'pair_cap_fits': pairs_n <= 4096,
                    'scoped_minimum_calls': scoped['minimum_actions'],
                    'core_matrix_pressure_calls': core_matrix,
                    'both_fidelity_stages_only': core_matrix + scoped['minimum_actions'],
                    'calls_left_from_174_after_fidelity_only': 174 - core_matrix - scoped['minimum_actions'],
                    'other_required_stages_included': False})
    result = {'status': 'INPUT_AND_WORKLOAD_SCREEN_ONLY_NO_METHOD_ADMISSION',
        'evidence_class': 'HYBRID_ACTUAL_PARTIAL_CLAIMS_AND_HISTORICAL_READINGS',
        'source_units': 55, 'actual_partial_claims': 78, 'historical_candidates': 12,
        'required_pairs': len(pairs), 'screens': results, 'workload_scenarios': scenarios,
        'qualification': 'Exact source mapping and bytes only; no actual complete inventory or candidate generation.',
        'no_default_selected': True, 'new_live_calls': 0, 'production_repairs': 0,
        'method': ref(Path(__file__)), 'plan': ref(PLAN), 'codec': ref(ROOT / 'scripts/legal_mission_evidence_route_design.py'),
        'inputs': [ref(packet_path), ref(history_path), ref(OUT / 'requests/retained-partial-cross.json')],
        'command': '.venv/bin/python scripts/legal_mission_staged_capacity_screen.py',
        'environment': {'python': sys.version, 'device': 'CPU; no GPU imports or calls', 'seed': 'N/A: deterministic'},
        'finished_at_utc': datetime.now(timezone.utc).isoformat(),
        'wall_seconds': round(time.monotonic() - start, 3)}
    save('staged-capacity.json', result)
    print(json.dumps({'status': result['status'], 'screens': [
        {k: v for k, v in r.items() if k != 'batches_measured'} for r in results]}))


if __name__ == '__main__':
    main()
