"""Report current P14 continuation without confusing predecessor labels."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import legal_optional_quote_validation as repair
from scripts.legal_mission_execution import read,ref,save,require

def main():
    census_path=Path('artifacts/legal-mission-control/2026-10-23/p14-corrected-context/decision-progress/20261023T095930474794Z.json')
    replay_path=repair.HERE/'deployment-replay/b0fa3511df191f32/result.json'
    census,replay=read(ROOT/census_path),read(ROOT/replay_path)
    rows={row['assignment']:dict(assignment=row['assignment'],population=row['population'],
        status='PENDING',evidence=None,basis='NO_COMPLETED_CONTINUATION') for row in census['rows']}
    require(len(rows)==696,'Changed continuation population')
    for row in replay['rows']:
        status=row.get('installed',{}).get('status',row['stored_status'])
        target=rows[row['assignment']]
        target.update(status=status,evidence=row['receipt'],basis='SETTLED_OFFLINE_REVALIDATED')
        if status=='VALIDATED':target['verdict']=row['stored_verdict']
        else:target['failure']=row.get('installed',row.get('retained_failure',{}))
    active=[]
    runtime=ROOT/repair.RUNTIME/'arms/p14/baseline'
    for path in sorted(runtime.glob('context-review-*.json')):
        receipt=read(path);identity=receipt['item']['id'];require(identity in rows,'Unknown successor assignment')
        result=receipt['result'];target=rows[identity]
        target.update(status=result['status'],evidence=ref(ROOT,path),basis='CURRENT_RUNTIME')
        target.pop('verdict',None);target.pop('failure',None)
        if result['status']=='VALIDATED':target['verdict']=result['value']['verdict']
        else:target['failure']={k:result.get(k) for k in ('error','reason')}
        active.append(identity)
    journal=runtime/'calls/dispatch.json'
    dispatch=read(journal) if journal.exists() else {'calls':{}}
    ledger=read(ROOT/repair.BASE/'live-calls.json')
    service=ROOT/Path(read(ROOT/repair.BASE/'current-binding.json')['phase_service_scope']['path']).parent
    recovery=read(service/'service-recovery.json')
    state=read(ROOT/repair.STATE)
    result=dict(at_utc=datetime.now(timezone.utc).isoformat(),total=len(rows),
        statuses=dict(Counter(r['status'] for r in rows.values())),
        valid_verdicts=dict(Counter(r['verdict'] for r in rows.values() if 'verdict' in r)),
        current_runtime_receipts=len(active),
        current_runtime_dispatches=dict(Counter(r['status'] for r in dispatch['calls'].values())),
        calls=len(ledger['calls']),call_ceiling=ledger['maximum'],
        recovery_charges=len(recovery['charges']),recovery_ceiling=recovery['maximum'],
        selected_tasks={tid:{k:state['tasks'][tid].get(k) for k in ('status','live_supervisor','reason')} for tid in repair.SELECTED},
        predecessor_census=ref(ROOT,census_path),strict_replay=ref(ROOT,replay_path),
        original_decisions_unchanged=True,legal_acceptance=False,rows=list(rows.values()))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=repair.HERE/'progress'/(stamp+'.json');save(ROOT/path,result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}|{'report':str(path)},indent=2))

if __name__=='__main__':main()
