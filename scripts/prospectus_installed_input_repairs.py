"""One admitted installed replay of three repaired prospectus input boundaries."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True;os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash,digest
from scripts import prospectus_component_revalidation as component
from scripts.prospectus_input_repair_evidence import FOLDERS,DENOMINATORS,load,same,require,validate_record
PLAN='docs/plans/prospectus-installed-input-repairs-2026-10-17.md'
SCRIPT='scripts/prospectus_installed_input_repairs.py'
WORKER='scripts/prospectus_input_repair_worker.py'
EVALUATOR='scripts/prospectus_input_repair_evidence.py'
TEST='tests/prospectus/test_input_repair_evidence.py'
DONOR=REL+'/attempts/source-bes-dep-06/attempt-012'
BOUNDS={'preparation_seconds':60,'stage_seconds':60,'cumulative_seconds':300,'new_bytes':48*1024**2,
        'reserve_bytes':1024**2,'evaluator_subprocesses':2,'preparation_test_starts':1}

def methods():
    names={str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath').rglob('*')
           if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    names|={PLAN,SCRIPT,WORKER,EVALUATOR,TEST,'scripts/prospectus_component_installed_worker.py',component.SCRIPT,component.EVALUATOR}
    return {n:file_hash(ROOT/n) for n in sorted(names)}

def package_check(expected):
    donor=ROOT/DONOR
    require(read(donor/'source-package.json')==expected==component.package_files(ROOT/'src/legalmath')
            ==component.package_files(donor/'installed/legalmath'),'Source and shared installed package differ')
    wheel=read(donor/'wheel.json');require(file_hash(donor/wheel['file'])==wheel['sha256'],'Shared wheel changed')
    with zipfile.ZipFile(donor/wheel['file']) as z:
        actual={n.removeprefix('legalmath/'):hashlib.sha256(z.read(n)).hexdigest()
                for n in z.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(actual==expected,'Wheel contents differ')

def prepare():
    start=time.monotonic();auth=Authority(ROOT);old,tasks,_=auth.spec();revision=old['revision']+1
    review_name=REL+'/reviews/installed-input-repairs-'+str(revision)
    folder=ROOT/review_name;folder.mkdir(parents=True,exist_ok=False)
    write(folder/'started.json',{'command':['.venv/bin/python',SCRIPT,'prepare'],
          'at':datetime.now(timezone.utc).isoformat(),'plan':PLAN},exclusive=True)
    signal.alarm(60)
    try:
        manifests={};history=[];inputs=set(tasks['source-authority']['inputs'])
        for name in [*FOLDERS.values(),DONOR]:
            event=next(e for e in reversed(auth.events()) if e.get('attempt')==name and e['kind'] in {'RECORD','ACCEPT','REJECT'})
            require(auth.retained_evidence_valid(event),'Retained input evidence invalid')
            manifests[name]=file_hash(ROOT/name/'outputs.json')
            history.append({'attempt':name,'event':event['sha256'],'disposition':event['kind']})
            inputs|={name+'/'+n for n in read(ROOT/name/'outputs.json')}|{name+'/outputs.json'}
        sources={}
        for directory in ['document-time-validation','conversion-admission']:
            source=ROOT/REL/'reviews'/directory/'source-bindings.json'
            sources.update(read(source));inputs.add(str(source.relative_to(ROOT)))
        req=REL+'/reviews/document-time-validation/request.json';sources[req]=file_hash(ROOT/req)
        package=component.package_files(ROOT/'src/legalmath');package_check(package)
        argv=[sys.executable,'-c',
              'import sys;sys.path[:0]=[sys.argv[1],sys.argv[2]];import pytest;raise SystemExit(pytest.main(sys.argv[3:]))',
              str(ROOT/'src'),str(ROOT),'-q',TEST,'--junitxml='+str(folder/'tests.xml')]
        with (folder/'tests.log').open('x') as log:
            subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},
                           stdout=log,stderr=subprocess.STDOUT,timeout=30,check=True)
        count=component.checked_tests(folder/'tests.xml',4)
        config={'package':package,'manifests':manifests,'source_files':sources,'history':history,'donor':DONOR}
        write(folder/'config.json',config,exclusive=True)
        write(folder/'preparation.json',{'seconds':time.monotonic()-start,'tests':count,'test_command':argv,
              'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','historical_unmeasured_seconds':'UNKNOWN'},exclusive=True)
        mf=methods();inputs|=set(mf)|set(sources)|{str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()}
        frozen={'methods':mf,'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},'runtime':component.runtime_files()}
        write(folder/'frozen.json',frozen,exclusive=True)
        admissions=[e['attempt'] for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']=='source-authority']
        before=old['budgets']['source-authority']['maximum_new_attempts']
        require(before==4 and len(admissions)==before,'Expected four source-authority admissions')
        new=deepcopy(old);new['revision']=revision;t=next(t for t in new['tasks'] if t['id']=='source-authority')
        t.update(dossier=PLAN,reason='Verify assembled installed input boundaries; preserve complete interval,conversion and document-date evidence and original unknowns',
                 installed_input_repairs={'version':'installed-input-repairs.v1','review':review_name,'donor':DONOR,'bounds':BOUNDS})
        t['inputs']=sorted(set(t['inputs'])|inputs|{review_name+'/frozen.json'})
        new['budgets']['source-authority']['maximum_new_attempts']=before+1
        routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=revision
        for row in routes['tasks']:
            if row['task']=='source-authority':
                row.update(phase=0,task_sha256=digest(t),dossier=PLAN,
                           next_action='Execute source and isolated installed repair matrices,compare package/import/answer identities,seal,record and refresh.')
            if row['task']=='finance-conventions':
                row.update(phase=5,remaining='006 restores exact-quantity conditional criterion with full current/installed equality; original wider finance requirements remain.',
                           next_action='Preserve current installed criterion and continue distinct financial-domain gaps; do not repeat completed evidence.')
        route=REL+f'/closure-routes-2026-10-17-installed-repairs-{revision}.json';write(ROOT/route,routes,exclusive=True)
        new['continuation_review'].update(plan=PLAN,routes=route)
        for n in [PLAN,route,SCRIPT,EVALUATOR,WORKER,TEST]:new['continuation_review']['bindings'][n]=file_hash(ROOT/n)
        audit={'baseline':digest(old),'changes':['Execute three repair matrices from exact shared installed wheel','Retain original results and five current component criteria'],
               'skeptical_audit':{'verdict':'PASS','plan':PLAN,'tested_harness':review_name+'/tests.xml'},
               'evidence_contract':{'question':'Does assembled wheel deliver each retained repair through actual consumers?',
                   'baseline':history,'primary':'Full outputs/refusals agree;complete denominators and installed bytes/imports match',
                   'veto':'Wrong package,missing controls,changed answers,corrupt sources,unexpected actions or resource exhaustion',
                   'explanatory':['counts','runtime'],'not_concluded':['whole task','whole build','actual facts','legal truth','native boundary']},
               'scope_unchanged':True,'budget_unchanged':False,
               'budget_revision':{'budget_key':'source-authority','previous_maximum':before,'new_maximum':before+1,
                   'retained_attempts':admissions,'reason':'Previously unexecuted installed source-to-answer checks after shared input repairs',
                   'next_discriminating_check':'Three-family current/installed replay with complete old results and refusals',
                   'stop_condition':BOUNDS,'same_scope_authorization':'User-directed general build and continued thorough verification'}}
        write(ROOT/REL/'proposals'/f'installed-input-repairs-{revision}.json',new,exclusive=True)
        write(ROOT/REL/'proposals'/f'installed-input-repairs-{revision}-review.json',audit,exclusive=True)
        print(json.dumps({'revision':revision,'attempt':REL+'/attempts/source-authority/attempt-005','tests':count,'seconds':time.monotonic()-start}))
    except Exception as exc:
        write(folder/'failure.json',{'error':type(exc).__name__+': '+str(exc),'seconds':time.monotonic()-start},exclusive=True)
        raise
    finally:signal.alarm(0)

def run(name,stage):
    auth=Authority(ROOT);program,tasks,_=auth.spec();here=ROOT/name
    ad=read(here/'admission.json');task=tasks['source-authority']
    spec=task['installed_input_repairs'];review=ROOT/spec['review']
    frozen=read(review/'frozen.json');config=read(review/'config.json')
    require(spec['bounds']==BOUNDS and ad['binding']==auth.binding(task)
            and ad['program_sha256']==digest(program),'Active admission changed')
    event=next(e for e in reversed(auth.events()) if e.get('task')=='source-authority')
    require(event['kind']=='ADMIT' and event['attempt']==name,'Unclosed admitted attempt required')
    require(methods()==frozen['methods'] and component.runtime_files()==frozen['runtime'],'Frozen methods/runtime changed')
    require(all(file_hash(ROOT/n)==h for n,h in frozen['inputs'].items()),'Frozen input changed')
    package_check(config['package']);stages=('source','installed','seal');require(stage in stages,'Unknown stage')
    for previous in stages[:stages.index(stage)]:
        require(read(here/'stages'/previous/'result.json')['status']=='PASS','Prior stage did not pass')
    target=here/'stages'/stage;target.mkdir(parents=True,exist_ok=False);start=time.monotonic();signal.alarm(60)
    write(target/'started.json',{'command':['.venv/bin/python',SCRIPT,'run',name,stage],
          'at':datetime.now(timezone.utc).isoformat()},exclusive=True)
    try:
        if stage=='source':write(here/'config.json',config,exclusive=True)
        if stage!='seal':
            imported=ROOT/'src' if stage=='source' else ROOT/DONOR/'installed'
            argv=[str(component.runtime()/'bin/python'),'-I','-B',str(ROOT/WORKER),str(ROOT),str(here),str(imported),stage]
            env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1',
                 'PYTHONDONTWRITEBYTECODE':'1','PIP_NO_INDEX':'1'}
            write(target/'command.json',{'argv':argv,'cwd':str(here),'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','timeout':50},exclusive=True)
            with (target/'stdout').open('xb') as out,(target/'stderr').open('xb') as err:
                code=subprocess.run(argv,cwd=here,env=env,stdout=out,stderr=err,timeout=50).returncode
            require(code==0,'Actual repair consumer failed; retained stderr')
            result=read(here/(stage+'-result.json'));require(result['status']=='PASS','Missing actual pass')
            proof=read(here/(stage+'-proof.json'))
            require(proof['isolated']==1 and proof['guard']=={'blocked':0}
                    and proof['package_files']==len(config['package']),'Invalid runtime proof')
            require(Path(proof['prefix']).resolve()==component.runtime().resolve()
                    and Path(proof['python']).resolve()==(component.runtime()/'bin/python').resolve(),'Wrong runtime')
            require(proof['modules'] and all(Path(v['path']).is_relative_to(imported/'legalmath')
                    and file_hash(Path(v['path']))==v['sha256'] for v in proof['modules'].values()),'Wrong production imports')
            details=result['counts']
        else:
            source=load(here/'source-record.json.gz');installed=load(here/'installed-record.json.gz')
            same(installed,source,'source versus installed whole repair record')
            details=validate_record(installed);require(details==DENOMINATORS,'Missing matrix')
            require((here/'RESULT.md').is_file(),'Detailed result required before seal')
        require(methods()==frozen['methods'] and component.runtime_files()==frozen['runtime'],'Methods/runtime mutated during stage')
        package_check(config['package'])
        prep=read(review/'preparation.json')['seconds']
        elapsed=prep+sum(read(p)['seconds'] for p in (here/'stages').glob('*/result.json'))+time.monotonic()-start
        revision=program['revision']
        paths=[here,review,ROOT/PLAN,ROOT/SCRIPT,ROOT/WORKER,ROOT/EVALUATOR,ROOT/TEST,
               ROOT/REL/'proposals'/f'installed-input-repairs-{revision}.json',
               ROOT/REL/'proposals'/f'installed-input-repairs-{revision}-review.json',
               ROOT/REL/'revisions'/f'{revision:04d}.json',ROOT/program['continuation_review']['routes']]
        files=set()
        for p in paths:
            files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
        size=sum(p.stat().st_size for p in files if p.exists())
        require(elapsed<300 and size+1024**2<48*1024**2,'Cumulative resource bound')
        write(target/'result.json',{'status':'PASS','seconds':time.monotonic()-start,'details':details,
              'bytes':size,'cumulative_seconds':elapsed},exclusive=True)
        if stage=='seal':
            write(here/'run-manifest.json',{'git_commit':ad['git_commit'],'plan':PLAN,'result':name+'/RESULT.md',
                  'methods':frozen['methods'],'runtime':str(component.runtime()),'sources':config['source_files'],
                  'commands':[read(p) for p in (here/'stages').glob('*/started.json')],
                  'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','seeds':'N/A deterministic',
                  'cumulative_seconds':elapsed,'new_bytes':size,'historical_unmeasured_seconds':'UNKNOWN'},exclusive=True)
            write(here/'result.json',{'task':'source-authority','status':'PASS','whole_task_complete':False,
                  'whole_program_complete':False,'scope':'INSTALLED_INPUT_REPAIRS','summary':details},exclusive=True)
            write(here/'outputs.json',{str(p.relative_to(here)):file_hash(p) for p in sorted(here.rglob('*'))
                  if p.is_file() and p.name not in {'admission.json','outputs.json'}},exclusive=True)
        print(json.dumps({'stage':stage,'status':'PASS','seconds':time.monotonic()-start,'counts':details}))
    except Exception as exc:
        if not (target/'result.json').exists():
            write(target/'result.json',{'status':'FAIL','seconds':time.monotonic()-start,
                  'error':type(exc).__name__+': '+str(exc)},exclusive=True)
        raise
    finally:signal.alarm(0)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:run(sys.argv[2],sys.argv[3])
