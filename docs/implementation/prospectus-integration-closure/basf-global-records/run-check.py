"""Retain pre-run identities and bounded test evidence for this continuation."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PLAN = 'docs/plans/prospectus-basf-global-records-2026-10-10.md'
name, bound, *tests = sys.argv[1:]
bound = int(bound)
folder = BASE / 'checks'
xml = folder / (name + '.xml')
manifest = folder / (name + '-manifest.json')
if xml.exists() or manifest.exists():
    raise ValueError('Refusing to overwrite a retained check')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
paths = [*sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py')),
         *sorted((ROOT/'scripts').glob('prospectus_closure_*.py')),
         *sorted((ROOT/'tests/prospectus_successor').glob('*.py')),
         ROOT/'tests/prospectus/test_closure_mechanisms.py', ROOT/'scripts/prospectus_delivery.py',
         ROOT/'scripts/author_basf_global_records_packet.py', Path(__file__), ROOT/PLAN, BASE/'basf-global-records/SOURCE-REVIEW.md',
         *sorted(BASE.glob('basf-*/review.json'))]
method = lambda: {str(p.relative_to(ROOT)): sha(p) for p in paths}
command = [str(ROOT/'.venv/bin/python'), '-m', 'scripts.prospectus_delivery', '--program', 'closure',
           'check', *tests, '--junitxml='+str(xml.relative_to(ROOT))]
record = {'command': command, 'timeout_seconds': bound, 'method': method(),
          'git_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'environment': {'python':sys.executable, 'version':sys.version, 'CUDA_VISIBLE_DEVICES':'-1'},
          'cpu_gpu': 'CPU; GPU intentionally hidden', 'random_seeds':'Deterministic controls; Hypothesis defaults for aggregate only',
          'data_version':'BASF frozen source graph and retained source packets; hashes in method',
          'plan_file': PLAN, 'result_file': str(xml.relative_to(ROOT)),
          'result_note':'docs/implementation/prospectus-integration-closure/basf-global-records/RESULT.md',
          'started_at': datetime.now(timezone.utc).isoformat(), 'status':'RUNNING'}
manifest.write_text(json.dumps(record,indent=2)+'\n')
tick=time.monotonic()
try:
    with (folder/(name+'.log')).open('w') as log:
        run=subprocess.run(command,cwd=ROOT,env=os.environ.copy(),stdout=log,stderr=subprocess.STDOUT,timeout=bound)
    record['exit_code']=run.returncode
    counts={k:sum(int(s.get(k,0)) for s in ET.parse(xml).getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    record.update(counts=counts,result_sha256=sha(xml),method_unchanged=method()==record['method'])
    record['status']='PASS' if run.returncode==0 and counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped')) and record['method_unchanged'] else 'FAIL'
except Exception as exc:
    record.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
record['wall_seconds']=time.monotonic()-tick
manifest.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in {'method','environment'}}))
if record['status']!='PASS': raise SystemExit(1)
