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
from scripts.prospectus_solver_corpus import run as evaluate,check_record,require,SOURCE_TEXT

PLAN='docs/plans/prospectus-solver-corpus-2026-10-17.md'
REVIEW=REL+'/reviews/solver-corpus'
DONOR=REL+'/attempts/source-bes-dep-06/attempt-011'
RUNTIME='.localresources/prospectus/report-installed-a264ahb5/environment/bin/python'
RUNNER='scripts/prospectus_solver_corpus_runner.py'
WORKER='scripts/prospectus_solver_installed_worker.py'
NEW_METHODS=(RUNNER,WORKER,'scripts/prospectus_solver_corpus.py','tests/prospectus/test_solver_corpus.py',PLAN)
BOUNDS={'preparation_seconds':60,'source_seconds':120,'installed_seconds':120,'verify_seconds':120,
        'seal_seconds':120,'incremental_seconds':540,'new_bytes':32*1024**2,'reserve_bytes':1024**2}

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
    paths|={p for d in (ROOT/REVIEW,attempt) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths|=set((ROOT/REL/'proposals').glob('solver-corpus-'+str(revision)+'*.json'))
    paths|={ROOT/REL/'revisions'/f'{revision:04d}.json'}
    total=sum(p.stat().st_size for p in paths if p.is_file())
    require(total+BOUNDS['reserve_bytes']<=BOUNDS['new_bytes'],'Solver corpus cumulative storage ceiling')
    return total

def frozen(task):
    value=read(ROOT/task['solver_corpus']['review']/'frozen.json')
    require(value['files']=={n:file_hash(ROOT/n) for n in value['files']},'Solver corpus frozen files changed')
    require(value['package']==package(ROOT/'src/legalmath')==package(ROOT/DONOR/'installed/legalmath'),'Current/installed package drift')
    return value

def prepare():
    started=time.monotonic(); signal.alarm(60)
    auth=Authority(ROOT); old,tasks,_=auth.spec(); require(old['revision']==221,'Expected revision221')
    review=ROOT/REVIEW; review.mkdir(parents=True,exist_ok=True)
    require(not (review/'frozen.json').exists(),'Preparation already frozen')
    task=tasks['reasoning-corpus']; require(task.get('validator') is None,'Whole-task finite promotion remains')
    history=[e for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
    require(len(history)==old['budgets'][task['budget_key']]['maximum_new_attempts']==5,'Expected original five admissions')
    last=next(e for e in reversed(auth.events()) if e.get('task')==task['id'])
    require(last['kind']=='RECORD' and auth.retained_evidence_valid(last),'Current finite result missing or changed')
    donor_event=next(e for e in reversed(auth.events()) if e.get('attempt')==DONOR and e['kind'] in {'RECORD','ACCEPT'})
    require(auth.retained_evidence_valid(donor_event),'Installed donor changed')
    require(read(ROOT/DONOR/'source-package.json')==package(ROOT/'src/legalmath')==package(ROOT/DONOR/'installed/legalmath'),'Wrong current installed wheel')
    fixture=review/'fixture'; fixture.mkdir(exist_ok=False)
    from scripts.prospectus_closure_fixtures import request
    write(fixture/'request.json',request(fixture,[SOURCE_TEXT]),exclusive=True)
    argv=[sys.executable,'-m','pytest','tests/prospectus/test_solver_corpus.py','-q','--junitxml='+str(review/'tests.xml')]
    with (review/'tests.log').open('x') as log:
        subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'},stdout=log,stderr=subprocess.STDOUT,timeout=30,check=True)
    from legalmath.prospectus.execution_acceptance import checked_tests
    tests=checked_tests(review/'tests.xml',7)
    import importlib.metadata as metadata
    require(metadata.version('z3-solver')=='4.16.0.0','Reviewed solver version changed')
    prep={'status':'PASS','seconds':time.monotonic()-started,'tests':tests,'test_command':argv,
        'diagnostic_smokes':{'failed':'Unbound clause: harness anchored before AST; no admitted candidate ran',
            'repaired_seconds':0.04162844456732273,'failed_elapsed':'UNKNOWN; short command exited1'},
        'historical_unrecorded_seconds':'UNKNOWN','cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'}
    write(review/'preparation.json',prep,exclusive=True)
    write(review/'history.json',{'admissions':history,'prior_record':last,'installed_donor':donor_event,
        'prior_attempt_bytes':sum(p.stat().st_size for p in (ROOT/REL/'attempts/reasoning-corpus').rglob('*') if p.is_file())},exclusive=True)
    files=set(task['inputs'])|set(NEW_METHODS)|{'scripts/prospectus_component_installed_worker.py','scripts/prospectus_closure_fixtures.py'}
    files|={str(p.relative_to(ROOT)) for p in review.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files|={DONOR+'/'+n for n in read(ROOT/DONOR/'outputs.json')}|{DONOR+'/outputs.json'}
    files|={'src/legalmath/'+n for n in package(ROOT/'src/legalmath')}
    files|={last['attempt']+'/'+n for n in read(ROOT/last['attempt']/'outputs.json')}|{last['attempt']+'/outputs.json'}
    import z3
    runtime={'executable':str((ROOT/RUNTIME).resolve()),'executable_sha256':file_hash((ROOT/RUNTIME).resolve()),
        'development_z3_path':str(Path(z3.__file__).resolve()),'development_z3_sha256':file_hash(Path(z3.__file__)),
        'z3_version':metadata.version('z3-solver')}
    write(review/'frozen.json',{'files':{n:file_hash(ROOT/n) for n in sorted(files)},'package':package(ROOT/'src/legalmath'),'runtime':runtime},exclusive=True)
    new=deepcopy(old); new['revision']=222
    current=next(t for t in new['tasks'] if t['id']==task['id'])
    current.update(dossier=PLAN,reason='Evaluate conditional BASF and larger-domain Z3 through source and installed products; preserve wider original acceptance',
        solver_corpus={'version':'solver-corpus.v1','review':REVIEW,'donor':DONOR,'bounds':BOUNDS},timeout_seconds=130)
    current['inputs']=sorted(files|{REVIEW+'/frozen.json'})
    new['budgets'][task['budget_key']]['maximum_new_attempts']=6
    mapping=read(ROOT/old['continuation_review']['routes']); new_tasks={t['id']:t for t in new['tasks']}
    completed={'source-bes-dep-06':'comparative011','basf-references':'pension010','source-bes-dep-05':'H1-unit018',
        'source-bes-dep-07':'cash-flow012','finance-conventions':'quantity005'}
    for row in mapping['tasks']:
        row['task_sha256']=digest(new_tasks[row['task']]); row['dossier']=new_tasks[row['task']]['dossier']
        if row['task']=='reasoning-corpus':
            row.update(phase=0,mode='local',next_action='Execute reviewed current and installed larger-domain Z3 corpus; preserve finite005 proof and partial acceptance; diagnose actual mismatches.',
                remaining='Finite005 independently checked; larger-domain Z3 downstream evidence, explanation minimality and source interpretation remain open.')
        elif row['task'] in completed:
            row.update(phase=2,next_action='Preserve installed '+completed[row['task']]+'; trace original source/financial gaps. Do not repeat the completed component replay.',
                remaining='Current installed '+completed[row['task']]+' passed; wider original acceptance remains incomplete.')
    routes=REL+'/closure-routes-2026-10-17-after-components-222.json'; write(ROOT/routes,mapping,exclusive=True)
    bindings=dict(old['continuation_review']['bindings'])
    require(all(file_hash(ROOT/n)==h for n,h in bindings.items()),'Continuation binding drift')
    for n in (PLAN,routes,REVIEW+'/preparation-notes.md',REL+'/continuation-reviews/reasoning-current-221-record/RESULT.md',
              REL+'/continuation-reviews/component-219-record/RESULT.md',REL+'/continuation-reviews/component-220-record/RESULT.md'):
        bindings[n]=file_hash(ROOT/n)
    new['continuation_review']={**new['continuation_review'],'plan':PLAN,'routes':routes,'bindings':bindings}
    audit={'baseline':digest(old),'changes':['Evaluate source and installed larger-domain solver corpus','Replace obsolete completed-component continuation advice'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'harness_repair':REVIEW+'/preparation-notes.md','finite_proof_not_task_completion':True},
        'evidence_contract':{'question':'Does explicit Z3 preserve declared consequences and downstream evidence?',
            'baseline':'Independent enumeration, original BASF profile, identical source/installed inputs',
            'primary':'404 cases, complete products, valid witnesses/cores, installed identity and negative controls',
            'veto':'Semantic mismatch, invalid artifact/source/import, missed control or resource overrun',
            'explanatory':['tests','runtime'],'not_concluded':['legal meaning','explanation minimality','unlimited solver correctness','whole-task completion']},
        'scope_unchanged':True,'budget_unchanged':False,
        'budget_revision':{'budget_key':task['budget_key'],'previous_maximum':5,'new_maximum':6,
            'retained_attempts':[e['attempt'] for e in history],'reason':'Close finite-only coverage gap with larger-domain installed solver evidence',
            'next_discriminating_check':'Independent 13/16-variable enumeration and actual source/installed P1-P5 consumers',
            'stop_condition':BOUNDS,'same_scope_authorization':'User-directed thorough general build and continued execution'}}
    write(ROOT/REL/'proposals/solver-corpus-222.json',new,exclusive=True)
    write(ROOT/REL/'proposals/solver-corpus-222-review.json',audit,exclusive=True)
    require(storage(ROOT/REL/'attempts/reasoning-corpus/attempt-006',222)<2*1024**2,'Preparation storage exceeds2MiB')
    signal.alarm(0)
    print(json.dumps({'prepared_revision':222,'tests':tests,'seconds':time.monotonic()-started,'partial_only':True}))

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
    write(target/'started.json',{'command':[sys.executable,'-m','scripts.prospectus_solver_corpus_runner','run','--attempt',attempt_name,'--stage',stage],
        'git_commit':admission['git_commit'],'plan':PLAN,'environment':{'executable':sys.executable,'version':sys.version},
        'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'Z3 random_seed=0; deterministic corpus',
        'data_version':file_hash(ROOT/REVIEW/'frozen.json'),'result':str((target/'result.json').relative_to(ROOT))},exclusive=True)
    def expired(_s,_f): raise TimeoutError('Solver stage exceeds120seconds')
    signal.signal(signal.SIGALRM,expired); signal.alarm(120)
    try:
        fixture=ROOT/REVIEW/'fixture'
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
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--attempt'); p.add_argument('--stage'); args=p.parse_args()
    if args.action=='prepare': return prepare()
    return run_stage(args.attempt,args.stage)

if __name__=='__main__':
    raise SystemExit(main())
