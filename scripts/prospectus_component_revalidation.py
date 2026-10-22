"""Bounded current and installed replay of named retained conditional components."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as adigest
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_component_evidence import COMPONENTS, baseline, evaluate, helper, load, prepare_controls, require, same

PLAN = 'docs/plans/prospectus-installed-components-2026-10-17.md'
SCRIPT = 'scripts/prospectus_component_revalidation.py'
WORKER = 'scripts/prospectus_component_installed_worker.py'
EVALUATOR = 'scripts/prospectus_component_evidence.py'
TEST = 'tests/prospectus/test_component_installed.py'
RUNTIME_ATTEMPT = REL+'/attempts/source-bes-dep-09/attempt-005'
BOUNDS = {'preparation_seconds':90,'candidate_seconds':180,'build_seconds':60,'install_seconds':60,
    'installed_seconds':180,'validation_seconds':180,'incremental_seconds':750,
    'new_bytes':96*1024**2,'reserve_bytes':1024**2,'network_native_OCR_GPU':0}


def package_files(folder):
    return {str(p.relative_to(folder)):file_hash(p) for p in sorted(folder.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def compress(path,value):
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),mtime=0))


def runtime():
    return Path(read(ROOT/RUNTIME_ATTEMPT/'workspace.json')['directory'])/'environment'


def runtime_files():
    # Existing dependency and package bytes are read, never installed over.
    env = runtime()
    files = package_files(env)
    files['resolved-interpreter'] = file_hash((env/'bin/python').resolve())
    return files


def methods():
    names = {str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    names |= {SCRIPT,WORKER,EVALUATOR,TEST,PLAN,'pyproject.toml'}
    for kind in COMPONENTS:
        h = helper(ROOT,kind)
        names.update(h.METHODS)
    return {n:file_hash(ROOT/n) for n in sorted(names)}


def selector(task):
    value = task.get('current_component_validation')
    require(isinstance(value,dict) and set(value) == {'version','kind','review','baseline','wheel_attempt','bounds'},
        'Missing reviewed component selector')
    kind = value['kind']
    require(kind in COMPONENTS and task['id'] == COMPONENTS[kind][0]
        and value['version'] == 'current-installed-component.v1' and value['bounds'] == BOUNDS
        and value['baseline'] == str(baseline(ROOT,kind).relative_to(ROOT)), 'Wrong component task or limits')
    review = (ROOT/value['review']).resolve()
    require(review.is_relative_to(ROOT/REL/'reviews'),'Component review outside authority')
    return value


def frozen(task):
    s = selector(task); f = read(ROOT/s['review']/'frozen.json')
    require(f['methods'] == methods(), 'Current component methods changed')
    require(f['inputs'] == {n:file_hash(ROOT/n) for n in f['inputs']}, 'Current component inputs changed')
    require(f['runtime_files'] == runtime_files(), 'Read-only runtime changed')
    require(set(f['methods'])|set(f['inputs'])|{s['review']+'/frozen.json'} <= set(task['inputs']),
        'Unbound current component evidence')
    return f


def usage(task,attempt):
    s = selector(task); review = ROOT/s['review']; revision = read(review/'preflight.json')['revision']
    files = {ROOT/n for n in methods()}
    files |= {p for folder in (review,attempt,ROOT/REL/'continuation-reviews'/('component-'+str(revision)+'-record'))
        for p in folder.rglob('*') if p.is_file()}
    files |= set((ROOT/REL/'proposals').glob('component-'+str(revision)+'*.json'))
    files.add(ROOT/REL/'revisions'/f'{revision:04d}.json')
    total = sum(p.stat().st_size for p in files if p.is_file())
    require(total+BOUNDS['reserve_bytes'] < BOUNDS['new_bytes'],'Installed-component storage ceiling')
    return {'new_bytes':total,'ceiling':BOUNDS['new_bytes'],'reserve':BOUNDS['reserve_bytes']}


def historic(kind):
    auth = Authority(ROOT); folder = baseline(ROOT,kind); path = str(folder.relative_to(ROOT))
    events = auth.events()
    original = next(e for e in reversed(events) if e.get('attempt') == path and e['kind'] in {'ACCEPT','RECORD','REJECT'})
    require(auth.retained_evidence_valid(original), 'Original finite evidence changed')
    accepted_path = path if kind != 'cash-flow' else str(folder.with_name('attempt-011').relative_to(ROOT))
    accepted = next(e for e in reversed(events) if e.get('attempt') == accepted_path and e['kind'] in {'ACCEPT','RECORD'})
    require(COMPONENTS[kind][2] in accepted.get('build_acceptances',[]) and auth.retained_evidence_valid(accepted),
        'Original finite acceptance missing')
    return {'original_attempt':path,'original_event_sha256':original['sha256'],
        'outputs_sha256':original['outputs_sha256'],'accepted_attempt':accepted_path,
        'accepted_event_sha256':accepted['sha256'],'accepted_outputs_sha256':accepted['outputs_sha256']}


def prepare(kind,wheel_attempt):
    auth = Authority(ROOT); program,tasks,_ = auth.spec(); revision = program['revision']+1
    key = COMPONENTS[kind][0]; task = tasks[key]; review_name = REL+'/reviews/component-'+str(revision)
    folder = ROOT/review_name; folder.mkdir(parents=True,exist_ok=False)
    start = time.monotonic(); error = None
    try:
        historical = historic(kind); write(folder/'history.json',historical,exclusive=True)
        h = helper(ROOT,kind); packet = prepare_controls(ROOT,kind)
        if packet is not None: compress(folder/'controls-packet.json.gz',packet)
        tests = sorted(set(h.TESTS)|{TEST})
        with (folder/'tests.log').open('x') as log:
            subprocess.run([sys.executable,'-m','pytest',*tests,'-q','--junitxml='+str(folder/'tests.xml')],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'CUDA_VISIBLE_DEVICES':'-1','PYTHONDONTWRITEBYTECODE':'1'},
                stdout=log,stderr=subprocess.STDOUT,timeout=max(1,90-(time.monotonic()-start)),check=True)
        count = checked_tests(folder/'tests.xml',1)
        if packet is not None:
            from scripts.prospectus_component_evidence import packet_controls
            same(packet_controls(ROOT,kind,packet),read(baseline(ROOT,kind)/'controls.json'),'prepared semantic control denominator')
        mf = methods(); old = baseline(ROOT,kind)
        inputs = set(task['inputs'])-set(mf)
        inputs |= {str((old/n).relative_to(ROOT)) for n in read(old/'outputs.json')}
        inputs |= {str((old/'outputs.json').relative_to(ROOT)),RUNTIME_ATTEMPT+'/workspace.json'}
        if kind == 'cash-flow':
            inputs.add(str(old.with_name('attempt-011').relative_to(ROOT))+'/outputs.json')
        if wheel_attempt:
            donor = auth.path(wheel_attempt)
            require(read(donor/'source-package.json') == package_files(ROOT/'src/legalmath') and
                package_files(donor/'installed/legalmath') == package_files(ROOT/'src/legalmath'),'Reused installed package differs')
            event = next(e for e in reversed(auth.events()) if e.get('attempt') == wheel_attempt and e['kind'] in {'RECORD','ACCEPT'})
            require(auth.retained_evidence_valid(event),'Reused installed evidence changed')
            inputs |= {wheel_attempt+'/'+n for n in read(donor/'outputs.json')}|{wheel_attempt+'/outputs.json'}
        prep = {'seconds':time.monotonic()-start,'tests':count,'status':'PASS','command':[sys.executable,'-m',SCRIPT.removesuffix('.py').replace('/','.'),'prepare','--kind',kind],
            'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1','historical_unrecorded_seconds':'UNKNOWN; no cumulative total invented'}
        require(prep['seconds'] <= 90,'Preparation bound')
        write(folder/'preparation.json',prep,exclusive=True)
        inputs |= {str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()}
        frozen_value = {'methods':mf,'inputs':{n:file_hash(ROOT/n) for n in sorted(inputs)},
            'runtime_files':runtime_files(),'history':historical,'package':package_files(ROOT/'src/legalmath')}
        write(folder/'frozen.json',frozen_value,exclusive=True)
        admissions = [e for e in auth.events() if e['kind']=='ADMIT' and e['budget_key']==task['budget_key']]
        before = program['budgets'][task['budget_key']]['maximum_new_attempts']
        require(len(admissions) == before,'Continuation expects exhausted original allowance')
        new = deepcopy(program); new['revision'] = revision; current = next(t for t in new['tasks'] if t['id']==key)
        current.update(dossier=PLAN,reason='Validate current and isolated installed complete '+kind+' component against immutable accepted evidence; preserve original wider acceptance',
            current_component_validation={'version':'current-installed-component.v1','kind':kind,'review':review_name,
                'baseline':str(old.relative_to(ROOT)),'wheel_attempt':wheel_attempt,'bounds':BOUNDS},timeout_seconds=210)
        current['inputs'] = sorted(set(current['inputs'])|set(mf)|inputs|{review_name+'/frozen.json',review_name+'/preflight.json'})
        new['budgets'][task['budget_key']]['maximum_new_attempts'] = before+1
        expected_attempt = REL+'/attempts/'+key+'/attempt-'+f'{before+1:03d}'
        original_admission = read(old/'admission.json')
        deltas = {n:{'old':v,'current':file_hash(ROOT/n)} for n,v in original_admission['binding'].items()
            if file_hash(ROOT/n) != v}
        # All original bytes outside source/method files stay immutable.
        require(all(n.startswith(('src/','scripts/','tests/')) or n=='pyproject.toml' for n in deltas),
            'Unexpected changed original source/document')
        prior_bytes = sum(p.stat().st_size for p in old.parent.rglob('*') if p.is_file())
        write(folder/'preflight.json',{'revision':revision,'expected_attempt':expected_attempt,'changed_original_methods':deltas,
            'prior_task_attempt_bytes':prior_bytes,'historical_cost_manifests':[
                {'path':str(p.relative_to(ROOT)),'sha256':file_hash(p)} for p in old.parent.rglob('run-manifest.json')],
            'new_ceiling':BOUNDS['new_bytes'],'reserve':BOUNDS['reserve_bytes'],'forecast_new_bytes':40*1024**2},exclusive=True)
        audit = {'baseline':adigest(program),'changes':['Actual current and installed '+kind+' replay','Preserve every original finite result and wider task requirement'],
            'skeptical_audit':{'verdict':'PASS','plan':PLAN,'runtime':'Original runtime read-only; no pytest import in installed controls',
                'changed_methods_review':review_name+'/preflight.json','primary':'Complete original answer, independent proof and all refusals; exact installed imports'},
            'evidence_contract':{'question':'Does the current wheel deliver the same finite conditional consumer?',
                'baseline':historical,'primary':'Full actual outputs and all controls match; complete package and imports match',
                'veto':'Source or method drift, incorrect origin/output/refusal or resource overrun','explanatory':['test total','runtime'],
                'not_concluded':['original task completion','legal truth','automatic discovery','portability','whole build']},
            'scope_unchanged':True,'budget_unchanged':False,'budget_revision':{'budget_key':task['budget_key'],
                'previous_maximum':before,'new_maximum':before+1,'retained_attempts':[e['attempt'] for e in admissions],
                'reason':'Current shared-code batch and previously unchecked actual installed component',
                'next_discriminating_check':'Actual isolated complete consumer and every original refusal',
                'stop_condition':BOUNDS,'same_scope_authorization':'User-directed general build and continued repairs'}}
        write(ROOT/REL/'proposals'/('component-'+str(revision)+'.json'),new,exclusive=True)
        write(ROOT/REL/'proposals'/('component-'+str(revision)+'-review.json'),audit,exclusive=True)
        usage(current,ROOT/expected_attempt)
        print(json.dumps({'prepared_revision':revision,'kind':kind,'tests':count,'seconds':prep['seconds'],'attempt':expected_attempt}))
        return 0
    except Exception as exc:
        error = type(exc).__name__+': '+str(exc)
        write(folder/'failure.json',{'error':error,'seconds':time.monotonic()-start},exclusive=True)
        (folder/'failure-trace.txt').write_text(traceback.format_exc(limit=10))
        print(json.dumps({'preparation':'FAIL','error':error})); return 1


def stage_names(task):
    return ('candidate','installed','seal') if selector(task)['wheel_attempt'] else ('candidate','build','install','installed','seal')


def execute_command(attempt,stage,argv,seconds):
    command = attempt/'stages'/stage
    env = {**os.environ,'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONNOUSERSITE':'1','PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_CACHE_DIR':'1'}
    write(command/'command.json',{'argv':argv,'cwd':str(attempt),'timeout':seconds,
        'environment':{k:env[k] for k in ('CUDA_VISIBLE_DEVICES','PYTHONPATH','PYTHONDONTWRITEBYTECODE','PIP_NO_INDEX')}},exclusive=True)
    with (command/'stdout').open('xb') as out,(command/'stderr').open('xb') as err:
        code = subprocess.run(argv,cwd=attempt,env=env,stdout=out,stderr=err,timeout=seconds).returncode
    require(code == 0,'Component '+stage+' command failed; see retained stderr')


def installed_target(task,attempt):
    donor = selector(task)['wheel_attempt']
    return (ROOT/donor if donor else attempt)/'installed'


def validate_inventory(task,attempt,f):
    target = installed_target(task,attempt); donor = target.parent
    require(read(donor/'source-package.json') == f['package'] == package_files(target/'legalmath'),'Installed package inventory differs')
    wheel = read(donor/'wheel.json'); path = donor/wheel['file']
    require(file_hash(path)==wheel['sha256'],'Wheel bytes changed')
    with zipfile.ZipFile(path) as archive:
        contents = {n.removeprefix('legalmath/'):hashlib.sha256(archive.read(n)).hexdigest()
            for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    require(contents == f['package'],'Wheel contents omit or change production file')
    proof = read(attempt/'installed-proof.json')
    require(proof['isolated']==1 and Path(proof['prefix']).resolve()==runtime().resolve()
        and Path(proof['python']).resolve()==(runtime()/'bin/python').resolve()
        and proof['process_guard']=={'starts':0,'blocked':0} and proof['package_files']==len(f['package']),
        'Installed runtime/import proof differs')
    require(proof['modules'] and all((target/'legalmath') in Path(v['path']).parents
        and file_hash(Path(v['path']))==v['sha256'] and f['package'].get(str(Path(v['path']).relative_to(target/'legalmath')))==v['sha256']
        for v in proof['modules'].values()),'Production module loaded outside current target')
    require(str(ROOT/'src') not in proof['sys_path'],'Source checkout on installed search path')
    command = read(attempt/'stages/installed/command.json')
    expected = [str(runtime()/'bin/python'),'-I','-B',str(ROOT/WORKER),str(ROOT),str(attempt),
        str(target),selector(task)['kind']]
    require(command['argv']==expected and command['cwd']==str(attempt) and command['timeout']==180
        and command['environment']['CUDA_VISIBLE_DEVICES']=='-1'
        and command['environment']['PIP_NO_INDEX']=='1', 'Actual installed command differs')


def run(attempt_name,stage):
    auth = Authority(ROOT); attempt = auth.path(attempt_name); admission = read(attempt/'admission.json')
    program,tasks,_ = auth.spec(); task = tasks[admission['task']]; s = selector(task)
    require(admission['program_sha256']==adigest(program) and admission['binding']==auth.binding(task)
        and admission['task_spec']==task,'Current admitted component required')
    event = next(e for e in reversed(auth.events()) if e.get('task')==task['id'])
    require(event['kind']=='ADMIT' and event['attempt']==attempt_name,'Component admission is not active')
    stages = stage_names(task); require(stage in stages,'Unknown component stage')
    for name in stages[:stages.index(stage)]:
        require(read(attempt/'stages'/name/'result.json')['status']=='PASS','Prior component stage failed')
    target = attempt/'stages'/stage; target.mkdir(parents=True,exist_ok=False)
    f = frozen(task); started = time.monotonic(); status,error,details = 'PASS',None,{}
    limit = BOUNDS.get(stage+'_seconds',30)
    manifest = {'started_at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-m','scripts.prospectus_component_revalidation',
        'run','--attempt',attempt_name,'--stage',stage],'git_commit':admission['git_commit'],'plan':PLAN,
        'environment':{'python':sys.version,'executable':sys.executable},'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds':'N/A deterministic','data_version':f['inputs'],'methods':f['methods'],'result':str((target/'result.json').relative_to(ROOT))}
    write(target/'started.json',manifest,exclusive=True)
    def expire(_s,_f): raise TimeoutError('Component '+stage+' time limit')
    previous = signal.getsignal(signal.SIGALRM); signal.signal(signal.SIGALRM,expire); signal.alarm(limit+5)
    try:
        if stage == 'candidate':
            write(attempt/'source-package.json',f['package'],exclusive=True)
            packet_path = ROOT/s['review']/'controls-packet.json.gz'
            packet = load(packet_path) if packet_path.exists() else None
            if packet is not None: compress(attempt/'controls-packet.json.gz',packet)
            details = evaluate(ROOT,s['kind'],packet); write(attempt/'current-checks.json',details,exclusive=True)
        elif stage == 'build':
            source = attempt/'source'; source.mkdir()
            shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
            shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.egg-info'))
            require(package_files(source/'src/legalmath')==f['package'],'Copied source differs')
            execute_command(attempt,stage,[str(runtime()/'bin/python'),'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation',
                '--no-index','--wheel-dir',str(attempt/'wheel'),str(source)],60)
            wheels = list((attempt/'wheel').glob('*.whl')); require(len(wheels)==1,'One wheel required')
            write(attempt/'wheel.json',{'file':str(wheels[0].relative_to(attempt)),'sha256':file_hash(wheels[0])},exclusive=True)
        elif stage == 'install':
            wheel = read(attempt/'wheel.json'); require(file_hash(attempt/wheel['file'])==wheel['sha256'],'Built wheel changed')
            execute_command(attempt,stage,[str(runtime()/'bin/python'),'-I','-B','-m','pip','install','--no-index','--no-deps',
                '--no-compile','--target',str(attempt/'installed'),str(attempt/wheel['file'])],60)
            require(package_files(attempt/'installed/legalmath')==f['package'],'Installed/source bytes differ')
        elif stage == 'installed':
            execute_command(attempt,stage,[str(runtime()/'bin/python'),'-I','-B',str(ROOT/WORKER),str(ROOT),str(attempt),
                str(installed_target(task,attempt)),s['kind']],180)
            validate_inventory(task,attempt,f)
            same(read(attempt/'installed-checks.json'),read(attempt/'current-checks.json'),'current versus installed complete checks')
            details = {'package_files':len(f['package']),'whole_output_and_controls_equal':True}
        else:
            validate_inventory(task,attempt,f)
            elapsed = sum(read(attempt/'stages'/n/'result.json')['wall_seconds'] for n in stages[:-1])
            prep = read(ROOT/s['review']/'preparation.json')['seconds']
            require(prep+elapsed+180 <= 750,'Incremental acceptance reserve exhausted')
            write(attempt/'result.json',{'task':task['id'],'status':'PASS','kind':s['kind'],
                'task_complete':False,'whole_program_complete':False,'wall_seconds':elapsed,'installed':True},exclusive=True)
            (attempt/'RESULT.md').write_text('# Current installed '+s['kind']+' component\n\n'
                'The actual current and isolated installed consumers match the immutable complete finite evidence and all original controls. '
                'Every wheel/installed production file matches current frozen source. The authority must replay the substantive checks before accepting this criterion.\n\n'
                '| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n'
                '| Submit finite installed result | Complete original equality and controls passed | No wrong imports or changed result | Supplied interpretations and broader coverage | Authority record, refresh and next component | No legal truth, actual holding, portability or whole-build claim |\n\n'
                'Post-run red team: identical outputs can preserve an incorrect supplied interpretation. Independent finite checkers and adverse mutations test the declared conditional behavior; they do not prove source authenticity or completeness.\n')
        frozen(task); details['storage'] = usage(task,attempt)
        require(time.monotonic()-started<=limit,'Component stage time ceiling')
    except Exception as exc:
        status,error='FAIL',type(exc).__name__+': '+str(exc)
        (target/'failure-trace.txt').write_text(traceback.format_exc(limit=12))
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM,previous)
    write(target/'result.json',{'status':status,'error':error,'wall_seconds':time.monotonic()-started,'details':details},exclusive=True)
    if stage=='seal' and status=='PASS':
        write(attempt/'outputs.json',{str(p.relative_to(attempt)):file_hash(p) for p in sorted(attempt.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.name!='outputs.json'},exclusive=True)
    print(json.dumps({'stage':stage,'kind':s['kind'],'status':status,'error':error,'seconds':time.monotonic()-started}))
    return int(status!='PASS')


def validate_submission(root,attempt,task):
    require(Path(root).resolve()==ROOT,'Wrong component validation root')
    s = selector(task); attempt = Path(attempt); start = time.monotonic(); previous = signal.getsignal(signal.SIGALRM)
    def expired(_s,_f): raise ValueError('Component acceptance180second ceiling')
    signal.signal(signal.SIGALRM,expired); signal.alarm(180)
    try:
        f = frozen(task); same(historic(s['kind']),f['history'],'original accepted history')
        prep = read(ROOT/s['review']/'preparation.json'); checked_tests(ROOT/s['review']/'tests.xml',prep['tests'])
        stages = stage_names(task); total = prep['seconds']
        for name in stages:
            r = read(attempt/'stages'/name/'result.json')
            require(r['status']=='PASS' and 0<=r['wall_seconds']<=BOUNDS.get(name+'_seconds',30),'Failed/out-of-bound component stage')
            total += r['wall_seconds']
        result = read(attempt/'result.json')
        require(result['status']=='PASS' and result['kind']==s['kind'] and result['task_complete'] is False
            and result['whole_program_complete'] is False,'Invalid component disposition')
        packet_path = ROOT/s['review']/'controls-packet.json.gz'; packet = load(packet_path) if packet_path.exists() else None
        if packet is not None: same(load(attempt/'controls-packet.json.gz'),packet,'installed input packet')
        actual = evaluate(ROOT,s['kind'],packet)
        same(actual,read(attempt/'current-checks.json'),'current replay'); same(actual,read(attempt/'installed-checks.json'),'installed replay')
        require(read(attempt/'installed-result.json')['status']=='PASS','No actual installed pass')
        validate_inventory(task,attempt,f); usage(task,attempt); frozen(task)
        require(total+time.monotonic()-start<=750,'Cumulative incremental component time ceiling')
        return True
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM,previous)
        print(json.dumps({'component_validation':s['kind'],'seconds':time.monotonic()-start}),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--kind',choices=list(COMPONENTS)); p.add_argument('--wheel-attempt'); p.add_argument('--attempt'); p.add_argument('--stage')
    args=p.parse_args()
    if args.action=='prepare':
        if not args.kind:p.error('--kind required')
        return prepare(args.kind,args.wheel_attempt)
    if not args.attempt or not args.stage:p.error('--attempt and --stage required')
    return run(args.attempt,args.stage)


if __name__=='__main__':raise SystemExit(main())
