"""Document/package outputs must influence actual service consumers."""
from copy import deepcopy
from scripts.prospectus_closure_fixtures import annotation_fixture, term_fixture
import pytest
from test_successor import request, PREFIX
from legalmath.prospectus.successor import (source_graph, service, contract_assembly,
    clause_graph, occurrences, annotation_bridge)
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.contracts import write

REVIEW = {"reviewer": "development-reader", "kind": "DEVELOPMENT", "reason": "Explicit synthetic control"}
LOSS = "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."


def pdf_fixture(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 10 Tf 40 720 Td (The Notes are unsecured obligations of the Issuer.) Tj '
        b'0 -24 Td (The Notes will be redeemed at 100 per cent of their principal amount at maturity.) Tj '
        b'0 -24 Td (This margin governs the repayment definition.) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(stream)
    path = tmp_path / 'source.pdf'
    with path.open('wb') as output:
        writer.write(output)
    req = request(tmp_path, [PREFIX])
    req['bundle']['documents'][0].update(path=str(path), sha256=digest(path.read_bytes()), format='pdf')
    graph = source_graph.build(req['bundle'], tmp_path)
    assert len(graph['units']) == 3
    req['assembly'] = {'operations': [{'unit': u['id'], 'source_text_sha256': u['text_sha256'],
        'role': 'INSTRUCTION' if i == 2 else 'OPERATIVE', 'reason': 'Synthetic page', 'context': 'whole'} for i,u in enumerate(graph['units'])]}
    layout = {'pages': {'1': {'size': {'height': 792}}}, 'texts': []}
    for i,u in enumerate(graph['units']):
        l,t,r,b = u['bbox']
        layout['texts'].append({'self_ref': f'#/texts/{i}', 'text': u['raw'], 'label': 'text',
            'prov': [{'page_no': 1, 'bbox': {'l': l, 't': t, 'r': r, 'b': b, 'coord_origin': 'TOPLEFT'}}]})
    a = [occurrences.anchor(u) for u in graph['units']]
    req['layout_admission'] = {'version': 'prospectus-layout.v1', 'graph_sha256': digest(graph),
        'documents': [{'document': 'd', 'source_sha256': a[0]['source_sha256'], 'docling': layout}],
        'governing': [{'id': 'margin', 'kind': 'governs', 'from': a[2], 'to': [a[1]],
                       'questions': ['Q1'], 'reason': 'Reviewed scope extent'}], 'review': REVIEW}
    return req


def test_layout_governing_output_is_consumed(tmp_path):
    req = pdf_fixture(tmp_path)
    report = service.assess(req, tmp_path)
    assert report['questions']['Q1']['status'] == 'NO'
    assert len(report['source_map']['layout']['projections'][0]['mappings']) == 3
    assert any(d['id'] == 'governing:margin:Q1' and d['status'] == 'RESOLVED' for d in report['dependencies'])
    req['assembly']['operations'][1]['role'] = 'EXCLUDED'
    report = service.assess(req, tmp_path)
    assert report['questions']['Q1']['status'] == 'UNKNOWN'
    assert 'governing:margin:Q1' in report['questions']['Q1']['unresolved']


def test_layout_stale_source_rejected(tmp_path):
    req = pdf_fixture(tmp_path)
    req['layout_admission']['graph_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='Layout source graph changed'):
        service.assess(req, tmp_path)




def test_authored_exception_changes_installed_service_input(tmp_path):
    req = annotation_fixture(tmp_path)
    req['observations'] = {'exempt': False}
    assert service.assess(req, tmp_path)['questions']['Q1']['status'] == 'YES'
    req['observations']['exempt'] = True
    assert service.assess(req, tmp_path)['questions']['Q1']['status'] == 'NO'
    del req['observations']
    assert service.assess(req, tmp_path)['questions']['Q1']['status'] == 'UNKNOWN'


def test_annotation_mapping_and_meaning_cannot_override_evidence(tmp_path):
    req = annotation_fixture(tmp_path)
    req['annotation_admission']['packets'][0]['map'][0]['source']['quote'] = 'invented'
    with pytest.raises(ValueError, match='quote changed'):
        service.assess(req, tmp_path)


@pytest.mark.parametrize('mutation', ['delete', 'redirect', 'unsupported'])
def test_authored_relation_must_reach_same_typed_clause_link(tmp_path, mutation):
    req = annotation_fixture(tmp_path)
    packet = req['annotation_admission']['packets'][0]['packet']
    decoded = annotation_bridge.reimport(packet, packet['text'], packet['source'])
    if mutation == 'delete':
        decoded['relations'] = []
    elif mutation == 'redirect':
        decoded['relations'][0]['to'] = '0'
    else:
        decoded['relations'][0]['kind'] = 'unimplemented'
    req['annotation_admission']['packets'][0]['packet'] = annotation_bridge.export(
        packet['text'], packet['source'], decoded['groups'], decoded['relations'])
    with pytest.raises(ValueError, match='authored relation|Authored relations'):
        service.assess(req, tmp_path)
    req = annotation_fixture(tmp_path)
    req['annotation_admission']['meanings'][0]['clause']['quote'] = 'invented'
    with pytest.raises(ValueError, match='evidence-derived'):
        service.assess(req, tmp_path)


def test_reviewed_disposition_promotes_only_bound_selected_text(tmp_path):
    req = request(tmp_path, [PREFIX])
    req.pop('assembly')
    p1 = service.source_product(req, tmp_path)
    base = service.construction_product(p1, tmp_path)['payload']['assembly']
    raw = p1['payload']['graph']['units'][0]
    req['reviewed_dispositions'] = {'version': 'reviewed-dispositions.v1', 'assembly_sha256': digest(base),
        'review': REVIEW, 'units': [{'unit': raw['id'], 'role': 'OPERATIVE', 'text_sha256': digest(raw['raw'].encode()),
                                  'reason': 'Complete supplied interpretation', 'sources': [occurrences.anchor(raw)]}]}
    assert service.assess(req, tmp_path)['questions']['Q1']['status'] == 'NO'
    req['reviewed_dispositions']['units'][0]['text_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='text/evidence changed'):
        service.assess(req, tmp_path)




def test_finance_consumes_selected_terms_and_rejects_wrong_rate(tmp_path):
    req = term_fixture(tmp_path)
    answer = service.assess(req, tmp_path)['questions']['Q5']
    assert answer['status'] == 'CONDITIONAL'
    assert [t['amount'] for t in answer['value']['calculation']['transfers']] == ['1001/100', '501/100']
    req['term_interpretations']['terms']['annual_rate']['value'] = '0.06'
    with pytest.raises(ValueError, match='Rate differs'):
        service.assess(req, tmp_path)


def test_current_consume_revalidates_derivative_but_frozen_replay_is_labelled(tmp_path):
    req = request(tmp_path, [PREFIX])
    doc = req['bundle']['documents'][0]
    ocr = {'source_sha256': doc['sha256'], 'page_count': 1, 'runtime': {'dpi': 300, 'language': 'eng'},
           'pages': [{'page': 1, 'text': PREFIX, 'words': []}]}
    write(tmp_path / 'ocr.json', ocr)
    doc['ocr'] = {'path': 'ocr.json', 'sha256': digest((tmp_path / 'ocr.json').read_bytes())}
    req.pop('assembly')
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
                'P5': service.financial_product(p1, p2, p3)}
    assert service.consume(products, tmp_path, mode='current')['assessment_mode'] == 'current'
    write(tmp_path / 'ocr.json', {**ocr, 'page_count': 2})
    assert service.consume(products, tmp_path)['assessment_mode'] == 'frozen'
    with pytest.raises(ValueError, match='OCR extraction changed'):
        service.consume(products, tmp_path, mode='current')


def test_missing_poppler_has_typed_error(tmp_path, monkeypatch):
    from legalmath.prospectus.successor.extraction import ExtractionUnavailable
    req = request(tmp_path, [PREFIX])
    req['bundle']['documents'][0]['format'] = 'pdf'
    def absent(*args, **kwargs):
        raise FileNotFoundError('pdftotext')
    monkeypatch.setattr(source_graph.subprocess, 'run', absent)
    with pytest.raises(ExtractionUnavailable, match='Poppler'):
        service.assess(req, tmp_path)
