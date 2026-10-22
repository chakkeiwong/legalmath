"""Inspect failed085 source index without changing or retrying its candidate."""
from datetime import datetime, timezone
import time
from scripts import prospectus_reference_address_projection as run
from legalmath.prospectus.successor import reference_addresses as module

started=time.monotonic()
folder=run.HERE/'stages/diagnostic';assert not (folder/'result.json').exists()
products,old=run.previous.baseline()
text,pieces,raw,nodes,issues=module.source_model(products,old)
groups=module.compound_groups(text,old['reference_scope_context']['contexts'],
    old['paragraph_reference_discovery']['discovery']['candidates'])
expected=run.read(run.PREP/'expected.json')
differences=[]
for group,wanted in zip(groups,expected['references']):
    row=module.resolve(group,nodes)
    if wanted['statute']:
        assert row['status']=='EXTERNAL_STATUTE';continue
    target_expected=[expected['targets'][i] for i in wanted['target_indices']]
    if row['status']!='STRUCTURAL_ADDRESS':
        differences.append({'source':wanted['paragraph_starts'],'result':row})
        continue
    comparisons=[{k:{'actual':actual.get(k),'expected':value} for k,value in want.items() if actual.get(k)!=value}
        for actual,want in zip(row['targets'],target_expected)]
    if len(row['targets'])!=len(target_expected) or any(comparisons):
        differences.append({'source':wanted['paragraph_starts'],'comparisons':comparisons,
            'actual_target_count':len(row['targets']),'expected_target_count':len(target_expected)})
issue_pieces=[p for p in pieces if any(i['start']==p['start'] for i in issues)]
result={'status':'PASS','diagnostic_only':True,'candidate_accepted':False,'index_issues':issues,
    'issue_pieces':issue_pieces,'remaining_address_differences':differences,
    'warning':'Calling resolve separately diagnoses later differences; it does not bypass the production refusal for acceptance',
    'command':['.venv/bin/python','-m','scripts.prospectus_reference_address_projection_diagnostic'],
    'finished_at':datetime.now(timezone.utc).isoformat(),'wall_seconds':time.monotonic()-started}
run.save(folder/'result.json',result)
print({'index_issues':issues,'remaining_address_differences':differences,
    'issue_text':[p['text'] for p in issue_pieces],'wall_seconds':result['wall_seconds']})
