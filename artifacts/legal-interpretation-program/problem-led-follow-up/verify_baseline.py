"""Independently recheck the unchanged S4 baseline and retain an identity snapshot."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import legal_interpretation_s4_execute as s4

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    start=time.monotonic()
    out=Path(__file__).resolve().parent
    result_path=ROOT/'artifacts/legal-interpretation-program/successor-s4/attempt-1/result.json'
    assert sha(result_path)=='798907115d69822755d7d417c50a95aeb37faec41b89a2fae1bc503bbb522ce6'
    result=json.loads(result_path.read_text())
    refs={**result['method']['source_and_tests'],**result['method']['drivers']}
    for name,h in refs.items():
        assert sha(ROOT/name)==h, name
    for row in result['outputs']:
        assert sha(ROOT/row['path'])==row['sha256'], row['path']
    print('S4 file identities match; running existing independent verifier.', flush=True)
    checked=s4.verify_attempt(result_path.parent)
    record={'status':'PASS','started_at':datetime.now(timezone.utc).isoformat(),
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'command':'.venv/bin/python -c \'import runpy; runpy.run_path("artifacts/legal-interpretation-program/problem-led-follow-up/verify_baseline.py",run_name="__main__")\'',
        'environment':sys.executable,'python':sys.version,'cpu_gpu':'CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
        'seeds':'N/A: deterministic integrity and replay checks','provider_calls':0,'network_requests':0,
        'plan':'docs/plans/legal-interpretation-problem-led-follow-up.md',
        'result_file':'artifacts/legal-interpretation-program/problem-led-follow-up/baseline-verification.json',
        'script_sha256':sha(Path(__file__)),'wall_seconds':time.monotonic()-start,
        's4_result':{'path':str(result_path.relative_to(ROOT)),'sha256':sha(result_path)},
        'independent_file_checks':len(refs)+len(result['outputs']),
        'method':result['method'],'output_references':result['outputs'],'fresh_verification':checked,
        'freeze_scope':'Identity snapshot with independently replayed S4; no method files changed. Any future method edit still requires a full historical dependency copy.',
        'data_version':'Exact retained S4 output references and method below'}
    p=out/'baseline-verification.json'
    with p.open('x') as f: json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps({k:record[k] for k in ('status','independent_file_checks','wall_seconds','fresh_verification')},indent=2))

if __name__=='__main__': main()
