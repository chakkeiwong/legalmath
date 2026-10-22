"""Finite crop experiment and unaccepted review consumer for original table words."""
from copy import deepcopy
from datetime import datetime, timezone
import base64
import gzip
import json
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus.successor import process_ledger, sealed_runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/page-coverage'
PRIOR = BASE / 'attempt-004'
HERE = BASE / 'attempt-005'
PYTHON = '/home/chakwong/miniconda3/envs/tfgpu/bin/python'
WORKER = ROOT / 'scripts/prospectus_table_segment_worker.py'
PLAN = 'docs/plans/prospectus-table-segmentation-2026-10-15.md'


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
    admission = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in admission['binding'].items())
    if (HERE / 'methods.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'methods.json').items())
    return admission


def prepare():
    for p, h in read(PRIOR / 'outputs.json').items():
        assert file_hash(PRIOR / p) == h
    controls = read(PRIOR / 'image-controls.json')
    doc = read(PRIOR / 'request.json')['bundle']['documents'][0]
    spec = {'image_path': str(PRIOR / 'page-84-300dpi.png'), 'image_sha256': controls['image_sha256'],
        'source_path': str(ROOT / doc['path']), 'source_sha256': doc['sha256'],
        'tessdata': str(ROOT / doc['hybrid_profile']['tessdata']),
        'model_sha256': doc['hybrid_profile']['models']['eng'],
        'regions': [{'id': c['id'], 'bbox': c['bbox']} for c in controls['controls']]}
    save('worker-spec.json', spec)
    snapshot = HERE / 'snapshot'
    (snapshot / 'blobs').mkdir(parents=True, exist_ok=False)
    old = PRIOR / 'snapshot'
    manifest = deepcopy(sealed_runtime.validate(read(old / 'manifest.json')))
    for hashed in {r['sha256'] for r in manifest['files']}:
        assert file_hash(old / 'blobs' / hashed) == hashed
        shutil.copyfile(old / 'blobs' / hashed, snapshot / 'blobs' / hashed)
    added = {}
    for path in (WORKER, Path(spec['image_path'])):
        hashed = file_hash(path)
        assert str(path) not in {r['path'] for r in manifest['files']}
        shutil.copyfile(path, snapshot / 'blobs' / hashed)
        manifest['files'].append({'path': str(path), 'sha256': hashed, 'size': path.stat().st_size, 'mode': 0o444})
        manifest['directories'] = sorted(set(manifest['directories']) | {str(p) for p in path.parents if str(p) != '/'})
        added[str(path)] = hashed
    manifest['files'].sort(key=lambda r: r['path'])
    sealed_runtime.validate(manifest)
    save('snapshot/manifest.json', manifest)
    save('snapshot/provenance.json', {'parent': str(old.relative_to(ROOT)), 'parent_sha256': file_hash(old / 'manifest.json'), 'added': added})
    process_ledger.create(HERE / 'native-ledger.json', 2, 67,
        'One crop-inspection diagnostic uses the spare; one batch worker uses40 OCR operations. No further native starts allowed.')
    paths = [Path(__file__), WORKER, ROOT / 'scripts/prospectus_rotated_table_ocr.py'] + sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))
    methods = {str(p.relative_to(ROOT)): file_hash(p) for p in paths}
    save('methods.json', methods)
    for name in methods:
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    api = Path(PYTHON).parent.parent / 'lib/python3.11/site-packages/pymupdf/__init__.py'
    lines = api.read_text().splitlines()
    with (HERE / 'installed-api-excerpt.txt').open('x') as stream:
        stream.write('\n'.join(lines[13701:13750]) + '\n')
    save('pre-run-audit.json', {'status': 'PASS', 'plan': PLAN,
        'baseline': str(PRIOR.relative_to(ROOT)), 'api_file': str(api), 'api_sha256': file_hash(api),
        'pre_ocr_native_diagnostic': 'Use the permitted spare for original-crop generation and visual inspection; no retry remains after two starts.',
        'literals_excluded_from_ocr_spec': True, 'expected_ocr_operations': 40,
        'promote_only': 'No promotion;all20 samples must match before nomination for separate independent validation',
        'must_not_conclude': 'General accuracy,package limitation,complete cell structure or independent acceptance'})
    return {'regions': 20, 'arms': [1, 3], 'snapshot_files': len(manifest['files']), 'native_starts': 0}


