"""Review retained Gatecoin cases independently of its running general audit."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1';sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.canonical import digest
from legalmath.interpretation.assurance import corpus_components as part
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
def read(p):return json.loads(p.read_text())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(n,v):
    with (WORK/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
    return ref(WORK/n)
expected=read(WORK/'corpus-context.json')
checkpoint=read(ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/checkpoints/gatecoin/baseline.json')
origin=checkpoint['calls']['answer-gatecoin']['result'];response=load_exact(ROOT/origin['path'])
assert response['status']=='VALIDATED';answer=response['value']
answerref=save('gatecoin-reviewed-answer.json',answer)
owned={}
for year in ('2023','2025'):
    path=ROOT/('artifacts/legal-mission-control/2026-10-13/master/ownership-'+year+'/attempt-3/ownership.json')
    owned[year]=(read(path),ref(path))
def source(year,collection,index):
    ownership,pointer=owned[year];row=ownership[collection][index]
    return dict(source_id=year,source=expected['sources'][year],passage=pointer,
        passage_pointer='/'+collection+'/'+str(index)+'/text',locator=row.get('locator') or row['owner'],quote=row['text'])
def ev(path,quote):
    x=answer
    for k in path.split('/')[1:]:x=x[int(k)] if isinstance(x,list) else x[k]
    assert quote in x;return dict(path=path,quote=quote)
props=[dict(id='cases:gatecoin-property-trust',status='SUPPORTED',source_ids=['2023'],
    reason='Property capacity is expressly separated from actual trust and objective terms; the Non-consenting Customer exception remains.',
    primary_evidence=[source('2023','main_paragraphs',58),source('2023','main_paragraphs',59),source('2023','full_components',235)],
    answer_evidence=[ev('/conclusion','An actual express trust still requires certainty of subject matter, beneficiaries and intention.')]),
    dict(id='cases:gatecoin-event-timing',status='SUPPORTED',source_ids=['2025'],
    reason='Later entries do not prove instruction, access or assent; automatic credits and earlier orders remain distinct and exceptions are bounded.',
    primary_evidence=[source('2025','full_components',38),source('2025','full_components',39),source('2025','full_components',47)],
    answer_evidence=[ev('/alternatives/0/consequence',answer['alternatives'][0]['consequence']),
        ev('/alternatives/1/consequence',answer['alternatives'][1]['consequence']),ev('/alternatives/2/consequence',answer['alternatives'][2]['consequence'])]),
    dict(id='cases:gatecoin-scenario-seven',status='SUPPORTED',source_ids=['2025'],
    reason='The current answer explicitly preserves the absence-of-factual-basis treatment beside the broader conditional grouping. This satisfies preservation only; the conflict remains unresolved.',
    primary_evidence=[source('2025','full_components',40),source('2025','full_components',48),source('2025','full_components',303)],
    answer_evidence=[ev('/unresolved/1',answer['unresolved'][1])]),
    dict(id='cases:gatecoin-party-transfer',status='SUPPORTED',source_ids=['2025'],
    reason='Dan–Samara and Gatecoin–Samara are separated; transfer to the Provider requires matching material premises and does not establish compliance.',
    primary_evidence=[source('2025','full_components',228),source('2025','full_components',309)],
    answer_evidence=[ev('/conclusion',"Dan's fiduciary obligations and trust relationship with Samara did not establish a direct trust owed by Gatecoin."),
        ev('/alternatives/4/consequence',answer['alternatives'][4]['consequence'])])]
assert {p['id'] for p in props}==set(expected['required_propositions']['gatecoin'])
review=save('corpus-gatecoin-answer-review.json',dict(profile=part.PROFILE,kind='answer',context_hash=digest(expected),
    scope=expected['scope'],as_of=expected['as_of'],reviewer='Codex: exact retained-answer original-case review, October 26 2026',
    review_note=ref(ROOT/'docs/implementation/legal-mission-control/results/gatecoin-answer-use-review-2026-10-26.md'),
    review=dict(question='gatecoin',answer=answerref,propositions=props)))
result=part.answer_review(ROOT,expected,answerref,review)
save('corpus-gatecoin-answer-result.json',dict(**result,provider_calls=0,original_answer_hash=digest(answer),origin=origin))
manifest=deepcopy(read(WORK/'corpus-components-with-p14.json'));manifest['answers']['gatecoin']=dict(answer=answerref,review=review)
manifestref=save('corpus-components-two-answers.json',manifest)
registration=dict(expected_context=ref(WORK/'corpus-context.json'),components=manifestref)
aggregate=part.consume(ROOT,registration,fidelity=read(ROOT/expected['fidelity']['path']),
    reconciled_sources={k:expected['sources'][k] for k in ('2023','2025','handbook')})
save('corpus-two-answers-result.json',dict(**aggregate,provider_calls=0,registration=registration,activation='SUPPLEMENTAL_EVIDENCE_ONLY'))
print(json.dumps(dict(status=result['status'],remaining=result['remaining'],provider_calls=0)))
