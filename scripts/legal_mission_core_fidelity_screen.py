"""Offline actual-core-fidelity input and admission screen; no provider dispatch."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.legal_mission_evidence_route_design import (
    OUT, RUN, WIRE_LIMIT, decode, encode, read, ref, require, save,
)
from legalmath.canonical import canonical, digest
from legalmath.domain import timestamp
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.semantics import (
    Fidelity, fidelity_request, merge_inventories,
    MAX_FIDELITY_BYTES, MAX_FIDELITY_CONCERNS, MAX_FIDELITY_PAIRS,
)
from legalmath.interpretation.assurance.source_context import augment, check_envelope
from legalmath.interpretation.assurance import source_references
from legalmath.interpretation.search.formal import bundle

PLAN = ROOT / 'docs/implementation/legal-mission-control/core-fidelity-review.md'
RESULT = OUT / 'core-fidelity-capacity.json'
HISTORY = ROOT / 'artifacts/legal-integration-coverage/2026-10-08/inputs.json'


def main():
    started = time.monotonic()
    require(not RESULT.exists(), 'retained core screen already exists')
    packet_path = Path(read(RUN / 'baseline/result.json')['details']['interpretation_directory']) / 'packet.json'
    packet, context = read(packet_path), read(RUN / 'qualified-source-context.json')
    retained_path = OUT / 'requests/retained-partial-cross.json'
    require(ref(retained_path)['sha256'] == 'bd405ed5813f45e6e3519d760bb652fc0bcc2b210b2cbd5d2cd1fa8b90211dec',
            'retained partial request changed')
    retained = read(retained_path)
    original = decode(retained['wire'], expected_request_hash=retained['prepared_hash'],
                      expected_packet_hash=context['compact_packet_hash'])
    claims = merge_inventories({'atomic-reader': original['inventory']})
    selected = [c for c in claims if c['relevance'] != 'CONTEXT']
    require((len(packet['units']), len(claims), len(selected)) == (55, 78, 67),
            'full packet or actual partial claims changed')
    require(ref(HISTORY)['sha256'] == '6aeeb1712cfc103e12174facf44ca367c247c700cbb8c1c4a75fcb5f130c8caf',
            'historical fixture changed')
    historical = read(HISTORY)
    at = timestamp('2026-10-10T00:00:00.000000Z')
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

    candidates = remap(historical['candidates'])
    require(len(candidates) == 12, 'historical candidate population changed')
    classification, pending = [], {}
    cached = []
    for cid, reading in candidates.items():
        try:
            bundle(reading, packet, at)
        except LegalMathError as exc:
            explanation = 'Executable representation unavailable: ' + exc.code + '; ' + str(exc.details)[:1200]
            cached.extend({'claim_id': c['claim_id'], 'candidate_id': cid, 'label': 'NOT_ESTABLISHED',
                           'source_evidence': [], 'representation_quotes': [], 'rationale': explanation,
                           'failing_stage': 'FORMALIZATION',
                           'question': 'Repair the unsupported expression or retain it as an unformalized interpretation.'}
                          for c in selected)
            classification.append({'candidate_id': cid, 'reading_hash': digest(reading),
                                   'core_path': 'DETERMINISTIC_ENCODER_DIAGNOSTIC', 'error': exc.code})
        else:
            pending[cid] = reading
            classification.append({'candidate_id': cid, 'reading_hash': digest(reading),
                                   'core_path': 'PENDING_MODEL_REVIEW_WITHOUT_CACHE'})
    all_pairs = {(c['claim_id'], cid) for c in selected for cid in candidates}
    cached_pairs = {(r['claim_id'], r['candidate_id']) for r in cached}
    pending_pairs = [(c['claim_id'], cid) for c in selected for cid in pending]
    require(len(cached) == len(cached_pairs) and cached_pairs.isdisjoint(pending_pairs)
            and cached_pairs | set(pending_pairs) == all_pairs, 'core matrix not conserved')
    require(len(all_pairs) <= MAX_FIDELITY_PAIRS, 'core pair capacity exceeded')
    cached_bytes = len(canonical({'checks': cached, 'additional_concerns': []}))
    screens = []
    for batch_size in (32, 64):
        measured, accounted = [], []
        for start in range(0, len(pending_pairs), batch_size):
            batch = pending_pairs[start:start + batch_size]
            request = fidelity_request(packet, claims, pending, batch)
            require(len(request['claims']) == len({c for c, _ in batch})
                    and len(request['candidates']) == len({r for _, r in batch}),
                    'core request failed to scope batch identities')
            qualified = augment(request, context)
            prepared, schema, _ = source_references.prepare(
                compact_request(qualified, profile='v2'), Fidelity.model_json_schema())
            wire, quote_count = encode(prepared)
            restored = decode(wire, expected_request_hash=digest(prepared),
                              expected_packet_hash=context['compact_packet_hash'])
            check_envelope(restored, context)
            measured.append({'batch': len(measured), 'pairs': len(batch),
                             'core_claims_supplied': len(request['claims']),
                             'core_candidates_supplied': len(request['candidates']),
                             'original_request_bytes': len(canonical(request)),
                             'qualified_request_bytes': len(canonical(qualified)),
                             'prepared_bytes': len(canonical(prepared)),
                             'encoded_wire_bytes': len(canonical(wire)),
                             'schema_bytes_separate': len(canonical(schema)),
                             'quote_occurrences': quote_count,
                             'request_hash': digest(qualified), 'prepared_hash': digest(prepared),
                             'wire_hash': digest(wire)})
            accounted.extend(batch)
        require(accounted == pending_pairs, 'pending core pairs missing, duplicated or reordered')
        batches = len(measured)
        # Mirrors engine._fidelity's no-cache conservative preflight. The
        # historical candidates are a hybrid fixture, not actual generated nodes.
        preflight_bytes = cached_bytes + batches * WIRE_LIMIT
        screens.append({'batch_size': batch_size, 'pending_batches': batches,
                        'minimum_core_calls_including_criticism': batches + 1,
                        'baseline_core_calls_remaining': 23,
                        'pending_pair_assignment_complete': True,
                        'maximum_encoded_wire_bytes': max((r['encoded_wire_bytes'] for r in measured), default=0),
                        'maximum_original_journal_bytes': max((r['original_request_bytes'] for r in measured), default=0),
                        'all_encoded_inputs_fit': all(r['encoded_wire_bytes'] <= WIRE_LIMIT for r in measured),
                        'old_journal_accepts_original': all(r['original_request_bytes'] <= WIRE_LIMIT for r in measured),
                        'conservative_preflight_bytes': preflight_bytes,
                        'conservative_preflight_fits': preflight_bytes <= MAX_FIDELITY_BYTES,
                        'worst_case_concerns': batches * 30,
                        'concern_preflight_fits': batches * 30 <= MAX_FIDELITY_CONCERNS,
                        'batches_measured': measured})
    result = {'status': 'CORE_INPUT_AND_PREFLIGHT_SCREEN_ONLY_NO_METHOD_ADMISSION',
              'evidence_class': 'HYBRID_ACTUAL_PARTIAL_CLAIMS_AND_HISTORICAL_READINGS',
              'source_units': len(packet['units']), 'actual_partial_claims': len(claims),
              'selected_noncontext_claims': len(selected), 'historical_candidates': len(candidates),
              'cached_deterministic_rows': len(cached), 'cached_rows_bytes': cached_bytes,
              'pending_pairs_without_cache': len(pending_pairs), 'all_pairs': len(all_pairs),
              'candidate_classification': classification, 'screens': screens,
              'qualification': 'Constructor inputs and no-cache preflight only; actual complete inventories, generated candidates, output, latency and legal reasoning unmeasured.',
              'new_live_calls': 0, 'production_repairs': 0, 'no_default_selected': True,
              'method': ref(Path(__file__)), 'plan': ref(PLAN),
              'inputs': [ref(packet_path), ref(retained_path), ref(HISTORY),
                         ref(RUN / 'qualified-source-context.json')],
              'code': [ref(ROOT / path) for path in (
                  'scripts/legal_mission_evidence_route_design.py',
                  'src/legalmath/interpretation/assurance/semantics.py',
                  'src/legalmath/interpretation/assurance/source_references.py',
                  'src/legalmath/interpretation/assurance/source_context.py',
                  'src/legalmath/interpretation/assurance/engine.py',
                  'src/legalmath/translation/model.py',
                  'src/legalmath/translation/ruleir.py')],
              'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'assessment_time': {'value': at, 'provenance': 'valid construction date for an engineering fixture; no temporal legal finding'},
              'command': '.venv/bin/python scripts/legal_mission_core_fidelity_screen.py',
              'environment': {'python': sys.version, 'device': 'CPU; no GPU imports or calls',
                              'seed': 'N/A: deterministic'},
              'finished_at_utc': datetime.now(timezone.utc).isoformat(),
              'wall_seconds': round(time.monotonic() - started, 3)}
    save(RESULT.name, result)
    print(json.dumps({'status': result['status'], 'selected_claims': len(selected),
                      'pending_pairs': len(pending_pairs), 'cached_rows': len(cached),
                      'screens': [{k: v for k, v in row.items() if k != 'batches_measured'}
                                  for row in screens]}))


if __name__ == '__main__':
    main()
