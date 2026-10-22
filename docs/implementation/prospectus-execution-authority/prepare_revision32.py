from copy import deepcopy
from pathlib import Path
import json
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write

a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==31 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-01']['state']==rows['source-bes-dep-08']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-08']==1
assert old['budgets']['source-bes-dep-08']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=32
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-08')
task['dossier']=str((BASE/'dossiers/unaudited-release.md').relative_to(ROOT))
task['reason']='Represent the exact explicitly unaudited issuer release without an invented audit conclusion; refuse false categories and omitted source qualifications'
inputs={task['dossier'],'docs/plans/prospectus-unaudited-release-2026-10-13.md'}
folder=BASE/'attempts/source-bes-dep-08/attempt-001';manifest=read(folder/'outputs.json')
assert all(file_hash(folder/n)==h for n,h in manifest.items())
inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Repair the exact unaudited issuer-release classification gap'],
    'skeptical_audit':'PASS: source literal and exact header coverage; UNKNOWN opinion stays unknown; no unaudited-to-no-assurance equivalence, date/publication confusion or whole-source acceptance',
    'evidence_contract':'Original and current diagnostic consumers preserve literal unaudited release/IFRS/EU/date; refuse false audit or review codes; omissions withhold support; all instrument questions/dependencies preserved',
    'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0032.json',new,exclusive=True);write(BASE/'reviews/0032.json',review,exclusive=True)
print(json.dumps({'revision':32,'task':'source-bes-dep-08','admission':'second original; maximum unchanged'}))
