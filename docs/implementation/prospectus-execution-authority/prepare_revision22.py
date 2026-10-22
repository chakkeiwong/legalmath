"""Continue source meanings only after original omission evidence is complete."""
from copy import deepcopy
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read,write

authority=Authority(ROOT)
old,tasks,_=authority.spec()
state=authority.status()
assert old['revision']==21 and not state['running']
rows={r['id']:r for r in state['tasks']}
assert rows['basf-meanings']['state']=='RESULT_RECORDED'
assert all(rows[k]['state']=='COMPLETE' for k in ('recovery','authority-acceptance'))
folder=BASE/'attempts/basf-meanings/attempt-004'
manifest=read(folder/'outputs.json')
assert all(file_hash(folder/name)==expected for name,expected in manifest.items())
assert read(folder/'result.json')['status']=='PASS'
assert read(folder/'result.json')['complete_original_case_set_across_attempts']==7
new=deepcopy(old);new['revision']=22
task=next(t for t in new['tasks'] if t['id']=='basf-meanings')
task['dossier']=str((BASE/'dossiers/basf-default-rights.md').relative_to(ROOT))
task['reason']='Carry six selected holder-default grounds through real answers with individual cure, quorum and notice; preserve unresolved German (f) and the completed redemption baseline'
names={task['dossier'],'docs/plans/prospectus-basf-default-rights-2026-10-13.md',
       str((folder/'outputs.json').relative_to(ROOT))}
names.update(str((folder/name).relative_to(ROOT)) for name in manifest)
for name in ('base-126.png','base-127.png','final-7.png'):
    names.add('docs/implementation/prospectus-basf-scope-repair/source-review-001/'+name)
task['inputs']=sorted(set(task['inputs'])|names)
attempts=[e['attempt'] for e in authority.events() if e['kind']=='ADMIT' and e.get('budget_key')=='basf-meanings']
assert len(attempts)==old['budgets']['basf-meanings']['maximum_new_attempts']==4
new['budgets']['basf-meanings']['maximum_new_attempts']=5
review={
    'baseline':digest(old),
    'changes':'Same original source-meaning task: six complete conditional section9 grounds; all33 earlier readings retained and German(f) construction explicitly unresolved',
    'skeptical_audit':'Newest open-facts result is protected; timeout and exact staged-equivalence evidence remain. Per-ground cure, receipt-time quorum exception and non-universal EUR200m threshold are explicit. English cannot replace German(f). Use the validated production-component partition. Reuse construction only when all construction-relevant inputs are equal; report it honestly.',
    'evidence_contract':'Exact selected quotations/maps, six complete source-defined routes, actual quorum/receipt/cure/notice effects, typed nominal/debt links, complete finite logic worlds, source/mutation controls and debt-definition omission. Preserve all outside meanings, construction, dependencies and Q4-Q6; Q1/Q2 UNKNOWN and Q3 PARTIAL. No actual transaction or independent legal acceptance.',
    'scope_unchanged':True,'budget_unchanged':False,
    'budget_revision':{
        'budget_key':'basf-meanings','previous_maximum':4,'new_maximum':5,'retained_attempts':attempts,
        'reason':'All originally required redemption cases now have evidence. Original selected section9 sources still lack conditional meanings, including consequential cure and quorum restrictions. The identified German(f) ambiguity narrows this package; it does not prevent source-supported independent grounds.',
        'next_discriminating_check':'Actual answers distinguish missing quorum from its receipt-time exception, cure of one ground from all other surviving grounds, and missing complete debt definition from a resolved clause chain.',
        'stop_condition':'Source/method drift, lost outside/earlier meaning, unknown(f) silently closed, changed construction, wrong route effects, absent diagnostics, any stage over120s or physical evidence over60MB. One diagnosed bounded local repair; no unchanged retry, automatic extension or production default change.',
        'same_scope_authorization':'Standing request for continuous thorough execution of the original prospectus program; original task/obligations and all cumulative admissions retained. No installation, network, external message, permission change, commit or publication.'}}
authority.validate_program(new)
write(BASE/'proposals/0022.json',new,exclusive=True)
write(BASE/'reviews/0022.json',review,exclusive=True)
print(json.dumps({'revision':22,'task':'basf-meanings','maximum':5,'retained_attempts':len(attempts),'new_bound_paths':len(names)}))
