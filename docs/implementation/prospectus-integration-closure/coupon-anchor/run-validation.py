"""Serial coupon validation with exact regression coverage and phase receipts."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'docs/implementation/prospectus-integration-closure'
PACKAGE=BASE/'coupon-anchor'
PLAN=ROOT/'docs/plans/prospectus-coupon-anchor-repair-2026-10-10.md'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.successor import closure_program

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def method():
    paths=[*sorted((ROOT/'src/legalmath').rglob('*.py')),
        *sorted((ROOT/'tests/prospectus_successor').glob('*.py')),
        *sorted((ROOT/'scripts').glob('prospectus_closure_*.py')),
        ROOT/'tests/prospectus/test_closure_mechanisms.py',ROOT/'scripts/prospectus_delivery.py',
        ROOT/'pyproject.toml',PLAN,PACKAGE/'execution-admission.json',
        *sorted(PACKAGE.glob('*.py')),*sorted(BASE.glob('basf-*/review.json'))]
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}

def suite_counts(path):
    return {k:sum(int(s.get(k,0)) for s in ET.parse(path).getroot().iter('testsuite')) for k in ('tests','failures','errors','skipped')}

def main():
    if sys.flags.optimize:
        raise RuntimeError('Validation requires Python assertions enabled')
    # Dedicated subprocess collection keeps pytest state out of the supervisor.
    if len(sys.argv)==3 and sys.argv[1]=='--collect':
        import pytest
        class Inventory:
            def pytest_collection_finish(self,session):
                rows=[]
                for item in session.items:
                    parts=item.nodeid.split('::')
                    filename=parts[0]
                    classname=filename[:-3].replace('/','.')
                    if len(parts)>2:
                        classname+='.'+'.'.join(parts[1:-1])
                    rows.append({'nodeid':item.nodeid,'classname':classname,'name':parts[-1]})
                save(Path(sys.argv[2]),rows)
        raise SystemExit(pytest.main(['-q','--collect-only','tests/prospectus_successor',
            'tests/prospectus/test_closure_mechanisms.py'],plugins=[Inventory()]))
    assert len(sys.argv)==1
    admission=read(PACKAGE/'execution-admission.json')
    assert admission['status']=='INTEGRATED_VALIDATION_PENDING'
    baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert baseline==admission['baseline_git_commit']
    folder=PACKAGE/'validation-001'
    assert not folder.exists(), 'Inspect the retained attempt; do not rerun an unchanged failed method'
    folder.mkdir()
    python=str(ROOT/'.venv/bin/python')
    expected=method()
    started=dict(version='coupon-anchor-validation.v1',status='RUNNING',method=expected,
        baseline_git_commit=baseline,started_at=datetime.now(timezone.utc).isoformat(),
        plan_file=str(PLAN.relative_to(ROOT)),environment={'python':sys.executable,'version':sys.version,'CUDA_VISIBLE_DEVICES':'-1'},
        cpu_gpu='CPU; GPU intentionally hidden; no probe',seeds='Deterministic examples; inherited Hypothesis cases retain their settings',
        data_version='Source-bound synthetic coupon controls and retained predecessor source packets',
        scope='Partitioned full regression with exact node union and actual phase receipts; no legal completion claim')
    save(folder/'started.json',started)
    progress={'status':'RUNNING','active':None,'completed':[]}
    def save_progress():
        save(folder/'progress.json',progress)
    def run(label,argv,limit,xml=None):
        assert method()==expected,'Method drift before '+label
        progress['active']=label
        save_progress()
        before=dict(command=argv,timeout_seconds=limit,git_commit=baseline,method=expected,
            started_at=datetime.now(timezone.utc).isoformat(),cpu_gpu=started['cpu_gpu'],
            environment=started['environment'],seeds=started['seeds'],data_version=started['data_version'],
            plan_file=started['plan_file'],result_file=str((folder/(label+'-result.json')).relative_to(ROOT)))
        save(folder/(label+'-started.json'),before)
        print(json.dumps({'starting':label,'limit':limit,'command':argv}),flush=True)
        tick=time.monotonic()
        try:
            completed=subprocess.run(argv,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'},capture_output=True,timeout=limit)
            (folder/(label+'.log')).write_bytes(completed.stdout+completed.stderr)
            result=dict(status='PASS' if completed.returncode==0 else 'FAIL',returncode=completed.returncode)
            if xml:
                counts=suite_counts(xml)
                result.update(counts=counts,xml_sha256=sha(xml),xml=str(xml.relative_to(ROOT)))
                if counts['tests']<1 or any(counts[k] for k in ('failures','errors','skipped')):
                    result['status']='FAIL'
            result['method_unchanged']=method()==expected
            if not result['method_unchanged']:
                result['status']='FAIL'
        except subprocess.TimeoutExpired as exc:
            (folder/(label+'.log')).write_bytes((exc.stdout or b'')+(exc.stderr or b''))
            result=dict(status='TIMEOUT',error='Reviewed bound exceeded; inspect before retry')
        result['wall_seconds']=time.monotonic()-tick
        save(folder/(label+'-result.json'),result)
        print(json.dumps({'completed':label,**result}),flush=True)
        if result['status']!='PASS':
            progress.update(status='REVIEW_REQUIRED',failed=label)
            save_progress()
            raise RuntimeError('Validation failed at '+label)
        progress['completed'].append({'label':label,'wall_seconds':result['wall_seconds']})
        progress['active']=None
        save_progress()
        return result
    tick=time.monotonic()
    try:
        inventory=folder/'inventory.json'
        run('collection',[python,str(Path(__file__)),'--collect',str(inventory)],60)
        rows=read(inventory)
        universe={r['nodeid'] for r in rows}
        keys={(r['classname'],r['name']):r['nodeid'] for r in rows}
        assert len(keys)==len(universe)==len(rows)>0,'Ambiguous test identities'
        covered=set()
        evidence=[]
        def include(label,xml):
            counts=suite_counts(xml)
            assert counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
            cases=list(ET.parse(xml).getroot().iter('testcase'))
            assert len(cases)==counts['tests']
            ids=[]
            for case in cases:
                key=(case.get('classname'),case.get('name'))
                assert key in keys,('Unmapped executed case',key)
                ids.append(keys[key])
            assert len(ids)==len(set(ids)), 'Duplicate execution identities within a suite'
            covered.update(ids)
            evidence.append({'label':label,'xml':str(xml.relative_to(ROOT)),'sha256':sha(xml),'nodes':ids,'counts':counts})
        xml=folder/'focused.xml'
        run('focused',[python,'-m','scripts.prospectus_delivery','--program','closure','check',
            'tests/prospectus_successor/test_closure_coupon_anchor.py','tests/prospectus_successor/test_closure_finance.py',
            '--junitxml='+str(xml)],120,xml)
        include('focused',xml)
        run('consumer',[python,str(PACKAGE/'run-consumer.py')],140)
        assert read(PACKAGE/'attempt-001/result.json')['status']=='PASS'
        run('installed',['timeout','1260',python,'-m','scripts.prospectus_closure_install',
            'application','--basf-status-pledge','--coupon-anchor'],1280)
        installed=BASE/'installed/attempt-015'
        assert read(installed/'result.json')['status']=='PASS'
        installed_rows=[read(installed/name) for name in ('installed-results.json','relocated-results.json','restored-results.json')]
        assert len(installed_rows[0]['questions'])==11
        assert installed_rows[0]['questions']==installed_rows[1]['questions']==installed_rows[2]['questions']
        assert installed_rows[0]['anchor_controls']==installed_rows[1]['anchor_controls']==installed_rows[2]['anchor_controls']
        phases=[]
        for phase in list(closure_program.DAG)[:-1]:
            row=next(r for r in closure_program.status(ROOT)['phases'] if r['phase']==phase)
            assert row['can_dispatch'],row
            run(phase,[python,'-m','scripts.prospectus_delivery','--program','closure','phase','--phase',phase],
                closure_program.PHASE_TIMEOUTS.get(phase,600)+120)
            row=next(r for r in closure_program.status(ROOT)['phases'] if r['phase']==phase)
            assert row['current'] and row['artifact_valid'] and row['execution']=='COMPLETED' and row['engineering_checks']=='PASS',row
            include(phase,ROOT/row['directory']/'tests.xml')
            phases.append(row)
        remainder=sorted(universe-covered)
        save(folder/'remaining-nodeids.json',remainder)
        if remainder:
            xml=folder/'remaining.xml'
            run('remaining',[python,'-m','scripts.prospectus_delivery','--program','closure','check',*remainder,
                '--junitxml='+str(xml)],600,xml)
            include('remaining',xml)
        assert covered==universe and method()==expected
        coverage=dict(version='coupon-anchor-regression-coverage.v1',status='PASS',
            inventory=str(inventory.relative_to(ROOT)),inventory_sha256=sha(inventory),
            unique_tests=len(universe),covered=len(covered),missing=[],unexpected=[],
            method=expected,method_unchanged=True,evidence=evidence,baseline_git_commit=baseline,
            scope='Union of current passing phase/focused/remainder tests; partitioned processes, not a single aggregate')
        save(folder/'coverage.json',coverage)
        run('attribution-update',[python,str(PACKAGE/'update-ledger.py')],60)
        run('R8',[python,'-m','scripts.prospectus_delivery','--program','closure','phase','--phase','R8'],720)
        status=closure_program.status(ROOT)
        assert all(r['current'] and r['artifact_valid'] and r['execution']=='COMPLETED' and r['engineering_checks']=='PASS' for r in status['phases'])
        assert read(BASE/'final-attribution.json')==read(ROOT/status['phases'][-1]['directory']/'attribution.json')
        save(folder/'final-status.json',status)
        progress.update(status='ENGINEERING_VALIDATION_COMPLETE',active=None,unique_tests=len(universe))
        result=dict(status='PASS',method_unchanged=method()==expected,unique_tests=len(universe),
            phases=status['phases'],wall_seconds=time.monotonic()-tick,
            program_complete=False,external_acceptance='NOT_ESTABLISHED')
    except Exception as exc:
        progress.update(status='REVIEW_REQUIRED',error=type(exc).__name__+': '+str(exc))
        result=dict(status='FAIL',error=progress['error'],wall_seconds=time.monotonic()-tick)
    save_progress()
    save(folder/'result.json',result)
    save(folder/'manifest.json',{'files':{str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}})
    print(json.dumps({'validation_directory':str(folder.relative_to(ROOT)),**result}),flush=True)
    if result['status']!='PASS':
        raise SystemExit(1)

if __name__=='__main__':
    main()
