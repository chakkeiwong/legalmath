"""Fixed reviewed H0-H2 phases with a separate additional-call grant."""
from pathlib import Path
import hashlib
import json
import subprocess
import run_interpretation_plan as supervisor
from legalmath.canonical import digest
from legalmath.interpretation.search.providers import verify_allowance_checkpoint

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round10'
PLAN=ROOT/'docs/implementation/interpretation-round10/master-plan.json'
BASELINE=ROOT/'.localresources/interpretation-round10/baseline.json'
PHASES=('H0','H1','H2')
original_run,original_write=supervisor.run,supervisor.write


def inputs():
    paths=[p for folder in ('src','tests') for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts]
    paths += [PLAN,BASELINE,Path(__file__),ROOT/'scripts/run_interpretation_plan.py',
        ROOT/'scripts/audit_public_issue.py',ROOT/'docs/plans/interpretation-h0-reusable-command.md',
        ROOT/'docs/implementation/interpretation-round10/authorization.json',
        ROOT/'examples/interpretation-assurance/declared-issue.json',
        ROOT/'scripts/run_public_issue_plan.py',
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
            authority='ENGINEERING_AND_BOUNDED_LIVE_FEASIBILITY',plan_file='docs/plans/interpretation-h0-reusable-command.md',
            result_file=str(path.relative_to(ROOT)),random_seed='Provider seed unavailable; deterministic task partition',
            data_version=supervisor.sha(BASELINE))
    original_write(path,value)


def commands(phase,attempt):
    py=str(supervisor.PYTHON)
    if phase=='H0':return [('tests',[py,'-m','pytest','tests/assurance/test_public_issue.py',
        'tests/assurance/test_discrepancy_triggers.py','tests/assurance/test_rejected_reconsideration.py',
        'tests/assurance/test_declared_evaluation.py',
        'tests/assurance/test_issue_search.py','tests/assurance/test_public_issue_master.py','-q',
        '--junitxml='+str(attempt/'tests.xml')])]
    if phase=='H1':
        directory=OUT/'issue'
        cmd=[py,'-m','legalmath.cli','assurance-interpret-issue',
            '--public',str(ROOT/'examples/interpretation-assurance/declared-issue.json'),
            '--out',str(directory),'--allowance',str(ROOT/'artifacts/interpretation/round7/live-allowance.json'),
            '--jdk',str(ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'),'--method','assurance']
        if (directory/'run.json').exists():cmd.append('--resume')
        return [('live',cmd),('audit',[py,'scripts/audit_public_issue.py','--out',str(attempt/'audit.json')])]
    if phase=='H2':return [('tests',[py,'-m','pytest','tests','-q',
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
    supervisor.COMMAND_TIMEOUT_SECONDS=3800 if phase=='H1' else 900
    original_run(phase,state)


supervisor.OUT,supervisor.PLAN,supervisor.PHASES=OUT,PLAN,PHASES
supervisor.inputs,supervisor.protect,supervisor.commands=inputs,protect,commands
supervisor.write,supervisor.refresh,supervisor.run=write,refresh,run
supervisor.COMMAND_TIMEOUT_SECONDS=900
supervisor.PREDECESSORS={p:PHASES[:i] for i,p in enumerate(PHASES)}

if __name__=='__main__':supervisor.main()
