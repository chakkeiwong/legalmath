"""Refine the original finance task for its reproduced local interface gaps."""
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
assert old['revision'] == 6
new = json.loads(json.dumps(old))
new['revision'] = 7
task = next(t for t in new['tasks'] if t['id'] == 'finance-conventions')
task['dossier'] = str((BASE / 'dossiers/finance-broken-coupon-continuation.md').relative_to(ROOT))
task['reason'] = 'Repair distinct published initial coupon/form inputs and source-selected first-stub schedules; compare actual direct/selected consumers with retained exact Shell arithmetic'
prior = BASE / 'attempts/finance-conventions/attempt-001'
task['inputs'] += ['docs/plans/prospectus-broken-coupon-interface-2026-10-13.md'] + [str((prior / name).relative_to(ROOT)) for name in (
    'RESULT.md','source-review.json','source-bindings.json','source-P1.json.gz','global-scenario.json',
    'definitive-scenario.json','independent-calendar.json','quantlib/result.json','comparison.json','outputs.json',
    'images/final-2.png','images/final-3.png','images/base-035.png','images/base-036.png')]
assert new['budgets'] == old['budgets'] and new['obligations'] == old['obligations']
review = {'baseline':digest(old),'changes':'Refine original finance-conventions task with unchanged 59 obligations, 44 tasks and original budgets',
    'skeptical_audit':'Reviewed plan narrows global form to one hypothetical aggregate, selected schedules to anchored first stubs, and distinguishes published amount checks from whole-source semantic truth',
    'evidence_contract':'Both actual consumers preserve exact form-specific amounts and matched Q1-Q4; wrong sources/amounts/bases/schedules reject; historical QuantLib and P1 are explicitly historical; no independent legal acceptance or full settlement claim',
    'scope_unchanged':True,'budget_unchanged':True}
for path,data in ((BASE / 'proposals/0007.json',new),(BASE / 'reviews/0007.json',review)):
    with path.open('x') as stream:
        json.dump(data,stream,indent=2,ensure_ascii=False)
        stream.write('\n')
print(json.dumps({'revision':7,'obligations':len(new['obligations']),'tasks':len(new['tasks']),'budget_unchanged':True}))
