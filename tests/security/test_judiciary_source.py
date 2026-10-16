"""The retained court-source host uses the same narrow public HTTPS policy."""
import pytest

from legalmath.errors import LegalMathError
from legalmath.sources.fetch import validate_url
from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
from scripts.legal_interpretation_s2_cases import source


def resolver(ip):
    return lambda *args, **kwargs: [(2, 1, 6, '', (ip, 443))]


def test_actual_retained_judgments_enter_as_explicitly_derived_text():
    documents = []
    for name in ('gatecoin-2023-official', 'gatecoin-2025-official'):
        text, original = source(name)
        parsed, addresses = validate_url(original['url'], resolver('8.8.8.8'))
        assert parsed.hostname == 'legalref.judiciary.hk' and addresses == ['8.8.8.8']
        documents.append({'url':original['url'], 'media_type':'text/plain', 'data':text.encode()})
    context = acquire_context(documents, max_documents=2, max_depth=0)
    assert len(context['documents']) == 2
    packet = packet_from_context(context, 'Conditional trust and acceptance analysis')
    assert all(any(word in u['text'] for u in packet['units']) for word in ('Samara','Non-Consenting'))
    assert not context['semantic_reference_completeness']


@pytest.mark.parametrize('url', [
    'http://legalref.judiciary.hk/x', 'https://legalref.judiciary.hk.evil.test/x',
    'https://user:password@legalref.judiciary.hk/x', 'https://legalref.judiciary.hk:8000/x',
    'https://judiciary.hk/x'])
def test_judiciary_host_does_not_admit_lookalikes_or_modified_authority(url):
    with pytest.raises(LegalMathError):
        validate_url(url, resolver('8.8.8.8'))


@pytest.mark.parametrize('ip', ['127.0.0.1','10.0.0.1','169.254.169.254','::1'])
def test_judiciary_host_still_rejects_private_dns(ip):
    with pytest.raises(LegalMathError):
        validate_url('https://legalref.judiciary.hk/x', resolver(ip))
