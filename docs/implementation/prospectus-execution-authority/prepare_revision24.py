"""Bind a reviewed source investigation to the original law-applicability task."""
from copy import deepcopy
from pathlib import Path
import sys
import json

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write

authority=Authority(ROOT)
old,_,_=authority.spec();state=authority.status()
assert old['revision']==23 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert all(rows[key]['state']=='RESULT_RECORDED' for key in ('basf-meanings','law-applicability'))
folder=BASE/'attempts/basf-meanings/attempt-006'
manifest=read(folder/'outputs.json')
assert all(file_hash(folder/name)==expected for name,expected in manifest.items())
assert read(folder/'result.json')['status']=='PASS'
admissions=[e['attempt'] for e in authority.events() if e['kind']=='ADMIT' and e.get('budget_key')=='law-applicability']
assert len(admissions)==1 and old['budgets']['law-applicability']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=24
task=next(t for t in new['tasks'] if t['id']=='law-applicability')
task['dossier']=str((BASE/'dossiers/schvg-source-review.md').relative_to(ROOT))
task['reason']='Inspect the missing official SchVG source, edition and contractual/statutory dependencies before designing the BASF creditor-amendment assessment; preserve prior recognition evidence'
names={task['dossier'],'docs/plans/prospectus-schvg-source-review-2026-10-13.md',
    'docs/plans/prospectus-basf-amendment-review-2026-10-13.md',str((folder/'outputs.json').relative_to(ROOT))}
names.update(str((folder/name).relative_to(ROOT)) for name in manifest)
names.update('docs/implementation/prospectus-basf-scope-repair/source-review-001/'+name for name in ('base-129.png','base-130.png','base-131.png','final-7.png'))
task['inputs']=sorted(set(task['inputs'])|names)
review={'baseline':digest(old),
    'changes':'Use the existing second law-applicability admission for the concrete SchVG source dependency of BASF section11; preserve original recognition cases and every obligation/budget',
    'skeptical_audit':'PASS for source investigation and smallest consumer diagnostic; separate review required before production changes. Complete statute scope/procedure and edition history must be inspected. Current consolidation cannot establish issue-date applicability. Amendment powers cannot be encoded as actual loss or conversion. Missing actual events do not stop conditional source analysis.',
    'evidence_contract':'Official bytes/provenance and full relevant provisions, contract/statute dependency map, explicit historical and actual-fact gaps, reproduced current consumer behavior and concrete next design. Six bounded official GETs maximum with failed requests retained,25s each,10MB new evidence. No actual resolution, statutory effectiveness, automatic legal reading or independent acceptance inferred.',
    'scope_unchanged':True,'budget_unchanged':True}
authority.validate_program(new)
write(BASE/'proposals/0024.json',new,exclusive=True)
write(BASE/'reviews/0024.json',review,exclusive=True)
print(json.dumps({'revision':24,'task':'law-applicability','retained_admissions':len(admissions),'maximum':2}))
