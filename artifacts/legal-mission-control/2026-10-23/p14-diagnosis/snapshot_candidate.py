"""Retain the reviewed isolated candidate without changing bound runtime files."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path('/home/chakwong/python/legalmath')
CANDIDATE = Path('/tmp/legalmath-p14-repair-20261023')
OUT = Path(__file__).resolve().parent
def git(*args):
    return subprocess.check_output(['git', *args],cwd=CANDIDATE)
modified = git('diff','--name-only','HEAD').decode().splitlines()
new = git('ls-files','--others','--exclude-standard','--','src','scripts','tests').decode().splitlines()
paths = sorted(set(modified+new))
assert all(p.startswith(('src/','scripts/','tests/')) for p in paths)
patch = git('diff','--binary','HEAD')
for name in new:
    diff = subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',name],cwd=CANDIDATE,capture_output=True)
    assert diff.returncode == 1, diff.stderr
    patch += diff.stdout
(OUT/'candidate.patch').write_bytes(patch)
rows=[]
for name in paths:
    source=CANDIDATE/name
    target=OUT/'candidate-files'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    rows.append(dict(path=name,sha256=sha256(source.read_bytes()).hexdigest(),bytes=source.stat().st_size))
shutil.copyfile('/tmp/p14-local-tests.py',OUT/'run_local_tests.py')
suite=ET.parse(OUT/'local-tests.xml').getroot().find('testsuite')
value=dict(profile='isolated-p14-local-candidate.v1',at_utc=datetime.now(timezone.utc).isoformat(),
    base_commit=git('rev-parse','HEAD').decode().strip(),branch=git('branch','--show-current').decode().strip(),
    checkout=str(CANDIDATE), files=rows, patch_sha256=sha256(patch).hexdigest(),
    test_result={k:suite.attrib[k] for k in ('tests','failures','errors','skipped','time')},
    test_command='.venv-context/bin/python /tmp/p14-local-tests.py',
    interpreter=str(ROOT/'.venv-context/bin/python'),
    environment={'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':str(CANDIDATE/'src')+':'+str(CANDIDATE)},
    gpu='Intentionally hidden; CPU-only local verification', random_seeds='N/A: deterministic fixtures',
    data_version='census.json retains exact original evidence hashes',
    plan='docs/plans/p14-failure-diagnosis-2026-10-23.md',
    result='docs/implementation/legal-mission-control/results/p14-failure-diagnosis-2026-10-23.md',
    provider_calls=0, deployed=False, legal_acceptance=False)
(OUT/'candidate-manifest.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k not in ('files',)},indent=2))
