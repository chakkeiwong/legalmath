"""Native absence is explained without asserting blankness or losing OCR evidence."""
from copy import deepcopy

import pytest

from scripts.prospectus_closure_fixtures import request, PREFIX
from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.contracts import TextUnit, digest


def unit(document='scan', page=1, text='', method='blank-or-unread', visible=True):
    result = TextUnit(f'{document}:p{page}:{method}', document, 'a' * 64, page, 0,
        text, None, f'{document}:p{page}', 'en', method).json()
    return {**result, 'visible': visible}


def test_native_absence_binds_each_page_without_claiming_blankness():
    graph = {'units': [unit(page=2, visible=False), unit(page=1)]}
    before = deepcopy(graph)
    rows = source_graph.native_text_gaps(graph)
    assert [(r['page'], r['visible']) for r in rows] == [(2, False), (1, True)]
    assert all(r['source_sha256'] == 'a' * 64 and not r['additional_text_methods'] for r in rows)
    assert all(r['status'] == 'NO_NATIVE_TEXT_REQUIRES_IMAGE_REVIEW' for r in rows)
    assert 'does not distinguish' in rows[0]['qualification']
    assert graph == before


def test_additional_text_is_bound_to_same_source_page():
    graph = {'units': [unit(), unit(text='OCR text', method='retained-pymupdf-tesseract'),
        unit(document='other', text='Other page', method='unrelated-method'),
        unit(page=2, text='Next page', method='another-method')]}
    assert source_graph.native_text_gaps(graph)[0]['additional_text_methods'] == ['retained-pymupdf-tesseract']
    assert source_graph.native_text_gaps({'units': [unit(text='Native text', method='pdftotext-bbox-layout')]}) == []


@pytest.mark.parametrize('excluded', [False, True])
def test_final_consumer_keeps_inventory_explanation_and_legal_questions(tmp_path, monkeypatch, excluded):
    req = request(tmp_path, [PREFIX])
    original = service.assess(req, tmp_path)
    path = tmp_path / 'scan.pdf'
    path.write_bytes(b'%PDF-SYNTHETIC TEST; extractor deliberately stubbed')
    doc = {'id': 'scan', 'path': path.name, 'sha256': digest(path.read_bytes()), 'format': 'pdf',
        'page_count': 1, 'language': 'en', 'authority': 'Synthetic extraction control'}
    req['bundle']['documents'].append(doc)
    extracted = unit()
    extracted['source_sha256'] = doc['sha256']
    monkeypatch.setattr(source_graph, 'pdf_units', lambda path, document:
        ([deepcopy(extracted)], 1, {'extractor': 'stubbed-native-test'}))
    if excluded:
        req['assembly']['operations'].append({'unit': extracted['id'], 'source_text_sha256': extracted['text_sha256'],
            'role': 'EXCLUDED', 'reason': 'Explicit diagnostic exclusion', 'questions': []})
    answer = service.assess(req, tmp_path)
    gap = answer['native_text_gaps']['pages'][0]
    assert gap['unit'] == extracted['id'] and gap['source_sha256'] == doc['sha256']
    assert gap['additional_text_methods'] == []
    if excluded:
        assert answer['questions'] == original['questions']
    else:
        assert answer['questions']['Q1']['status'] == 'UNKNOWN'
        assert answer['questions']['Q3']['status'] == 'PARTIAL'
    assert 'native_text_gaps' not in original
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']
