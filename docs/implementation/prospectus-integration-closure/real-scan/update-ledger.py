"""Record inspected BES evidence without promoting raw extraction or eligibility."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = BASE / 'real-scan'
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
    if (coverage['status'] != 'PASS' or coverage['covered'] != coverage['unique_tests'] or
            coverage['unique_tests'] != 685 or coverage['missing'] or coverage['unexpected']):
        raise ValueError('Complete reviewed current coverage required')
    if any(sha(ROOT / name) != value for name, value in coverage['method'].items()):
        raise ValueError('Validation method changed')
    for name in ('analysis/attempt-001', 'authoring/attempt-001', 'consumer/attempt-001', 'focused-001'):
        folder = PACKAGE / name
        files = read(folder / 'manifest.json')['files']
        actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
        if actual != set(files) or any(sha(folder / p) != h for p, h in files.items()):
            raise ValueError('Real-scan evidence changed: ' + name)
        if read(folder / 'result.json')['status'] != 'PASS':
            raise ValueError('Real-scan prerequisite failed: ' + name)
    analysis = read(PACKAGE / 'analysis/attempt-001/result.json')
    consumer = read(PACKAGE / 'consumer/attempt-001/result.json')
    if (analysis['primary_automatic_criterion'] != 'FAIL' or analysis['target_denominator'] != 23 or
            analysis['supplied_region_exact'] != 16 or analysis['automatic_relations']['proposed'] != 0 or
            consumer['reviewed_targets'] != 23 or consumer['required_relationships'] != 8 or
            consumer['meaning_omissions'] != 23 or consumer['relationship_omissions'] != 8 or
            consumer['adverse_controls'] != 7 or consumer['independent_acceptance'] != 'NOT_ESTABLISHED'):
        raise ValueError('Reviewed interpretation differs from actual retained result')
    findings = {
        'G09': 'The BASF reviewed governing-edge consumer is joined by eight explicit BES row/qualification dependencies through the actual service. Both complete endpoints are required; all eight matched omissions expose unresolved dependencies. The raw BES route proposes zero of the eight required relations.',
        'G10': 'The OCR model-path boundary repair remains retained. A further local correction guard defect was reproduced: actual retained OCR method names bypassed the image requirement. The repaired guard passes twenty producer/service controls. Six BES pages have exact image identities; raw page text exactly contains 14 of 23 frozen targets, supplied regions 16 of 23. Eight image-reviewed replacements reach the actual source/annotation consumer with original words and geometry unchanged.',
        'G11': 'Authored local and reviewed cross-document relations reach typed clauses with exact binding. The BES consumer additionally preserves 23 supplied source readings through correction and annotation, with all original quotations retained. Every single-meaning omission restores uncovered original units; inserted/uncertain and partial replacement evidence is rejected.',
        'G20': 'Current real-scan validation covers all 685 unique collected test identities and actual serial phase receipts. The retained failed raw-trial region rule, its valid analysis, repaired image guard and successful assisted consumer have separate verdicts; engineering PASS does not promote automatic extraction or legal acceptance.'}
    remaining = {
        'G09': 'Automatic governing-relation prediction and broader unexposed scan families remain open. The 537 BASF intervals, calculation-agent authority and incorporation interpretations still require source-specific decisions.',
        'G10': 'The fixed English OCR profile still misses seven reviewed regions, including Portuguese text and the ISIN. Automated correction/row discovery, independent review, source authentication and missing BES incorporated sources are not established.',
        'G11': 'Actual reader-authored cross-document exports and independent semantics remain pending. BES is an agent-supplied preservation reading, not a new live browser or Cassis package trial.'}
    actions = {
        'G09': 'Design a source-bound row/qualification candidate and validate it against protected critical targets on an additional source family; keep reviewed dependencies and automatic proposals separate.',
        'G10': 'Inspect the actual OCR language/resource profile and geometry failure before a bounded extraction comparison; retain every failed target and compare only supported package configurations.',
        'G11': 'Continue source-specific consumer work locally; genuine independently authored browser exports require assigned qualified readers.',
        'G20': 'Continue the reviewed next substantive package without repeating unchanged passing diagnostics; retain separate package, engineering and external-acceptance conclusions.'}
    evidence = {
        'G09': ['analysis/attempt-001/result.json', 'consumer/attempt-001/comparisons.json', 'consumer/attempt-001/manifest.json'],
        'G10': ['image-binding/attempt-001/result.json', 'candidate-check/baseline-002/result.json', 'candidate-check/candidate-001/result.json',
                'integration-admission.json', 'focused-001/result.json', 'analysis/attempt-001/result.json', 'consumer/attempt-001/result.json'],
        'G11': ['authoring/attempt-001/review.json', 'consumer/attempt-001/comparisons.json', 'consumer/attempt-001/result.json'],
        'G20': ['validation-001/coverage.json', 'validation-001/inventory.json', 'baseline/attempt-001/result.json',
                'analysis/attempt-001/result.json', 'consumer/attempt-001/result.json']}
    ledger, review = read(BASE / 'gap-status.json'), read(BASE / 'attribution-review.json')

    def add_evidence(row, paths):
        existing = {item['path'] for item in row['evidence']}
        row['evidence'].extend({'path': str((PACKAGE / p).relative_to(ROOT)), 'sha256': sha(PACKAGE / p)}
            for p in paths if str((PACKAGE / p).relative_to(ROOT)) not in existing)

    for rows in (ledger['gaps'], review['gaps']):
        for row in rows:
            key = row['id']
            if key not in findings:
                continue
            row['finding'], row['next_action'] = findings[key], actions[key]
            if key in remaining:
                row['remaining'] = remaining[key]
            if rows is ledger['gaps']:
                row['evidence'] = list(dict.fromkeys(row['evidence'] +
                    [str((PACKAGE / name).relative_to(ROOT)) for name in evidence[key]]))
            else:
                add_evidence(row, evidence[key])
    for row in review['packages']:
        if row['package'] == 'PyMuPDF/Tesseract and Poppler':
            row['finding'] += ' ' + findings['G10']
            row['remaining'] = remaining['G10'] + ' Native immutable dependencies and second-host portability remain open.'
            add_evidence(row, evidence['G10'])
        elif row['package'] == 'Docling 2.60.1':
            row['remaining'] += ' BES was not run through the born-digital Docling profile, which disables OCR and table structure; no scan verdict about Docling follows from this service-only assisted case.'
            add_evidence(row, ['analysis/attempt-001/result.json', 'consumer/attempt-001/result.json'])
        elif row['package'] == 'INCEpTION 38 / dkpro-cassis 0.10.1':
            row['finding'] += ' ' + findings['G11']
            row['remaining'] = remaining['G11']
            add_evidence(row, evidence['G11'])
        elif row['package'] == 'Hypothesis/pytest':
            row['finding'] = findings['G20']
            add_evidence(row, evidence['G20'])
    reviewed_changes = {'src/legalmath/prospectus/successor/corrections.py',
                        'src/legalmath/prospectus/successor/closure_program.py'}
    for row in review['gaps'] + review['packages']:
        for item in row['evidence']:
            current = sha(ROOT / item['path'])
            if current != item['sha256']:
                if item['path'] not in reviewed_changes:
                    raise ValueError('Unreviewed evidence drift: ' + item['path'])
                item['sha256'] = current
    ledger['review_date'] = '2026-10-11'
    ledger['last_review'] = 'Real BES assisted source/correction consumer passes after local image-binding repair; raw OCR and automatic relationships remain incomplete. No fundamental package limitation or independent acceptance is established.'
    ledger['regression'] = {'path': str((PACKAGE / 'validation-001/coverage.json').relative_to(ROOT)),
        'passed': coverage['unique_tests'], 'execution': 'PARTITIONED_NODE_UNION',
        'method_unchanged': True, 'single_process_aggregate': False}
    ledger.setdefault('family_exposure', {})['Banco Espirito Santo series 23 final terms'] = 'DEVELOPMENT_EXPOSED; exclude related family from unseen cohort'
    ledger['real_scan'] = {'analysis': str((PACKAGE / 'analysis/attempt-001/result.json').relative_to(ROOT)),
        'consumer': str((PACKAGE / 'consumer/attempt-001/result.json').relative_to(ROOT)),
        'frozen_targets': 23, 'raw_page_exact': 14, 'supplied_region_exact': 16,
        'automatic_relationships': 0, 'supplied_relationships': 8, 'reviewed_replacements': 8,
        'actual_eligibility': 'NOT_ESTABLISHED', 'independent_acceptance': 'NOT_ESTABLISHED'}
    save(BASE / 'gap-status.json', ledger)
    save(BASE / 'attribution-review.json', review)
    save(BASE / 'final-attribution.json', report(ROOT))
    print(json.dumps({'status': 'UPDATED_REVIEWED_ATTRIBUTION', 'unique_tests': coverage['unique_tests']}))


if __name__ == '__main__':
    main()
