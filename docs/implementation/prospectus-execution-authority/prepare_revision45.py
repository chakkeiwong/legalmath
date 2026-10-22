"""Review a cumulative source continuation, preserving all original attempts."""
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
assert old['revision'] == 44 and not state['running']
assert next(t for t in state['tasks'] if t['id'] == 'basf-meanings')['state'] == 'RESULT_RECORDED'
new = deepcopy(old)
new['revision'] = 45
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE / 'dossiers/basf-governance-terms.md').relative_to(ROOT))
task['reason'] = 'Complete20 connected substitution, collective-action and language readings, including exact previously reviewed notice order; preserve unknown law and actual events'
inputs = {task['dossier'], 'docs/plans/prospectus-basf-governance-terms-2026-10-14.md'}
for rel in ('basf-meanings/attempt-010', 'law-applicability/attempt-006'):
    folder = BASE / 'attempts' / rel
    manifest = read(folder / 'outputs.json')
    assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
    inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
    inputs.update(str((folder / name).relative_to(ROOT)) for name in manifest)
images = BASE.parent / 'prospectus-basf-scope-repair/source-review-001'
inputs.update(str((images / f'base-{p}.png').relative_to(ROOT)) for p in (128,129,130,132,133))
task['inputs'] = sorted(set(task['inputs']) | inputs)
attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
assert len(attempts) == old['budgets']['basf-meanings']['maximum_new_attempts'] == 10
new['budgets']['basf-meanings']['maximum_new_attempts'] = 11
review = {
    'baseline':digest(old), 'changes':'20 connected governance readings with exact original and reviewed notice spans; same basf-meanings obligations and cumulative history',
    'skeptical_audit':'PASS under docs/plans/prospectus-basf-governance-terms-2026-10-14.md. Original images and law006 source packet checked. Preserve all substitution prerequisites, majority denominator, unequal-treatment consent and proof alternatives. Existing ambiguity and independent acceptance remain open.',
    'evidence_contract':'20 exact current P3/answer readings, protected83 prior meanings/Q4-Q6, exact notice character conservation, role-only baseline, omitted unequal-treatment safeguard and adverse controls; current methods,120s/80MB bounds.',
    'scope_unchanged':True, 'budget_unchanged':False,
    'budget_revision':{
        'budget_key':'basf-meanings','previous_maximum':10,'new_maximum':11,'retained_attempts':attempts,
        'reason':'Current185 pending selected units contain connected substitution and collective-action text. Original images and already reviewed conditional-source mapping support20 further discriminating readings without resolving disputed default(f) or inventing events.',
        'next_discriminating_check':'Current answer preserves exact original prerequisites,83 earlier meanings and Q4-Q6; original notice spans survive reviewed reorder; omitted unequal-treatment rule restores unknown.',
        'stop_condition':'Corrupt/unverifiable evidence, missing prerequisite, unintended prior-answer change, stage above120s, evidence above80MB, or second harness failure; at most one diagnosed changed repair. All prior deviations retained.',
        'same_scope_authorization':'Continuous authorized original prospectus source program, unchanged obligations and all ten admissions; no external permission or human acceptance inferred.'}}
a.validate_program(new)
write(BASE / 'proposals/0045.json',new,exclusive=True)
write(BASE / 'reviews/0045.json',review,exclusive=True)
print(json.dumps({'revision':45,'retained_admissions':len(attempts),'maximum':11}))
