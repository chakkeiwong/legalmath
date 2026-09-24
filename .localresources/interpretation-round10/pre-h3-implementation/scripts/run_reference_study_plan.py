"""Fixed C0-C3 study continuation with protected evidence and bounded live use."""
from pathlib import Path
import hashlib,json,subprocess
import run_interpretation_plan as supervisor

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/interpretation/round5'
PLAN=ROOT/'docs/implementation/interpretation-round5/master-plan.json'
BASELINE=ROOT/'.localresources/interpretation-round5/baseline.json'
PHASES=('C0','C1','C2','C3')
original_run,original_write=supervisor.run,supervisor.write


def inputs():
    paths=[p for directory in ('src','tests') for p in (ROOT/directory).rglob('*.py') if '__pycache__' not in p.parts]
    paths += [PLAN,BASELINE,Path(__file__),ROOT/'scripts/run_interpretation_plan.py',
        ROOT/'scripts/prepare_public_reference_study.py',ROOT/'scripts/validate_public_reference_study.py',
        ROOT/'docs/implementation/interpretation-round5/c3-repair-and-audit.md',
        ROOT/'docs/plans/interpretation-c1-reference-study.md',ROOT/'pyproject.toml',ROOT/'requirements-dev.lock']
    paths += [p for directory in (ROOT/'.localresources/interpretation-round5/public-qa-v1',
                                   ROOT/'docs/implementation/interpretation-round5/contracts')
              for p in directory.rglob('*') if p.is_file()]
    live=ROOT/'scripts/run_public_qa_feasibility.py'
    if live.exists():paths.append(live)
    hashes={str(p.relative_to(ROOT)):supervisor.sha(p) for p in sorted(set(paths))}
    return {'files':hashes,'digest':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}


def protect():
    baseline=supervisor.read(BASELINE)
    for name,expected in baseline['protected'].items():
        if supervisor.sha(ROOT/name)!=expected:raise ValueError('Earlier evidence changed: '+name)
    ledger=supervisor.read(ROOT/'artifacts/interpretation/round2/live-allowance.json')
    prior=baseline['allowance'];n=len(prior['calls'])
    if ledger['maximum']!=prior['maximum'] or ledger['calls'][:n]!=prior['calls'] or len(ledger['calls'])>ledger['maximum']:
        raise ValueError('Allowance reset, changed history or excess use')
    for phase,entry in supervisor.state()['phases'].items():
        for accepted in entry['attempts']:
            p=ROOT/accepted['path']
            if supervisor.sha(p)!=accepted['sha256']:raise ValueError('Earlier attempt changed: '+phase)
            for name,expected in supervisor.read(p).get('artifact_sha256',{}).items():
                if supervisor.sha(p.parent/name)!=expected:raise ValueError('Earlier attempt file changed: '+name)
    return {'protected_files':len(baseline['protected']),'calls_consumed':len(ledger['calls']),
            'remaining_calls':ledger['maximum']-len(ledger['calls']),'history_preserved':True}


def write(path,value):
    if isinstance(value,dict) and 'git_commit' in value and value['git_commit'] is None:
        value.update(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            authority='LOCAL_ENGINEERING_AND_LABELLED_PUBLIC_SOURCE_FEASIBILITY',
            plan_file='docs/plans/interpretation-c1-reference-study.md',
            result_file=str(path.relative_to(ROOT)),random_seed='924 for four-arm study order; N/A for deterministic checks',
            data_version=supervisor.sha(ROOT/'.localresources/interpretation-round5/public-qa-v1/manifest.json'))
    original_write(path,value)


def commands(phase,attempt):
    py=str(supervisor.PYTHON)
    tests=[py,'-m','pytest','tests/assurance/test_evaluation.py','-q','--junitxml='+str(attempt/'tests.xml')]
    if phase=='C0':return [('tests',tests)]
    if phase=='C1':return [('reference-replay',[py,'scripts/validate_public_reference_study.py','--out',str(attempt/'reference')])]
    if phase=='C2':return [('live-feasibility',[py,'scripts/run_public_qa_feasibility.py','--out',str(attempt/'live')])]
    if phase=='C3':return [('tests',[py,'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60'])]
    raise ValueError('Unknown phase')


def refresh(phase,state):
    i=PHASES.index(phase);entry=supervisor.read(PLAN)['phases'][i]
    value={'phase':phase,'created_at':supervisor.now(),'source':inputs(),'master_plan_hash':supervisor.sha(PLAN),
        'predecessors':{p:state['phases'][p] for p in PHASES[:i]},'tasks':entry['tasks'],'acceptance':entry['acceptance'],
        'executable':entry['executable'],'repairs':state['phases'][phase].get('repairs',[]),
        'limits':['No bank release','No comparative ranking from live feasibility','No model allowance increase'],
        'required_before_execution':['Current input review','Executed repairs before retry','Protected prior evidence']}
    write(OUT/phase/'next-plan.json',value);return value


def run(phase,state):
    if not supervisor.read(PLAN)['phases'][PHASES.index(phase)]['executable']:
        raise ValueError('Phase is not reviewed for execution')
    original_run(phase,state)


supervisor.OUT,supervisor.PLAN,supervisor.PHASES=OUT,PLAN,PHASES
supervisor.inputs,supervisor.protect,supervisor.commands=inputs,protect,commands
supervisor.write,supervisor.refresh,supervisor.run=write,refresh,run
supervisor.COMMAND_TIMEOUT_SECONDS=2400
supervisor.PREDECESSORS={p:PHASES[:i] for i,p in enumerate(PHASES)}

if __name__=='__main__':supervisor.main()
