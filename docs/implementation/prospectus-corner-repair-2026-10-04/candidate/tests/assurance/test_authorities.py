from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import pytest
from legalmath.canonical import raw_digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.authorities import AuthorityCatalog, root_reference
from legalmath.interpretation.assurance.sources import extract_document, packet_from_context, audit_packet, visual_inventory
from legalmath.interpretation.assurance.monitor import Monitor
from .test_sources import doc

TEXT = ('Code of Conduct. Effective from 2023-09-01 until 2024-01-01.\n'
        '3.11 Gifts. A distributor should not offer gifts.\n'
        'Footnote: except for a discount of fees or charges.\n'
        'Unrelated section on a different control.\n')


def catalog_data(text=TEXT):
    source = {'url': 'https://www.sfc.hk/test/code.pdf', 'media_type': 'text/plain', 'data': text.encode()}
    document = {**source, **extract_document(source)}
    def anchor(quote):
        start = text.index(quote)
        return {'edition_id': 'edition.2023', 'start': start, 'end': start + len(quote), 'quote': quote}
    identity = anchor('Code of Conduct.')
    temporal = anchor('Effective from 2023-09-01 until 2024-01-01.')
    value = {'version': 'authority-catalog.v1',
        'authorities': [{'authority_id': 'sfc.code', 'issuer': 'Securities and Futures Commission',
            'jurisdiction': 'Hong Kong', 'kind': 'CODE', 'title': 'Code of Conduct', 'identity_evidence': [identity]}],
        'editions': [{'edition_id': 'edition.2023', 'authority_id': 'sfc.code', 'url': source['url'],
            'raw_sha256': document['raw_sha256'], 'text_sha256': document['text_sha256'], 'media_type': 'text/plain',
            'path': 'code.txt', 'retrieved_at': '2026-09-24T00:00:00Z', 'published_on': '2023-09-01',
            'effective_from': '2023-09-01', 'effective_until': '2024-01-01',
            'temporal_evidence': [temporal], 'temporal_status': 'DOCUMENTED_INTERVAL'}],
        'provisions': [
            {'provision_id': 'code.3.11', 'authority_id': 'sfc.code', 'edition_id': 'edition.2023', 'locator': '3.11',
             'regions': [{'region_id': 'gift', 'role': 'PROVISION', 'anchor': anchor('3.11 Gifts. A distributor should not offer gifts.')}],
             'requires': ['code.footnote'], 'unresolved_references': [], 'context_status': 'REVIEWED_SELECTION',
             'selection_basis': 'Controlled fixture declares its attached footnote.'},
            {'provision_id': 'code.footnote', 'authority_id': 'sfc.code', 'edition_id': 'edition.2023', 'locator': 'footnote',
             'regions': [{'region_id': 'discount', 'role': 'PROVISION', 'anchor': anchor('Footnote: except for a discount of fees or charges.')}],
             'requires': [], 'unresolved_references': [], 'context_status': 'REVIEWED_SELECTION',
             'selection_basis': 'Controlled fixture exception.'}],
        'aliases': [{'locator': s, 'authority_id': 'sfc.code', 'provision_locator': '3.11',
                     'evidence': [identity], 'basis': 'Declared fixture locator'} for s in ('Paragraph 3.11 of the Code', 'Code paragraph 3.11')],
        'relationships': []}
    return value, {'edition.2023': document}


def registry():
    return AuthorityCatalog(*catalog_data())


def test_exact_aliases_preserve_identity_temporal_boundaries_and_wrong_issuer():
    c = registry()
    a = c.resolve('Paragraph 3.11 of the Code', '2023-11-30')
    b = c.resolve('Code paragraph 3.11', '2023-11-30')
    assert a['status'] == b['status'] == 'RESOLVED'
    assert a['provision_id'] == b['provision_id'] == 'code.3.11'
    assert c.resolve('Code paragraph 3.11', '2023-08-31')['status'] == 'WRONG_EDITION'
    assert c.resolve('Code paragraph 3.11', '2024-01-01')['status'] == 'WRONG_EDITION'
    assert c.resolve('Code paragraph 3.11', '2023-11-30', issuer='Another regulator')['status'] == 'UNAVAILABLE'
    assert c.resolve('Probably the Code 3.11', '2023-11-30')['status'] == 'UNAVAILABLE'


