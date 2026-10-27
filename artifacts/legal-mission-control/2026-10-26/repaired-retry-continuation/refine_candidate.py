from pathlib import Path
import json,shutil,sys
ROOT=Path('/home/chakwong/python/legalmath');WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import save,ref
path='src/legalmath/interpretation/assurance/phased/review_repair.py'
body=(ROOT/path).read_text()
anchor="        valid, invalid = split_result(product, qid, result, ids, call['request'], raw)"
assert body.count(anchor)==1
body=body.replace(anchor,"""        if raw is None and result['status'] == 'FAILED':
            from .retry_checkpoint import retained_raw
            from .capacity_policy import annotate
            prepared = product.prepare_calls([call])[0]
            raw = retained_raw(product,key,result,annotate(prepared['request']),prepared['schema'])
"""+anchor)
target=WORK/'source'/path;target.write_text(body)
value=json.loads((WORK/'preparation.json').read_text());value['sources'][path]=ref(ROOT,target)
save(WORK/'preparation.json',value)
baseline=json.loads((WORK/'baseline.json').read_text())
held=WORK/'before'/path;held.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,held)
baseline['changed_paths']=sorted(set(baseline['changed_paths'])|{path})
baseline['archived'].append(dict(previous=ref(ROOT,path),archive=ref(ROOT,held)))
save(WORK/'baseline.json',baseline)
shutil.copyfile(WORK/'seed.json',WORK/'seed-first.json')
(WORK/'seed.json').unlink()
shutil.copyfile(WORK/'tests-staged.xml',WORK/'tests-before-malformed-group-reuse.xml')
print('Preserve valid malformed-group siblings; candidate refinement recorded.')
