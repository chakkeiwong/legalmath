from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.errors import LegalMathError
from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.sources import (
    acquire_context, extract_document, packet_from_context, audit_packet, normalized)

URL = 'https://www.sfc.hk/test/circular'


def doc(text='<p>A distributor must disclose risks.</p><p>Except where exempt.</p>', url=URL):
    return {'url': url, 'media_type': 'application/json', 'data': json.dumps({'html': text, 'appendixDocList': []}).encode()}


def test_independent_inventory_detects_dropped_footnote_and_forged_text():
    context = acquire_context([doc()]); packet = packet_from_context(context, 'Disclosures')
    assert context['status'] == 'EXPLICIT_REFERENCES_CHECKED'
    assert audit_packet(packet, context) == []
    omitted = deepcopy(packet); omitted['units'].pop()
    assert audit_packet(omitted, context)[0]['kind'] == 'MISSING_SOURCE_TEXT'
    forged = deepcopy(packet); forged['units'][0]['text'] = 'A distributor may hide risks.'
    with pytest.raises(LegalMathError) as error:
        audit_packet(forged, context)
    assert error.value.code == 'E_REFERENCE'


def test_annex_is_acquired_and_bounded_missing_annex_cannot_pass():
    source = doc(); value = json.loads(source['data']); value.update(refNo='23EC35', appendixDocList=[{'refNo': 0, 'caption': 'Annex'}]); source['data'] = json.dumps(value).encode()
    calls = []
    def fetched(url):
        calls.append(url); return {'url': url, 'data': b'Annex qualification.', 'media_type': 'text/plain'}
    context = acquire_context([source], fetcher=fetched)
    assert len(calls) == 1 and len(context['documents']) == 2
    assert audit_packet(packet_from_context(context, 'Disclosures'), context) == []
    limited = acquire_context([source], fetcher=fetched, max_documents=1)
    assert any(f['kind'] == 'ACQUISITION_LIMIT' for f in limited['findings'])


def test_reference_cycles_missing_sources_and_untrusted_hosts_are_visible():
    a = doc('<p>Rule <a href="https://www.sfc.hk/test/b">B</a></p>')
    b = doc('<p><a href="' + URL + '">A</a></p>', 'https://www.sfc.hk/test/b')
    context = acquire_context([a], retained=[b])
    assert len(context['documents']) == 2
    assert any(f['kind'] == 'REFERENCE_CYCLE' for f in context['findings'])
    failed = acquire_context([a], fetcher=lambda url: (_ for _ in ()).throw(OSError('offline')))
    assert any(f['kind'] == 'SOURCE_UNAVAILABLE' for f in failed['findings'])
    external = doc('<p><a href="https://127.0.0.1/secrets">Annex</a></p>')
    result = acquire_context([external], fetcher=lambda _: pytest.fail('Must not fetch private host'))
    assert result['findings'][0]['kind'] == 'UNRESOLVED_AUTHORITY'


def test_changed_and_superseded_versions_do_not_reuse_old_results():
    source = doc('<p>This circular has been replaced by new requirements.</p>')
    context = acquire_context([source], expected_versions={URL: 'a'*64})
    assert {'SOURCE_VERSION_CHANGED', 'SUPERSESSION_NOTICE'} <= {f['kind'] for f in context['findings']}


def test_secondary_parser_disagreement_and_unavailable_are_findings():
    source = doc()
    parsed = extract_document(source, secondary=lambda raw, media: ('Rule without exception', 'other'))
    assert parsed['findings'][0]['kind'] == 'EXTRACTION_DISAGREEMENT'
    def unavailable(*args): raise LegalMathError('E_DEPENDENCY')
    assert extract_document(source, secondary=unavailable)['findings'][0]['kind'] == 'SECOND_EXTRACTION_UNAVAILABLE'


def test_real_circular_inventory_is_reproducible_and_contains_discount():
    root = Path(__file__).resolve().parents[2]
    source = {'url': URL, 'media_type': 'application/json', 'data': (root/'.localresources/sfc/23EC46.json').read_bytes()}
    a = acquire_context([source]); b = acquire_context([source])
    assert a == b
    packet = packet_from_context(a, 'Paragraph 10 gift control')
    assert not audit_packet(packet, a)
    assert any('other than a discount' in u['text'] for u in packet['units'])
    assert a['documents'][0]['agreement']


def test_whitespace_change_preserves_inventory_but_not_source_version():
    a, b = doc(), doc('<p>A distributor must disclose risks.</p>\n  <p>Except where exempt.</p>')
    x, y = extract_document(a), extract_document(b)
    assert normalized(x['text']) == normalized(y['text'])
    assert x['raw_sha256'] != y['raw_sha256']


def test_unbound_and_duplicate_units_rejected():
    context = acquire_context([doc()]); packet = packet_from_context(context, 'Rule')
    packet['units'][0]['span'] = None
    assert audit_packet(packet, context)[0]['kind'] == 'UNBOUND_SOURCE_UNIT'
    packet['units'].append(deepcopy(packet['units'][0]))
    with pytest.raises(LegalMathError) as error:
        audit_packet(packet, context)
    assert error.value.code == 'E_DUPLICATE_ID'
