"""Retain current master evidence, exact issue populations and protected resources."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
from legalmath.canonical import digest
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from legalmath.interpretation.assurance.phased.current_issue_disposition import census
def read(p):return json.loads((ROOT/p).read_text())
def ref(p):return dict(path=str(p),sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
def save(name,value):
    with (WORK/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
base=Path('artifacts/legal-mission-control/2026-10-13/master')
program=read('docs/implementation/legal-mission-control/integration-master.json')
state=read(base/'execution-state.json');binding=read(base/'current-binding.json');calls=read(base/'live-calls.json')
budget=read(binding['execution_budget']['path'])
save('resource-inventory.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
    calls=len(calls['calls']),remaining=calls['maximum']-len(calls['calls']),
    budget=budget,task_counts=dict(Counter(r['status'] for r in state['tasks'].values())),
    tasks=[dict(id=t['id'],requires=t['requires'],after=t['after'],maximum_attempts=t['maximum_attempts'],
        status=state['tasks'][t['id']]['status'],attempts=len(state['tasks'][t['id']]['attempts']),
        reason=state['tasks'][t['id']].get('reason')) for t in program['tasks']],
    program=ref('docs/implementation/legal-mission-control/integration-master.json'),
    live_snapshot_only=True,legal_acceptance=False))
checkpoint=read('artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/checkpoints/p14/baseline.json')
fixed=read(checkpoint['fixed_correction']['path']);held=load_exact(ROOT/fixed['answers']['path'])['p14']['correction']
reviews=[r for r in held['original_reviews'] if r.get('status')=='VALIDATED']
assessments=[]
for old in held['review_warrants']:
    original=held['original_reviews'][old.get('original_review_index',old.get('review_index'))]
    candidates=[i for i,r in enumerate(reviews) if digest(r)==old['original_review_hash']]
    assert len(candidates)==1
    assessments.append({**old,'review_index':candidates[0]})
rows=census(reviews,assessments)
save('p14-current-issue-census.json',dict(profile='current-answer-issue-census.v1',
    question=fixed['question'],original_answer_hash=digest(held['original_answer']['value']),
    current_answer_hash=digest(held['candidate']['value']),issue_population_hash=digest(rows),
    answer_reference=fixed['answers'],reviews=reviews,assessments=assessments,issues=rows,
    classifications=dict(Counter((r['prior_assessment'] or {}).get('disposition','INVALID_ASSESSMENT') for r in rows)),
    status='NEEDS_EXPLICIT_CURRENT_ANSWER_REVIEW',legal_acceptance=False))
save('p14-review-packet.json',dict(question=fixed['question'],answer=held['candidate']['value'],
    issues=[{**r,'original_review':reviews[r['review_index']]['value']} for r in rows],
    instruction='Review every issue against this fixed answer; preserve material uncertainty and necessary missing evidence.'))
print(json.dumps(dict(calls=len(calls['calls']),p14_issues=len(rows),
    dispositions=dict(Counter((r['prior_assessment'] or {}).get('disposition','INVALID_ASSESSMENT') for r in rows)))))
