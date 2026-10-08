"""Offline D0/D1 evidence checks. No live model or allowance reservation path."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT), str(ROOT/'scripts')]
from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import readable_tables as rt, source_references as refs, single_reader as sr
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.interpretation.assurance.issue_limits import IssueLimits
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.search.models import Settings
from assurance_continuation_checks import baseline, retained, GRANT, OLD
from assurance_successor_audit import audit_journals, check_scoped_result

PRIOR = ROOT/'artifacts/assurance-continuation/2026-09-29'


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def relative(path): return str(Path(path).relative_to(ROOT))


def reference(ref):
    path = ROOT/ref['path']
    if not path.resolve().is_relative_to(ROOT) or sha(path) != ref['sha256']:
        raise LegalMathError('E_INTEGRITY', details='Changed inherited evidence: '+ref['path'])
    return path


def D0(work):
    report = read(PRIOR/'final-report.json')
    assessment_path = reference(report['assessment']); assessment = read(assessment_path)
    if assessment['input_changes'] or assessment['regression'] != report['regression']:
        raise LegalMathError('E_INTEGRITY')
    for path, expected in assessment['outputs'].items():
        if sha(assessment_path.parent/path) != expected: raise LegalMathError('E_INTEGRITY')
    archive_path = reference(report['tested_input_archive'])
    isolation = read(PRIOR/'final-assessment/isolation-repair/manifest.json')
    if sha(PRIOR/'final-assessment/isolation-repair/manifest.json') != assessment['isolation_manifest_sha256']:
        raise LegalMathError('E_INTEGRITY')
    with ZipFile(archive_path) as archive:
        if set(archive.namelist()) != set(isolation['inputs']): raise LegalMathError('E_INTEGRITY')
        for path, expected in isolation['inputs'].items():
            if hashlib.sha256(archive.read(path)).hexdigest() != expected: raise LegalMathError('E_INTEGRITY')
    for attempts in report['phases'].values():
        for attempt in attempts:
            manifest = read(reference(attempt['manifest']))
            for path, expected in manifest['outputs'].items():
                if sha(ROOT/path) != expected: raise LegalMathError('E_INTEGRITY')
    baseline_result = baseline(work/'source-check')
    grant = GrantedAllowance(GRANT).verify()
    if grant != report['live']['grant'] or grant['used'] != grant['maximum']:
        raise LegalMathError('E_INTEGRITY', details='Changed inherited grant accounting')
    task, dossier, packet, claims, readings = retained('25ec66')
    questions = {r['candidate_id']: r['question'] for r in dossier['questions']['assignments']}
    all_pairs = {(c['claim_id'], ident) for c in claims for ident in readings}
    old_scoped = list((OLD/'unfamiliar-study/25ec66/ensemble').glob('revisions/*/scoped/result.json'))
    old_complete = set(); scoped_receipts = []
    for path in old_scoped:
        scoped_receipts.append(check_scoped_result(path, packet, claims, readings, questions))
        value = read(path)
        old_complete.update(tuple(pair) for b in value['batches'] if not b['missing_perspectives'] for pair in b['required_pairs'])
    live = read(reference(report['live']['raw_evidence']))
    scoped_path = PRIOR/'C6/attempt-02/scoped/result.json'
    if read(scoped_path) != live['new_scoped_result']: raise LegalMathError('E_INTEGRITY')
    scoped_receipts.append(check_scoped_result(scoped_path, packet, claims, readings, questions))
    new = live['new_scoped_result']
    new_complete = {tuple(p) for b in new['batches'] if not b['missing_perspectives'] for p in b['required_pairs']}
    pending = all_pairs - (old_complete | new_complete)
    disputes = [d for b in new['batches'] if b.get('reconciliation') for d in b['reconciliation']['disputes']]
    if (len(all_pairs) != 225 or len(pending) != 60 or len(disputes) != 42 or
            pending != set(map(tuple, live['remaining_pairs'])) or
            set(map(tuple, new['required_pairs'])) != all_pairs - old_complete):
        raise LegalMathError('E_INTEGRITY', details='Inherited question denominator or disputes changed')
    journals = audit_journals(OLD/'unfamiliar-study') + audit_journals(PRIOR/'C6')
    histories = {}
    for base in (OLD/'unfamiliar-study', PRIOR/'C6', PRIOR/'split-capacity'):
        for p in sorted(base.rglob('*.json')):
            if 'issue' not in p.name: continue
            value = read(p)
            binding = value.get('value', {}).get('binding', {}) if isinstance(value, dict) else {}
            if 'maximum_attempts' not in binding: continue
            limits = IssueLimits(p, binding['inputs'], maximum_attempts=binding['maximum_attempts'],
                deadline_seconds=binding['deadline_seconds'], inherited=binding['inherited'])
            histories[relative(p)] = {'sha256': sha(p), 'issues': limits.report()}
    task_rows = []
    for task in read(OLD/'unfamiliar-study/result.json')['tasks']:
        row = {'task_id': task['task_id'], 'arms': {}}
        for arm in ('ensemble', 'single'):
            path = OLD/'unfamiliar-study'/task['task_id']/(arm+'-allowance.json')
            budget = read(path)
            row['arms'][arm] = {'path': relative(path), 'sha256': sha(path), 'ledger': budget}
        task_rows.append(row)
    state = read(PRIOR/'state.json')
    immutable = {relative(p): sha(p) for p in [PRIOR/'final-report.json', GRANT,
        GrantedAllowance(GRANT).path, GrantedAllowance(GRANT).predecessor, PRIOR/'state.json',
        *[ROOT/a['path'] for attempts in state['phases'].values() for a in attempts]]}
    result = {'status': 'INHERITED_EVIDENCE_REVERIFIED', 'tasks': task_rows,
        'grant': grant, 'all_ucits_pairs': sorted(all_pairs), 'pending_pairs': sorted(pending),
        'disputes': disputes, 'readings': readings, 'questions': questions,
        'authority_questions': report['authority_questions'], 'native_journals': journals,
        'native_scoped_checks': scoped_receipts, 'native_issue_histories': histories,
        'source_check': baseline_result, 'immutable': immutable,
        'live_calls': 0, 'historical_study_complete': False, 'legal_correctness': 'NOT_ESTABLISHED'}
    save(work/'inherited-state.json', result)
    return {'status': result['status'], 'tasks': len(task_rows), 'pairs': len(all_pairs),
        'pending_pairs': len(pending), 'disputes': len(disputes), 'readings': len(readings),
        'authority_questions': len(result['authority_questions']), 'native_journals': len(journals),
        'live_calls': 0, 'remaining_live_authorization': 0, 'legal_correctness': 'NOT_ESTABLISHED'}


def D1(work):
    # Reuse preserved synthetic coverage, never supply a legal answer key.
    from tests.search.support import FunctionProvider
    from tests.assurance.test_capacity_tables import decoded_response
    base = PRIOR/'split-capacity'
    original = read(base/'run/model/action-0015/references/wire-request.json')
    wire = rt.encode(original); restored = rt.decode(wire, expected_request_hash=digest(original))
    if canonical(restored) != canonical(original) or len(canonical(wire)) >= 200000:
        raise LegalMathError('E_RESOURCE_LIMIT', details='Retained request capacity criterion failed')
    save(work/'retained-encoded-request.json', wire)
    save(work/'retained-round-trip.json', {'request_hash': digest(original), 'restored_hash': digest(restored),
        'original_bytes': len(canonical(original)), 'encoded_bytes': len(canonical(wire)),
        'limit': 200000, 'headroom_bytes': 200000-len(canonical(wire))})
    frozen = read(OLD/'study-source-freeze.json')
    packet = next(t['packet'] for t in frozen['tasks'] if t['task_id'] == '26ec35')
    previous = read(base/'run/result.json'); interpretation = previous['interpretations'][0]
    provider = FunctionProvider(decoded_response(packet, interpretation, all_unresolved=True))
    run = sr.run(packet, provider, work/'full-source-simulation', transport_profile=rt.PROFILE)
    if (not run['execution_complete'] or run['coverage'] != previous['coverage'] or
            len(run['reconciliations'][0]['concerns']) != 263 or
            any(c['status'] != 'RETAINED_UNRESOLVED' for c in run['reconciliations'][0]['concerns'])):
        raise LegalMathError('E_INTEGRITY', details='Full context or uncertainty lost')
    sizes = [len(canonical(req)) for req in provider.requests]
    if max(sizes) >= 200000: raise LegalMathError('E_INTEGRITY')
    # A distinct shape with many unique, substantive strings must retain a
    # capacity failure instead of dropping text to obtain the smaller result.
    long_request = read(base/'run/model/action-0015/references/original-request.json')
    for i, row in enumerate(long_request['coverage']['units']):
        row['rationale'] = f'Unique qualification {i}: '+''.join(digest([i, n]) for n in range(20))
    for i, row in enumerate(long_request['coverage']['concerns']):
        row['explanation'] = f'Unrelated concern {i}: '+digest(row)
        row['evidence'].append(deepcopy(long_request['coverage']['units'][(i+17) % 263]['evidence'][0]))
    long_request['coverage_hash'] = digest(long_request['coverage'])
    long_request['output_identity_contract']['coverage_hash'] = long_request['coverage_hash']
    unused = FunctionProvider(lambda request: (_ for _ in ()).throw(AssertionError('Oversized dispatch')))
    try:
        refs.complete(unused, long_request, sr.Reconciliation.model_json_schema(), Settings(
            timeout_seconds=300, max_input_bytes=200000, max_output_bytes=200000), work/'unique-overflow', input_profile=rt.PROFILE)
    except LegalMathError as exc:
        if exc.code != 'E_RESOURCE_LIMIT': raise
        overflow = {'status': 'RETAINED_CAPACITY_QUALIFICATION', 'error': exc.code,
                    **read(work/'unique-overflow/encoding-validation.json')}
    else: raise LegalMathError('E_INTEGRITY', details='Oversized challenge unexpectedly dispatched')
    if unused.requests: raise LegalMathError('E_INTEGRITY')
    result = {'status': 'EXACT_CONTEXT_PRESERVED_SIMULATED_PROCESSING_COMPLETE',
        'baseline_original_hash': digest(original), 'coverage_hash': digest(run['coverage'][0]),
        'source_hash': digest(packet), 'source_units': len(packet['units']),
        'questions': len(interpretation['questions']), 'concerns': len(run['reconciliations'][0]['concerns']),
        'original_bytes': len(canonical(original)), 'encoded_bytes': len(canonical(wire)),
        'configured_limit_bytes': 200000, 'headroom_bytes': 200000-len(canonical(wire)),
        'simulated_requests': len(provider.requests), 'request_sizes': sizes,
        'unique_overflow': overflow, 'live_calls': 0, 'synthetic_only': True,
        'model_comprehension_of_encoding': 'NOT_TESTED', 'legal_correctness': 'NOT_ESTABLISHED',
        'unknown_future_legal_generalization': 'NOT_ESTABLISHED', 'release_eligible': False}
    save(work/'result.json', result); return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['D0', 'D1']); parser.add_argument('directory', type=Path)
    args = parser.parse_args(); args.directory.mkdir(parents=True, exist_ok=True)
    result = globals()[args.phase](args.directory); save(args.directory/'result.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'request_sizes'}, sort_keys=True))
