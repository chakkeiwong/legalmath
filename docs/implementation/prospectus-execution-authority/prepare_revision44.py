"""Prepare a reviewed cumulative continuation; never edit the active program."""
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
assert old['revision'] == 43 and not state['running']
assert next(t for t in state['tasks'] if t['id'] == 'basf-meanings')['state'] == 'RESULT_RECORDED'
new = deepcopy(old)
new['revision'] = 44
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE / 'dossiers/basf-payment-terms.md').relative_to(ROOT))
task['reason'] = 'Complete23 connected original payment and tax readings with exact conditions and current consumers; preserve unknown actual events and historical law'
inputs = {task['dossier'], 'docs/plans/prospectus-basf-payment-terms-2026-10-14.md'}
previous = BASE / 'attempts/basf-meanings/attempt-009'
manifest = read(previous / 'outputs.json')
assert all(file_hash(previous / name) == expected for name, expected in manifest.items())
inputs.add(str((previous / 'outputs.json').relative_to(ROOT)))
inputs.update(str((previous / name).relative_to(ROOT)) for name in manifest)
images = BASE.parent / 'prospectus-basf-scope-repair/source-review-001'
inputs.update(str((images / f'base-{p}.png').relative_to(ROOT)) for p in (111,112,113,114,115,125,126))
inputs.update(str((images / f'final-{p}.png').relative_to(ROOT)) for p in (4,5))
task['inputs'] = sorted(set(task['inputs']) | inputs)
attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
assert len(attempts) == old['budgets']['basf-meanings']['maximum_new_attempts'] == 9
new['budgets']['basf-meanings']['maximum_new_attempts'] = 10
review = {
    'baseline': digest(old),
    'changes': '23 connected selected payment/tax source readings, same task, protected prior60 meanings and cumulative history',
    'skeptical_audit': 'PASS under docs/plans/prospectus-basf-payment-terms-2026-10-14.md; original pages inspected, corrected latest baseline, current consumers, explicit tax/deposit conditions and historical-law unknowns. Attempt009 repair-bound deviation retained; typed dispatch and production construction prevent the reproduced copied-runner defects.',
    'evidence_contract': '23 exact supplied readings in current P3/answer; protected60 meanings and Q4-Q6; current role-only baseline, deposit-discharge omission and adverse source/reference/event controls; original hashes and120s stages; at most one diagnosed repair and80MB evidence.',
    'scope_unchanged': True, 'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'basf-meanings', 'previous_maximum': 9, 'new_maximum': 10,
        'retained_attempts': attempts,
        'reason': 'Connected selected interest/payment/tax provisions remain unknown; original source evidence supports23 discriminating readings. This is untouched substantive scope, not a retry of failed unchanged harness stages.',
        'next_discriminating_check': 'Exact current answer preserves each payment/tax condition and all prior meanings; omitted deposit-discharge restores unknown; no actual payment, tax or discharge inferred.',
        'stop_condition': 'Source/method corruption, missing conditions/diagnostics, changed prior meaning, stage over120seconds, evidence above80MB, or second harness failure; at most one bounded changed repair, earlier deviation preserved.',
        'same_scope_authorization': 'Continuous authorized original prospectus execution, unchanged obligations and all cumulative attempts; local source analysis only, no external permission or human acceptance inferred.'}}
a.validate_program(new)
write(BASE / 'proposals/0044.json', new, exclusive=True)
write(BASE / 'reviews/0044.json', review, exclusive=True)
print(json.dumps({'revision': 44, 'retained_admissions': len(attempts), 'maximum': 10}))
