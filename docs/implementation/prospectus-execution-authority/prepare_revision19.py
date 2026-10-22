"""Preserve cumulative authority audit history and bind its current inputs."""
from copy import deepcopy
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, CODE, digest, file_hash, read, write

authority = Authority(ROOT)
old, tasks, _ = authority.spec()
state = authority.status()
assert old['revision'] == 18 and not state['running']
rows = {r['id']: r for r in state['tasks']}
recovery = BASE / 'attempts/recovery/attempt-006'
assert rows['recovery']['state'] == 'COMPLETE'
assert rows['recovery']['attempt'] == str(recovery.relative_to(ROOT))
assert all(rows[key]['state'] == 'COMPLETE' for key in ('native-cohort', 'native-interfaces'))
prior = read(BASE / 'attempts/authority-acceptance/attempt-002/admission.json')
checked = [*CODE, 'tests/prospectus/test_execution_acceptance.py',
           'tests/prospectus/test_execution_authority.py',
           str((BASE / 'finite-acceptance-defensive-tests.xml').relative_to(ROOT))]
assert all(file_hash(ROOT / name) == prior['binding'][name] for name in checked)
new = deepcopy(old)
new['revision'] = 19
task = next(t for t in new['tasks'] if t['id'] == 'authority-acceptance')
assert task['validator'] == 'authority-audit.v1'
task['dossier'] = str((BASE / 'dossiers/post-occurrence-authority-audit.md').relative_to(ROOT))
task['reason'] = 'Check current recovery acceptance, all original mappings and retained evidence, then continue the reviewed substantive source analysis'
manifest = read(recovery / 'outputs.json')
assert all(file_hash(recovery / name) == expected for name, expected in manifest.items())
task['inputs'] = sorted(set(task['inputs']) | set(checked) | {
    str((recovery / name).relative_to(ROOT)) for name in manifest
} | {str((recovery / 'outputs.json').relative_to(ROOT)), task['dossier'],
     'docs/plans/prospectus-post-occurrence-acceptance-2026-10-13.md',
     'scripts/prospectus_verify_task.py',
     str((BASE / 'attempts/basf-margins/attempt-002/RESULT.md').relative_to(ROOT)),
     str((BASE / 'attempts/basf-margins/attempt-002/outputs.json').relative_to(ROOT))})
attempts = [e['attempt'] for e in authority.events()
            if e['kind'] == 'ADMIT' and e.get('budget_key') == 'authority-acceptance']
assert len(attempts) == old['budgets']['authority-acceptance']['maximum_new_attempts'] == 2
new['budgets']['authority-acceptance']['maximum_new_attempts'] = 3
review = {
    'baseline': digest(old),
    'changes': 'One cumulative original authority audit after accepted current recovery; preserve unchanged validator, every obligation and all prior results',
    'skeptical_audit': 'Use current revision-18 evidence instead of stale original revision-3 baseline. Current native cohort/interfaces remain accepted under unchanged actual inputs. The retained defensive report and all its authority/test method hashes match attempt-002; no fresh-test claim. No result counts establish legal progress.',
    'evidence_contract': 'Actual recovery ACCEPT, all original mappings, intact retained evidence, complete cumulative budgets, required regression selection and incomplete delivery streams. Changed evidence, scope loss, false completion or reset limits veto acceptance. Finite process verification only.',
    'scope_unchanged': True,
    'budget_unchanged': False,
    'unchanged_defensive_test_inputs': {name: file_hash(ROOT / name) for name in checked},
    'budget_revision': {
        'budget_key': 'authority-acceptance', 'previous_maximum': 2, 'new_maximum': 3,
        'retained_attempts': attempts,
        'reason': 'The original audit predates current recovery and substantive scope evidence; the previously reviewed consolidated revalidation plan requires a final current audit.',
        'next_discriminating_check': 'Unchanged authority-audit.v1 recomputes actual mapping, states, accepted recovery and evidence integrity before recording the finite acceptance.',
        'stop_condition': 'Changed bound methods/evidence, scope loss, false completion, malformed transition or timeout. Diagnose before another attempt; no unchanged retry or automatic budget extension.',
        'same_scope_authorization': 'User standing instruction to refresh, review and execute the original prospectus program continuously; same original task and full cumulative history, no external action.'
    }
}
authority.validate_program(new)
write(BASE / 'proposals/0019.json', new, exclusive=True)
write(BASE / 'reviews/0019.json', review, exclusive=True)
print(json.dumps({'revision': 19, 'task': 'authority-acceptance', 'maximum': 3,
                  'retained_attempts': len(attempts), 'unchanged_defensive_inputs': len(checked)}))
