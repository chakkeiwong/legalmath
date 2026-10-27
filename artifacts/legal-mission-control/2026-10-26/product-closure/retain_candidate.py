"""Retain exact candidate bytes and test results, without activating the worker."""
from pathlib import Path
import hashlib,json,shutil
from xml.etree import ElementTree as ET
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
TREE=Path('/tmp/legalmath-product-closure-20261026')
PATHS=['src/legalmath/canonical.py','src/legalmath/interpretation/assurance/bounded_product.py',
 'src/legalmath/interpretation/assurance/phased/retry_checkpoint.py',
 'src/legalmath/interpretation/assurance/phased/current_issue_disposition.py',
 'src/legalmath/interpretation/assurance/corpus_components.py',
 'scripts/legal_product_closure.py','scripts/legal_mission_execution.py',
 'scripts/legal_mission_control.py','scripts/legal_integration_phased_live.py',
 'tests/unit/test_canonical_equivalence.py','tests/assurance/test_current_issue_disposition.py',
 'tests/assurance/test_corpus_components.py','tests/tooling/test_product_closure.py']
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
manifest=[]
for name in PATHS:
    source=TREE/name;compile(source.read_text(),name,'exec')
    target=WORK/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==source.read_bytes()
    else:shutil.copyfile(source,target)
    manifest.append(dict(path=name,candidate=ref(target),before=ref(ROOT/name) if (ROOT/name).exists() else None))
evidence=[];tests=0
for name in ('canonical','components','regression-fixed','amendment'):
    path=WORK/(name+'-tests.xml');tree=ET.parse(path).getroot()
    assert not list(tree.iter('failure')) and not list(tree.iter('error'))
    tests+=len(list(tree.iter('testcase')));evidence.append(ref(path))
history=json.loads((WORK/'candidate-history-validation.json').read_text());assert history['verdict']=='PASS'
evidence.append(ref(WORK/'candidate-history-validation.json'))
result=dict(verdict='PASS',test_executions=tests,provider_calls=0,legal_acceptance=False,
    evidence=evidence,sources=manifest,
    limits=['Current-answer dispositions require actual review before activation',
        'Independent corpus components do not replace final complete coverage controls',
        'Timing remains descriptive; repeated full-history traversals remain'],
    prior_environment_failures_retained='regression-tests.xml')
with (WORK/'local-result.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(retained_sources=len(manifest),test_executions=tests,active_changes=False)))
