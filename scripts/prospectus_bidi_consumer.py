"""Bounded actual source consumer for the retained mixed Arabic/Latin original."""
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import gzip
import json
import os
import re
from pathlib import Path
import shutil
import signal
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, file_hash, read, write
from legalmath.prospectus.successor import process_ledger, sealed_runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import VERSION, digest

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'native-layout-cases/attempt-003'
SOURCE = BASE / 'native-layout-cases/attempt-002'
SNAPSHOT = BASE / 'native-binding/attempt-008/snapshot'
PLAN = 'docs/plans/prospectus-bidi-consumer-2026-10-15.md'
URLS = ('https://www.riyadbank.com/', 'www.cma.org.sa',
        'www.saudiexchange.sa', 'https://www.riyadcapital.com/')
PAGES = (5, 6, 14)


def save(name, value):
    write(HERE / name, value, exclusive=True)


def gzsave(name, value):
    with (HERE / name).open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), mtime=0))


def gzread(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def consumer_methods():
    return {str(p.relative_to(ROOT)): file_hash(p)
            for p in sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))}


def check_bindings():
    admission = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / name) == hashed for name, hashed in admission['binding'].items())
    assert not (HERE / 'outputs.json').exists()
    if (HERE / 'consumer-methods.json').exists():
        assert consumer_methods() == read(HERE / 'consumer-methods.json')
    return admission


def prepare():
    for name, hashed in read(SOURCE / 'outputs.json').items():
        assert file_hash(SOURCE / name) == hashed
    manifest = deepcopy(sealed_runtime.validate(read(SNAPSHOT / 'manifest.json')))
    folder = HERE / 'snapshot'
    (folder / 'blobs').mkdir(parents=True, exist_ok=False)
    for hashed in {r['sha256'] for r in manifest['files']}:
        assert file_hash(SNAPSHOT / 'blobs' / hashed) == hashed
        shutil.copyfile(SNAPSHOT / 'blobs' / hashed, folder / 'blobs' / hashed)
    source = (SOURCE / 'riyad-bank-sukuk-ar.pdf').resolve()
    hashed = file_hash(source)
    assert str(source) not in {r['path'] for r in manifest['files']}
    shutil.copyfile(source, folder / 'blobs' / hashed)
    manifest['files'].append({'path': str(source), 'sha256': hashed,
                              'size': source.stat().st_size, 'mode': 0o444})
    manifest['files'].sort(key=lambda r: r['path'])
    manifest['directories'] = sorted(set(manifest['directories']) |
                                    {str(p) for p in source.parents if str(p) != '/'})
    sealed_runtime.validate(manifest)
    save('snapshot/manifest.json', manifest)
    save('snapshot/provenance.json', {'parent': str(SNAPSHOT.relative_to(ROOT)),
         'parent_manifest_sha256': file_hash(SNAPSHOT / 'manifest.json'),
         'added': {str(source): hashed}, 'copied_blobs_verified': True})
    process_ledger.create(HERE / 'native-ledger.json', 2, 62,
                         'One planned native text source; one diagnostic/trusted fallback reservation; no OCR')
    observed = '2026-10-15T00:00:00+08:00'
    request = {'version': VERSION, 'bundle': {
        'instrument_id': 'riyad-arabic-sukuk-development-observation', 'purpose': 'review',
        'issue_date': observed, 'effective_at': observed, 'known_at': observed,
        'documents': [{'id': 'riyad-ar', 'path': str(source.relative_to(ROOT)),
            'sha256': hashed, 'page_count': 198, 'language': 'ar',
            'authority': 'Observed CMA catalogue original; legal authority and publication date not independently established',
            'acquisition': {'path': str((SOURCE / 'fetches/04/result.json').relative_to(ROOT)),
                            'sha256': file_hash(SOURCE / 'fetches/04/result.json')}}]}}
    save('request.json', request)
    save('consumer-methods.json', consumer_methods())
    for name in consumer_methods():
        target = HERE / 'consumer-methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return {'snapshot_files': len(manifest['files']), 'source_sha256': hashed,
            'native_starts': 0, 'observation_time_is_not_issue_date': True}


