"""Freeze tested follow-through; never alter running source or grant."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,shutil,xml.etree.ElementTree as ET
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
TREE=Path('/tmp/legalmath-product-closure-20261026')
def read(p):return json.loads(p.read_text())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha256(p.read_bytes()).hexdigest())
def put(name,value):
    with (WORK/name).open('x') as stream:json.dump(value,stream,ensure_ascii=False,indent=2)
    return ref(WORK/name)
files=['src/legalmath/interpretation/assurance/corpus_review.py',
    'src/legalmath/interpretation/assurance/corpus_components.py',
    'tests/assurance/test_baseline_corpus_repairs.py',
    'tests/assurance/test_corpus_answer_attribution.py']
rows=[]
for name in files:
    dest=WORK/'answer-attribution-candidate'/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    assert not dest.exists(),'Retained candidate already exists'
    shutil.copy2(TREE/name,dest)
    baseline=WORK/'answer-evidence-before'/name
    rows.append(dict(path=name,candidate=ref(dest),before=ref(baseline) if baseline.exists() else None))
suite=ET.parse(WORK/'answer-attribution-tests.xml').getroot()
results=[x for x in suite.iter('testsuite')]
assert sum(int(x.get('failures','0'))+int(x.get('errors','0')) for x in results)==0
put('answer-attribution-candidate-result.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
    verdict='PASS',activation='PENDING_SAFE_CHECKPOINT',sources=rows,
    tests=sum(int(x.get('tests','0')) for x in results),
    evidence=[ref(WORK/'answer-attribution-tests.xml'),ref(WORK/'answer-evidence-omission-reproducer.json'),
        ref(WORK/'actual-answer-attribution-result.json'),ref(WORK/'answer-evidence-repair-plan.md')],
    provider_calls=0,legal_acceptance=False))
pairs=[('23EC52-current.html','artifacts/authority-source-revision/2026-09-29/attempt-01/sources/23ec52.json',
    'https://apps.sfc.hk/edistributionWeb/api/circular/content?refNo=23EC52&lang=EN'),
    ('23EC52-appendix-current.pdf','artifacts/authority-source-revision/2026-09-29/attempt-01/sources/23ec52-appendix.pdf',
    'https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?lang=EN&refNo=23EC52&appendix=0'),
    ('26EC23-current.html','artifacts/legal-mission-control/2026-10-11/source-applicability/26EC23-retained.json',
    'https://apps.sfc.hk/edistributionWeb/api/circular/content?refNo=26EC23&lang=EN'),
    ('ut-handbook-current.pdf','artifacts/legal-mission-control/2026-10-13/master/corpus-work/ut-handbook-current.pdf',
    'https://www.sfc.hk/-/media/EN/assets/components/codes/files-current/web/codes/sfc-handbook-for-unit-trusts-and-mutual-funds/sfc-handbook-for-unit-trusts-and-mutual-funds.pdf?rev=69136164312f412381ba681c4d9c86af')]
comparisons=[]
for current,prior,url in pairs:
    same=(WORK/current).read_bytes()==(ROOT/prior).read_bytes()
    assert same,'Current edition differs: '+current
    comparisons.append(dict(current=ref(WORK/current),prior=ref(ROOT/prior),url=url,byte_identical=same))
put('edition-review-result.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
    status='CURRENT_PUBLISHED_BYTES_VERIFIED',comparisons=comparisons,
    handbook_index=ref(WORK/'sfc-codes-current.html'),handbook_index_date='2 Oct 2024',
    note=ref(ROOT/'docs/implementation/legal-mission-control/results/product-closure-edition-review-2026-10-26.md'),
    provider_calls=0,client_applicability_established=False,exhaustive_current_law_research=False,legal_acceptance=False))
print(json.dumps(dict(candidate_tests=93,edition_matches=len(comparisons),provider_calls=0,
    activation='PENDING_SAFE_CHECKPOINT')))
