"""Review the same source-meaning task's missing representative restriction."""
from copy import deepcopy
from pathlib import Path
import sys
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read, write

authority = Authority(ROOT)
old, _, _ = authority.spec()
state = authority.status()
assert old['revision'] == 22 and not state['running']
assert next(t for t in state['tasks'] if t['id'] == 'basf-meanings')['state'] == 'RESULT_RECORDED'
folder = BASE / 'attempts/basf-meanings/attempt-005'
manifest = read(folder / 'outputs.json')
assert all(file_hash(folder / name) == expected for name, expected in manifest.items())
assert read(folder / 'result.json')['status'] == 'PASS'
new = deepcopy(old)
new['revision'] = 23
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE / 'dossiers/basf-representative-restriction.md').relative_to(ROOT))
task['reason'] = 'Repair the source-supported section11(6) restriction omitted from seven supplied individual-holder routes; preserve unresolved statutory and actual mandate facts'
names = {task['dossier'], 'docs/plans/prospectus-basf-representative-restriction-2026-10-13.md', str((folder / 'outputs.json').relative_to(ROOT))}
names.update(str((folder / name).relative_to(ROOT)) for name in manifest)
names.update('docs/implementation/prospectus-basf-scope-repair/source-review-001/' + name for name in ('base-130.png', 'final-7.png'))
task['inputs'] = sorted(set(task['inputs']) | names)
attempts = [e['attempt'] for e in authority.events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-meanings']
assert len(attempts) == old['budgets']['basf-meanings']['maximum_new_attempts'] == 5
new['budgets']['basf-meanings']['maximum_new_attempts'] = 6
review = {
    'baseline': digest(old),
    'changes': 'Add the exact selected representative restriction to seven existing holder-exercised supplied meanings under the same original task; broader amendment work remains open',
    'skeptical_audit': 'PASS for narrowed source-specific interaction: current39 meanings protected; only seven enumerated conditions refined; per-right effective mandate/express permission are hypotheses, never inferred facts. Exact sentence cuts preserve neighboring instructions/reporting duties. No change to production methods. Existing qualified whole answers remain qualified.',
    'evidence_contract': 'Reproduce old route activation despite assumed exclusive mandate; actual candidate consumers must show suppression and express-permission exception per right. Test missing/conflicting hypotheses, omitted source target, false original grounds, exact old source and Q4-Q6 preservation. No actual appointment, statutory compliance, package failure, or independent legal acceptance inferred.',
    'scope_unchanged': True, 'budget_unchanged': False,
    'budget_revision': {
        'budget_key': 'basf-meanings', 'previous_maximum': 5, 'new_maximum': 6, 'retained_attempts': attempts,
        'reason': 'Source review identified a concrete omitted cross-clause restriction in the seven existing holder-exercise conditions, including the previously supplied change-of-control put. The next attempt discriminates and repairs this omission without replacing historical evidence.',
        'next_discriminating_check': 'Exact selected section11(6) source, then matched old/candidate route activation under effective exclusive mandate, express permission and missing scope; per-right application must not suppress unrelated routes.',
        'stop_condition': 'Source/method drift, wrong character cut, lost earlier meaning, invalid/missing diagnostics, any stage over120s or physical evidence over60MB. One diagnosed bounded repair, no blind retry or automatic extension.',
        'same_scope_authorization': 'Standing user request for continuous reviewed execution of the original prospectus program; same original task and all cumulative admissions retained. No network, installation, external messages, global permissions, commit or publication.'
    }
}
authority.validate_program(new)
write(BASE / 'proposals/0023.json', new, exclusive=True)
write(BASE / 'reviews/0023.json', review, exclusive=True)
print(json.dumps({'revision': 23, 'retained_admissions': len(attempts), 'maximum': 6}))
