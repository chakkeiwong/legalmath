"""Preserve the unsupported annual-report warrant without authorizing correction."""
from pathlib import Path
from copy import deepcopy
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,require,digest
HERE=isolation.HERE
require(not (ROOT/HERE/'registration.json').exists(),'Published successor cannot be revised')
for name in ('warrant-target-followup.json','seed.json','checkpoints/p14/baseline-reviewed.json','observed-preflight.json'):
    source=ROOT/HERE/name
    if not source.exists(): continue
    target=ROOT/HERE/'unpublished-v2'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f: f.write(source.read_bytes())
followup=read(ROOT/HERE/'warrant-target-followup.json')
folder=ROOT/isolation.SOURCE/'arms/p14/baseline'
population=read(folder/'contextual-group-review-p14.json')['reviews']
assessment=next(r for r in read(folder/'early-warrants-p14.json')['assessed'] if r['review_index']==1463)
matches=[key for key,pointers in followup['retained'].items() if read(ROOT/pointers['result']['path'])==assessment['result']]
require(len(matches)==1,'Annual-report warrant is not exact')
key=matches[0]; pointers=followup['retained'][key]
request=read(ROOT/pointers['request']['path']); result=assessment['result']
require(request['payload']['review']==population[1463]['value'] and
    request['question']['question_id']=='p14' and
    result['value']['decisions'][0]['disposition']=='WARRANTED','Changed reviewed scope evidence')
followup['exclusions'][key]=dict(result=pointers['result'],value_hash=digest(result['value']),
    answer_hash=digest(request['payload']['answer']),review_hash=digest(request['payload']['review']),
    issue_ids=['issue-0'],review_index=1463,full_assessments=result['value']['decisions'],
    disposition='EXCLUDE_FROM_ANSWER_CORRECTION_ONLY',
    reason='The warrant demands analysis of a separate annual-report passage without identifying an incorrect answer statement or establishing its necessity to P14. The actual question concerns request trigger, objects and standards in paragraph 14/footnote 5 and paragraphs 15–16. The assigned source reading says the passage does not resolve that question. Preserve adverse evidence and unresolved relevance; no automatic answer correction or acceptance.',
    question=deepcopy(request['question']),assigned_review_targets=deepcopy(request['payload']['assigned_review_targets']))
followup.update(excluded_issue_occurrences=7,review=ref(ROOT,isolation.REVIEW))
save(ROOT/HERE/'warrant-target-followup.json',followup)
seed=read(ROOT/HERE/'seed.json')
checkpoint_path=seed['arm_checkpoints']['p14']['baseline']['path']
checkpoint=read(ROOT/checkpoint_path)
checkpoint['warrant_target_followup']=ref(ROOT,HERE/'warrant-target-followup.json')
save(ROOT/checkpoint_path,checkpoint)
seed.update(warrant_target_followup=ref(ROOT,HERE/'warrant-target-followup.json'))
seed['arm_checkpoints']['p14']['baseline']=ref(ROOT,checkpoint_path)
save(ROOT/HERE/'seed.json',seed)
print(dict(excluded_issue_occurrences=7,retained_warrants=34,provider_calls=0,historical_verdicts_unchanged=True))
