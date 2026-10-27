"""Retain scoped supplements without changing any live answer or program."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,sys
ROOT=Path('/home/chakwong/python/legalmath');sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import read,save,ref,require,process_identity
from scripts.legal_integration_master import DOC,PROGRAM
WORK=Path('artifacts/legal-mission-control/2026-10-26/product-closure')
packet=read(ROOT/WORK/'p14-review-packet.json');answer=packet['answer']
selected=[answer['support'][i] for i in (0,1,2,3,8,9)]
require('reasonable to rely' in selected[-1]['quote'] and 'smart contract is deployed' in selected[-1]['quote'],
    'Missing exact reliance and deployed-contract source')
note=Path('docs/implementation/legal-mission-control/results/p14-assurance-supplement-2026-10-26.md')
proof_path=ROOT/WORK/'p14-assurance-supplement-proof.json'
proof=dict(
    at_utc=datetime.now(timezone.utc).isoformat(),supplement=ref(ROOT,note),
    fixed_answer=ref(ROOT,WORK/'p14-reviewed-answer.json'),source_packet=ref(ROOT,WORK/'p14-review-packet.json'),
    exact_support=selected,review=ref(ROOT,Path('docs/implementation/legal-mission-control/results/p14-answer-use-review-2026-10-26.md')),
    deployed_version_requirement='Explicit local evidential inference; not a quoted independent legal rule',
    candidate_status='SOURCE_REVIEWED_DRAFT_NOT_CONSUMED',provider_calls=0,legal_acceptance=False)
if proof_path.exists():
    retained=read(proof_path)
    require({k:v for k,v in retained.items() if k!='at_utc'}==
        {k:v for k,v in proof.items() if k!='at_utc'},'Changed retained supplement proof')
else:
    save(proof_path,proof)
recorded=read(ROOT/WORK/'armed.json')['process'];observed=process_identity(recorded['pid'])
try:
    raw_stat=Path(f"/proc/{recorded['pid']}/stat").read_text()
    stat_error=None
except OSError as exc:
    raw_stat=None;stat_error=repr(exc)
alive=observed==recorded
# This action records research, not process ownership or dispatch authority.
# An unavailable observation cannot justify either a restart or losing research.
save(ROOT/WORK/'gap-audit-liveness-correction.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
    original_snapshot=ref(ROOT,WORK/'gap-audit-snapshot.json'),recorded=recorded,observed=observed,
    worker_alive=alive,raw_proc_stat=raw_stat,proc_stat_error=stat_error,
    observation_status='MATCHED_PID_START' if alive else 'IDENTITY_NOT_CONFIRMED_BY_THIS_OBSERVER',
    original_liveness_false_cause='Not established; separate PID/start observations and ps have shown the recorded worker alive',
    worker_restarted=False,provider_calls=0))
missionpath=ROOT/DOC/'mission.json'
with missionpath.with_suffix('.execution.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    mission=read(missionpath);require(mission['integration_master']['program']==ref(ROOT,PROGRAM),'Master changed')
    event='product-closure-supplement-2026-10-26'
    require(not any(x['id']==event for x in mission['history']),'Supplement already recorded')
    reason='Continue registered execution; retain the P14 version-and-reliance supplement for fresh combined-answer review at a safe checkpoint. Process observations are retained separately; no redispatch is authorized by this research record.'
    mission['history'].append(dict(id=event,task_id='product-contribution',kind='product_evaluation',outcome='no_advance',
        decision='Recorded source-reviewed P14 supplement and supplemental process observation; cause of inconsistent liveness reports is unestablished. No acceptance or new attempt.',
        next_task='product-contribution',next_task_reason=reason,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        result_evidence=[ref(ROOT,WORK/'p14-assurance-supplement-proof.json'),ref(ROOT,WORK/'gap-audit-liveness-correction.json')]))
    mission['next_task_reason']=reason
    mission['last_product_closure_audit']['p14_supplement']=ref(ROOT,WORK/'p14-assurance-supplement-proof.json')
    mission['last_product_closure_audit']['liveness_correction']=ref(ROOT,WORK/'gap-audit-liveness-correction.json')
    save(missionpath,mission)
print(json.dumps(dict(worker_alive=alive,observed=observed,supplement='SOURCE_REVIEWED_DRAFT_NOT_CONSUMED',provider_calls=0)))
