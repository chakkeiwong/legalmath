"""Prepare an unchanged-budget continuation for two real report counterexamples."""
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest

state = Authority(ROOT).status()
assert not state['running'] and state['next_task'] is None
old = json.loads((BASE / 'program.json').read_bytes())
assert old['revision'] == 5
new = json.loads(json.dumps(old))
new['revision'] = 6
task = next(t for t in new['tasks'] if t['id'] == 'portuguese-2008')
task['dossier'] = str((BASE / 'dossiers/portuguese-context-continuation.md').relative_to(ROOT))
task['reason'] = 'Repair misleading event-date and omitted local-accounting exception readings using exact full-report context; compare actual downstream v1/v2 results'
prior = BASE / 'attempts/portuguese-2008/attempt-001'
task['inputs'] += ['docs/plans/prospectus-portuguese-context-2026-10-13.md'] + [str((prior / name).relative_to(ROOT)) for name in (
    'RESULT.md', 'IMAGE-REVIEW.md', 'semantic-limits.json', 'selected-reading.json', 'scope-admission.json',
    'source-product.json.gz', 'outputs.json', 'p248-150dpi.png', 'p251-150dpi.png')]
assert new['budgets'] == old['budgets'] and new['obligations'] == old['obligations']
review = {'baseline': digest(old), 'changes': 'Same Portuguese report task, two reproduced semantic-context failures; all 59 obligations and 44 tasks retained',
    'skeptical_audit': 'Plan inspects source pages and code; optional limited grammar cannot prove arbitrary semantics; actual retained-P1/current-downstream comparator and fail-closed context rules required',
    'evidence_contract': 'Positive conditional readings survive, two misleading readings lose complete report-use support, source quotes/debt answers remain unchanged; leakage/corruption or changed debt answer invalidates run; no independence or native-package verdict',
    'scope_unchanged': True, 'budget_unchanged': True}
for path, data in [(BASE / 'proposals/0006.json', new), (BASE / 'reviews/0006.json', review)]:
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
print(json.dumps({'revision': 6, 'obligations': len(new['obligations']), 'tasks': len(new['tasks']), 'budget_unchanged': True}))
