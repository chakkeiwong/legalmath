"""Apply only the executed portability repair to the retained test snapshot."""
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parents[4]
SNAPSHOT=Path('/tmp/legalmath-continuation-final-20260929')
OUT=ROOT/'artifacts/assurance-continuation/2026-09-29/final-assessment'
DEST=OUT/'isolation-repair'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())


prior=read(OUT/'isolation/manifest.json')
failed=read(OUT/'attempt-03/manifest.json')
assert failed['status']=='FAILED' and failed['regression']=={
    'tests':1519,'failures':1,'errors':0,'skipped':0}
assert all(sha(SNAPSHOT/p)==h for p,h in prior['inputs'].items())
focused=OUT/'portability-focused-03.xml'
tree=ET.parse(focused).getroot()
counts={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite'))
        for k in ('tests','failures','errors','skipped')}
assert counts=={'tests':15,'failures':0,'errors':0,'skipped':0}
DEST.mkdir(exist_ok=False)
changed=['scripts/assurance_successor_sources.py','tests/assurance/test_successor_source_freeze.py',
         'docs/plans/assurance-continuation-final-assessment.md']
inputs=dict(prior['inputs']);changes={}
for name in changed:
    data=(ROOT/name).read_bytes()
    changes[name]={'before':sha(SNAPSHOT/name),'after':hashlib.sha256(data).hexdigest()}
    (SNAPSHOT/name).write_bytes(data);inputs[name]=sha(SNAPSHOT/name)
with ZipFile(DEST/'tested-inputs.zip','w',ZIP_DEFLATED) as archive:
    for name in sorted(inputs):archive.write(SNAPSHOT/name,name)
manifest={**prior,'status':'REPAIRED_SNAPSHOT_CREATED','inputs':inputs,'changes':changes,
    'archive_sha256':sha(DEST/'tested-inputs.zip'),
    'prior_snapshot_manifest_sha256':sha(OUT/'isolation/manifest.json'),
    'failed_assessment_sha256':sha(OUT/'attempt-03/manifest.json'),
    'focused_result':{'path':str(focused.relative_to(ROOT)),'sha256':sha(focused),'counts':counts},
    'focused_command':['.venv/bin/python','-m','pytest','-q',
        'tests/assurance/test_successor_source_freeze.py',
        '--junitxml=artifacts/assurance-continuation/2026-09-29/final-assessment/portability-focused-03.xml'],
    'script_sha256':sha(__file__),'argv':[sys.executable,*sys.argv],
    'scope':'Two code/test changes plus the reviewed repair plan; all other frozen inputs identical.',
    'live_calls':0}
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('Archived repaired snapshot',len(inputs),changes)
