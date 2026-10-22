"""Prepare, do not activate, the reviewed finite-engineering continuation."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, read, write, file_hash

a = Authority(ROOT)
old, _, _ = a.spec()
assert old['revision'] == 3
state = a.status()
assert not state['running'] and not any(r['state'] == 'ADMITTED' for r in state['tasks'])
new = deepcopy(old)
new['revision'] = 4
review_path = HERE / 'FINITE-ACCEPTANCE-REVIEW.md'
plan_path = ROOT / 'docs/plans/prospectus-authority-acceptance-2026-10-13.md'
tests = [ROOT / 'tests/prospectus/test_execution_authority.py', ROOT / 'tests/prospectus/test_execution_acceptance.py',
         HERE / 'finite-acceptance-defensive-tests.xml']
for task in new['tasks']:
    if task['id'] == 'recovery':
        task['priority'] = 1
        folder = HERE / 'attempts/recovery/attempt-001'
        evidence = read(folder / 'outputs.json')
        started = read(folder / 'started.json')
        paths = [str((folder / p).relative_to(ROOT)) for p in evidence]
        paths += [str((folder / 'outputs.json').relative_to(ROOT)),
                  *started['sources'], *started['methods'], str(review_path.relative_to(ROOT))]
        task['inputs'] = sorted(set(task['inputs'] + paths))
        task['validator'] = 'recovery-sequence.v1'
        task['evidence_attempt'] = str(folder.relative_to(ROOT))
        task['dossier'] = str((HERE / 'dossiers/recovery-continuation.md').relative_to(ROOT))
        task['reason'] = 'Validate actual retained eight-state multilingual/correction recovery; preserve broader native and legal requirements'
    elif task['id'] == 'authority-acceptance':
        task['priority'] = 2
        task['validator'] = 'authority-audit.v1'
        task['depends_on'] = ['recovery']
        task['dossier'] = str((HERE / 'dossiers/authority-acceptance-continuation.md').relative_to(ROOT))
        task['reason'] = 'Verify actual finite-recovery acceptance and current complete mapping before continuing substantive repair'
        paths = [review_path, plan_path, *tests, ROOT / 'src/legalmath/prospectus/successor/closure_program.py']
        task['inputs'] = sorted(set(task['inputs'] + [str(p.relative_to(ROOT)) for p in paths]))
proposal = HERE / 'proposals/0004.json'
review = HERE / 'reviews/0004.json'
write(proposal, new, exclusive=True)
write(review, {'baseline': digest(old), 'changes': 'Named finite engineering validators and same-task recovery/authority continuation',
    'skeptical_audit': 'Specific complete products, adverse controls, actual transitions and bound identities; arbitrary PASS and human substitution rejected',
    'evidence_contract': 'Accept only the original finite engineering task requirements; preserve other source/automatic/human/package obligations and all budgets',
    'scope_unchanged': True, 'budget_unchanged': True,
    'review_note': str(review_path.relative_to(ROOT)), 'review_note_sha256': file_hash(review_path),
    'tests': {str(p.relative_to(ROOT)): file_hash(p) for p in tests},
    'remaining': 'Substantive relation/financial/source repairs, native prerequisites and actual external inputs remain'}, exclusive=True)
print(json.dumps({'proposal': str(proposal.relative_to(ROOT)), 'review': str(review.relative_to(ROOT)),
                  'task_count': len(new['tasks']), 'obligations': len(new['obligations']), 'budgets_unchanged': new['budgets'] == old['budgets']}))
