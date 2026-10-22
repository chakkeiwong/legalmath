from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==85
new=deepcopy(old);new['revision']=86;base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-installed-optionals-2026-10-15.md';dossier=base+'/dossiers/installed-optionals.md'
task=next(t for t in new['tasks'] if t['id']=='native-candidates');task['dossier']=dossier
task['reason']='Run all five optional APIs from an offline installed wheel under isolated imports with exact retained full-output comparisons and adverse controls.'
evidence=['native-candidates/attempt-006','relation-discovery/attempt-003','relation-discovery/attempt-004',
          'page-coverage/attempt-003','native-layout-cases/attempt-004','native-confinement/attempt-002']
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,'pyproject.toml'}|
 {base+'/attempts/'+p+'/'+name for p in evidence for name in ('outputs.json','result.json')}|
 {str(p.relative_to(ROOT)) for p in (ROOT/'src').rglob('*') if p.is_file() and p.suffix in {'.py','.json'} and '__pycache__' not in p.parts})
new['budgets'][task['budget_key']]['maximum_new_attempts']=7
routes=read(ROOT/old['continuation_review']['routes']);route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),next_action=task['reason'],
 remaining='Installed optional API evidence; unseen complete cases,missing families and independent readings remain separate.',
 stop_condition='10 outer commands,120seconds/stage,500MiB,one local repair,zero native/external starts.')
route_name=base+'/closure-routes-2026-10-15-installed-optionals.json';write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name;new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],'skeptical_audit':'PASS: source/wheel/module identities,isolated imports,actual full comparisons and installed adverse controls; no import-only completion or portability claim.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':6,'new_maximum':7,'retained_attempts':attempts,
 'reason':'Current optional APIs have actual checkout evidence but no installed-use result; this evaluates a missing delivery route without native reruns.',
 'next_discriminating_check':'Installed module paths/hashes and exact complete outputs for geometry,review,boundaries,regions and native-text choice.',
 'stop_condition':'10 outer command reservations;zero native/external calls;one local repair;500MiB.',
 'same_scope_authorization':'User requested complete tool integration repair and continuous execution of the repaired master program.'}}
write(ROOT/base/'proposals/installed-optionals-86.json',new,exclusive=True)
write(ROOT/base/'proposals/installed-optionals-86-review.json',review,exclusive=True)
print({'revision':86,'task':task['id'],'retained_admissions':len(attempts),'maximum':7})
