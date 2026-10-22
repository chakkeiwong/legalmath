"""Exercise both declaration commands using the fresh isolated wheel."""
import json
import os
from pathlib import Path
import sys

root, here, prep = map(Path, sys.argv[1:4])
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path.insert(0, str(here / 'installed'))
from legalmath.cli import main

for command, name, extra in [
    ('discover-definition-declarations', 'report', []),
    ('reconcile-definition-declarations', 'reconciliation', ['--discovery', str(here / 'installed-report.json'),
                                                           '--lineage', str(prep / 'lineage.json')])]:
    sys.argv = ['legalmath', 'prospectus', command, '--request', str(prep / 'request.json'),
                '--output', str(here / ('installed-' + name + '.json')), *extra]
    main()
    assert json.loads((here / ('ordinary-' + name + '.json')).read_text()) == json.loads(
        (here / ('installed-' + name + '.json')).read_text()), 'Complete installed report differs'
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert 'legalmath.prospectus.successor.definition_declarations' in imports
assert all(Path(p).resolve().is_relative_to((here / 'installed').resolve()) for p in imports.values())
for name, value in [('installed-imports.json', imports), ('installed-result.json', {
    'status': 'PASS', 'actual_cli': True, 'complete_discovery_equal': True,
    'complete_reconciliation_equal': True, 'installed_imports': len(imports)})]:
    with (here / name).open('x') as output:
        json.dump(value, output, indent=2)
print('PASS isolated installed declaration discovery and reconciliation')
