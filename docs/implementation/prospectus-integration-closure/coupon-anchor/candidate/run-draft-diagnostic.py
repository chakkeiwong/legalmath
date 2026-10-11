"""A bounded, isolated candidate diagnostic; never imports the tested worktree."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT=Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
CANDIDATE=Path(__file__).resolve().parent
PLAN=ROOT/'docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p,row):
    p.write_text(json.dumps(row,indent=2)+'\n')

def main():
    baseline=json.loads((CANDIDATE/'baseline.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in baseline['files'].items()), 'Staging baseline changed'
    proposed=[*sorted((CANDIDATE/'src').rglob('*.py')),*sorted((CANDIDATE/'scripts').glob('*.py')),
              *sorted((CANDIDATE/'tests').rglob('*.py'))]
    for p in proposed:
        ast.parse(p.read_text(),filename=str(p))
    originals=[*sorted((ROOT/'src/legalmath').rglob('*.py')),*sorted((ROOT/'scripts').glob('*.py'))]
    method={str(p.relative_to(ROOT)):sha(p) for p in originals}
    candidate_method={str(p.relative_to(CANDIDATE)):sha(p) for p in proposed}
    number=1
    while Path(f'/tmp/prospectus-coupon-anchor-diagnostic-{number:03d}').exists():
        number+=1
    folder=Path(f'/tmp/prospectus-coupon-anchor-diagnostic-{number:03d}')
    folder.mkdir()
    with tempfile.TemporaryDirectory(prefix='prospectus-coupon-anchor-runtime-') as temporary:
        temporary=Path(temporary)
        shutil.copytree(ROOT/'src',temporary/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        (temporary/'scripts').mkdir()
        for p in (ROOT/'scripts').glob('*.py'):
            shutil.copy2(p,temporary/'scripts'/p.name)
        for p in proposed:
            target=temporary/p.relative_to(CANDIDATE)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target)
        runner=temporary/'run.py'
        runner.write_text('''import sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path[:0]=[str(root/'src'),str(root)]
import legalmath
assert Path(legalmath.__file__).resolve().is_relative_to(root), legalmath.__file__
import scripts.prospectus_closure_fixtures as fixtures
assert Path(fixtures.__file__).resolve().is_relative_to(root), fixtures.__file__
import pytest
raise SystemExit(pytest.main(['-q','-c','/dev/null',str(root/'tests/prospectus_successor/test_closure_coupon_anchor.py'),
    '--basetemp='+str(root/'pytest-tmp'),'--junitxml='+sys.argv[1]]))
''')
        command=[str(ROOT/'.venv/bin/python'),'-I',str(runner),str(folder/'tests.xml')]
        before=dict(version='coupon-anchor-draft-diagnostic.v1',status='RUNNING',
            question='Does the isolated draft preserve the explicit original coupon anchor and exact conditional fractions through both service routes?',
            baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            comparator='Retained finance-anchor-diagnostic; legacy August/February rejection remains expected',
            plan_file=str(PLAN.relative_to(ROOT)),plan_sha256=sha(PLAN),
            original_method=method,candidate_method=candidate_method,driver_sha256=sha(Path(__file__)),
            command=command,environment=dict(python=sys.executable,version=sys.version,CUDA_VISIBLE_DEVICES='-1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'),
            cpu_gpu='CPU; GPU intentionally hidden, no probe',seeds='N/A; deterministic examples',
            data_version='Synthetic independently listed dates; source hashes retained in test requests',
            timeout_seconds=120,started_at=datetime.now(timezone.utc).isoformat(),result_file=str(folder/'result.json'),
            claim_limit='Preliminary candidate diagnostic; not integrated, installed, real-instrument or legal acceptance')
        save(folder/'started.json',before)
        tick=time.monotonic()
        try:
            run=subprocess.run(command,cwd=temporary,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'},capture_output=True,timeout=120)
            (folder/'command.log').write_bytes(run.stdout+run.stderr)
            counts={k:sum(int(s.get(k,0)) for s in ET.parse(folder/'tests.xml').getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}
            unchanged=method=={str(p.relative_to(ROOT)):sha(p) for p in originals} and candidate_method=={str(p.relative_to(CANDIDATE)):sha(p) for p in proposed} and sha(PLAN)==before['plan_sha256']
            result=dict(status='PASS' if run.returncode==0 and counts['tests'] and not any(counts[k] for k in ('failures','errors','skipped')) and unchanged else 'FAIL',counts=counts,returncode=run.returncode,method_unchanged=unchanged)
        except subprocess.TimeoutExpired as exc:
            (folder/'command.log').write_bytes((exc.stdout or b'')+(exc.stderr or b''))
            result=dict(status='TIMEOUT',error='120-second candidate diagnostic bound exceeded; review before retry')
        result.update(wall_seconds=time.monotonic()-tick,integrated=False,claim_limit=before['claim_limit'])
        save(folder/'result.json',result)
        save(folder/'manifest.json',{'files':{p.name:sha(p) for p in folder.iterdir() if p.is_file()}})
    print(json.dumps({'directory':str(folder),**result}),flush=True)
    if result['status']!='PASS':
        raise SystemExit(1)

if __name__=='__main__':
    main()
