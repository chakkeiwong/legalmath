"""Inventory authenticated completed calls without dropping failures or history."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, ref, save, require
from legalmath.canonical import digest
WORK = Path(__file__).resolve().parent
OLD = ROOT/'artifacts/legal-mission-control/2026-10-20/common-capacity-interface'

def collect(seed, directory):
    result = deepcopy(read(ROOT/seed['path']))
    result.setdefault('review_groups', {})
    for parent, journal in ((directory/'calls', directory/'calls/dispatch.json'), (directory/'capacity', None)):
        if not parent.exists(): continue
        state = read(journal) if journal and journal.exists() else None
        for request_path in sorted(parent.glob('*/request.json')):
            folder = request_path.parent
            if not (folder/'result.json').exists() or not (folder/'schema.json').exists(): continue
            key = folder.name
            request, outcome = read(request_path), read(folder/'result.json')
            if state is not None and key in state['calls']:
                recorded = state['calls'][key]
                require(recorded['status'] != 'RESERVED' and recorded['result_hash'] == digest(outcome), 'Unsettled checkpoint')
            row = {name:ref(ROOT, folder/(name+'.json')) for name in ('request','schema','result')}
            if state is not None and key in state['calls']: row['dispatch'] = ref(ROOT, journal)
            if request['task'] == 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
                if outcome['status'] == 'VALIDATED' or (folder/'raw.json').exists():
                    if (folder/'raw.json').exists(): row['raw'] = ref(ROOT, folder/'raw.json')
                    result['review_groups'].setdefault(key, row)
                continue
            # Only completed exact successes survive the changed implementation.
            # Failed values remain in the predecessor and are not promoted.
            if outcome['status'] == 'VALIDATED':
                row['mode'] = 'VALIDATED'
                result['calls'][key] = row
    return result

def main():
    program = read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
    old = program['common_capacity']
    report = {}
    for q in ('p10','p14','evidence','gatecoin'):
        value = collect(old['checkpoints'][q], OLD/'live'/q/'product')
        save(WORK/'checkpoints'/(q+'.json'), value)
        arms = dict(old['arm_checkpoints'].get(q, {}))
        if (OLD/'live/arms'/q).exists():
            for path in (OLD/'live/arms'/q).iterdir():
                if path.is_dir(): arms.setdefault(path.name, old['checkpoints'][q])
        report[q] = dict(preparation_calls=len(value['calls']), arms={})
        for arm, seed in arms.items():
            value = collect(seed, OLD/'live/arms'/q/arm)
            save(WORK/'checkpoints/arms'/q/(arm+'.json'), value)
            report[q]['arms'][arm] = dict(exact_calls=len(value['calls']), review_groups=len(value['review_groups']),
                review_assignments=sum(len(read(ROOT/r['request']['path'])['required_considered']) for r in value['review_groups'].values()))
    save(WORK/'reuse-census.json', dict(provider_calls=0, questions=report))
    print(json.dumps(report))

if __name__ == '__main__': main()
