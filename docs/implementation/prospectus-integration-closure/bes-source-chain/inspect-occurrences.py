"""Bounded preparation: inspect current raw occurrence identities without assessment."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import source_graph


def read(p):
    return json.loads(p.read_text())


def bundle():
    request = read(PACKAGE.parent / 'real-scan/consumer/attempt-001/request.json')
    inventory = read(PACKAGE / 'source-review-001/inventory.json')
    for n, row in enumerate(inventory[1:]):
        request['bundle']['documents'].append({
            'id': 'bes-base-2010' if n == 0 else 'bes-supplement-' + str(n),
            'path': row['path'], 'sha256': row['sha256'], 'page_count': row['pages'],
            'document_date': row['document_date'] + 'T00:00:00Z', 'known_from': row['known_from'],
            'language': 'en', 'authority': 'Retained programme source; authenticity not independently established'})
    return request['bundle']


def main():
    tick = time.monotonic()
    folder = PACKAGE / 'occurrences-001'
    if folder.exists():
        raise ValueError('Preserve prior occurrence inspection')
    folder.mkdir()
    graph = source_graph.build(bundle(), ROOT)
    chosen = []
    pages = {1, 37, 38, 40, 41, 76, 77, 78, 79, 80, 111, 112}
    for u in graph['units']:
        if u['document'] == 'bes-base-2010' and u['page'] not in pages:
            continue
        if u['document'] == 'bes-final-terms-2011' and u['page'] not in {1, 2, 3}:
            continue
        chosen.append(u)
    (folder / 'selected-units.json').write_text(json.dumps(chosen, ensure_ascii=False, indent=2) + '\n')
    (folder / 'lines.txt').write_text('\n'.join(u['id'] + ' ' + u['raw'] for u in chosen) + '\n')
    (folder / 'summary.json').write_text(json.dumps({'all_units': len(graph['units']),
        'selected_units': len(chosen), 'pages': sum(d['page_count'] for d in graph['documents']),
        'wall_seconds': time.monotonic() - tick, 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'scope': 'Preparation only; no consumer assessment or change to production code'}, indent=2) + '\n')
    print((folder / 'summary.json').read_text())


if __name__ == '__main__':
    main()
