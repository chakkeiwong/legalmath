"""Record the checked execution order without changing the registered graph."""
from datetime import datetime,timezone
import fcntl
from pathlib import Path
import sys
ROOT=Path('/home/chakwong/python/legalmath')
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import read,save,ref,verify,require

DOC=Path('docs/implementation/legal-mission-control')
HERE=Path('artifacts/legal-mission-control/2026-10-23/p14-corrected-context')
WORK=HERE/'requested-owner'
identity='p14-requested-owner-continuation-2026-10-23'
with (ROOT/DOC/'mission.execution.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    mission=read(ROOT/DOC/'mission.json')
    require(mission['current_task']=='product-contribution','Different admitted task')
    if not any(r['id']==identity for r in mission['history']):
        operation=read(ROOT/WORK/'operation.json')
        for pointer in operation['evidence']: verify(ROOT,pointer)
        require(read(ROOT/WORK/'handover.json')['supervisor_ended'],'Incomplete handover')
        state=read(ROOT/'artifacts/legal-mission-control/2026-10-13/master/execution-state.json')
        worker=read(ROOT/WORK/'worker.json')
        require(state['tasks']['baseline-p14']['live_supervisor']==worker['process']
                and len(state['tasks']['baseline-p14']['attempts'])==5,'P14 continuation not adopted')
        snapshot=dict(at_utc=datetime.now(timezone.utc).isoformat(),worker=worker,
                      p14_status=state['tasks']['baseline-p14']['status'],p14_attempts=5,
                      program=ref(ROOT,DOC/'integration-master.json'),
                      binding=ref(ROOT,'artifacts/legal-mission-control/2026-10-13/master/current-binding.json'),
                      legal_acceptance=False)
        save(ROOT/WORK/'adopted-checkpoint.json',snapshot)
        source=ROOT/DOC/'mission.json'
        with (ROOT/WORK/'before/mission-before-order-note.json').open('xb') as out:
            out.write(source.read_bytes())
        reason=('P14 attempt 5 has adopted the checked selected-owner supervisor. Continue its original '
                'need dispositions and supported correction, then retained Gatecoin attempts and the '
                'independent ready frontier. No attempt, call allowance, deadline or verdict was reset.')
        pointers=[ref(ROOT,p) for p in (WORK/'operation.json',WORK/'handover.json',
            WORK/'settled-state-archives.json',WORK/'adopted-checkpoint.json',
            HERE/'fn4-delivery-diagnostic.json',HERE/'fn4-context-coverage.json')]
        mission['history'].append(dict(id=identity,task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',recorded_at_utc=snapshot['at_utc'],
            decision='Checked execution handover resumes requested P14 work before independent tool queues; all existing work is retained.',
            next_task='product-contribution',next_task_reason=reason,result_evidence=pointers))
        mission['next_task_reason']=reason
        save(source,mission)
        print('Recorded selected P14 continuation; graph and cumulative authority unchanged.')
    else:
        print('Selected P14 continuation already recorded.')
