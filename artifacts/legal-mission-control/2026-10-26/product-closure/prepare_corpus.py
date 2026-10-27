"""Register independent dated research and unchanged original proposition duties."""
from pathlib import Path
from collections import Counter
import hashlib,json,os,sys
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
sys.path[:0]=['/tmp/legalmath-product-closure-20261026/src',str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.canonical import digest
from legalmath.interpretation.assurance import corpus_components as components
def read(p):return json.loads((ROOT/p).read_text())
def ref(p):
    p=ROOT/p
    return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def save(name,v):
    p=WORK/name
    with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2)
    return ref(p)
envelope=read('artifacts/legal-mission-control/2026-10-14/prerequisite-repair/complete-handbook-envelope.json')
accepted=envelope['answer_acceptance'];questions={q['question_id'] for q in envelope['original_questions']}
assert len(accepted['acceptance_obligations'])==46 and len(accepted['original_readings'])==35
props={q:[] for q in questions}
for kind in ('acceptance_obligations','original_readings','cases'):
    for row in accepted[kind]:
        for q in row['question_ids']:
            props[q].append(kind+':'+row['case_id' if kind=='cases' else 'id'])
sources={};ownership={}
base=Path('artifacts/legal-mission-control/2026-10-13/master')
for name in ('2023','2025','handbook'):
    data=read(base/('ownership-'+name)/'attempt-3/evidence.json')
    ownership[name]=data['ownership'];sources[name]=read(data['ownership']['path'])['source']
sources.update({'26EC22':accepted['source_documents'][0]['source'],
    '23EC52':accepted['source_documents'][1]['source'],
    '23EC52-appendix':ref(Path('artifacts/authority-source-revision/2026-09-29/attempt-01/sources/23ec52-appendix.pdf'))})
expected=dict(profile=components.PROFILE,scope='Original four questions, all 46 obligations and 35 readings; conditional source interpretation only, with client fulfillment and exhaustive current-law research unresolved.',
    as_of='2026-10-26T00:00:00+08:00',sources=sources,required_propositions=props,
    fidelity=ref(base/'corpus-qualification/attempt-6/corpus-reconciliation.json'))
context=save('corpus-context.json',expected)
note=ref(Path('docs/implementation/legal-mission-control/results/product-closure-source-review-2026-10-26.md'))
history=Path('artifacts/legal-mission-control/2026-10-11/source-applicability')
rows={}
for sid,source in sources.items():
    if sid=='26EC22':
        applicability='Retained primary-dealing safeguards apply to the stated SFC-authorised public-offer product scope. The original textual P10/P14 questions can be considered conditionally. No client product classification, assessment period, authorisation conditions or actual requests are supplied.'
        later='Fresh official endpoint bytes match the retained October 11 capture. This is source identity evidence; it does not establish absence of other current instruments or later guidance.'
        searches=[ref(WORK/'26EC22-current.html'),ref(history/'current-identity-check.json'),ref(history/'26EC22-inspection.json')]
    elif sid in ('2023','2025'):
        applicability='The retained judgment concerns Gatecoin liquidation, customer contractual groups, assets and chronology. Transfer of its reasoning to a Product Provider remains conditional on materially relevant facts and legal relationships. The scenario-seven reading conflict is not resolved by ownership/fidelity checks.'
        later='The retained exact-citation query returned a search exception, not a negative finding. Name and case-number results and inspected later judgments provide bounded treatment evidence. No exhaustive October 26 treatment search or authoritative scenario-seven resolution is established.'
        searches=[ownership[sid],ref(history/'gatecoin-citation-search.json'),ref(history/'gatecoin-name-search.json'),ref(history/'gatecoin-case-search.json'),ref(history/'hkcfi-2024-370.json'),ref(history/'hkdc-2024-1628.json'),ref(history/'hkdc-2026-1402.json')]
    elif sid=='handbook':
        applicability='The qualified retained clauses distinguish Overarching Principles from Unit Trusts duties. Product and actor classification, constitutive documents, relevant interval and authorisation conditions remain necessary for a client-specific determination. Clauses can support explicitly scoped textual analysis.'
        later='The retained October 2024 fifth edition and its checked 35 pages establish the corpus used. Full current-edition and amendment applicability across the missing client interval is not established by that fidelity receipt.'
        searches=[ownership[sid],ref(history/'edition-comparison.json')]
    else:
        applicability='Intermediary-facing tokenised-securities duties and the appendix provide actor-specific risk considerations. Their incorporation into Provider arrangements must preserve the source identity, where-applicable condition and distinction between non-exhaustive factors and mandatory fulfillment.'
        later='Retained source bytes are available. A fresh comprehensive amendment/supersession search for this instrument and appendix has not completed; no absence of later treatment is inferred.'
        searches=[source,note]
    row=dict(source_id=sid,source=source,version='Exact retained bytes '+source['sha256'],
        applicability=dict(status='UNRESOLVED',finding=applicability,search_evidence=searches),
        later_treatment=dict(status='UNRESOLVED',finding=later,search_evidence=searches))
    rows[sid]=save('corpus-source-'+sid+'.json',dict(profile=components.PROFILE,kind='source',
        context_hash=digest(expected),scope=expected['scope'],as_of=expected['as_of'],
        reviewer='Codex: bounded retained-source research, October 26 2026',review_note=note,review=row))
manifest=save('corpus-components.json',dict(profile=components.PROFILE,context_hash=digest(expected),sources=rows,answers={}))
registration=dict(expected_context=context,components=manifest)
outcome=components.consume(ROOT,registration,fidelity=read(expected['fidelity']['path']),
    reconciled_sources={k:sources[k] for k in ('2023','2025','handbook')})
save('corpus-independent-result.json',dict(**outcome,provider_calls=0,original_obligations=46,original_readings=35))
save('corpus-registration.json',registration)
print(json.dumps(dict(source_reviews=len(rows),remaining=outcome['remaining'],corpus_acceptance_complete=False,provider_calls=0)))
