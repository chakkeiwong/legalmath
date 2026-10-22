"""Short, retained local stages for the admitted reference-mention repair."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

from scripts import prospectus_reference_mentions_trial as prep

ROOT, AUTH, PREP, HERE = prep.ROOT, prep.AUTH, prep.PREP, prep.HERE
read, save, rel = prep.read, prep.save, prep.rel
sha = prep.file_hash
FILES = (prep.METHOD, prep.PLAN, 'scripts/prospectus_reference_mentions_run.py',
         'scripts/prospectus_reference_mentions_installed.py',
         'tests/prospectus_successor/test_reference_mentions.py', *prep.TARGETS)
STAGES = ('freeze', 'tests', 'ordinary', 'audit', 'package', 'installed', 'seal')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    measured = base['combined_measured_seconds'] + extra
    for directory in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json', 'development/*.json'):
            measured += sum(read(p).get('wall_seconds', 0) for p in directory.glob(pattern))
    paths = {p for directory in (PREP, HERE) for p in directory.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0355.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / name).stat().st_size - start['production_bytes'][name]) for name in prep.TARGETS)
    charge = base['conservative_extra_seconds'] + 120
    assert measured + charge < prep.SECONDS_BOUND, 'Cumulative time exhausted'
    assert size < prep.BYTES_BOUND - 4 * 1024**2, 'Cumulative storage reserve reached'
    assert measured - base['combined_measured_seconds'] < 300, 'New command allowance exhausted'
    assert size - base['combined_bytes'] < 128 * 1024**2, 'New storage allowance exhausted'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charge,
        'combined_accounted_seconds': measured + charge, 'combined_bytes': size,
        'seconds_bound': prep.SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': prep.BYTES_BOUND,
        'prior_costs_reset': False, 'older_unmeasured_authoring_time': 'UNKNOWN'}


def execute(name, argv, timeout=120, cwd=ROOT):
    started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
           'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    logs = HERE / 'commands'
    logs.mkdir(exist_ok=True)
    with (logs / (name + '.log')).open('x') as output:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
    save(logs / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'exit_code': result.returncode,
         'wall_seconds': time.monotonic() - started, 'timeout_seconds': timeout})
    assert result.returncode == 0, name + ' failed; inspect retained log'


def frozen():
    for name, checksum in read(PREP / 'source-freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen source changed: ' + name
    method = HERE / 'methods.json'
    if method.exists():
        for name, checksum in read(method)['bindings'].items():
            assert sha(ROOT / name) == checksum, 'Frozen method changed: ' + name


def diagnose():
    """Development only: preserve mismatches without treating this as acceptance."""
    from legalmath.prospectus.successor.reference_mentions import discover
    start = time.monotonic()
    req = read(PREP / 'request.json')
    report = discover(req)
    index = {(r['start'], r['end'], r['kind']): r for r in report['mentions']}
    missing = [r for r in read(PREP / 'expected.json')['records'] if (r['start'], r['end'], r['kind']) not in index]
    result = {'role': 'DEVELOPMENT_ONLY', 'promotion_evidence': False,
              'missing': missing, 'mentions': len(index), 'issues': report['issues'],
              'method_bindings': {n: sha(ROOT / n) for n in prep.TARGETS},
              'wall_seconds': time.monotonic() - start}
    target = HERE / 'development' / ('diagnostic-' + str(len(list((HERE / 'development').glob('*.json'))) + 1).zfill(3) + '.json')
    save(target, result)
    return {'status': 'DEBUG_ONLY', 'missing': len(missing), 'mentions': len(index),
            'issues': len(report['issues']), 'artifact': rel(target),
            'missing_literals': [r['raw'] for r in missing]}


def freeze():
    baseline = ast.parse((PREP / 'baseline/service.py').read_text())
    current = ast.parse((ROOT / prep.TARGETS[1]).read_text())
    functions = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    before, after = functions(baseline), functions(current)
    assert before.keys() == after.keys()
    assert all(before[n] == after[n] for n in before if n not in ('configure', 'dispatch'))
    previous = AUTH / 'attempts/basf-references/attempt-093'
    for name, checksum in read(previous / 'outputs.json').items():
        assert sha(previous / name) == checksum
    save(HERE / 'methods.json', {'bindings': {n: sha(ROOT / n) for n in FILES},
         'production_map': package_files(ROOT / 'src/legalmath'),
         'unchanged_service_functions': sorted(n for n in before if n not in ('configure', 'dispatch')),
         'prior093_sealed_outputs_verified': True, 'prior_complete_answer_reexecuted': False})
    return {'status': 'PASS', 'service_functions_unchanged': len(before) - 2, 'methods_frozen': True}


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        'tests/prospectus_successor/test_reference_mentions.py',
        'tests/prospectus_successor/test_paragraph_references.py',
        'tests/prospectus_successor/test_conditional_profiles_cli.py', '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / 'tests.xml').getroot()
    assert not any(int(r.attrib.get('failures', 0)) or int(r.attrib.get('errors', 0)) for r in suites)
    return {'status': 'PASS', 'tests': sum(int(r.attrib.get('tests', 0)) for r in suites)}


def ordinary():
    execute('ordinary-cli', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', 'prospectus',
        'discover-references', '--request', str(PREP / 'request.json'), '--output', str(HERE / 'ordinary-report.json')])
    return {'status': 'PASS', 'actual_cli': True}


def audit():
    request = read(PREP / 'request.json')
    report = read(HERE / 'ordinary-report.json')
    assert report['report_sha256'] == prep.digest({k: v for k, v in report.items() if k != 'report_sha256'})
    assert report['request_sha256'] == prep.digest(request)
    assert report['general_recall_established'] is report['target_resolution_established'] is False
    assert report['legal_interpretation_established'] is report['document_authenticity_established'] is False
    rows = report['mentions']
    index = {(r['start'], r['end'], r['kind']): r for r in rows}
    assert len(index) == len(rows) and len({r['id'] for r in rows}) == len(rows)
    expected = read(PREP / 'expected.json')['records']
    keys = set()
    for row in expected:
        key = (row['start'], row['end'], row['kind'])
        found = index[key]
        assert all(found[k] == row[k] for k in ('raw', 'source_projection'))
        keys.add(key)
    for row in rows:
        a, b = row['start'], row['end']
        assert request['text'][a:b] == row['raw']
        assert row['source_projection'] == prep.project(request, a, b)
        assert row['target'] is None and row['review_required'] is True
        assert row['raw_copy_complete'] == all(p['source'] is not None for p in row['source_projection'])
    extras = [r for r in rows if (r['start'], r['end'], r['kind']) not in keys]
    save(HERE / 'extra-candidates.json', extras)
    result = {'status': 'PASS', 'original_records': 60, 'original_expectations': len(expected),
        'distinct_expected_mentions': len(keys), 'matched_original_records': len({r['record'] for r in expected}),
        'extra_candidates': len(extras), 'all_source_projections_checked': len(rows),
        'issues': report['issues'], 'matching_by_overlap': False,
        'general_recall_established': False, 'target_resolution_established': False}
    save(HERE / 'independent-verification.json', result)
    return result


def package_files(folder):
    return {str(p.relative_to(folder)): sha(p) for p in folder.rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def package():
    source = HERE / 'package-source'
    source.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    expected = read(HERE / 'methods.json')['production_map']
    assert package_files(source / 'src/legalmath') == expected
    python = read(AUTH / 'attempts/basf-references/attempt-093/package.json')['python']
    execute('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
        '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)])
    wheels = list((HERE / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                  for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual == expected
    execute('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps',
        '--no-compile', '--target', str(HERE / 'installed'), str(wheels[0])])
    assert package_files(HERE / 'installed/legalmath') == expected
    save(HERE / 'package.json', {'python': python, 'files': expected, 'wheel_sha256': sha(wheels[0])})
    return {'status': 'PASS', 'package_files': len(expected)}


def installed():
    python = read(HERE / 'package.json')['python']
    execute('installed-cli', [python, '-I', '-B', str(ROOT / 'scripts/prospectus_reference_mentions_installed.py'),
        str(ROOT), str(HERE), str(PREP)], cwd=HERE)
    return read(HERE / 'installed-result.json')


def seal():
    verification = read(HERE / 'independent-verification.json')
    dispositions = read(HERE / 'extra-dispositions.json')
    extras = read(HERE / 'extra-candidates.json')
    assert sorted(r['id'] for r in dispositions['candidates']) == sorted(r['id'] for r in extras)
    assert all(r['reason'] and r['disposition'] for r in dispositions['candidates'])
    assert dispositions['issues'] == verification['issues']
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'GENERAL_SOURCE_BOUND_REFERENCE_MENTION_DISCOVERY',
        **{k: v for k, v in verification.items() if k != 'issues'},
        'ordinary_installed_equal': True, 'prior_full_answer_reexecuted': False,
        'resources': costs(), 'next_action': 'Reconcile detected mentions with reviewed targets; retain seven original gaps'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'installed_environment': read(HERE / 'package.json')['python'],
        'cpu_gpu': 'CPU;GPU intentionally hidden', 'seeds': 'N/A deterministic',
        'data_version': sha(PREP / 'request.json'), 'wall_time': costs(), 'plan': prep.PLAN,
        'result': rel(HERE / 'result.json')})
    return result


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    stage = sys.argv[1]
    assert stage == 'diagnose' or stage in STAGES
    frozen()
    if stage == 'diagnose':
        assert not (HERE / 'methods.json').exists(), 'Use reviewed repair after formal method freeze'
        result = diagnose()
        costs()
        print(json.dumps(result, ensure_ascii=False))
        return
    for previous in STAGES[:STAGES.index(stage)]:
        assert read(HERE / 'stages' / previous / 'result.json')['status'] == 'PASS'
    folder = HERE / 'stages' / stage
    assert not folder.exists(), 'Unchanged stage retry refused'
    costs()
    start = time.monotonic()
    save(folder / 'started.json', {'command': sys.argv, 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[stage]()
        frozen()
        costs(time.monotonic() - start)
        result['wall_seconds'] = time.monotonic() - start
        save(folder / 'result.json', result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps({k: v for k, v in result.items() if k not in ('issues', 'resources')}, ensure_ascii=False))
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'reason': str(error), 'exception': type(error).__name__,
             'wall_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
