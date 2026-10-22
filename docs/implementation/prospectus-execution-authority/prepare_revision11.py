from copy import deepcopy
import json
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest
a=Authority(ROOT);old,tasks,_=a.spec();state=a.status()
assert old['revision']==10 and state['next_task'] is None and not state['running']
new=deepcopy(old);new['revision']=11
key='recovery';task=next(t for t in new['tasks'] if t['id']==key)
task.pop('validator');task.pop('evidence_attempt')
task['dossier']=str((BASE/'dossiers/current-recovery-evidence.md').relative_to(ROOT))
task['reason']='Produce fresh eight-state actual/clean recovery after consolidated source/report/finance edits; record evidence before separately binding existing validator'
task['inputs']+=['docs/plans/prospectus-current-revalidation-2026-10-13.md']
new['budgets'][key]['maximum_new_attempts']=3
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e.get('budget_key')==key]
assert len(attempts)==2 and old['budgets'][key]['maximum_new_attempts']==2
review={'baseline':digest(old),'changes':'Current recovery evidence production under same original task, with subsequent separate named validation required',
    'skeptical_audit':'Eight current method changes make retained recovery historical; pre-run binding cannot include not-yet-generated outputs; temporarily omit optional validator for partial evidence only and preserve original acceptance requirements',
    'evidence_contract':'Same eight states, actual/clean complete equality, exact original units/images, rejection and restoration; no legal/native/portability promotion',
    'scope_unchanged':True,'budget_unchanged':False,
    'budget_revision':{'budget_key':key,'previous_maximum':2,'new_maximum':3,'retained_attempts':attempts,
        'reason':'One current evidence rerun after consolidated product edits; earlier successful execution and verification remain immutable',
        'next_discriminating_check':'Current actual/clean eight-state equality and original source/image preservation',
        'stop_condition':'Input or method drift, unequal actual/clean outputs, accepted malformed input, timeout or failed source preservation; investigate before any further admission',
        'same_scope_authorization':'User requested refreshed master program and continuous execution of known repairs; this is local revalidation of the original recovery task, not new external work'}}
for path,data in ((BASE/'proposals/0011.json',new),(BASE/'reviews/0011.json',review)):
    with path.open('x') as stream:json.dump(data,stream,indent=2);stream.write('\n')
print({'revision':11,'task':key,'maximum':3,'retained_attempts':len(attempts)})
