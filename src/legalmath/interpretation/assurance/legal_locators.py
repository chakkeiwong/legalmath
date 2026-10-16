"""Source-bound legal locators from a retained numbered HTML document.

This deliberately narrow profile refuses ambiguous numbering. It supplies a
separate index: the retained packet, source text and historical locators do not
change. A locator establishes where a quotation occurs, not what it entails.
"""
from html.parser import HTMLParser
import hashlib
import json
import re
from pathlib import Path

from ...canonical import digest
from ...errors import LegalMathError


def require(ok, message):
    if not ok:
        raise LegalMathError('E_REFERENCE', details=message)


def normalized(text):
    return ' '.join(text.split())


class NumberedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lists = []
        self.current = None
        self.outside = None
        self.sup = None
        self.records = []
        self.links = []
        self.paragraph = None
        self.emphasis = 0
        self.headings = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('strong', 'em'):
            self.emphasis += 1
        if tag == 'ol':
            require('reversed' not in attrs, 'Reversed numbering needs a different source profile')
            self.lists.append(int(attrs.get('start', '1')) - 1)
        elif tag == 'li' and len(self.lists) == 1:
            require(self.current is None, 'Unclosed numbered paragraph')
            number = int(attrs.get('value', self.lists[-1] + 1))
            require(number > 0, 'Invalid paragraph number')
            self.lists[-1] = number
            self.current = {'locator': 'P' + str(number), 'text': '', 'kind': 'paragraph'}
            self.records.append(self.current)
        elif tag == 'p' and not self.lists:
            self.outside = {'text': '', 'footnote': None}
        if tag in ('p', 'br') and self.current is not None:
            self.current['text'] += ' '
        if tag == 'p' and self.current is not None:
            self.paragraph = {'start': len(self.current['text']), 'heading': True, 'text': ''}
        if tag == 'sup':
            self.sup = {'text': '', 'leading': self.outside is not None and not self.outside['text'].strip()}

    def handle_data(self, data):
        if self.paragraph is not None:
            self.paragraph['text'] += data
            if data.strip() and not self.emphasis:
                self.paragraph['heading'] = False
        if self.current is not None:
            self.current['text'] += data
        if self.outside is not None:
            self.outside['text'] += data
        if self.sup is not None:
            self.sup['text'] += data

    def handle_endtag(self, tag):
        if tag in ('strong', 'em'):
            self.emphasis = max(0, self.emphasis - 1)
        if tag == 'p' and self.paragraph is not None:
            # Typography alone cannot distinguish a heading from substantive law.
            # Preserve all text; a reviewed source profile may narrow unit spans.
            self.paragraph = None
        if tag == 'sup' and self.sup is not None:
            number = self.sup['text'].strip()
            if number.isdigit():
                if self.current is not None:
                    self.links.append({'from': self.current['locator'], 'to': 'FN' + number})
                elif self.outside is not None and self.sup['leading']:
                    self.outside['footnote'] = number
            self.sup = None
        if tag == 'li' and len(self.lists) == 1:
            self.current = None
        elif tag == 'ol':
            require(bool(self.lists), 'Unbalanced ordered list')
            self.lists.pop()
        elif tag == 'p' and self.outside is not None:
            if self.outside['footnote'] is not None:
                self.records.append({'locator': 'FN' + self.outside['footnote'],
                                     'kind': 'footnote', 'text': self.outside['text']})
            self.outside = None


