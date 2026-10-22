from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==35 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-06']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-06']==1
assert old['budgets']['source-bes-dep-06']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=36
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-06')
task['dossier']=str((BASE/'dossiers/english-audit-context.md').relative_to(ROOT))
task['reason']='Repair wrong-role and incomplete supplied spans on the inspected English consolidated audit; preserve full source context'
inputs={task['dossier'],'docs/plans/prospectus-english-audit-context-2026-10-13.md'}
folder=BASE/'attempts/source-bes-dep-06/attempt-001';manifest=read(folder/'outputs.json')
assert all(file_hash(folder/n)==h for n,h in manifest.items())
inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Inspect and repair exact English audit context under the original second admission'],
 'skeptical_audit':'PASS: original images and full text inspected; exact finite source binding does not establish general semantics; current matched comparator, retained source noise, role/date/context controls and preserved obligations',
 'evidence_contract':'Reproduce wrong-role promotion before repair; complete source-bound scope reaches current consumer; omissions withhold and wrong categories refuse; original14 dependencies and questions preserved',
 'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0036.json',new,exclusive=True);write(BASE/'reviews/0036.json',review,exclusive=True)
print(json.dumps({'revision':36,'task':'source-bes-dep-06','admission':'second original; maximum unchanged'}))
