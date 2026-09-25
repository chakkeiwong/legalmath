"""Fixed reviewed G0-G3 phases with a separate additional-call grant."""
from pathlib import Path
import hashlib
import json
import subprocess
import run_interpretation_plan as supervisor
from legalmath.canonical import digest
from legalmath.interpretation.search.providers import verify_allowance_checkpoint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round9'
PLAN=ROOT/'docs/implementation/interpretation-round9/master-plan.json'
BASELINE=ROOT/'.localresources/interpretation-round9/baseline.json'
PHASES=('G0','G1','G2','G3')
original_run,original_write=supervisor.run,supervisor.write


def inputs():
    paths=[p for folder in ('src','tests') for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts]
    paths += [PLAN,BASELINE,Path(__file__),ROOT/'scripts/run_interpretation_plan.py',
        ROOT/'scripts/run_declared_study.py',ROOT/'docs/plans/interpretation-g0-declared-comparison.md',
        ROOT/'docs/implementation/interpretation-round9/authorization.json',
        ROOT/'docs/implementation/interpretation-round9/study.json',ROOT/'docs/implementation/interpretation-round9/live-contract.json',
        ROOT/'scripts/validate_declared_study.py',
        ROOT/'pyproject.toml',ROOT/'requirements-dev.lock']

    files={str(p.relative_to(ROOT)):supervisor.sha(p) for p in sorted(set(paths))}
    return {'files':files,'digest':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}


def protect():
    baseline=supervisor.read(BASELINE)
    for name,expected in baseline['protected'].items():
        if supervisor.sha(ROOT/name)!=expected:raise ValueError('Prior evidence changed: '+name)
    current=verify_allowance_checkpoint(ROOT/'artifacts/interpretation/round7/live-allowance.json',baseline['allowance_checkpoint_hash'])
    for phase,entry in supervisor.state()['phases'].items():
        for attempt in entry['attempts']:
            path=ROOT/attempt['path']
            if supervisor.sha(path)!=attempt['sha256']:raise ValueError('Attempt changed: '+phase)
            for name,expected in supervisor.read(path).get('artifact_sha256',{}).items():
                if supervisor.sha(path.parent/name)!=expected:raise ValueError('Attempt file changed: '+name)
    return {'protected_files':len(baseline['protected']),'new_allowance':current}


def write(path,value):
    if isinstance(value,dict) and 'git_commit' in value and value['git_commit'] is None:
        value.update(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            authority='ENGINEERING_AND_BOUNDED_LIVE_FEASIBILITY',plan_file='docs/plans/interpretation-g0-declared-comparison.md',
            result_file=str(path.relative_to(ROOT)),random_seed='Provider seed unavailable; deterministic task partition',
            data_version=supervisor.sha(BASELINE))
    original_write(path,value)


def commands(phase,attempt):
    py=str(supervisor.PYTHON)
    if phase=='G0':return [('tests',[py,'-m','pytest','tests/assurance/test_declared_evaluation.py',
        'tests/assurance/test_declared_master.py','tests/assurance/test_issue_search.py','-q',
        '--junitxml='+str(attempt/'tests.xml')])]
    if phase=='G1':return [('reference',[py,'scripts/validate_declared_study.py','--out',str(attempt/'reference')])]
    if phase=='G2':return [('live',[py,'scripts/run_declared_study.py','--out',str(attempt/'live')])]
    if phase=='G3':return [('tests',[py,'-m','pytest','tests','-q',
        '--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60'])]
    raise ValueError('Unknown phase')


def refresh(phase,state):
    i=PHASES.index(phase);description=supervisor.read(PLAN)['phases'][i]
    write(OUT/phase/'next-plan.json',{'phase':phase,'created_at':supervisor.now(),'source':inputs(),
        'master_plan_hash':supervisor.sha(PLAN),'predecessors':{p:state['phases'][p] for p in PHASES[:i]},
        'tasks':description['tasks'],'acceptance':description['acceptance'],
        'repairs':state['phases'][phase].get('repairs',[]),
        'limits':['Check completion is not English correctness','500 new calls maximum; earlier ledger frozen'],
        'required_before_execution':['Current-source review','Executed repair after failed acceptance','Protected history']})


def run(phase,state):
    if not supervisor.read(PLAN)['phases'][PHASES.index(phase)]['executable']:raise ValueError('Phase not executable')
    if phase=='G3':supervisor.COMMAND_TIMEOUT_SECONDS=900
    original_run(phase,state)


supervisor.OUT,supervisor.PLAN,supervisor.PHASES=OUT,PLAN,PHASES
supervisor.inputs,supervisor.protect,supervisor.commands=inputs,protect,commands
supervisor.write,supervisor.refresh,supervisor.run=write,refresh,run
supervisor.COMMAND_TIMEOUT_SECONDS=60000
supervisor.PREDECESSORS={p:PHASES[:i] for i,p in enumerate(PHASES)}

if __name__=='__main__':supervisor.main()