def native(stage):
    if stage == 'worker':
        assert read(HERE / 'crop-image-review.json')['proceed'] is True
    manifest = read(HERE / 'snapshot/manifest.json')
    rt = sealed_source.SourceRuntime(HERE / 'snapshot', sealed_runtime.digest(manifest),
        evidence_directory=HERE / ('native-' + stage), native_text_max_stream=64 * 1024 * 1024)
    spec = read(HERE / 'worker-spec.json')
    spec['mode'] = 'crops' if stage == 'crops' else 'ocr'
    required = {str(p): file_hash(p) for p in (Path(PYTHON), WORKER, Path(spec['image_path']),
                Path(spec['source_path']), Path(spec['tessdata']) / 'eng.traineddata')}
    with process_ledger.observe(HERE / 'native-ledger.json'):
        result = rt.execute([PYTHON, str(WORKER)], json.dumps(spec).encode(), required, max_stream=64 * 1024 * 1024)
    output = json.loads(result['stdout'])
    if stage == 'crops':
        (HERE / 'crops').mkdir()
        for row in output['rows']:
            raw = base64.b64decode(row.pop('image_base64'), validate=True)
            name = 'crops/' + row['id'] + '-' + str(row['scale']) + '.png'
            with (HERE / name).open('xb') as stream:
                stream.write(raw)
            assert file_hash(HERE / name) == row['crop_sha256']
            row['crop_path'] = str((HERE / name).relative_to(ROOT))
        for index, data in enumerate(output.pop('contact_sheets')):
            with (HERE / ('contact-sheet-' + str(index) + '.png')).open('xb') as stream:
                stream.write(base64.b64decode(data, validate=True))
    save(stage + '-output.json', output)
    return {'rows': len(output['rows']), 'ocr_operations': output['ocr_operations'], 'native_reservations_this_stage': 1}


def source_anchors(graph, bbox):
    l, t, r, b = bbox
    return [anchor(u, w['start'], w['end']) for u in graph['units'] if u['page'] == 84
        for w in u.get('words', []) if w.get('bbox') and
        l <= (w['bbox'][0] + w['bbox'][2]) / 2 <= r and t <= (w['bbox'][1] + w['bbox'][3]) / 2 <= b]


def review_consumer(products, packet, *, expected_packet_sha256):
    if digest(packet) != expected_packet_sha256:
        raise ValueError('Pinned candidate packet changed')
    if packet['accepted'] is not False or packet['whole_table_complete'] is not False:
        raise ValueError('Candidate acceptance or completeness is unsupported')
    if packet['source_graph_sha256'] != digest(products['P1']['payload']['graph']):
        raise ValueError('Foreign source graph')
    spec = read(HERE / 'worker-spec.json')
    if (packet['image_sha256'] != spec['image_sha256'] or file_hash(Path(spec['image_path'])) != spec['image_sha256']
            or packet['model_sha256'] != spec['model_sha256']
            or file_hash(Path(spec['tessdata']) / 'eng.traineddata') != spec['model_sha256']):
        raise ValueError('Changed image or model')
    evidence = read(HERE / 'worker-output.json')
    expected = {(r['id'], r['scale']): r for r in evidence['rows']}
    crops = {(r['id'], r['scale']): r for r in read(HERE / 'crops-output.json')['rows']}
    if len(packet['rows']) != 40 or {(r['id'], r['scale']) for r in packet['rows']} != set(expected):
        raise ValueError('Missing or duplicate candidate region')
    for row in packet['rows']:
        key = row['id'], row['scale']
        crop_row = crops[key]
        if file_hash(ROOT / crop_row['crop_path']) != row['candidate']['crop_sha256']:
            raise ValueError('Changed candidate crop')
        if row['candidate'] != expected[key] or row['candidate']['transform'] != crop_row['transform']:
            raise ValueError('Candidate differs from raw worker or crop transform')
        if row['source_anchors'] != source_anchors(products['P1']['payload']['graph'], row['candidate']['bbox']):
            raise ValueError('Source-word context changed')
    return {'answer': service.consume(products, ROOT, include_artifacts=True),
            'candidate_review': packet, 'source_replaced': False, 'cell_acceptance': False}


