"""Debug only: compare existing local interfaces under the same anchor premise."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
BASE = ROOT/'docs/implementation/prospectus-integration-closure/finance-anchor-diagnostic'
PLAN = 'docs/plans/prospectus-coupon-anchor-diagnostic-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from legalmath.prospectus.successor import contract_terms, fixed_coupon

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    tick = time.monotonic()
    assert Path(contract_terms.__file__).resolve().is_relative_to(ROOT/'src')
    assert Path(fixed_coupon.__file__).resolve().is_relative_to(ROOT/'src')
    BASE.mkdir()
    copied = BASE/'run-diagnostic.py'
    copied.write_bytes(Path(__file__).read_bytes())
    paths = [Path(contract_terms.__file__), Path(fixed_coupon.__file__),
             ROOT/'tests/prospectus_successor/test_closure_finance.py', ROOT/PLAN, copied]
    method = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    record = {'version':'coupon-anchor-debug.v1', 'plan':PLAN,
        'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'command':['timeout','30','.venv/bin/python','/tmp/prospectus_coupon_anchor_diagnostic.py'],
        'environment':{'python':sys.executable,'version':sys.version,'CUDA_VISIBLE_DEVICES':'-1'},
        'cpu_gpu':'CPU; GPU intentionally hidden; no device probe', 'seeds':'N/A; deterministic exact date calculation',
        'started_at':datetime.now(timezone.utc).isoformat(), 'method':method,
        'data_version':'Existing month-end regression fixture in test_closure_finance.py',
        'timeout_seconds':30,'result_file':str((BASE/'result.json').relative_to(ROOT)),
        'result_note':str((BASE/'RESULT.md').relative_to(ROOT))}
    (BASE/'started.json').write_text(json.dumps(record,indent=2)+'\n')
    dates = contract_terms.regular_schedule('2023-08-30','2024-02-29','2024-08-30',2,False,'REGULAR')
    assert dates == ['2024-02-29','2024-08-30']
    references = [{'start':'2023-08-30','end':dates[0]}, {'start':dates[0],'end':dates[1]}]
    probes=[]
    for start, refs, expected in [('2024-02-29',references[1:],'1/2'), ('2023-08-30',references,'1')]:
        row = {'start':start,'end':'2024-08-30','references':refs,'expected_fraction_under_schedule':'{}'.format(expected)}
        try:
            row['computed_fraction'] = str(fixed_coupon.year_fraction(start,row['end'],'ACT_ACT_ICMA',references=refs,frequency=2,eom=False))
            row['agrees_with_schedule'] = row['computed_fraction']==expected
        except ValueError as exc:
            row.update(error=type(exc).__name__+': '+str(exc),agrees_with_schedule=False)
        probes.append(row)
    unchanged = method=={str(p.relative_to(ROOT)):sha(p) for p in paths}
    assert unchanged
    record.update(status='CONSISTENT' if all(p['agrees_with_schedule'] for p in probes) else 'LOCAL_INTERFACE_INCONSISTENCY',
        schedule=dates,probes=probes,method_unchanged=unchanged,wall_seconds=time.monotonic()-tick,
        packages_invoked=[],interpretation='Local schedule/reference admission disagree under the existing fixture; no real-instrument or third-party-package conclusion')
    assert record['wall_seconds'] < 30
    (BASE/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    (BASE/'manifest.json').write_text(json.dumps({'files':{p.name:sha(p) for p in BASE.iterdir() if p.is_file()}},indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('status','schedule','probes','wall_seconds','method_unchanged')}))

if __name__=='__main__':
    main()
