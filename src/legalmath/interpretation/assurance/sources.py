"""Bounded source closure and independently implemented extraction inventories."""
from collections import Counter, deque
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs, urlencode

from ...canonical import digest, raw_digest
from ...errors import LegalMathError
from ...sources.extract import extract, TextParser
from ...sources.fetch import HOSTS, fetch
from ...sources.anchors import make_span
from ..contracts import Packet, parse
from ..search.models import DIMENSIONS


def normalized(text):
    """Whitespace only; negation, punctuation, numbers and order remain significant."""
    return re.sub(r'\s+', ' ', text).strip()


def official_url(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None, 443):
        raise LegalMathError('E_FETCH', details='Only explicit official HTTPS references may be acquired')
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))


def transport_url(url):
    """SFC gateway links are HTML shells; acquire their official document API."""
    p = urlsplit(url); query = parse_qs(p.query)
    if p.hostname == 'apps.sfc.hk' and '/gateway/' in p.path and 'refNo' in query:
        return 'https://apps.sfc.hk/edistributionWeb/api/circular/doc?' + urlencode({'refNo': query['refNo'][0], 'lang': 'EN'})
    return url


def second_extract(raw, media_type):
    if media_type in ('application/json', 'text/html'):
        html = json.loads(raw)['html'] if media_type == 'application/json' else raw.decode('utf-8')
        # Separate tokenization algorithm from HTMLParser. Excluded hidden content
        # and malformed markup can disagree; disagreement is deliberately retained.
        html = re.sub(r'<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>', '', html, flags=re.S | re.I)
        html = re.sub(r'</(?:p|li|ol|h[1-6]|div|tr)>|<br\b[^>]*>', '\n', html, flags=re.I)
        return unescape(re.sub(r'<[^>]*>', '', html)), 'independent-html-tokenizer.v1'
    if media_type == 'text/plain':
        return raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n'), 'utf8-line-inventory.v1'
    if media_type == 'application/pdf':
        tool = shutil.which('pdftotext')
        if tool is None:
            raise LegalMathError('E_DEPENDENCY', details='Independent PDF extractor unavailable')
        with tempfile.TemporaryDirectory(prefix='legalmath-inventory-') as tmp:
            source = Path(tmp) / 'source.pdf'; target = Path(tmp) / 'text.txt'
            source.write_bytes(raw)
            subprocess.run([tool, '-layout', str(source), str(target)], check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if target.stat().st_size > 20 * 1024 * 1024:
                raise LegalMathError('E_RESOURCE_LIMIT')
            return target.read_text(), 'poppler-pdftotext-layout'
    raise LegalMathError('E_UNSUPPORTED_PROFILE')


def extract_document(document, *, secondary=second_extract):
    raw, media = document['data'], document['media_type']
    if not isinstance(raw, bytes) or len(raw) > 20 * 1024 * 1024:
        raise LegalMathError('E_RESOURCE_LIMIT')
    if media == 'text/html':
        parser = TextParser(); parser.feed(raw.decode('utf-8'))
        primary, method = ''.join(parser.parts), {'name': 'html-parser'}
    else:
        primary, method = extract(raw, media)
    findings = []
    try:
        other, other_method = secondary(raw, media)
        agreement = normalized(primary) == normalized(other)
        if not agreement:
            findings.append({'kind': 'EXTRACTION_DISAGREEMENT', 'primary_only':
                list((Counter(primary.split()) - Counter(other.split())).elements())[:100],
                'secondary_only': list((Counter(other.split()) - Counter(primary.split())).elements())[:100]})
    except (LegalMathError, OSError, ValueError, subprocess.SubprocessError):
        other, other_method, agreement = None, 'unavailable', False
        findings.append({'kind': 'SECOND_EXTRACTION_UNAVAILABLE'})
    if not primary.strip():
        findings.append({'kind': 'EMPTY_EXTRACTION'})
    return {'text': primary, 'secondary_text': other, 'primary_method': method,
            'secondary_method': other_method, 'agreement': agreement, 'findings': findings,
            'raw_sha256': raw_digest(raw), 'text_sha256': raw_digest(primary.encode())}


def references(document):
    """Discover explicit locators only. Text-only authorities stay unresolved."""
    url, media, raw = document['url'], document['media_type'], document['data']
    if media not in ('application/json', 'text/html'):
        return []
    value = json.loads(raw) if media == 'application/json' else {'html': raw.decode('utf-8')}
    html = value['html']; result = []
    for match in re.finditer(r'\bhref\s*=\s*([\"\'])(.*?)\1', html, re.I | re.S):
        href = unescape(match.group(2)).strip()
        if not href or href.startswith('#'):
            continue
        result.append({'url': urljoin(url, href).split('#')[0], 'locator': href, 'relation': 'references'})
    for index, attachment in enumerate(value.get('appendixDocList', [])):
        if not value.get('refNo'):
            result.append({'url': None, 'locator': attachment.get('caption', 'attachment'), 'relation': 'incorporates'})
            continue
        target = 'https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?' + urlencode({
            'lang': 'EN', 'refNo': value['refNo'], 'appendix': attachment.get('refNo', index)})
        result.append({'url': target, 'locator': attachment.get('caption', target), 'relation': 'incorporates'})
    return result


def acquire_context(roots, *, retained=(), fetcher=None, max_documents=20, max_depth=3,
                    expected_versions=None, secondary=second_extract):
    """Acquire linked documents with explicit bounds and retained immutable bytes.

    A supplied fetcher is an integration/test port; the production default is the
    repository's DNS-pinned official-host fetcher. No model supplies executable IO.
    """
    if not roots or not 1 <= max_documents <= 100 or not 0 <= max_depth <= 6:
        raise LegalMathError('E_SCHEMA')
    expected_versions = expected_versions or {}
    known = {official_url(d['url']): d for d in [*retained, *roots]}
    queue = deque((official_url(d['url']), 0, ()) for d in roots)
    documents, edges, findings, attempted = {}, [], [], set()
    while queue:
        url, depth, ancestry = queue.popleft()
        if url in ancestry:
            findings.append({'kind': 'REFERENCE_CYCLE', 'url': url}); continue
        if url in attempted:
            continue
        if depth > max_depth or len(attempted) >= max_documents:
            findings.append({'kind': 'ACQUISITION_LIMIT', 'url': url}); continue
        attempted.add(url)
        try:
            doc = known.get(url)
            if doc is None:
                response = (fetcher or fetch)(transport_url(url))
                official_url(response.get('url', url))
                doc = {**response, 'url': url}
            extraction = extract_document(doc, secondary=secondary)
        except (LegalMathError, OSError, ValueError, KeyError) as exc:
            findings.append({'kind': 'SOURCE_UNAVAILABLE', 'url': url,
                             'error': getattr(exc, 'code', type(exc).__name__)}); continue
        documents[url] = {**doc, **extraction}
        findings += [{**f, 'url': url} for f in extraction['findings']]
        if url in expected_versions and extraction['raw_sha256'] != expected_versions[url]:
            findings.append({'kind': 'SOURCE_VERSION_CHANGED', 'url': url,
                             'previous': expected_versions[url], 'current': extraction['raw_sha256']})
        if re.search(r'\b(?:replaced|superseded)\s+by\b', extraction['text'], re.I):
            findings.append({'kind': 'SUPERSESSION_NOTICE', 'url': url})
        for ref in references(doc):
            edge = {'from': url, **ref}; edges.append(edge)
            try:
                target = official_url(ref['url']) if ref['url'] else None
            except (LegalMathError, ValueError):
                target = None
            if target is None:
                findings.append({'kind': 'UNRESOLVED_AUTHORITY', **edge})
            else:
                queue.append((target, depth + 1, (*ancestry, url)))
    return {'documents': list(documents.values()), 'references': edges, 'findings': findings,
            'attempted_urls': sorted(attempted), 'limits': {'documents': max_documents, 'depth': max_depth},
            'status': 'SOURCE_CONTEXT_INCOMPLETE' if findings else 'EXPLICIT_REFERENCES_CHECKED',
            'semantic_reference_completeness': False}


def packet_from_context(context, selected_slice):
    units = []
    for doc in context['documents']:
        prefix = 'd' + digest(doc['url'])[:12]
        for index, match in enumerate(re.finditer(r'[^\n\f]+', doc['text'])):
            value = match.group(); start = match.start() + len(value) - len(value.lstrip()); end = match.end() - len(value) + len(value.rstrip())
            if start == end:
                continue
            # Units exceeding the contract are split without losing characters.
            for offset in range(start, end, 18000):
                stop = min(offset + 18000, end); uid = f'{prefix}.u{index}.{offset}'
                units.append({'unit_id': uid, 'locator': doc['url'] + f' chars {offset}:{stop}',
                    'text': doc['text'][offset:stop], 'normative': True,
                    'span': make_span('s.' + uid, prefix, doc['data'], doc['text'], offset, stop)})
    packet = {'source_key': 'assurance.' + digest([d['raw_sha256'] for d in context['documents']])[:24],
              'authority': 'RETAINED_SOURCE', 'selected_slice': selected_slice, 'units': units,
              'dependencies': [{'dependency_id': 'missing.' + digest(f)[:24], 'source_hash': None}
                               for f in context['findings']][:100], 'family_ids': list(DIMENSIONS)}
    return parse(Packet, packet)


def audit_packet(packet, context):
    """Check retained spans and complete text coverage, independently of unit labels."""
    packet = parse(Packet, packet); findings = []
    by_id = {'d' + digest(d['url'])[:12]: d for d in context['documents']}
    coverage = {key: [] for key in by_id}
    seen = set()
    for unit in packet['units']:
        if unit['unit_id'] in seen:
            raise LegalMathError('E_DUPLICATE_ID')
        seen.add(unit['unit_id']); span = unit['span']
        if not span or span['source_id'] not in by_id:
            findings.append({'kind': 'UNBOUND_SOURCE_UNIT', 'unit_id': unit['unit_id']}); continue
        doc = by_id[span['source_id']]
        from ...sources.anchors import verify_span
        retained_quote = verify_span(span, doc['data'], doc['text'])
        if unit['text'] != retained_quote:
            raise LegalMathError('E_REFERENCE', details='Unit text differs from retained quote')
        coverage[span['source_id']].append((span['start'], span['end']))
    for key, ranges in coverage.items():
        text = by_id[key]['text']; mask = bytearray(len(text))
        for a, b in ranges:
            mask[a:b] = b'\1' * (b-a)
        uncovered = ''.join(c for i, c in enumerate(text) if not mask[i] and not c.isspace())
        if uncovered:
            findings.append({'kind': 'MISSING_SOURCE_TEXT', 'url': by_id[key]['url'], 'text': uncovered[:2000]})
    return findings
