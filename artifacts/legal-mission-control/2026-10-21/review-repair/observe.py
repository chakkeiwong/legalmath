"""Observe retained repair state; never dispatch or alter execution authority."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
WORK=Path(__file__).resolve().parent
BASE=ROOT/'artifacts/legal-mission-control/2026-10-13/master'


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observe():
    program=read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
    correction=program['review_repair'].get('timeout_correction') or program['review_repair']['receipt_correction']
    runtime=ROOT/correction['runtime']
    state=read(BASE/'execution-state.json')
    ledger=read(BASE/'live-calls.json')
    seed=read(ROOT/correction['seed']['path'])
    baseline=read(ROOT/correction['baseline']['path'])
    old_state=read(ROOT/correction['prior_state']['path'])
    archived={r['previous']['path']:r['archive'] for r in baseline['archived']}
    old_ledger=read(ROOT/archived[str((BASE/'live-calls.json').relative_to(ROOT))]['path'])
    issues=[]
    old_requests=set()
    for row in seed['files']:
        original,copied=ROOT/row['source']['path'],ROOT/row['copy']['path']
        if fingerprint(original)!=row['source']['sha256']: issues.append('Changed predecessor '+str(original))
        if row['mutable']:
            prior,current=read(original),read(copied)
            for key,value in prior['calls'].items():
                if key==row.get('reviewed_exclusion'):
                    replacement=current['calls'].get(key)
                    if replacement and replacement['identity']!=value['identity']:
                        issues.append('Changed exact timeout request '+key)
                    continue
                if current['calls'].get(key)!=value: issues.append('Changed settled dispatch '+key)
        elif fingerprint(copied)!=row['copy']['sha256']: issues.append('Changed retained file '+str(copied))
        if original.name=='wire-response.json': old_requests.add(read(original)['provenance']['request_hash'])
    for item in seed.get('excluded',[]):
        for row in item['files']+[item['proof']['receipt'],item['proof']['dispatch_result']]:
            if fingerprint(ROOT/row['path'])!=row['sha256']: issues.append('Changed timeout evidence '+row['path'])
    if ledger['calls'][:len(old_ledger['calls'])]!=old_ledger['calls']: issues.append('Changed old charge ledger')
    duplicate=sum(r['request_hash'] in old_requests for r in ledger['calls'][len(old_ledger['calls']):])
    if duplicate: issues.append('Previously settled request recharged')
    for tid,old in old_state['tasks'].items():
        current=state['tasks'][tid]
        if len(current['attempts'])<len(old['attempts']): issues.append('Lost attempts '+tid)
        for a,b in zip(old['attempts'],current['attempts']):
            if any(b.get(k)!=v for k,v in a.items()): issues.append('Changed attempt '+tid)
        if old['status']=='SUCCEEDED' and current!=old: issues.append('Changed successful owner '+tid)
    arms={}
    for path in sorted((runtime/'arms').glob('*/*/calls/dispatch.json')):
        calls=read(path)['calls']
        arms[str(path.parent.parent.relative_to(runtime/'arms'))]={
            'groups':dict(Counter(v['status'] for k,v in calls.items() if k.startswith('audit-group-'))),
            'repairs':dict(Counter(v['status'] for k,v in calls.items() if k.startswith('repair-review-'))),
            'reserved':[k for k,v in calls.items() if v['status']=='RESERVED']}
    circuit=read(WORK/'service/service-circuit.json')
    recovery=read(WORK/'service/service-recovery.json')
    last=recovery['charges'][-1]
    return dict(at_utc=datetime.now(timezone.utc).isoformat(),verdict='PASS' if not issues else 'FAIL',issues=issues,
        worker=read(WORK/'worker.json'),calls=len(ledger['calls']),remaining=ledger['maximum']-len(ledger['calls']),
        running={k:{'attempt':len(v['attempts']),'supervisor':v.get('live_supervisor')}
            for k,v in state['tasks'].items() if v['status']=='RUNNING'},
        arms=arms,circuit_open=circuit['open'],
        circuit_probe_reserved=circuit.get('half_open_reserved',False),
        circuit_probe_request_hash=circuit.get('half_open_request_hash'),
        latest_failed_slot=circuit['failed_slots'][-1] if circuit.get('failed_slots') else None,
        replacements=len(recovery['charges']),
        latest_retry={k:last.get(k) for k in ('failed_slot','next_retry_at_utc','failure_kind')},
        continuation_vetoes=state.get('continuation_vetoes',[]),
        seed_files_checked=len(seed['files']),settled_request_recharges=duplicate,
        terminal={n:read(WORK/(n+'.json')) for n in ('worker-error','live-result','finished') if (WORK/(n+'.json')).exists()},
        provider_calls_from_observer=0,legal_acceptance=False,integration_complete=False)


if __name__=='__main__':
    value=observe()
    target=WORK/'execution-checkpoint.json'
    temporary=target.with_suffix('.observer-tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(target)
    print(json.dumps(value))
