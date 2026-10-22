from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==88
new=deepcopy(old);new['revision']=89;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-jpx-source-pair-2026-10-15.md';dossier=base+'/dossiers/jpx-source-pair.md'
task=next(t for t in new['tasks'] if t['id']=='native-layout-cases');task['dossier']=dossier
task['reason']='Acquire the two exact previously observed JPX Japanese programme/correction originals,inspect layout and execute actual source-to-answer consumers without presuming vertical writing.'
prior=base+'/attempts/native-layout-cases/attempt-002'
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,prior+'/outputs.json',
 prior+'/fetches/06/body',prior+'/fetches/06/result.json',prior+'/jpx-issuer-document-links.json',
 base+'/attempts/page-coverage/attempt-005/outputs.json',base+'/attempts/page-coverage/attempt-005/result.json'})
new['budgets'][task['budget_key']]['maximum_new_attempts']=5
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),dossier=dossier,next_action=task['reason'],
 remaining='Japanese original and true vertical source remain absent;official exact programme/correction links are retained but untested.',
 stop_condition='Three HTTP starts,three native starts,120s stages,350MiB,one repair;source HTTP6 and native69 history retained.')
pc=next(r for r in routes['tasks'] if r['task']=='page-coverage')
pc['remaining']='Actual OCR004 recovers words but15/20 controls mismatch;crop005 arms match8/20 and7/20 with regressions.Both rejected;full table interpretation absent.'
pc['next_action']='Preserve sealed004/005;no further exposed crop tuning. Require a reviewed distinct table method and independent full-cell readings before broader acceptance.'
route_name=base+'/closure-routes-2026-10-15-jpx-source.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],
 'skeptical_audit':'PASS: two exact observed official links,new Japanese source/correction family,actual source consumers;vertical writing and historical authority remain hypotheses.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
 'reason':'Earlier002 exhausted six starts acquiring Arabic original and discovering JPX links;004 completed distinct Arabic intake repair.New exact Japanese sources remain unfetched.',
 'next_discriminating_check':'Original PDF layout inventory and images plus actual P1–P5/full answer for Japanese programme/correction;no synthetic vertical proxy.',
 'stop_condition':'Three HTTP starts,three native reservations,120s stages,350MiB,one repair;no expanded search.',
 'same_scope_authorization':'User authorized downloading further difficult original prospectuses and continued execution of reviewed master repairs.'}}
write(ROOT/base/'proposals/jpx-source-89.json',new,exclusive=True)
write(ROOT/base/'proposals/jpx-source-89-review.json',review,exclusive=True)
print({'revision':89,'task':task['id'],'retained_admissions':len(attempts),'maximum':5})
