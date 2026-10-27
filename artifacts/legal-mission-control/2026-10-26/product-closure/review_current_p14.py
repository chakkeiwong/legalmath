"""Retain a reviewed issue-by-issue disposition; never dispatch or accept an answer."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
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
def save(name,value):
    with (WORK/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
packet=read(WORK/'p14-review-packet.json');census=read(WORK/'p14-current-issue-census.json')
answer=packet['answer']; support=answer['support']; population=census['issues']
checkpoint=read(ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation/checkpoints/p14/baseline.json')
fixed=read(ROOT/checkpoint['fixed_correction']['path'])
held=load_exact(ROOT/fixed['answers']['path'])['p14']['correction']
envelope=read(ROOT/'artifacts/legal-mission-control/2026-10-14/prerequisite-repair/complete-handbook-envelope.json')
product=BoundedProduct.__new__(BoundedProduct);product.root=ROOT
product.route=ContextRoute(envelope,tokenizer(ROOT/TOKENIZER),limits=Limits())
product.active_questions=['p14']
assert product.route.input_hash==held['source_identity']
rows={}
def add(ids,disposition,reason,indices=(0,1),path='/conclusion',quote=None,premises=None):
    for identity in ids.split():
        assert identity not in rows,identity
        row=dict(id=identity,disposition=disposition,reason=reason)
        if disposition!='STILL_REQUIRED':
            row.update(blocking_source_gaps=[],support=[support[i] for i in indices],
                answer_evidence=dict(path=path,quote=quote or answer['conclusion']))
            if disposition=='CONDITIONALLY_ADDRESSED':
                row['necessary_premises']=premises or [dict(description='No client request or performance is established; this finding concerns only the expressly bounded source interpretation.',
                    answer_evidence=dict(path='/unresolved/3',quote=answer['unresolved'][3]))]
        rows[identity]=row
network='The delivered intermediary material discusses network types, network-specific controls, attacks affecting transaction finality, cybersecurity, recovery, money-laundering and know-your-client risks, including heightened risks for bearer-form securities using permissionless tokens on public-permissionless networks.'
add('14:issue-0 99:issue-0 366:issue-0 408:issue-0 617:issue-0 618:issue-0 622:issue-0 730:issue-0 734:issue-1 827:issue-0 876:issue-0 914:issue-0 916:issue-0 916:issue-1 918:issue-0 919:issue-0 927:issue-0 934:issue-0 948:issue-0 949:issue-0 952:issue-0 953:issue-0 954:issue-0 958:issue-0 964:issue-0 1052:issue-0 1058:issue-0 1061:issue-0 1071:issue-0 1072:issue-0 1086:issue-1 1110:issue-0 1150:issue-0 1376:issue-0 1443:issue-0 1625:issue-0 1628:issue-0',
    'CORRECTED_IN_CURRENT_ANSWER','This exact objection attacks the prior absence claim. The fixed conclusion now identifies the supplied network-risk discussion and its actor, token-form and network conditions; the old absence statement is absent from conclusion and unresolved fields. Its source_gaps no longer identify the intermediary network-risk paragraph. The correction is a finding about delivery, not proof of adequate controls.',(10,14,17,18),quote=network)
controls='Product Providers are also not expected to issue tokenised authorised products in bearer form, and burning and re-issuance is supplied as an illustrative risk-mitigation option.'
add('700:issue-0 703:issue-0 703:issue-1 703:issue-2 704:issue-0 704:issue-1 704:issue-2 705:issue-0 705:issue-1 707:issue-0 707:issue-1 709:issue-0 709:issue-1 709:issue-2 716:issue-0 716:issue-1 734:issue-0',
    'CORRECTED_IN_CURRENT_ANSWER','The fixed answer now states the non-bearer expectation and describes burning/reissue as an illustrative option, then expressly refuses an actual-compliance conclusion. The product-circular footnotes are no longer in its source-gap list. The permission is not converted into mandatory implementation or demonstrated success.',(11,12),quote=controls)
add('96:issue-0 96:issue-1 728:issue-0 734:issue-2 1093:issue-0 1093:issue-1',
    'CORRECTED_IN_CURRENT_ANSWER','The corrected answer cites the supplied operative product provisions and explanatory notes. Its remaining product-circular gap locators are P6 and P7, not the operative P10-P16 or FN1-FN5 passages. The listed intermediary gaps retain their separate document identity. This closes the obsolete delivery assertion only.',(4,5,6,7,9,11,12,13),quote='The substantive duties remain independently relevant: retained Provider responsibility despite outsourcing, ownership-record maintenance, operational compatibility, cybersecurity, recovery and business-continuity measures, and additional controls responsive to network risks.')
add('373:issue-0','CORRECTED_IN_CURRENT_ANSWER','The fixed conclusion expressly describes the separate requested audit/verification and legal-opinion provisions and cites their delivered texts. Neither neighbouring provision remains a source gap.',(2,3),quote='The neighbouring provisions separately concern obtaining third-party audit or verification and a satisfactory legal opinion, each upon an SFC request.')
add('1086:issue-0','CORRECTED_IN_CURRENT_ANSWER','The fixed answer no longer says that the technical appendix is partly delivered. Both retained general and custody portions are cited. Its generic limitation concerns remaining incorporated material and completeness of compliance analysis; it is not a claim that these quoted appendix portions are absent.',(10,17,18),path='/unresolved/2',quote=answer['unresolved'][2])
add('13:issue-0 622:issue-1 1023:issue-1','CONDITIONALLY_ADDRESSED','The fixed answer confines itself to the delivered operative propositions and expressly limits completeness. Missing incorporated material remains a limitation on a complete compliance analysis. The answer does not purport to exhaust all assurance requirements or determine actual fulfillment.',(4,5,6,7,9,10,17,18),path='/unresolved/2',quote=answer['unresolved'][2])
add('35:issue-0 35:issue-1 36:issue-0 36:issue-1 115:issue-0 115:issue-1 116:issue-0 116:issue-1 538:issue-0 538:issue-1',
    'NOT_APPLICABLE_TO_CURRENT_ANSWER','The exact question asks how the confirmation/demonstration words and neighbouring procurement clauses attach. The fixed answer does not transfer Gatecoin trust propositions, establish customer consent or determine ownership. Those questions remain in the separate original Gatecoin work; disposing of this objection does not dispose of those obligations.',(0,1,19),path='/assumptions/1',quote=answer['assumptions'][1])
add('117:issue-0 117:issue-1 118:issue-0 118:issue-1 119:issue-0 119:issue-1 506:issue-0 509:issue-0 510:issue-0 512:issue-0 513:issue-0 514:issue-0 517:issue-0 519:issue-0 1072:issue-1 1248:issue-0 1410:issue-1 1454:issue-2',
    'CONDITIONALLY_ADDRESSED','The fixed answer does not decide actual performance, staffing, supervisory adequacy, ownership or client applicability. It states the unknown facts and keeps the actors separate. Those facts would be necessary to decide fulfillment; they are not prerequisites to the stated conditional textual interpretation.',(0,1,4,5),path='/unresolved/3',quote=answer['unresolved'][3])
add('890:issue-0 890:issue-1 1454:issue-0 1454:issue-1 1455:issue-0 1455:issue-1 1456:issue-0 1456:issue-1 1460:issue-0 1460:issue-1 1461:issue-0 1461:issue-1 1463:issue-0 1465:issue-0 1465:issue-1 1465:issue-2 1699:issue-0',
    'NOT_APPLICABLE_TO_CURRENT_ANSWER','The objection asks this P14 attachment answer to determine a different Handbook valuation, expenses, reporting or trustee-removal requirement. No conclusion in the fixed answer decides that requirement or relies on its fulfillment. The source fragment remains relevant to its own question/obligations; an unrelated dependency assignment is not a defect in the limited P14 conclusion.',(0,1,2,3),path='/assumptions/1',quote=answer['assumptions'][1])
add('730:issue-1 1058:issue-1 1072:issue-2','CONDITIONALLY_ADDRESSED','The fixed answer preserves both the request-conditioned and rival readings, separate requested procurement, actor-specific network controls and absence of proven compliance. It neither turns illustrative audit factors into a universal procurement command nor treats procurement as regulatory satisfaction.',(0,1,2,3,7,10,14),quote='They do not state that procurement substitutes for confirmation, demonstration, or the underlying responsibilities.')
add('13:issue-1','STILL_REQUIRED','The current conclusion still includes a Handbook legal-effect statement, but its support list contains no direct Handbook quotation for that statement. The full retained Handbook may cure it; the exact supporting clause and current-answer review must be supplied before this issue is settled.')
add('1023:issue-0 1033:issue-0 1033:issue-1','STILL_REQUIRED','The retained original review reports a missing association between local dependency IDs and opaque output selectors. A corrected prose answer does not repair that harness mapping. Preserve this defect until exact assignment/selector evidence is checked against the original and current review populations.')
add('1061:issue-1','STILL_REQUIRED','Matching words under another source identity do not fulfill the typed original request. Resolve the exact document/locator mapping with retained ownership and need records before treating this issue as supplied.')
add('1248:issue-1 1248:issue-2 1410:issue-0','STILL_REQUIRED','The generic objection does not identify enough exact source/assignment information to establish closure here. Trace its originating dependency and assigned records; a broad scope disclaimer cannot waive a still-required review question or demonstrate the missing source association.')
assert set(rows)=={r['id'] for r in population},(set(rows)-{r['id'] for r in population},{r['id'] for r in population}-set(rows))
note=ROOT/'docs/implementation/legal-mission-control/results/p14-current-answer-review-2026-10-26.md'
value=dict(profile=issue.PROFILE,question_id='p14',question_hash=digest(packet['question']),
    input_hash=product.route.input_hash,original_answer_hash=digest(held['original_answer']['value']),
    current_answer_hash=digest(answer),requirement_details_hash=digest(held['corrected_requirement_details']),
    issue_population_hash=digest([{k:r[k] for k in ('id','review_index','review_hash','issue')} for r in population]),reviewer='Codex: explicit retained-answer review, October 26 2026',
    review_note=ref(note),dispositions=[rows[r['id']] for r in population])
outcome=issue.validate(product,'p14',packet['question'],held['original_answer']['value'],answer,
    held['corrected_requirement_details'],census['reviews'],census['assessments'],value)
save('p14-current-dispositions-v2.json',value)
save('p14-current-disposition-result-v2.json',dict(**outcome,counts=dict(Counter(r['disposition'] for r in rows.values())),
    evidence=[ref(note),ref(WORK/'p14-current-dispositions-v2.json'),ref(WORK/'p14-current-issue-census.json')],
    actual_sources_checked=True,provider_calls=0,activation='PENDING_REVIEWED_BINDING'))
successor={**checkpoint,'current_answer_issue_dispositions':{'p14':ref(WORK/'p14-current-dispositions-v2.json')}}
save('p14-checkpoint.json',successor)
print(json.dumps(dict(issue_count=outcome['issue_count'],pending=[r['id'] for r in outcome['pending']],
    counts=dict(Counter(r['disposition'] for r in rows.values())),legal_acceptance=False)))
