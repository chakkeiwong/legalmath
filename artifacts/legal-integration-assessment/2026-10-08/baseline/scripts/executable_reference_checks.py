"""Offline replay of actual historical responses, without manufacturing judgments."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT), str(ROOT/'scripts')]
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import executable_references_v2 as refs, fidelity_v2 as fv, source_references
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.interpretation.assurance.diversity import save
from assurance_continuation_checks import retained
from assurance_capacity_checks import D0


def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def relative(p): return str(Path(p).relative_to(ROOT))


def check_manifest(path, output_key='outputs', success='PASSED'):
    value = read(path)
    if value['status'] != success: raise RuntimeError('Failed predecessor: '+str(path))
    base = ROOT if output_key == 'outputs' else path.parent
    for name, expected in value[output_key].items():
        if sha(base/name) != expected: raise RuntimeError('Changed predecessor output: '+name)
    return {'path': relative(path), 'sha256': sha(path), 'verified_outputs': len(value[output_key])}


def run(work):
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    capacity = read(ROOT/'artifacts/assurance-capacity/2026-09-29/final-report.json')
    imported = {}
    for phase, ref in capacity['phase_receipts'].items():
        path = ROOT/ref['path']
        if sha(path) != ref['sha256']: raise RuntimeError('Changed capacity manifest')
        imported['capacity.'+phase] = check_manifest(path)
    for phase in ('G3', 'G4'):
        path = ROOT/'docs/implementation/eligibility-gap-closure'/phase/'attempt-001/manifest.json'
        imported[phase] = check_manifest(path, 'output_hashes', 'PASS')
    baseline = D0(work/'inherited')
    _, dossier, packet, claims, readings = retained('25ec66')
    questions = {r['candidate_id']: r['question'] for r in dossier['questions']['assignments']}
    schema = fv.FidelityV2.model_json_schema()
    base = ROOT/'artifacts/assurance-continuation/2026-09-29/C6/attempt-02/scoped/model'
    immutable = {relative(p): sha(p) for p in base.rglob('*') if p.is_file()}
    rows = []; old_counts = Counter(); derived_counts = Counter()
    for directory in sorted(base.glob('action-*')):
        raw_path = directory/'source-references/resolved-response.json'
        if not raw_path.exists(): continue
        original = read(raw_path); original_hash = digest(original)
        request = read(directory/'request.json'); outcome = read(directory/'result.json')
        pairs = [(p['claim_id'], p['candidate_id']) for p in request['required_pairs']]
        historical_error = None
        try:
            checked = fv.validate(original, packet, claims, readings, questions, pairs)
            status = 'VALIDATED_PROPOSAL'
            if checked != outcome.get('value'): raise RuntimeError('Historical validated value changed')
        except LegalMathError as exc:
            status = 'REJECTED_RESPONSE'; historical_error = {'code': exc.code, 'details': exc.details}
            if exc.code != outcome['diagnostic']['error']: raise RuntimeError('Historical rejection changed')
        if status != outcome['status']: raise RuntimeError('Historical acceptance status changed')
        old_counts[status] += 1
        # This is a NEW offline request with explicit original-reading identity,
        # not a rewrite of the historical request or a new model observation.
        upgraded = deepcopy(request)
        for candidate in upgraded['candidates']: candidate['reading_hash'] = digest(readings[candidate['candidate_id']])
        upgraded = compact_request(upgraded, profile='v2')
        wire, wire_schema, table = refs.prepare(upgraded, schema, readings=readings, questions=questions)
        combined, _, _ = source_references.prepare(wire, wire_schema)
        # Historical literal quotes are not v2 identifiers. Rejection here is a
        # protocol check only; the original semantic decision was replayed above.
        literal_error = None
        try:
            refs.resolve(original, upgraded, schema, table, readings=readings, questions=questions)
        except LegalMathError as exc:
            literal_error = {'code': exc.code, 'details': exc.details}
        text = {c['candidate_id']: c['representation'] for c in upgraded['candidates']}
        encoded = deepcopy(original); unavailable_quotes = []
        for row in encoded['checks']:
            selected = []
            for quote in row['executable_correspondence']['representation_quotes']:
                matches = [s for s in table['spans'] if s['candidate_id'] == row['candidate_id'] and
                    text[row['candidate_id']][s['start_codepoint']:s['end_codepoint']] == quote]
                if not matches:
                    unavailable_quotes.append({'claim_id': row['claim_id'], 'candidate_id': row['candidate_id'], 'quote': quote})
                else: selected.append(matches[0]['span_id'])
            row['executable_correspondence']['representation_quotes'] = selected
        derived_error = None; resolved = None
        if unavailable_quotes:
            derived = 'NOT_REENCODABLE_WITHOUT_CHANGING_QUOTATION'
            # Do not emit a shortened response whose evidence differs from what
            # the model supplied. Preserve the unmappable quotation explicitly.
            encoded = None
        else:
            try:
                resolved = refs.resolve(encoded, upgraded, schema, table, readings=readings, questions=questions)
                if resolved != original: raise RuntimeError('Re-encoding changed a historical judgment')
                fv.validate(resolved, packet, claims, readings, questions, pairs)
                derived = 'VALIDATED_UNCHANGED'
            except LegalMathError as exc:
                derived = 'REJECTED_UNCHANGED'; derived_error = {'code': exc.code, 'details': exc.details}
        if digest(original) != original_hash: raise RuntimeError('Input response mutated')
        derived_counts[derived] += 1
        record = {'action': directory.name, 'historical_path': relative(raw_path), 'historical_sha256': sha(raw_path),
            'historical_status': status, 'historical_error': historical_error, 'derived_status': derived,
            'v2_literal_protocol_rejection': literal_error,
            'derived_error': derived_error, 'unselectable_quotes': unavailable_quotes,
            'combined_wire_bytes': len(canonical(combined)), 'within_existing_200000_bound': len(canonical(combined)) <= 200000,
            'new_request_hash': digest(upgraded), 'original_response_hash': original_hash, 'table_hash': digest(table)}
        save(work/'replay'/directory.name/'record.json', record)
        save(work/'replay'/directory.name/'request.json', upgraded)
        save(work/'replay'/directory.name/'references.json', table)
        save(work/'replay'/directory.name/'original-response.json', original)
        if encoded is not None: save(work/'replay'/directory.name/'selected-response.json', encoded)
        if resolved is not None: save(work/'replay'/directory.name/'resolved-response.json', resolved)
        rows.append(record)
    if old_counts != {'VALIDATED_PROPOSAL': 27, 'REJECTED_RESPONSE': 9}: raise RuntimeError(str(old_counts))
    unencoded = [r for r in rows if r['historical_error'] and
        r['historical_error']['details'].get('claim_id') == 'claim.9393beb42f3f951c0d910e5a' and
        r['historical_error']['details'].get('candidate_id') == 'node.8eb374ffa546ddd2ba291e37' and
        r['historical_error']['details'].get('field') == 'executable_correspondence.status']
    if len(unencoded) != 2 or any(r['v2_literal_protocol_rejection'] is None or
            r['derived_status'] not in ('REJECTED_UNCHANGED', 'NOT_REENCODABLE_WITHOUT_CHANGING_QUOTATION') for r in unencoded):
        raise RuntimeError('Unencoded OMITS failures were not preserved')
    if any(sha(ROOT/p) != h for p, h in immutable.items()): raise RuntimeError('Original journal changed')
    save(work/'historical-files.json', immutable)
    result = {'status': 'D2_OFFLINE_EVIDENCE_CHECKED', 'predecessors': imported, 'inherited': baseline,
        'historical_responses': len(rows), 'historical_statuses': dict(old_counts), 'derived_statuses': dict(derived_counts),
        'unencoded_omits_rejections_preserved': len(unencoded), 'maximum_combined_wire_bytes': max(r['combined_wire_bytes'] for r in rows),
        'oversized_batches': [r['action'] for r in rows if not r['within_existing_200000_bound']],
        'rows': rows, 'historical_files_unchanged': True, 'historical_study_complete': False,
        'live_calls': 0, 'live_model_comprehension': 'NOT_TESTED', 'legal_correctness': 'NOT_ESTABLISHED',
        'unknown_future_legal_generalization': 'NOT_ESTABLISHED'}
    save(work/'result.json', result)
    return result


if __name__ == '__main__':
    result = run(Path(sys.argv[1]))
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'predecessors')}))
