"""Keep the first candidate evidence; retain the revised tested sources separately."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib,json,shutil
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
TREE=Path('/tmp/legalmath-product-closure-20261026')
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
prior=json.loads((WORK/'local-result.json').read_text())
paths=[r['path'] for r in prior['sources']]+['scripts/legal_integration_qualification_continuation.py']
tests=WORK/'final-fixed-v2-tests.xml';tree=ET.parse(tests).getroot()
assert not list(tree.iter('failure')) and not list(tree.iter('error'))
manifest=[]
for name in paths:
    source=TREE/name;compile(source.read_text(),name,'exec')
    target=WORK/'source-v2'/name;target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists();shutil.copyfile(source,target)
    manifest.append(dict(path=name,candidate=ref(target),before=ref(ROOT/name) if (ROOT/name).exists() else None))
evidence=[ref(tests),ref(WORK/'candidate-history-validation.json'),ref(WORK/'canonical-baseline.py'),
    ref(WORK/'p14-current-disposition-result-v2.json'),ref(WORK/'corpus-independent-result.json')]
result=dict(verdict='PASS',test_executions=len(list(tree.iter('testcase'))),
    provider_calls=0,legal_acceptance=False,evidence=evidence,sources=manifest,
    predecessor=ref(WORK/'local-result.json'),failed_test_evidence=ref(WORK/'final-v2-tests.xml'),
    limits=['Eight original P14 issue occurrences remain unresolved',
        'Corpus components do not establish final qualification',
        'Full staged and installed master validation still required'])
with (WORK/'local-result-v2.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(sources=len(manifest),tests=result['test_executions'],provider_calls=0)))
