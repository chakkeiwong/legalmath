"""Review one substantive repair of the actual mixed-script intake defect."""
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();assert old['revision']==84
new=deepcopy(old);new['revision']=85
base='docs/implementation/prospectus-execution-authority'
plan='docs/plans/prospectus-native-text-choice-2026-10-15.md'
dossier=base+'/dossiers/native-text-choice.md'
task=next(t for t in new['tasks'] if t['id']=='native-layout-cases')
task['dossier']=dossier
task['reason']='Repair reproduced mixed-script intake through explicit pinned native-page selection with exact line/word accounting and actual full consumer comparison.'
prior=base+'/attempts/native-layout-cases/attempt-003'
task['inputs']=sorted(set(task['inputs'])|{plan,dossier,prior+'/outputs.json'}|
                     {prior+'/'+name for name in read(ROOT/prior/'outputs.json')})
new['budgets'][task['budget_key']]['maximum_new_attempts']=4
routes=read(ROOT/old['continuation_review']['routes'])
route=next(r for r in routes['tasks'] if r['task']==task['id'])
route.update(task_sha256=digest(task),next_action=task['reason'],
 remaining='Native text selection repair; independent full-page Arabic readings, unseen evaluation and true vertical original still missing.',
 stop_condition='No native/external starts,120s per stage,80MiB evidence,one implementation repair; broader acceptance remains separate.')
route_name=base+'/closure-routes-2026-10-15-native-text.json'
write(ROOT/route_name,routes,exclusive=True)
new['continuation_review']['routes']=route_name
new['continuation_review']['bindings'].pop(old['continuation_review']['routes'])
new['continuation_review']['bindings'][route_name]=file_hash(ROOT/route_name)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
review={'baseline':digest(old),'changes':[task['reason']],
 'skeptical_audit':'PASS: earlier geometry-only idea does not fix upstream text; this optional explicit alternative retains both extractions,all words/lines and complete consumer differences. Page5 block mismatch inspected before implementation.',
 'evidence_contract':plan,'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':3,'new_maximum':4,
 'retained_attempts':attempts,'reason':'New actual evidence reproduces literal-space insertion and native Arabic order disagreement; one changed repair,not a replay.',
 'next_discriminating_check':'All2682 native words and168 lines preserved,4 actual literal repairs,195 untouched pages,unknown legal answers and tamper controls.',
 'stop_condition':'Zero native/external calls;120seconds/stage;80MiB;one preserved local repair.',
 'same_scope_authorization':'User directs continued execution of the repaired master program,root-cause integration repairs and independent ready work without checkpoints.'}}
write(ROOT/base/'proposals/native-text-85.json',new,exclusive=True)
write(ROOT/base/'proposals/native-text-85-review.json',review,exclusive=True)
print({'revision':85,'retained_admissions':len(attempts),'new_maximum':4})
