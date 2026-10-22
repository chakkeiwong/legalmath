"""Bounded same-task evidence for exact coupon-input retention."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/coupon-premises-359'
HERE = AUTH / 'attempts/finance-conventions/attempt-010'
PLAN = 'docs/plans/prospectus-coupon-premise-retention-2026-10-20.md'
TARGET = 'src/legalmath/prospectus/successor/fixed_coupon.py'
TEST = 'tests/prospectus_successor/test_coupon_premises.py'
WORKER = 'scripts/prospectus_coupon_premises_worker.py'
BOUNDS = {'command_seconds': 420, 'stage_seconds': 90, 'new_bytes': 160*1024**2,
          'reserve_bytes': 2*1024**2, 'conservative_authoring_seconds': 120}
STAGES = ('freeze', 'tests', 'ordinary', 'package', 'installed', 'seal')

def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rel(path):
    return str(Path(path).relative_to(ROOT))

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode()
    if str(path).endswith('.gz'):
        raw = gzip.compress(raw, mtime=0)
    with path.open('xb') as stream:
        stream.write(raw)

def costs(extra=0):
    measured = extra
    for folder in (PREP, HERE):
        for p in (folder / 'stages').glob('*/result.json'):
            measured += read(p).get('wall_seconds', 0)
        for p in (folder / 'stages').glob('*/failure.json'):
            measured += read(p).get('wall_seconds', 0)
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (PLAN, TARGET, TEST, WORKER, rel(Path(__file__))))
    paths.update(p for p in (AUTH / 'revisions/0359.json', AUTH / 'program.json') if p.exists())
    size = sum(p.stat().st_size for p in paths if p.exists())
    assert measured < BOUNDS['command_seconds'], 'New command-time bound exhausted'
    assert size < BOUNDS['new_bytes'] - BOUNDS['reserve_bytes'], 'Storage reserve reached'
    return {'new_measured_seconds': measured, 'new_retained_bytes_conservative': size,
            'authoring_charge_seconds':120, 'older_unmeasured_runtime':'UNKNOWN',
            'historical_costs_reset':False, 'bounds':BOUNDS}

def command(name, argv, folder=HERE, timeout=90, cwd=ROOT):
    logs = folder / 'commands'
    logs.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES':'-1', 'PYTHONDONTWRITEBYTECODE':'1',
           'PYTHONPATH':str(ROOT/'src'), 'PIP_NO_INDEX':'1', 'PIP_DISABLE_PIP_VERSION_CHECK':'1'}
    result, error = None, None
    try:
        with (logs / (name+'.log')).open('x') as stream:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, name+' failed; inspect retained log'
    except Exception as exc:
        error = {'type':type(exc).__name__, 'message':str(exc)}
        raise
    finally:
        save(logs / (name+'.json'), {'command':argv, 'cwd':str(cwd), 'wall_seconds':time.monotonic()-start,
             'returncode':result.returncode if result is not None else None, 'error':error, 'timeout_seconds':timeout})

def prepare():
    from legalmath.prospectus.execution_authority import Authority, digest, write
    authority = Authority(ROOT)
    old, _, _ = authority.spec()
    assert old['revision'] == 358
    admissions = [e['attempt'] for e in authority.events() if e['kind']=='ADMIT' and e['budget_key']=='finance-conventions']
    assert len(admissions) == old['budgets']['finance-conventions']['maximum_new_attempts'] == 9
    baseline = PREP/'baseline/fixed_coupon.py'
    baseline.parent.mkdir(parents=True, exist_ok=True)
    with baseline.open('xb') as stream:
        stream.write((ROOT/TARGET).read_bytes())
    bindings, cases = {}, []
    def authentic(path):
        manifest = path.parent/'outputs.json'
        expected = read(manifest)[path.name]
        assert sha(path) == expected, 'Historical evidence changed: '+str(path)
        bindings[rel(path)] = expected
        bindings[rel(manifest)] = sha(manifest)
        return rel(path)
    finance = AUTH/'attempts/finance-conventions'
    for name in ('direct-global','direct-definitive','selected-global','selected-definitive'):
        folder = finance/'attempt-002'
        cases.append({'id':'shell-'+name, 'products':authentic(folder/(name+'-products.json.gz')),
                      'historical_answer':authentic(folder/(name+'-answer.json.gz'))})
    for name in ('selected','holiday','excluded'):
        folder = finance/'attempt-008'
        cases.append({'id':'danske-'+name,
                      'products':{p:authentic(folder/(name+'-'+p+'.json.gz')) for p in ('P1','P2','P3','P4','P5')},
                      'historical_answer':authentic(folder/(name+'-answer.json.gz'))})
    save(PREP/'cases.json',cases)
    save(PREP/'source-bindings.json',bindings)
    command('baseline',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/WORKER),str(ROOT),str(PREP),'baseline'],folder=PREP)
    history=[]
    for name in admissions:
        folder=ROOT/name
        result=read(folder/'result.json')
        history.append({'attempt':name,'bytes':sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
                        'resources':{k:v for k,v in result.items() if k in ('resources','costs','wall_seconds')},
                        'unmeasured_history':'UNKNOWN; not reset'})
    save(PREP/'historical-accounting.json',history)
    fixed={rel(p):sha(p) for p in PREP.rglob('*') if p.is_file()}
    fixed.update({n:sha(ROOT/n) for n in (PLAN,rel(Path(__file__)),WORKER,'scripts/prospectus_fixed_phase_oracle.py')})
    save(PREP/'freeze.json',{'bindings':fixed,'baseline_production_sha256':sha(ROOT/TARGET),
         'skeptical_audit':'PASS: exact current pre-repair observations, historical evidence retained, independent amounts and adverse controls, no external opinion or legal completion inference'})
    new=deepcopy(old);new['revision']=359
    task=next(t for t in new['tasks'] if t['id']=='finance-conventions')
    task.update(dossier=PLAN, build_criteria_scope=[], reason='Repair exact validated coupon-premise loss and mutable output aliases in real financial answers')
    task['coupon_premise_retention']={'version':'coupon-premises.v1','review':rel(PREP),'bounds':BOUNDS,
        'retained_admissions':admissions,'whole_task_acceptance':False,'automatic_retry':False}
    task['inputs']=sorted((set(task['inputs'])-{TARGET,TEST}) | set(fixed) | set(bindings) | {rel(PREP/'freeze.json')})
    new['budgets']['finance-conventions']['maximum_new_attempts']=10
    routes=read(ROOT/old['continuation_review']['routes']);routes['baseline_revision']=359
    route=next(r for r in routes['tasks'] if r['task']=='finance-conventions')
    route.update(task_sha256=digest(task),dossier=PLAN,remaining='Exact coupon inputs and alias isolation missing in complete financial answers; original finance coverage remains open',
        next_action='Execute admitted premise retention, source-backed ordinary/installed consumers, full-answer projection and independent arithmetic; record/refresh then original finance coverage',stop_condition=json.dumps(BOUNDS,sort_keys=True))
    routes_path=PREP/'routes.json';save(routes_path,routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(routes_path))
    for name in (TARGET,TEST):new['continuation_review']['bindings'].pop(name,None)
    new['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),rel(routes_path):sha(routes_path),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review={'baseline':digest(old),'changes':['Preserve all original obligations/tasks and nine finance admissions',
       'Current pre-repair full answers and sealed historical results retained separately',
       'One admission9-to10 for additive exact coupon-input retention; no arithmetic or event-domain change'],
       'skeptical_audit':read(PREP/'freeze.json')['skeptical_audit'],'evidence_contract':{
          'question':'Does the real answer preserve the complete validated coupon premises without aliasing?',
          'baseline':'Seven actual pre-repair full answers from authenticated Shell002/Danske008 products',
          'primary':'Exact retained scenarios, unchanged full-answer projection, independent source-integer amounts, ordinary/isolated installed equality',
          'veto':['Changed prior answer beyond named additions and derived hashes','Lost/normalized premises','Mutable alias','Wrong import origin'],
          'continuation_veto':['Corrupt evidence','Method drift','Exhausted bound'],
          'explanatory':['Counts','Time','Storage'],
          'not_concluded':['Legal truth','Actual entitlement/calendar','Early-payment support','Whole task/build acceptance']},
       'scope_unchanged':True,'budget_unchanged':False,'original_obligations_preserved':True,'external_opinion_required':False,
       'budget_revision':{'budget_key':'finance-conventions','previous_maximum':9,'new_maximum':10,
          'retained_attempts':admissions,'reason':'Reproduced answer input-loss/alias gap, distinct from passed QuantLib comparison',
          'next_discriminating_check':'Real answer exact scenario preservation, alias controls and complete old-answer projection',
          'stop_condition':BOUNDS,'same_scope_authorization':'User refresh master program and continue general build'}}
    assert old['obligations']==new['obligations'] and old['build_contract']==new['build_contract']
    # Authority uses sorted, indented JSON. Reserve three full program copies.
    forecast=len(json.dumps(new,sort_keys=True,indent=2).encode())*3 + costs()['new_retained_bytes_conservative'] + 48*1024**2
    assert forecast < BOUNDS['new_bytes']-BOUNDS['reserve_bytes']
    save(PREP/'preflight.json',{'forecast_bytes':forecast,'bounds':BOUNDS,'admissions_retained':len(admissions),'historical_runtime':'UNKNOWN unless measured in retained records'})
    write(PREP/'proposal.json',new,exclusive=True);write(PREP/'review.json',review,exclusive=True)
    return {'revision':359,'cases':len(cases),'diagnostic':read(PREP/'baseline-summary.json'),'forecast_bytes':forecast}

def frozen():
    for name,checksum in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name)==checksum,'Preparation changed: '+name
    if (HERE/'methods.json').exists():
        for name,checksum in read(HERE/'methods.json')['bindings'].items():
            assert sha(ROOT/name)==checksum,'Frozen method changed: '+name

def admitted():
    from legalmath.prospectus.execution_authority import Authority,digest
    authority=Authority(ROOT);program,tasks,_=authority.spec()
    admission=read(HERE/'admission.json')
    assert program['revision']==359 and admission['program_sha256']==digest(program)
    assert admission['binding']==authority.binding(tasks['finance-conventions'])

def freeze():
    admitted()
    paths=[ROOT/PLAN,Path(__file__),ROOT/WORKER,ROOT/TEST,HERE/'METHOD-REVIEW.md']
    paths += [p for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    production_map={str(p.relative_to(ROOT/'src/legalmath')):sha(p) for p in paths if p.is_relative_to(ROOT/'src/legalmath')}
    save(HERE/'methods.json',{'bindings':{rel(p):sha(p) for p in paths},'production_map':production_map,'whole_task_acceptance':False})
    return {'status':'PASS','frozen_files':len(paths)}

def tests():
    import xml.etree.ElementTree as ET
    names=[TEST,'tests/prospectus_successor/test_closure_finance.py','tests/prospectus_successor/test_fixed_phase.py',
        'tests/prospectus_successor/test_initial_coupon.py','tests/prospectus_successor/test_bond_basis.py',
        'tests/prospectus_successor/test_closure_coupon_anchor.py']
    command('tests',[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*names,'--junitxml='+str(HERE/'tests.xml')])
    suites=ET.parse(HERE/'tests.xml').getroot().findall('testsuite')
    assert suites and all(int(s.get(k,'0'))==0 for s in suites for k in ('failures','errors','skipped'))
    return {'status':'PASS','tests':sum(int(s.get('tests')) for s in suites)}

def ordinary():
    command('ordinary',[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/WORKER),str(ROOT),str(HERE),'ordinary'])
    return read(HERE/'ordinary-summary.json')

def package():
    from scripts import prospectus_reference_mentions_run as packaging
    packaging.ROOT,packaging.AUTH,packaging.HERE=ROOT,AUTH,HERE
    packaging.execute=lambda name,argv,timeout=90,cwd=ROOT: command(name,argv,timeout=min(timeout,90),cwd=cwd)
    return packaging.package()

def installed():
    python=read(HERE/'package.json')['python']
    command('installed',[python,'-I','-B',str(ROOT/WORKER),str(ROOT),str(HERE),'installed'],cwd=HERE)
    return read(HERE/'installed-summary.json')

def seal():
    ordinary=read(HERE/'ordinary-summary.json');installed=read(HERE/'installed-summary.json')
    assert ordinary['status']==installed['status']=='PASS'
    result={'status':'PASS','task':'finance-conventions','whole_task_complete':False,'build_criteria_claimed':[],
       'classification':'EXACT_COUPON_PREMISES_RETAINED_WITH_DETACHED_OUTPUTS','ordinary':ordinary,'installed':installed,'resources':costs()}
    save(HERE/'result.json',result)
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
       'command_records':sorted(rel(p) for p in (HERE/'commands').glob('*.json')),
       'environment':str(ROOT/'.venv/bin/python'),'installed_environment':read(HERE/'package.json')['python'],
       'CPU_GPU':'CPU; GPU intentionally hidden','seeds':'N/A deterministic','data_version':sha(PREP/'source-bindings.json'),
       'wall_time':costs(),'plan':PLAN,'result':rel(HERE/'result.json'),'historical_accounting':rel(PREP/'historical-accounting.json')})
    return {'status':'PASS','whole_task_complete':False,'resources':costs()}

def main():
    stage=sys.argv[1];assert stage=='prepare' or stage in STAGES
    folder=(PREP if stage=='prepare' else HERE)/'stages'/stage
    assert not folder.exists(),'Unchanged stage retry refused'
    if stage!='prepare':
        frozen();admitted()
        for earlier in STAGES[:STAGES.index(stage)]:assert read(HERE/'stages'/earlier/'result.json')['status']=='PASS'
    costs();started=time.monotonic()
    save(folder/'started.json',{'command':sys.argv,'utc':datetime.now(timezone.utc).isoformat()})
    try:
        result=globals()[stage]();elapsed=time.monotonic()-started
        costs(elapsed)
        if stage!='prepare':frozen()
        result.update(status='PASS',wall_seconds=elapsed);save(folder/'result.json',result)
        if stage=='seal':save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps(result))
    except Exception as exc:
        save(folder/'failure.json',{'status':'FAIL','type':type(exc).__name__,'reason':str(exc),'wall_seconds':time.monotonic()-started})
        raise

if __name__=='__main__':main()
