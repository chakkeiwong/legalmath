"""Bind sealed current recovery evidence without changing its acceptance rule."""
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
assert old['revision'] == 17 and not state['running']
row = next(r for r in state['tasks'] if r['id'] == 'recovery')
folder = BASE / 'attempts/recovery/attempt-005'
assert row['state'] == 'RESULT_RECORDED' and row['attempt'] == str(folder.relative_to(ROOT))
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
assert read(folder / 'comparison.json')['status'] == 'PASS'
started = read(folder / 'started.json')
assert all(file_hash(ROOT / name) == expected
           for name, expected in {**started['methods'], **started['sources']}.items())

new = deepcopy(old)
new['revision'] = 18
task = next(t for t in new['tasks'] if t['id'] == 'recovery')
task['validator'] = 'recovery-sequence.v1'
task['evidence_attempt'] = str(folder.relative_to(ROOT))
task['dossier'] = str((BASE / 'dossiers/occurrence-recovery-acceptance.md').relative_to(ROOT))
task['reason'] = 'Verify the freshly sealed original eight-state evidence under current governing-occurrence methods, then continue the authority audit and substantive work'
task['inputs'] = sorted(set(task['inputs']) | {
    str((folder / name).relative_to(ROOT)) for name in manifest
} | {str((folder / 'outputs.json').relative_to(ROOT)), task['dossier'],
     'docs/plans/prospectus-post-occurrence-acceptance-2026-10-13.md',
     'scripts/prospectus_verify_task.py', *started['methods'], *started['sources']})
attempts = [e['attempt'] for e in authority.events()
            if e['kind'] == 'ADMIT' and e.get('budget_key') == 'recovery']
assert len(attempts) == old['budgets']['recovery']['maximum_new_attempts'] == 5
new['budgets']['recovery']['maximum_new_attempts'] = 6
review = {
    'baseline': digest(old),
    'changes': 'Bind every sealed attempt-005 file and current source/method; restore unchanged named recovery acceptance under the same task',
    'skeptical_audit': 'Actual evidence exists and its hashes are intact. Separate pre-admission binding avoids circular production/acceptance. The eight states and original comparator are unchanged. Preserve all historical attempts and broader unresolved obligations.',
    'evidence_contract': 'Exact actual/clean products and restorations, original Portuguese units/images, three specific rejections, 44 focused checks and current source/method identity; mismatch vetoes acceptance. Finite same-host consistency only, with shared-code limitations.',
    'scope_unchanged': True,
    'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'recovery', 'previous_maximum': 5, 'new_maximum': 6,
        'retained_attempts': attempts,
        'reason': 'Fresh original-scope evidence must be separately bound before the unchanged validator can accept it, as planned before its production.',
        'next_discriminating_check': 'recovery-sequence.v1 consumes every bound current evidence file and the authority independently recomputes it before recording ACCEPT.',
        'stop_condition': 'Missing/changed evidence, unequal products, absent specific rejection, method drift or timeout; no unchanged retry or further extension implied.',
        'same_scope_authorization': 'Standing user request to review and continue authorized prospectus work across checkpoints; original task, evidence and cumulative history retained, with no new external permission.'
    }
}
authority.validate_program(new)
write(BASE / 'proposals/0018.json', new, exclusive=True)
write(BASE / 'reviews/0018.json', review, exclusive=True)
print(json.dumps({'revision': 18, 'task': 'recovery', 'maximum': 6,
                  'retained_attempts': len(attempts), 'evidence_files': len(manifest)}))