def test_missing_and_overlapping_editions_and_same_title_other_authority_stay_ambiguous():
    value, docs = catalog_data()
    value['editions'][0].update(temporal_status='UNKNOWN', effective_from=None, effective_until=None, temporal_evidence=[])
    assert AuthorityCatalog(value, docs).resolve('Code paragraph 3.11', '2023-11-30')['status'] == 'UNKNOWN_VERSION'
    value, docs = catalog_data(); p = deepcopy(value['provisions'][0]); p['provision_id'] = 'code.other'
    value['provisions'].append(p)
    assert AuthorityCatalog(value, docs).resolve('Code paragraph 3.11', '2023-11-30')['status'] == 'AMBIGUOUS_VERSION'
    value, docs = catalog_data(); other = deepcopy(value['authorities'][0]); other['authority_id'] = 'sfc.other'
    value['authorities'].append(other)
    alias = deepcopy(value['aliases'][0]); alias['authority_id'] = 'sfc.other'; value['aliases'].append(alias)
    assert AuthorityCatalog(value, docs).resolve(alias['locator'], '2023-11-30')['status'] == 'AMBIGUOUS_IDENTITY'


def test_changed_bytes_and_forged_span_and_missing_date_evidence_rejected():
    value, docs = catalog_data(); docs['edition.2023']['data'] += b' changed'
    with pytest.raises(LegalMathError): AuthorityCatalog(value, docs)
    value, docs = catalog_data(); value['provisions'][0]['regions'][0]['anchor']['quote'] = 'Invented rule'
    with pytest.raises(LegalMathError): AuthorityCatalog(value, docs)
    value, docs = catalog_data(); value['editions'][0]['temporal_evidence'] = []
    with pytest.raises(LegalMathError): AuthorityCatalog(value, docs)


def test_full_context_closure_retains_remote_exception_and_accounts_for_omitted_text():
    c = registry(); selected = c.select(c.resolve('Code paragraph 3.11', '2023-11-30'))
    assert selected['status'] == 'DECLARED_CONTEXT_CHECKED'
    context = {'documents': selected['documents'], 'findings': []}
    p = packet_from_context(context, 'Gift rule')
    assert any('discount' in u['text'] for u in p['units'])
    assert all('Unrelated' not in u['text'] for u in p['units'])
    assert selected['documents'][0]['data'] == TEXT.encode()
    findings = audit_packet(p, context)
    assert {f['kind'] for f in findings} == {'SELECTED_AUTHORITY_CONTEXT'}
    broken = deepcopy(p); broken['units'].pop()
    assert any(f['kind'] == 'MISSING_SOURCE_TEXT' for f in audit_packet(broken, context))
    assert selected['documents'][0]['selection']['omitted_characters'] > 0


def test_context_limits_missing_reference_and_proposed_selection_never_mean_complete():
    c = registry(); resolution = c.resolve('Code paragraph 3.11', '2023-11-30')
    assert c.select(resolution, max_provisions=1)['status'] == 'CONTEXT_INCOMPLETE'
    value, docs = catalog_data(); value['provisions'][0]['requires'].append('missing.definition')
    value['provisions'][0]['context_status'] = 'PROPOSED_SELECTION'
    c = AuthorityCatalog(value, docs); selected = c.select(c.resolve('Code paragraph 3.11', '2023-11-30'))
    assert {'MISSING_CONTEXT_PROVISION', 'PROPOSED_CONTEXT_SELECTION'} <= {f['kind'] for f in selected['findings']}
    value, docs = catalog_data(TEXT + 'Long qualification. ' * 200)
    value['provisions'][0]['regions'].append({'region_id': 'long', 'role': 'QUALIFICATION',
        'anchor': {'edition_id': 'edition.2023', 'start': len(TEXT), 'end': len(docs['edition.2023']['text']),
                   'quote': docs['edition.2023']['text'][len(TEXT):]}})
    c = AuthorityCatalog(value, docs); selected = c.select(c.resolve('Code paragraph 3.11', '2023-11-30'), max_bytes=1000)
    assert selected['status'] == 'CONTEXT_INCOMPLETE' and selected['documents'] == []
    assert selected['selected_bytes'] > 1000


