"""Continue original BASF meanings against the latest sealed source baseline."""
from copy import deepcopy
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

authority = Authority(ROOT)
old, tasks, _ = authority.spec()
state = authority.status()
assert old['revision'] == 19 and not state['running']
rows = {r['id']: r for r in state['tasks']}
assert all(rows[k]['state'] == 'COMPLETE' for k in ('recovery', 'authority-acceptance'))
assert rows['basf-meanings']['state'] == 'RESULT_RECORDED'
new = deepcopy(old)
new['revision'] = 20
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE / 'dossiers/basf-remaining-redemption.md').relative_to(ROOT))
task['reason'] = 'Continue the source-complete early-call, residual-call and make-whole reading now that exact selected scopes and current recovery are retained'
names = {task['dossier'], 'docs/plans/prospectus-basf-remaining-redemption-2026-10-13.md'}
for relative in ('basf-margins/attempt-002', 'basf-references/attempt-002'):
    folder = BASE / 'attempts' / relative
    manifest = read(folder / 'outputs.json')
    assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
    names.update(str((folder / name).relative_to(ROOT)) for name in manifest)
    names.add(str((folder / 'outputs.json').relative_to(ROOT)))
for name in ('base-120.png', 'base-121.png', 'base-122.png', 'base-123.png',
             'final-5.png', 'final-6.png', 'final-7.png'):
    names.add('docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name)
task['inputs'] = sorted(set(task['inputs']) | names)
attempts = [e['attempt'] for e in authority.events()
            if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
assert len(attempts) == old['budgets']['basf-meanings']['maximum_new_attempts'] == 2
new['budgets']['basf-meanings']['maximum_new_attempts'] = 3
review = {
    'baseline': digest(old),
    'changes': 'One complete same-task source-reading continuation for selected section 5(5), 5(8) and 5(10)(b), using latest occurrence-bound margin and nominal-definition products',
    'skeptical_audit': 'Earlier meanings alone is the wrong baseline. Use current margin v3; preserve every previous known meaning and all outside unknown spans. Separate purchase permission from forced repayment, require actual global-note reduction as well as 75% acquisition, and distinguish resolved source-use rows from meaning completeness. All finite authority/recovery checks passed; no production default or package change is proposed.',
    'evidence_contract': 'Exact original source/maps and prior semantics, actual conditional route effects, complete amount-definition chain, scoped adverse/omission controls, independently formulated Boolean expectations, and unchanged Q4-Q6 with overall Q1/Q2 UNKNOWN and Q3 PARTIAL. Counts are explanatory; no actual payment, numerical valuation or independent legal acceptance.',
    'scope_unchanged': True,
    'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'basf-meanings', 'previous_maximum': 2, 'new_maximum': 3,
        'retained_attempts': attempts,
        'reason': 'The intervening margin continuation established exact complete selected source extents and occurrence-safe use. The next unsupplied meanings are local and inspectable; missing client facts do not block conditional source analysis.',
        'next_discriminating_check': 'Actual matched consumers must distinguish purchase, residual call and early call, retain every restriction and follow the exact amount definition while preserving the latest baseline.',
        'stop_condition': 'Source/method drift, lost outside spans or earlier meanings, incorrect route activation, unknown scope silently closed, timeout or storage failure. At most one diagnosed bounded repair in this admission; no unchanged retry or automatic further extension.',
        'same_scope_authorization': 'Standing request to thoroughly repair and execute the prospectus program continuously. Original meanings task, cumulative history and unresolved obligations retained; local source analysis only.'
    }
}
authority.validate_program(new)
write(BASE / 'proposals/0020.json', new, exclusive=True)
write(BASE / 'reviews/0020.json', review, exclusive=True)
print(json.dumps({'revision': 20, 'task': 'basf-meanings', 'maximum': 3,
                  'retained_attempts': len(attempts), 'new_bound_source_paths': len(names)}))
