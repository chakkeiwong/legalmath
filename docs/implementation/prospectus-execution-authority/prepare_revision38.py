from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==37 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-09']['state']==rows['source-bes-dep-10']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-10']==1
assert old['budgets']['source-bes-dep-10']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=38
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-10')
task['dossier']=str((BASE/'dossiers/finance-exact-url.md').relative_to(ROOT))
task['reason']='Enumerate exact issuer-parameter archive captures after the retained wrong-issuer replay; cumulative metadata6/content4 and original admission2 ceilings'
inputs={task['dossier'],'docs/plans/prospectus-finance-exact-url-2026-10-13.md'}
folder=BASE/'attempts/source-bes-dep-10/attempt-001';manifest=read(folder/'outputs.json')
assert all(file_hash(folder/n)==h for n,h in manifest.items())
inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Exact-URL route; explicitly refine local metadata ceiling from4 to6 cumulative, content ceiling remains4 and task admissions remain2'],
 'skeptical_audit':'PASS: actual different issuer reproduced previously; preserve opaque source query encoding, inspect exact capture identities and refuse replay substitutions; empty/denied queries do not prove source absence',
 'evidence_contract':'At most2 new metadata and1 qualifying content response under retained cumulative counts; exact source identity/pages still required; no source claim from metadata alone or source closure from a matching index',
 'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0038.json',new,exclusive=True);write(BASE/'reviews/0038.json',review,exclusive=True)
print(json.dumps({'revision':38,'task':'source-bes-dep-10','original_admission_budget':2,
 'cumulative_search_bounds':{'metadata':6,'content':4}}))
