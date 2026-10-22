"""Staged partial solver evaluation under the existing prospectus authority."""
import argparse
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from scripts.prospectus_solver_corpus_v2 import run as evaluate,check_record,require,SOURCE_TEXT

PLAN='docs/plans/prospectus-solver-corpus-repair-2026-10-17.md'
REVIEW=REL+'/reviews/solver-corpus-r2'
DONOR=REL+'/attempts/source-bes-dep-06/attempt-011'
RUNTIME='.localresources/prospectus/report-installed-a264ahb5/environment/bin/python'
RUNNER='scripts/prospectus_solver_corpus_runner_v2.py'
WORKER='scripts/prospectus_solver_installed_worker_v2.py'
NEW_METHODS=(RUNNER,WORKER,'scripts/prospectus_solver_corpus_v2.py','tests/prospectus/test_solver_corpus.py',PLAN)
BOUNDS={'preparation_seconds':60,'source_seconds':120,'installed_seconds':120,'verify_seconds':120,
        'seal_seconds':120,'incremental_seconds':540,'new_bytes':48*1024**2,'reserve_bytes':1024**2}

def package(folder):
    return {str(p.relative_to(folder)):file_hash(p) for p in folder.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def load(path):
    with gzip.open(path,'rt') as stream: return json.load(stream)

def compressed(path,value):
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),mtime=0))

