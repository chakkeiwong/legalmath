"""Review one cumulative admission for the previously explicit arithmetic gap."""
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
assert old['revision'] == 38 and not state['running']
assert next(t for t in state['tasks'] if t['id'] == 'law-applicability')['state'] == 'RESULT_RECORDED'
new = deepcopy(old)
new['revision'] = 39
task = next(t for t in new['tasks'] if t['id'] == 'law-applicability')
task['dossier'] = str((BASE / 'dossiers/voting-arithmetic.md').relative_to(ROOT))
task['reason'] = 'Compute source-bound declared majority/quorum thresholds from eligible totals while retaining unknown legal eligibility and actual-effectiveness limits'
inputs = {task['dossier'], 'docs/plans/prospectus-voting-arithmetic-2026-10-13.md'}
for number in (2, 4):
    folder = BASE / f'attempts/law-applicability/attempt-{number:03}'
    manifest = read(folder / 'outputs.json')
    assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
    inputs.add(str((folder / 'outputs.json').relative_to(ROOT)))
    inputs.update(str((folder / name).relative_to(ROOT)) for name in manifest)
task['inputs'] = sorted(set(task['inputs']) | inputs)
attempts = [e['attempt'] for e in authority.events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'law-applicability']
assert len(attempts) == old['budgets']['law-applicability']['maximum_new_attempts'] == 4
new['budgets']['law-applicability']['maximum_new_attempts'] = 5
review = {
    'baseline': digest(old),
    'changes': 'Optional exact declared ratio facts in real P4/current consumers; retain the original twelve-family conditional source model and all prior evidence',
    'skeptical_audit': 'PASS under the detailed source/assumption/evidence audit in the plan. Prior threshold hypotheses are not a Boolean implementation bug. Supplied eligible denominators and legal rule readings remain conditional. Missing/conflicting/temporal/identity controls and exact legacy answer comparison required; no arithmetic implies effective amendment.',
    'evidence_contract': 'Actual current consumer must distinguish exact and below thresholds, simple-majority tie, missing/future/conflicting tallies, and refuse mixed identity/unit, malformed values and Boolean overrides. Retain computations in final Q4; preserve legacy Q1-Q6 and measure9 statutory-contract distinction. No historical law or independent acceptance conclusion.',
    'scope_unchanged': True,
    'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'law-applicability', 'previous_maximum': 4, 'new_maximum': 5,
        'retained_attempts': attempts,
        'reason': 'Attempt002 explicitly identified an unimplemented numerical threshold module. Its completed necessary-condition model supplies exact source anchors and a matched current-consumer comparator; no further source acquisition is needed for conditional arithmetic.',
        'next_discriminating_check': 'Retain current legacy answers and numeric-input rejection, then compute exact vote/quorum conditions in matched actual current consumers while independently withholding eligibility evidence.',
        'stop_condition': 'Source/method corruption, missing diagnostics, any stage beyond120seconds or new evidence above30MB; one diagnosed bounded repair and no unchanged retry.',
        'same_scope_authorization': 'Standing request for continuous reviewed execution of the original prospectus program; same original law task and all cumulative admissions retained. No new network, installation, host policy, external message or publication.'
    }
}
authority.validate_program(new)
write(BASE / 'proposals/0039.json', new, exclusive=True)
write(BASE / 'reviews/0039.json', review, exclusive=True)
print(json.dumps({'revision': 39, 'retained_admissions': len(attempts), 'maximum': 5}))
