"""Full ordinary or isolated installed CLI with independent qualification checks."""
from copy import deepcopy
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
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.issuer_qualification import KEY
from legalmath.prospectus.successor.issuer_qualification_verify import verify_answer

def read(path): return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())
def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    with path.open('xb') as stream: stream.write(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)

started = time.monotonic(); request = read(prep / 'reproduction.json')
manifest = prep / 'profiles.json'; temporary = here / (mode + '-answer.json'); assert not temporary.exists()
sys.argv = ['legalmath', 'prospectus', 'consume', '--products', str(root / request['products']),
    '--repository', str(root), '--output', str(temporary), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main(); answer = read(temporary); ordinary = read(root / request['baseline']); profile = read(prep / 'profile.json')
check = verify_answer(answer, ordinary, profile, expected_profile_sha256=digest(profile))
expected = read(prep / 'expected.json')['qualification']
for row in answer[KEY]['scenarios']: assert row['qualification_result']['status'] == expected[row['id']]
if mode == 'installed': assert answer == read(here / 'ordinary-answer.json.gz')
controls = []
for kind in ('qualification', 'downstream', 'scope', 'ordinary'):
    changed = deepcopy(answer)
    row = next(s for s in changed[KEY]['scenarios'] if s['id'] == 'german-excluded')
    if kind == 'qualification': row['qualification_result']['status'] = 'YES'
    elif kind == 'downstream': row['publication_decisions']['conditional_contract_readings']['broad_replacement'] = 'YES'
    elif kind == 'scope': changed[KEY]['actual_issuer_qualification_established'] = True
    else: changed['may_execute_transaction'] = True
    changed['report_sha256'] = digest({k: v for k, v in changed.items() if k != 'report_sha256'})
    try: verify_answer(changed, ordinary, profile, expected_profile_sha256=digest(profile))
    except ValueError as error: controls.append({'kind': kind, 'reason': str(error)})
    else: raise AssertionError('Rehashed corrupt answer accepted')
imports = {n: m.__file__ for n, m in sys.modules.items() if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
origin = (here / 'installed' if mode == 'installed' else root / 'src').resolve()
assert all(Path(p).resolve().is_relative_to(origin) for p in imports.values())
save(here / (mode + '-imports.json'), imports); save(here / (mode + '-answer.json.gz'), answer)
temporary.unlink()  # Only this worker's fully preserved serialization.
save(here / (mode + '-verification.json'), {**check, 'actual_cli': True, 'corruption_controls': controls,
    'complete_installed_equal': mode == 'installed', 'module_origins_checked': len(imports),
    'wall_seconds': time.monotonic() - started, 'cpu_gpu': 'CPU;GPU intentionally hidden'})
print(json.dumps({'status': 'PASS', 'mode': mode, **check, 'imports': len(imports)}))