def source(stage):
    manifest = read(HERE / 'snapshot/manifest.json')
    runtime = sealed_source.SourceRuntime(HERE / 'snapshot', sealed_runtime.digest(manifest),
        evidence_directory=HERE / ('native-' + stage), native_text_max_stream=64 * 1024 * 1024)
    with process_ledger.observe(HERE / 'native-ledger.json'):
        product = sealed_source.source_product(read(HERE / 'request.json'), ROOT, runtime)
    assert len(runtime.receipts) == 1
    gzsave('source-product.json.gz', product)
    save('native-receipts.json', runtime.receipts)
    return {'pages': product['payload']['graph']['documents'][0]['page_count'],
            'units': product['payload']['graph']['unit_count'], 'native_starts_this_stage': 1}


def diagnose():
    graph = gzread(HERE / 'source-product.json.gz')['payload']['graph']
    selected = [u for u in graph['units'] if u['page'] in PAGES]
    gzsave('selected-poppler-units.json.gz', selected)
    inventory = []
    for page in PAGES:
        native = gzread(SOURCE / f'riyad-page-{page}-native-reviewed.json.gz')
        units = [u for u in selected if u['page'] == page]
        # Exact literals are compared within original occurrences; no reversal or cleanup.
        checks = []
        for target in URLS if page == 6 else ():
            checks.append({'literal': target,
                'poppler': [{'unit': u['id'], 'start': i, 'end': i + len(target), 'raw': u['raw']}
                            for u in units for i in range(len(u['raw'])) if u['raw'].startswith(target, i)],
                'pymupdf_text_occurrences': native['text'].count(target),
                'pymupdf_word_occurrences': sum(w[4].count(target) for w in native['words'])})
        chars = ''.join(u['raw'] for u in units)
        inventory.append({'page': page, 'poppler_units': len(units),
            'poppler_rtl_characters': sum(unicodedata.bidirectional(c) in {'R', 'AL'} for c in chars),
            'poppler_ltr_letters': sum(unicodedata.bidirectional(c) == 'L' for c in chars),
            'exact_url_checks': checks,
            'directions_not_inferred': True, 'independent_transcription': False})
    save('native-comparison.json', {'pages': inventory, 'comparators_are_extraction_observations': True,
                                  'full_arabic_quality_evaluated': False})
    return {'selected_pages': list(PAGES), 'selected_units': len(selected),
            'literal_matches': [{ 'literal': r['literal'], 'poppler': len(r['poppler']),
                'pymupdf_text': r['pymupdf_text_occurrences'], 'pymupdf_words': r['pymupdf_word_occurrences']}
                for p in inventory for r in p['exact_url_checks']]}


def construct():
    p1 = gzread(HERE / 'source-product.json.gz')
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
                'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume(products, ROOT, include_artifacts=True)
    gzsave('products.json.gz', products)
    gzsave('baseline-answer.json.gz', answer)
    return {'questions': {q: r['status'] for q, r in answer['questions'].items()},
            'units': len(answer['source_map']['units']), 'native_starts': 0}


