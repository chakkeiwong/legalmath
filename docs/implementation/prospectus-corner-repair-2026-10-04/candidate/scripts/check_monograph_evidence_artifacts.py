"""Validate retained review evidence without creating semantic judgments."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/monograph/review/revision'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors, message):
    errors.append(message)


def main():
    errors = []
    rendered = json.loads((REVIEW / 'rendered-review.json').read_text())
    pdf = ROOT / rendered['pdf']
    if not pdf.exists() or digest(pdf) != rendered['pdf_sha256']:
        fail(errors, 'Rendered-review PDF hash does not match the current PDF')
    pages = rendered.get('pages', [])
    if len(pages) != 282:
        fail(errors, f'Expected 282 rendered page records, found {len(pages)}')
    for page in pages:
        path = ROOT / page['image']
        if not path.exists() or digest(path) != page['sha256']:
            fail(errors, f"Rendered page hash mismatch: {page.get('pdf_page')}")
    if rendered.get('blocking_render_findings'):
        fail(errors, 'Rendered review contains blocking findings')

    currentness = json.loads((REVIEW / 'regulator-currentness.json').read_text())
    if not currentness.get('scope_limit') or not currentness.get('results'):
        fail(errors, 'Official-currentness scope or result record is missing')
    for result in currentness.get('results', []):
        path_text = result.get('fresh')
        if not path_text:
            continue
        path = ROOT / path_text
        expected = result.get('fresh_sha256')
        if not path.exists() or (expected and digest(path) != expected):
            fail(errors, f"Official-currentness hash mismatch: {result.get('reference')}")
    index = currentness.get('index', {})
    if index.get('complete') is not False:
        fail(errors, 'Official-currentness index must retain its incomplete-scope flag')

    updates = json.loads((REVIEW / 'source-update-check.json').read_text())
    if not updates.get('limitation') or not updates.get('records'):
        fail(errors, 'Publisher-currentness limitation or records are missing')
    allowed = {'metadata_captured_not_exhaustive_retraction_search', 'no_registered_doi_in_manifest'}
    for record in updates['records']:
        if record.get('status') not in allowed:
            fail(errors, f"Publisher-currentness record is unresolved: {record.get('key')}")
        path_text = record.get('path')
        if path_text:
            path = ROOT / path_text
            if not path.exists() or (record.get('sha256') and digest(path) != record['sha256']):
                fail(errors, f"Publisher-currentness hash mismatch: {record.get('key')}")

    teaching = json.loads((REVIEW / 'concept-teaching-map.json').read_text())
    if len(teaching) != 200:
        fail(errors, f'Expected 200 teaching records, found {len(teaching)}')
    for record in teaching:
        path = ROOT / record['file']
        if not path.exists() or digest(path) != record['sha256']:
            fail(errors, f"Teaching-unit hash mismatch: {record.get('unit')}")
        if record.get('review_status') != 'rendered_author_review_complete_target_reader_acceptance_pending':
            fail(errors, f"Teaching-unit review status is not explicit: {record.get('unit')}")

    guards = json.loads((REVIEW / 'program-guard-diagnostics.json').read_text())
    if guards.get('status') != 'PASS':
        fail(errors, 'Program guard diagnostics did not pass')
    result = {'status': 'PASS' if not errors else 'FAIL', 'errors': errors,
              'limits': 'Checks identity and completeness of retained evidence; it does not validate legal entailment, human comprehension or production readiness.'}
    (REVIEW / 'evidence-artifact-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
