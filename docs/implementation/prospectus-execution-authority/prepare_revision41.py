from copy import deepcopy
from pathlib import Path
import json
import sys
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write
a=Authority(ROOT);old,_,_=a.spec();state=a.status()
assert old['revision']==40 and not state['running']
assert next(t for t in state['tasks'] if t['id']=='law-applicability')['state']=='RESULT_RECORDED'
new=deepcopy(old);new['revision']=41
task=next(t for t in new['tasks'] if t['id']=='law-applicability')
task['dossier']=str((BASE/'dossiers/meeting-proof.md').relative_to(ROOT))
task['reason']='Distinguish source-specific meeting notice, registration and participation-proof alternatives while preserving unknown statutory compatibility and actual facts'
inputs={task['dossier'],'docs/plans/prospectus-meeting-proof-2026-10-13.md'}
for rel in ('basf-meanings/attempt-007','law-applicability/attempt-005'):
    folder=BASE/'attempts'/rel;manifest=read(folder/'outputs.json')
    assert all(file_hash(folder/name)==expected for name,expected in manifest.items())
    inputs.add(str((folder/'outputs.json').relative_to(ROOT)))
    inputs.update(str((folder/name).relative_to(ROOT)) for name in manifest)
task['inputs']=sorted(set(task['inputs'])|inputs)
attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e.get('budget_key')=='law-applicability']
assert len(attempts)==old['budgets']['law-applicability']['maximum_new_attempts']==5
new['budgets']['law-applicability']['maximum_new_attempts']=6
review={'baseline':digest(old),'changes':'Source-specific necessary meeting-proof and notice conditions through existing P4, with actual current consumers and exact reviewed source order',
 'skeptical_audit':'PASS under the source and assumption audit in the plan. Prior entitlement_proof Boolean is an explicit coarse hypothesis, not an engine defect. Preserve notice alternatives, actual ticket validity, statutory compatibility, incomplete timing conventions and source-scope limitations; no production changes.',
 'evidence_contract':'Exact original spans and source identity, independently enumerated formula controls, actual current positive/adverse/unknown/conflict cases, and explicit onward statutory/source limitations; no actual holder or effective meeting verdict.',
 'scope_unchanged':True,'budget_unchanged':False,
 'budget_revision':{'budget_key':'law-applicability','previous_maximum':5,'new_maximum':6,'retained_attempts':attempts,
 'reason':'Review of the next selected original paragraph reveals deposit versus blocked-custody-plus-evidence routes and notice-specific proof exceptions hidden by the coarse supplied premise; retained sources permit a discriminating local analysis.',
 'next_discriminating_check':'Exact reviewed source order and conditional proof alternatives; missing delivered custody evidence or unknown notice branch must withhold the corresponding necessary-condition answer.',
 'stop_condition':'Source/method corruption, unmodeled factual default, missing diagnostics, production change, stage over120seconds or evidence above15MB; one diagnosed bounded harness repair.',
 'same_scope_authorization':'Continuous authorized execution of original prospectus law/source program with unchanged obligations and cumulative history; no external call, setting change or publication.'}}
a.validate_program(new)
write(BASE/'proposals/0041.json',new,exclusive=True);write(BASE/'reviews/0041.json',review,exclusive=True)
print(json.dumps({'revision':41,'retained_admissions':len(attempts),'maximum':6}))