def storage(attempt,revision):
    paths={ROOT/n for n in NEW_METHODS}
    folders=[ROOT/REL/'reviews/solver-corpus',ROOT/REVIEW,ROOT/REL/'attempts/reasoning-corpus/attempt-006',attempt]
    paths|={p for d in folders for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths|=set((ROOT/REL/'proposals').glob('solver-corpus-22*.json'))
    paths|=set((ROOT/REL).glob('closure-routes-2026-10-17-after-components-22*.json'))
    paths|={ROOT/REL/'revisions/0222.json',ROOT/REL/'revisions'/f'{revision:04d}.json'}
    total=sum(p.stat().st_size for p in paths if p.is_file())
    require(total+BOUNDS['reserve_bytes']<=BOUNDS['new_bytes'],'Cumulative solver repair storage ceiling')
    return total

def frozen(task):
    value=read(ROOT/task['solver_corpus']['review']/'frozen.json')
    require(value['files']=={n:file_hash(ROOT/n) for n in value['files']},'Solver corpus frozen files changed')
    require(value['package']==package(ROOT/'src/legalmath')==package(ROOT/DONOR/'installed/legalmath'),'Current/installed package drift')
    return value

def run_stage(attempt_name,stage):
    auth=Authority(ROOT); program,tasks,_=auth.spec(); attempt=auth.path(attempt_name)
    admission=read(attempt/'admission.json'); task=tasks[admission['task']]
    require(task['id']=='reasoning-corpus' and task.get('validator') is None,'Wrong reasoning disposition')
    require(admission['program_sha256']==digest(program) and admission['binding']==auth.binding(task),'Changed admission')
    event=next(e for e in reversed(auth.events()) if e.get('task')==task['id'])
    require(event['kind']=='ADMIT' and event['attempt']==attempt_name,'Inactive solver admission')
    stages=['source','installed','verify','seal']; require(stage in stages,'Unknown stage')
    for previous in stages[:stages.index(stage)]:
        require(read(attempt/'stages'/previous/'result.json')['status']=='PASS','Earlier solver stage failed')
    target=attempt/'stages'/stage; target.mkdir(parents=True,exist_ok=False)
    f=frozen(task); start=time.monotonic(); status,error='PASS',None; details={}
    write(target/'started.json',{'command':[sys.executable,'-m','scripts.prospectus_solver_corpus_runner_v2','run','--attempt',attempt_name,'--stage',stage],
        'git_commit':admission['git_commit'],'plan':PLAN,'environment':{'executable':sys.executable,'version':sys.version},
        'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'Z3 random_seed=0; deterministic corpus',
        'data_version':file_hash(ROOT/REVIEW/'frozen.json'),'result':str((target/'result.json').relative_to(ROOT))},exclusive=True)
    def expired(_s,_f): raise TimeoutError('Solver stage exceeds120seconds')
    signal.signal(signal.SIGALRM,expired); signal.alarm(120)
    try:
        fixture=ROOT/REL/'reviews/solver-corpus/fixture'
        if stage=='source':
            write(attempt/'source-package.json',f['package'],exclusive=True)
            value=evaluate(ROOT,fixture); details=check_record(value)
            compressed(attempt/'source-record.json.gz',value)
            write(attempt/'source-checks.json',details,exclusive=True)
        elif stage=='installed':
            argv=[str(ROOT/RUNTIME),'-I','-B',str(ROOT/WORKER),str(ROOT),str(ROOT/DONOR/'installed'),str(fixture),str(attempt)]
            write(target/'command.json',{'argv':argv,'timeout':115},exclusive=True)
            with (target/'worker.log').open('x') as log:
                subprocess.run(argv,cwd=ROOT,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=115,check=True)
            require(load(attempt/'source-record.json.gz')==load(attempt/'installed-record.json.gz'),'Complete source/installed records differ')
            details=read(attempt/'installed-checks.json')
        elif stage=='verify':
            source,installed=load(attempt/'source-record.json.gz'),load(attempt/'installed-record.json.gz')
            require(source==installed,'Retained installed corpus differs')
            details=check_record(source)
            require(details==read(attempt/'source-checks.json')==read(attempt/'installed-checks.json'),'Retained independent checks differ')
            proof=read(attempt/'installed-proof.json')
            require(proof['isolated']==1 and proof['guard']=={'blocked':0} and proof['package_files']==450,'Invalid installed proof')
            require(proof['python']==str(ROOT/RUNTIME) and proof['z3_version']=='4.16.0','Wrong solver runtime')
            for name,row in proof['modules'].items():
                path=Path(row['path']); pkg=(ROOT/DONOR/'installed/legalmath').resolve()
                require(path.is_relative_to(pkg) and file_hash(path)==row['sha256']==f['package'][str(path.relative_to(pkg))],'Wrong installed module')
            z3path=Path(proof['z3_module']['path'])
            require(z3path.is_relative_to((ROOT/RUNTIME).parent.parent.resolve()) and file_hash(z3path)==proof['z3_module']['sha256'],'Wrong installed solver module')
            details['installed_provenance_verified']=True
            write(attempt/'verification.json',details,exclusive=True)
        else:
            details=read(attempt/'verification.json')
            elapsed=sum(read(attempt/'stages'/s/'result.json')['seconds'] for s in stages[:-1])
            write(attempt/'result.json',{'task':task['id'],'status':'PASS','scope':'PARTIAL_SOLVER_CORPUS','whole_task_complete':False,
                'whole_program_complete':False,'summary':details,'wall_seconds':elapsed},exclusive=True)
            (attempt/'RESULT.md').write_text('# Current source and installed solver corpus\n\nThe declared Boolean consequences, witnesses and inconsistent cores pass independent checks. Complete source and installed records agree. This is partial engineering evidence; original legal-meaning and explanation-minimality obligations remain open.\n\n'+json.dumps(details,sort_keys=True)+'\n\n| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n|---|---|---|---|---|---|\n| Retain partial solver evidence | Exact conditional results, controls and installed identity | No declared veto | Supplied meanings and wider source completeness | Record, refresh, inspect substantive gaps | No whole-task or legal-truth promotion |\n')
        frozen(task); details['new_bytes']=storage(attempt,program['revision'])
        elapsed=read(ROOT/REVIEW/'preparation.json')['seconds']+time.monotonic()-start
        elapsed+=sum(read(attempt/'stages'/s/'result.json')['seconds'] for s in stages[:stages.index(stage)])
        require(elapsed<=BOUNDS['incremental_seconds'],'Cumulative solver time ceiling')
    except Exception as exc:
        status,error='FAIL',type(exc).__name__+': '+str(exc)
        (target/'failure-trace.txt').write_text(traceback.format_exc(limit=12))
    finally:
        signal.alarm(0)
    write(target/'result.json',{'status':status,'error':error,'seconds':time.monotonic()-start,'details':details},exclusive=True)
    if stage=='seal' and status=='PASS':
        write(attempt/'outputs.json',{str(p.relative_to(attempt)):file_hash(p) for p in sorted(attempt.rglob('*')) if p.is_file() and p.name!='outputs.json'},exclusive=True)
    print(json.dumps({'stage':stage,'status':status,'error':error,'seconds':time.monotonic()-start}))
    return int(status!='PASS')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['run'])
    p.add_argument('--attempt'); p.add_argument('--stage'); args=p.parse_args()
    return run_stage(args.attempt,args.stage)

if __name__=='__main__':
    raise SystemExit(main())
