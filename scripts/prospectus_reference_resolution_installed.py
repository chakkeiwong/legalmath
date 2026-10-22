"""Exercise both actual CLIs using only the newly installed wheel."""
import json
import os
from pathlib import Path
import sys

root, here, prep = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed'))
from legalmath.cli import main

for command, name, extra in [
    ('resolve-references', 'report', []),
    ('reconcile-references', 'graph', ['--resolution', str(here / 'installed-report.json'),
                                     '--reviewed-graph', str(prep / 'reviewed-graph.json')])]:
    sys.argv = ['legalmath', 'prospectus', command, '--request', str(prep / 'request.json'),
                '--output', str(here / ('installed-' + name + '.json')), *extra]
    main()
    assert json.loads((here / ('ordinary-' + name + '.json')).read_text()) == json.loads(
        (here / ('installed-' + name + '.json')).read_text()), 'Complete installed report differs'
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert 'legalmath.prospectus.successor.reference_resolution' in imports
assert all(Path(p).resolve().is_relative_to((here / 'installed').resolve()) for p in imports.values())
for name, value in [('installed-imports.json', imports), ('installed-result.json', {
    'status': 'PASS', 'actual_cli': True, 'complete_resolution_equal': True,
    'complete_reconciliation_equal': True, 'installed_imports': len(imports)})]:
    with (here / name).open('x') as output:
        json.dump(value, output, indent=2)
print('PASS isolated installed resolution and reconciliation')