def compare():
    products = gzread(HERE / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    units = [u for u in graph['units'] if u['page'] in PAGES]
    native_folder = HERE / 'native-source-trusted/0'
    receipt = read(native_folder / 'receipt.json')
    manifest = read(HERE / 'snapshot/manifest.json')
    sealed_runtime.verify_receipt(receipt, manifest, receipt['argv'],
        (native_folder / 'stdin').read_bytes(), (native_folder / 'stdout').read_bytes(),
        (native_folder / 'stderr').read_bytes())
    raw_xml = (native_folder / 'stdout').read_bytes().decode('utf-8')
    illegal = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
    removed = [{'offset': m.start(), 'codepoint': ord(m.group())} for m in illegal.finditer(raw_xml)]
    assert removed == graph['documents'][0]['xml_illegal_characters']
    xml = ET.fromstring(illegal.sub('', raw_xml))
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    pages = xml.findall('.//x:page', ns)
    assert len(pages) == 198
    xml_checks = []
    for page in PAGES:
        lines = [line for block in pages[page - 1].findall('.//x:block', ns)
                 for line in block.findall('x:line', ns)]
        actual = [u for u in units if u['page'] == page]
        assert len(lines) == len(actual)
        for line, unit in zip(lines, actual):
            words = [''.join(w.itertext()) for w in line.findall('x:word', ns)]
            assert words == [w['text'] for w in unit['words']]
            assert unit['raw'] == ' '.join(words)
            assert all(unit['raw'][w['start']:w['end']] == w['text'] for w in unit['words'])
        xml_checks.append({'page': page, 'lines': len(lines), 'all_xml_words_preserved': True,
                           'inserted_space_rule_confirmed': True})
    literal_evidence = []
    for target in URLS:
        exact = [u['id'] for u in units if u['page'] == 6 and target in u['raw']]
        joined = []
        for unit in units:
            if unit['page'] != 6:
                continue
            chars = [(i, c) for i, c in enumerate(unit['raw']) if not c.isspace()]
            compact = ''.join(c for _, c in chars)
            start = compact.find(target)
            if start >= 0:
                offsets = [i for i, _ in chars[start:start + len(target)]]
                joined.append({'unit': unit['id'], 'raw_start': offsets[0], 'raw_end': offsets[-1] + 1,
                    'raw_quote': unit['raw'][offsets[0]:offsets[-1] + 1],
                    'character_offsets': offsets, 'removed_spaces': offsets[-1] - offsets[0] + 1 - len(target),
                    'status': 'DIAGNOSTIC_ONLY; NOT_AN_EXACT_SOURCE_MATCH'})
        assert not exact and len(joined) == 1
        literal_evidence.append({'literal': target, 'exact_matches': exact, 'formatting_diagnosis': joined})
    paired = []
    for page in PAGES:
        pymu = gzread(SOURCE / f'riyad-page-{page}-native-reviewed.json.gz')['words']
        for unit in units:
            if unit['page'] != page:
                continue
            for word in unit['words']:
                matches = [w for w in pymu if max(abs(a-b) for a,b in zip(w[:4], word['bbox'])) <= .001]
                for other in matches:
                    if (word['text'] != other[4] and word['text'] == other[4][::-1]
                            and any(unicodedata.bidirectional(c) in {'R','AL'} for c in word['text'])):
                        paired.append({'page': page, 'unit': unit['id'], 'bbox': word['bbox'],
                            'poppler': word['text'], 'pymupdf': other[4],
                            'basis': 'Exact reversal at matching rectangles within 0.001 point; explanatory only'})
    save('literal-attribution.json', {'xml_pages': xml_checks, 'urls': literal_evidence,
         'xml_illegal_characters_retained_in_native_stream': removed,
         'paired_reverse_tokens': paired, 'coordinate_tolerance_points': .001,
         'tolerance_role': 'Nominate source-token correspondences; not language truth or promotion',
         'word_or_line_reversal_is_not_a_repair': True})
    baseline = gzread(HERE / 'baseline-answer.json.gz')
    repeated = service.consume(products, ROOT, include_artifacts=True)
    assert baseline == repeated
    gzsave('reconsumed-answer.json.gz', repeated)
    controls = []
    for name in ('altered-product', 'missing-parent'):
        bad = deepcopy(products)
        if name == 'altered-product':
            bad['P1']['payload']['graph']['units'][0]['raw'] += '!'
        else:
            bad['P2']['inputs']['P1'] = '0'*64
            bad['P2']['sha256'] = digest({k:v for k,v in bad['P2'].items() if k != 'sha256'})
        try:
            service.consume(bad, ROOT)
        except ValueError as error:
            controls.append({'case': name, 'refused': True, 'reason': str(error)})
        else:
            raise AssertionError('Tampered products accepted')
    save('actual-controls.json', controls)
    ledger = process_ledger.checked(HERE / 'native-ledger.json')
    assert len(ledger['reservations']) == 2
    result = {'status': 'PASS', 'literal_failures': 4, 'matching_box_reverse_tokens': len(paired),
        'full_answers_identical': True, 'controls_refused': len(controls),
        'planned_ordering_adapter_implemented': False,
        'reason': 'Reproduced loss originates before geometric projection; preserve and repair native intake separately',
        'native_reservations': 2, 'successful_native_text_calls': 1,
        'historical_visible_reservation_lower_bound': 64}
    save('comparison.json', result)
    return result


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'source', 'source-trusted', 'diagnose', 'construct', 'compare', 'compare-reviewed'}
    admission = check_bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, folder / 'method.py')
    tick = time.monotonic()
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_bidi_consumer', stage],
        'git_commit': admission['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(), 'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds': 'N/A deterministic', 'method_sha256': file_hash(Path(__file__))})
    def expire(signum, frame):
        raise TimeoutError('120-second stage bound')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        result = source(stage) if stage.startswith('source') else (compare() if stage == 'compare-reviewed' else globals()[stage]())
        check_bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 300 * 1024 * 1024
        outcome = {'status': 'PASS', 'details': result, 'wall_seconds': time.monotonic() - tick}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL',
             'error': type(error).__name__ + ': ' + str(error), 'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps(outcome, ensure_ascii=False))


if __name__ == '__main__':
    with (HERE / 'execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
