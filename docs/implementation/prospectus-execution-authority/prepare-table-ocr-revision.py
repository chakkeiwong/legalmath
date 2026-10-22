from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==86
new=deepcopy(old);new['revision']=87;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-rotated-table-ocr-2026-10-15.md';dossier=base+'/dossiers/rotated-table-ocr.md'
task=next(t for t in new['tasks'] if t['id']=='page-coverage');task['dossier']=dossier
task['reason']='Run actual selected-page OCR for four missing rotated cohort tables;compare full consumers and exposed image controls without claiming complete coverage.'
evidence=['page-coverage/attempt-002','page-coverage/attempt-003','native-candidates/attempt-007']
task['inputs']=sorted(set(task['inputs'])|{plan,dossier}|
 {base+'/attempts/'+p+'/'+name for p in evidence for name in ('outputs.json','result.json')}|
 {base+'/attempts/page-coverage/attempt-003/'+name for name in read(ROOT/base/'attempts/page-coverage/attempt-003/outputs.json')}|
 {str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath/prospectus/successor').glob('*.py')})
new['budgets'][task['budget_key']]['maximum_new_attempts']=4
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),next_action=task['reason'],
 remaining='Actual OCR and cell/region review for the retained four-table page;complete independent cell readings remain open.',
 stop_condition='Four native reservations,120s stages,350MiB,one local repair;native64 history retained.')
# The installed evidence changes next-work advice without changing accepted task scope.
nc=next(r for r in routes['tasks'] if r['task']=='native-candidates')
nc['remaining']='Five optional APIs now have exact installed replay evidence from007;nine installed controls pass. Fresh/independent evaluation and missing families remain.'
nc['next_action']='Preserve installed007 comparators;continue source families and independent complete-page evidence before another native candidate.'
route_name=base+'/closure-routes-2026-10-15-table-ocr.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],'skeptical_audit':'PASS: real native-only missing-content blocker;existing OCR profile,exact same original,full downstream comparison and pre-OCR image controls;no text-presence completeness proxy.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':3,'new_maximum':4,'retained_attempts':attempts,
 'reason':'Prior003 identifies four specific unavailable regions;new actual OCR changes the extraction mechanism while retaining native baseline.',
 'next_discriminating_check':'All four required tables through actual selected-page OCR and full source-to-answer consumers;image-bound label/percentage controls.',
 'stop_condition':'Four native reservations,120seconds/stage,350MiB,one repair;no network/install/model calls.',
 'same_scope_authorization':'User requested difficult prospectus cases,tool integration repair and continued master execution without checkpoints.'}}
write(ROOT/base/'proposals/table-ocr-87.json',new,exclusive=True);write(ROOT/base/'proposals/table-ocr-87-review.json',review,exclusive=True)
print({'revision':87,'task':task['id'],'retained_admissions':len(attempts),'maximum':4})
