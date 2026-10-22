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
assert old['revision'] == 27 and not state['running']
rows = {t['id']: t for t in state['tasks']}
assert rows['page-coverage']['state'] == 'RESULT_RECORDED'
assert rows['reasoning-corpus']['state'] == 'RESULT_RECORDED'
assert state['budget_admissions']['page-coverage'] == 1
assert old['budgets']['page-coverage']['maximum_new_attempts'] == 2
new = deepcopy(old)
new['revision'] = 28
task = next(t for t in new['tasks'] if t['id'] == 'page-coverage')
task['dossier'] = str((BASE / 'dossiers/retained-layout-coverage.md').relative_to(ROOT))
task['reason'] = 'Inspect still-unexamined retained originals for missing layout families; preserve current native prerequisite and independent-review boundaries'
inputs = {task['dossier'], 'docs/plans/prospectus-retained-layout-coverage-2026-10-13.md'}
for identity in ('page-coverage/attempt-001', 'native-layout-cases/attempt-001', 'reasoning-corpus/attempt-002'):
    folder = BASE / 'attempts' / identity
    manifest = read(folder / 'outputs.json')
    assert all(file_hash(folder / n) == h for n, h in manifest.items())
    inputs.update(str((folder / n).relative_to(ROOT)) for n in ('RESULT.md', 'outputs.json', 'result.json'))
task['inputs'] = sorted(set(task['inputs']) | inputs)
review = {'baseline': digest(old), 'changes': ['Continue original page-coverage task with a changed, bounded original-source inventory'],
    'skeptical_audit': 'PASS: root/byte/page caps and omitted files explicit; nomination metrics cannot establish layout semantics; original images precede actual consumers; current native predecessor not bypassed',
    'evidence_contract': 'Frozen exact-source inventory, bounded metadata nominations, original-image review, matched source/layout consumers and adverse controls if genuinely new families occur; negative results retain acquisition needs, not universal absence',
    'scope_unchanged': True, 'budget_unchanged': True}
authority.validate_program(new)
write(BASE / 'proposals/0028.json', new, exclusive=True)
write(BASE / 'reviews/0028.json', review, exclusive=True)
print(json.dumps({'revision': 28, 'task': 'page-coverage', 'admissions': '1 of 2 used; unchanged maximum'}))
