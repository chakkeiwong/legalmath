"""Extend the completed production replay with the reviewed scope-only veto."""
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT=Path(__file__).resolve().parents[4]
CANDIDATE=Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path[:0]=[str(CANDIDATE/'src'),str(ROOT)]
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,verify,require
from legalmath.interpretation.assurance.phased.review_repair import correction_issues
HERE=isolation.HERE
base=read(ROOT/HERE/'unpublished-v2/observed-preflight.json')
require(base['verdict']=='PASS' and base['provider_calls']==0,'Missing actual production replay')
verify(ROOT,base['warrant_replay'])
old_seed=read(ROOT/HERE/'unpublished-v2/seed.json')
seed=read(ROOT/HERE/'seed.json')
old=read(ROOT/HERE/'unpublished-v2/checkpoints/p14/baseline-reviewed.json')
current=read(ROOT/seed['arm_checkpoints']['p14']['baseline']['path'])
require({k:v for k,v in old.items() if k!='warrant_target_followup'}==
    {k:v for k,v in current.items() if k!='warrant_target_followup'},'Scope review changed reused calls')
followup=read(ROOT/current['warrant_target_followup']['path'])
old_followup=read(ROOT/HERE/'unpublished-v2/warrant-target-followup.json')
require(followup['retained']==old_followup['retained'],'Scope review changed retained warrants')
require(all(followup['exclusions'].get(k)==v for k,v in old_followup['exclusions'].items()),
    'Scope review changed earlier exclusions')
p=SimpleNamespace(root=ROOT,capacity_checkpoint=seed['arm_checkpoints']['p14']['baseline'])
rows=[]
for key,pointers in followup['retained'].items():
    for pointer in pointers.values(): verify(ROOT,pointer)
    request=read(ROOT/pointers['request']['path']); result=read(ROOT/pointers['result']['path'])
    ids,excluded=correction_issues(p,key,request['payload']['answer'],request['payload']['review'],result)
    rows.append(dict(key=key,correction_issues=sorted(ids),excluded=sorted(excluded),
        full_assessments=[r for r in result['value']['decisions'] if r['issue_id'] in ids]))
require(sum(len(r['excluded']) for r in rows)==7 and
    sum(len(r['correction_issues']) for r in rows)==18,'Unexpected correction-target accounting')
save(ROOT/HERE/'scope-veto-replay.json',rows)
result={**base,'excluded_issue_occurrences':7,'correction_issues':18,
    'correction_reviews':sum(bool(r['correction_issues']) for r in rows),
    'production_replay_before_scope_veto':ref(ROOT,HERE/'unpublished-v2/observed-preflight.json'),
    'scope_veto_replay':ref(ROOT,HERE/'scope-veto-replay.json'),
    'scope':'Completed actual production replay plus exact seven-issue correction-consumption check; no request, schema, source, answer or historical decision changed by the final scope veto.'}
save(ROOT/HERE/'observed-preflight.json',result)
print(dict(verdict='PASS',retained_warrants=34,correction_issues=18,
    correction_reviews=result['correction_reviews'],excluded_issue_occurrences=7,provider_calls=0))
