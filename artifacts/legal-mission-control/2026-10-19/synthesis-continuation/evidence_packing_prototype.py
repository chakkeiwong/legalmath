"""Isolated zero-call reproduction; deliberately not installed in production."""
from pathlib import Path
import json,itertools,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.grouping import pack_items
from scripts.legal_mission_execution import read,save,ref,require
WORK=Path(__file__).resolve().parent
diagnosis=read(WORK/'evidence-capacity-diagnosis.json')
source=ROOT/diagnosis['source']['path'];rows=read(source)
by_members={tuple(x['ids']):x for x in diagnosis['rows']}
def measured(members):
    row=by_members[tuple(x['id'] for x in members)]
    return row.get('measurement') if row['fits'] else None
groups,blocked=pack_items(rows,measured,maximum_items=6)
require(len(groups)==4 and not blocked,'Original greedy failure not reproduced')
pair=None;probes=0
for i,j in itertools.combinations(range(len(rows)),2):
    probes+=1
    receipt=measured([rows[i],rows[j]])
    if receipt is not None:
        pair=(i,j,receipt);break
require(pair is not None,'No feasible exact pair')
i,j,receipt=pair
replacement=[dict(members=[rows[i],rows[j]],measurement=receipt)]+[g for n,g in enumerate(groups) if n not in (i,j)]
flattened=[r for g in replacement for r in g['members']]
require(len(flattened)==len(rows) and {r['id']:digest(r) for r in flattened}=={r['id']:digest(r) for r in rows},'Packing changed members')
require(all(measured(g['members']) is not None for g in replacement),'Proposed group exceeds actual measured capacity')
out=dict(verdict='PASS',source=diagnosis['source'],diagnosis=ref(ROOT,WORK/'evidence-capacity-diagnosis.json'),
    reviewed_plan=ref(ROOT,WORK/'evidence-packing-review.md'),original_groups=4,proposed_groups=len(replacement),
    pair_searches=probes,group_members=[[r['id'] for r in g['members']] for g in replacement],
    all_member_hashes_preserved=True,provider_calls=0,production_code_changed=False,legal_acceptance=False)
save(WORK/'evidence-packing-prototype.json',out);print(json.dumps(out,indent=2))