def test_forged_resolution_and_selected_ranges_cannot_hide_or_substitute_text():
    c = registry(); resolution = c.resolve('Code paragraph 3.11', '2023-11-30')
    resolution['provision_id'] = 'code.footnote'
    with pytest.raises(LegalMathError): c.select(resolution)
    selected = c.select(c.resolve('Code paragraph 3.11', '2023-11-30'))
    selected['documents'][0]['text'] += ' changed'
    with pytest.raises(LegalMathError): packet_from_context({'documents': selected['documents'], 'findings': []}, 'Gift')


def test_catalog_load_retains_unavailable_and_rejects_path_escape(tmp_path):
    value, docs = catalog_data(); path = tmp_path/'catalog.json'
    path.write_text(json.dumps(value)); (tmp_path/'code.txt').write_bytes(TEXT.encode())
    assert AuthorityCatalog.load(path).resolve('Code paragraph 3.11', '2023-11-30')['status'] == 'RESOLVED'
    value['editions'][0]['path'] = 'missing.txt'; path.write_text(json.dumps(value))
    assert AuthorityCatalog.load(path).resolve('Code paragraph 3.11', '2023-11-30')['status'] == 'UNAVAILABLE'
    value['editions'][0]['path'] = '../outside.txt'; path.write_text(json.dumps(value))
    with pytest.raises(LegalMathError): AuthorityCatalog.load(path)


def test_exact_root_reference_resolves_retained_circular_without_retrieval(root):
    path = root/'.localresources/sfc/24EC16.json'
    document = {'url': 'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=24EC16',
                'data': path.read_bytes(), 'media_type': 'application/json'}
    result = root_reference('SFC circular, refNo=24EC16 (official locator in source packet)', [document])
    assert result['status'] == 'RESOLVED_ROOT_IDENTITY' and result['raw_sha256'] == raw_digest(path.read_bytes())
    assert root_reference('SFC circular, refNo=24EC17', [document]) is None
    assert root_reference('Probably 24EC16', [document]) is None


def test_dependency_change_reinvestigates_only_declared_closure(tmp_path):
    first = registry(); value, docs = catalog_data()
    value['provisions'][1]['selection_basis'] = 'Revised exception selection needs reinvestigation'
    second = AuthorityCatalog(value, docs)
    controls = [{'control_id': 'gift', 'source': 'circular', 'dependencies': ['authority.code.3.11']},
                {'control_id': 'unrelated', 'source': 'other', 'dependencies': []}]
    monitor = Monitor(tmp_path); calls = []
    def investigate(c, s): calls.append(c['control_id']); return {'release_eligible': False, 'status': 'UNRESOLVED'}
    versions = {'circular': 'c', 'other': 'o', **first.version_dependencies(['code.3.11'], '2023-11-30')}
    monitor.tick(controls, versions, 'method', 'facts', 0, investigate)
    monitor.tick(controls, {**versions, **second.version_dependencies(['code.3.11'], '2023-11-30')}, 'method', 'facts', 1, investigate)
    assert calls == ['gift', 'unrelated', 'gift']


def mixed_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
    w = PdfWriter(); p = w.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    img = DecodedStreamObject(); img.set_data(b'\xff\xff\xff')
    img.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Image'),
                NameObject('/Width'): NumberObject(1), NameObject('/Height'): NumberObject(1),
                NameObject('/ColorSpace'): NameObject('/DeviceRGB'), NameObject('/BitsPerComponent'): NumberObject(8)})
    p[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): w._add_object(font)}),
        NameObject('/XObject'): DictionaryObject({NameObject('/Im1'): w._add_object(img)})})
    content = DecodedStreamObject(); content.set_data(b'BT /F1 12 Tf 10 200 Td (Rule text without scanned footnote.) Tj ET q 100 0 0 20 10 100 cm /Im1 Do Q')
    p[NameObject('/Contents')] = w._add_object(content)
    output = BytesIO(); w.write(output); return output.getvalue()


def test_agreeing_extractors_cannot_certify_a_partially_scanned_pdf():
    raw = mixed_pdf(); document = {'data': raw, 'media_type': 'application/pdf', 'url': 'https://www.sfc.hk/test/pdf'}
    from legalmath.sources.extract import extract
    text, _ = extract(raw, 'application/pdf')
    result = extract_document(document, secondary=lambda *args: (text, 'controlled-second-extractor'))
    assert result['agreement'] and any(f['kind'] == 'UNSUPPORTED_VISUAL_CONTENT' for f in result['findings'])
    assert result['visual_inventory']['pages'][0]['images'] == 1
    assert not result['visual_inventory']['ocr_performed'] and not result['visual_inventory']['visual_completeness_established']


