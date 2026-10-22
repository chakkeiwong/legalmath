"""Bounded source-authority003 stages, selected by the execution authority."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

START = time.monotonic()
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
from legalmath.prospectus.successor import archive_observations, service
from legalmath.prospectus.successor.contracts import digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority'
HERE = BASE / 'attempts/source-authority/attempt-003'
Q1 = BASE / 'attempts/source-bes-dep-11/attempt-001'
SECOND = Q1.parent / 'attempt-002'
PLAN = 'docs/plans/prospectus-archive-textsearch-2026-10-16.md'
PROFILE = 'source-archive-observations.textsearch.v1'
TESTS = ['tests/prospectus_successor/test_archive_observations.py',
         'tests/prospectus_successor/test_report_scope.py']
CASES = ['baseline-current', 'capture-after-supplement', 'capture-at', 'capture-before',
         'capture-printed-date', 'baseline-early-knowledge', 'capture-early-knowledge']
CAPTURE = '2011-05-27T01:20:12Z'
NATIVE = []


def file_hash(path):
    h = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(name, value):
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with (HERE / name).open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)


def methods():
    paths = [*sorted((ROOT / 'src/legalmath/prospectus').rglob('*.py')), Path(__file__)]
    paths += [ROOT / n for n in TESTS + ['tests/prospectus_successor/test_successor.py', 'tests/conftest.py']]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def verify(name):
    assert all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items()), name


def binding(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': file_hash(path)}


def packet():
    record = read(Q1 / 'release-search.json')['response_items'][8]
    event = read(BASE / 'history/000111.json')
    return {'version': PROFILE, 'query_at': '2011-06-06T00:00:00Z',
        'review': {'reviewer': 'executor', 'kind': 'DEVELOPMENT',
                   'reason': 'Exact retained Q1 replay; URL equivalence and independent source authority unresolved'},
        'captures': [{'id': 'arquivo-q1-2011', 'document': 'bes-release-q111',
            'source_sha256': file_hash(Q1 / 'release.pdf'), 'original_url': record['originalURL'],
            'capture_at': CAPTURE, 'retrieved_at': event['at'],
            'index': binding(Q1 / 'release-search.json'), 'record_index': 8,
            'headers': binding(Q1 / 'release.headers'), 'content': binding(Q1 / 'release.pdf'),
            'memento_original_url': 'http://www.bes.pt/sitebes/cms.aspx?plg=999945b1-d68b-4029-8fdb-9655c6792edd',
            'receipt': binding(Q1 / 'network.json'), 'receipt_request_index': 1,
            'retrieval_record': binding(BASE / 'history/000111.json'),
            'retained_outputs': binding(Q1 / 'outputs.json')}]}


def prepare():
    admission = read(HERE / 'admission.json')
    assert admission['task'] == 'source-authority' and admission['revision'] == 108
    assert Path(service.__file__).resolve().is_relative_to(ROOT / 'src')
    bindings = deepcopy(admission['binding'])
    histories = [Q1, SECOND, HERE.parent / 'attempt-001', HERE.parent / 'attempt-002']
    verified = {}
    for prior in histories:
        outputs = read(prior / 'outputs.json')
        assert all(file_hash(prior / p) == h for p, h in outputs.items()), str(prior)
        verified[str(prior.relative_to(ROOT))] = len(outputs)
        bindings.update({str((prior / p).relative_to(ROOT)): h for p, h in outputs.items()})
    old = read(Q1 / 'source-product.json.gz')
    service.verify(old, 'P1')
    for d in old['payload']['request']['bundle']['documents']:
        assert file_hash(ROOT / d['path']) == d['sha256']
        bindings[d['path']] = d['sha256']
    (HERE / 'before').mkdir()
    shutil.copyfile(ROOT / 'src/legalmath/prospectus/successor/archive_observations.py', HERE / 'before/archive_observations.py')
    save('archive-input.json', packet())
    for mode in ('current', 'early'):
        req = read(Q1 / 'request-with-readings.json')
        graph = deepcopy(old['payload']['graph'])
        if mode == 'early':
            req['bundle']['known_at'] = '2026-10-12T19:54:25Z'
            graph['context']['known_at'] = req['bundle']['known_at']
            graph['bundle_sha256'] = digest(req['bundle'])
            assert 'layout' not in graph
            req['source_report_readings']['graph_sha256'] = digest(graph)
        p1 = service.seal('P1', req['bundle'], {'request': digest(req)}, {'request': req, 'graph': graph})
        p2 = service.construction_product(p1, ROOT)
        selected = p2['payload']['source_report_readings']
        assert selected['reports'] == read(Q1 / 'selected-reading.json')['reports']
        scope = read(SECOND / 'corrected-original-scope.json')
        scope['readings_sha256'] = digest(selected)
        assert scope['reports'][0]['reading_sha256'] == selected['reports'][0]['sha256']
        reference = read(Q1 / 'reference-admission.json')
        reference['assembly_sha256'] = digest(p2['payload']['assembly'])
        save(mode + '-common.json.gz', {'P1': p1, 'P2': p2, 'scope': scope, 'reference': reference})
    baseline_packet = packet()
    baseline_packet['version'] = archive_observations.VERSION
    for row in baseline_packet['captures']:
        for k in ('memento_original_url', 'receipt', 'receipt_request_index', 'retrieval_record', 'retained_outputs'):
            row.pop(k)
    req = deepcopy(read(HERE / 'current-common.json.gz')['P1']['payload']['request'])
    req['archive_observations'] = baseline_packet
    source = service.seal('P1', req['bundle'], {'request': digest(req)},
                          {'request': req, 'graph': old['payload']['graph']})
    try:
        service.construction_product(source, ROOT)
    except ValueError as error:
        refusal = str(error)
    else:
        raise AssertionError('Expected current adapter refusal was not reproduced')
    assert 'Archive index URL, date or PDF status differs' in refusal
    save('baseline-refusal.json', {'reproduced': True, 'P2_refusal': refusal,
         'missing_statusCode': 'statusCode' not in read(Q1 / 'release-search.json')['response_items'][8],
         'separate_url_mismatch': packet()['captures'][0]['original_url'] != packet()['captures'][0]['memento_original_url']})
    bindings.update({str((HERE / n).relative_to(ROOT)): file_hash(HERE / n) for n in
                     ('archive-input.json', 'current-common.json.gz', 'early-common.json.gz')})
    save('input-bindings.json', bindings)
    save('before-methods.json', methods())
    return {'prior_files_verified': sum(verified.values()), 'baseline_refusal': refusal,
            'historical_P1': True, 'fresh_P2': True, 'selected_units': len(old['payload']['graph']['units'])}


def candidate():
    verify('input-bindings.json')
    before = read(HERE / 'before-methods.json')
    allowed = {'src/legalmath/prospectus/successor/archive_observations.py', TESTS[0]}
    assert all(file_hash(ROOT / p) == h for p, h in before.items() if p not in allowed)
    spec = importlib.util.spec_from_file_location('legalmath.prospectus.successor._archive003_before', HERE / 'before/archive_observations.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    prior = HERE.parent / 'attempt-002'
    checks = {}
    for name in ('original', 'current'):
        bundle = read(prior / (name + '-common.json.gz'))['request']['bundle']
        for date in ('2011-07-15T00:00:00Z', '2015-04-24T13:29:17Z'):
            supplied = read(prior / 'archive-input.json')
            supplied['query_at'] = date
            checks[name + ':' + date] = old.admit(bundle, supplied, ROOT) == archive_observations.admit(bundle, supplied, ROOT)
    assert all(checks.values())
    save('v1-compatibility.json', checks)
    save('frozen-methods.json', methods())
    return {'old_v1_exact_equality': checks}


def tests():
    verify('frozen-methods.json')
    import pytest
    args = ['-q', *TESTS, '--basetemp=' + str(HERE / 'test-tmp'), '--junitxml=' + str(HERE / 'tests.xml')]
    with (HERE / 'tests.log').open('x') as log, redirect_stdout(log), redirect_stderr(log):
        code = pytest.main(args)
    rows = list(ET.parse(HERE / 'tests.xml').getroot().iter('testcase'))
    result = {'exit_code': int(code), 'tests': len(rows), 'pytest_args': args,
              'failed': [r.attrib.get('name') for r in rows if any(r.find(k) is not None for k in ('failure', 'error', 'skipped'))]}
    save('test-summary.json', result)
    assert code == 0 and not result['failed'], result
    verify('frozen-methods.json')
    return result


def run_case(case):
    verify('input-bindings.json')
    verify('frozen-methods.json')
    mode = 'early' if 'early-knowledge' in case else 'current'
    common = read(HERE / (mode + '-common.json.gz'))
    req = deepcopy(common['P1']['payload']['request'])
    graph = common['P1']['payload']['graph']
    expected = None
    if case.startswith('capture'):
        supplied = read(HERE / 'archive-input.json')
        supplied['query_at'] = {'capture-at': CAPTURE, 'capture-before': '2011-05-27T01:20:11Z',
                               'capture-printed-date': '2011-05-02T00:00:00Z'}.get(case, '2011-06-06T00:00:00Z')
        req['archive_observations'] = supplied
        expected = ('EVIDENCE_NOT_YET_KNOWN' if mode == 'early' else
                    'NOT_ESTABLISHED_BY_THIS_CAPTURE' if case in ('capture-before', 'capture-printed-date') else
                    'ARCHIVE_RECORDED_BY_QUERY_DATE')
    assert len(list(HERE.glob('call-*.json'))) < 8
    save('call-' + case + '.json', {'started_utc': datetime.now(timezone.utc).isoformat()})
    p1 = service.seal('P1', req['bundle'], {'request': digest(req)}, {'request': req, 'graph': graph})
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2, {'source_report_scope': common['scope'], 'reference_admission': common['reference']})
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume(products, ROOT)
    save(case + '-answer.json.gz', answer)
    packed = deepcopy(products)
    packed['P1']['payload'] = {}
    packed['P2']['payload'] = {}
    envelope = {'common': mode + '-common.json.gz', 'common_sha256': file_hash(HERE / (mode + '-common.json.gz')),
                'archive_input': req.get('archive_observations'), 'archive_output': p2['payload'].get('archive_observations'), 'products': packed}
    restored = restore(envelope)
    assert restored == products
    save(case + '-products.json.gz', envelope)
    assert answer['consumed_products'] == {k: p['sha256'] for k, p in products.items()}
    assert not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
    assert answer['questions']['Q3']['status'] == 'PARTIAL'
    report, = answer['source_reports']
    assert report['use_assessment']['unaudited_financial_release'] == 'SUPPLIED_SOURCE_DESCRIPTION'
    assert report['facts']['conclusion']['status'] == 'UNKNOWN'
    if expected:
        observation, = answer['source_archive_observations']['observations']
        assert observation['as_of_query'] == expected
        assert observation['original_url_equivalence'] == 'NOT_ESTABLISHED'
        assert observation['archive_index_http_status'] == 'UNKNOWN'
        assert observation['source_origin'] == 'SAME_RETAINED_ARCHIVE_REPLAY'
        assert observation['publication_date'] == observation['edition_authenticity'] == 'UNKNOWN'
        assert not observation['legal_availability_established'] and not observation['earlier_absence_established']
        assert report['archive_observations'] == [observation]
    else:
        assert 'source_archive_observations' not in answer
    verify('input-bindings.json')
    verify('frozen-methods.json')
    return {'case': case, 'as_of_query': expected, 'report_status': report['status']}


def restore(envelope):
    assert file_hash(HERE / envelope['common']) == envelope['common_sha256']
    common = read(HERE / envelope['common'])
    result = deepcopy(envelope['products'])
    result['P1']['payload'] = deepcopy(common['P1']['payload'])
    if envelope['archive_input'] is not None:
        result['P1']['payload']['request']['archive_observations'] = envelope['archive_input']
    result['P2']['payload'] = deepcopy(common['P2']['payload'])
    if envelope['archive_output'] is not None:
        result['P2']['payload']['archive_observations'] = envelope['archive_output']
    for stage, p in result.items():
        service.verify(p, stage)
    return result


def compare():
    verify('input-bindings.json')
    verify('frozen-methods.json')
    checks = {}
    for case in CASES:
        mode = 'early' if 'early-knowledge' in case else 'current'
        basecase = 'baseline-early-knowledge' if mode == 'early' else 'baseline-current'
        answer = read(HERE / (case + '-answer.json.gz'))
        baseline = read(HERE / (basecase + '-answer.json.gz'))
        products = restore(read(HERE / (case + '-products.json.gz')))
        baseproducts = restore(read(HERE / (basecase + '-products.json.gz')))
        checks[case + ': actual identities'] = answer['consumed_products'] == {k: v['sha256'] for k, v in products.items()}
        checks[case + ': answer integrity'] = answer['report_sha256'] == digest({k: v for k, v in answer.items() if k != 'report_sha256'})
        checks[case + ': questions unchanged'] = answer['questions'] == baseline['questions']
        checks[case + ': reports unchanged except observation'] = [{k: v for k, v in r.items() if k != 'archive_observations'} for r in answer['source_reports']] == baseline['source_reports']
        checks[case + ': construction unchanged except observation'] = {k: v for k, v in products['P2']['payload'].items() if k != 'archive_observations'} == baseproducts['P2']['payload']
        for stage in ('P3', 'P4', 'P5'):
            checks[case + ': ' + stage + ' payload unchanged'] = products[stage]['payload'] == baseproducts[stage]['payload']
        original = products['P1']['payload']['request']['bundle']['dependencies']
        checks[case + ': fourteen original unresolved'] = len(original) == 14 and all(d['status'] == 'UNRESOLVED' and d in products['P3']['payload']['dependencies'] for d in original)
        checks[case + ': no permissions'] = not answer['independent_legal_acceptance'] and not answer['may_execute_transaction']
    checks['old profile exact equality'] = all(read(HERE / 'v1-compatibility.json').values())
    checks['all regression tests pass'] = not read(HERE / 'test-summary.json')['failed']
    checks['within native test-only bound'] = sum(len(read(p)) for p in HERE.glob('stage-*-native.json')) <= 64
    save('comparison.json', {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks})
    assert all(checks.values()), [k for k, v in checks.items() if not v]
    return {'checks': len(checks)}


def boundaries(test=False):
    def forbid(*a, **k):
        raise RuntimeError('Unreviewed process/network execution forbidden in archive003')
    original = subprocess.Popen
    executable = Path(shutil.which('pdftotext')).resolve() if test else None
    executable_hash = file_hash(executable) if test else None
    def pdf_only(argv, *a, **k):
        if not test or not isinstance(argv, list) or len(argv) != 6:
            return forbid()
        assert argv[1:4] == ['-bbox-layout', '-enc', 'UTF-8'] and argv[5] == '-'
        resolved = Path(shutil.which(argv[0])).resolve()
        path = Path(argv[4]).resolve()
        assert resolved == executable and file_hash(resolved) == executable_hash
        assert path.is_relative_to((HERE / 'test-tmp').resolve()) and path.suffix == '.pdf'
        assert path.stat().st_size < 100_000 and not k.get('shell') and not a
        assert len(NATIVE) < 64
        NATIVE.append({'argv': argv, 'executable_sha256': executable_hash, 'input_sha256': file_hash(path)})
        return original(argv, **k)
    subprocess.Popen = pdf_only
    os.system = forbid
    if hasattr(os, 'posix_spawn'): os.posix_spawn = forbid
    if hasattr(os, 'posix_spawnp'): os.posix_spawnp = forbid
    socket.create_connection = forbid
    socket.socket.connect = forbid
    socket.socket.connect_ex = forbid


def seal():
    ends = [read(p) for p in HERE.glob('stage-*-result.json')]
    passed = (HERE / 'comparison.json').is_file() and read(HERE / 'comparison.json')['status'] == 'PASS' and all(r['status'] == 'PASS' for r in ends)
    if passed:
        verify('input-bindings.json')
        verify('frozen-methods.json')
    assert (HERE / 'RESULT.md').is_file() and (HERE / 'NEXT-WORK.md').is_file()
    elapsed = sum(r['wall_seconds'] for r in ends) + time.monotonic() - START
    assert elapsed < 360
    result = {'task': 'source-authority', 'status': 'PASS' if passed else 'FAIL', 'task_complete': False,
        'meaning_of_status': 'Finite optional Q1 text-search observation only', 'wall_seconds': elapsed,
        'actual_consumer_calls': len(list(HERE.glob('call-*.json'))),
        'acceptance_blockers': ['Independent archive/edition authenticity absent', 'Original publication and legal availability unknown',
                                'Index/Memento URL equivalence unresolved; source is the same retained replay'],
        'result_note': 'RESULT.md', 'next_action': 'Continue reviewed independent routes; no fourth source admission implied'}
    save('result.json', result)
    outputs = {str(p.relative_to(HERE)): file_hash(p) for p in sorted(HERE.rglob('*')) if p.is_file()
               and p.name not in ('outputs.json', 'admission.json') and '__pycache__' not in p.parts}
    save('outputs.json', outputs)
    size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
    assert size < 80_000_000
    return {**result, 'files': len(outputs), 'bytes': size}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['prepare', 'candidate', 'tests', 'case', 'compare', 'seal'])
    parser.add_argument('--case', choices=CASES)
    args = parser.parse_args()
    if args.stage == 'seal':
        print(json.dumps(seal()), flush=True)
        return
    assert not (HERE / 'outputs.json').exists()
    starts, ends = list(HERE.glob('stage-*-start.json')), list(HERE.glob('stage-*-result.json'))
    assert len(starts) == len(ends), 'Incomplete earlier stage; do not duplicate it'
    results = [read(p) for p in ends]
    assert all(r['status'] == 'PASS' for r in results), 'Prior stage veto'
    elapsed = sum(r['wall_seconds'] for r in results)
    assert elapsed < 360
    if args.stage != 'prepare': assert read(HERE / 'stage-prepare-result.json')['status'] == 'PASS'
    if args.stage in ('tests', 'case', 'compare'): assert read(HERE / 'stage-candidate-result.json')['status'] == 'PASS'
    assert args.stage != 'case' or args.case
    name = args.stage + ('-' + args.case if args.case else '')
    command = ['timeout', '120', '.venv/bin/python', '-m', 'scripts.prospectus_archive_textsearch', *sys.argv[1:]]
    save('stage-' + name + '-start.json', {'command': command, 'started_at': datetime.now(timezone.utc).isoformat()})
    def expired(signum, frame): raise TimeoutError('Reviewed execution bound reached')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(max(1, min(118, int(360 - elapsed))))
    outcome = {'status': 'PASS'}
    try:
        boundaries(args.stage == 'tests')
        outcome['details'] = run_case(args.case) if args.stage == 'case' else globals()[args.stage]()
    except Exception as error:
        outcome.update(status='FAIL', error=type(error).__name__ + ': ' + str(error))
        with (HERE / ('stage-' + name + '-traceback.txt')).open('x') as log:
            traceback.print_exc(file=log)
    finally:
        signal.alarm(0)
    save('stage-' + name + '-native.json', NATIVE)
    outcome.update(wall_seconds=time.monotonic() - START, command=command, environment=sys.executable,
        git_commit=read(HERE / 'admission.json')['git_commit'], cpu_gpu='CPU only; GPU intentionally hidden',
        random_seeds='N/A', plan=PLAN, result='RESULT.md', data_version='input-bindings.json',
        completed_at=datetime.now(timezone.utc).isoformat())
    save('stage-' + name + '-result.json', outcome)
    print(json.dumps({'stage': name, 'status': outcome['status'], 'wall_seconds': outcome['wall_seconds'], 'error': outcome.get('error')}), flush=True)
    if outcome['status'] != 'PASS': raise SystemExit(1)


if __name__ == '__main__':
    main()
