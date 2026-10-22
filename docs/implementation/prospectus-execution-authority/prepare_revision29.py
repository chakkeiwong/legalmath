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
assert old['revision'] == 28 and not state['running']
rows = {t['id']: t for t in state['tasks']}
assert rows['source-bes-dep-05']['state'] == rows['page-coverage']['state'] == 'RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-05'] == 1
assert old['budgets']['source-bes-dep-05']['maximum_new_attempts'] == 2
new = deepcopy(old)
new['revision'] = 29
task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-05')
task['dossier'] = str((BASE / 'dossiers/interim-review-repair.md').relative_to(ROOT))
task['reason'] = 'Repair the retained false statutory-audit classification of the actual moderate-assurance interim review; preserve original source scope and independence requirements'
inputs = {task['dossier'], 'docs/plans/prospectus-interim-review-repair-2026-10-13.md'}
folder = BASE / 'attempts/source-bes-dep-05/attempt-001'
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / n) == h for n,h in manifest.items())
inputs.update(str((folder / n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
task['inputs'] = sorted(set(task['inputs']) | inputs)
review = {'baseline': digest(old), 'changes': ['Continue BES-DEP-05 with a reproduced source-classification repair'],
    'skeptical_audit': 'PASS: exact source structure and coverage, original false-answer comparator, no moderate/limited normalization or generic semantics claim; unrelated profiles and instrument questions protected',
    'evidence_contract': 'Reproduce wrong audit and rejected correct review; current source/report/final consumers preserve correct moderate interim review, reject false codes and omitted qualifications; no source or independent acceptance inferred',
    'scope_unchanged': True, 'budget_unchanged': True}
authority.validate_program(new)
write(BASE / 'proposals/0029.json', new, exclusive=True)
write(BASE / 'reviews/0029.json', review, exclusive=True)
print(json.dumps({'revision':29,'task':'source-bes-dep-05','admission':'second original; maximum unchanged'}))
