"""Offline wheel and isolated actual consumers, with bounded command receipts."""
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from legalmath.prospectus.execution_authority import file_hash,read,write
from legalmath.prospectus.successor import process_ledger
HERE=ROOT/'docs/implementation/prospectus-execution-authority/attempts/native-candidates/attempt-007'
PRIOR=ROOT/'docs/implementation/prospectus-execution-authority/attempts/native-confinement/attempt-002'
PLAN='docs/plans/prospectus-installed-optionals-2026-10-15.md'
RUNNER=ROOT/'scripts/prospectus_installed_optional_runner.py'
CASES=('geometry','review','boundaries','regions','native-text')

def save(name,value):write(HERE/name,value,exclusive=True)
def workspace():return Path(read(HERE/'workspace.json')['directory'])
def python():return str(workspace()/'environment/bin/python')
def package_files(folder):
    return {str(p.relative_to(folder)):file_hash(p) for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
def bindings():
    a=read(HERE/'admission.json');assert not (HERE/'outputs.json').exists()
    assert all(file_hash(ROOT/p)==h for p,h in a['binding'].items());return a
def methods():
    return {str(p.relative_to(ROOT)):file_hash(p) for p in (Path(__file__),RUNNER,ROOT/'pyproject.toml',ROOT/PLAN)}

def prepare():
    old=Path(read(PRIOR/'workspace.json')['directory'])/'environment'
    assert old.is_dir()
    temp=Path(tempfile.mkdtemp(prefix='installed-optionals-',dir=ROOT/'.localresources/prospectus'))
    shutil.copytree(old,temp/'environment',symlinks=True)
    (temp/'source').mkdir();shutil.copyfile(ROOT/'pyproject.toml',temp/'source/pyproject.toml')
    shutil.copytree(ROOT/'src',temp/'source/src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
    shutil.copyfile(RUNNER,temp/'runner.py')
    save('workspace.json',{'directory':str(temp),'environment_cloned_from':str(old)})
    save('source-package.json',package_files(temp/'source/src/legalmath'))
    save('environment-metadata.json',{str(p.relative_to(temp/'environment')):file_hash(p)
         for p in (temp/'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    save('method-identities.json',methods())
    for p in methods():
        target=HERE/'method'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    process_ledger.create(HERE/'command-ledger.json',10,0,'Build,install,inventory,five API cases;two diagnostic repair starts;no native calls')
    (HERE/'installed-results').mkdir()
    return {'workspace':str(temp),'network_calls':0,'source_files':len(read(HERE/'source-package.json'))}

def run(name,argv):
    folder=HERE/'commands'/name;folder.mkdir(parents=True,exist_ok=False)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1',
         'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_CACHE_DIR':'1'}
    save('commands/'+name+'/started.json',{'argv':argv,'cwd':str(workspace()),
         'environment':{k:env[k] for k in ('CUDA_VISIBLE_DEVICES','PYTHONPATH','PYTHONNOUSERSITE','PIP_NO_INDEX')},'timeout':110})
    tick=time.monotonic()
    with (folder/'stdout').open('xb') as out,(folder/'stderr').open('xb') as err,process_ledger.observe(HERE/'command-ledger.json'):
        result=subprocess.run(argv,cwd=workspace(),env=env,stdout=out,stderr=err,timeout=110)
    save('commands/'+name+'/result.json',{'returncode':result.returncode,'wall_seconds':time.monotonic()-tick})
    assert result.returncode==0,'See retained '+name+' stdout/stderr'
    return {'returncode':0}

def build():
    (HERE/'wheel').mkdir()
    run('build',[python(),'-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
                '--wheel-dir',str(HERE/'wheel'),str(workspace()/'source')])
    wheels=list((HERE/'wheel').glob('*.whl'));assert len(wheels)==1
    result={'path':str(wheels[0].relative_to(HERE)),'sha256':file_hash(wheels[0])};save('built-wheel.json',result);return result
def install():
    wheel=read(HERE/'built-wheel.json');assert file_hash(HERE/wheel['path'])==wheel['sha256']
    return run('install',[python(),'-m','pip','install','--no-index','--no-deps','--force-reinstall',str(HERE/wheel['path'])])
def installed(stage):
    run(stage,[python(),'-I',str(workspace()/'runner.py'),str(HERE),str(ROOT),stage])
    return read(HERE/'installed-results'/stage/'result.json')
def compare():
    results={s:read(HERE/'installed-results'/s/'result.json') for s in ('inventory',*CASES)}
    assert all(r['status']=='PASS' and r['native_calls']==0 for r in results.values())
    package=workspace()/'environment/lib/python3.11/site-packages/legalmath'
    assert package_files(package)==read(HERE/'source-package.json')
    proofs={s:read(HERE/'installed-results'/s/'import-proof.json') for s in ('inventory',*CASES)}
    assert all(p['isolated']==1 for p in proofs.values())
    assert all(p['modules']==proofs['inventory']['modules'] for p in proofs.values())
    ledger=process_ledger.checked(HERE/'command-ledger.json')
    assert len(ledger['reservations'])==8
    controls=[row for s in CASES for row in read(HERE/'installed-results'/s/'controls.json')]
    assert len(controls)==9 and all(r.get('refused') or r.get('safely_unresolved') for r in controls)
    result={'status':'PASS','installed_optional_apis':list(CASES),'actual_controls':len(controls),
      'outer_commands':8,'native_calls':0,'exact_package_files':len(read(HERE/'source-package.json')),
      'full_outputs_match':True,'different_host_portability':False,'independent_legal_acceptance':False,
      'default_changed':False,'fresh_extraction_evaluated':False}
    save('comparison.json',result);return result

def main():
    stage=sys.argv[1];assert stage in {'prepare','build','install','inventory',*CASES,'compare'}
    ad=bindings();folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False)
    tick=time.monotonic();save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_installed_optionals',stage],
      'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
      'started_at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU only;CUDA_VISIBLE_DEVICES=-1','methods':methods()})
    def expired(s,f):raise TimeoutError('120-second installed optional stage bound')
    signal.signal(signal.SIGALRM,expired);signal.alarm(120)
    try:
        if stage!='prepare':assert methods()==read(HERE/'method-identities.json')
        result=installed(stage) if stage in ('inventory',*CASES) else globals()[stage]()
        bindings()
        size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())+sum(p.stat().st_size for p in workspace().rglob('*') if p.is_file())
        assert size<500*1024*1024
        outcome={'status':'PASS','details':result,'wall_seconds':time.monotonic()-tick}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':type(error).__name__+': '+str(error),'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/'+stage+'/result.json',outcome);print(json.dumps(outcome))

if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
