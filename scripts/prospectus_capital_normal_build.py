"""Bounded normal wheel build and isolated use of the unchanged capital profile."""
from datetime import datetime, timezone
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONPATH='')
from legalmath.prospectus.execution_authority import Authority,digest,file_hash,read
from scripts import prospectus_2010_capital_install as old

BASE=old.BASE
HERE=old.SOURCE/'attempt-014'
REVIEW=BASE/'reviews/capital-normal-build-194'
PLAN='docs/plans/prospectus-capital-normal-build-2026-10-17.md'
ROUTES=BASE/'closure-routes-2026-10-17-capital-normal-build-194.json'
REVIEW_FILE=BASE/'proposals/capital-normal-build-194-review.json'
WRAPPER=old.WRAPPER
STAGES=('prepare','wheel','install','installed-candidate-products','installed-candidate-answer','installed-input-a','installed-phase-c','seal')
CHILDREN=STAGES[1:-1]
SELECTOR={'version':'capital-v2-normal-build.v1','stages':list(STAGES),'children':list(CHILDREN),
          'new_seconds':260,'combined003_onward_seconds':1960,'new_bytes':20*1024**2,
          'combined003_onward_bytes':220*1024**2,'reserve_bytes':512*1024,
          'work_seconds':45,'stage_seconds':50,'child_seconds':35,'child_file_bytes':2*1024**2,
          'new_installed_refusals':4,'historical_unrepeated_refusals':10,
          'extraction_OCR_render_network_model_GPU_dependency_install_production_git_retries':0}
require=old.require
files=old.previous.cases.legacy.package_files


def support():
    return {p for p in REVIEW.rglob('*') if p.is_file()}|{Path(__file__),ROOT/PLAN,ROUTES,REVIEW_FILE}


def storage():
    paths=support()|{p for p in HERE.rglob('*') if p.is_file()}
    now=sum(p.stat().st_size for p in paths if p.is_file())
    history=read(REVIEW/'history.json')
    return {'previous_bytes':history['previous_bytes'],'new_bytes':now,
            'combined_bytes':history['previous_bytes']+now,'previous_seconds':history['previous_seconds']}


def space(additional=0,failure=False):
    now=storage(); reserve=0 if failure else SELECTOR['reserve_bytes']
    require(now['new_bytes']+additional<SELECTOR['new_bytes']-reserve and
            now['combined_bytes']+additional<SELECTOR['combined003_onward_bytes']-reserve,
            'Normal-build cumulative storage/reserve exhausted')
    return now


def save(name,value,failure=False):
    data=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()+b'\n'
    space(len(data),failure)
    path=HERE/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(data)


def historical():
    detail=old.historical()
    history=read(REVIEW/'history.json')
    require(old.storage()['combined_bytes']==history['previous_bytes'],'Historical cumulative storage changed')
    require(files(old.HERE)==history['attempt013_files'],'Sealed013 files changed')
    authority=Authority(ROOT)
    require(all(authority.retained_evidence_valid(e) for e in history['retained_events']),'Historical source09 outcome changed')
    require(files(ROOT/'src/legalmath')==history['package'],'Current package changed')
    return detail


def bindings():
    authority=Authority(ROOT);program,tasks,_=authority.spec();task=tasks['source-bes-dep-09']
    admission=read(HERE/'admission.json')
    event=next(e for e in reversed(authority.events()) if e.get('task')==task['id'])
    require(event['kind']=='ADMIT' and event['attempt']==str(HERE.relative_to(ROOT)) and
            event['admission_sha256']==file_hash(HERE/'admission.json') and
            admission['task_spec']==task and task['capital_normal_build']==SELECTOR and
            admission['program_sha256']==digest(program) and admission['binding']==authority.binding(task),
            'Unchanged normal-build admission required')
    require(not (HERE/'outputs.json').exists(),'Normal build already sealed')
    require(not (REVIEW/'proposal.pending.json').exists() and (REVIEW/'transport-retirement.json').is_file(),
            'Verified proposal retirement required')
    historical()
    if (HERE/'final-methods.json').exists():
        require(all(file_hash(ROOT/p)==h for p,h in read(HERE/'final-methods.json').items()),'Frozen normal-build method changed')
    return admission


def prepare():
    save('final-package.json',read(REVIEW/'history.json')['package'])
    save('final-methods.json',{str(p.relative_to(ROOT)):file_hash(p) for p in sorted(support()|{WRAPPER,ROOT/'pyproject.toml'})})
    save('resource-contract.json',{'selector':SELECTOR,'forecast':read(REVIEW/'preflight.json'),'current':storage()})
    return {'normal_build_not_previously_evaluated':True,'package_files':441,'prior_outcomes':13}


