"""Record the closure checkpoint without altering running program bindings."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import fcntl,json,sys
ROOT=Path('/home/chakwong/python/legalmath');sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,ref,save,require,process_alive
from scripts.legal_integration_master import BASE,DOC,PROGRAM,STATE
from legalmath.interpretation.assurance.phased.branch_budget import bucket
WORK=Path('artifacts/legal-mission-control/2026-10-26/product-closure')
require(read(ROOT/WORK/'installed-verification.json')['verdict']=='PASS','Deployment not verified')
program=read(ROOT/PROGRAM);binding=read(ROOT/BASE/'current-binding.json')
state=read(ROOT/STATE);ledger=read(ROOT/BASE/'live-calls.json')
budget=read(ROOT/binding['execution_budget']['path']);before=read(ROOT/budget['ledger_before']['path'])
used={k:0 for k in budget['protected_calls']}
for row in ledger['calls'][len(before['calls']):]:
    k=bucket(row.get('owner','other'));used[k]=used.get(k,0)+1
recovery=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-recovery.json')
used['service']=max(used['service'],len(recovery['charges'])-budget['prior_service_replacements'])
floors={k:max(0,n-used.get(k,0)) for k,n in budget['protected_calls'].items()}
armed=read(ROOT/WORK/'armed.json');remaining=ledger['maximum']-len(ledger['calls'])
snapshot=dict(at_utc=datetime.now(timezone.utc).isoformat(),program=ref(ROOT,PROGRAM),
    calls=len(ledger['calls']),remaining_calls=remaining,protected_floors=floors,
    unprotected_calls=remaining-sum(floors.values()),service_replacements=len(recovery['charges']),
    task_counts=dict(Counter(v['status'] for v in state['tasks'].values())),
    running=[k for k,v in state['tasks'].items() if v['status']=='RUNNING'],
    worker=armed['process'],worker_alive=process_alive(armed['process']),
    original_obligations=46,original_readings=35,provider_calls_added_by_audit=0,
    integration_complete=False,legal_acceptance=False)
save(ROOT/WORK/'gap-audit-snapshot.json',snapshot)
paths=[WORK/'gap-audit-snapshot.json',WORK/'local-result-v3.json',WORK/'staged-verification.json',
    WORK/'installed-verification.json',WORK/'corpus-handler/result.json',WORK/'corpus-two-answers-result.json',
    WORK/'corpus-p14-answer-result.json',WORK/'corpus-gatecoin-answer-result.json',WORK/'treatment-search-result.json',
    Path('docs/implementation/legal-mission-control/results/product-closure-gap-audit-2026-10-26.md')]
evidence=[ref(ROOT,p) for p in paths]
missionpath=ROOT/DOC/'mission.json'
with missionpath.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    mission=read(missionpath)
    require(mission['integration_master']['program']==ref(ROOT,PROGRAM),'Program changed while recording review')
    event_id='product-closure-gap-audit-2026-10-26'
    require(not any(r['id']==event_id for r in mission['history']),'Audit already recorded')
    reason='Continue the registered independent ready branches within protected budgets; retain P14 audit-confidence repair, exact source-treatment limits and pending original-answer/tool comparisons. Use the product-closure gap audit at the next safe checkpoint.'
    mission['history'].append(dict(id=event_id,task_id='product-contribution',kind='product_evaluation',
        outcome='no_advance',decision='Installed repair verified; source and original-case reviews retained; mission completion remains unestablished.',
        next_task='product-contribution',next_task_reason=reason,recorded_at_utc=snapshot['at_utc'],result_evidence=evidence))
    mission['next_task_reason']=reason
    mission['last_product_closure_audit']=dict(snapshot=evidence[0],result=evidence[-1],
        p14_answer_use=ref(ROOT,WORK/'corpus-p14-answer-result.json'),
        gatecoin_answer_use=ref(ROOT,WORK/'corpus-gatecoin-answer-result.json'),
        treatment=ref(ROOT,WORK/'treatment-search-result.json'))
    save(missionpath,mission)
save(ROOT/WORK/'gap-audit-recorded.json',dict(at_utc=snapshot['at_utc'],event_id=event_id,
    program_unchanged=True,attempts_added=0,calls_added=0,mission=ref(ROOT,DOC/'mission.json')))
print(json.dumps(snapshot,indent=2))
