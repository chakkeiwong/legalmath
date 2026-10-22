"""Run the whole ordinary consumer with isolated installed imports."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

root, here, prep = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here/'installed'))
from legalmath.cli import main
from legalmath.prospectus.successor.contracts import digest

manifest = prep/'profiles.json'
sys.argv = ['legalmath', 'prospectus', 'consume', '--products',
    str(root/'docs/implementation/prospectus-execution-authority/reviews/conditional-cli-311/products.json'),
    '--repository', str(root), '--output', str(here/'installed-answer.json'), '--mode', 'frozen',
    '--conditional-profiles', str(manifest.relative_to(root)),
    '--conditional-profiles-sha256', hashlib.sha256(manifest.read_bytes()).hexdigest()]
main()
actual = json.loads((here/'installed-answer.json').read_text())
ordinary = json.loads(gzip.decompress((here/'ordinary-answer.json.gz').read_bytes()))
assert actual == ordinary, 'Complete installed/ordinary mismatch'
imports = {name: module.__file__ for name, module in sys.modules.items()
    if (name == 'legalmath' or name.startswith('legalmath.')) and getattr(module, '__file__', None)}
assert 'legalmath.prospectus.successor.bgb_onward' in imports
assert all(Path(p).resolve().is_relative_to((here/'installed').resolve()) for p in imports.values())
for name, value in [('installed-imports.json', imports), ('installed-result.json', {
    'status': 'PASS', 'complete_answer_equal': True, 'actual_cli': True,
    'answer_sha256': digest(actual), 'installed_imports': len(imports),
    'cpu_gpu': 'CPU;GPU intentionally hidden'})]:
    with (here/name).open('x') as stream:
        json.dump(value, stream, indent=2)
print('PASS complete installed BGB onward consumer')
