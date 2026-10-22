from copy import deepcopy
from pathlib import Path
import json,sys
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==33 and not state['running']
rows={t['id']:t for t in state['tasks']}
assert rows['source-bes-dep-07']['state']==rows['source-bes-dep-11']['state']=='RESULT_RECORDED'
assert state['budget_admissions']['source-bes-dep-07']==1
assert old['budgets']['source-bes-dep-07']['maximum_new_attempts']==2
new=deepcopy(old);new['revision']=34
task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-07')
task['dossier']=str((BASE/'dossiers/bilingual-note.md').relative_to(ROOT))
task['reason']='Expose the exact unresolved Note46 bilingual monetary discrepancy in current answers with paired context and provenance; choose neither amount'
inputs={task['dossier'],'docs/plans/prospectus-bilingual-note-2026-10-13.md'}
folder=BASE/'attempts/source-bes-dep-07/attempt-001';manifest=read(folder/'outputs.json')
assert all(file_hash(folder/n)==h for n,h in manifest.items())
inputs.update(str((folder/n).relative_to(ROOT)) for n in manifest)
inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
for row in read(folder/'edition-review.json')['editions']:
    for key in ('source','receipt'):
        assert file_hash(ROOT/row[key])==row[key+'_sha256'];inputs.add(row[key])
task['inputs']=sorted(set(task['inputs'])|inputs)
review={'baseline':digest(old),'changes':['Carry the inspected bilingual first-bullet discrepancy into current answers'],
    'skeptical_audit':'PASS: complete original context, exact two-side identity, matched no-review baseline, no amount normalization or unrelated bond-principal inference; all original unknowns preserved',
    'evidence_contract':'Actual source-pair consumer preserves unresolved amounts and provenance; adverse integrity/context cases refuse; questions/dependencies/calculations unchanged',
    'scope_unchanged':True,'budget_unchanged':True}
a.validate_program(new)
write(BASE/'proposals/0034.json',new,exclusive=True);write(BASE/'reviews/0034.json',review,exclusive=True)
print(json.dumps({'revision':34,'task':'source-bes-dep-07','admission':'second original; maximum unchanged'}))
