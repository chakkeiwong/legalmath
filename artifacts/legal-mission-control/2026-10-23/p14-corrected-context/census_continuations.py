"""Preserve the exact new decision population separately from the original census."""
from pathlib import Path
from collections import Counter
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,require
HERE=isolation.HERE
seed=read(ROOT/HERE/'seed.json')
calls=[r for r in seed['imported'] if r['key'].endswith('-contract-continuation')]
require(len(calls)==52 and all(r['status']=='VALIDATED' for r in calls),'Incomplete continuation population')
assignments={}
for r in calls:
    request=read(ROOT/r['request']['path'])
    identity,=request['required_considered']
    require(identity not in assignments,'Repeated new continuation target')
    assignments[identity]=r
population_path=isolation.SOURCE/'arms/p14/baseline/contextual-group-review-p14.json'
population=read(ROOT/population_path)['reviews']
rows=[dict(index=i,assignment=r['value']['considered'][0],decision=r['value'],
    exact_call=assignments[r['value']['considered'][0]])
    for i,r in enumerate(population) if r['value']['considered'][0] in assignments]
require(len(rows)==52,'New population alignment differs')
save(ROOT/HERE/'continuation-decisions.json',rows)
summary=dict(total=52,verdicts=dict(Counter(r['decision']['verdict'] for r in rows)),
    unresolved_need_combinations=dict(Counter('+'.join(sorted({n['kind'] for n in r['decision'].get('context_needs',[])}))
        or 'UNTYPED' for r in rows if r['decision']['verdict']=='UNRESOLVED')),
    rejection_issue_occurrences=sum(len(r['decision']['issues']) for r in rows if r['decision']['verdict']=='REJECT'),
    population_verdicts=dict(Counter(r['value']['verdict'] for r in population)),
    population=ref(ROOT,population_path),delta=ref(ROOT,HERE/'continuation-decisions.json'),
    historical_verdicts_unchanged=True,legal_acceptance=False)
save(ROOT/HERE/'continuation-census.json',summary)
print(summary)
for row in rows:
    if row['decision']['verdict']!='ACCEPT':
        print(dict(index=row['index'],verdict=row['decision']['verdict'],reason=row['decision']['reason'],
            queries=[n['query'] for n in row['decision'].get('context_needs',[])]))
