"""Prepare a reviewed refinement with explicit cumulative budget accounting."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

authority = Authority(ROOT)
old, _, _ = authority.spec()
assert old['revision'] == 83
new = deepcopy(old)
new['revision'] = 84
task = next(t for t in new['tasks'] if t['id'] == 'native-layout-cases')
plan = 'docs/plans/prospectus-bidi-consumer-2026-10-15.md'
dossier = 'docs/implementation/prospectus-execution-authority/dossiers/bidi-consumer.md'
base = 'docs/implementation/prospectus-execution-authority'
source = base + '/attempts/native-layout-cases/attempt-002'
snapshot = base + '/attempts/native-binding/attempt-008/snapshot'
task['dossier'] = dossier
task['reason'] = 'Use new genuine Arabic/Latin original in actual native source and full downstream consumers; diagnose geometric order and repair only with explicit source occurrence accounting.'
task['inputs'] = sorted(set(task['inputs']) | {plan, dossier, source + '/outputs.json',
    source + '/result.json', source + '/IMAGE-REVIEW.md', source + '/CONSUMER-MATRIX.md',
    snapshot + '/manifest.json'} | {source + '/' + name for name in read(ROOT / source / 'outputs.json')}
    | {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath/prospectus/successor').glob('*.py')})
new['budgets']['native-layout-cases']['maximum_new_attempts'] = 3
routes = read(ROOT / old['continuation_review']['routes'])
route = next(r for r in routes['tasks'] if r['task'] == task['id'])
route.update(task_sha256=digest(task), mode='mixed',
    remaining='Actual mixed-script consumer evaluation and exact independent readings; true vertical original still missing.',
    next_action='Execute the reviewed actual mixed-script consumer package; retain geometric-order or upstream extraction failures and all source identities.',
    stop_condition='Two native reservations or local repair bound exhausted; retain failure and continue independent work. Independent readings veto broader acceptance.')
route_name = base + '/closure-routes-2026-10-15-bidi-consumer.json'
write(ROOT / route_name, routes, exclusive=True)
new['continuation_review']['routes'] = route_name
new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name] = file_hash(ROOT / route_name)
attempts = [e['attempt'] for e in authority.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
review = {
    'baseline': digest(old), 'changes': [task['reason'], 'Cumulative native-layout allowance 2 to 3; no source-acquisition extension'],
    'skeptical_audit': 'PASS: inspected current native and projection code; bind new original, use exact visible URL controls, preserve full answers and unreviewed language uncertainty. See plan audit and assumptions.',
    'evidence_contract': plan, 'scope_unchanged': True, 'budget_unchanged': False,
    'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 2, 'new_maximum': 3,
        'retained_attempts': attempts, 'reason': 'Newly acquired original supplies missing script family and discriminates current geometric source projection; prior source packages remain partial.',
        'next_discriminating_check': 'Actual Poppler source-to-answer on the Riyad original with literal URL and ordered occurrence controls against retained native observations.',
        'stop_condition': 'Two native starts maximum, 120 seconds per stage, 300 MiB evidence, one local repair; no automatic retry or additional HTTP.',
        'same_scope_authorization': 'User continues the repaired master program and explicitly requests corner-case downloads, complete integration repairs and continuous independent execution.'},
}
write(ROOT / base / 'proposals/bidi-consumer-84.json', new, exclusive=True)
write(ROOT / base / 'proposals/bidi-consumer-84-review.json', review, exclusive=True)
print({'revision': new['revision'], 'task': task['id'], 'retained_admissions': len(attempts), 'maximum': 3})