def test_soft_404_and_pdf_disguised_html_are_rejected():
    with pytest.raises(LegalMathError):
        extract_document({'data': b'<html><title>404 | SFC</title>Not found</html>', 'media_type': 'text/html'})
    with pytest.raises(LegalMathError):
        extract_document({'data': b'<html><title>404 | SFC</title></html>', 'media_type': 'application/pdf'})


def test_selected_qualification_cannot_be_dropped_by_editing_only_the_range_mask():
    c = registry(); selected = c.select(c.resolve('Code paragraph 3.11', '2023-11-30'))
    selected['documents'][0]['selection']['ranges'].pop()
    with pytest.raises(LegalMathError):
        packet_from_context({'documents': selected['documents'], 'findings': []}, 'Gift')


@pytest.mark.parametrize('passes', [1, 2])
def test_runtime_acquires_catalog_context_before_removing_missing_authority_finding(root, tmp_path, passes):
    from legalmath.interpretation.assurance.engine import Assurance
    from tests.search.support import FunctionProvider
    from .test_integration import responder, settings, source
    normal = responder()
    def respond(request):
        result = normal(request)
        if request['task'] == 'SOURCE_INVENTORY':
            result['authorities'] = [{'dependency_id': 'code', 'title_or_locator': 'Code paragraph 3.11',
                                     'evidence': result['claims'][0]['evidence'][0], 'needed_for_control': True}]
            result['units'] += [{'unit_id': u['unit_id'], 'disposition': 'CONTEXT', 'claim_ids': [],
                                'rationale': 'Retained code/exception supports the selected root control.'}
                               for u in request['source_packet']['units'][1:]]
        if request.get('original_task', request['task']) in ('GENERATE', 'REFINE'):
            result['coverage'] += [{'unit_id': u['unit_id'], 'status': 'CONTEXT', 'reason': 'Catalog context'}
                                   for u in request['source_packet']['units'][1:]]
        return result
    provider = FunctionProvider(respond)
    config = settings().model_copy(update={'max_context_passes': passes})
    run = Assurance(tmp_path/'run', provider, root/'.localresources/java-toolchain/jdk-17.0.20.1+1',
                    '2023-11-30T00:00:00.000000Z', config)
    result = run.drive([source()], 'Gift rule', authority_registry=registry())
    assert result['execution_complete'], result
    packet = loads((tmp_path/'run/packet.json').read_bytes())
    assert (len(packet['units']) > 1) == (passes == 2)
    assert any(f['kind'] == 'AUTHORITY_NEEDED' for f in result['findings']) == (passes == 1)
    if passes == 2:
        generation = next(r for r in provider.requests if r['task'] == 'GENERATE')
        assert any('Footnote' in u['text'] for u in generation['source_packet']['units'])
        assert any(f['kind'] == 'SELECTED_AUTHORITY_CONTEXT' for f in result['findings'])
    assert (tmp_path/'run/authority-catalog.json').is_file() and list((tmp_path/'run/authority-sources').glob('*.bin'))
    assert run.verify() == result


def test_unresolved_authority_survives_source_inventory_repair(root, tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from tests.search.support import FunctionProvider
    from .test_integration import responder, settings, source
    normal = responder()
    def respond(request):
        repaired = request['task'] == 'REPAIR_SOURCE_INVENTORY'
        result = normal({**request, 'task': 'SOURCE_INVENTORY'} if repaired else request)
        if request['task'] in ('SOURCE_INVENTORY', 'REPAIR_SOURCE_INVENTORY'):
            result['authorities'] = [{'dependency_id':'code','title_or_locator':'Code paragraph 3.11',
                'evidence':result['claims'][0]['evidence'][0],'needed_for_control':True}]
            if not repaired: result['claims'][0]['exceptions'] = []
        return result
    run = Assurance(tmp_path/'run', FunctionProvider(respond), root/'.localresources/java-toolchain/jdk-17.0.20.1+1',
                    '2026-09-23T00:00:00.000000Z', settings(1))
    result = run.drive([source()], 'Gift rule', authority_registry=registry())
    assert any(r['kind']=='SOURCE_INVENTORY' for r in result['repairs']),result
    assert any(f['kind']=='AUTHORITY_RESOLUTION_UNCERTAIN' for f in result['findings'])
