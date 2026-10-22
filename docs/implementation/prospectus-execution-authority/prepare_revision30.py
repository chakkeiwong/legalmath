from copy import deepcopy
from pathlib import Path
import json
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

authority = Authority(ROOT)
old, _, _ = authority.spec()
state = authority.status()
assert old['revision'] == 29 and not state['running']
rows = {t['id']: t for t in state['tasks']}
assert rows['native-binding']['state'] == rows['source-bes-dep-05']['state'] == 'RESULT_RECORDED'
assert state['budget_admissions']['native-binding'] == 1
assert old['budgets']['native-binding']['maximum_new_attempts'] == 2
new = deepcopy(old)
new['revision'] = 30
task = next(t for t in new['tasks'] if t['id'] == 'native-binding')
task['dossier'] = str((BASE / 'dossiers/native-trace-accounting.md').relative_to(ROOT))
task['reason'] = 'Explain the retained descriptor-path and readlink-error omissions without granting native closure or reuse'
inputs = {task['dossier'], 'docs/plans/prospectus-native-trace-accounting-2026-10-13.md'}
folder = BASE / 'attempts/native-binding/attempt-001'
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / n) == h for n,h in manifest.items())
inputs.update(str((folder / n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
task['inputs'] = sorted(set(task['inputs']) | inputs)
review = {'baseline': digest(old), 'changes': ['Continue native-binding with the observed finite trace-parser gap'],
    'skeptical_audit': 'PASS: actual sealed trace and first-quote parser comparator; exact line preservation, error/descriptor semantics, unresolved forms and unchanged native reuse veto; no new OCR or legal progress claim',
    'evidence_contract': 'All retained lines accounted once, baseline observations preserved,86 omissions explained, adversarial grammar remains explicit, installed CLI consumes the actual trace with hash refusal; no immutable closure or confinement inference',
    'scope_unchanged': True, 'budget_unchanged': True}
authority.validate_program(new)
write(BASE / 'proposals/0030.json', new, exclusive=True)
write(BASE / 'reviews/0030.json', review, exclusive=True)
print(json.dumps({'revision':30,'task':'native-binding','admission':'second original; maximum unchanged'}))
