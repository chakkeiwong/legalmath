from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==89
new=deepcopy(old);new['revision']=90;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-jpx-codec-repair-2026-10-15.md';dossier=base+'/dossiers/jpx-codec-repair.md'
task=next(t for t in new['tasks'] if t['id']=='native-layout-cases');task['dossier']=dossier
task['reason']='Repair reproduced missing raw_unicode_escape dependency in a new sealed snapshot;complete actual Japanese source inspection and consumers without new downloads.'
prior=base+'/attempts/native-layout-cases/attempt-005'
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,prior+'/outputs.json'}|
 {prior+'/'+name for name in read(ROOT/prior/'outputs.json') if not name.startswith(('snapshot/blobs/','methods/','invocations/'))})
new['budgets'][task['budget_key']]['maximum_new_attempts']=6
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),dossier=dossier,next_action=task['reason'],
 remaining='Two exact Japanese originals downloaded;inspection failed because sealed Python codec missing.Original scope and independent reading remain open.',
 stop_condition='Three native starts,no retry,no HTTP,120s stages,350MiB,one repair;native70 and source HTTP8 history retained.')
route_name=base+'/closure-routes-2026-10-15-jpx-codec.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],
 'skeptical_audit':'PASS: exact failing receipt,same inspector/PDFs,one required codec added;actual Japanese source consumers required. No unchanged retry or broad host fallback.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':5,'new_maximum':6,'retained_attempts':attempts,
 'reason':'005 failed on concrete missing standard-library codec;retain failed start and originals and change the sealed declared dependency.',
 'next_discriminating_check':'Same original Japanese helper with exact new codec,then two actual source extractions and full consumer.',
 'stop_condition':'Three native reservations,zero downloads,120s stages,350MiB,one repair;no native retry.',
 'same_scope_authorization':'User requests complete repair of package integration/usage issues and continued reviewed master execution.'}}
write(ROOT/base/'proposals/jpx-codec-90.json',new,exclusive=True)
write(ROOT/base/'proposals/jpx-codec-90-review.json',review,exclusive=True)
print({'revision':90,'task':task['id'],'retained_admissions':len(attempts),'maximum':6})
