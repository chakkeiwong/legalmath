"""Reproduce the existing evidence reader's behavior; this is not a classifier."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

import fitz

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = ROOT / 'docs/prospectus/bank-senior-controls'
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from legalmath.prospectus.evidence import investigate


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main():
    started = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()
    catalog = json.loads((ARCHIVE / 'sources.json').read_text())
    manifest_path = ARCHIVE / 'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    previous_hashes = {r['id']: r['source_sha256'] for r in previous['documents']} if previous else {}
    code_paths = [ROOT / 'src/legalmath/prospectus' / f for f in ('evidence.py', 'semantics.py', 'common.py')]
    code_hashes = {str(p.relative_to(ROOT)): digest(p) for p in code_paths}
    documents = []
    texts = {}
    for row in catalog['sources']:
        original = ARCHIVE / 'originals' / (row['id'] + '.pdf')
        source_hash = digest(original)
        if row['id'] in previous_hashes and previous_hashes[row['id']] != source_hash:
            raise ValueError('Preserved source changed: ' + row['id'])
        with fitz.open(original) as pdf:
            pages = [{'page': i + 1, 'text': page.get_text()} for i, page in enumerate(pdf)]
        if not pages or not any(p['text'].strip() for p in pages):
            raise ValueError('No extractable text: ' + row['id'])
        document = {'source_sha256': source_hash, 'preliminary_indicator': row['preliminary_indicator'],
                    'pages': pages, 'extractor': 'PyMuPDF ' + fitz.VersionBind}
        text_path = ARCHIVE / 'text' / (row['id'] + '.json')
        write(text_path, document)
        documents.append({**row, 'source_sha256': source_hash, 'bytes': original.stat().st_size,
                          'pages': len(pages), 'empty_text_pages': [p['page'] for p in pages if not p['text'].strip()],
                          'original': str(original.relative_to(ARCHIVE)),
                          'text': str(text_path.relative_to(ARCHIVE)), 'text_sha256': digest(text_path)})
        texts[row['id']] = document
    write(manifest_path, {'created_utc': previous['created_utc'] if previous else timestamp,
                         'sources_sha256': digest(ARCHIVE / 'sources.json'), 'documents': documents,
                         'pdf_count': len(documents), 'pages': sum(d['pages'] for d in documents),
                         'meaning_verified': False, 'human_quality_evidence': False})
    rows = [r for r in catalog['sources'] if r['diagnostic_included']]
    summary = investigate(rows, OUTPUT / 'existing-reader', root=ARCHIVE)
    reports = json.loads((OUTPUT / 'existing-reader/instruments.json').read_text())
    quotations = json.loads((OUTPUT / 'existing-reader/quotations.json').read_text())
    diagnostics = []
    for row in rows:
        claims = [c for c in quotations if c['document'] == row['id']]
        report = next((r for r in reports if r['document'] == row['id']), None)
        # Deliberately naive keyword comparator: descriptive only; no accuracy score.
        keyword_pages = [p['page'] for p in texts[row['id']]['pages'] if re.search(
            r'write[ -]?down|written[ -]?down|bail.in|convert|loss.absorb', p['text'], re.I)]
        diagnostics.append({'document': row['id'], 'role': row['role'],
                            'retrieved_fields': dict(Counter(c['field'] for c in claims)),
                            'retrieved_claims_after_page_8': sum(c['page'] > 8 for c in claims),
                            'existing_classification': report['classification'] if report else None,
                            'candidate_facts': report['candidate_facts'] if report else None,
                            'naive_keyword_hit_pages': keyword_pages,
                            'requested_binary_label_available': bool(report and 'loss_absorption' in report)})
    for path in code_paths:
        if digest(path) != code_hashes[str(path.relative_to(ROOT))]:
            raise ValueError('Implementation changed during diagnostic: ' + str(path))
    write(OUTPUT / 'diagnostic.json', {'existing_reader_summary': summary, 'documents': diagnostics,
          'description_counts': dict(Counter(r['classification'] for r in reports)),
          'requested_binary_classifier': 'NOT_IMPLEMENTED',
          'scope': 'Existing retrieval/description interface only. No legal-accuracy or generalization result.',
          'human_quality_evidence': False, 'model_calls': 0})
    artifacts = [manifest_path, OUTPUT / 'diagnostic.json'] + sorted((OUTPUT / 'existing-reader').glob('*.json'))
    write(OUTPUT / 'run-manifest.json', {
        'started_utc': timestamp, 'wall_seconds': round(time.monotonic() - started, 3),
        'command': 'python3 ' + str(Path(__file__).resolve().relative_to(ROOT)),
        'python': sys.executable, 'python_version': platform.python_version(), 'pymupdf': fitz.VersionBind,
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'git_worktree': 'dirty; concurrent unrelated work retained; exact reader source hashes below',
        'cpu_gpu': 'CPU PDF text and Python logic only; no GPU framework imported or initialized',
        'seeds': 'N/A: deterministic text retrieval', 'data_version': digest(manifest_path),
        'plan': 'docs/plans/bank-senior-prospectus-check.md',
        'plan_sha256': digest(ROOT / 'docs/plans/bank-senior-prospectus-check.md'),
        'result': str((OUTPUT / 'diagnostic.json').relative_to(ROOT)),
        'driver_sha256': digest(Path(__file__)), 'implementation_sha256': code_hashes,
        'artifacts_sha256': {str(p.relative_to(ROOT)): digest(p) for p in artifacts}})
    print(json.dumps({'preserved_pdfs': len(documents), 'preserved_pages': sum(d['pages'] for d in documents),
                      'reader': summary, 'binary_classifier': 'NOT_IMPLEMENTED'}))


if __name__ == '__main__':
    main()
