"""Fixed offline B0 acceptance with protected A7 history and B1 plan refresh."""
from pathlib import Path
import hashlib
import json
import subprocess
import run_interpretation_plan as supervisor
from legalmath.interpretation.search.providers import verify_allowance_checkpoint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/interpretation/round4'
PLAN = ROOT / 'docs/implementation/interpretation-round4/master-plan.json'
BASELINE = ROOT / '.localresources/interpretation-round4/baseline.json'
PHASES = ('B0', 'B1', 'B2a', 'B2b', 'B3', 'B4', 'B5', 'B6')
original_write, original_run, original_state = supervisor.write, supervisor.run, supervisor.state


def inputs():
    paths = [p for folder in ('src', 'tests') for p in (ROOT / folder).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    paths += [PLAN, BASELINE, ROOT/'docs/plans/interpretation-b0-reliability.md',
              ROOT/'pyproject.toml', ROOT/'requirements-dev.lock', Path(__file__),
              ROOT/'scripts/run_interpretation_plan.py',
              ROOT/'scripts/interpretation_reliability_acceptance.py']
    paths += [ROOT/'docs/plans/interpretation-b1-b5-execution.md',
              ROOT/'.localresources/interpretation-round4/successor-baseline.json',
              ROOT/'scripts/interpretation_authority_acceptance.py',
              ROOT/'scripts/prepare_authority_examples.py',
              ROOT/'scripts/interpretation_composition_acceptance.py',
              ROOT/'scripts/interpretation_question_acceptance.py',
              ROOT/'docs/implementation/interpretation-round4/b2b-design-audit.md',
              ROOT/'scripts/prepare_case_examples.py', ROOT/'scripts/interpretation_example_acceptance.py',
              ROOT/'docs/implementation/interpretation-round4/b3-design-audit.md',
              ROOT/'scripts/interpretation_evaluation_acceptance.py',
              ROOT/'docs/implementation/interpretation-round4/b4-design-audit.md',
              ROOT/'scripts/interpretation_operations_acceptance.py',
              ROOT/'docs/implementation/interpretation-round4/b5-design-audit.md',
              ROOT/'docs/implementation/interpretation-round4/b5-operator-contract.md',
              ROOT/'docs/implementation/interpretation-round4/b6-repair-plan.md',
              ROOT/'docs/implementation/interpretation-round4/final-red-team.md']
    paths += [p for p in (ROOT/'.localresources/sfc-authorities/b1').rglob('*') if p.is_file()]
    paths += [p for p in (ROOT/'.localresources/sfc-examples/b3').rglob('*') if p.is_file()]
    hashes = {str(p.relative_to(ROOT)): supervisor.sha(p) for p in sorted(set(paths))}
    return {'files': hashes, 'digest': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


def protect():
    record = supervisor.read(BASELINE)
    if not record:
        raise ValueError('Missing B0 baseline')
    for name, expected in record['protected_evidence'].items():
        if name == 'artifacts/interpretation/round2/live-allowance.json':
            verify_allowance_checkpoint(ROOT/name,expected)
            continue
        if supervisor.sha(ROOT / name) != expected:
            raise ValueError('Historical evidence or allowance changed: ' + name)
    # Preserve the earlier frozen P12 comparator as well as the A7 result.
    prior = ROOT / '.localresources/interpretation-round3'
    frozen = supervisor.read(prior/'baseline.json')
    for name, expected in frozen['files'].items():
        if supervisor.sha(prior/'baseline'/name) != expected:
            raise ValueError('Frozen P12 baseline changed: ' + name)
    for name, expected in frozen['protected_evidence'].items():
        if supervisor.sha(ROOT/name) != expected:
            raise ValueError('Pre-A7 historical evidence changed: ' + name)
    successor = supervisor.read(ROOT/'.localresources/interpretation-round4/successor-baseline.json')
    for name, expected in successor['protected_B0'].items():
        if supervisor.sha(ROOT/name) != expected:
            raise ValueError('Accepted B0 evidence changed: ' + name)
    for phase, entry in supervisor.read(OUT/'state.json', {'phases':{}})['phases'].items():
        if entry['status'] != 'PASSED': continue
        accepted = entry['attempts'][-1]; manifest_path = ROOT/accepted['path']
        if supervisor.sha(manifest_path) != accepted['sha256']:
            raise ValueError('Accepted phase manifest changed: '+phase)
        for name, expected in supervisor.read(manifest_path)['artifact_sha256'].items():
            if supervisor.sha(manifest_path.parent/name) != expected:
                raise ValueError('Accepted phase evidence changed: '+phase+'/'+name)
    return {'frozen_files': len(frozen['files']),
            'protected_A7_files': len(record['protected_evidence']),
            'protected_earlier_files': len(frozen['protected_evidence']), 'new_live_calls': 0}


def write(path, value):
    if isinstance(value, dict) and 'git_commit' in value and value['git_commit'] is None:
        value.update(git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                     authority='DETERMINISTIC_ENGINEERING_REVALIDATION',
                     plan_file=('docs/plans/interpretation-b0-reliability.md' if value.get('phase') == 'B0'
                                else 'docs/plans/interpretation-b1-b5-execution.md'),
                     random_seed='N/A: scripted tests and deterministic revalidation',
                     data_version=supervisor.sha(BASELINE), result_file=str(path.relative_to(ROOT)))
    original_write(path, value)


def commands(phase, attempt):
    py = str(supervisor.PYTHON)
    if phase in ('B5','B6'):
        return [('tests', [py, '-m', 'pytest', 'tests', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('operations', [py, 'scripts/interpretation_operations_acceptance.py', '--out', str(attempt/'operations')])]
    if phase == 'B4':
        return [('tests', [py, '-m', 'pytest', 'tests/assurance', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('evaluation', [py, 'scripts/interpretation_evaluation_acceptance.py', '--out', str(attempt/'evaluation')])]
    if phase == 'B3':
        return [('tests', [py, '-m', 'pytest', 'tests/assurance', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('examples', [py, 'scripts/interpretation_example_acceptance.py', '--out', str(attempt/'examples')])]
    if phase == 'B2b':
        return [('tests', [py, '-m', 'pytest', 'tests/assurance', 'tests/search', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('questions', [py, 'scripts/interpretation_question_acceptance.py', '--out', str(attempt/'questions')])]
    if phase == 'B2a':
        return [('tests', [py, '-m', 'pytest', 'tests/assurance', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('composition', [py, 'scripts/interpretation_composition_acceptance.py', '--out', str(attempt/'composition')])]
    if phase == 'B1':
        return [('tests', [py, '-m', 'pytest', 'tests/assurance', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                           '-o', 'faulthandler_timeout=60']),
                ('authorities', [py, 'scripts/interpretation_authority_acceptance.py', '--out', str(attempt/'authorities')])]
    if phase != 'B0':
        raise ValueError('Phase needs its implemented fixed commands and reviewed evidence contract')
    return [('tests', [py, '-m', 'pytest', 'tests', '-q', '--junitxml=' + str(attempt/'tests.xml'),
                       '-o', 'faulthandler_timeout=60']),
            ('retained', [py, 'scripts/interpretation_reliability_acceptance.py', '--out', str(attempt/'retained')])]


def refresh(phase, state):
    index = PHASES.index(phase)
    description = supervisor.read(PLAN)['phases'][index]
    record = {'phase': phase, 'created_at': supervisor.now(), 'source': inputs(),
              'master_plan_hash': supervisor.sha(PLAN), 'tasks': description['tasks'],
              'acceptance': description['acceptance'], 'executable': description['executable'],
              'predecessors': {p: state['phases'][p] for p in PHASES[:index]},
              'repairs': state['phases'][phase].get('repairs', []),
              'required_before_execution': ['current-input author review', 'executed repairs before retry',
                                            'protected prior evidence and allowance'],
              'limits': ['Bounded engineering evidence only', 'No legal-correctness or review-cost claim',
                         'No new live calls authorized by this phase']}
    write(OUT/phase/'next-plan.json', record)
    return record


def run(phase, state):
    if not supervisor.read(PLAN)['phases'][PHASES.index(phase)]['executable']:
        raise ValueError('Successor is not executable until its implementation and evidence contract are reviewed')
    original_run(phase, state)
    if phase in ('B4','B5'):
        current=original_state()
        current['phases'][phase]['acceptance_scope']='LOCAL_ENGINEERING'
        current['phases'][phase]['external_acceptance']=(
            'EMPIRICAL_UNDER_BUDGETED' if phase=='B4' else 'INSTITUTION_CONFIGURATION_REQUIRED')
        current['master_program_complete']=False
        supervisor.write(OUT/'state.json',current)


def state():
    record = original_state()
    for phase in PHASES:
        record['phases'].setdefault(phase, {'status': 'PLANNED', 'attempts': []})
    return record


supervisor.OUT, supervisor.PLAN, supervisor.PHASES = OUT, PLAN, PHASES
supervisor.inputs, supervisor.protect, supervisor.commands = inputs, protect, commands
supervisor.refresh, supervisor.write, supervisor.run = refresh, write, run
supervisor.state = state
supervisor.COMMAND_TIMEOUT_SECONDS = 900
supervisor.PREDECESSORS = {p: PHASES[:i] for i,p in enumerate(PHASES)}

if __name__ == '__main__':
    supervisor.main()
