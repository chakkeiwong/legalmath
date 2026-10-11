"""Image identities must survive actual OCR producer and service correction routes."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor import corrections, service, source_graph
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

ROOT = Path(__file__).resolve().parents[2]
RAW = 'docs/implementation/prospectus-integration-closure/worker-recovery/ocr-baseline/attempt-001/raw-worker.json'
PDF = 'docs/implementation/prospectus-integration-closure/packages/scan/attempt-001/new-scan.pdf'
REVIEW = {'kind': 'DEVELOPMENT', 'reviewer': 'regression control',
          'reason': 'Preserve the required image identity for actual OCR-produced units'}


def actual_ocr_graph(fallback=False):
    data = json.loads((ROOT / RAW).read_text())
    assert data['source_sha256'] == digest((ROOT / PDF).read_bytes())
    if fallback:
        # Exercise the real adapter's no-word fallback using the same retained
        # page text and image, not a hand-invented extraction method label.
        data['pages'][0]['words'] = []
    doc = {'id': 'scan', 'sha256': data['source_sha256'], 'language': 'en', 'page_count': 2}
    units, count, _ = source_graph.retained_ocr_units(doc, ROOT, data=data)
    assert count == 2
    return {'units': units}


def packet(graph, unit, image):
    row = {'id': 'reviewed-line', 'source': anchor(unit), 'operations': [
        {'kind': 'copy', 'start': 0, 'end': len(unit['raw']), 'text': unit['raw'],
         'reason': 'The complete unchanged OCR occurrence remains the raw evidence'}]}
    if image != 'OMITTED':
        row['image_sha256'] = image
    return {'version': 'reviewed-corrections.v1', 'graph_sha256': digest(graph),
            'review': REVIEW, 'entries': [row]}


@pytest.mark.parametrize('fallback', [False, True], ids=['words', 'text-fallback'])
@pytest.mark.parametrize('case', ['matching', 'missing', 'wrong', 'missing-source',
                                 'empty-source', 'malformed-source', 'nonstring-source', 'unfamiliar-image-method'])
def test_correction_binds_actual_ocr_page_identity(fallback, case):
    graph = actual_ocr_graph(fallback)
    unit = next(u for u in graph['units'] if u['page'] == 1 and u['raw'])
    original = deepcopy(unit)
    expected_method = 'retained-original-text-or-blank' if fallback else 'retained-pymupdf-tesseract'
    assert unit['method'] == expected_method
    image = unit['image_sha256']
    if case == 'missing':
        image = 'OMITTED'
    elif case == 'wrong':
        image = '0' * 64
    elif case == 'missing-source':
        unit.pop('image_sha256')
    elif case == 'empty-source':
        unit['image_sha256'] = image = ''
    elif case == 'malformed-source':
        unit['image_sha256'] = image = 'z' * 64
    elif case == 'nonstring-source':
        unit['image_sha256'] = image = 123
    elif case == 'unfamiliar-image-method':
        unit['method'] = 'future-image-worker'
        image = '0' * 64
    supplied = packet(graph, unit, image)
    if case == 'matching':
        admitted = corrections.admit(graph, supplied)
        assert admitted['entries'][0]['image_sha256'] == image
        assert admitted['entries'][0]['text'] == original['raw']
        assert admitted['entries'][0]['bbox'] is None
        assert unit == original
    else:
        with pytest.raises(ValueError, match='retained source-page image identity'):
            corrections.admit(graph, supplied)


def test_correction_plain_text_without_image_remains_supported(tmp_path):
    path = tmp_path / 'source.txt'
    path.write_text('The N0tes are unsecured obligations of the Issuer.')
    bundle = {'instrument_id': 'plain-text', 'purpose': 'review',
              'issue_date': '2026-01-01T00:00:00Z', 'effective_at': '2026-01-01T00:00:00Z',
              'known_at': '2026-01-01T00:00:00Z', 'documents': [
                  {'id': 'text', 'path': 'source.txt', 'format': 'text',
                   'sha256': digest(path.read_bytes()), 'language': 'en',
                   'document_date': '2026-01-01T00:00:00Z', 'known_from': '2026-01-01T00:00:00Z'}]}
    graph = source_graph.build(bundle, tmp_path)
    unit = graph['units'][0]
    supplied = packet(graph, unit, 'OMITTED')
    supplied['entries'][0]['operations'][0].update(kind='replace', text=unit['raw'].replace('N0tes', 'Notes'))
    admitted = corrections.admit(graph, supplied)
    assert admitted['entries'][0]['text'] == 'The Notes are unsecured obligations of the Issuer.'
    assert admitted['entries'][0]['image_sha256'] is None


@pytest.mark.parametrize('image_case', ['matching', 'missing', 'wrong'])
def test_corrected_real_ocr_service_keeps_required_image_binding(tmp_path, image_case):
    data = json.loads((ROOT / RAW).read_text())
    (tmp_path / 'source.pdf').write_bytes((ROOT / PDF).read_bytes())
    (tmp_path / 'ocr.json').write_text(json.dumps(data))
    req = {'version': 'prospectus-successor.v3', 'bundle': {
        'instrument_id': 'actual-worker-correction-control', 'purpose': 'review',
        'issue_date': '2026-01-01T00:00:00Z', 'effective_at': '2026-01-01T00:00:00Z',
        'known_at': '2026-01-01T00:00:00Z', 'documents': [
            {'id': 'scan', 'path': 'source.pdf', 'sha256': data['source_sha256'], 'language': 'en',
             'authority': 'Protected synthetic scan; no legal acceptance', 'page_count': 2,
             'document_date': '2026-01-01T00:00:00Z', 'known_from': '2026-01-01T00:00:00Z',
             'ocr': {'path': 'ocr.json', 'sha256': digest((tmp_path / 'ocr.json').read_bytes())}}]}}
    graph = source_graph.build(req['bundle'], tmp_path)
    unit = next(u for u in graph['units'] if u['page'] == 1 and u['raw'])
    supplied = unit['image_sha256'] if image_case == 'matching' else 'OMITTED' if image_case == 'missing' else '0' * 64
    req['correction_admission'] = packet(graph, unit, supplied)
    if image_case != 'matching':
        with pytest.raises(ValueError, match='retained source-page image identity'):
            service.assess(req, tmp_path)
    else:
        report = service.assess(req, tmp_path)
        assert report['source_map']['units'] == graph['units']
        corrected = report['source_map']['corrections']['entries'][0]
        assert corrected['image_sha256'] == unit['image_sha256']
        assert corrected['bbox'] is None
        assert report['mode'] == 'ASSISTED'
        assert sorted(report['questions']) == ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6']
        assert report['questions']['Q3']['status'] == 'PARTIAL'