class NumberedParagraphHTML(HTMLParser):
    """Explicit decimal paragraphs and superscript footnotes in retained 23EC52.

    Footnotes may share one HTML paragraph; their superscripts delimit separate
    records. This profile is selected explicitly, never inferred for arbitrary HTML.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.sup = None
        self.records, self.links, self.headings, self.lists = [], [], [], []

    def handle_starttag(self, tag, attrs):
        require(tag not in {'ol','li'}, 'Mixed list numbering needs another source profile')
        if tag == 'p':
            require(self.current is None, 'Nested paragraph')
            self.current = {'text':'', 'supers':[]}
        if self.current is not None:
            if tag == 'br': self.current['text'] += ' '
            if tag == 'sup':
                require(self.sup is None, 'Nested superscript')
                self.sup = {'start':len(self.current['text']), 'text':''}

    def handle_data(self, data):
        if self.current is not None: self.current['text'] += data
        if self.sup is not None: self.sup['text'] += data

    def handle_endtag(self, tag):
        if tag == 'sup' and self.sup is not None:
            self.current['supers'].append(self.sup); self.sup = None
        if tag != 'p' or self.current is None: return
        require(self.sup is None, 'Unclosed superscript')
        text, supers = self.current['text'], self.current['supers']
        match = re.match(r'^\s*([1-9]\d*)\.\s+', text)
        if match:
            locator = 'P' + match.group(1)
            self.records.append({'locator':locator, 'kind':'paragraph', 'text':text})
            self.links.extend({'from':locator, 'to':'FN'+s['text'].strip()}
                              for s in supers if s['text'].strip().isdigit())
        elif supers and not text[:supers[0]['start']].strip():
            require(all(s['text'].strip().isdigit() for s in supers), 'Ambiguous footnote labels')
            for i, s in enumerate(supers):
                end = supers[i+1]['start'] if i+1 < len(supers) else len(text)
                self.records.append({'locator':'FN'+s['text'].strip(), 'kind':'footnote',
                                     'text':text[s['start']:end]})
        self.current = None


def retained_html(source_ref, root=None):
    root = Path(root or Path(__file__).resolve().parents[4]).resolve()
    require(isinstance(source_ref, dict) and set(source_ref) == {'path', 'sha256'},
            'Retained source path and SHA256 required')
    path = (root / source_ref['path']).resolve()
    require(not Path(source_ref['path']).is_absolute() and path.is_relative_to(root),
            'Retained source must be inside evidence root')
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == source_ref['sha256'], 'Original source bytes changed')
    value = json.loads(data)['html'] if path.suffix == '.json' else data.decode('utf-8')
    require(isinstance(value, str) and value.strip(), 'Retained source lacks HTML')
    return value


def build_index(packet, html, *, source_ref, unit_ids, root=None, numbering_profile='ordered-lists'):
    """Only map units explicitly assigned to this document; never cross sources."""
    require(isinstance(html, str) and html.strip(), 'Missing retained HTML')
    if source_ref:
        require(html == retained_html(source_ref, root), 'HTML differs from claimed original bytes')
    require(numbering_profile in {'ordered-lists','decimal-paragraphs'}, 'Unknown source numbering profile')
    parser = NumberedHTML() if numbering_profile == 'ordered-lists' else NumberedParagraphHTML()
    parser.feed(html)
    parser.close()
    require(not parser.lists and parser.current is None, 'Incomplete HTML list')
    records = [{**r, 'text': normalized(r['text'])} for r in parser.records]
    labels = [r['locator'] for r in records]
    if numbering_profile == 'decimal-paragraphs':
        numbers = [int(r['locator'][1:]) for r in records if r['kind']=='paragraph']
        require(numbers and numbers == list(range(1,len(numbers)+1)), 'Incomplete decimal paragraph sequence')
    require(records and len(labels) == len(set(labels)), 'Ambiguous or absent legal numbering')
    require(all(link['to'] in labels for link in parser.links), 'Unresolved footnote link')
    units = {u['unit_id']: u for u in packet['units']}
    require(len(units) == len(packet['units']) and len(unit_ids) == len(set(unit_ids))
            and set(unit_ids) <= units.keys(), 'Foreign or duplicate source unit')
    mapped = {}
    for uid in unit_ids:
        text = normalized(units[uid]['text'])
        matches = [r['locator'] for r in records if text and text in r['text']]
        mapped[uid] = {'unit_hash': digest(units[uid]), 'locators': matches,
                       'status': 'LOCATED' if len(matches) == 1 else 'AMBIGUOUS' if matches else 'UNLOCATED'}
    result = {'profile': 'numbered-html-locators.v2', 'packet_hash': digest(packet),
              'original_bytes_verified': bool(source_ref),
              'source': source_ref, 'html_hash': digest(html), 'records': records,
              'headings_without_paragraph_locator': parser.headings,
              'footnote_links': parser.links, 'units': mapped,
              'limit': 'Numbering and attachment only; no resolution of interpretive attachment or legal warrant.'}
    if numbering_profile != 'ordered-lists': result['numbering_profile'] = numbering_profile
    return {**result, 'index_hash': digest(result)}


def verify_index(packet, index, *, root=None, expected_index_hash=None):
    require(index['index_hash'] == digest({k: v for k, v in index.items() if k != 'index_hash'}), 'Source index changed')
    require(index['packet_hash'] == digest(packet), 'Source packet changed')
    require(index.get('original_bytes_verified') is True, 'Unbound test index is not legal provenance')
    require(expected_index_hash is None or index['index_hash'] == expected_index_hash, 'Unapproved index')
    rebuilt = build_index(packet, retained_html(index['source'], root), source_ref=index['source'],
                          unit_ids=list(index['units']), root=root,
                          numbering_profile=index.get('numbering_profile','ordered-lists'))
    require(index == rebuilt, 'Index differs from retained source or extraction profile')
    return index


def validate_citation(packet, index, *, unit_id, quote, locator, root=None, expected_index_hash=None):
    verify_index(packet, index, root=root, expected_index_hash=expected_index_hash)
    units = {u['unit_id']: u for u in packet['units']}
    require(unit_id in units and isinstance(quote, str) and quote.strip() and quote in units[unit_id]['text'], 'Inexact source quotation')
    row = index['units'].get(unit_id)
    require(row and row['unit_hash'] == digest(units[unit_id]), 'Unbound source unit')
    if row['status'] == 'LOCATED':
        require(row['locators'] == [locator], 'Wrong, unknown or ambiguous legal locator')
    else:
        # A lossless extraction unit may contain several numbered paragraphs.
        # Qualify the actual quote against the independently reconstructed
        # document numbering, without assigning one paragraph to the whole unit.
        matches = [r['locator'] for r in index['records']
                   if normalized(quote) in r['text']]
        require(matches == [locator], 'Wrong, unknown or ambiguous quotation locator')
    return {'unit_id': unit_id, 'quote': quote, 'locator': locator, 'index_hash': index['index_hash']}
