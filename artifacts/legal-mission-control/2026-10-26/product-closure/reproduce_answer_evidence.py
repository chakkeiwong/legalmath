from pathlib import Path
from copy import deepcopy
import json, os, sys, tempfile
ROOT=Path('/home/chakwong/python/legalmath')
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tests.assurance.test_corpus_components import setup
from tests.assurance.test_baseline_corpus_repairs import put
from legalmath.interpretation.assurance import corpus_components as part
from legalmath.interpretation.assurance import corpus_review as corpus
from tests.assurance.test_baseline_corpus_repairs import corpus_setup
out=[]
with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    expected,source,answer=setup(root)
    for name,quotes in [('invented_answer_quote_and_pointer',[dict(path='/does_not_exist',quote='fabricated answer passage')]),('missing_answer_evidence',None)]:
        candidate=deepcopy(answer)
        if quotes is None:
            candidate['review']['propositions'][0].pop('answer_evidence',None)
        else:
            candidate['review']['propositions'][0]['answer_evidence']=quotes
        result=part.answer_review(root,expected,candidate['review']['answer'],put(root,name+'.json',candidate))
        out.append(dict(consumer='independent',control=name,qualified=result['qualified']))
    full,bundle=corpus_setup(root)
    bundle['answer_use'][0]['propositions'][0]['answer_evidence']=[dict(path='/missing',quote='fabricated final-answer passage')]
    result=corpus.evaluate(root,full,put(root,'invented-final-review.json',bundle))
    out.append(dict(consumer='final',control='invented_answer_quote_and_pointer',qualified=result['corpus_acceptance_complete']))
assert all(row['qualified'] for row in out),out
value=dict(status='REPRODUCED',provider_calls=0,controls=out,legal_acceptance=False)
target=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure/answer-evidence-omission-reproducer.json'
with target.open('x') as handle:json.dump(value,handle,indent=2)
print(json.dumps(value))
