"""One bounded navigation index of retained annual note headings; no interpretation."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import signal
import time

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
SOURCE = AUTH / 'attempts/source-bes-dep-09'
OUT = AUTH / 'reviews/annual-note-roadmap-439'
PLAN = 'docs/plans/prospectus-annual-notes-roadmap-2026-10-22.md'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Three-second note-index ceiling')))
    signal.alarm(3)
    assert not OUT.exists(), 'No repeated index'
    post = read(AUTH / 'reviews/english-applicability-439/post-record.json')
    prior_seconds = post['costs']['cumulative_charged_seconds']
    assert prior_seconds + 3 < 1960, 'Original source09time ceiling'
    p1 = SOURCE / 'attempt-002/original-P1.json.gz'
    ref = read(SOURCE / 'attempt-003/candidate-P1-reference.json.gz')
    assert ROOT / ref['original_P1'] == p1 and sha(p1) == ref['file_sha256']
    graph = read(p1)['payload']['graph']
    required = {92, 94, 96, 190, 191} | set(range(97, 188))
    units = [u for u in graph['units'] if u['document'] == 'bes-2010-en']
    assert len({u['page'] for u in units}) == 256 and required <= {u['page'] for u in units}
    headings = []
    for u in units:
        if 97 <= u['page'] <= 187:
            match = re.match(r'^NOTE\s+(\d+)\s*[–—-]\s*(.+)', u['raw'])
            if match:
                headings.append({'number': int(match[1]), 'title': match[2], 'page': u['page'],
                    'unit': u['id'], 'quote': u['raw'], 'source_sha256': u['source_sha256']})
    headings.sort(key=lambda r: (r['page'], r['number'], r['unit']))
    basis = [u for u in units if u['page'] == 103]
    links = [{'unit': u['id'], 'quote': u['raw'],
              'note_numbers': [int(n) for n in re.findall(r'\bNote\s+(\d+)\b', u['raw'])]}
             for u in basis if re.search(r'\bNote\s+\d+\b', u['raw'])]
    coverage = read(ROOT / '.localresources/prospectus-preparation/annual-scope-review-recovery/coverage.json')
    assert coverage['required_pages'] == sorted(required)
    result = {'status': 'INDEXED', 'interpretation_complete': False, 'headings': headings,
        'distinct_notes_found': sorted({r['number'] for r in headings}),
        'heading_count': len(headings), 'basis_cross_references': links,
        'required_pages': sorted(required), 'uninterpreted_required_pages': coverage['uninterpreted_required_pages'],
        'basis_reading_qualification': 'Printed order retained; continuation paragraphs after footer need substantive review',
        'source': {'path': str(p1.relative_to(ROOT)), 'sha256': sha(p1)},
        'plan': PLAN, 'plan_sha256': sha(ROOT / PLAN),
        'method_sha256': sha(Path(__file__)), 'command': '.venv/bin/python -B -m scripts.prospectus_annual_note_index',
        'prior_cumulative_charged_seconds': prior_seconds, 'seconds': time.monotonic() - start}
    data = json.dumps(result, ensure_ascii=False, indent=2).encode()
    assert len(data) < 1024**2 and prior_seconds + result['seconds'] < 1960
    OUT.mkdir()
    with (OUT / 'index.json').open('xb') as stream:
        stream.write(data)
    signal.alarm(0)
    print(json.dumps({'status': 'INDEXED', 'headings': len(headings),
                      'notes': result['distinct_notes_found'], 'seconds': result['seconds']}))


if __name__ == '__main__':
    main()
