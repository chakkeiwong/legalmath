"""Bounded, retained verification of the admitted printed-section guard."""
import ast
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from scripts import prospectus_explicit_scope_trial as prep
from scripts import prospectus_reference_mentions_run as packaging

ROOT, AUTH, PREP, HERE = prep.ROOT, prep.AUTH, prep.PREP, prep.HERE
sys.path.insert(0, str(ROOT / 'src'))
from legalmath.prospectus.successor.contracts import digest

read, save, rel, sha = prep.read, prep.save, prep.rel, prep.sha
STAGES = ('freeze', 'tests', 'ordinary', 'consume', 'audit', 'package', 'installed', 'seal')
FILES = (prep.PLAN, prep.METHOD, 'scripts/prospectus_explicit_scope_run.py',
         'scripts/prospectus_explicit_scope_installed.py',
         'tests/prospectus_successor/test_definition_scope_evidence.py', *prep.TARGETS,
         rel(HERE / 'METHOD-REVIEW.md'), rel(HERE / 'REPAIR-REVIEW-001.md'))


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    base = start['prior']
    measured = base['combined_measured_seconds'] + extra
    for folder in (PREP, HERE):
        for pattern in ('stages/*/result.json', 'stages/*/failure.json', 'development/*.json'):
            measured += sum(read(p).get('wall_seconds', 0) for p in folder.glob(pattern))
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / name for name in FILES)
    paths.add(AUTH / 'revisions/0358.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = base['combined_bytes'] + sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size += sum(max(0, (ROOT / n).stat().st_size - start['production_bytes'][n]) for n in prep.TARGETS)
    charge = base['conservative_extra_seconds'] + 120
    assert measured + charge < prep.SECONDS_BOUND, 'Cumulative accounted time exhausted'
    assert size < prep.BYTES_BOUND - 4 * 1024**2, 'Cumulative storage reserve reached'
    assert measured - base['combined_measured_seconds'] < 900, 'New command allowance exhausted'
    assert size - base['combined_bytes'] < 128 * 1024**2, 'New storage allowance exhausted'
    return {'combined_measured_seconds': measured, 'conservative_extra_seconds': charge,
            'combined_accounted_seconds': measured + charge, 'combined_bytes': size,
            'seconds_bound': prep.SECONDS_BOUND, 'bytes_bound_with_4MiB_reserve': prep.BYTES_BOUND,
            'prior_costs_reset': False, 'older_unmeasured_authoring_time': 'UNKNOWN',
            'authoring_charge_is_measurement': False}


def execute(name, argv, timeout=100, cwd=ROOT):
    started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
           'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    logs = HERE / 'commands'
    logs.mkdir(exist_ok=True)
    result, exception = None, None
    try:
        with (logs / (name + '.log')).open('x') as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, name + ' failed; inspect retained log'
    except Exception as error:
        exception = {'kind': type(error).__name__, 'reason': str(error)}
        raise
    finally:
        save(logs / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
             'exit_code': result.returncode if result else None, 'exception': exception,
             'wall_seconds': time.monotonic() - started})


