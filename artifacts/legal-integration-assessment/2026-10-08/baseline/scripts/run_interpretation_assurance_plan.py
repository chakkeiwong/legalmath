"""Fixed, reviewed A0–A7 execution; historical P0–P12 evidence is immutable."""
from pathlib import Path
import hashlib
import json
import subprocess
import run_interpretation_plan as supervisor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/interpretation/round3'
PLAN = ROOT / 'docs/implementation/interpretation-round3/master-plan.json'
PHASES = tuple('A' + str(i) for i in range(8))
original_write = supervisor.write


def inputs():
    paths = [p for folder in ('src', 'tests', 'examples/interpretation-assurance')
             for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [PLAN, ROOT / 'docs/plans/interpretation-automation-execution.md',
              ROOT / 'pyproject.toml', ROOT / 'requirements-dev.lock',
              ROOT / 'scripts/run_interpretation_plan.py', Path(__file__)]
    paths += list((ROOT / 'scripts').glob('*interpretation_assurance*.py'))
    paths += [ROOT / 'docs/implementation/interpretation-round3/live-pilot-contract.md']
    paths += [ROOT / 'artifacts/interpretation/round3/recovered-source-inventory.json']
    paths += [ROOT / 'artifacts/interpretation/round3/A7/attempt-05/pilot/23EC46/manifest.json',
              ROOT / 'artifacts/interpretation/round3/A7/attempt-05/pilot/24EC16/manifest.json',
              ROOT / 'docs/implementation/interpretation-round3/a7-criticism-repair-plan.md']
    paths += [ROOT / 'docs/implementation/interpretation-round3/a7-attack-repair-plan.md']
    paths += [ROOT / 'docs/implementation/interpretation-round3/a7-encoding-repair-plan.md']
    paths += [ROOT / 'docs/implementation/interpretation-round3/a7-schema-repair-plan.md']
    paths += [ROOT / 'docs/implementation/interpretation-round3/a7-retained-completion-plan.md',
              ROOT / 'docs/implementation/interpretation-round3/a7-retained-replay.json',
              ROOT / 'artifacts/interpretation/round3/A7/attempt-07/pilot/23EC46/manifest.json',
              ROOT / 'artifacts/interpretation/round3/A7/attempt-06/pilot/23EC46/manifest.json']
    hashes = {str(p.relative_to(ROOT)): supervisor.sha(p) for p in sorted(set(paths))}
    return {'files': hashes, 'digest': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


def protect():
    base = ROOT / '.localresources/interpretation-round3'
    record = supervisor.read(base / 'baseline.json')
    if not record:
        raise ValueError('Missing frozen P12 baseline')
    for name, expected in record['files'].items():
        if supervisor.sha(base / 'baseline' / name) != expected:
            raise ValueError('Frozen baseline changed: ' + name)
    for name, expected in record['protected_evidence'].items():
        if supervisor.sha(ROOT / name) != expected:
            raise ValueError('Historical evidence changed: ' + name)
    return {'frozen_files': len(record['files']), 'protected_evidence': len(record['protected_evidence'])}


def write(path, value):
    if isinstance(value, dict) and 'git_commit' in value and value['git_commit'] is None:
        value['git_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        value.update(authority='ENGINEERING_EVIDENCE_ONLY',
                     plan_file=str(PLAN.relative_to(ROOT)), random_seed='Deterministic tests; live provider seed unavailable',
                     data_version='Source and challenge hashes in input and pilot manifests',
                     result_file=str(path.relative_to(ROOT)))
    original_write(path, value)


def commands(phase, attempt):
    py = str(supervisor.PYTHON)
    files = {
        'A0': ['tests/assurance/test_master.py'],
        'A1': ['tests/assurance/test_sources.py'],
        'A2': ['tests/assurance/test_semantics.py'],
        'A3': ['tests/assurance/test_arguments.py'],
        'A4': ['tests/assurance/test_repair.py'],
        'A5': ['tests/assurance/test_monitor.py', 'tests/assurance/test_challenges.py'],
        'A6': ['tests/assurance'],
        'A7': ['tests'],
    }
    result = [('tests', [py, '-m', 'pytest', *files[phase], '-q',
                         '--junitxml=' + str(attempt / 'tests.xml'), '-o', 'faulthandler_timeout=60'])]
    if phase == 'A7':
        result += [('assurance-pilot', [py, 'scripts/interpretation_assurance_pilot.py',
                    '--out', str(attempt / 'pilot'), '--allowance',
                    str(ROOT / 'artifacts/interpretation/round2/live-allowance.json'),
                    '--recover',str(ROOT / 'artifacts/interpretation/round3/recovered-source-inventory.json'),
                    '--replay-plan',str(ROOT / 'docs/implementation/interpretation-round3/a7-retained-replay.json')])]
    return result


def refresh(phase, state):
    index = PHASES.index(phase)
    description = supervisor.read(PLAN)['phases'][index]
    record = {'phase': phase, 'created_at': supervisor.now(), 'source': inputs(),
              'master_plan_hash': supervisor.sha(PLAN), 'tasks': description['tasks'],
              'acceptance': description['acceptance'],
              'predecessors': {p: state['phases'][p] for p in PHASES[:index]},
              'repairs': state['phases'][phase].get('repairs', []),
              'required_before_execution': ['review exact inputs', 'execute repairs before retry',
                                            'preserve P12 evidence and counted live allowance'],
              'limits': ['Engineering profile only', 'No absolute English accuracy claim',
                         'No production approval or external consultancy required']}
    write(OUT / phase / 'next-plan.json', record)
    return record


supervisor.OUT, supervisor.PLAN, supervisor.PHASES = OUT, PLAN, PHASES
supervisor.inputs, supervisor.protect, supervisor.commands = inputs, protect, commands
supervisor.refresh, supervisor.write = refresh, write
supervisor.COMMAND_TIMEOUT_SECONDS = 7800
supervisor.PREDECESSORS = {p: PHASES[:i] for i, p in enumerate(PHASES)}

if __name__ == '__main__':
    supervisor.main()
