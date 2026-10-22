from copy import deepcopy
from pathlib import Path
import json,sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==34 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['independent-packet']['state']==rows['source-bes-dep-07']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['independent-packet']==1
assert old['budgets']['independent-packet']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=35
task=next(t for t in new['tasks'] if t['id']=='independent-packet')
task['dossier']=str((BASE/'dossiers/review-inventory.md').relative_to(ROOT))
task['reason']='Repair the reproduced manifest file-field omission and conservatively propagate development exposure across retained source aliases'
inputs={task['dossier'],'docs/plans/prospectus-review-inventory-2026-10-13.md'}
folder=BASE/'attempts/independent-packet/attempt-001';manifest=read(folder/'outputs.json')
assert all(file_hash(folder/n)==h for n,h in manifest.items())
inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
for rel,h in read(folder/'input-hashes.json').items():
    assert file_hash(ROOT/rel)==h;inputs.add(rel)
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Repair the 22 manifest omissions and retain conservative alias/family exposure in cohort preparation'],
    'skeptical_audit':'PASS: exact baseline denominator and hashes, explicit family provenance, unknown remains blocked; no authenticated people or unexposed cohort fabricated',
    'evidence_contract':'Every declared entry accounted; actual preparation rejects exposed/unknown candidates; missing/mismatched/ambiguous source controls refuse; no independent acceptance',
    'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0035.json',new,exclusive=True);write(BASE/'reviews/0035.json',review,exclusive=True)
print(json.dumps({'revision':35,'task':'independent-packet','admission':'second original; maximum unchanged'}))
