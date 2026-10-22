"""Original BES scan occurrences and full qualifications reach the real service."""
import importlib.util
import json
from pathlib import Path
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import service, source_graph, extraction
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'docs/implementation/prospectus-integration-closure/real-scan'


def source_reading(**controls):
    # Use the reviewed packet authoring route to rebind each current parent;
    # the assertions below come from the independently retained printed oracle.
    spec = importlib.util.spec_from_file_location('bes_consumer', PACKAGE / 'consumer.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    review = module.load_review()
    return review, service.assess(module.request(review, **controls), ROOT)


def test_real_scan_corrections_keep_raw_identifiers_and_full_qualifications():
    review, report = source_reading()
    original = json.loads((PACKAGE / 'baseline/attempt-001/service-report.json').read_text())
    assert report['source_map']['units'] == original['source_map']['units']
    assert {q: r['status'] for q, r in report['questions'].items()} == {
        'Q1': 'UNKNOWN', 'Q2': 'UNKNOWN', 'Q3': 'PARTIAL',
        'Q4': 'UNKNOWN', 'Q5': 'UNSUPPORTED', 'Q6': 'UNKNOWN'}
    corrections = report['source_map']['corrections']['entries']
    isin = next(row for row in corrections if row['id'] == 'isin-segment-0')
    assert isin['source']['quote'] == 'PTBEQBOMO0010'
    assert isin['text'] == 'PTBEQBOM0010'
    assert all(row['bbox'] is None and len(row['image_sha256']) == 64 for row in corrections)
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert len(nodes) == 23
    for identity in ('eligibility-qualification', 'ratings-qualification'):
        target = next(t for t in review['targets'] if t['id'] == identity)
        assert nodes['bes:' + identity]['quote'] == ' '.join(s['source']['quote'] for s in target['segments'])
    assert nodes['bes:intended-value']['quote'] == 'Yes'
    assert len([d for d in report['dependencies'] if d['id'].startswith('governing:bes-') and d['status'] == 'RESOLVED']) == 16
    assert report['mode'] == 'ASSISTED' and not report['independent_legal_acceptance']


def test_real_scan_layout_requires_whole_qualification_even_when_yes_survives():
    _, report = source_reading(exclude_target='eligibility-qualification')
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert nodes['bes:intended-value']['quote'] == 'Yes'
    assert 'bes:eligibility-qualification' not in nodes
    dependencies = {d['id']: d for d in report['dependencies']}
    for question in ('Q1', 'Q2'):
        identity = 'governing:bes-eligibility-qualified:' + question
        assert dependencies[identity]['status'] == 'UNRESOLVED'
        assert identity in report['questions'][question]['unresolved']
        assert report['questions'][question]['status'] == 'UNKNOWN'


def hybrid_correction_fixture(tmp_path, monkeypatch):
    """A long PDF with native headers and separately reviewed image-page text."""
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for page_number in range(1, 24):
        page = writer.add_blank_page(width=612, height=792)
        font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 10 Tf 40 720 Td (Native header {page_number}) Tj ET'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    with (tmp_path/'source.pdf').open('wb') as stream:
        writer.write(stream)
    (tmp_path/'models').mkdir()
    (tmp_path/'models/eng.traineddata').write_bytes(b'pinned-synthetic-model')
    model_hash = digest(b'pinned-synthetic-model')
    original_hash = digest((tmp_path/'source.pdf').read_bytes())
    profile = {'version':'pymupdf-hybrid.v1','dpi':300,'language':'eng',
        'max_pages':2,'page_count':23,'pages':[22,23],'tessdata':'models',
        'models':{'eng':model_hash}}
    document = {'id':'hybrid','path':'source.pdf','sha256':original_hash,'language':'en',
        'authority':'Synthetic mixed-page source; no legal acceptance',
        'page_count':23,'hybrid_profile':profile,'document_date':'2026-01-01T00:00:00Z',
        'known_from':'2026-01-01T00:00:00Z'}
    data = {'version':'hybrid-ocr.v1','source_sha256':original_hash,'page_count':23,
        'selected_pages':[22,23],
        'pages':[{'page':p,'image_sha256':digest(str(p).encode()),
            'image_width':2550,'image_height':3300,'width_points':612,'height_points':792,
            'text':f'Reviewed audit body {p}',
            'words':[[20,20,200,40,f'Reviewed audit body {p}',0,0,0]]} for p in (22,23)],
        'runtime':{'dpi':300,'language':'eng','language_models':{'eng':model_hash}}}
    def save_data():
        (tmp_path/'ocr.json').write_text(json.dumps(data))
        document['hybrid_ocr']={'path':'ocr.json','sha256':digest((tmp_path/'ocr.json').read_bytes())}
    def image_check(doc, root, retained):
        if doc['sha256'] != original_hash or retained['pages'][0]['image_sha256'] != digest(b'22'):
            raise ValueError('Retained hybrid page images differ from the bound original')
        return {'verified_image_pages':[22,23], 'verification_mode':'CONTROL_IMAGE_HOOK'}
    monkeypatch.setattr(extraction,'verify_hybrid_images',image_check)
    save_data()
    bundle = {'instrument_id':'synthetic-hybrid','purpose':'review',
        'issue_date':'2026-01-01T00:00:00Z','effective_at':'2026-01-01T00:00:00Z',
        'known_at':'2026-10-11T00:00:00Z','documents':[document]}
    return bundle, data, save_data


def test_real_scan_hybrid_correction_preserves_native_and_original_pages(tmp_path, monkeypatch):
    bundle, data, _ = hybrid_correction_fixture(tmp_path, monkeypatch)
    native_bundle = deepcopy(bundle)
    native_bundle['documents'][0].pop('hybrid_profile')
    native_bundle['documents'][0].pop('hybrid_ocr')
    baseline = source_graph.build(native_bundle, tmp_path)
    graph = service.source_product({'version':'prospectus-successor.v3','bundle':bundle},tmp_path)['payload']['graph']
    native = [u for u in graph['units'] if u['method']=='pdftotext-bbox-layout']
    selected = [u for u in graph['units'] if u['method']=='retained-pymupdf-tesseract']
    assert native == baseline['units']
    assert len(native)==23 and [u['page'] for u in selected]==[22,23]
    assert all('Native header' in u['raw'] for u in native)
    assert all(u['image_sha256']==data['pages'][i]['image_sha256'] for i,u in enumerate(selected))
    assert graph['documents'][0]['page_coverage'][21]['status']=='NATIVE_AND_OCR_REQUIRES_REVIEW'
    assert graph['documents'][0]['image_verification']['verified_image_pages']==[22,23]
    assert 'hybrid text coverage' in graph['unresolved'][-1]['reason']


@pytest.mark.parametrize('mutation',['source','count','page','model','image','selection'])
def test_real_scan_hybrid_correction_rejects_wrong_identity(tmp_path,monkeypatch,mutation):
    bundle,data,save=hybrid_correction_fixture(tmp_path,monkeypatch)
    doc=bundle['documents'][0]
    if mutation=='source':data['source_sha256']='0'*64
    elif mutation=='count':data['page_count']=24
    elif mutation=='page':data['pages'][1]['page']=22
    elif mutation=='model':data['runtime']['language_models']={'eng':'0'*64}
    elif mutation=='image':data['pages'][0]['image_sha256']='0'*64
    else:doc['hybrid_profile']['pages']=[23,22]
    save()
    with pytest.raises(ValueError):source_graph.build(bundle,tmp_path)
