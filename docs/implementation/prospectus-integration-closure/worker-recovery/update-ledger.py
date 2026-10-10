"""Record inspected worker evidence without promoting native reuse or legal status."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = BASE / 'worker-recovery'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts.prospectus_closure_attribution import report  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    coverage = read(PACKAGE / 'validation-001/coverage.json')
    if coverage['status'] != 'PASS' or coverage['covered'] != coverage['unique_tests'] or coverage['missing']:
        raise ValueError('Complete passing current coverage required')
    if any(sha(ROOT / name) != value for name, value in coverage['method'].items()):
        raise ValueError('Validation method changed')
    for name in ('recovery-sequence/attempt-004', 'native-boundary/attempt-001', 'ocr-baseline/attempt-001'):
        folder = PACKAGE / name
        manifest = read(folder / 'manifest.json')
        actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        if actual != set(manifest['files']) or any(sha(folder / p) != value for p, value in manifest['files'].items()):
            raise ValueError('Worker evidence manifest changed: ' + name)
        if read(folder / 'result.json')['status'] != 'PASS':
            raise ValueError('Worker evidence failed: ' + name)
    native = read(PACKAGE / 'native-boundary/attempt-001/result.json')
    recovery = read(PACKAGE / 'recovery-sequence/attempt-004/result.json')
    if recovery['step_count'] != 11 or not all(row['stale_before_recovery_reason'] for row in recovery['steps']):
        raise ValueError('Recovery does not establish pre-marker invalidation')
    if native['read_context_reusable'] or native['trace_complete_for_reuse'] or native['production_policy_changed']:
        raise ValueError('Native diagnostic cannot authorize complete reuse')
    findings = {
        'G10': 'Each OCR model target is now bound to the declared source root before byte validation. The outside-root same-byte symlink defect is reproduced and repaired; actual two-page English OCR and model deletion/change/restoration preserve complete page and runtime evidence.',
        'G16': 'Eleven finite actual OCR/authored-XMI states match separate clean recomputation. Missing/changed model, copied interpreter deletion, authored-link deletion and corrupt XMI are rejected; restoration returns complete original products. Resource changes invalidate before the recovery reason record.',
        'G18': 'Actual strace direct/child/symlink/changed-file and failed-lookup controls pass. Bubblewrap denies outside fixture reads; the traced and confined actual OCR output equals the protected full baseline. Unbound native reads still veto production reuse; complete dependency binding is not established.',
        'G20': f'Worker recovery validation retains exact current partitioned coverage of {coverage["unique_tests"]} unique test identities, actual serial phase receipts and reviewed local failure attribution. Earlier failed probes are preserved and corrected by separate changed-method attempts.'}
    remaining = {
        'G10': 'Real multilingual/table scan quality, independently reviewed corrections and source authentication remain open.',
        'G16': 'Finite copied-input recovery does not bind environment-only changes or all host-library inputs. Broader corrected extraction and optional workers remain to be tested.',
        'G18': 'No production native-confinement integration or complete immutable dependency closure exists. Broad runtime mounts, proc/device/negative lookups, races and second-host portability remain open.'}
    actions = {
        'G10': 'Freeze named real prospectus table and bilingual pages with source occurrence and page oracles before comparing extraction.',
        'G16': 'Extend to reviewed correction-map and real multilingual extraction changes, preserving typed failures and pre-marker invalidation.',
        'G18': 'Design a supported immutable runtime/mount profile and bind failed lookups and runtime inputs before considering any reuse-policy change; test a second supported host separately.',
        'G20': 'Continue substantive source/extraction work after current validation; external acceptance remains separate.'}
    evidence = {
        'G10': ['model-path/attempt-001/result.json', 'model-path/attempt-002/result.json', 'ocr-baseline/attempt-001/result.json'],
        'G16': ['recovery-sequence/attempt-004/result.json', 'recovery-sequence/attempt-004/manifest.json'],
        'G18': ['native-boundary/attempt-001/result.json', 'native-boundary/attempt-001/manifest.json'],
        'G20': ['validation-001/coverage.json', 'validation-001/inventory.json']}
    ledger, review = read(BASE / 'gap-status.json'), read(BASE / 'attribution-review.json')
    for rows in (ledger['gaps'], review['gaps']):
        for row in rows:
            key = row['id']
            if key not in findings:
                continue
            row['finding'] = findings[key]
            if key in remaining:
                row['remaining'] = remaining[key]
            row['next_action'] = actions[key]
            paths = [str((PACKAGE / name).relative_to(ROOT)) for name in evidence[key]]
            if rows is ledger['gaps']:
                row['evidence'] = list(dict.fromkeys(row['evidence'] + paths))
            else:
                existing = {item['path'] for item in row['evidence']}
                row['evidence'].extend({'path': p, 'sha256': sha(ROOT / p)} for p in paths if p not in existing)
    for row in review['packages']:
        if row['package'] == 'PyMuPDF/Tesseract and Poppler':
            row['finding'] = findings['G10'] + ' ' + findings['G16']
            row['remaining'] = remaining['G10'] + ' ' + remaining['G16']
            paths = evidence['G10'] + evidence['G16']
        elif row['package'] == 'INCEpTION 38 / dkpro-cassis 0.10.1':
            row['finding'] += ' Actual authored-XMI link removal/corruption and restoration match clean service recomputation. The initial decoder mismatch was in the new mutation helper.'
            paths = evidence['G16']
        elif row['package'] == 'Hypothesis/pytest':
            row['finding'] = findings['G20'] + ' Baseline-observation, authored-schema and invalidation-marker probe flaws were identified and corrected locally.'
            paths = evidence['G20']
        else:
            continue
        existing = {item['path'] for item in row['evidence']}
        row['evidence'].extend({'path': str((PACKAGE / p).relative_to(ROOT)), 'sha256': sha(PACKAGE / p)}
            for p in paths if str((PACKAGE / p).relative_to(ROOT)) not in existing)
    review['packages'].append({'package': 'strace 5.16 / Bubblewrap 0.6.1',
        'finding': findings['G18'], 'remaining': remaining['G18'], 'next_action': actions['G18'],
        'fundamental_limitation_established': False,
        'evidence': [{'path': str((PACKAGE / p).relative_to(ROOT)), 'sha256': sha(PACKAGE / p)} for p in evidence['G18']]})
    reviewed_changes = {'src/legalmath/prospectus/successor/extraction.py',
        'src/legalmath/prospectus/successor/closure_program.py', 'tests/prospectus_successor/test_closure_runtime.py'}
    for row in review['gaps'] + review['packages']:
        for item in row['evidence']:
            current = sha(ROOT / item['path'])
            if current != item['sha256']:
                if item['path'] not in reviewed_changes:
                    raise ValueError('Unreviewed evidence drift: ' + item['path'])
                item['sha256'] = current
    ledger['review_date'] = '2026-10-11'
    ledger['last_review'] = 'Actual worker recovery and native boundary diagnostics pass; local model-path defect repaired. Production native reuse remains vetoed and independent acceptance is not established.'
    ledger['regression'] = {'path': str((PACKAGE / 'validation-001/coverage.json').relative_to(ROOT)),
        'passed': coverage['unique_tests'], 'execution': 'PARTITIONED_NODE_UNION',
        'method_unchanged': True, 'single_process_aggregate': False}
    ledger['worker_recovery'] = {'recovery': str((PACKAGE / 'recovery-sequence/attempt-004/result.json').relative_to(ROOT)),
        'native_boundary': str((PACKAGE / 'native-boundary/attempt-001/result.json').relative_to(ROOT)),
        'production_native_reuse': 'VETOED', 'portability': 'NOT_ESTABLISHED'}
    save(BASE / 'gap-status.json', ledger)
    save(BASE / 'attribution-review.json', review)
    save(BASE / 'final-attribution.json', report(ROOT))
    print(json.dumps({'status': 'UPDATED_REVIEWED_ATTRIBUTION', 'unique_tests': coverage['unique_tests']}))


if __name__ == '__main__':
    main()
