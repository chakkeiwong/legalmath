from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==39 and not state['running']
assert next(t for t in state['tasks'] if t['id']=='basf-meanings')['state']=='RESULT_RECORDED'
new=deepcopy(old);new['revision']=40
task=next(t for t in new['tasks'] if t['id']=='basf-meanings')
task['dossier']=str((BASE/'dossiers/representative-governance.md').relative_to(ROOT))
task['reason']='Expose four exact selected representative governance sentences while preserving prior rights and unresolved historical statutory requirements'
inputs={task['dossier'],'docs/plans/prospectus-representative-governance-2026-10-13.md'}
for relative in ('basf-meanings/attempt-006','law-applicability/attempt-005'):
    folder=BASE/'attempts'/relative;manifest=read(folder/'outputs.json')
    assert all(file_hash(folder/name)==expected for name,expected in manifest.items())
    inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
    inputs.update(str((folder/name).relative_to(ROOT)) for name in manifest)
task['inputs']=sorted(set(task['inputs'])|inputs)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e.get('budget_key')=='basf-meanings']
assert len(attempts)==old['budgets']['basf-meanings']['maximum_new_attempts']==6
new['budgets']['basf-meanings']['maximum_new_attempts']=7
review={'baseline':digest(old),'changes':'Four source-specific governance meanings and their actual ordinary-answer explanation; all earlier forty meanings preserved',
 'skeptical_audit':'PASS: complete rendered source inspected; genuine remaining supplied-meaning gap. Keep authority/compliance unknown, excluded alternative absent and onward statute unresolved. Current method baseline and exact staged argument guards prevent stale evidence claims. Full evidence/default audit in the plan.',
 'evidence_contract':'Exact source cuts and prior meanings preserved; baseline/candidate/omission actual consumers and malformed controls; four governance readings visible with unchanged global qualified status and Q4-Q6. No independent acceptance, historical law resolution or actual mandate inferred.',
 'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':'basf-meanings','previous_maximum':6,'new_maximum':7,'retained_attempts':attempts,
 'reason':'Attempt006 expressly leaves adjacent instruction/reporting/power/statutory-reference sentences unresolved. Their original text is retained and four complete supplied meanings can be tested in actual consumers without acquiring external facts.',
 'next_discriminating_check':'Exact selected original paragraph, protected forty meanings and ordinary answer lacking governance explanation; compare supplied four-clause candidate and omitted source.',
 'stop_condition':'Source/method drift, swallowed adjacent source, lost prior meaning/dependency, missing diagnostics, stage beyond120seconds or new evidence above60MB; one diagnosed repair without budget reset.',
 'same_scope_authorization':'Continuous reviewed execution of the original prospectus program, same original task and full cumulative history; no new external call, permission policy or publication.'}}
a.validate_program(new)
write(BASE/'proposals/0040.json',new,exclusive=True);write(BASE/'reviews/0040.json',review,exclusive=True)
print(json.dumps({'revision':40,'retained_admissions':len(attempts),'maximum':7}))
