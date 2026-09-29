"""Render the changed teaching section and process chart for visual inspection."""
import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
state = json.loads((OUT/'state.json').read_text())
receipt = state['phases']['verify'][-1]
manifest_path = ROOT/receipt['path']
if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != receipt['sha256']:
    raise RuntimeError('Changed verification receipt')
manifest = json.loads(manifest_path.read_text())
if manifest['status'] != 'PASSED': raise RuntimeError('Verification did not pass')
pdf = manifest_path.parent/'documents/monograph.pdf'
doc = fitz.open(pdf)
entries = doc.get_toc()
entry = next(i for i, row in enumerate(entries) if row[1].endswith('Checking executable quotations and calendar comparisons'))
level, title, first = entries[entry]
last = next(row[2]-1 for row in entries[entry+1:] if row[0] <= level)
pages = set(range(first-1, last))
for i, page in enumerate(doc):
    if 'Check program references and dates independently' in ' '.join(page.get_text().split()):
        pages.add(i)
destination = OUT/('rendered-'+manifest_path.parent.name); destination.mkdir(exist_ok=False)
rows = []
for i in sorted(pages):
    path = destination/f'page-{i+1:03d}.png'
    doc[i].get_pixmap(matrix=fitz.Matrix(1.4, 1.4)).save(path)
    rows.append({'page': i+1, 'image': str(path.relative_to(ROOT)),
                 'text': doc[i].get_text(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
record = {'pdf': str(pdf.relative_to(ROOT)), 'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
          'page_count': len(doc), 'pages': rows, 'status': 'RENDERED_PENDING_INSPECTION'}
(OUT/'rendered-selection.json').write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
print(json.dumps({'page_count': len(doc), 'selected_pages': [r['page'] for r in rows]}, indent=2))
