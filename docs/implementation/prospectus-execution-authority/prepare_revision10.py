import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest
state=Authority(ROOT).status()
assert not state['running'] and state['next_task'] is None
old=json.loads((BASE/'program.json').read_bytes()); assert old['revision']==9
new=json.loads(json.dumps(old)); new['revision']=10
task=next(t for t in new['tasks'] if t['id']=='basf-references')
task['dossier']=str((BASE/'dossiers/basf-tax-definition-continuation.md').relative_to(ROOT))
task['reason']='Resolve the inspected two-step tax redemption amount definition and expose either missing endpoint in actual consumers'
prior=BASE/'attempts/basf-meanings/attempt-002'
task['inputs']+=['docs/plans/prospectus-basf-tax-amount-definition-2026-10-13.md']+[str((prior/f).relative_to(ROOT)) for f in (
    'RESULT.md','outputs.json','common.json.gz','source-readings.json','open-P3.json.gz','open-answer.json.gz',
    'open-products.json.gz','base-123-followup.png','input-bindings.json','frozen-methods.json','run_basf.py','readings.py')]
assert old['budgets']==new['budgets'] and old['obligations']==new['obligations']
review={'baseline':digest(old),'changes':'Refine existing basf-references task under remaining original admission',
    'skeptical_audit':'Inspected exact selected page 123 and original image; tax uses 5(10)(a), not adjacent make-whole 5(10)(b); separate amount definition from maturity activation; retain outside spans and use roles-only comparator',
    'evidence_contract':'Actual two-step typed definition closure and each endpoint omission, with all prior meanings and conditions preserved; wrong source/route or unrelated changes veto; no automatic or independent legal acceptance',
    'scope_unchanged':True,'budget_unchanged':True}
for path,data in ((BASE/'proposals/0010.json',new),(BASE/'reviews/0010.json',review)):
    with path.open('x') as stream: json.dump(data,stream,indent=2,ensure_ascii=False); stream.write('\n')
print({'revision':10,'budget_unchanged':True})
