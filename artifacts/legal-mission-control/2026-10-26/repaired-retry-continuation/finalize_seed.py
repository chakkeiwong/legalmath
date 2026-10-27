from pathlib import Path
import json,shutil,sys
ROOT=Path('/home/chakwong/python/legalmath');WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import ref,save
seed=json.loads((WORK/'seed.json').read_text())
shutil.copyfile(WORK/'seed.json',WORK/'seed-before-individual-refinement.json')
for q,arms in seed['arm_checkpoints'].items():
    for arm,pointer in arms.items():
        path=ROOT/pointer['path'];value=json.loads(path.read_text())
        if value.get('retry_profile')!='repaired-review-checkpoint.v1':continue
        changed=0
        for key,row in value['calls'].items():
            if row['mode']=='RETAINED_FAILURE' and 'repair-review-' in key and row.get('raw'):
                row['mode']='REVIEWED_FAILURE_RETRY';row.pop('raw')
                value['reviewed_failed_results'].append(row['result']);changed+=1
        if changed:
            save(path,value);arms[arm]=ref(ROOT,path)
            for census in seed['census']:
                if census['question']==q and census['arm']==arm:
                    census['retryable']+=changed
                    census['counts']['AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS / RETAINED_FAILURE']-=changed
                    name='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS / REVIEWED_FAILURE_RETRY'
                    census['counts'][name]=census['counts'].get(name,0)+changed
save(WORK/'seed.json',seed)
print(json.dumps(seed['census'],indent=2))
