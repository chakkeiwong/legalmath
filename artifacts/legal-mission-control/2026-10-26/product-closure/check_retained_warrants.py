"""Actual retained inputs, zero dispatch, exact disposition validation."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
from legalmath.interpretation.assurance.bounded_context import ContextRoute,Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from legalmath.interpretation.assurance.phased import current_issue_disposition as issue
from scripts.legal_integration_master import TOKENIZER
def read(p):return json.loads(p.read_text())
packet=read(WORK/'p14-review-packet.json')
checkpoint=read(WORK/'p14-checkpoint-v3.json')
fixed=read(ROOT/checkpoint['fixed_correction']['path'])
held=load_exact(ROOT/fixed['answers']['path'])['p14']['correction']
envelope=read(ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/complete-handbook-envelope.json')
product=BoundedProduct.__new__(BoundedProduct);product.root=ROOT
product.route=ContextRoute(envelope,tokenizer(ROOT/TOKENIZER),limits=Limits())
product.active_questions=['p14']
valid=[r for r in held['original_reviews'] if r.get('status')=='VALIDATED']
result=issue.validate(product,'p14',packet['question'],held['original_answer']['value'],
    held['candidate']['value'],held['corrected_requirement_details'],valid,held['review_warrants'],
    read(WORK/'p14-current-dispositions-v3.json'))
out=dict(at_utc=datetime.now(timezone.utc).isoformat(),verdict='PASS',
    original_valid_reviews=len(valid),retained_assessments=len(held['review_warrants']),
    issue_count=result['issue_count'],pending=len(result['pending']),
    provider_calls=0,fresh_reviews_still_required=True,legal_acceptance=False)
with (WORK/'retained-warrant-real-input-result.json').open('x') as stream:json.dump(out,stream,indent=2)
print(json.dumps(out))
