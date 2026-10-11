"""Retain exact source identities, selected text and original PDF review images."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent
BASE = PACKAGE.parent
DATES = ['2011-07-14', '2010-11-03', '2010-11-15', '2011-03-03',
         '2011-04-19', '2011-06-06', '2011-06-17', '2011-07-13']
BASE_PAGES = [1, 37, 38, 40, 41, 76, 77, 78, 79, 80, 110, 111, 112]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main():
    import fitz
    if fitz.__version__ != '1.27.2.2' or len(sys.argv) != 1:
        raise ValueError('Reviewed renderer/invocation changed')
    folder = PACKAGE / 'source-review-001'
    if folder.exists():
        raise ValueError('Preserve existing source review')
    folder.mkdir(parents=True)
    sources = json.loads((BASE / 'scan-documentation/source-availability.json').read_text())['files']
    inventory = []
    for n, (source, date) in enumerate(zip(sources, DATES, strict=True)):
        pdf = ROOT / source['path']
        if sha(pdf) != source['sha256']:
            raise ValueError('Original PDF changed: ' + source['id'])
        record = {**source, 'document_date': date,
                  'role': 'final_terms' if n == 0 else 'base_prospectus' if n == 1 else 'supplement',
                  'known_from': '2026-10-04T00:00:00Z',
                  'chronology': 'dated before the 15 July 2011 issue; authenticity and actual delivery not established'}
        record.pop('consumer_scope')
        if n == 0:
            record['image_review'] = 'See protected real-scan/oracle.json and SOURCE-REVIEW.md'
            inventory.append(record)
            continue
        text_file = pdf.parent / 'pages.json'
        retained = json.loads(text_file.read_text())['pages']
        pages = BASE_PAGES if n == 1 else list(range(1, source['pages'] + 1))
        selected = [p for p in retained if p['page'] in pages]
        if [p['page'] for p in selected] != pages:
            raise ValueError('Retained text page identity differs')
        save(folder / (source['id'] + '-text.json'), selected)
        record['retained_text'] = {'path': str(text_file.relative_to(ROOT)), 'sha256': sha(text_file)}
        record['review_pages'] = pages
        record['images'] = []
        with fitz.open(pdf) as doc:
            if len(doc) != source['pages']:
                raise ValueError('Page count differs')
            for page in pages:
                image_path = folder / (source['id'] + '-p' + str(page) + '.png')
                pix = doc[page - 1].get_pixmap(dpi=110, alpha=False)
                pix.save(image_path)
                record['images'].append({'page': page, 'file': image_path.name,
                                         'sha256': sha(image_path), 'width': pix.width, 'height': pix.height})
        inventory.append(record)
    save(folder / 'inventory.json', inventory)
    save(folder / 'run.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': ['timeout', '60', '/home/chakwong/miniconda3/envs/tfgpu/bin/python',
                    str(Path(__file__).relative_to(ROOT))],
        'environment': {'python': sys.executable, 'PyMuPDF': fitz.__version__, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU; GPU intentionally hidden; no device query', 'seeds': 'N/A deterministic rendering',
        'date': datetime.now(timezone.utc).isoformat(),
        'plan': 'docs/plans/prospectus-bes-source-chain-2026-10-11.md',
        'script_sha256': sha(Path(__file__)), 'source_count': len(inventory),
        'scope': 'Source preparation only; selected images require actual visual inspection'} )
    payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
    if payload > 20_000_000:
        raise ValueError('Reviewed source-evidence cap exceeded')
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir() if p.is_file()}})
    print(json.dumps({'source_count': len(inventory), 'images': sum(len(r.get('images', [])) for r in inventory),
                      'payload_bytes': payload, 'directory': str(folder.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
