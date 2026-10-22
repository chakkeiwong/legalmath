"""Prepare a same-task, unchanged-budget scope-repair continuation."""
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import Authority, digest

authority = Authority(ROOT)
state = authority.status()
assert not state['running'] and state['next_task'] is None
old = json.loads((BASE / 'program.json').read_bytes())
assert old['revision'] == 4
new = json.loads(json.dumps(old))
new['revision'] = 5
task = next(t for t in new['tasks'] if t['id'] == 'relation-discovery')
task['dossier'] = str((BASE / 'dossiers/relation-scope-continuation.md').relative_to(ROOT))
task['reason'] = 'Repair the reproduced long-distance regulatory qualification and explicit German margin scope; preserve suggestions-only behavior'
paths = ['docs/plans/prospectus-relation-scope-2026-10-13.md']
prior = BASE / 'attempts/relation-discovery/attempt-001'
paths += [str((prior / p).relative_to(ROOT)) for p in (
    'RESULT.md', 'outputs.json', 'protected-targets.json', 'parent-bindings.json',
    'candidate-answer.json.gz', 'basf-base-september-2022-exchange-graph.json',
    'deutsche-at1-2025-graph.json')]
task['inputs'] += paths
assert new['budgets'] == old['budgets'] and new['obligations'] == old['obligations']
review = {'baseline': digest(old), 'changes': 'Same relation-discovery task, explicit printed scope mechanism; all 59 obligations and 44 tasks retained',
    'skeptical_audit': 'Reviewed in docs/plans/prospectus-relation-scope-2026-10-13.md: finite exposed targets cannot establish automatic or independent acceptance; v1/default and actual downstream matched comparators retained',
    'evidence_contract': 'Exact anchors, original finite endpoints, v1 preservation, unchanged legal answer; leakage/corruption/changed answer invalidates run, finite misses veto promotion only; actual products and reports retained',
    'scope_unchanged': True, 'budget_unchanged': True}
for path, data in [(BASE / 'proposals/0005.json', new), (BASE / 'reviews/0005.json', review)]:
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
print(json.dumps({'revision': 5, 'obligations': len(new['obligations']), 'tasks': len(new['tasks']), 'budget_unchanged': True}))
