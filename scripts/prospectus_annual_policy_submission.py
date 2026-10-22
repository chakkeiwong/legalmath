"""Freeze and record the original annual policy/events continuation."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
sys.dont_write_bytecode = True
from scripts import prospectus_annual_policy_program as work
from legalmath.prospectus.execution_authority import Authority, digest, file_hash

AUTH, SOURCE, WORK, PREP, HERE = work.AUTH, work.SOURCE, work.WORK, work.PREP, work.HERE
read, save, require, inventory, costs = work.read, work.save, work.require, work.inventory, work.costs
TASK = 'source-bes-dep-09'
SELF = 'scripts/prospectus_annual_policy_submission.py'
SUPPORT = work.SUPPORT + [SELF, 'pyproject.toml', 'scripts/prospectus_annual_basis_source.py',
    'scripts/prospectus_annual_basis_program.py', 'scripts/prospectus_annual_basis_reading.py',
    'scripts/prospectus_annual_basis_checks.py', 'scripts/prospectus_english_applicability_program.py',
    'scripts/prospectus_2010_capital_product_cases.py', 'scripts/prospectus_2010_annual_cases.py']


def rel(path):
    return str(Path(path).relative_to(ROOT))


def size(value):
    return len(json.dumps(value,ensure_ascii=False,indent=2).encode())


def freeze():
    a=Authority(ROOT)
    old,tasks,_=a.spec()
    require(old['revision']==440 and not HERE.exists() and not (PREP/'freeze.json').exists(),'Fresh440baseline required')
    latest={e['task']:e for e in a.events() if e.get('task')}
    require(all(e['kind'] not in ('ADMIT','LAUNCH','START') for e in latest.values()),'Active task exists')
    require(read(PREP/'commands/tests.json')['exit_code']==0 and all(
        read(WORK/('candidate-'+part)/'result.json')['status']=='PASS' for part in work.PARTS),'All candidate segments required')
    candidate=read(PREP/'candidate.json')
    package=inventory(WORK/'candidate/src/legalmath')
    require(inventory(ROOT/'src/legalmath')==candidate['baseline'] and package==candidate['candidate'],'Candidate/baseline changed')
    require(package.keys()==candidate['baseline'].keys() and {n for n in package if package[n]!=candidate['baseline'][n]}=={work.CHANGE},'Unexpected production change')
    runtime=read(AUTH/'reviews/english-applicability-439/baseline.json')
    from scripts.prospectus_english_applicability_program import check_runtime
    check_runtime(runtime['runtime'],runtime['runtime_files'])
    evidence={p:file_hash(ROOT/p) for p in SUPPORT}
    for folder in (WORK,PREP):
        evidence.update({rel(p):file_hash(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    evidence.update({'src/legalmath/'+n:h for n,h in package.items()})
    for path in (work.OLD/'outputs.json',AUTH/'reviews/annual-basis-440/post-record.json'):
        evidence[rel(path)]=file_hash(path)
    frozen={'evidence':evidence,'package':package,'baseline':candidate['baseline'],
            'runtime':runtime['runtime'],'runtime_files':runtime['runtime_files'],'parts':work.PARTS}
    proposal=deepcopy(old)
    proposal['revision']=441
    task=next(t for t in proposal['tasks'] if t['id']==TASK)
    task.update(dossier=work.PLAN,pre_admission_review=work.PLAN,annual_policy_review=rel(PREP/'freeze.json'),
        reason='Integrate original Note2.2–2.7 conditions and Note47 events; preserve complete prior annual meanings')
    task['inputs']=sorted(set(task['inputs'])|set(evidence)|{rel(PREP/'freeze.json'),rel(PREP/'forecast.json')})
    attempts=[e['attempt'] for e in a.events() if e['kind']=='ADMIT' and e['budget_key']==TASK]
    require(len(attempts)==old['budgets'][TASK]['maximum_new_attempts']==16,'Retain16admissions')
    proposal['budgets'][TASK]['maximum_new_attempts']=17
    routes=read(ROOT/old['continuation_review']['routes'])
    routes['baseline_revision']=441
    for row in routes['tasks']:
        if row['task']==TASK:
            row.update(task_sha256=digest(task),dossier=work.PLAN,phase=0,
                remaining='Original annual scope incomplete: remaining Note2 policies, Note1 and numerical notes; finite source readings do not close source09.',
                next_action='Complete441ordinary/installed comparisons and record; then read remaining original policies and numerical notes with full cumulative history.',
                stop_condition='Same source09lineage;17admissions;2960cumulative seconds600MiB;600new seconds160MiB;one changed recovery maximum.')
    proposal['continuation_review'].update(plan=work.PLAN,routes=rel(PREP/'routes.json'))
    bindings=proposal['continuation_review']['bindings']
    bindings['src/legalmath/'+work.CHANGE]=package[work.CHANGE]
    bind_paths=[SELF,work.SELF,work.PLAN,rel(PREP/'freeze.json'),rel(PREP/'routes.json'),rel(PREP/'forecast.json')]
    for name in bind_paths:
        bindings[name]='0'*64
    review={'baseline':digest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Optional annual-v4source readings for original missing policies/events','Preserve prior full annual answers and439report protections'],
        'skeptical_audit':{'verdict':'PASS','plan':work.PLAN,'source_review':rel(WORK/'SOURCE-REVIEW.md'),
            'candidate_parts':work.PARTS,'forecast_before_freeze':True},
        'evidence_contract':{'baseline':'Complete016annual-v3answer with historical annual-v2preservation',
            'primary':'Actual source-qualified full answer, exact old meanings and38adverse qualifier/order cases',
            'promotion_veto':['Source/meaning/import/full-answer mismatch'],
            'continuation_veto':['Invalid authority','Corrupted common evidence','Spent cumulative bound'],
            'explanatory':['Counts','Elapsed time'],'not_concluded':['Independent IFRS/legal truth','Whole annual completeness','General interpretation']},
        'budget_revision':{'budget_key':TASK,'previous_maximum':16,'new_maximum':17,'retained_attempts':attempts,
            'reason':'Distinct original Note2.2–2.7 and47missing meanings; retain all costs; explicit2560to2960seconds and448to600MiB extension',
            'next_discriminating_check':'Complete candidate/current/installed baseline,new-answer,controls and public refusals',
            'stop_condition':{'new_seconds':600,'cumulative_seconds':2960,'new_bytes':160*1024**2,'cumulative_bytes':600*1024**2,
                'reserve_bytes':2*1024**2,'process_seconds':60,'unchanged_retries':0,'changed_recoveries_maximum':1},
            'same_scope_authorization':'Recover and continue original prospectus build; no new external authority or scope'}}
    package_bytes=sum((ROOT/'src/legalmath'/n).stat().st_size for n in package)
    proposal_bytes=size(proposal)+8192
    components={'retained_current_usage':costs()['new_bytes'],'freeze_routes_review':size(frozen)+size(routes)+size(review)+32768,
        'proposal_and_revision':2*proposal_bytes,'current_program_growth':max(0,proposal_bytes-(AUTH/'program.json').stat().st_size),
        'admission':size(task)+1024**2,'four_package_copies':4*package_bytes,'results_and_metadata':16*1024**2}
    forecast=sum(components.values())
    prior=read(AUTH/'reviews/annual-basis-440/post-record.json')['costs']['cumulative_bytes']
    require(forecast+2*1024**2<160*1024**2 and prior+forecast+2*1024**2<600*1024**2,'Forecast exceeds cumulative bound')
    require(costs()['allowed'],'Pre-freeze resource bound')
    save(PREP/'start.json',{'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
                          'program_bytes':(AUTH/'program.json').stat().st_size})
    save(PREP/'freeze.json',frozen)
    save(PREP/'routes.json',routes)
    save(PREP/'forecast.json',{'components':components,'new_bytes':forecast,'cumulative_bytes':prior+forecast,'reserve_bytes':2*1024**2})
    for name in bind_paths:
        bindings[name]=file_hash(ROOT/name)
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'FROZEN','forecast_new_bytes':forecast,'costs':costs()}


def cutover():
    a=Authority(ROOT)
    f=read(PREP/'freeze.json')
    require(digest(a.spec()[0])==read(PREP/'review.json')['baseline'] and inventory(ROOT/'src/legalmath')==f['baseline'],'Baseline changed')
    shutil.copyfile(WORK/'candidate/src/legalmath'/work.CHANGE,ROOT/'src/legalmath'/work.CHANGE)
    require(inventory(ROOT/'src/legalmath')==f['package'],'Cutover differs')
    save(PREP/'cutover.json',{'changed':[work.CHANGE],'revision_required':441})
    return {'status':'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def admitted():
    a=Authority(ROOT)
    program,tasks,_=a.spec()
    require(program['revision']==441 and read(HERE/'admission.json')['binding']==a.binding(tasks[TASK]),'Current441admission required')
    require(next(e for e in reversed(a.events()) if e.get('task')==TASK)['kind']=='ADMIT','Attempt already terminal')
    require(not (HERE/'outputs.json').exists(),'Already sealed')


def stage(kind,part):
    admitted()
    f=read(PREP/'freeze.json')
    require(costs()['allowed'],'Before-stage resource bound')
    if kind=='package':
        source=HERE/'package-source'
        source.mkdir()
        shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
        shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
        python=f['runtime']['package_python']
        work.command('wheel',[python,'-I','-B','-m','pip','wheel','--no-index','--no-deps','--no-build-isolation','--wheel-dir',str(HERE/'wheel'),str(source)],HERE/'commands')
        wheel,=(HERE/'wheel').glob('*.whl')
        with zipfile.ZipFile(wheel) as archive:
            files={n.removeprefix('legalmath/'):hashlib.sha256(archive.read(n)).hexdigest() for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
        require(files==f['package'],'Wheel differs')
        work.command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile','--target',str(HERE/'installed-package'),str(wheel)],HERE/'commands')
        require(inventory(HERE/'installed-package/legalmath')==files,'Installed package differs')
        save(HERE/'package.json',{'status':'PASS','files':files,'wheel':{'path':rel(wheel),'sha256':file_hash(wheel)}})
    else:
        require(part in work.PARTS,'Explicit part required')
        if kind=='installed':
            require(read(HERE/'package.json')['status']=='PASS','Installed package required')
        python=f['runtime']['package_python' if kind=='installed' else 'ordinary_python']
        work.command(kind+'-'+part,[python,'-I','-B',str(ROOT/work.SELF),'worker','--kind',kind,'--part',part],HERE/'commands')
    require(costs()['allowed'],'Post-stage resource bound')
    return {'status':'PASS','kind':kind,'part':part}


def seal():
    admitted()
    f=read(PREP/'freeze.json')
    require(all(file_hash(ROOT/p)==h for p,h in f['evidence'].items()),'Frozen evidence changed')
    require(inventory(ROOT/'src/legalmath')==f['package']==inventory(HERE/'installed-package/legalmath'),'Package changed')
    from scripts.prospectus_english_applicability_program import check_runtime
    check_runtime(f['runtime'],f['runtime_files'])
    for part in work.PARTS:
        require(read(WORK/('candidate-'+part)/'result.json')==read(HERE/('ordinary-'+part)/'result.json')==read(HERE/('installed-'+part)/'result.json'),'Missing/mismatched part '+part)
    require(read(HERE/'ordinary-answer/answer-delta.json.gz')==read(HERE/'installed-answer/answer-delta.json.gz')==read(WORK/'candidate-answer/answer-delta.json.gz'),'Complete answer delta differs')
    require((HERE/'RESULT.md').exists() and (HERE/'COVERAGE.md').exists(),'Substantive notes required')
    save(HERE/'result.json',{'status':'PASS','task_complete':False,'whole_program_complete':False,'costs':costs(),'plan':work.PLAN})
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[rel(p) for p in (HERE/'commands').glob('*.json')],
        'preparation_commands':[rel(p) for p in (PREP/'commands').glob('*.json')],
        'environment':f['runtime'],'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','random_seeds':'N/A deterministic',
        'charged_substantive_seconds':costs()['new_seconds'],'data_version':rel(PREP/'freeze.json'),
        'plan':work.PLAN,'result':rel(HERE/'RESULT.md')})
    outputs={str(p.relative_to(HERE)):file_hash(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    save(HERE/'outputs.json',outputs)
    require(costs()['allowed'],'Post-seal resource ceiling')
    return {'status':'SEALED'}


def record():
    started=time.monotonic()
    argv=[str(ROOT/'.venv/bin/python'),'-B','-m','scripts.prospectus_control','record','--attempt',rel(HERE)]
    with (PREP/'record-projection.log').open('x') as log:
        try:
            result=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=60)
            code=result.returncode
        except subprocess.TimeoutExpired:
            code=-1
    save(PREP/'record-projection.json',{'argv':argv,'exit_code':code,'seconds':time.monotonic()-started,'role':'AUTHORITY_RECORD_AND_VIEW'})
    a=Authority(ROOT)
    event=next(e for e in reversed(a.events()) if e.get('attempt')==rel(HERE))
    require(code==0 and event['kind']=='RECORD' and a.retained_evidence_valid(event),'Inspect actual record before any redispatch')
    save(PREP/'post-record.json',{'event':event,'costs':costs(),'retained_evidence_valid':True})
    return {'status':'RECORDED','event':event['sha256']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','cutover','stage','seal','record','costs'])
    parser.add_argument('--kind',choices=['ordinary','package','installed'])
    parser.add_argument('--part',choices=work.PARTS)
    args=parser.parse_args()
    started=time.monotonic()
    before=costs()['new_seconds']
    tracked=args.action in ('freeze','cutover','stage','seal')
    try:
        result=stage(args.kind,args.part) if args.action=='stage' else globals()[args.action]()
    except Exception as exc:
        if tracked:
            elapsed=time.monotonic()-started
            save(PREP/'commands'/('failed-'+args.action+'-'+str(args.kind)+'-'+str(args.part)+'.json'),
                 {'argv':sys.argv,'exit_code':1,'seconds':max(0,elapsed-(costs()['new_seconds']-before)),'error':str(exc)})
        raise
    if tracked:
        elapsed=time.monotonic()-started
        save(PREP/'commands'/('overhead-'+args.action+'-'+str(args.kind)+'-'+str(args.part)+'.json'),
             {'argv':sys.argv,'exit_code':0,'seconds':max(0,elapsed-(costs()['new_seconds']-before)),'role':'WRAPPER_OVERHEAD_CHILD_TIME_ALREADY_CHARGED'})
    print(json.dumps({**result,'costs':costs()}),flush=True)
