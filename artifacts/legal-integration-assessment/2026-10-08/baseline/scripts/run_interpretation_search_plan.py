"""Fixed-command master program for the substantive interpretation-search increment."""
from pathlib import Path
import hashlib
import json
import subprocess
import run_interpretation_plan as supervisor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/interpretation/round2'
PLAN = ROOT / 'docs/implementation/interpretation-round2/master-plan.json'
PHASES = tuple('P'+str(i) for i in range(13))
original_write = supervisor.write
original_state = supervisor.state


def state():
    value=original_state()
    for phase in PHASES:value['phases'].setdefault(phase,{'status':'PLANNED','attempts':[]})
    return value


def inputs():
    paths = [p for directory in ('src', 'tests', 'examples/interpretation-search')
             for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [PLAN, PLAN.with_suffix('.md'), Path(__file__), ROOT/'scripts/run_interpretation_plan.py',
              ROOT/'pyproject.toml', ROOT/'requirements-dev.lock',
              ROOT/'docs/plans/interpretation-fact-alignment.md']
    paths += list((ROOT/'scripts').glob('*interpretation_search*.py'))
    hashes = {str(p.relative_to(ROOT)):supervisor.sha(p) for p in sorted(set(paths))}
    return {'files':hashes,'digest':hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()}


def protect():
    base=ROOT/'.localresources/interpretation-round2'
    record=supervisor.read(base/'baseline.json')
    if not record:
        raise ValueError('Missing frozen baseline')
    for name, expected in record['files'].items():
        if supervisor.sha(base/'baseline'/name)!=expected:
            raise ValueError('Frozen baseline changed: '+name)
    return {'frozen_files':len(record['files'])}


def write(path, value):
    if isinstance(value, dict) and 'git_commit' in value and value['git_commit'] is None:
        value['git_commit'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        value['environment']['context'] = 'bounded interpretation-search phase runner'
        value['authority'] = 'ENGINEERING_EVIDENCE_ONLY'
    original_write(path, value)


def commands(phase, attempt):
    py=str(supervisor.PYTHON)
    paths={
        'P0':['tests/unit'],
        'P1':['tests/search/test_contracts.py','tests/search/test_provider.py'],
        'P2':['tests/search/test_formal.py','tests/search/test_arguments.py'],
        'P3':['tests/search/test_engine.py'],
        'P4':['tests/search','tests/interpretation'],
        'P6':['tests'],
        'P7':['tests'],
        'P10':['tests/search/test_alignment.py','tests/search/test_questions.py'],
        'P11':['tests/search/test_alignment_review.py','tests/search/test_api.py','tests/search/test_integration.py'],
    }
    if phase in ('P5','P8'):
        return [('live-pilot',[py,'scripts/interpretation_search_pilot.py','--out',str(attempt/'pilot'),
                               '--allowance',str(OUT/'live-allowance.json'),
                               *(['--rounds','3','--max-calls','12','--min-rounds','2'] if phase=='P8' else [])])]
    if phase=='P7':
        return [('tests',[py,'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60']),
                ('frozen-live-replay',[py,'scripts/interpretation_search_replay.py','--out',str(attempt/'replay')])]
    if phase=='P9':
        return [('tree-depth',[py,'-m','pytest','tests/search/test_engine.py::test_bounded_search_descends_to_a_grandchild_and_keeps_frontier','-q','-o','faulthandler_timeout=60']),
                ('tests',[py,'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60'])]
    if phase=='P12':
        return [('tests',[py,'-m','pytest','tests','-q','--junitxml='+str(attempt/'tests.xml'),'-o','faulthandler_timeout=60']),
                ('fact-correspondence-replay',[py,'scripts/interpretation_search_alignment_replay.py','--out',str(attempt/'replay')])]
    return [('tests',[py,'-m','pytest',*paths[phase],'-q','--junitxml='+str(attempt/'tests.xml'),
                      '-o','faulthandler_timeout=60'])]


def refresh(phase, state):
    ix=PHASES.index(phase)
    record={'phase':phase,'created_at':supervisor.now(),'source':inputs(),'master_plan_hash':supervisor.sha(PLAN),
            'predecessors':{p:state['phases'][p] for p in PHASES[:ix]},
            'acceptance':supervisor.read(PLAN)['phases'][ix]['acceptance'],
            'tasks':supervisor.read(PLAN)['phases'][ix]['tasks'],
            'repairs':state['phases'][phase].get('repairs',[]),
            'limits':['No automatic legal approval','No accuracy claim from same-author labels',
            f"Live calls share a persistent {supervisor.read(PLAN)['live_call_allowance']}-call allowance",'Scores are investigation priorities'],
            'required_before_execution':['review exact current inputs','all preceding phases passed',
                                         'repair actual defects before retrying']}
    write(OUT/phase/'next-plan.json',record)
    return record


supervisor.OUT,supervisor.PLAN,supervisor.PHASES=OUT,PLAN,PHASES
supervisor.inputs,supervisor.protect,supervisor.commands=inputs,protect,commands
supervisor.refresh,supervisor.write=refresh,write
supervisor.state=state
supervisor.COMMAND_TIMEOUT_SECONDS=2700
supervisor.PREDECESSORS={p:PHASES[:i] for i,p in enumerate(PHASES)}
# Regression is independent of live-service availability and cannot certify P5.
supervisor.PREDECESSORS['P6']=PHASES[:5]

if __name__=='__main__':
    supervisor.main()
