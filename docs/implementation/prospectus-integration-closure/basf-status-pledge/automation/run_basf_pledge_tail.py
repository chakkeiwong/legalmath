"""Continue serial validation, stopping only on failed evidence or bounds."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/home/chakwong/python/legalmath/.worktrees/bond-gap-closure')
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'basf-status-pledge'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.successor import closure_program

def read(p):
    return json.loads(p.read_text())

def main():
    focused=read(BASE/'checks/basf-pledge-001-manifest.json')
    assert focused['status']=='PASS' and focused['method_unchanged']
    assert focused['counts']==dict(tests=23,failures=0,errors=0,skipped=0)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in focused['method'].items())
    progress={'version':'basf-pledge-validation-progress.v1','completed':[], 'active':None,
        'status':'RUNNING','started_at':datetime.now(timezone.utc).isoformat(),
        'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'plan':'docs/plans/prospectus-basf-status-pledge-execution-2026-10-10.md'}
    target=PACKAGE/'validation-progress.json'
    assert not target.exists()
    def save():
        target.write_text(json.dumps(progress,indent=2)+'\n')
    def run(label,argv,bound):
        progress['active']=label
        save()
        started=time.monotonic()
        print(json.dumps({'starting':label,'command':argv,'bound':bound}),flush=True)
        try:
            result=subprocess.run(argv,cwd=ROOT,env=os.environ.copy(),timeout=bound)
        except subprocess.TimeoutExpired:
            progress.update(status='REVIEW_REQUIRED',error='Timeout at '+label)
            save()
            raise
        if result.returncode:
            progress.update(status='REVIEW_REQUIRED',error='Failed '+label,exit_code=result.returncode)
            save()
            raise SystemExit(1)
        progress['completed'].append({'label':label,'command':argv,'wall_seconds':time.monotonic()-started})
        progress['active']=None
        save()
    python=str(ROOT/'.venv/bin/python')
    run('consumer',['timeout','1260',python,'-m','scripts.prospectus_closure_basf_status_pledge'],1280)
    assert read(PACKAGE/'attempt-001/result.json')['status']=='PASS'
    run('installed',['timeout','1260',python,'-m','scripts.prospectus_closure_install','application','--basf-status-pledge'],1280)
    assert read(BASE/'installed/attempt-014/result.json')['status']=='PASS'
    run('aggregate',[python,str(PACKAGE/'run-check.py'),'aggregate'],4520)
    run('attribution-update',[python,'/tmp/update_basf_pledge_ledger.py'],60)
    phases={'version':'basf-pledge-phase-progress.v1','plan':progress['plan'],
        'baseline_commit':progress['baseline_commit'],'aggregate':'checks/successor-013.xml',
        'completed':[],'active':None,'remaining':list(closure_program.DAG),
        'status':'RUNNING','program_complete':False,'external_acceptance':'NOT_ESTABLISHED'}
    phase_path=PACKAGE/'phase-progress.json'
    assert not phase_path.exists()
    def save_phases():
        phase_path.write_text(json.dumps(phases,indent=2)+'\n')
    for phase in closure_program.DAG:
        row=next(r for r in closure_program.status(ROOT)['phases'] if r['phase']==phase)
        if not row['current']:
            assert row['can_dispatch'],row
            phases['active']=phase
            save_phases()
            run(phase,[python,'-m','scripts.prospectus_delivery','--program','closure','phase','--phase',phase],
                closure_program.PHASE_TIMEOUTS.get(phase,600)+120)
            row=next(r for r in closure_program.status(ROOT)['phases'] if r['phase']==phase)
        if not (row['current'] and row['artifact_valid'] and row['execution']=='COMPLETED' and row['engineering_checks']=='PASS'):
            phases.update(status='REVIEW_REQUIRED',failed=row)
            save_phases()
            progress.update(status='REVIEW_REQUIRED',failed=row)
            save()
            raise SystemExit(1)
        result=read(ROOT/row['directory']/'result.json')
        print(json.dumps({'phase':phase,'directory':row['directory'],'current':row['current'],
            'engineering_checks':row['engineering_checks'],'primary_criterion':row['primary_criterion'],
            'test_counts':result['test_counts'],'wall_seconds':result['wall_seconds']}),flush=True)
        phases['completed'].append(phase+'/'+row['directory'].rsplit('-',1)[-1])
        phases['remaining'].remove(phase)
        phases['active']=None
        save_phases()
    phases['status']='ENGINEERING_VALIDATION_COMPLETE'
    save_phases()
    assert read(BASE/'final-attribution.json')==read(ROOT/row['directory']/'attribution.json')
    run('final-evidence-index',[python,'/tmp/finalize_basf_pledge.py'],60)
    progress.update(status='ENGINEERING_VALIDATION_COMPLETE',active=None)
    save()
    print(json.dumps(progress),flush=True)

if __name__=='__main__':
    main()
