"""Preserve a bounded CPU-only regression in the trusted environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round15'


def main():
    if (OUT/'full-regression-manifest.json').exists():
        raise RuntimeError('Preserve the previous run before starting another attempt')
    cmd=[str(ROOT/'.venv/bin/python'),'-m','pytest','tests','-q','-o','faulthandler_timeout=0',
         '--junitxml='+str(OUT/'full-regression.xml')]
    paths=sorted(list((ROOT/'src').rglob('*.py'))+list((ROOT/'tests').rglob('*.py'))+
        [ROOT/'scripts/run_assurance_round15.py',ROOT/'scripts/assurance_round15_checks.py'])
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    manifest={'command':cmd,'supervisor_command':['python3','-m','scripts.run_round15_regression'],
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'environment':str(ROOT/'.venv'),'execution_context':'trusted',
        'cpu_gpu':'CPU only; CUDA_VISIBLE_DEVICES=-1','plan':'docs/implementation/interpretation-round15/delivery-verification-plan.md',
        'random_seeds':'N/A: deterministic checks and existing property-test configuration',
        'data_version':'frozen fixtures and code hashes','started_at':datetime.now(timezone.utc).isoformat(),
        'code_hashes':{str(p.relative_to(ROOT)):sha(p) for p in paths},'status':'RUNNING'}
    def save(): (OUT/'full-regression-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save();began=time.monotonic()
    with (OUT/'full-regression.log').open('w') as log:
        try:
            result=subprocess.run(cmd,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1'},
                stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            manifest.update(exit_code=result.returncode,status='PASS' if result.returncode==0 else 'FAIL')
        except subprocess.TimeoutExpired:manifest.update(exit_code=None,status='TIMEOUT_INCOMPLETE')
    manifest.update(wall_seconds=time.monotonic()-began,finished_at=datetime.now(timezone.utc).isoformat(),
        code_unchanged=all(sha(ROOT/p)==h for p,h in manifest['code_hashes'].items()),
        log='artifacts/interpretation/round15/full-regression.log',result='artifacts/interpretation/round15/full-regression.xml')
    if not manifest['code_unchanged']:manifest['status']='STALE_CODE'
    save();print(json.dumps({k:v for k,v in manifest.items() if k!='code_hashes'},indent=2))


if __name__=='__main__':main()
