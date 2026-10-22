from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==32 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-08']['state']==rows['source-bes-dep-11']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-11']==1
assert old['budgets']['source-bes-dep-11']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=33
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-11')
task['dossier']=str((BASE/'dossiers/q1-unaudited-release.md').relative_to(ROOT))
task['reason']='Represent the separately inspected Q1 2011 unaudited release; refuse false audit classifications and crossed period/date support'
inputs={task['dossier'],'docs/plans/prospectus-q1-release-2026-10-13.md'}
for rel in ('source-bes-dep-11/attempt-001','source-bes-dep-08/attempt-002'):
    folder=BASE/'attempts'/rel;manifest=read(folder/'outputs.json')
    assert all(file_hash(folder/n)==h for n,h in manifest.items())
    inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
    inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Bind the distinct Q1 release title/date to its inspected finite source profile'],
    'skeptical_audit':'PASS: original source inspected; no arbitrary date generalization; exact FY regression and current Q1 comparator; missing qualifications withhold, source authority stays unknown',
    'evidence_contract':'Original and matched current consumers retain literal unaudited IFRS/EU scope; false categories reject; crossed title/date pairs withhold; original dependencies and questions unchanged',
    'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0033.json',new,exclusive=True);write(BASE/'reviews/0033.json',review,exclusive=True)
print(json.dumps({'revision':33,'task':'source-bes-dep-11','admission':'second original; maximum unchanged'}))
