"""Independent exact-answer case review; preserve partial semantic failure."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
from legalmath.canonical import digest
from legalmath.interpretation.assurance import corpus_components as part
def read(p):return json.loads(p.read_text())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(n,v):
    if (WORK/n).exists():
        assert read(WORK/n)==v, 'Refuse changed retained review evidence'
        return ref(WORK/n)
    with (WORK/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
    return ref(WORK/n)
expected=read(WORK/'corpus-context.json');packet=read(WORK/'p14-review-packet.json');answer=packet['answer']
answerref=save('p14-reviewed-answer.json',answer)
source=expected['sources']['26EC22'];raw=(ROOT/source['path']).read_text()
def support(index):
    s=answer['support'][index];quote=s['quote']
    # Short exact literal snippets avoid JSON whitespace and escape transformations.
    snippets={0:'confirm and, upon SFC’s request, demonstrate to the SFC’s satisfaction',
        1:'Product Providers should confirm and demonstrate to the SFC that, at a minimum,',
        2:'obtain third party audit or verification',3:'obtain satisfactory legal opinion to support its application'}
    text=snippets[index];assert text in raw and text in quote
    return dict(source_id='26EC22',source=source,passage=source,locator=s['locator'],quote=text)
def ev(path,quote):
    v=answer
    for key in path.split('/')[1:]:v=v[int(key)] if isinstance(v,list) else v[key]
    assert quote in v
    return dict(path=path,quote=quote)
props=[dict(id='cases:p14-no-request',status='SUPPORTED',source_ids=['26EC22'],
    reason='Confirmation and requested demonstration are distinguished; the unqualified footnote rival remains and no fulfillment is inferred.',
    primary_evidence=[support(0),support(1)],answer_evidence=[ev('/alternatives/0/consequence',answer['alternatives'][0]['consequence']),
        ev('/alternatives/1/consequence',answer['alternatives'][1]['consequence'])]),
    dict(id='cases:p14-unknown-request',status='SUPPORTED',source_ids=['26EC22'],
    reason='The no-request premise is expressly hypothetical, and no actual request or correspondence history is established.',
    primary_evidence=[support(0)],answer_evidence=[ev('/assumptions/0',answer['assumptions'][0]),ev('/unresolved/3',answer['unresolved'][3])]),
    dict(id='cases:p14-audit-confidence',status='UNRESOLVED',source_ids=['26EC22','23EC52-appendix'],
    reason='Narrow and broad confidence scopes and unknown assurance coverage are preserved, but the answer does not explicitly connect assurance to the deployed contract version or explain justified reliance on a third-party audit. An appendix quote alone does not supply that reasoning.',
    answer_evidence=[ev('/alternatives/4/consequence',answer['alternatives'][4]['consequence']),
        ev('/alternatives/5/consequence',answer['alternatives'][5]['consequence']),ev('/unresolved/3',answer['unresolved'][3])]),
    dict(id='cases:p14-separate-requests',status='SUPPORTED',source_ids=['26EC22'],
    reason='Demonstration, audit or verification, and legal-opinion requests remain separate. Procurement does not establish substantive compliance or regulatory acceptance.',
    primary_evidence=[support(0),support(2),support(3)],answer_evidence=[ev('/alternatives/6/consequence',answer['alternatives'][6]['consequence']),
        ev('/alternatives/7/consequence',answer['alternatives'][7]['consequence'])])]
assert {p['id'] for p in props}==set(expected['required_propositions']['p14'])
note=ref(ROOT/'docs/implementation/legal-mission-control/results/p14-answer-use-review-2026-10-26.md')
review=save('corpus-p14-answer-review.json',dict(profile=part.PROFILE,kind='answer',context_hash=digest(expected),
    scope=expected['scope'],as_of=expected['as_of'],reviewer='Codex: exact fixed-answer original-case review, October 26 2026',
    review_note=note,review=dict(question='p14',answer=answerref,propositions=props)))
result=part.answer_review(ROOT,expected,answerref,review)
save('corpus-p14-answer-result.json',dict(**result,provider_calls=0,original_answer_hash=digest(answer)))
manifest=deepcopy(read(WORK/'corpus-components.json'));manifest['answers']['p14']=dict(answer=answerref,review=review)
manifestref=save('corpus-components-with-p14.json',manifest)
registration=dict(expected_context=ref(WORK/'corpus-context.json'),components=manifestref)
fidelity=read(ROOT/expected['fidelity']['path'])
aggregate=part.consume(ROOT,registration,fidelity=fidelity,reconciled_sources={k:expected['sources'][k] for k in ('2023','2025','handbook')})
save('corpus-with-p14-result.json',dict(**aggregate,provider_calls=0,registration=registration,activation='SUPPLEMENTAL_EVIDENCE_ONLY'))
print(json.dumps(dict(status=result['status'],remaining=result['remaining'],provider_calls=0)))
