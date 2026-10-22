import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest

state=Authority(ROOT).status()
assert not state['running'] and state['next_task'] is None
old=json.loads((BASE/'program.json').read_bytes())
assert old['revision']==7
new=json.loads(json.dumps(old))
new['revision']=8
task=next(t for t in new['tasks'] if t['id']=='source-authority')
task['dossier']=str((BASE/'dossiers/archive-observation-continuation.md').relative_to(ROOT))
task['reason']='Integrate the retained exact-byte 2015 archive observation with separate query and knowledge dates, preserving publication/authenticity unknowns'
prior=BASE/'attempts/source-authority/attempt-001'
task['inputs']+=['docs/plans/prospectus-archive-observation-2026-10-13.md']+[str((prior/name).relative_to(ROOT)) for name in (
    'RESULT.md','ARCHIVE-REVIEW.md','archive-result.json','arquivo-2015.pdf','arquivo-2015.headers',
    'arquivo-history.body','arquivo-history-page2.body','source-product.json.gz','request.json','scope-admission.json','outputs.json')]
assert new['budgets']==old['budgets'] and new['obligations']==old['obligations']
review={'baseline':digest(old),'changes':'Refine same source-authority task; all original obligations and budgets retained',
    'skeptical_audit':'Inspected source data and consumers; corrected midnight-before-retrieval baseline; archive date is a conditional observation, never a publication date or 2011 proof',
    'evidence_contract':'Byte/metadata-bound current P2/final observation with date and knowledge controls; matched questions/report facts remain equal; metadata corruption, wrong edition or temporal overclaim vetoes; no independent authentication',
    'scope_unchanged':True,'budget_unchanged':True}
for path,data in ((BASE/'proposals/0008.json',new),(BASE/'reviews/0008.json',review)):
    with path.open('x') as stream:
        json.dump(data,stream,indent=2,ensure_ascii=False)
        stream.write('\n')
print(json.dumps({'revision':8,'obligations':len(new['obligations']),'tasks':len(new['tasks']),'budget_unchanged':True}))