def compare():
    before = read(PRIOR / 'literal-comparison.json')['controls']
    refs = {r['id']: r for r in before}
    raw = read(HERE / 'worker-output.json')
    crops = {(r['id'], r['scale']): r for r in read(HERE / 'crops-output.json')['rows']}
    assert len(raw['rows']) == 40 and raw['ocr_operations'] == 40
    assert {(r['id'], r['scale']) for r in raw['rows']} == set(crops)
    controls = []
    products = load(PRIOR / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    packet = {'version': 'unaccepted-table-crop-review.v1', 'source_graph_sha256': digest(graph),
        'image_sha256': raw['image_sha256'], 'model_sha256': raw['model_sha256'],
        'accepted': False, 'whole_table_complete': False, 'rows': []}
    for row in raw['rows']:
        key = row['id'], row['scale']
        assert all(row[k] == crops[key][k] for k in ('crop_sha256', 'bbox', 'transform'))
        assert len(row['raw_words']) == len(row['mapped_words'])
        assert [w[4] for w in row['raw_words']] == [w['text'] for w in row['mapped_words']]
        ref = refs[row['id']]
        ordered = sorted(row['raw_words'], key=lambda w: (w[0], w[1]))
        actual = ' '.join(w[4] for w in ordered)
        matched = not ordered if ref['literal'] is None else actual == ref['literal']
        controls.append({'id': row['id'], 'scale': row['scale'], 'expected': ref['literal'],
            'baseline_actual': ref['actual'], 'baseline_matched': ref['matched'], 'actual': actual,
            'matched': matched, 'regression': ref['matched'] and not matched,
            'crop_path': crops[key]['crop_path'], 'crop_sha256': row['crop_sha256']})
        packet['rows'].append({'id': row['id'], 'scale': row['scale'], 'candidate': row,
                              'source_anchors': source_anchors(graph, row['bbox'])})
    save('sample-comparison.json', controls)
    save('review-packet.json', packet)
    save('review-packet-pin.json', {'sha256': digest(packet)})
    consumer = review_consumer(products, packet, expected_packet_sha256=digest(packet))
    save('review-consumer.json.gz', consumer)
    baseline = load(PRIOR / 'hybrid-answer.json.gz')
    assert consumer['answer'] == baseline
    ledger = process_ledger.checked(HERE / 'native-ledger.json')
    assert len(ledger['reservations']) == 2
    for stage in ('crops', 'worker'):
        folder = HERE / ('native-' + stage) / '0'
        receipt = read(folder / 'receipt.json')
        sealed_runtime.verify_receipt(receipt, read(HERE / 'snapshot/manifest.json'), receipt['argv'],
            (folder / 'stdin').read_bytes(), (folder / 'stdout').read_bytes(), (folder / 'stderr').read_bytes())
    arms = []
    for scale in (1, 3):
        group = [c for c in controls if c['scale'] == scale]
        arms.append({'scale': scale, 'matches': sum(c['matched'] for c in group),
            'mismatch_ids': [c['id'] for c in group if not c['matched']],
            'regression_ids': [c['id'] for c in group if c['regression']],
            'blank_samples_preserved': sum(c['matched'] for c in group if c['expected'] is None),
            'all_sample_screen_passed': all(c['matched'] for c in group)})
    report = {'status': 'PASS', 'scope': 'FINITE_EXPOSED_CROP_PRESENTATION_DIAGNOSTIC',
        'baseline_matches': 5, 'samples_per_arm': 20, 'arms': arms, 'full_hybrid_answer_unchanged': True,
        'raw_worker_words_unchanged': True, 'crop_transforms_reproduced': 40,
        'native_reservations': 2, 'historical_visible_reservation_lower_bound': 69,
        'ocr_operations': 40, 'accepted_cells': 0, 'whole_table_complete': False,
        'package_limitation_proven': False, 'independent_accuracy_evaluated': False}
    save('comparison.json', report)
    return report


def controls():
    products = load(PRIOR / 'products.json.gz')
    original = read(HERE / 'review-packet.json')
    results = []
    for name in ('wrong-image', 'wrong-model', 'raw-text-repair', 'changed-transform', 'missing-region', 'promotion', 'wrong-source-context'):
        packet = deepcopy(original)
        if name == 'wrong-image': packet['image_sha256'] = '0' * 64
        elif name == 'wrong-model': packet['model_sha256'] = '0' * 64
        elif name == 'raw-text-repair': packet['rows'][0]['candidate']['raw_text'] += 'CORRECTED'
        elif name == 'changed-transform': packet['rows'][0]['candidate']['transform']['scale'] = 2
        elif name == 'missing-region': packet['rows'].pop()
        elif name == 'promotion': packet['accepted'] = True
        else: packet['rows'][0]['source_anchors'].append({'unit': 'foreign'})
        try:
            review_consumer(products, packet, expected_packet_sha256=digest(packet))
        except ValueError as error:
            results.append({'case': name, 'refused': True, 'repinned': True, 'reason': str(error)})
        else:
            raise AssertionError('Adverse review accepted: ' + name)
    save('actual-controls.json', results)
    return {'refused': len(results), 'full_consumer_passed_before_controls': True}


def main(stage):
    assert stage in {'prepare', 'crops', 'worker', 'compare', 'controls'}
    admission = bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_rotated_table_ocr', 'segment-' + stage],
        'environment': sys.executable, 'native_environment': PYTHON, 'git_commit': admission['git_commit'],
        'plan': PLAN, 'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic'})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second stage bound;no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        details = native(stage) if stage in {'crops', 'worker'} else globals()[stage]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 300 * 1024 * 1024
        outcome = {'status': 'PASS', 'stage': stage, 'details': details, 'evidence_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error), 'wall_seconds': time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)
    outcome['wall_seconds'] = time.monotonic()-tick
    save('invocations/' + stage + '/result.json', outcome)
    print(json.dumps(outcome))
