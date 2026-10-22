"""Unchanged complete CLI answer plus installed downstream receipt controls."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

root, prep, here, mode = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed' if mode == 'installed' else root / 'src'))
from legalmath.cli import main
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

def read(path): return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())
def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + chr(10)).encode()
    with path.open('xb') as stream: stream.write(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)

started = time.monotonic(); config = read(prep / 'config.json')
manifest = root / config['profiles']; temporary = here / (mode + '-answer.json'); assert not temporary.exists()
for path, checksum in config['receipts'].items(): assert hashlib.sha256((root / path).read_bytes()).hexdigest() == checksum
sys.argv = ['legalmath', 'prospectus', 'consume', '--products', str(root / config['products']),
    '--repository', str(root), '--output', str(temporary), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main(); answer = read(temporary); baseline = read(root / config['baseline'])
assert answer == baseline, 'Complete valid answer changed'
assert answer['report_sha256'] == digest({k: v for k, v in answer.items() if k != 'report_sha256'})
if mode == 'installed': assert answer == read(here / 'ordinary-answer.json.gz')

controls = here / (mode + '-synthetic'); controls.mkdir()
source = controls / 'source.txt'; source.write_text('The Notes pay interest.')
receipt = controls / 'receipt.json'; receipt.write_text(json.dumps({'source': 'SYNTHETIC'}))
raw = receipt.read_bytes(); at = '2026-01-01T00:00:00Z'
request = {'version': 'prospectus-successor.v3', 'bundle': {'instrument_id': 'synthetic-receipt-integrity',
    'purpose': 'review', 'issue_date': at, 'effective_at': at, 'known_at': at, 'documents': [
        {'id': 'd', 'path': 'source.txt', 'sha256': digest(source.read_bytes()), 'format': 'text',
         'language': 'en', 'authority': 'Synthetic control', 'document_date': at, 'known_from': at,
         'acquisition': {'path': 'receipt.json', 'sha256': digest(raw)}}], 'dependencies': []}}
p1 = service.source_product(request, controls); p2 = service.construction_product(p1, controls)
p3 = service.interpretation_product(p1, p2)
products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
good = service.consume(products, controls); refusals = []
for mutation in ('changed', 'missing'):
    if mutation == 'changed': receipt.write_text('Changed synthetic receipt')
    else: receipt.unlink()
    for boundary, call in [('construction', lambda: service.construction_product(p1, controls)),
                           ('frozen', lambda: service.consume(products, controls)),
                           ('current', lambda: service.consume(products, controls, mode='current'))]:
        try: call()
        except (ValueError, FileNotFoundError) as error: refusals.append({'mutation': mutation, 'boundary': boundary, 'reason': str(error)})
        else: raise AssertionError('Stale receipt accepted: ' + boundary)
    receipt.write_bytes(raw); assert service.consume(products, controls) == good
imports = {n: m.__file__ for n, m in sys.modules.items() if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
origin = (here / 'installed' if mode == 'installed' else root / 'src').resolve()
assert all(Path(p).resolve().is_relative_to(origin) for p in imports.values())
save(here / (mode + '-imports.json'), imports); save(here / (mode + '-answer.json.gz'), answer)
temporary.unlink()  # Only this worker's fully preserved temporary serialization.
result = {'status': 'PASS', 'actual_cli': True, 'complete_baseline_equal': True,
    'complete_installed_equal': mode == 'installed', 'original_receipts_checked': len(config['receipts']),
    'refusals': refusals, 'restored_complete_synthetic_answer_equal': True,
    'module_origins_checked': len(imports), 'wall_seconds': time.monotonic() - started,
    'cpu_gpu': 'CPU;GPU intentionally hidden', 'source_authenticity_established': False}
save(here / (mode + '-verification.json'), result)
print(json.dumps({'status': 'PASS', 'mode': mode, 'complete_baseline_equal': True, 'refusals': len(refusals), 'imports': len(imports)}))
