from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==90
new=deepcopy(old);new['revision']=91;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-jpx-edition-target-2026-10-15.md';dossier=base+'/dossiers/jpx-edition-target.md'
task=next(t for t in new['tasks'] if t['id']=='relation-discovery');task['dossier']=dossier
task['reason']='Review the new Japanese correction against its exact2025 parent and the actual incompatible2026 programme through source-bound optional edition screening and current consumers.'
prior=base+'/attempts/native-layout-cases/attempt-006'
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,prior+'/outputs.json'}|
 {prior+'/'+name for name in read(ROOT/prior/'outputs.json') if not name.startswith(('snapshot/','methods/','invocations/'))}|
 {base+'/attempts/native-layout-cases/attempt-002/fetches/06/body',base+'/attempts/native-layout-cases/attempt-002/jpx-issuer-document-links.json',
  base+'/attempts/native-layout-cases/attempt-005/programme.pdf',base+'/attempts/native-layout-cases/attempt-005/correction.pdf'})
new['budgets'][task['budget_key']]['maximum_new_attempts']=5
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),dossier=dossier,next_action=task['reason'],
 remaining='New Japanese correction targets2025 programme;default relation grammar lacks this source family and exact target review.',
 stop_condition='Two HTTP,four native reservations,120s stages,350MiB,one repair;native73 and source HTTP8 history retained.')
nl=next(r for r in routes['tasks'] if r['task']=='native-layout-cases')
nl['remaining']='Japanese50-page source pair consumed after one-codec repair006;true vertical original and independent reading remain missing.'
nl['next_action']='Preserve failed005 and repaired006;continue substantive edition target under relation-discovery. No repeated layout experiment without new family evidence.'
route_name=base+'/closure-routes-2026-10-15-jpx-edition.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],
 'skeptical_audit':'PASS:new observed source family/exact wrong-edition risk;current default gap is absence,not proven false acceptance;all original statements and unknown law preserved.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
 'reason':'Native-layout006 supplies genuinely new Japanese source/correction family and exact2025 target candidate,meeting prior no-unchanged-replay condition.',
 'next_discriminating_check':'Actual2025/2026 programme editions against explicit correction target;missing/duplicate/false-publication-date and context controls.',
 'stop_condition':'Two HTTP starts,four native reservations,120s stages,350MiB,one repair;no OCR/install/model calls.',
 'same_scope_authorization':'User requested difficult prospectus cases and thorough relation/tool integration repairs with continued reviewed execution.'}}
write(ROOT/base/'proposals/jpx-edition-91.json',new,exclusive=True)
write(ROOT/base/'proposals/jpx-edition-91-review.json',review,exclusive=True)
print({'revision':91,'task':task['id'],'retained_admissions':len(attempts),'maximum':5})
