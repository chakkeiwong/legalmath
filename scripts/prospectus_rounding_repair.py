"""Bounded continuation of sealed entitlement003; no baseline re-execution."""
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import gzip
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/entitlement/attempt-003'
HERE = AUTH / 'attempts/entitlement/attempt-004'
PLAN = 'docs/plans/prospectus-rounding-storage-repair-2026-10-15.md'
DOSSIER = 'docs/implementation/prospectus-execution-authority/dossiers/entitlement-rounding-storage-repair.md'
STAGES = ['prepare', 'candidate', 'adverse-direct', 'adverse-selected', 'legacy', 'tests', 'verify']
LIMIT = 70_000_000
NEW_LIMIT = 10_000_000
RESERVE = 500_000
SUPPORT = [PLAN, DOSSIER, 'scripts/prospectus_rounding_repair.py',
           'docs/implementation/prospectus-execution-authority/proposals/entitlement-storage-104.json',
           'docs/implementation/prospectus-execution-authority/proposals/entitlement-storage-104-review.json',
           'docs/implementation/prospectus-execution-authority/revisions/0104.json',
           'docs/implementation/prospectus-execution-authority/closure-routes-2026-10-15-storage-repair.json']


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.name.endswith('.gz') else raw)


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def storage():
    attempts = sum(p.stat().st_size for p in HERE.parent.rglob('*') if p.is_file())
    current = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    support = sum((ROOT / p).stat().st_size for p in SUPPORT)
    return {'cumulative_bytes': attempts + support, 'attempt004_bytes': current,
            'support_bytes': support, 'cumulative_limit': LIMIT, 'attempt004_limit': NEW_LIMIT}


def put(name, value=None, *, raw=None):
    path = HERE / name
    assert not path.exists(), 'Refuse overwrite: ' + name
    if raw is None:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode() + b'\n'
    if name.endswith('.gz'):
        raw = gzip.compress(raw, mtime=0)
    usage = storage()
    assert usage['cumulative_bytes'] + len(raw) + RESERVE <= LIMIT, usage
    assert usage['attempt004_bytes'] + len(raw) + RESERVE <= NEW_LIMIT, usage
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


