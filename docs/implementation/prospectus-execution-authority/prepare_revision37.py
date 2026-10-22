from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==36 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-06']['state']==rows['source-bes-dep-09']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-09']==1
assert old['budgets']['source-bes-dep-09']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=37
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-09')
task['dossier']=str((BASE/'dossiers/english-2010-reports.md').relative_to(ROOT))
task['reason']='Supply separate inspected English2010 statutory and committee context; retain paragraph8, knowledge qualifier and distinct closing dates'
inputs={task['dossier'],'docs/plans/prospectus-english-2010-reports-2026-10-13.md'}
for rel in ('source-bes-dep-09/attempt-001','source-bes-dep-06/attempt-002'):
    folder=BASE/'attempts'/rel;manifest=read(folder/'outputs.json')
    assert all(file_hash(folder/n)==h for n,h in manifest.items())
    inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
    inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Separate two actual English report roles and qualify their supplied support'],
 'skeptical_audit':'PASS: both source images/texts inspected, distinct paragraph8 and committee knowledge/date considered; same-source comparator, exact2009 regression, finite-profile nonclaims and original budgets retained',
 'evidence_contract':'Original and matched current two-report consumers; omitted paragraph8/knowledge, wrong dates and merged roles withhold; false categories reject; original14 obligations remain visible',
 'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0037.json',new,exclusive=True);write(BASE/'reviews/0037.json',review,exclusive=True)
print(json.dumps({'revision':37,'task':'source-bes-dep-09','admission':'second original; maximum unchanged'}))
