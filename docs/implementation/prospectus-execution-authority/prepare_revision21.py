"""Review an explicit cumulative extension after the retained final-case timeout."""
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
assert old['revision'] == 20 and not state['running']
rows = {r['id']: r for r in state['tasks']}
assert rows['basf-meanings']['state'] == 'REPAIR_REQUIRED'
assert all(rows[k]['state'] == 'COMPLETE' for k in ('recovery', 'authority-acceptance'))
folder = BASE / 'attempts/basf-meanings/attempt-003'
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
assert read(folder/'result.json')['status'] == 'FAIL'
assert read(folder/'timeout.json')['exit_code'] == 124
new = deepcopy(old)
new['revision'] = 21
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE/'dossiers/basf-omission-staging.md').relative_to(ROOT))
task['reason'] = 'Complete the original missing-makewhole case through bound production-component stages after proving exact open-case equivalence; preserve the original timeout'
names = {task['dossier'], 'docs/plans/prospectus-basf-omission-staging-2026-10-13.md',
         str((folder/'outputs.json').relative_to(ROOT))}
names.update(str((folder/name).relative_to(ROOT)) for name in manifest)
for name in ('base-126.png', 'base-127.png', 'final-7.png'):
    names.add('docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name)
task['inputs'] = sorted(set(task['inputs']) | names)
attempts = [e['attempt'] for e in authority.events()
            if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
assert len(attempts) == old['budgets']['basf-meanings']['maximum_new_attempts'] == 3
new['budgets']['basf-meanings']['maximum_new_attempts'] = 4
review = {
    'baseline': digest(old),
    'changes': 'Same original meanings task: retain incomplete attempt003 and split unchanged production operations to complete the missing required make-whole omission evidence',
    'skeptical_audit': 'The original admission already used its one import repair, so no second repair is hidden inside it. Full retained-open P3 equality and argument-mutation controls must validate the partition before omission execution. Exact inputs, production methods,120s bounds and all admission/failure history remain. No internal timing or platform-disconnection cause is invented.',
    'evidence_contract': 'Exact staged-open P3 equality; actual withheld-definition consumer with explicit unresolved target in every relevant question; all previous meanings, sources, construction, governing dependencies, incorporation and Q4-Q6 preserved. Q1/Q2 UNKNOWN and Q3 PARTIAL. Timings and counts are explanatory only; no legal acceptance or performance ranking.',
    'scope_unchanged': True,
    'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'basf-meanings', 'previous_maximum': 3, 'new_maximum': 4,
        'retained_attempts': attempts,
        'reason': 'Six cases passed but the final interpretation command timed out without a result. Inspected code exposes a concrete partition into existing returned clause/dependency structures and remaining service operations; exact successful baseline evidence can test it before the failed case continues.',
        'next_discriminating_check': 'Require full staged-open P3 equality to the successful monolithic P3 and exact argument-rejection guards before running the omitted target through the real final consumer.',
        'stop_condition': 'Source/method drift, changed arguments, staged-baseline inequality, wrong omitted-target effects, missing diagnostics, command over120s or physical evidence over60MB. No unchanged retry or production repair in this admission; all original failures and limits retained.',
        'same_scope_authorization': 'Standing request for thorough continuous execution of the original prospectus program, retaining original task identity, obligations and all cumulative admissions. No new network, external message, installation, publication or permission change.'
    }
}
authority.validate_program(new)
write(BASE/'proposals/0021.json', new, exclusive=True)
write(BASE/'reviews/0021.json', review, exclusive=True)
print(json.dumps({'revision': 21, 'task': 'basf-meanings', 'maximum': 4,
                  'retained_attempts': len(attempts), 'new_bound_paths': len(names)}))
