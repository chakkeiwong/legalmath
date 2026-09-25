"""Run bounded MathDevMCP obligations and retain exact requests and responses.

Algebraic equivalence is not evidence for legal interpretation or model accuracy.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/monograph/review/revision/math-obligations'
ENV = '/home/chakwong/miniconda3/envs/mathdevmcp-backends/bin/python'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    obligations = [
      ('common-error-example', '2/100+(1-2/100)*(1/10)**3', '2098/100000', [], 'eq:common-error'),
      ('marginal-error', '2/100+(1-2/100)*(1/10)', '118/1000', [], 'eq:common-error'),
      ('fair-independent-comparator', '(118/1000)**3', '1643032/1000000000', [], 'eq:common-error'),
      ('old-comparator-is-different', '(118/1000)**3', '1/1000', [], 'eq:common-error'),
      ('equicorrelation-variance', '(m*s**2+m*(m-1)*rho*s**2)/m**2', 's**2/m*(1+(m-1)*rho)', ['m > 0'], 'eq:ensemble-variance'),
      ('cost-equality', 'K+(K/(M-A))*A', '(K/(M-A))*M', ['M > A'], 'eq:cost'),
      ('cost-example', '100000/(2000-1500)', '200', [], 'eq:cost'),
      ('ternary-domain-size', '3**6', '729', [], 'finite-input-domain'),
      ('exact-scale-example', '3*33+1', '100', [], 'eq:exact-scale'),
      ('exposure-race', '8+3/2+3/2', '11', [], 'host-concurrency'),
      ('wealth-example', '120-15-30', '75', [], 'net-assets-example'),
      ('ownership-example', '60*(20/100)', '12', [], 'ownership-example'),
      ('asset-conservation', '(b-q)+(r+q)', 'b+r', ['0 <= q', 'q <= b'], 'eq:asset-transfer'),
      ('escrow-conservation', '(p-d)+d+r', 'p+r', ['0 <= d', 'd <= p'], 'eq:escrow-deposit'),
      ('uniform-entropy', '(-3*(1/3)*log(1/3))', 'log(3)', [], 'eq:semantic-entropy'),
      ('binomial-log-inversion', 'n*(log(alpha)/n)', 'log(alpha)', ['n > 0', '0 < alpha', 'alpha < 1'], 'eq:zero-errors'),
    ]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH='/home/chakwong/python/MathDevMCP/src', CUDA_VISIBLE_DEVICES='-1')
    results=[]
    for name,lhs,rhs,assumptions,label in obligations:
        cmd=[ENV,'-m','mathdevmcp.cli','check-proof-obligation',lhs,rhs,'--backend','sympy']
        for assumption in assumptions:
            cmd.extend(['--assumption',assumption])
        start=time.monotonic()
        run=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=45)
        response=json.loads(run.stdout) if run.returncode==0 else {'error':run.stderr}
        result={'id':name,'source_label':label,'command':cmd,'cpu_only':'GPU devices intentionally hidden',
                'wall_seconds':time.monotonic()-start,'exit_code':run.returncode,'response':response,
                'assumption_limit':'The calculation checks the written illustrative model; it does not establish the model assumptions.'}
        (OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        results.append({'id':name,'status':response.get('status'),'expected_difference':name=='old-comparator-is-different'})
    lean_path = OUT/'MonographLogic.lean'
    cmd = [ENV, str(Path(__file__).resolve()), '--lean-worker']
    start = time.monotonic()
    run = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    response = json.loads(run.stdout) if run.returncode == 0 else {'status': 'error', 'error': run.stderr}
    (OUT/'MonographLogic.json').write_text(json.dumps({
        'command':cmd, 'request': {'function':'MathDevMCP.check_lean_source', 'allow_sorry':False,
        'source':str(lean_path.relative_to(ROOT)), 'sha256':hashlib.sha256(lean_path.read_bytes()).hexdigest()},
        'cpu_only':'GPU devices intentionally hidden', 'wall_seconds':time.monotonic()-start,
        'response':response, 'limits':'Exactly the supplied Lean declarations; no source-interpretation or deployed-runtime proof.'},indent=2)+'\n')
    results.append({'id':'MonographLogic', 'status':response.get('status'), 'expected_difference':False})
    manifest={'tool_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd='/home/chakwong/python/MathDevMCP',text=True).strip(),
              'environment':ENV,'results':results,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in {'.json','.lean'} and p.name != 'manifest.json'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(results,indent=2))
    assert all(r['status'] == ('mismatch' if r['expected_difference'] else 'verified' if r['id'] == 'MonographLogic' else 'equivalent') for r in results), 'A bounded obligation did not reach its expected verdict; inspect the retained response.'


if __name__=='__main__':
    if '--lean-worker' in sys.argv:
        from mathdevmcp.lean_check import check_lean_source
        print(json.dumps(check_lean_source((OUT/'MonographLogic.lean').read_text(),allow_sorry=False)))
    else:
        main()
