"""Versioned review of the eight traced original objections; no live calls."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib,json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import ContextRoute,Limits,tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from legalmath.interpretation.assurance.phased import current_issue_disposition as issue
from scripts.legal_integration_master import TOKENIZER
def read(p):return json.loads(p.read_text())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(name,v):
    with (WORK/name).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
packet=read(WORK/'p14-review-packet.json');census=read(WORK/'p14-current-issue-census.json')
value=deepcopy(read(WORK/'p14-current-dispositions-v2.json'));answer=packet['answer'];support=answer['support']
rows={r['id']:r for r in value['dispositions']}
callbase=ROOT/'artifacts/legal-mission-control/2026-10-23/p14-optional-quote/live/arms/p14/baseline/calls'
proofs=[];evidence=[]
for suffix,alias,original in [('5e592fdc0b87f2e52af10cd4','r18','dependency-d5f02808b1484834c7e2811f'),
        ('65a02da91b8df7cb99ffa73b','r19','dependency-dbe394357dbd13abca92037d')]:
    path=callbase/('audit-context-disposition-p14-'+suffix)/'reference-binding.json';b=read(path)
    p=b['request']['payload'];c=p['assignment_correspondence']
    assert b['aliases'][alias]==original and p['item']['id']==alias
    assert c['original_assignment_id']==original and c['delivered_item']['id']==alias
    assert c['required_considered']==[alias]
    assert b['schema']['properties']['considered']['properties']['c0']['enum']==[alias]
    proofs.append(dict(original=original,alias=alias,correspondence=c,evidence=ref(path)))
    evidence.append(ref(path))
for suffix in ('dff7fe2559b51c9d7adf5f8c','8ab9df39ee57260fd98a3b54'):
    evidence.append(ref(callbase/('audit-context-disposition-p14-'+suffix)/'request.json'))
ownership=ROOT/'artifacts/legal-mission-control/2026-10-13/master/ownership-handbook/attempt-3/handbook-ownership.json'
owned=read(ownership);assert owned['clauses'][5]['label']=='1.6' and owned['clauses'][11]['label']=='1.12'
evidence += [ref(ownership),ref(WORK/'p14-current-issue-census.json')]
storepath=ROOT/'artifacts/legal-mission-control/2026-10-21/review-repair/recovered-live/arms/p14/baseline/source-store.json'
store=load_exact(storepath);evidence.append(ref(storepath))
handbook=[]
for page in (7,8,9):
    k='source:handbook.oct2024.page'+str(page)+':0';record=store[k]
    handbook.append(dict(record_id=k,locator='',quote=record['text']))
def replace(ids,kind,reason,indices=(0,1),path='/conclusion',quote=None,premise=False,extra=None):
    for identity in ids.split():
        assert rows[identity]['disposition']=='STILL_REQUIRED'
        row=dict(id=identity,disposition=kind,reason=reason,blocking_source_gaps=[],
            support=extra or [support[i] for i in indices],
            answer_evidence=dict(path=path,quote=quote or answer['conclusion']))
        if premise:row['necessary_premises']=[dict(description='No actual fulfillment, applicability or ownership is established.',
            answer_evidence=dict(path='/unresolved/3',quote=answer['unresolved'][3]))]
        rows[identity]=row
replace('13:issue-1','SUPPORTED_BY_REVIEWED_SOURCE',
    'Full retained Handbook OPS 1.6 across pages 7–8 and OPS 1.12 on page 9 support this bounded statement. Supplemental review support does not alter the fixed answer or pretend its inline citation list has changed.',
    quote='The Handbook material distinguishes regulatory consequences from automatic liability and authorization from proof of compliance.',extra=handbook)
replace('1023:issue-0 1033:issue-0 1033:issue-1','NOT_APPLICABLE_TO_CURRENT_ANSWER',
    'Exact retained wire request, alias table, assignment_correspondence and output schema all identify the same dependency/selector. The model returned the same selector. The allegation of missing association is contradicted by implementation evidence; no display-order assumption or legal conclusion is made.',
    quote='The preferred reading separates confirmation from request-triggered demonstration.')
replace('1061:issue-1','NOT_APPLICABLE_TO_CURRENT_ANSWER',
    'The original typed need incorrectly names intermediary index 26872a04 P10/FN1. Preserve that request as malformed, not supplied through substitution. The actual answer explicitly supports Provider responsibility with product index 12219d32 P10/FN1, whose records are distinct and checked. This disposition concerns the answer proposition only.',
    indices=(4,8),quote='retained Provider responsibility despite outsourcing')
replace('1248:issue-1','CONDITIONALLY_ADDRESSED',
    'Product P10–P16 and FN1–FN5, the intermediary risk passage and appendix are supplied and cited in the fixed answer. Remaining incorporated-material limits apply to a complete compliance analysis; the answer does not claim such completeness.',
    indices=(0,1,2,3,4,5,6,7,8,9,10,11,12,13,17,18),path='/unresolved/2',quote=answer['unresolved'][2],premise=True)
replace('1248:issue-2','NOT_APPLICABLE_TO_CURRENT_ANSWER',
    'The exact prior REVIEW_QUESTION itself says the judicial scenario tension lies outside the answer and no judicial ownership rule is imported. This answer preserves that scope and establishes neither supervision adequacy nor proper-record fulfillment. The separate obligations remain unfulfilled pending their own evidence.',
    path='/assumptions/1',quote=answer['assumptions'][1])
replace('1410:issue-0','NOT_APPLICABLE_TO_CURRENT_ANSWER',
    'The source assignment is an incomplete Handbook custody-actor list, while the typed continuation need points to product P14/P15. That mismatch cannot prove custody compliance. The actual attachment interpretation is supported by correct product P14/FN5/P15/P16 and does not infer fulfillment from the fragment.',
    indices=(0,1,2,3),path='/unresolved/3',quote=answer['unresolved'][3])
save('p14-residual-proof.json',dict(mapping_proofs=proofs,evidence=evidence,provider_calls=0,legal_acceptance=False))
note=ROOT/'docs/implementation/legal-mission-control/results/p14-residual-review-2026-10-26.md'
value['review_note']=ref(note);value['reviewed_evidence']=[ref(WORK/'p14-residual-proof.json'),*evidence]
value['dispositions']=[rows[r['id']] for r in value['dispositions']]
checkpoint=read(ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/checkpoints/p14/baseline.json')
fixed=read(ROOT/checkpoint['fixed_correction']['path']);held=load_exact(ROOT/fixed['answers']['path'])['p14']['correction']
envelope=read(ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/complete-handbook-envelope.json')
product=BoundedProduct.__new__(BoundedProduct);product.root=ROOT
product.route=ContextRoute(envelope,tokenizer(ROOT/TOKENIZER),limits=Limits());product.active_questions=['p14']
outcome=issue.validate(product,'p14',packet['question'],held['original_answer']['value'],answer,
    held['corrected_requirement_details'],census['reviews'],census['assessments'],value)
save('p14-current-dispositions-v3.json',value)
save('p14-current-disposition-result-v3.json',dict(**outcome,counts=dict(Counter(r['disposition'] for r in rows.values())),
    evidence=[ref(note),ref(WORK/'p14-current-dispositions-v3.json'),ref(WORK/'p14-residual-proof.json')],provider_calls=0,
    original_answer_unchanged=True,activation='PENDING_REVIEWED_BINDING'))
checkpoint['current_answer_issue_dispositions']={'p14':ref(WORK/'p14-current-dispositions-v3.json')}
save('p14-checkpoint-v3.json',checkpoint)
print(json.dumps(dict(issue_count=outcome['issue_count'],pending=len(outcome['pending']),legal_acceptance=False)))
