from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==87
new=deepcopy(old);new['revision']=88;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-table-segmentation-2026-10-15.md';dossier=base+'/dossiers/table-segmentation.md'
task=next(t for t in new['tasks'] if t['id']=='page-coverage');task['dossier']=dossier
task['reason']='Discriminate exposed table OCR errors using two fixed original-raster crop arms;retain unaccepted candidate readings and actual full consumer.'
prior=base+'/attempts/page-coverage/attempt-004'
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,prior+'/outputs.json'}|
 {prior+'/'+name for name in read(ROOT/prior/'outputs.json') if not name.startswith(('snapshot/','consumer-methods/','invocations/'))})
new['budgets'][task['budget_key']]['maximum_new_attempts']=5
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),dossier=dossier,next_action=task['reason'],
 remaining='Actual OCR recovers four tables but15/20 exposed controls mismatch;two fixed crop arms test usage before further interpretation.',
 stop_condition='Two native reservations,40 planned OCR operations,60s worker,120s stages,300MiB,one repair;history67 retained;no third arm.')
nl=next(r for r in routes['tasks'] if r['task']=='native-layout-cases')
nl['remaining']='Optional native-page selection004 repairs all four URL literals and retains2682 words;independent full-page Arabic and true vertical original remain absent.'
nl['next_action']='Require a true vertical original or new source-family evidence before further native-layout repair;preserve installed optional replay007.'
rd=next(r for r in routes['tasks'] if r['task']=='relation-discovery')
rd['remaining']='Finite boundary repair and installed optional replay007 retained;independent endpoint/scope inventory and new source families remain absent.'
route_name=base+'/closure-routes-2026-10-15-table-segmentation.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],
 'skeptical_audit':'PASS: exact original and current whole-page baseline;two fixed image-presentation arms;reference literals excluded from OCR;no source-text repair or independent/whole-table promotion.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
 'reason':'Previous004 demonstrates numeric corruption and missing titles before import;segmentation/scale is a distinct finite usage mechanism.',
 'next_discriminating_check':'Same20 original crops at1x/3x plus padding,raw OCR/output mapping and unaccepted review consumer;all controls and regressions retained.',
 'stop_condition':'Two native reservations,40 planned OCR operations,120s stages,300MiB,one repair,no third arm;then independent work.',
 'same_scope_authorization':'User requested comprehensive package integration/usage repair and uninterrupted execution of the repaired master program.'}}
write(ROOT/base/'proposals/table-segmentation-88.json',new,exclusive=True)
write(ROOT/base/'proposals/table-segmentation-88-review.json',review,exclusive=True)
print({'revision':88,'task':task['id'],'retained_admissions':len(attempts),'maximum':5})
