"""Review the next original BASF margin admission without resetting history."""
from copy import deepcopy
from pathlib import Path
import json
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

a = Authority(ROOT)
old, _, _ = a.spec()
state = a.status()
assert old['revision'] == 45 and not state['running']
assert next(t for t in state['tasks'] if t['id'] == 'basf-margins')['state'] == 'RESULT_RECORDED'
new = deepcopy(old)
new['revision'] = 46
task = next(t for t in new['tasks'] if t['id'] == 'basf-margins')
task['dossier'] = str((BASE / 'dossiers/basf-remaining-margins.md').relative_to(ROOT))
task['reason'] = ('Review remaining BASF printed bars and exact selected uses against current attempt011; '
                  'repair the page112–113 reference-period selection only if the full source supports it')
inputs = {task['dossier'], 'docs/plans/prospectus-basf-remaining-margins-2026-10-14.md'}
for rel in ('basf-margins/attempt-001', 'basf-margins/attempt-002',
            'basf-meanings/attempt-011'):
    folder = BASE / 'attempts' / rel
    manifest = read(folder / 'outputs.json')
    assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
    inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
    if rel == 'basf-margins/attempt-002':
        names = ('cumulative-margin-ledger.json', 'v3/scope-review.json', 'RESULT.md')
    elif rel == 'basf-meanings/attempt-011':
        names = ('common.json.gz', 'original-graph.json.gz', 'candidate-P3.json.gz',
                 'candidate-answer.json.gz', 'current-methods.json')
    else:
        names = ('scope-review.json', 'margin-ledger.json', 'RESULT.md')
    assert all(name in manifest for name in names)
    inputs.update(str((folder / name).relative_to(ROOT)) for name in names)
images = BASE.parent / 'prospectus-basf-scope-repair/source-review-001'
for page in list(range(108, 116)) + list(range(124, 134)):
    inputs.add(str((images / f'base-{page}.png').relative_to(ROOT)))
for page in (3, 5, 7):
    inputs.add(str((images / f'final-{page}.png').relative_to(ROOT)))
task['inputs'] = sorted(set(task['inputs']) | inputs)
attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT'
            and e.get('budget_key') == 'basf-margins']
assert len(attempts) == old['budgets']['basf-margins']['maximum_new_attempts'] == 2
new['budgets']['basf-margins']['maximum_new_attempts'] = 3
review = {
    'baseline': digest(old),
    'changes': 'Same original BASF margin task, remaining printed groups and a source-justified correction trigger; retain all two earlier admissions and immutable results',
    'skeptical_audit': 'PASS under docs/plans/prospectus-basf-remaining-margins-2026-10-14.md. Current attempt011 is comparator; old margin evidence is lineage. Original images and final terms expose a possible page112–113 selection error; no prior meaning is protected from an evidenced correction. Exact-use v2 and current consumers are mandatory.',
    'evidence_contract': 'Account for every remaining original occurrence; full source-reviewed raw/selected bar extents; actual current P3/answer and omission controls; Q4–Q6 equality and explicit reference-period correction if confirmed; 120s stages,80MB evidence, one diagnosed changed repair.',
    'scope_unchanged': True, 'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'basf-margins', 'previous_maximum': 2, 'new_maximum': 3,
        'retained_attempts': attempts,
        'reason': '373 original margin inventory occurrences remain unreviewed after eleven bars. Original pp108–115 and124–133 plus final terms permit a connected complete-scope review; the current reference-period use has a source-specific correction trigger. This is untouched original scope, not an unchanged retry.',
        'next_discriminating_check': 'Complete printed bar endpoints, exact selected uses and real answer effects; adjudicate p112–113 continuation and preserve all valid prior meanings.',
        'stop_condition': 'Corrupt source/evidence, unresolved printed boundary, unintended answer change, missing diagnostic, >120s stage, >80MB evidence, or second harness failure; at most one diagnosed changed repair.',
        'same_scope_authorization': 'Original authorized prospectus program, unchanged obligations, cumulative attempts and no external or independent-review permission.'}}
a.validate_program(new)
write(BASE / 'proposals/0046.json', new, exclusive=True)
write(BASE / 'reviews/0046.json', review, exclusive=True)
print(json.dumps({'revision': 46, 'retained_admissions': len(attempts), 'maximum': 3}))