def command(stage):
    python=str(Path(read(old.previous.REVIEW/'history.json')['build_environment']['path'])/'bin/python')
    if stage=='wheel':
        return [python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
                '--wheel-dir',str(HERE/'wheel'),str(HERE/'build-source')]
    if stage=='install':
        wheel=read(HERE/'built-wheel.json')
        require(file_hash(HERE/wheel['path'])==wheel['sha256'],'Fresh wheel changed')
        return [python,'-I','-B','-m','pip','install','--no-deps','--no-index','--no-compile',
                '--target',str(HERE/'installed'),str(HERE/wheel['path'])]
    return [python,'-I','-B',str(WRAPPER),str(ROOT),str(old.OLD),str(HERE),stage.removeprefix('installed-')]


def wheel_validation():
    wheel,=tuple((HERE/'wheel').glob('*.whl'))
    baseline=old.OLD/'wheel/legalmath-0.1.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as fresh,zipfile.ZipFile(baseline) as prior:
        record=old.previous.validate_record(fresh)
        require(old.previous.validate_record(prior)==record,'Normal-build RECORD path changed')
        require(set(fresh.namelist())==set(prior.namelist()) and fresh.testzip() is None and prior.testzip() is None,
                'Normal-build archive inventory/integrity differs')
        require(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in fresh.namelist()),'Unsafe archive entry')
        differences=[n for n in fresh.namelist() if n!=record and fresh.read(n)!=prior.read(n)]
        require(not differences,'Normal-build package/distribution metadata differs: '+','.join(differences))
        def record_rows(z):return sorted(csv.reader(io.StringIO(z.read(record).decode())))
        require(record_rows(fresh)==record_rows(prior),'Normal-build RECORD semantics differ')
        package={n.removeprefix('legalmath/'):hashlib.sha256(fresh.read(n)).hexdigest() for n in fresh.namelist() if n.startswith('legalmath/')}
        require(package==read(HERE/'final-package.json'),'Fresh wheel package differs')
    save('built-wheel.json',{'path':str(wheel.relative_to(HERE)),'sha256':file_hash(wheel),'bytes':wheel.stat().st_size,
         'baseline_sha256':file_hash(baseline),'package_files':len(package),'all_non_RECORD_entry_bytes_equal':True,
         'RECORD_semantics_equal':True,'normal_build':True,'wheel_container_byte_identity_required':False})


