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
assert old['revision'] == 8
new = json.loads(json.dumps(old))
new['revision'] = 9
task = next(t for t in new['tasks'] if t['id'] == 'basf-meanings')
task['dossier'] = str((BASE / 'dossiers/basf-redemption-continuation.md').relative_to(ROOT))
task['reason'] = 'Interpret complete selected German section 5(1)–(4) as conditional redemption routes with source and downstream controls'
task['inputs'] += ['docs/plans/prospectus-basf-redemption-meanings-2026-10-13.md']
for name, files in (
    ('basf-meanings', ('RESULT.md', 'coverage.json', 'outputs.json')),
    ('basf-references', ('actual-P1.json.gz', 'actual-P2.json.gz', 'SOURCE-REVIEW.md', 'outputs.json')),
    ('basf-incorporation', ('actual-P3.json.gz', 'actual-P4.json.gz', 'actual-P5.json.gz', 'actual-answer.json.gz', 'outputs.json'))):
    task['inputs'] += [str((BASE / 'attempts' / name / 'attempt-001' / f).relative_to(ROOT)) for f in files]
task['inputs'] += [f'docs/implementation/prospectus-basf-scope-repair/source-review-001/base-{p}.png' for p in (118,119,120)]
assert old['budgets'] == new['budgets'] and old['obligations'] == new['obligations']
review = {'baseline': digest(old), 'changes': 'Refine the same BASF meanings task under its second original admission',
          'skeptical_audit': 'Read code, selected German text and original pages; require role-only comparator, exact outside-span preservation and explicit conditional premises; do not promote counts or infer unconditional repayment',
          'evidence_contract': 'Four complete source-bound repayment readings with condition-sensitive actual downstream reasoning; wrong source, lost prior meaning/outside span or unrelated answer promotion vetoes; conditional supplied development evidence only',
          'scope_unchanged': True, 'budget_unchanged': True}
for path, data in ((BASE / 'proposals/0009.json', new), (BASE / 'reviews/0009.json', review)):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
print(json.dumps({'revision': 9, 'tasks': len(new['tasks']), 'obligations': len(new['obligations']), 'budget_unchanged': True}))
