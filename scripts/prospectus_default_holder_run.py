"""Persisted dependency stages for the explicit-holder authority attempt."""
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from scripts import prospectus_default_holder as prep
ROOT, AUTH, PREP, HERE = prep.ROOT, prep.AUTH, prep.PREP, prep.HERE
read, save, sha, rel = prep.read, prep.save, prep.sha, prep.rel
DEPS = {'freeze': (), 'source': ('freeze',), 'tests': ('freeze',),
        'ordinary': ('source',), 'package': ('freeze',), 'installed': ('ordinary', 'package'),
        'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('source', 'tests', 'ordinary', 'package', 'installed')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    seconds = extra + read(PREP / 'reproduction.json')['wall_seconds']
    paths = [PREP / 'preparation-result.json']
    paths += list((PREP / 'development').glob('*.json'))
    paths += list((HERE / 'stages').glob('*/result.json')) + list((HERE / 'stages').glob('*/failure.json'))
    seconds += sum(read(p).get('wall_seconds', 0) for p in paths if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in prep.FILES)
    files.add(AUTH / 'revisions/0362.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    assert seconds < 1000 and size < 124 * 1024**2, 'Incremental resource ceiling reached'
    assert start['prior_seconds'] + seconds < 2700, 'Cumulative time ceiling reached'
    assert start['prior_bytes'] + size < 764 * 1024**2, 'Cumulative storage ceiling reached'
    return {'new_measured_seconds': seconds, 'new_bytes': size,
        'known015plus_seconds': start['prior_seconds'] + seconds,
        'known015plus_bytes': start['prior_bytes'] + size, 'prior_costs_reset': False,
        'historical_unmeasured_time': 'UNKNOWN', 'manual_controller_and_authoring_time': 'UNKNOWN',
        'cumulative_limits': {'seconds': 2700, 'bytes': 768 * 1024**2}, 'seal_reserve_bytes': 4 * 1024**2}


def frozen():
    admission = read(HERE / 'admission.json')
    assert prep.adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert prep.Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen method/input changed: ' + name


def execute(name, argv, *, timeout=120, cwd=ROOT, development=False):
    logs = PREP / 'development' if development else HERE / 'commands'
    logs.mkdir(exist_ok=True)
    result, failure = None, None
    started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
        'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    try:
        with (logs / (name + '.log')).open('x') as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, 'Inspect retained ' + name + '.log'
    except Exception as error:
        failure = {'kind': type(error).__name__, 'reason': str(error)}
        raise
    finally:
        save(logs / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
            'wall_seconds': time.monotonic() - started, 'exit_code': result.returncode if result else None,
            'failure': failure, 'role': 'DEVELOPMENT_ONLY' if development else 'FORMAL_STAGE'})


def test_command(output):
    return [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        'tests/prospectus_successor/test_default_holder.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py', '--junitxml=' + str(output)]


def develop():
    assert not (PREP / 'freeze.json').exists(), 'Frozen method requires reviewed repair'
    number = len(list((PREP / 'development').glob('check-*.json'))) + 1
    execute('check-' + str(number), test_command(PREP / 'development' / ('tests-' + str(number) + '.xml')),
            development=True)
    return {'status': 'PASS', 'role': 'DEVELOPMENT_ONLY', 'resources': costs()}


def freeze():
    before = ast.parse((PREP / 'baseline/service.py').read_text())
    after = ast.parse((ROOT / 'src/legalmath/prospectus/successor/service.py').read_text())
    functions = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
    a, b = functions(before), functions(after)
    assert a.keys() == b.keys() and all(a[k] == b[k] for k in a if k != 'consume')
    save(HERE / 'methods.json', {'bindings': read(PREP / 'freeze.json')['bindings'],
                               'unchanged_service_functions': sorted(k for k in a if k != 'consume')})
    return {'status': 'PASS', 'method_frozen': True}


def source():
    from legalmath.prospectus.successor import default_holder as model
    request = read(PREP / 'reproduction.json')
    products = {k: read(ROOT / r['path']) for k, r in read(ROOT / request['products'])['products'].items()}
    ordinary = read(prep.BASE / 'ordinary-answer.json.gz')
    profile = read(PREP / 'profile.json')
    result = model.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=prep.digest(profile))
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body.update(result)
    from legalmath.prospectus.successor.default_holder_verify import verify_answer
    check = verify_answer({**body, 'report_sha256': prep.digest(body)}, ordinary, profile,
                          expected_profile_sha256=prep.digest(profile))
    from copy import deepcopy
    controls = []
    for kind in ('representative-copy', 'source-image', 'product-pin'):
        changed = deepcopy(profile)
        if kind == 'representative-copy': changed['groups']['representative'][0]['selected_text'] += ' altered'
        elif kind == 'source-image': changed['sources'][0]['images'][-1]['sha256'] = '0' * 64
        else: changed['products_sha256'] = '0' * 64
        try: model.evaluate(products, ordinary, changed, ROOT, expected_profile_sha256=prep.digest(changed))
        except ValueError as error: controls.append({'kind': kind, 'error': str(error)})
        else: raise AssertionError('Source control accepted: ' + kind)
    save(HERE / 'source-verification.json', {**check, 'controls': controls,
        'whole_consumer_executed': False, 'original_roles_preserved': True})
    return {'status': 'PASS', 'source_controls': len(controls), 'checked_decisions': check['checked_decisions']}


