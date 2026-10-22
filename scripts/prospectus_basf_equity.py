"""Bounded page208 reading and installed replay; all stages require PASS parents."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus import basf_equity as equity
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import service, process_ledger
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'basf-incorporation/attempt-003'
PRIOR = BASE / 'basf-incorporation/attempt-002/repair'
SOURCE = BASE / 'basf-incorporation/attempt-001'
INSTALLED = BASE / 'native-candidates/attempt-008'
PLAN = 'docs/plans/prospectus-basf-equity-content-2026-10-15.md'
IMAGE = SOURCE / 'basf-annual-2022-exchange-208.png'
RUNNER = ROOT / 'scripts/prospectus_installed_table_runner.py'
PREDECESSORS = {'prepare': (), 'profile': ('prepare',), 'baseline': ('profile',),
                'compare': ('baseline', 'profile'), 'controls': ('compare',), 'tests': ('controls',),
                'install-prepare': ('tests',), 'build': ('install-prepare',), 'install': ('build',),
                'replay': ('install',), 'verify': ('replay',)}
HEADERS = {
    '2022': [[124,125],[21,22],[23,24],[7,8,9,10],[127,128],[129,130,131],
             [119,120],[121,122,123],[11,12,13,14],[15,16,17],[18]],
    '2021': [[134,135],[136,137],[138,139],[140,141,142,143],[194,195],[196,197,198],
             [199,200],[201,202,203],[204,205,206,207],[208,209,210],[211]],
}
LABELS = {'2022': [[126],[34],[46],[58],[70],[82,83],[95],[118]],
          '2021': [[184],[152],[160],[167],[173],[185]]}
CELLS = {
    '2022': [[25,26,27,28,29,30,31,32,33,19,20],list(range(35,46)),list(range(47,58)),
             list(range(59,70)),list(range(71,82)),list(range(84,95)),list(range(96,107)),list(range(107,118))],
    '2021': [[144,145,146,147,148,149,150,151,212,213,214],
             [153,154,155,156,157,158,159,215,216,217,218],
             [161,162,163,164,165,166,219,220,221,222,223],
             [168,169,170,171,172,224,225,226,227,228,229],
             [174,175,176,177,178,230,231,232,233,234,235],
             [179,180,181,182,183,236,237,238,239,240,241]],
}
# Supplied original-image transcription, separate from geometric source association.
IMAGE_VALUES = {
    '2022': [s.split('|') for s in [
        '1,176|3,106|40,365|–3,793|406|5|–472|–3,855|40,792|1,289|42,081',
        '–32|32|–1,325|–|–|–|–|–|–1,325|–|–1,325',
        '–|–|–3,072|–|–|–|–|–|–3,072|–176 c|–3,248',
        '–|–|–627|–|–|–|–|–|–627|236|–391',
        '–|–|–|2,586|1,135|–16|84|3,788|3,788|6|3,794',
        '–|–|–|–|–|–|–116|–116|–116|–|–116',
        '–|9 d|113|–|–|12|–|12|134|–6|128',
        '1,144|3,147|35,453|–1,207|1,540|0|–504|–171|39,573|1,350|40,923']],
    '2021': [s.split('|') for s in [
        '1,176|3,115|37,911|–6,538|–1,800|7|–143|–8,474|33,728|670|34,398',
        '–|–|–3,031|–|–|–|–|–|–3,031|–281 c|–3,312',
        '–|–|5,523|–|–|–|–|–|5,523|459|5,982',
        '–|–|–|2,709|2,205|–2|–329|4,583|4,583|90|4,673',
        '–|–10 d|–37|36|–|–|–|36|–11|351|340',
        '1,176|3,106|40,365|–3,793|406|5|–472|–3,855|40,792|1,289|42,081']],
}


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with path.open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)


def package_files(folder):
    return {str(p.relative_to(folder)): file_hash(p) for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def methods():
    names = [Path(__file__), RUNNER, ROOT / PLAN, HERE / 'EXECUTION-AUDIT.md', ROOT / 'pyproject.toml',
             ROOT / 'tests/prospectus/test_basf_equity.py', ROOT / 'tests/prospectus/test_basf_statement.py']
    names += sorted((ROOT / 'src/legalmath').rglob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def bindings():
    assert not (HERE / 'outputs.json').exists()
    ad = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    if (HERE / 'methods.json').exists():
        assert methods() == read(HERE / 'methods.json')
    if (HERE / 'protected-inputs.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'protected-inputs.json').items())
    return ad


def prepare():
    protected = {}
    for folder in (PRIOR.parent, SOURCE, INSTALLED):
        for p, h in read(folder / 'outputs.json').items():
            assert file_hash(folder / p) == h
            protected[str((folder / p).relative_to(ROOT))] = h
        protected[str((folder / 'outputs.json').relative_to(ROOT))] = file_hash(folder / 'outputs.json')
    save('protected-inputs.json', protected)
    save('methods.json', methods())
    for p in methods():
        target = HERE / 'methods' / p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / p, target)
    shutil.copyfile(PRIOR / 'products.json.gz', HERE / 'products.json.gz')
    assert file_hash(HERE / 'products.json.gz') == file_hash(PRIOR / 'products.json.gz')
    save('IMAGE-REVIEW.json', {'image_path': str(IMAGE.relative_to(ROOT)), 'image_sha256': file_hash(IMAGE),
        'reviewer': 'Codex original-image review2026-10-15', 'independent': False,
        'tables': IMAGE_VALUES, 'columns': equity.COLUMNS, 'row_roles': equity.ROW_ORDER,
        'footnotes': equity.FOOTNOTES, 'occurrences': 242, 'cells': 154,
        'supplied_associations': True, 'extraction_order_is_reading_order': False})
    save('pre-run-audit.json', {'status': 'PASS', 'plan': PLAN,
        'baseline': str(PRIOR.relative_to(ROOT)), 'products_reused_exactly': True,
        'historical_native_lower_bound': 77, 'historical_source_http_lower_bound': 9,
        'promotion': 'Complete source/cell/qualification retention;exact full answer and installed outputs;actual refusals',
        'arithmetic_role': 'EXPLANATORY_ONLY', 'independent_review': False,
        'native_allowance': 0, 'http_allowance': 0, 'outer_command_limit': 4, 'local_repair_limit': 1})
    return {'products_reused_exactly': True, 'image_cells': 154, 'image_occurrences': 242}


def profile():
    products = load(HERE / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    def numbered(n):
        return anchor(units[equity.DOCUMENT + ':p208:l' + str(n)])
    source = next(d for d in products['P1']['payload']['request']['bundle']['documents'] if d['id'] == equity.DOCUMENT)
    prior = load(PRIOR / 'statement-consumer.json.gz')
    tables = []
    for year, subtitle, unit in [('2022', 5, 6), ('2021', 132, 133)]:
        rows = []
        for name, label, cells, expected in zip(equity.ROW_ORDER[year], LABELS[year], CELLS[year], IMAGE_VALUES[year]):
            values = [numbered(i) for i in cells]
            assert [a['quote'] for a in values] == expected
            rows.append({'id': name, 'label': [numbered(i) for i in label], 'cells': dict(zip(equity.COLUMNS, values))})
        tables.append({'year': year, 'subtitle': numbered(subtitle), 'unit': numbered(unit),
            'columns': [{'id': key, 'fragments': [numbered(i) for i in ids]} for key, ids in zip(equity.COLUMNS, HEADERS[year])],
            'rows': rows})
    value = {'version': equity.VERSION, 'graph_sha256': digest(graph),
        'incorporation_sha256': digest(prior['answer']['incorporation']), 'statement_sha256': digest(prior['statement_review']),
        'reviewer': {'identity': 'Codex supplied original-image review2026-10-15',
                     'basis': 'AGENT_EXPOSED_DEVELOPMENT_REVIEW', 'independent': False},
        'source': {'document': equity.DOCUMENT, 'page': 208, 'path': source['path'], 'sha256': source['sha256'],
                   'image_path': str(IMAGE.relative_to(ROOT)), 'image_sha256': file_hash(IMAGE)},
        'metadata': [numbered(i) for i in (0,1,2)], 'heading': numbered(3), 'entity': numbered(4), 'tables': tables,
        'footnotes': {k: {'marker': numbered(m), 'text': numbered(t)} for k,m,t in zip('abcd',range(186,190),range(190,194))},
        'selected_reading': None, 'financial_values_validated': False}
    save('profile.json', value)
    save('profile-pin.json', {'sha256': digest(value)})
    return {'tables': 2, 'rows': 14, 'cells': 154, 'footnotes': 4}


def baseline():
    answer = service.consume(load(HERE / 'products.json.gz'), ROOT)
    save('baseline-answer.json.gz', answer)
    assert answer == load(PRIOR / 'baseline-answer.json.gz')
    return {'full_current_answer_equal': True}


def compare():
    profile = read(HERE / 'profile.json')
    statement_profile = read(PRIOR / 'profile.json')
    result = equity.consume(load(HERE / 'products.json.gz'), statement_profile, profile, ROOT,
                            expected_statement_profile_sha256=digest(statement_profile), expected_profile_sha256=digest(profile))
    save('equity-consumer.json.gz', result)
    assert result['answer'] == load(HERE / 'baseline-answer.json.gz')
    assert {k: result[k] for k in ('answer', 'statement_review')} == load(PRIOR / 'statement-consumer.json.gz')
    review = result['equity_review']
    assert (review['printed_cells'], review['original_occurrences_accounted'], review['footnoted_amounts']) == (154, 242, 4)
    for table in review['tables']:
        assert [[r['cells'][c]['literal'] for c in equity.COLUMNS] for r in table['rows']] == IMAGE_VALUES[table['year']]
    comparisons = review['cross_statement_comparisons']
    assert len(comparisons) == 25 and all(c['status'] == 'EQUAL_PRINTED_VALUES' for c in comparisons)
    report = {'status': 'PASS', 'ordinary_answer_unchanged': True, 'page204_review_unchanged': True,
        'cells': 154, 'source_occurrences': 242, 'rows': 14, 'footnoted_amounts': 4,
        'cross_statement_equalities': 14, 'closing_opening_equalities': 11, 'comparison_role': 'EXPLANATORY_ONLY',
        'incorporation_alternatives': [r['page208_in_candidate_scope'] for r in review['incorporation_alternatives']],
        'legal_scope_resolved': False, 'financial_values_validated': False, 'independent_legal_acceptance': False,
        'native_calls': 0, 'http_calls': 0}
    save('comparison.json', report)
    return report


def controls():
    products, original = load(HERE / 'products.json.gz'), read(HERE / 'profile.json')
    prior = load(PRIOR / 'statement-consumer.json.gz')
    names = ('swapped-years', 'swapped-tables', 'cross-year-cells', 'cross-row', 'swapped-columns',
        'sign-loss', 'omitted-cell', 'duplicate-cell', 'omitted-header-fragment', 'duplicate-header-fragment',
        'cross-year-header', 'omitted-row-fragment', 'changed-unit', 'changed-source', 'changed-image',
        'omitted-footnote', 'swapped-footnote-texts', 'omitted-numeric-marker', 'wrong-numeric-marker',
        'truncated-numeric-anchor', 'omitted-subtitle-marker', 'claimed-legal-selection',
        'claimed-financial-validation', 'claimed-independent-review', 'stale-statement', 'stale-pin')
    results = []
    for name in names:
        value = deepcopy(original)
        table, other = value['tables']
        rows = {r['id']: r for r in table['rows']}
        if name == 'swapped-years': table['year'], other['year'] = other['year'], table['year']
        elif name == 'swapped-tables': value['tables'].reverse()
        elif name == 'cross-year-cells': table['rows'][0]['cells'], other['rows'][0]['cells'] = other['rows'][0]['cells'], table['rows'][0]['cells']
        elif name == 'cross-row': table['rows'][0]['cells'], table['rows'][1]['cells'] = table['rows'][1]['cells'], table['rows'][0]['cells']
        elif name == 'swapped-columns':
            cells = rows['opening']['cells']; cells['capital'], cells['reserves'] = cells['reserves'], cells['capital']
        elif name == 'sign-loss': rows['income']['cells']['equity']['quote'] = '391'
        elif name == 'omitted-cell': del rows['opening']['cells']['equity']
        elif name == 'duplicate-cell': rows['opening']['cells']['capital'] = deepcopy(rows['opening']['cells']['reserves'])
        elif name == 'omitted-header-fragment': table['columns'][3]['fragments'].pop()
        elif name == 'duplicate-header-fragment': table['columns'][3]['fragments'].append(deepcopy(table['columns'][3]['fragments'][-1]))
        elif name == 'cross-year-header': table['columns'][0]['fragments'] = deepcopy(other['columns'][0]['fragments'])
        elif name == 'omitted-row-fragment': rows['hedge_elimination']['label'].pop()
        elif name == 'changed-unit': table['unit'] = deepcopy(value['entity'])
        elif name == 'changed-source': value['source']['sha256'] = '0' * 64
        elif name == 'changed-image': value['source']['image_sha256'] = '0' * 64
        elif name == 'omitted-footnote': del value['footnotes']['c']
        elif name == 'swapped-footnote-texts': value['footnotes']['c']['text'], value['footnotes']['d']['text'] = value['footnotes']['d']['text'], value['footnotes']['c']['text']
        elif name == 'omitted-numeric-marker': rows['dividends']['cells']['nci']['quote'] = '–176'
        elif name == 'wrong-numeric-marker': rows['dividends']['cells']['nci']['quote'] = '–176 d'
        elif name == 'truncated-numeric-anchor':
            cell = rows['dividends']['cells']['nci']; cell['quote'] = '–176'; cell['end'] -= 2
        elif name == 'omitted-subtitle-marker': table['subtitle']['quote'] = 'Statement of changes in equity'
        elif name == 'claimed-legal-selection': value['selected_reading'] = 'full-financial-statements'
        elif name == 'claimed-financial-validation': value['financial_values_validated'] = True
        elif name == 'claimed-independent-review': value['reviewer']['independent'] = True
        elif name == 'stale-statement': value['statement_sha256'] = '0' * 64
        else: value['reviewer']['identity'] += 'changed'
        pin = digest(original) if name == 'stale-pin' else digest(value)
        save('adverse-inputs/' + name + '.json.gz', {'profile': value, 'expected_profile_sha256': pin})
        try:
            equity.evaluate(products['P1']['payload']['graph'], prior['answer']['incorporation'], prior['statement_review'],
                            value, ROOT, expected_profile_sha256=pin)
        except ValueError as error:
            results.append({'case': name, 'refused': True, 'repinned': name != 'stale-pin', 'reason': str(error)})
        else:
            raise AssertionError('Altered source reading accepted: ' + name)
    save('actual-controls.json', results)
    return {'actual_controls_refused': len(results), 'repinned': len(results) - 1}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_basf_statement.py', 'tests/prospectus/test_basf_equity.py',
                        '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'pytest_exit': int(code)}


def workspace():
    return Path(read(HERE / 'workspace.json')['directory'])


def install_prepare():
    old = Path(read(INSTALLED / 'workspace.json')['directory']) / 'environment'
    assert package_files(old / 'lib/python3.11/site-packages/legalmath') == read(INSTALLED / 'source-package.json')
    temp = Path(tempfile.mkdtemp(prefix='installed-basf-tables-', dir=ROOT / '.localresources/prospectus'))
    save('workspace.json', {'directory': str(temp), 'environment_cloned_from': str(old)})
    shutil.copytree(old, temp / 'environment', symlinks=True)
    (temp / 'source').mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', temp / 'source/pyproject.toml')
    shutil.copytree(ROOT / 'src', temp / 'source/src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    shutil.copyfile(RUNNER, temp / 'runner.py')
    package = package_files(temp / 'source/src/legalmath')
    old_package = read(INSTALLED / 'source-package.json')
    assert all(package.get(p) == h for p, h in old_package.items())
    added = sorted(set(package) - set(old_package))
    assert added == ['prospectus/basf_equity.py', 'prospectus/basf_statement.py']
    save('source-package.json', package)
    save('prior-optional-identity.json', {'status': 'PASS', 'all_prior_package_files_unchanged': len(old_package),
        'prior_optional_apis': ['geometry', 'review', 'boundaries', 'regions', 'native-text', 'edition'],
        'prior_evidence': str(INSTALLED.relative_to(ROOT)), 'new_modules': added})
    save('environment-metadata.json', {str(p.relative_to(temp / 'environment')): file_hash(p)
        for p in (temp / 'environment/lib/python3.11/site-packages').glob('*.dist-info/METADATA')})
    process_ledger.create(HERE / 'command-ledger.json', 4, 0, 'Build,install,combined two-table replay;one repair spare;zero native calls')
    return {'source_files': len(package), 'unchanged_prior_files': len(old_package), 'new_modules': added}


def run(name, argv):
    folder = HERE / 'commands' / name
    folder.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1',
           'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1'}
    save('commands/' + name + '/started.json', {'argv': argv, 'cwd': str(workspace()), 'timeout': 110,
        'environment': {k: env[k] for k in ('CUDA_VISIBLE_DEVICES', 'PYTHONPATH', 'PYTHONNOUSERSITE', 'PIP_NO_INDEX')}})
    tick = time.monotonic()
    with (folder / 'stdout').open('xb') as out, (folder / 'stderr').open('xb') as err, process_ledger.observe(HERE / 'command-ledger.json'):
        result = subprocess.run(argv, cwd=workspace(), env=env, stdout=out, stderr=err, timeout=110)
    save('commands/' + name + '/result.json', {'returncode': result.returncode, 'wall_seconds': time.monotonic() - tick})
    assert result.returncode == 0, 'See retained ' + name + ' stdout/stderr'
    return {'returncode': 0}


def build():
    (HERE / 'wheel').mkdir()
    run('build', [str(workspace() / 'environment/bin/python'), '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                  '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(workspace() / 'source')])
    wheels = list((HERE / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    result = {'path': str(wheels[0].relative_to(HERE)), 'sha256': file_hash(wheels[0])}
    save('built-wheel.json', result)
    return result


def install():
    wheel = read(HERE / 'built-wheel.json')
    assert file_hash(HERE / wheel['path']) == wheel['sha256']
    return run('install', [str(workspace() / 'environment/bin/python'), '-m', 'pip', 'install', '--no-index',
                           '--no-deps', '--force-reinstall', str(HERE / wheel['path'])])


def replay():
    run('replay', [str(workspace() / 'environment/bin/python'), '-I', str(workspace() / 'runner.py'), str(HERE), str(ROOT)])
    return read(HERE / 'installed-results/result.json')


def verify():
    result = read(HERE / 'installed-results/result.json')
    assert result['status'] == 'PASS' and result['full_outputs_equal'] and result['native_calls'] == 0
    assert result['controls'] == {'statement': 14, 'equity': 26}
    package = workspace() / 'environment/lib/python3.11/site-packages/legalmath'
    expected = read(HERE / 'source-package.json')
    assert package_files(package) == expected == read(HERE / 'installed-results/package-files.json')
    proof = read(HERE / 'installed-results/import-proof.json')
    assert proof['isolated'] == 1
    for module in proof['modules'].values():
        p = Path(module['path']).resolve()
        assert p.is_relative_to(package) and file_hash(p) == module['sha256'] == expected[str(p.relative_to(package))]
    assert load(HERE / 'installed-results/equity-consumer.json.gz') == load(HERE / 'equity-consumer.json.gz')
    assert load(HERE / 'installed-results/statement-consumer.json.gz') == load(PRIOR / 'statement-consumer.json.gz')
    ledger = process_ledger.checked(HERE / 'command-ledger.json')
    assert len(ledger['reservations']) == 3
    result = {**read(HERE / 'comparison.json'), 'installed_full_outputs_equal': True,
        'actual_controls_refused': 40, 'new_equity_controls': 26, 'outer_commands': 3,
        'exact_package_files': len(expected), 'prior_package_files_unchanged': 420,
        'different_host_portability': False, 'local_repairs_used': 0,
        'historical_visible_native_reservation_lower_bound': 77,
        'historical_visible_source_http_lower_bound': 9}
    save('verified-result.json', result)
    return result


def main():
    stage = sys.argv[1]
    assert stage in PREDECESSORS
    ad = bindings()
    for prior in PREDECESSORS[stage]:
        assert read(HERE / 'invocations' / prior / 'result.json')['status'] == 'PASS', 'Failed prerequisite: ' + prior
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_basf_equity', stage],
        'git_commit': ad['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'random_seeds': 'N/A deterministic',
        'cpu_gpu': 'CPU only;no GPU/framework imports;children CUDA_VISIBLE_DEVICES=-1',
        'required_predecessors': list(PREDECESSORS[stage])})
    tick = time.monotonic()
    def expired(signum, frame):
        raise TimeoutError('120-second equity stage bound;no automatic retry')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(120)
    try:
        details = globals()[stage.replace('-', '_')]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        if (HERE / 'workspace.json').exists():
            size += sum(p.stat().st_size for p in workspace().rglob('*') if p.is_file())
        assert size < 500 * 1024 * 1024
        result = {'status': 'PASS', 'stage': stage, 'details': details,
                  'wall_seconds': time.monotonic() - tick, 'evidence_and_workspace_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
            'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
