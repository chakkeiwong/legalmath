from pathlib import Path
from collections import Counter
from legalmath.canonical import loads,digest
from legalmath.interpretation.assurance.checkpoints import CheckpointQueue,check_manifest
from legalmath.interpretation.search.providers import verify_allowance_checkpoint
from legalmath.interpretation.assurance.monitor import save
ROOT=Path('/home/chakwong/python/legalmath')
root=ROOT/'artifacts/interpretation/round9';live=root/'G2/attempt-01/live'
ledger=ROOT/'artifacts/interpretation/round7/live-allowance.json'
study=loads((ROOT/'docs/implementation/interpretation-round9/study.json').read_bytes())
manifest=loads((live/'job-manifests.json').read_bytes());counts=Counter();rows=[]
for job in study['study']['jobs']:
    directory=root/'jobs'/job['blind_id'];check_manifest(directory,manifest[job['blind_id']])
    check_manifest(directory/'method')
    before=loads((directory/'assignment.json').read_bytes())['allowance_before']
    after=loads((directory/'allowance-after.json').read_bytes())
    verify_allowance_checkpoint(ledger,digest(before));verify_allowance_checkpoint(ledger,digest(after))
    row=loads((directory/'scored.json').read_bytes());assert row['calls']==len(after['calls'])-len(before['calls'])
    for p in sorted((directory/'method/queues').glob('*/plan.json')):
        q=CheckpointQueue(p.parent,loads(p.read_bytes()));r=q.report();assert r['execution_complete']
        counts['queues']+=1;counts['validated_tasks']+=r['completed_tasks'];counts['attempts']+=r['attempts']
        for record in q._state()['tasks'].values():
            for attempt in record['attempts']:counts[attempt['status']]+=1
    result=loads((directory/'method/result.json').read_bytes())
    counts['java_cases']+=result['java_cases'];counts['cycles']+=result['cycles']
    rows.append({k:row[k] for k in ('blind_id','case_id','arm','calls') } | {
        'status':row['outcome']['status'],'reference_in_set':row['outcome']['reference_in_candidate_set'],
        'distinct_signatures':row['outcome']['distinct_signatures'],'excess_signatures':row['outcome']['excess_reference_signatures'],
        'behavior_groups':result['behavior_groups'],'java_cases':result['java_cases'],'cycles':result['cycles']})
result={'status':'PASSED','jobs':len(rows),'counts':dict(counts),'rows':rows,
    'allowance_used':len(loads(ledger.read_bytes())['calls']), 'legal_accuracy_evaluated':False,'release_eligible':False}
save(root/'evidence-audit.json',result);print(result)