@lru_cache(None)
def helper():
    spec = importlib.util.spec_from_file_location('retained_rounding_baseline', BASE / 'run_rounding.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def methods():
    before = read(BASE / 'started.json')['before_methods']
    names = [p for p in before if p.startswith(('src/', 'tests/')) or p == 'scripts/prospectus_closure_fixtures.py']
    names += ['scripts/prospectus_rounding_repair.py', PLAN, DOSSIER,
              str((BASE / 'run_rounding.py').relative_to(ROOT))]
    return {p: file_hash(ROOT / p) for p in names}


@lru_cache(maxsize=2)
def baseline(name):
    path = BASE / 'baseline' / name
    expected = read(BASE / 'outputs.json')['baseline/' + name]
    assert file_hash(path) == expected, name
    return read(path)


def changes(old, new, prefix=()):
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(old.keys() | new.keys()):
            if key not in new:
                result.append({'op': 'delete', 'path': [*prefix, key]})
            elif key not in old:
                result.append({'op': 'set', 'path': [*prefix, key], 'value': new[key]})
            else:
                result.extend(changes(old[key], new[key], (*prefix, key)))
        return result
    if type(old) is type(new) and digest(old) == digest(new):
        return []
    return [{'op': 'set', 'path': list(prefix), 'value': new}]


def apply_changes(old, patch):
    value = deepcopy(old)
    for row in patch:
        assert row['op'] in {'set', 'delete'}
        path = row['path']
        if not path:
            assert row['op'] == 'set'
            value = deepcopy(row['value'])
            continue
        node = value
        for key in path[:-1]:
            node = node[key]
        if row['op'] == 'delete':
            del node[path[-1]]
        else:
            node[path[-1]] = deepcopy(row['value'])
    return value


def expand(packed):
    assert packed['version'] == 'prospectus-lossless-record.v1'
    name = packed['baseline']['name']
    assert Path(name).name == name
    assert file_hash(BASE / 'baseline' / name) == packed['baseline']['sha256']
    value = apply_changes(baseline(name), packed['changes'])
    assert digest(value) == packed['expanded_sha256'], 'Expanded evidence differs'
    return value


def retain(folder, name, value, base_name):
    packed = {'version': 'prospectus-lossless-record.v1',
              'baseline': {'name': base_name, 'sha256': file_hash(BASE / 'baseline' / base_name)},
              'changes': changes(baseline(base_name), value), 'expanded_sha256': digest(value)}
    assert digest(expand(packed)) == digest(value)
    put(f'{folder}/{name}.json.gz', packed)


def prepare():
    old = read(BASE / 'started.json')
    manifest = read(BASE / 'outputs.json')
    for rel, expected in manifest.items():
        assert file_hash(BASE / rel) == expected, rel
    for rel, expected in old['sources'].items():
        assert file_hash(ROOT / rel) == expected, rel
    current = methods()
    for rel, expected in old['before_methods'].items():
        if rel in current:
            assert current[rel] == expected, 'Baseline method drift: ' + rel
    assert read(BASE / 'baseline-result.json')['status'] == 'FAIL'
    assert read(BASE / 'result.json')['status'] == 'FAIL'
    example = {'nested': {'keep': [1, {'x': True}], 'remove': 2}, 'type': True}
    target = {'nested': {'keep': [1, {'x': False}], 'new': None}, 'type': 1}
    assert digest(apply_changes(example, changes(example, target))) == digest(target)
    for old_value, new_value in [(True, 1), (1, True), ([True], [1]), ({'x': 1}, {'x': 1.0})]:
        assert digest(apply_changes(old_value, changes(old_value, new_value))) == digest(new_value)
    name = 'direct-original-active.json.gz'
    value = baseline(name)
    packed = {'version': 'prospectus-lossless-record.v1',
              'baseline': {'name': name, 'sha256': file_hash(BASE / 'baseline' / name)},
              'changes': [], 'expanded_sha256': digest(value)}
    assert digest(expand(packed)) == digest(value)
    for field in ['baseline', 'expanded_sha256']:
        bad = deepcopy(packed)
        if field == 'baseline':
            bad['baseline']['sha256'] = '0' * 64
        else:
            bad[field] = '0' * 64
        try:
            expand(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError('Tampered evidence accepted')
    put('started.json', {'started_at': datetime.now(timezone.utc).isoformat(),
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'environment': str(Path(sys.executable).resolve()), 'cpu_gpu': 'CPU only; GPU intentionally hidden',
        'random_seeds': 'N/A deterministic controls', 'plan_file': PLAN,
        'result_file': str((HERE / 'RESULT.md').relative_to(ROOT)), 'sources': old['sources'],
        'before_methods': current, 'baseline_attempt': str(BASE.relative_to(ROOT)),
        'baseline_output_manifest_sha256': file_hash(BASE / 'outputs.json'),
        'prior_baseline_wall_seconds': read(BASE / 'baseline-result.json')['wall_seconds'],
        'prior_failure_preserved': True, 'no_baseline_rerun': True, 'storage': storage(),
        'codec_checks': ['nested add/delete', 'list replacement', 'Boolean/integer distinction',
                         'exact complete reconstruction', 'baseline hash tampering refused', 'expanded hash tampering refused']})
    return {'sealed_baseline_files_verified': len(manifest), 'codec': 'PASS', 'storage': storage()}


def candidate():
    h = helper()
    current = methods()
    before = read(HERE / 'started.json')['before_methods']
    changed = [p for p in before if before[p] != current[p]]
    assert set(changed) == {'src/legalmath/prospectus/successor/fixed_coupon.py', *h.TEST_FILES[:3]}, changed
    put('candidate-methods.json', current)
    for rel in changed:
        put('candidate-method/' + rel, raw=(ROOT / rel).read_bytes())
    rows = []
    for route in ['direct', 'selected']:
        products = h.products_for(route)
        for label, change in h.VALID:
            for entitled in [True, False]:
                supplied, rounding = h.inputs(products, route)
                for row in supplied['holdings']:
                    row['entitled'] = entitled
                if change:
                    rounding.update(change)
                name = f'{route}-{label}-' + ('active' if entitled else 'excluded')
                record = h.consume(products, route) if label == 'original' and entitled else h.consume(products, route, supplied, rounding)
                h.assert_valid(record, route, supplied)
                assert digest(record) == digest(baseline(name + '.json.gz')), name
                retain('candidate', name, record, name + '.json.gz')
                rows.append({'case': name, 'complete_record_equal': True,
                             'amounts': [r['amount'] for r in h.calculated(record, route)['transfers']]})
    return {'valid_complete_comparisons': rows, 'changed_files': changed}


def adverse(route):
    h = helper()
    products = h.products_for(route)
    rows = []
    base_name = route + '-original-active.json.gz'
    for field, invalids in h.INVALID.items():
        for index, invalid in enumerate(invalids):
            for entitled in [True, False]:
                supplied, rounding = h.inputs(products, route)
                for row in supplied['holdings']:
                    row['entitled'] = entitled
                rounding[field] = invalid
                record = h.consume(products, route, supplied, rounding)
                expected = 'UNSUPPORTED' if route == 'direct' else 'ValueError'
                assert record['boundary'] == expected, (field, invalid, entitled, record['boundary'], record.get('error'))
                if route == 'direct':
                    assert 'rounding' in ' '.join(record['answer']['questions']['Q5']['unresolved'])
                    for question in ['Q1', 'Q2', 'Q3', 'Q4', 'Q6']:
                        assert record['answer']['questions'][question] == baseline(base_name)['answer']['questions'][question]
                else:
                    assert 'rounding' in record['error']
                    assert record['products']['P3']['payload']['contract_terms']['terms']['rounding']['value'] == rounding
                name = f'{route}-{field}-{index}-' + ('active' if entitled else 'excluded')
                retain('adverse', name, record, base_name)
                rows.append({'case': name, 'field': field, 'invalid': invalid, 'entitled': entitled, 'boundary': expected})
    put(f'adverse/{route}-index.json', rows)
    return {'route': route, 'actual_consumer_refusals': len(rows)}


def legacy():
    h = helper()
    rows = []
    for route in ['direct', 'selected']:
        for form in ['global', 'definitive']:
            products = h.shell_products(route + '-' + form)
            for entitled in [True, False]:
                supplied, rounding = h.inputs(products, route)
                for row in supplied['holdings']:
                    row['entitled'] = entitled
                record = h.consume(products, route) if entitled else h.consume(products, route, supplied, rounding)
                name = f'shell-{route}-{form}-' + ('active' if entitled else 'excluded')
                h.assert_valid(record, route, supplied)
                assert digest(record) == digest(baseline(name + '.json.gz')), name
                retain('legacy', name, record, name + '.json.gz')
                rows.append({'case': name, 'complete_record_equal': True})
    for entitled in [True, False]:
        for quantum in [None, 0, '1/0']:
            record = h.original_v2(entitled, quantum)
            name = 'v2-' + ('active' if entitled else 'excluded') + '-' + str(quantum).replace('/', '_')
            assert record['boundary'] == ('CONDITIONAL' if quantum is None else 'UNSUPPORTED'), name
            if quantum is None:
                assert digest(record) == digest(baseline(name + '.json')), name
            put('legacy/' + name + '.json', record)
    return {'valid_complete_comparisons': rows, 'v2_valid': 2, 'v2_refusals': 4}


def tests():
    h = helper()
    with tempfile.TemporaryDirectory(prefix='prospectus-rounding-') as folder:
        xml = Path(folder) / 'tests.xml'
        argv = [sys.executable, '-m', 'pytest', '-q', *h.TEST_FILES, '--junitxml=' + str(xml)]
        env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1'}
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True, timeout=110)
        put('tests.log', raw=(result.stdout + result.stderr).encode())
        put('tests-command.json', {'argv': argv, 'returncode': result.returncode, 'test_invocations': 1})
        if xml.exists():
            put('tests.xml', raw=xml.read_bytes())
    assert result.returncode == 0, result.stdout[-3500:] + result.stderr[-1000:]
    cases = list(ET.parse(HERE / 'tests.xml').getroot().iter('testcase'))
    new = {name: sum(c.get('name', '').startswith(name) for c in cases) for name in h.NEW_TESTS}
    assert all(new.values()), new
    from legalmath.prospectus.successor.closure_program import JOBS
    paths, expression = JOBS['R5']
    assert set(h.TEST_FILES[:3]) <= set(paths.split()) and 'coupon' in expression.split(' or ')
    put('registered-regressions.json', {'executed_cases': new, 'registered_paths': paths,
        'expression': expression, 'second_test_invocation': False})
    return {'new_regressions': new, 'test_invocations': 1}


def verify_records():
    h = helper()
    valid = 0
    for folder in ['candidate', 'legacy']:
        for path in sorted((HERE / folder).glob('*.json.gz')):
            packed = read(path)
            actual = expand(packed)
            assert digest(actual) == digest(baseline(packed['baseline']['name'])), path.name
            for stage, product in actual['products'].items():
                h.service.verify(product, stage)
            valid += 1
    assert valid == 24
    total = 0
    for route in ['direct', 'selected']:
        rows = read(HERE / f'adverse/{route}-index.json')
        assert len(rows) == 38
        for field, invalids in h.INVALID.items():
            for entitled in [True, False]:
                assert digest([r['invalid'] for r in rows if r['field'] == field and r['entitled'] is entitled]) == digest(invalids)
        for row in rows:
            record = expand(read(HERE / f'adverse/{row["case"]}.json.gz'))
            assert record['boundary'] == row['boundary']
            assert digest(record['rounding'][row['field']]) == digest(row['invalid'])
            assert all(r['entitled'] is row['entitled'] for r in record['supplied']['holdings'])
            for stage, product in record['products'].items():
                h.service.verify(product, stage)
        total += len(rows)
    for entitled in [True, False]:
        for quantum in [None, 0, '1/0']:
            name = 'v2-' + ('active' if entitled else 'excluded') + '-' + str(quantum).replace('/', '_') + '.json'
            record = read(HERE / 'legacy' / name)
            assert record['boundary'] == ('CONDITIONAL' if quantum is None else 'UNSUPPORTED')
            if quantum is None:
                assert digest(record) == digest(baseline(name))
    return valid, total


def verify():
    assert methods() == read(HERE / 'candidate-methods.json')
    for rel, expected in read(HERE / 'started.json')['sources'].items():
        assert file_hash(ROOT / rel) == expected, rel
    for rel, expected in read(BASE / 'outputs.json').items():
        assert file_hash(BASE / rel) == expected, rel
    valid, refusals = verify_records()
    counts = {key: sum(int(s.get(key, 0)) for s in ET.parse(HERE / 'tests.xml').getroot().iter('testsuite'))
              for key in ['tests', 'failures', 'errors', 'skipped']}
    assert counts['tests'] > 0 and all(counts[k] == 0 for k in ['failures', 'errors', 'skipped'])
    result = {'status': 'PASS', 'full_P5_Q1_Q6_comparisons': valid, 'actual_consumer_refusals': refusals,
              'v2_valid_comparisons': 2, 'v2_typed_refusals': 4, 'focused_tests': counts,
              'new_regressions': read(HERE / 'registered-regressions.json')['executed_cases'],
              'storage': storage(), 'baseline_rerun': False, 'failed003_preserved': True,
              'actual_entitlement_established': False, 'independent_legal_acceptance': False,
              'full_settlement_supported': False, 'task_complete': False}
    put('comparison.json', result)
    return result


def elapsed():
    previous = read(BASE / 'baseline-result.json')['wall_seconds']
    return previous + sum(read(p)['wall_seconds'] for p in HERE.glob('*-result.json'))


def seal():
    assert not (HERE / 'outputs.json').exists()
    assert methods() == read(HERE / 'candidate-methods.json')
    comparison = read(HERE / 'comparison.json')
    assert comparison['status'] == 'PASS' and comparison['full_P5_Q1_Q6_comparisons'] == 24
    sessions = read(HERE / 'tool-sessions.json')
    assert set(sessions) == set(STAGES)
    rows = []
    for stage in STAGES:
        result = read(HERE / f'{stage}-result.json')
        assert result['status'] == 'PASS'
        limit = 30 if stage == 'prepare' else 120
        assert result['wall_seconds'] < limit
        rows.append({'stage': stage, 'command': ['timeout', str(limit), '.venv/bin/python',
                     'scripts/prospectus_rounding_repair.py', stage], 'wall_seconds': result['wall_seconds'],
                     'tool_session': sessions[stage], 'polled_to_completion': True})
    assert elapsed() < 840
    for name in ['RESULT.md', 'NEXT-WORK.md']:
        assert (HERE / name).is_file()
    put('run-manifest.json', {**read(HERE / 'started.json'), 'stages': rows,
        'wall_seconds_cumulative003_004': elapsed(), 'test_invocations': 1, 'running_sessions': [],
        'storage': storage(), 'changed_repairs': 1, 'duplicate_product_launches': 0,
        'historical_failure': 'Sealed003 baseline exceeded40MB; all evidence retained; no retroactive PASS',
        'retained_source_scope': 'Frozen graphs/assembly; actual changed selected terms readmitted through P3',
        'artifacts': ['candidate', 'adverse', 'legacy', 'tests.xml', 'comparison.json', 'RESULT.md', 'NEXT-WORK.md']})
    put('result.json', {'task': 'entitlement', 'status': 'PASS', 'task_complete': False,
        'execution_plan_compliant': True, 'comparison': comparison, 'result_note': 'RESULT.md',
        'meaning_of_status': 'Finite rounding repair passed; actual entitlement obligations remain partial',
        'acceptance_blockers': ['Authentic form/holder/event/clearing records', 'Independent legal review',
                                'Broader financial and settlement coverage'],
        'next_action': 'Record, refresh and inspect independent remaining routes'})
    paths = [p for p in sorted(HERE.rglob('*')) if p.is_file()]
    put('outputs.json', {str(p.relative_to(HERE)): file_hash(p) for p in paths})
    print(json.dumps({'sealed_files': len(paths), 'storage': storage(), 'task_complete': False}))


def main():
    stage = sys.argv[1]
    if stage == 'seal':
        seal()
        return
    assert stage in STAGES
    assert (HERE / 'admission.json').exists()
    assert not (HERE / f'{stage}-started.json').exists(), 'Refuse stage relaunch'
    index = STAGES.index(stage)
    if index:
        assert read(HERE / f'{STAGES[index-1]}-result.json')['status'] == 'PASS'
        if stage != 'candidate':
            assert methods() == read(HERE / 'candidate-methods.json'), 'Candidate method drift'
    assert elapsed() < 840
    tick = time.monotonic()
    put(f'{stage}-started.json', {'started_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).relative_to(ROOT)), stage], 'pid': os.getpid()})
    try:
        result = adverse(stage.removeprefix('adverse-')) if stage.startswith('adverse-') else globals()[stage]()
        assert elapsed() + time.monotonic() - tick < 840
    except BaseException as exc:
        put(f'{stage}-result.json', {'status': 'FAIL', 'error': str(exc),
            'traceback': traceback.format_exc(), 'wall_seconds': time.monotonic() - tick})
        raise
    duration = time.monotonic() - tick
    put(f'{stage}-result.json', {'status': 'PASS', 'result': result, 'wall_seconds': duration})
    print(json.dumps({'stage': stage, 'status': 'PASS', 'wall_seconds': duration}))


if __name__ == '__main__':
    main()
