"""Reviewed fixed D0-D2 continuation, with prior evidence and call-history protection."""
from pathlib import Path
import hashlib,json,subprocess
import run_interpretation_plan as supervisor
from legalmath.interpretation.search.providers import verify_allowance_checkpoint
from legalmath.canonical import digest

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round6'
PLAN=ROOT/'docs/implementation/interpretation-round6/master-plan.json'
BASELINE=ROOT/'.localresources/interpretation-round6/baseline.json'
PHASES=('D0','D1','D1R','D1F','D1S','D2')
original_run,original_write=supervisor.run,supervisor.write


def inputs():
    paths=[p for folder in ('src','tests') for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts]
    paths += [PLAN,BASELINE,Path(__file__),ROOT/'scripts/run_interpretation_plan.py',
        ROOT/'scripts/run_decomposed_feasibility.py',ROOT/'scripts/run_decomposed_resume.py',ROOT/'scripts/run_fidelity_piece.py',ROOT/'docs/plans/interpretation-d1-decomposition.md',
        ROOT/'pyproject.toml',ROOT/'requirements-dev.lock']
    paths += [p for folder in (ROOT/'.localresources/interpretation-round5/public-qa-v1',
        ROOT/'docs/implementation/interpretation-round6/contracts') for p in folder.rglob('*') if p.is_file()]
    files={str(p.relative_to(ROOT)):supervisor.sha(p) for p in sorted(set(paths))}
    return {'files':files,'digest':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}


def protect():
    baseline=supervisor.read(BASELINE)
    for name,expected in baseline['protected'].items():
        if supervisor.sha(ROOT/name)!=expected:raise ValueError('Prior evidence changed: '+name)
    prior=supervisor.read(ROOT/'.localresources/interpretation-round5/baseline.json')
    for name,expected in prior['protected'].items():
        if supervisor.sha(ROOT/name)!=expected:raise ValueError('Round4 evidence changed: '+name)
    ledger=ROOT/'artifacts/interpretation/round2/live-allowance.json'
    checked=verify_allowance_checkpoint(ledger,digest(baseline['allowance']))
    for phase,entry in supervisor.state()['phases'].items():
        for a in entry['attempts']:
            p=ROOT/a['path']
            if supervisor.sha(p)!=a['sha256']:raise ValueError('Attempt changed: '+phase)
            for name,expected in supervisor.read(p).get('artifact_sha256',{}).items():
                if supervisor.sha(p.parent/name)!=expected:raise ValueError('Attempt file changed: '+name)
    return {'protected_files':len(baseline['protected'])+len(prior['protected']),**checked}


def write(path,value):
    if isinstance(value,dict) and 'git_commit' in value and value['git_commit'] is None:
        value.update(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            authority='ENGINEERING_AND_BOUNDED_LIVE_FEASIBILITY',plan_file='docs/plans/interpretation-d1-decomposition.md',
            result_file=str(path.relative_to(ROOT)),random_seed='Provider seed unavailable; deterministic unit partitions',
            data_version=supervisor.sha(ROOT/'.localresources/interpretation-round5/public-qa-v1/manifest.json'))
    original_write(path,value)


def commands(phase,attempt):
    py=str(supervisor.PYTHON)
    if phase=='D0':return [('tests',[py,'-m','pytest','tests/assurance/test_decomposition.py',
        'tests/assurance/test_integration.py','tests/search/test_provider.py','-q','--junitxml='+str(attempt/'tests.xml')])]
    if phase=='D1':return [('live',[py,'scripts/run_decomposed_feasibility.py','--out',str(attempt/'live')])]
    if phase=='D1R':return [('live',[py,'scripts/run_decomposed_resume.py','--out',str(attempt/'live')])]
    if phase=='D1F':return [('live',[py,'scripts/run_decomposed_resume.py','--phase','D1F','--out',str(attempt/'live')])]
    if phase=='D1S':return [('live',[py,'scripts/run_fidelity_piece.py','--out',str(attempt/'live')])]
    if phase=='D2':return [('tests',[py,'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60'])]
    raise ValueError('Unknown phase')


def refresh(phase,state):
    i=PHASES.index(phase);description=supervisor.read(PLAN)['phases'][i]
    value={'phase':phase,'created_at':supervisor.now(),'source':inputs(),'master_plan_hash':supervisor.sha(PLAN),
        'predecessors':{p:state['phases'][p] for p in PHASES[:i]},'tasks':description['tasks'],
        'acceptance':description['acceptance'],'repairs':state['phases'][phase].get('repairs',[]),
        'limits':['Finite engineering evidence','No legal correctness or service guarantee','No allowance expansion'],
        'required_before_execution':['Current source review','Executed repair','Protected history']}
    write(OUT/phase/'next-plan.json',value);return value


def run(phase,state):
    if not supervisor.read(PLAN)['phases'][PHASES.index(phase)]['executable']:raise ValueError('Phase not executable')
    original_run(phase,state)


supervisor.OUT,supervisor.PLAN,supervisor.PHASES=OUT,PLAN,PHASES
supervisor.inputs,supervisor.protect,supervisor.commands=inputs,protect,commands
supervisor.write,supervisor.refresh,supervisor.run=write,refresh,run
supervisor.COMMAND_TIMEOUT_SECONDS=4200
supervisor.PREDECESSORS={p:PHASES[:i] for i,p in enumerate(PHASES)}

if __name__=='__main__':supervisor.main()
