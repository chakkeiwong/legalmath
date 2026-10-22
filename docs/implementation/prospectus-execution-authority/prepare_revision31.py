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
assert old['revision'] == 30 and not state['running']
rows = {t['id']: t for t in state['tasks']}
assert rows['native-binding']['state'] == rows['source-bes-dep-01']['state'] == 'RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-01'] == 1
assert old['budgets']['source-bes-dep-01']['maximum_new_attempts'] == 2
new = deepcopy(old)
new['revision'] = 31
task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-01')
task['dossier'] = str((BASE / 'dossiers/bes-statement-scope.md').relative_to(ROOT))
task['reason'] = 'Repair the retained one-of304 statement-target acceptance through existing reference routes, retaining exact source qualifications and unresolved original obligations'
inputs = {task['dossier'], 'docs/plans/prospectus-bes-statement-scope-2026-10-13.md'}
folder = BASE / 'attempts/source-bes-dep-01/attempt-001'
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / n) == h for n,h in manifest.items())
inputs.update(str((folder / n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
task['inputs'] = sorted(set(task['inputs']) | inputs)
review = {'baseline': digest(old), 'changes': ['Repair the reproduced source-specific incomplete statement target admission'],
    'skeptical_audit': 'PASS: exact original edition and full page readings pinned before edit; old routes guarded without opt-in bypass; full selected occurrence and source restriction preserved; no legal closure',
    'evidence_contract': 'Reproduce one-of304 acceptance then refuse it; preserve complete original edge, unrelated references, original dependencies and current diagnostic questions; reject target/source/availability/coverage corruption',
    'scope_unchanged': True, 'budget_unchanged': True}
authority.validate_program(new)
write(BASE / 'proposals/0031.json', new, exclusive=True)
write(BASE / 'reviews/0031.json', review, exclusive=True)
print(json.dumps({'revision':31,'task':'source-bes-dep-01','admission':'second original; maximum unchanged'}))
