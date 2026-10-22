"""Bounded actual hybrid OCR on the retained rotated Hypo cohort tables."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
PYTHON = '/home/chakwong/miniconda3/envs/tfgpu/bin/python'
os.environ['LEGALMATH_OCR_PYTHON'] = PYTHON
from legalmath.prospectus.execution_authority import file_hash, read, write
from legalmath.prospectus.successor import process_ledger, sealed_runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.region_coverage import consume_with_region_coverage

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'page-coverage/attempt-004'
PRIOR = BASE / 'page-coverage/attempt-003'
SNAPSHOT = BASE / 'native-binding/attempt-008/snapshot'
PLAN = 'docs/plans/prospectus-rotated-table-ocr-2026-10-15.md'
RENDER = '\n'.join([
    'import os', "os.environ['CUDA_VISIBLE_DEVICES'] = '-1'",
    'import json, sys, fitz', 'spec = json.load(sys.stdin)',
    'with fitz.open(spec["source"]) as document:',
    '    assert len(document) == 278 and document[83].rotation == 90',
    '    pix = document[83].get_pixmap(dpi=300, colorspace=fitz.csRGB)',
    '    assert (pix.width, pix.height) == (3300, 2550)',
    '    sys.stdout.buffer.write(pix.tobytes("png"))', ''])


def load(path):
    return json.loads(gzip.decompress(Path(path).read_bytes())) if str(path).endswith('.gz') else read(path)


def save(name, value):
    path = HERE / name
    if name.endswith('.gz'):
        with path.open('xb') as stream:
            stream.write(gzip.compress(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), mtime=0))
    else:
        write(path, value, exclusive=True)


def methods():
    paths = sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))
    paths.append(ROOT / 'src/legalmath/prospectus/region_coverage.py')
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def bindings():
    assert not (HERE / 'outputs.json').exists(), 'Sealed attempt'
    admission = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items()), 'Admitted input changed'
    if (HERE / 'consumer-methods.json').exists():
        assert methods() == read(HERE / 'consumer-methods.json'), 'Consumer method changed'
    return admission


def prepare():
    for name, hashed in read(PRIOR / 'outputs.json').items():
        assert file_hash(PRIOR / name) == hashed
    products = load(PRIOR / 'hypo-products.json.gz')
    request = deepcopy(products['P1']['payload']['request'])
    document = request['bundle']['documents'][0]
    assert document['sha256'] == '3d0b4bb3ba56014512e34779bb91bb891c037bbb02345a0db5de7e30f5bc3341'
    document['hybrid_profile'] = {
        'version': 'pymupdf-hybrid.v2', 'geometry_policy': 'preserve-text-without-invalid-box.v1',
        'dpi': 300, 'language': 'eng', 'max_pages': 1, 'page_count': 278, 'pages': [84],
        'tessdata': 'docs/prospectus/closure-2026-10-05/tools',
        'models': {'eng': '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'}}
    save('request.json', request)
    helper = HERE / 'render_worker.py'
    with helper.open('x') as stream:
        stream.write(RENDER)
    manifest = deepcopy(sealed_runtime.validate(read(SNAPSHOT / 'manifest.json')))
    folder = HERE / 'snapshot'
    (folder / 'blobs').mkdir(parents=True, exist_ok=False)
    for hashed in {r['sha256'] for r in manifest['files']}:
        assert file_hash(SNAPSHOT / 'blobs' / hashed) == hashed
        shutil.copyfile(SNAPSHOT / 'blobs' / hashed, folder / 'blobs' / hashed)
    additions = {}
    for path in ((ROOT / document['path']).resolve(), helper.resolve()):
        hashed = file_hash(path)
        assert str(path) not in {r['path'] for r in manifest['files']}
        if not (folder / 'blobs' / hashed).exists():
            shutil.copyfile(path, folder / 'blobs' / hashed)
        manifest['files'].append({'path': str(path), 'sha256': hashed, 'size': path.stat().st_size, 'mode': 0o444})
        manifest['directories'] = sorted(set(manifest['directories']) | {str(p) for p in path.parents if str(p) != '/'})
        additions[str(path)] = hashed
    manifest['files'].sort(key=lambda r: r['path'])
    sealed_runtime.validate(manifest)
    save('snapshot/manifest.json', manifest)
    save('snapshot/provenance.json', {'parent': str(SNAPSHOT.relative_to(ROOT)),
        'parent_manifest_sha256': file_hash(SNAPSHOT / 'manifest.json'), 'added': additions, 'copied_blobs_verified': True})
    process_ledger.create(HERE / 'native-ledger.json', 4, 64,
        'Three planned: render, native source, selected page OCR. One documented trusted retry or diagnostic spare.')
    save('consumer-methods.json', methods())
    for name in methods():
        target = HERE / 'consumer-methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    save('resume-audit.json', {'status': 'PASS', 'baseline': str(PRIOR.relative_to(ROOT)),
        'primary_question': 'Does actual selected-page hybrid OCR retain usable source-bound content in the four missing tables?',
        'promotion_vetoes': ['Wrong or missing cells', 'Invalid geometry', 'Unproven complete table structure'],
        'continuation_vetoes': ['Corrupt source or raster identity', 'Missing native streams', 'Exceeded budget', 'Second implementation failure'],
        'explanatory_only': ['Word counts', 'Exposed sample matches'],
        'default_provenance': 'Existing unchanged 300dpi English hybrid.v2 product route; baseline, not a tuned optimum',
        'early_check': 'Freeze image readings before OCR; verify original rotation and exact worker raster hash',
        'not_concluded': 'Whole-table accuracy, independent reading, package limitation, legal completeness or portability',
        'trusted_runtime_basis': 'native-layout-cases/attempt-003 retained sandbox namespace failure and successful trusted retry'})
    return {'snapshot_files': len(manifest['files']), 'native_reservations': 0}


def runtime(stage):
    manifest = read(HERE / 'snapshot/manifest.json')
    return sealed_source.SourceRuntime(HERE / 'snapshot', sealed_runtime.digest(manifest),
        evidence_directory=HERE / ('native-' + stage), native_text_max_stream=64 * 1024 * 1024)


def render():
    rt = runtime('render')
    source = (ROOT / read(HERE / 'request.json')['bundle']['documents'][0]['path']).resolve()
    helper = (HERE / 'render_worker.py').resolve()
    with process_ledger.observe(HERE / 'native-ledger.json'):
        result = rt.execute([PYTHON, str(helper)], json.dumps({'source': str(source)}).encode(),
            {str(path): file_hash(path) for path in (Path(PYTHON), helper, source)}, max_stream=64 * 1024 * 1024)
    with (HERE / 'page-84-300dpi.png').open('xb') as stream:
        stream.write(result['stdout'])
    report = {'page': 84, 'original_rotation': 90, 'dpi': 300, 'pixels': [3300, 2550],
        'display_rect': [0, 0, 792, 612], 'image_sha256': file_hash(HERE / 'page-84-300dpi.png'),
        'native_receipt_sha256': file_hash(HERE / 'native-render/0/receipt.json')}
    save('render.json', report)
    return report


def source():
    controls = read(HERE / 'image-controls.json')
    assert controls['image_sha256'] == read(HERE / 'render.json')['image_sha256']
    assert controls['frozen_before_ocr'] is True and controls['independent'] is False
    assert controls['controls']
    save('image-control-pin.json', {'sha256': file_hash(HERE / 'image-controls.json')})
    rt = runtime('source')
    with process_ledger.observe(HERE / 'native-ledger.json'):
        product = sealed_source.source_product(read(HERE / 'request.json'), ROOT, rt)
    save('source-product.json.gz', product)
    save('native-receipts.json', rt.receipts)
    assert len(rt.receipts) == 2
    ocr = read(HERE / 'native-source/1/stdout')
    assert ocr['selected_pages'] == [84] and len(ocr['pages']) == 1
    assert ocr['pages'][0]['image_sha256'] == controls['image_sha256'], 'Worker raster differs'
    assert file_hash(HERE / 'image-controls.json') == read(HERE / 'image-control-pin.json')['sha256']
    return {'units': product['payload']['graph']['unit_count'], 'ocr_words': len(ocr['pages'][0]['words']),
            'raster_identical': True, 'native_reservations_this_stage': 2}


def construct():
    p1 = load(HERE / 'source-product.json.gz')
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
                'P5': service.financial_product(p1, p2, p3)}
    save('products.json.gz', products)
    answer = service.consume(products, ROOT, include_artifacts=True)
    save('hybrid-answer.json.gz', answer)
    inv = deepcopy(read(PRIOR / 'hypo-inventory.json'))
    inv['source_graph_sha256'] = digest(p1['payload']['graph'])
    inv['pages'][0]['render_path'] = str((HERE / 'page-84-300dpi.png').relative_to(ROOT))
    inv['pages'][0]['render_sha256'] = read(HERE / 'render.json')['image_sha256']
    save('hybrid-inventory.json', inv)
    result = consume_with_region_coverage(products, inv, ROOT, expected_inventory_sha256=digest(inv))
    save('region-consumer.json.gz', result)
    save('region-coverage.json', result['region_coverage'])
    assert result['answer'] == answer
    return {'questions': {q: r['status'] for q, r in answer['questions'].items()},
        'regions': [{'id': r['id'], 'status': r['status'], 'retained_words': len(r['retained_word_anchors']),
                     'partial_words': len(r['partial_word_anchors'])} for r in result['region_coverage']['regions']]}


def diagnose():
    assert file_hash(HERE / 'image-controls.json') == read(HERE / 'image-control-pin.json')['sha256']
    controls = read(HERE / 'image-controls.json')
    graph = load(HERE / 'source-product.json.gz')['payload']['graph']
    units = [u for u in graph['units'] if u['page'] == 84 and u['method'] == 'retained-pymupdf-tesseract']
    words = [{'unit': u['id'], **w} for u in units for w in u['words']]
    save('page-84-ocr-units.json.gz', units)
    checks = []
    for control in controls['controls']:
        l, t, r, b = control['bbox']
        selected = []
        for word in words:
            box = word.get('bbox')
            if box is not None and l <= (box[0] + box[2]) / 2 <= r and t <= (box[1] + box[3]) / 2 <= b:
                selected.append(word)
        selected.sort(key=lambda w: (w['bbox'][0], w['bbox'][1]))
        actual = ' '.join(w['text'] for w in selected)
        matched = not selected if control['literal'] is None else actual == control['literal']
        checks.append({**control, 'actual': actual, 'matched': matched, 'word_evidence': selected,
            'status': 'EXPOSED_SAMPLE_MATCH' if matched else 'EXPOSED_SAMPLE_MISMATCH'})
    save('literal-comparison.json', {'image_sha256': controls['image_sha256'],
        'frozen_controls_sha256': read(HERE / 'image-control-pin.json')['sha256'], 'controls': checks,
        'accuracy_estimate': False, 'whole_table_coverage': False, 'independent': False})
    rows = read(HERE / 'region-coverage.json')['regions']
    by_id = {u['id']: u for u in graph['units']}
    evidence = []
    for row in rows:
        partial = []
        for anchored in row['partial_word_anchors']:
            # Retain anchor and complete occurrence without projecting a cropped word.
            unit_id = anchored.get('unit') or anchored.get('unit_id')
            partial.append({'anchor': anchored, 'unit': by_id.get(unit_id)})
        evidence.append({'id': row['id'], 'bbox': row['bbox'], 'status': row['status'],
            'partial_intersections': partial, 'unknown_geometry_units': row['unknown_geometry_units']})
    save('region-boundary-diagnosis.json', evidence)
    return {'ocr_words': len(words), 'sample_matches': sum(c['matched'] for c in checks),
        'sample_mismatches': [{'id': c['id'], 'expected': c['literal'], 'actual': c['actual']}
                              for c in checks if not c['matched']],
        'blank_samples_preserved': sum(c['matched'] for c in checks if c['literal'] is None),
        'invalid_word_boxes': sum(w.get('bbox') is None for w in words)}


def differences(before, after, path='$'):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict):
        out = []
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                out.append({'path': path + '.' + key, 'before_present': key in before, 'after_present': key in after,
                            'before': before.get(key), 'after': after.get(key)})
            else:
                out.extend(differences(before[key], after[key], path + '.' + key))
        return out
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [row for i, (a, b) in enumerate(zip(before, after)) for row in differences(a, b, path + '[' + str(i) + ']')]
    return [{'path': path, 'before': before, 'after': after}]


def without_unresolved(value):
    if isinstance(value, dict):
        return {k: without_unresolved(v) for k, v in value.items() if k != 'unresolved'}
    if isinstance(value, list):
        return [without_unresolved(v) for v in value]
    return value


def compare():
    old = load(PRIOR / 'hypo-products.json.gz')
    products = load(HERE / 'products.json.gz')
    baseline = load(PRIOR / 'hypo-baseline-answer.json.gz')
    repeated = service.consume(old, ROOT, include_artifacts=True)
    save('baseline-reconsumed.json.gz', repeated)
    assert baseline == repeated, 'Baseline no longer reproduces'
    after = load(HERE / 'hybrid-answer.json.gz')
    before_units = old['P1']['payload']['graph']['units']
    all_units = products['P1']['payload']['graph']['units']
    native = [u for u in all_units if u['method'] != 'retained-pymupdf-tesseract']
    assert native == before_units, 'Native units changed'
    assert [u for u in all_units if u['page'] != 84] == [u for u in before_units if u['page'] != 84]
    assert all(u['page'] == 84 for u in all_units if u['method'] == 'retained-pymupdf-tesseract')
    diffs = differences(baseline, after)
    save('complete-answer-differences.json.gz', diffs)
    question_comparison = {q: {'before': baseline['questions'][q]['status'], 'after': answer['status'],
        'equal': baseline['questions'][q] == answer,
        'equal_except_unresolved': without_unresolved(baseline['questions'][q]) == without_unresolved(answer),
        'differences': differences(baseline['questions'][q], answer)} for q, answer in after['questions'].items()}
    save('question-comparison.json.gz', question_comparison)
    controls = []
    for name in ('altered-product', 'wrong-parent'):
        bad = deepcopy(products)
        if name == 'altered-product':
            bad['P1']['payload']['graph']['units'][-1]['raw'] += '!'
        else:
            bad['P2']['inputs']['P1'] = '0' * 64
            bad['P2']['sha256'] = digest({k: v for k, v in bad['P2'].items() if k != 'sha256'})
        try:
            service.consume(bad, ROOT)
        except ValueError as error:
            controls.append({'case': name, 'refused': True, 'reason': str(error)})
        else:
            raise AssertionError('Altered product accepted')
    save('actual-controls.json', controls)
    coverage = read(HERE / 'region-coverage.json')
    assert len(coverage['regions']) == 4
    assert not any(coverage[k] for k in ('may_claim_coverage', 'page_complete', 'document_complete', 'independent_legal_acceptance'))
    assert all(r['retained_word_anchors'] for r in coverage['regions'])
    assert all(a['status'] in {'UNKNOWN', 'PARTIAL', 'UNSUPPORTED'} for a in after['questions'].values())
    literals = read(HERE / 'literal-comparison.json')['controls']
    ledger = process_ledger.checked(HERE / 'native-ledger.json')
    assert len(ledger['reservations']) == 3
    for stage, count in (('render', 1), ('source', 2)):
        manifest = read(HERE / 'snapshot/manifest.json')
        for i in range(count):
            folder = HERE / ('native-' + stage) / str(i)
            receipt = read(folder / 'receipt.json')
            sealed_runtime.verify_receipt(receipt, manifest, receipt['argv'], (folder / 'stdin').read_bytes(),
                (folder / 'stdout').read_bytes(), (folder / 'stderr').read_bytes())
    report = {'status': 'PASS', 'scope': 'FINITE_ACTUAL_HYBRID_OCR_DIAGNOSTIC',
        'native_units_unchanged': len(native), 'unselected_pages_unchanged': 277,
        'ocr_units_added': len(all_units) - len(native), 'ocr_words_added': 1033,
        'regions_with_retained_words': 4, 'regions_with_boundary_intersections': sum(bool(r['partial_word_anchors']) for r in coverage['regions']),
        'sample_controls': len(literals), 'sample_matches': sum(c['matched'] for c in literals),
        'sample_mismatches': [c['id'] for c in literals if not c['matched']],
        'blank_samples_preserved': sum(c['matched'] for c in literals if c['literal'] is None),
        'baseline_full_answer_reproduced': True, 'full_answer_changed': baseline != after,
        'question_statuses_unchanged': all(r['before'] == r['after'] for r in question_comparison.values()),
        'questions_equal_except_unresolved': [q for q, r in question_comparison.items() if r['equal_except_unresolved']],
        'complete_answer_difference_count': len(diffs), 'actual_controls_refused': len(controls),
        'native_reservations': 3, 'historical_visible_reservation_lower_bound': 67,
        'page_complete': False, 'independent_acceptance': False, 'fundamental_package_limitation_proven': False}
    save('comparison.json', report)
    return report


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'render', 'source', 'construct', 'diagnose', 'compare'}
    admission = bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, folder / 'method.py')
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_rotated_table_ocr', stage],
        'git_commit': admission['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'native_environment': PYTHON, 'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1',
        'random_seeds': 'N/A deterministic', 'started_at': datetime.now(timezone.utc).isoformat(),
        'method_sha256': file_hash(Path(__file__))})
    def expire(signum, frame):
        raise TimeoutError('120-second stage bound; no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    tick = time.monotonic()
    try:
        details = globals()[stage]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 350 * 1024 * 1024, 'Evidence bound exceeded'
        outcome = {'status': 'PASS', 'stage': stage, 'details': details, 'evidence_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
            'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    outcome['wall_seconds'] = time.monotonic() - tick
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps(outcome))


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1].startswith('segment-'):
        from scripts.prospectus_table_segments import main as segment_main
        segment_main(sys.argv[1][len('segment-'):])
    else:
        main()