def frozen():
    for name, checksum in read(PREP / 'source-freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, 'Frozen source changed: ' + name
    if (HERE / 'methods.json').exists():
        for name, checksum in read(HERE / 'methods.json')['bindings'].items():
            assert sha(ROOT / name) == checksum, 'Frozen method changed: ' + name


def test_command(output):
    return [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
            'tests/prospectus_successor/test_definition_scope_evidence.py',
            'tests/prospectus_successor/test_definition_declarations.py',
            'tests/prospectus_successor/test_conditional_profiles_cli.py', '--junitxml=' + str(output)]


def develop():
    assert not (HERE / 'methods.json').exists(), 'Formal methods require reviewed repair'
    number = len(list((HERE / 'development').glob('check-*.json'))) + 1
    execute('development-' + str(number).zfill(3),
            test_command(HERE / 'development' / ('tests-' + str(number).zfill(3) + '.xml')))
    return {'status': 'PASS', 'role': 'DEVELOPMENT_ONLY', 'promotion_evidence': False}


def freeze():
    functions = lambda text: {n.name: ast.dump(n) for n in ast.parse(text).body
                              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name, allowed in [('service.py', {'configure', 'dispatch'}), ('definition_applications.py', {'admit'})]:
        before = functions((PREP / 'baseline' / name).read_text())
        after = functions((ROOT / 'src/legalmath/prospectus/successor' / name).read_text())
        assert before.keys() == after.keys()
        assert all(before[n] == after[n] for n in before if n not in allowed)
    request = {k: v for k, v in read(PREP / 'request.json').items() if k != 'rules'}
    save(HERE / 'source-request.json', request)
    save(HERE / 'methods.json', {'bindings': {n: sha(ROOT / n) for n in (*FILES, rel(HERE / 'source-request.json'))},
         'production_map': packaging.package_files(ROOT / 'src/legalmath'),
         'source_only_discovery': True, 'reviewed_extents_excluded_from_discovery': True,
         'unchanged_functions_verified': True})
    return {'status': 'PASS', 'source_only_discovery': True, 'methods_frozen': True}


def tests():
    execute('tests', test_command(HERE / 'tests.xml'))
    suites = ET.parse(HERE / 'tests.xml').getroot()
    assert not any(int(r.attrib.get('failures', 0)) or int(r.attrib.get('errors', 0)) for r in suites)
    return {'status': 'PASS', 'tests': sum(int(r.attrib.get('tests', 0)) for r in suites)}


def ordinary():
    execute('ordinary-scope', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', 'prospectus',
            'discover-definition-scope', '--request', str(HERE / 'source-request.json'),
            '--output', str(HERE / 'ordinary-scope.json')])
    return {'status': 'PASS', 'actual_cli': True}


def compress(name):
    path = HERE / name
    raw = path.read_bytes()
    target = Path(str(path) + '.gz')
    with target.open('xb') as stream:
        stream.write(gzip.compress(raw, compresslevel=6, mtime=0))
    result = {'uncompressed_sha256': prep.digest(raw), 'uncompressed_bytes': len(raw),
              'compressed_path': rel(target), 'compressed_bytes': target.stat().st_size}
    path.unlink()
    return result


def compare_complete(path):
    actual = read(path)
    baseline = read(AUTH / 'attempts/basf-references/attempt-093/ordinary-answer.json.gz')
    assert actual == baseline, 'Complete answer differs from sealed093'
    assert len(actual['definition_sources']['records']) == 62
    assert len(actual['definition_remainder_review']['uses']) == 612
    return {'status': 'PASS', 'complete_baseline_equal': True, 'answer_sha256': digest(actual),
            'records': 62, 'associations': 612, 'all_readings_and_premises_preserved': True}


def consume():
    manifest = read(PREP / 'source-freeze.json')
    profiles = ROOT / manifest['profiles']
    execute('ordinary-consume', [str(ROOT / '.venv/bin/python'), '-m', 'legalmath.cli', 'prospectus',
            'consume', '--products', str(ROOT / manifest['products']), '--repository', str(ROOT),
            '--output', str(HERE / 'ordinary-answer.json'), '--mode', 'frozen',
            '--conditional-profiles', rel(profiles), '--conditional-profiles-sha256', sha(profiles)], timeout=380)
    result = compare_complete(HERE / 'ordinary-answer.json')
    return {**result, 'actual_cli': True, **compress('ordinary-answer.json')}


def audit():
    report = read(HERE / 'ordinary-scope.json')
    assert report['request_sha256'] == digest(read(HERE / 'source-request.json'))
    assert report['report_sha256'] == digest({k: v for k, v in report.items() if k != 'report_sha256'})
    actual = [{k: row[k] for k in ('start', 'end', 'status', 'extent', 'section')} for row in report['restrictions']]
    assert actual == read(PREP / 'expected.json')['restrictions']
    assert actual[3]['extent'] == read(PREP / 'line-oracle.json')['explicit_extent']
    assert report['restrictions'][3]['label_roles'] == ['HEADER']
    assert report['restrictions'][3]['boundary_roles'] == ['HEADER']
    assert report['legal_scope_established'] is report['document_authenticity_established'] is False
    result = {'status': 'PASS', 'independently_expected_restrictions': len(actual),
              'explicit_printed_sections': 1, 'ambiguous_purposes_unresolved': 4,
              'legal_scope_established': False, 'complete_answer_preserved': True}
    save(HERE / 'independent-verification.json', result)
    return result


def package():
    packaging.ROOT, packaging.AUTH, packaging.HERE = ROOT, AUTH, HERE
    packaging.execute = execute
    return packaging.package()


def installed():
    execute('installed-cli', [read(HERE / 'package.json')['python'], '-I', '-B',
            str(ROOT / 'scripts/prospectus_explicit_scope_installed.py'), str(ROOT), str(HERE), str(PREP)],
            timeout=380, cwd=HERE)
    return {**read(HERE / 'installed-result.json'), **compress('installed-answer.json')}


def seal():
    result = {'status': 'PASS', 'task': 'basf-references', 'original_task_complete': False,
              'result_kind': 'PRINTED_SELF_SECTION_CONSUMER_CONSISTENCY',
              **read(HERE / 'independent-verification.json'), **read(HERE / 'installed-result.json'),
              'resources': costs(), 'next_action': 'Original governing-use, historical-law and source-to-answer acceptance'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
         'command_records': [rel(p) for p in sorted((HERE / 'commands').glob('*.json'))],
         'environment': str(ROOT / '.venv/bin/python'), 'installed_environment': read(HERE / 'package.json')['python'],
         'cpu_gpu': 'CPU;GPU intentionally hidden', 'seeds': 'N/A deterministic',
         'data_version': sha(PREP / 'request.json'), 'wall_time': costs(), 'plan': prep.PLAN,
         'result': rel(HERE / 'result.json')})
    return result


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    stage = sys.argv[1]
    assert stage == 'develop' or stage in STAGES
    frozen()
    if stage == 'develop':
        folder = HERE / 'development'
        folder.mkdir(exist_ok=True)
        number = len(list(folder.glob('check-*.json'))) + 1
        target = folder / ('check-' + str(number).zfill(3) + '.json')
    else:
        for earlier in STAGES[:STAGES.index(stage)]:
            assert read(HERE / 'stages' / earlier / 'result.json')['status'] == 'PASS'
        folder = HERE / 'stages' / stage
        assert not folder.exists(), 'Unchanged stage retry refused'
        target = folder / 'result.json'
    assert not target.exists(), 'Unchanged diagnostic retry refused'
    costs()
    started = time.monotonic()
    started_path = folder / ('started-' + str(number).zfill(3) + '.json' if stage == 'develop' else 'started.json')
    save(started_path, {'command': sys.argv, 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[stage]()
        frozen()
        costs(time.monotonic() - started)
        result['wall_seconds'] = time.monotonic() - started
        save(target, result)
        if stage == 'seal':
            save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file()})
        print(json.dumps({k: v for k, v in result.items() if k != 'resources'}))
    except Exception as error:
        save(target if stage == 'develop' else folder / 'failure.json', {
             'status': 'FAIL', 'exception': type(error).__name__, 'reason': str(error),
             'role': 'DEVELOPMENT_ONLY' if stage == 'develop' else 'FORMAL_STAGE',
             'wall_seconds': time.monotonic() - started})
        raise


if __name__ == '__main__':
    main()
