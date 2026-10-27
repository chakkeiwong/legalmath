"""Stage current dirty source bytes without touching the running worker."""
from pathlib import Path
import hashlib, json, shutil
ROOT = Path('/home/chakwong/python/legalmath')
WORK = ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
TREE = Path('/tmp/legalmath-product-closure-20261026')
assert not TREE.exists(), 'Do not replace candidate work'
TREE.mkdir()
for name in ('src', 'scripts', 'tests'):
    shutil.copytree(ROOT/name, TREE/name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for name in ('pyproject.toml', 'pytest.ini', 'conftest.py'):
    if (ROOT/name).is_file(): shutil.copyfile(ROOT/name, TREE/name)
path = TREE/'src/legalmath/canonical.py'
original = path.read_bytes()
text = original.decode().replace('import json\n', 'import json\nimport re\n')
text = text.replace('MAX_BYTES = 20 * 1024 * 1024', 'MAX_BYTES = 20 * 1024 * 1024\n_SURROGATE = re.compile("[\\ud800-\\udfff]")')
old = 'any(0xD800 <= ord(c) <= 0xDFFF for c in value)'
assert text.count(old) == 1
path.write_text(text.replace(old, '_SURROGATE.search(value) is not None'))
(WORK/'candidate-manifest.json').write_text(json.dumps(dict(tree=str(TREE),
    original_canonical_sha256=hashlib.sha256(original).hexdigest(),
    candidate_canonical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    current_dirty_sources=True, provider_calls=0), indent=2))
print(json.dumps(dict(staged=str(TREE), active_sources_changed=False)))