def tests():
    execute('tests', test_command(HERE / 'tests.xml'))
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / 'tests.xml').getroot()
    assert not any(int(s.get('failures', 0)) or int(s.get('errors', 0)) for s in suites)
    return {'status': 'PASS', 'tests': sum(int(s.get('tests', 0)) for s in suites)}


def ordinary():
    execute('ordinary', [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'scripts/prospectus_default_holder_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'ordinary'], timeout=380)
    return {'status': 'PASS', **read(HERE / 'ordinary-verification.json')}


def package():
    source = HERE / 'package-source'
    source.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    python = read(prep.BASE / 'package.json')['python']
    execute('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
        '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)])
    wheels = list((HERE / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    expected = {str(Path(k).relative_to('src/legalmath')): v
                for k, v in read(PREP / 'freeze.json')['production'].items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): prep.hashlib.sha256(archive.read(n)).hexdigest()
            for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual == expected, 'Wheel differs from frozen production files'
    execute('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
        '--target', str(HERE / 'installed'), str(wheels[0])])
    actual = {str(p.relative_to(HERE / 'installed/legalmath')): sha(p)
        for p in (HERE / 'installed/legalmath').rglob('*') if p.is_file()}
    assert actual == expected
    save(HERE / 'package.json', {'python': python, 'files': expected, 'wheel_sha256': sha(wheels[0])})
    return {'status': 'PASS', 'source_matched_files': len(expected)}


def installed():
    execute('installed', [read(HERE / 'package.json')['python'], '-I', '-B',
        str(ROOT / 'scripts/prospectus_default_holder_worker.py'), str(ROOT), str(PREP), str(HERE), 'installed'],
        timeout=380, cwd=HERE)
    return {'status': 'PASS', **read(HERE / 'installed-verification.json')}


def states():
    result = {}
    for stage in DEPS:
        directory = HERE / 'stages' / stage
        if (directory / 'result.json').exists(): result[stage] = read(directory / 'result.json')['status']
        elif (directory / 'failure.json').exists(): result[stage] = 'FAIL'
        elif (directory / 'started.json').exists(): result[stage] = 'INTERRUPTED_OR_RUNNING'
        elif any(result.get(d) in ('FAIL', 'BLOCKED') for d in DEPS[stage]): result[stage] = 'BLOCKED'
        else: result[stage] = 'PENDING'
    ready = [s for s, state in result.items() if state == 'PENDING' and all(result[d] == 'PASS' for d in DEPS[s])]
    if not all(result[s] in ('PASS', 'FAIL', 'BLOCKED') for s in CHECKS):
        ready = [s for s in ready if s not in ('reconcile', 'seal')]
    return {'stages': result, 'ready': ready, 'whole_build_complete': False}


def reconcile():
    outcome = states()['stages']
    save(HERE / 'original-requirements.json', {'task': 'basf-meanings', 'original_task_complete': False,
        'original_obligations': ['G03', 'G12', 'G13', 'E01', 'RESIDUAL-02', 'RESIDUAL-03'],
        'outcomes': {s: outcome[s] for s in CHECKS},
        'remaining': ['Unselected, nonexhaustive German default(f) meaning',
            'Full source applicability, definition and onward-reference coverage',
            'Statutory validity and priority', 'Wider amendment and default domains'],
        'deferred_by_user': ['Actual holdings and reader acceptance after build', 'CDM receiving system', 'Portability'],
        'external_adviser_opinion_required': False})
    return {'status': 'PASS', 'completion_only_review': True, 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']
    status = 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL'
    result = {'status': status, 'task': 'basf-meanings', 'original_task_complete': False,
        'result_kind': 'EXPLICIT_CONDITIONAL_DEFAULT_F_HOLDER_AUTHORITY',
        'resources': costs(), 'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Reconcile original source meanings and discover remaining substantive source-to-answer gaps; no exhaustive interpretation claim'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic Boolean enumeration', 'data_version': sha(PREP / 'source-bindings.json'),
        'plan': prep.PLAN, 'result': rel(HERE / 'result.json'), 'wall_time': costs()})
    return result


def main():
    stage = sys.argv[1]
    if stage == 'status': return states()
    if stage == 'develop': return develop()
    assert stage in DEPS and stage in states()['ready'], 'Stage not ready; inspect status and retained original worker'
    frozen()
    costs()
    directory = HERE / 'stages' / stage
    started = time.monotonic()
    save(directory / 'started.json', {'command': sys.argv, 'pid': os.getpid(),
         'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[stage]()
        frozen()
        costs(time.monotonic() - started)
        save(directory / 'result.json', {**result, 'wall_seconds': time.monotonic() - started})
    except Exception as error:
        save(directory / 'failure.json', {'status': 'FAIL', 'error': str(error), 'kind': type(error).__name__,
             'wall_seconds': time.monotonic() - started})
        raise
    if stage == 'seal':
        outputs = {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()
                   and p.name not in ('admission.json', 'outputs.json') and '__pycache__' not in p.parts
                   and not any(n in p.parts for n in ('installed', 'package-source'))}
        save(HERE / 'outputs.json', outputs)
    return {'status': result['status'], 'stage': stage, 'frontier': states(), 'resources': costs()}


if __name__ == '__main__':
    print(json.dumps(main()))
