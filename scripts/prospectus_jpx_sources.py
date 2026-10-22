"""Bounded original JPX programme/correction acquisition and actual consumer."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import base64
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus.successor import process_ledger, sealed_runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import VERSION, digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'native-layout-cases/attempt-005'
OLD = BASE / 'native-layout-cases/attempt-002'
SNAPSHOT = BASE / 'native-binding/attempt-008/snapshot'
PYTHON = '/home/chakwong/miniconda3/envs/tfgpu/bin/python'
WORKER = ROOT / 'scripts/prospectus_jpx_inspector.py'
PLAN = 'docs/plans/prospectus-jpx-source-pair-2026-10-15.md'
PREFIX = 'https://www.jpx.co.jp/equities/products/tpbm/announcement/detail/nlsgeu0000035yn5-att/'
FILES = {'programme': 't13vrt000001rjc9.pdf', 'correction': 't13vrt000001rjhr.pdf'}
CODEC_REPAIR = len(sys.argv) > 1 and sys.argv[1].startswith('codec-')
ACQUISITION = HERE
NATIVE_HISTORY = 69
NATIVE_LIMIT = 3
if CODEC_REPAIR:
    HERE = BASE / 'native-layout-cases/attempt-006'
    SNAPSHOT = ACQUISITION / 'snapshot'
    PLAN = 'docs/plans/prospectus-jpx-codec-repair-2026-10-15.md'
    NATIVE_HISTORY = 70


def load(path):
    return json.loads(gzip.decompress(Path(path).read_bytes())) if str(path).endswith('.gz') else read(path)


def save(name, value):
    if name.endswith('.gz'):
        with (HERE / name).open('xb') as stream:
            stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), mtime=0))
    else:
        write(HERE / name, value, exclusive=True)


def bindings():
    assert not (HERE / 'outputs.json').exists()
    ad = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    if (HERE / 'methods.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'methods.json').items())
    return ad


def prepare():
    if CODEC_REPAIR:
        for name, hashed in read(ACQUISITION / 'outputs.json').items():
            assert file_hash(ACQUISITION / name) == hashed
        assert 'unknown encoding: raw_unicode_escape' in (ACQUISITION / 'native-inspect/0/stderr').read_text()
        methods = {str(p.relative_to(ROOT)): file_hash(p) for p in [Path(__file__), WORKER] + sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))}
        save('methods.json', methods)
        for name in methods:
            target = HERE / 'methods' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        save('repair-audit.json', {'status': 'PASS', 'plan': PLAN,
            'negative_comparator': str((ACQUISITION / 'native-inspect/0/receipt.json').relative_to(ROOT)),
            'negative_comparator_sha256': file_hash(ACQUISITION / 'native-inspect/0/receipt.json'),
            'repair': 'Add exactly installed encodings/raw_unicode_escape.py;same interpreter,inspector and PDF bytes',
            'new_http_starts': 0, 'historical_visible_source_http_lower_bound': 8,
            'historical_visible_native_reservation_lower_bound': 70,
            'not_concluded': 'Complete codec registry coverage or independent Japanese accuracy'})
        return {'retained_originals': 2, 'http_starts': 0, 'native_starts': 0, 'repair': 'single codec declaration'}
    links = read(OLD / 'jpx-issuer-document-links.json')
    catalogue = (OLD / 'fetches/06/body').read_text()
    assert all(PREFIX + name in links and name in catalogue for name in FILES.values())
    sources = [{'id': 'jpx-jica-' + key, 'role': key, 'url': PREFIX + name,
        'catalogue_label': 'プログラム情報' if key == 'programme' else '訂正プログラム情報',
        'catalogue_display_date': '2026/08/06', 'official_listing_date_is_not_proven_publication': True}
        for key, name in FILES.items()]
    save('candidates.json', {'issuer_label': '独立行政法人 国際協力機構', 'sources': sources,
        'catalogue_path': str((OLD / 'fetches/06/body').relative_to(ROOT)),
        'catalogue_sha256': file_hash(OLD / 'fetches/06/body'), 'prior_http_starts': 6,
        'http_start_limit': 3, 'vertical_writing': 'UNTESTED', 'plan_audit': 'PASS: two exact observed links;no layout or historical-authority assumption'})
    methods = {str(p.relative_to(ROOT)): file_hash(p) for p in [Path(__file__), WORKER] + sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))}
    save('methods.json', methods)
    for name in methods:
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return {'exact_candidates': 2, 'http_starts': 0, 'native_starts': 0}


def reserve(role):
    assert role in FILES
    folders = sorted((HERE / 'fetches').glob('*')) if (HERE / 'fetches').exists() else []
    assert len(folders) < 3, 'HTTP start limit exhausted'
    folder = HERE / 'fetches' / str(len(folders) + 1).zfill(2)
    folder.mkdir(parents=True, exist_ok=False)
    argv = ['curl', '--silent', '--show-error', '--connect-timeout', '10', '--max-time', '25',
        '--max-filesize', '20971520', '--max-redirs', '0', '--dump-header', str((folder / 'headers').relative_to(ROOT)),
        '--output', str((folder / 'body').relative_to(ROOT)), '--write-out',
        '{"http_code":"%{http_code}","size_download":%{size_download},"time_total":%{time_total}}', PREFIX + FILES[role]]
    write(folder / 'started.json', {'role': role, 'number': len(folders)+1, 'command': argv,
        'started_at': datetime.now(timezone.utc).isoformat(), 'budget_maximum': 3,
        'prior_http_starts': 6, 'state': 'RESERVED_HTTP_COMMAND'}, exclusive=True)
    return {'number': len(folders)+1, 'command': argv}


def record(role):
    metrics = json.loads(sys.argv[2])
    exit_code = int(sys.argv[3])
    folders = [p for p in sorted((HERE / 'fetches').glob('*'))
        if read(p / 'started.json')['role'] == role and not (p / 'result.json').exists()]
    assert len(folders) == 1
    folder = folders[0]
    body = folder / 'body'
    result = {**metrics, 'exit_code': exit_code, 'actual_command': read(folder / 'started.json')['command'],
        'redirect_followed': False, 'execution': 'trusted network command',
        'retained_files': {name: {'sha256': file_hash(folder / name), 'bytes': (folder / name).stat().st_size}
                          for name in ('headers', 'body') if (folder / name).exists()}}
    write(folder / 'result.json', result, exclusive=True)
    assert exit_code == 0 and str(metrics['http_code']) == '200', 'Retained non-successful HTTP attempt'
    assert body.read_bytes().startswith(b'%PDF-') and body.stat().st_size == metrics['size_download'] <= 20 * 1024 * 1024
    target = HERE / (role + '.pdf')
    with target.open('xb') as stream:
        stream.write(body.read_bytes())
    return {'role': role, 'source_sha256': file_hash(target), 'source_bytes': target.stat().st_size}


def native_prepare():
    spec = {'sources': [{'id': 'jpx-jica-' + role, 'path': str(ACQUISITION / (role + '.pdf')),
                         'sha256': file_hash(ACQUISITION / (role + '.pdf'))} for role in FILES]}
    save('inspection-spec.json', spec)
    folder = HERE / 'snapshot'
    (folder / 'blobs').mkdir(parents=True, exist_ok=False)
    manifest = deepcopy(sealed_runtime.validate(read(SNAPSHOT / 'manifest.json')))
    for hashed in {r['sha256'] for r in manifest['files']}:
        assert file_hash(SNAPSHOT / 'blobs' / hashed) == hashed
        shutil.copyfile(SNAPSHOT / 'blobs' / hashed, folder / 'blobs' / hashed)
    added = {}
    paths = [WORKER] + [Path(s['path']) for s in spec['sources']]
    if CODEC_REPAIR:
        paths.append(Path(PYTHON).parent.parent / 'lib/python3.11/encodings/raw_unicode_escape.py')
    for path in paths:
        hashed = file_hash(path)
        existing = next((r for r in manifest['files'] if r['path'] == str(path)), None)
        if existing:
            assert existing['sha256'] == hashed
            continue
        shutil.copyfile(path, folder / 'blobs' / hashed)
        manifest['files'].append({'path': str(path), 'sha256': hashed, 'size': path.stat().st_size, 'mode': 0o444})
        manifest['directories'] = sorted(set(manifest['directories']) | {str(p) for p in path.parents if str(p) != '/'})
        added[str(path)] = hashed
    manifest['files'].sort(key=lambda r: r['path'])
    sealed_runtime.validate(manifest)
    save('snapshot/manifest.json', manifest)
    save('snapshot/provenance.json', {'parent': str(SNAPSHOT.relative_to(ROOT)),
        'parent_sha256': file_hash(SNAPSHOT / 'manifest.json'), 'added': added})
    if CODEC_REPAIR:
        assert len(added) == 1 and next(iter(added)).endswith('/encodings/raw_unicode_escape.py')
        save('dependency-repair.json', {'only_added_file': added, 'old_files_unchanged': True,
            'failed_parent_preserved': True, 'source_pdfs_unchanged': True, 'inspector_unchanged': True})
    process_ledger.create(HERE / 'native-ledger.json', NATIVE_LIMIT, NATIVE_HISTORY,
        'One joint native inventory/render;remaining reserved starts for actual Poppler sources;no OCR or native retry')
    return {'sources': len(spec['sources']), 'snapshot_files': len(manifest['files']), 'native_starts': 0}


def runtime(stage):
    manifest = read(HERE / 'snapshot/manifest.json')
    return sealed_source.SourceRuntime(HERE / 'snapshot', sealed_runtime.digest(manifest),
        evidence_directory=HERE / ('native-' + stage), native_text_max_stream=64 * 1024 * 1024)


def inspect():
    spec = read(HERE / 'inspection-spec.json')
    required = {str(p): file_hash(p) for p in [Path(PYTHON), WORKER] + [Path(s['path']) for s in spec['sources']]}
    rt = runtime('inspect')
    with process_ledger.observe(HERE / 'native-ledger.json'):
        result = rt.execute([PYTHON, str(WORKER)], json.dumps(spec).encode(), required, max_stream=64 * 1024 * 1024)
    output = json.loads(result['stdout'])
    for source in output['sources']:
        for obs in source['observations']:
            name = source['id'] + '-page-' + str(obs['page'])
            with (HERE / (name + '.png')).open('xb') as stream:
                stream.write(base64.b64decode(obs.pop('image_base64'), validate=True))
            assert file_hash(HERE / (name + '.png')) == obs['image_sha256']
            save(name + '-native.json.gz', obs)
    save('inspection.json', output)
    return {'sources': [{'id': s['id'], 'pages': s['page_count'], 'inspected': s['inspected_pages'],
        'wmode1_pages': s['vertical_nomination_pages'], 'selected_pages': [r['page'] for r in s['observations']]}
        for s in output['sources']]}


def source():
    inspection = read(HERE / 'inspection.json')
    assert read(HERE / 'IMAGE-REVIEW.json')['reviewed'] is True
    docs = []
    for row in inspection['sources']:
        role = row['id'].removeprefix('jpx-jica-')
        receipts = [p / 'result.json' for p in sorted((ACQUISITION / 'fetches').glob('*'))
            if read(p / 'started.json')['role'] == role and (p / 'result.json').exists()
            and str(read(p / 'result.json')['http_code']) == '200']
        assert len(receipts) == 1
        docs.append({'id': row['id'], 'path': str((ACQUISITION / (role + '.pdf')).relative_to(ROOT)),
            'sha256': row['source_sha256'], 'language': 'ja', 'format': 'pdf', 'page_count': row['page_count'],
            'authority': 'Original bytes from observed official JPX link;publication,legal priority and independent authenticity not established',
            'acquisition': {'path': str(receipts[0].relative_to(ROOT)), 'sha256': file_hash(receipts[0])}})
    observed = read(HERE / 'invocations/prepare/started.json')['started_at']
    request = {'version': VERSION, 'bundle': {'instrument_id': 'jpx-jica-programme-correction-development',
        'purpose': 'review', 'issue_date': observed, 'effective_at': observed, 'known_at': observed, 'documents': docs},
        'scope': {'Q1': {'complete': False, 'reason': 'Original Japanese source diagnostic;observation timestamps are not issue facts'},
                  'Q2': {'complete': False, 'reason': 'No accepted language or programme/correction scope reading'}}}
    save('request.json', request)
    rt = runtime('source')
    with process_ledger.observe(HERE / 'native-ledger.json'):
        product = sealed_source.source_product(request, ROOT, rt)
    save('source-product.json.gz', product)
    save('source-receipts.json', rt.receipts)
    assert len(rt.receipts) == 2
    return {'source_units': product['payload']['graph']['unit_count'], 'native_text_calls': 2}


def construct():
    p1 = load(HERE / 'source-product.json.gz')
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume(products, ROOT, include_artifacts=True)
    save('products.json.gz', products)
    save('answer.json.gz', answer)
    return {'questions': {q: r['status'] for q, r in answer['questions'].items()},
            'source_units': len(answer['source_map']['units'])}


def compare():
    products = load(HERE / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    exact = []
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    for index, doc in enumerate(read(HERE / 'request.json')['bundle']['documents']):
        folder = HERE / 'native-source' / str(index)
        raw = (folder / 'stdout').read_bytes().decode('utf-8')
        xml = ET.fromstring(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw))
        xml_words = [''.join(w.itertext()) for w in xml.findall('.//x:word', ns)]
        units = [u for u in graph['units'] if u['document'] == doc['id']]
        words = [w['text'] for u in units for w in u.get('words', [])]
        assert Counter(xml_words) == Counter(words)
        assert all(u['raw'][w['start']:w['end']] == w['text'] for u in units for w in u.get('words', []))
        exact.append({'document': doc['id'], 'page_count': doc['page_count'], 'native_units': len(units),
                      'xml_words': len(xml_words), 'all_native_word_occurrences_preserved': True})
    save('native-word-accounting.json', exact)
    repeated = service.consume(products, ROOT, include_artifacts=True)
    assert repeated == load(HERE / 'answer.json.gz')
    save('reconsumed-answer.json.gz', repeated)
    controls = []
    for name in ('changed-source-word', 'wrong-parent'):
        bad = deepcopy(products)
        if name == 'changed-source-word':
            bad['P1']['payload']['graph']['units'][0]['raw'] += '!'
        else:
            bad['P2']['inputs']['P1'] = '0' * 64
            bad['P2']['sha256'] = digest({k: v for k, v in bad['P2'].items() if k != 'sha256'})
        try:
            service.consume(bad, ROOT)
        except ValueError as error:
            controls.append({'case': name, 'refused': True, 'reason': str(error)})
        else:
            raise AssertionError('Tampered source accepted')
    save('actual-controls.json', controls)
    assert len(process_ledger.checked(HERE / 'native-ledger.json')['reservations']) == 3
    manifest = read(HERE / 'snapshot/manifest.json')
    for stage, number in (('inspect', 1), ('source', 2)):
        for index in range(number):
            folder = HERE / ('native-' + stage) / str(index)
            receipt = read(folder / 'receipt.json')
            sealed_runtime.verify_receipt(receipt, manifest, receipt['argv'], (folder / 'stdin').read_bytes(),
                (folder / 'stdout').read_bytes(), (folder / 'stderr').read_bytes())
    inspection = read(HERE / 'inspection.json')
    report = {'status': 'PASS', 'scope': 'ORIGINAL_JAPANESE_PROGRAMME_CORRECTION_SOURCE_DIAGNOSTIC',
        'original_sources': 2, 'source_pages': sum(s['page_count'] for s in inspection['sources']),
        'inspected_pages': sum(s['inspected_pages'] for s in inspection['sources']),
        'native_wmode1_pages': sum(len(s['vertical_nomination_pages']) for s in inspection['sources']),
        'visual_vertical_text_established': read(HERE / 'IMAGE-REVIEW.json')['true_vertical_established'],
        'native_word_occurrences_preserved': sum(r['xml_words'] for r in exact),
        'full_answer_reproduced': True, 'altered_controls_refused': len(controls),
        'native_reservations': 3, 'historical_visible_native_reservation_lower_bound': NATIVE_HISTORY + 3,
        'http_starts': 0 if CODEC_REPAIR else len(list((HERE / 'fetches').glob('*'))),
        'prior_source_http_starts': 8 if CODEC_REPAIR else 6,
        'missing_codec_repair': CODEC_REPAIR,
        'independent_reading': False, 'amendment_meaning_established': False, 'complete_coverage': False}
    save('comparison.json', report)
    return report


def main():
    stage = sys.argv[1].removeprefix('codec-') if CODEC_REPAIR else sys.argv[1]
    assert stage in {'prepare', 'reserve-programme', 'reserve-correction', 'record-programme', 'record-correction',
                     'native-prepare', 'inspect', 'source', 'construct', 'compare'}
    ad = bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_jpx_sources', *sys.argv[1:]],
        'environment': sys.executable, 'native_environment': PYTHON, 'git_commit': ad['git_commit'],
        'plan': PLAN, 'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only;CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic'})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second stage bound;no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        if stage.startswith('reserve-'): details = reserve(stage.removeprefix('reserve-'))
        elif stage.startswith('record-'): details = record(stage.removeprefix('record-'))
        else: details = globals()[stage.replace('-', '_')]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 350 * 1024 * 1024
        outcome = {'status': 'PASS', 'stage': stage, 'details': details, 'evidence_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)
    outcome['wall_seconds'] = time.monotonic()-tick
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps(outcome, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].startswith('edition-'):
        from scripts.prospectus_programme_editions import main as edition_main
        edition_main(sys.argv[1][len('edition-'):])
    else:
        main()
