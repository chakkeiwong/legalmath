"""Prepare a versioned answer repair without changing the running answer."""
from pathlib import Path
from copy import deepcopy
from hashlib import sha256
from datetime import datetime,timezone
import json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
from jsonschema import validate
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_product import NOTE
from legalmath.interpretation.assurance.corpus_review import answer_support
def read(path):return json.loads(path.read_text())
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha256(path.read_bytes()).hexdigest())
def put(name,value):
    path=WORK/name
    with path.open('x') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
    return ref(path)
original=read(WORK/'p14-reviewed-answer.json')
note=ROOT/'docs/implementation/legal-mission-control/results/p14-assurance-supplement-2026-10-26.md'
text=note.read_text()
body=text[text.index('The existence of a smart-contract audit'):text.index('## Source and reasoning review')].strip()
candidate=deepcopy(original)
candidate['conclusion']+=chr(10)+chr(10)+body
assert all(candidate[k]==original[k] for k in original if k!='conclusion')
assert candidate['conclusion'].startswith(original['conclusion'])
validate(candidate,NOTE)
candidate_ref=put('p14-assurance-candidate.json',candidate)
reviewed=[
    ('audit existence','The existence of a smart-contract audit does not establish the assurance sought'),
    ('deployed version','there must\nbe evidence connecting what was audited to what was deployed and operated.'),
    ('justified reliance','demonstrate that reliance is reasonable'),
    ('actor qualification',"preserves its where-applicable qualification and the actors' different\nroles"),
    ('unknown facts','If version correspondence,\ncoverage or justified reliance is unknown, that part of the assurance remains\nunestablished.'),
    ('SFC satisfaction','does not, by itself,\nestablish all operational responsibilities, an SFC request, the sufficiency of\nthe entire demonstration, or SFC satisfaction.')
]
# Literal line breaks are retained from the reviewed prose.
checks=[]
for obligation,quote in reviewed:
    quote=quote.replace('\n',chr(10))
    answer_support(candidate,[dict(path='/conclusion',quote=quote)])
    checks.append(dict(distinction=obligation,answer_evidence=dict(path='/conclusion',quote=quote)))
case=[c for c in read(ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/complete-handbook-envelope.json')['answer_acceptance']['cases'] if c['case_id']=='p14-audit-confidence'][0]
result=dict(at_utc=datetime.now(timezone.utc).isoformat(),status='REVIEW_READY_NOT_ACTIVATED',
    original_answer=ref(WORK/'p14-reviewed-answer.json'),candidate=candidate_ref,
    original_case=case,original_fields_preserved=True,prior_conclusion_preserved=True,
    source_review=ref(WORK/'p14-assurance-supplement-proof.json'),supplement=ref(note),
    answer_schema='PASS',exact_passage_attribution=checks,
    remaining=['Fresh source-grounded combined-answer review',
        'Registered activation with new answer identity at a safe checkpoint',
        'Original answer-specific review population and comparison fairness'],
    provider_calls=0,legal_acceptance=False)
put('p14-assurance-candidate-review.json',result)
print(json.dumps({k:result[k] for k in ('status','answer_schema','remaining','provider_calls')}))
