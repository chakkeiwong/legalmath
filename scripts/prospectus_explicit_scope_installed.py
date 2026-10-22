"""Actual scope and whole-answer CLI use from the newly installed wheel."""
from copy import deepcopy
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
from legalmath.prospectus.successor.definition_scope_evidence import check_rules

request = json.loads((prep / 'request.json').read_text())
adverse = deepcopy(request['rules'])
adverse[3]['extents'] = [[34003, 34124]]
try:
    check_rules(request['text'], request['source_pieces'], adverse)
except ValueError as error:
    assert 'conflicts with printed self-section' in str(error)
else:
    raise AssertionError('Installed guard accepted conflicting extent')
sys.argv = ['legalmath', 'prospectus', 'discover-definition-scope', '--request',
            str(here / 'source-request.json'), '--output', str(here / 'installed-scope.json')]
main()
assert json.loads((here / 'installed-scope.json').read_text()) == json.loads((here / 'ordinary-scope.json').read_text())
bindings = json.loads((prep / 'source-freeze.json').read_text())
profiles = root / bindings['profiles']
sys.argv = ['legalmath', 'prospectus', 'consume', '--products', str(root / bindings['products']),
            '--repository', str(root), '--output', str(here / 'installed-answer.json'), '--mode', 'frozen',
            '--conditional-profiles', str(profiles.relative_to(root)),
            '--conditional-profiles-sha256', hashlib.sha256(profiles.read_bytes()).hexdigest()]
main()
actual = json.loads((here / 'installed-answer.json').read_text())
ordinary = json.loads(gzip.decompress((here / 'ordinary-answer.json.gz').read_bytes()))
assert actual == ordinary, 'Complete installed/ordinary answer differs'
imports = {n: m.__file__ for n, m in sys.modules.items()
           if (n == 'legalmath' or n.startswith('legalmath.')) and getattr(m, '__file__', None)}
assert 'legalmath.prospectus.successor.definition_scope_evidence' in imports
assert all(Path(p).resolve().is_relative_to((here / 'installed').resolve()) for p in imports.values())
for name, value in [('installed-imports.json', imports), ('installed-result.json', {
    'status': 'PASS', 'actual_cli': True, 'complete_scope_report_equal': True,
    'complete_answer_equal': True, 'conflicting_extent_refused': True,
    'answer_sha256': digest(actual), 'installed_imports': len(imports),
    'legal_scope_established': False, 'whole_task_complete': False})]:
    with (here / name).open('x') as stream:
        json.dump(value, stream, indent=2)
print('PASS installed scope, conflicting extent refusal and complete consumer')