def child(stage):
    if stage=='wheel':
        space(3*4328229+3*1364403+1024**2)
        source=HERE/'build-source';source.mkdir()
        shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
        shutil.copytree(ROOT/'src/legalmath',source/'src/legalmath',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        require(files(source/'src/legalmath')==read(HERE/'final-package.json'),'Staged source differs')
    if stage=='install':require(not (HERE/'installed').exists(),'Existing install target refused')
    argv=command(stage)
    temporary=HERE/'temporary';temporary.mkdir(exist_ok=True)
    env={'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
         'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_CACHE_DIR':'1','PIP_CONFIG_FILE':'/dev/null',
         'TMPDIR':str(temporary),'TMP':str(temporary),'TEMP':str(temporary)}
    save('commands/'+stage+'/command.json',{'argv':argv,'cwd':str(HERE),'environment':env,'timeout':35,
         'reservation':CHILDREN.index(stage)+1,'build_backend_internal_processes_counted':False,
         'child_per_file_limit':SELECTOR['child_file_bytes']})
    folder=HERE/'commands'/stage
    stop=threading.Event();observed={'peak_new_bytes':storage()['new_bytes'],'error':None}
    def file_limit():resource.setrlimit(resource.RLIMIT_FSIZE,(SELECTOR['child_file_bytes'],SELECTOR['child_file_bytes']))
    tick=time.monotonic()
    with (folder/'stdout').open('xb') as out,(folder/'stderr').open('xb') as err:
        process=subprocess.Popen(argv,cwd=HERE,env={**os.environ,**env},stdout=out,stderr=err,
                                 start_new_session=True,preexec_fn=file_limit)
        def monitor():
            while not stop.is_set():
                try:
                    now=space();observed['peak_new_bytes']=max(observed['peak_new_bytes'],now['new_bytes'])
                except FileNotFoundError:
                    pass  # pip may retire a transient file between listing and stat
                except BaseException as exc:
                    observed['error']=str(exc)
                    try:os.killpg(process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    return
                stop.wait(0.1)
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
        try:
            process.wait(timeout=35)
        except BaseException:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait(timeout=2)
            raise
        finally:
            stop.set();watcher.join(timeout=1)
    save('commands/'+stage+'/result.json',{'returncode':process.returncode,'wall_seconds':time.monotonic()-tick,
         'storage_monitor':observed},failure=bool(observed['error']))
    require(process.returncode==0 and observed['error'] is None,'Normal-build child failed: '+stage)
    require(all((folder/n).stat().st_size<65536 for n in ('stdout','stderr')),'Unexpected child diagnostic size')
    if stage=='wheel':wheel_validation()
    elif stage=='install':require(files(HERE/'installed/legalmath')==read(HERE/'final-package.json'),'Fresh installed package differs')
    else:require(read(HERE/'installed-checks'/(stage.removeprefix('installed-')+'.json'))['status']=='PASS','Installed comparison missing')
    return {'child':stage,'returncode':process.returncode,'peak_new_bytes':observed['peak_new_bytes']}


def seal():
    require((HERE/'RESULT.md').is_file(),'Actual normal-build result required')
    for name in CHILDREN[2:]:
        require(read(HERE/'installed-checks'/(name.removeprefix('installed-')+'.json'))['status']=='PASS','Missing actual comparison')
    require(files(HERE/'installed/legalmath')==read(HERE/'final-package.json'),'Installed package drift')
    save('verified-result.json',{'normal_build_evaluated':True,'package_files':441,'installed_actions':4,
         'new_installed_refusals':4,'other_historical_refusals':10,'prior012_outcome':'FAIL/REJECT',
         'task_complete':False,'program_complete':False,'independent_acceptance':False,
         'result_sha256':file_hash(HERE/'RESULT.md'),'wheel':read(HERE/'built-wheel.json')})
    return {'finite_normal_build_verified':True,'task_complete':False}


def run(stage):
    with Authority(ROOT).lock():
        admitted=bindings();index=STAGES.index(stage)
        require({p.parent.name for p in (HERE/'stages').glob('*/started.json')}==
                {p.parent.name for p in (HERE/'stages').glob('*/result.json')}==set(STAGES[:index]),'Repeated/skipped/interrupted stage')
        previous=[read(HERE/'stages'/s/'result.json') for s in STAGES[:index]]
        require(all(r['status']=='PASS' and r['wall_seconds']<50 for r in previous),'Failed predecessor stage')
        spent=sum(r['wall_seconds'] for r in previous);before=space()
        require(spent<260 and before['previous_seconds']+spent<1960,'Cumulative normal-build time exhausted')
        save('stages/'+stage+'/started.json',{'command':['timeout','55','.venv/bin/python','-m','scripts.prospectus_capital_normal_build',stage],
             'at':datetime.now(timezone.utc).isoformat(),'git_commit':admitted['git_commit'],'python':sys.executable,
             'CPU_GPU':'CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPUs','random_seeds':'N/A deterministic',
             'data_version':str(old.OLD.relative_to(ROOT)),'plan':PLAN,'result':str((HERE/'RESULT.md').relative_to(ROOT))})
        tick=time.monotonic();details=error=None
        def expire(signum,frame):raise TimeoutError('Normal-build stage limit; no unchanged retry')
        prior=signal.signal(signal.SIGALRM,expire)
        signal.setitimer(signal.ITIMER_REAL,min(45,260-spent,1960-before['previous_seconds']-spent))
        try:
            commands=[command(stage)] if stage in CHILDREN else []
            with old.previous.execution_guard(commands) as guard:details=child(stage) if commands else globals()[stage]()
            require(guard.result()=={'starts':len(commands),'blocked':0},'Unexpected process/network action')
            details['process_guard']=guard.result();bindings();space()
            elapsed=time.monotonic()-tick
            require(elapsed<50 and spent+elapsed<260 and before['previous_seconds']+spent+elapsed<1960,'Cumulative execution bound exceeded')
        except BaseException as exc:
            error={'type':type(exc).__name__,'message':str(exc)}
            save('stages/'+stage+'/error.json',{'traceback':traceback.format_exc()},failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior)
        result={'stage':stage,'status':'FAIL' if error else 'PASS','error':error,'details':details,
                'wall_seconds':time.monotonic()-tick,'bounds':storage(),
                'timing_scope':'Body plus final binding checks; historical startup/final-receipt exclusion retained'}
        result['cumulative_seconds']=spent+result['wall_seconds']
        save('stages/'+stage+'/result.json',result,failure=bool(error))
        if error or stage=='seal':
            save('result.json',{**result,'task':'source-bes-dep-09','task_complete':False,'program_complete':False},failure=bool(error))
            save('outputs.json',files(HERE),failure=bool(error))
        print(json.dumps({k:result[k] for k in ('stage','status','error','wall_seconds','cumulative_seconds')}))
        return int(error is not None)


if __name__=='__main__':raise SystemExit(run(sys.argv[1]))
