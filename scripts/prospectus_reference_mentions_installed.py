"""Execute the actual discovery CLI with isolated imports from the new wheel."""
import hashlib
import json
import os
from pathlib import Path
import sys

root, here, prep = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed'))
from legalmath.cli import main

sys.argv = ['legalmath', 'prospectus', 'discover-references', '--request', str(prep / 'request.json'),
            '--output', str(here / 'installed-report.json')]
main()
ordinary = json.loads((here / 'ordinary-report.json').read_text())
installed = json.loads((here / 'installed-report.json').read_text())
assert ordinary == installed, 'Complete installed/ordinary discovery mismatch'
imports = {n: m.__file__ for n, m in sys.modules.items() if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert 'legalmath.prospectus.successor.reference_mentions' in imports
assert all(Path(p).resolve().is_relative_to((here / 'installed').resolve()) for p in imports.values())
for name, value in [('installed-imports.json', imports), ('installed-result.json', {
    'status': 'PASS', 'actual_cli': True, 'complete_report_equal': True, 'installed_imports': len(imports),
    'installed_report_sha256': hashlib.sha256((here / 'installed-report.json').read_bytes()).hexdigest()})]:
    with (here / name).open('x') as output:
        json.dump(value, output, indent=2)
print('PASS isolated installed reference discovery')
