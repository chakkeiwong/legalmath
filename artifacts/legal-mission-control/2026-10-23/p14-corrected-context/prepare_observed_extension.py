"""Preserve the unpublished package and enumerate the checked non-answer issues."""
from pathlib import Path
from copy import deepcopy
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from scripts.legal_mission_execution import read,save,ref,verify,require,digest
from scripts import legal_review_context_isolation as isolation
HERE=isolation.HERE
require(not (ROOT/HERE/'registration.json').exists(),'Cannot extend a published successor')
for name in ('candidate-source.json','deployment-tests.xml','local-result.json','installation-manifest.json',
        'seed.json','checkpoints/p14/baseline.json','deployment-review.md'):
    path=ROOT/HERE/name
    target=ROOT/HERE/'unpublished-v1'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream: stream.write(path.read_bytes())
extra='src/legalmath/interpretation/assurance/phased/review_repair.py'
archive=HERE/'before'/extra
(ROOT/archive).parent.mkdir(parents=True,exist_ok=True)
with (ROOT/archive).open('xb') as stream: stream.write((ROOT/extra).read_bytes())
save(ROOT/HERE/'additional-before.json',dict(archived=[dict(previous=ref(ROOT,extra),archive=ref(ROOT,archive))]))
folder=ROOT/isolation.SOURCE/'arms/p14/baseline'
population=read(folder/'contextual-group-review-p14.json')['reviews']
assessed=read(folder/'early-warrants-p14.json')['assessed']
journal=read(folder/'calls/dispatch.json')
retained={}
for key,row in journal['calls'].items():
    if not key.startswith('warrant-'): continue
    path=folder/'calls'/key
    request,result=read(path/'request.json'),read(path/'result.json')
    require(row['status']==result['status']=='VALIDATED' and row['result_hash']==digest(result),'Invalid retained warrant')
    retained[key]=dict(request=ref(ROOT,path/'request.json'),result=ref(ROOT,path/'result.json'))
selected={115:['issue-0','issue-1'],116:['issue-1'],509:['issue-0'],517:['issue-0'],519:['issue-0']}
exclusions={}
for index,ids in selected.items():
    assessment=next(a for a in assessed if a['review_index']==index)
    matches=[key for key,pointers in retained.items() if read(ROOT/pointers['result']['path'])==assessment['result']]
    require(len(matches)==1,'Ambiguous exact warrant')
    key=matches[0]; request=read(ROOT/retained[key]['request']['path']); result=assessment['result']
    require(request['payload']['review']==population[index]['value'],'Warrant target differs from population')
    rows=[r for r in result['value']['decisions'] if r['issue_id'] in ids]
    require(len(rows)==len(ids) and all(r['disposition']=='WARRANTED' for r in rows),'Wrong reviewed issue')
    exclusions[key]=dict(result=retained[key]['result'],value_hash=digest(result['value']),
        review_hash=digest(request['payload']['review']),answer_hash=digest(request['payload']['answer']),
        issue_ids=ids,review_index=index,full_assessments=rows,
        disposition='EXCLUDE_FROM_ANSWER_CORRECTION_ONLY',
        reason='The inspected full assessment supports a criticism of an unnecessary dependency and states no defect in the answer. Historical verdict remains unchanged.')
followup=dict(profile='reviewed-warrant-target-followup.v1',retained_warrant_keys=sorted(retained),
    retained=retained,exclusions=exclusions,excluded_issue_occurrences=sum(map(len,selected.values())),
    provider_calls=0,legal_acceptance=False,review=ref(ROOT,isolation.REVIEW))
save(ROOT/HERE/'warrant-target-followup.json',followup)
seed=read(ROOT/HERE/'unpublished-v1/seed.json')
checkpoint=read(ROOT/seed['arm_checkpoints']['p14']['baseline']['path'])
checkpoint['warrant_target_followup']=ref(ROOT,HERE/'warrant-target-followup.json')
target=HERE/'checkpoints/p14/baseline-reviewed.json'
save(ROOT/target,checkpoint)
seed['arm_checkpoints']['p14']['baseline']=ref(ROOT,target)
seed['warrant_target_followup']=ref(ROOT,HERE/'warrant-target-followup.json')
save(ROOT/HERE/'seed.json',seed)
print({'retained_warrants':len(retained),'excluded_issue_occurrences':sum(map(len,selected.values())),
    'prior_provider_calls_preserved':len(seed['imported']),'provider_calls':0})
