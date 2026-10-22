"""Retained receipt-byte checks at actual downstream product boundaries."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.contracts import digest

TIME = '2026-01-01T00:00:00Z'


def inputs(root, optional=True, hidden=False):
    source = root / 'source.txt'; source.write_text('The Notes pay interest.')
    receipt = root / 'receipt.json'; receipt.write_text('{"source":"SYNTHETIC"}')
    document = {'id': 'd', 'path': 'source.txt', 'sha256': digest(source.read_bytes()),
        'format': 'text', 'language': 'en', 'authority': 'Synthetic validation control',
        'document_date': TIME, 'known_from': '2027-01-01T00:00:00Z' if hidden else TIME}
    if optional: document['acquisition'] = {'path': 'receipt.json', 'sha256': digest(receipt.read_bytes())}
    request = {'version': 'prospectus-successor.v3', 'bundle': {'instrument_id': 'synthetic-receipt-integrity',
        'purpose': 'review', 'issue_date': TIME, 'effective_at': TIME, 'known_at': TIME,
        'documents': [document], 'dependencies': []}}
    return request, receipt


def products(request, root):
    p1 = service.source_product(request, root); p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
            'P5': service.financial_product(p1, p2, p3)}


def boundary(which, request, values, root):
    if which == 'intake': return service.source_product(request, root)
    if which == 'construction': return service.construction_product(values['P1'], root)
    return service.consume(values, root, mode=which)


@pytest.mark.parametrize('which', ['intake', 'construction', 'frozen', 'current'])
@pytest.mark.parametrize('change', ['changed', 'missing'])
@pytest.mark.parametrize('hidden', [False, True])
def test_receipt_drift_refused_and_restoration_exact(tmp_path, which, change, hidden):
    request, receipt = inputs(tmp_path, hidden=hidden); values = products(request, tmp_path)
    expected = boundary(which, request, values, tmp_path); before = deepcopy(values); raw = receipt.read_bytes()
    if change == 'changed': receipt.write_text('Changed synthetic receipt')
    else: receipt.unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        boundary(which, request, values, tmp_path)
    receipt.write_bytes(raw)
    assert boundary(which, request, values, tmp_path) == expected
    assert values == before


@pytest.mark.parametrize('which', ['intake', 'construction', 'frozen', 'current'])
def test_absent_optional_receipt_preserves_full_answer(tmp_path, which):
    request, receipt = inputs(tmp_path, optional=False); values = products(request, tmp_path)
    expected = boundary(which, request, values, tmp_path); receipt.unlink()
    assert boundary(which, request, values, tmp_path) == expected
    assert values['P1']['payload']['graph']['documents'][0]['acquisition_status'] == 'NOT_SUPPLIED'


@pytest.mark.parametrize('which', ['intake', 'construction', 'frozen', 'current'])
def test_changed_document_still_refused(tmp_path, which):
    request, _ = inputs(tmp_path); values = products(request, tmp_path)
    (tmp_path / 'source.txt').write_text('Changed source')
    with pytest.raises(ValueError, match='[Ss]ource bytes changed'):
        boundary(which, request, values, tmp_path)


def test_construction_rejects_receipt_before_assembly(tmp_path, monkeypatch):
    request, receipt = inputs(tmp_path); values = products(request, tmp_path)
    receipt.write_text('Changed receipt')
    def forbidden(*args, **kwargs): pytest.fail('Assembly ran before receipt verification')
    monkeypatch.setattr(service.contract_assembly, 'assemble', forbidden)
    with pytest.raises(ValueError, match='Acquisition receipt changed'):
        service.construction_product(values['P1'], tmp_path)


def test_frozen_rejects_receipt_without_new_extraction(tmp_path, monkeypatch):
    request, receipt = inputs(tmp_path); values = products(request, tmp_path)
    def forbidden(*args, **kwargs): pytest.fail('Frozen path rebuilt source extraction')
    monkeypatch.setattr(service, 'source_product', forbidden)
    expected = service.consume(values, tmp_path)
    receipt.write_text('Changed receipt')
    with pytest.raises(ValueError, match='Acquisition receipt changed'):
        service.consume(values, tmp_path)
    assert expected['may_execute_transaction'] is False


def test_receipt_symlink_cannot_escape_root(tmp_path):
    request, receipt = inputs(tmp_path); values = products(request, tmp_path)
    outside = tmp_path.parent / (tmp_path.name + '-outside'); outside.write_bytes(receipt.read_bytes())
    receipt.unlink(); receipt.symlink_to(outside)
    with pytest.raises(ValueError, match='escapes declared root'):
        service.consume(values, tmp_path)
