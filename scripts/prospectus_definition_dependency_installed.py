"""Fresh isolated CLI execution using only the installed legalmath package."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

root, here, prep = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed'))
from legalmath.cli import main
from legalmath.prospectus.successor.contracts import digest

manifest = prep / 'profiles.json'
sys.argv = ['legalmath', 'prospectus', 'consume', '--products',
    str(root / 'docs/implementation/prospectus-execution-authority/reviews/conditional-cli-311/products.json'),
    '--repository', str(root), '--output', str(here / 'installed-answer.json'), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main()
actual = json.loads((here / 'installed-answer.json').read_text())
expected = json.loads(gzip.decompress((here / 'ordinary-answer.json.gz').read_bytes()))
assert actual == expected, 'Installed answer differs from complete source answer'
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert 'legalmath.prospectus.successor.definition_dependencies' in imports
assert all(Path(p).resolve().is_relative_to((here / 'installed').resolve()) for p in imports.values())
for name, data in [('installed-imports.json', imports), ('installed-result.json', {
        'status': 'PASS', 'actual_cli': True, 'complete_answer_equal': True,
        'answer_sha256': digest(actual), 'installed_imports': len(imports),
        'cpu_gpu': 'CPU; GPU intentionally hidden'})]:
    with (here / name).open('x') as stream:
        json.dump(data, stream, indent=2)
print('PASS installed source-reviewed definition dependencies')
