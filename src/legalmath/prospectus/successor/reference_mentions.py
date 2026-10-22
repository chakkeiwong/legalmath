"""Source-bound reference mentions in a finite German/English citation grammar.

Mention discovery neither chooses destinations nor establishes legal meaning.
Raw bindings are checked against supplied source units, not document authenticity.
"""
from copy import deepcopy
import re

from .contracts import digest
from .paragraph_references import discover as paragraph_discover

VERSION = 'reference-mention-report.v1'
LIMITS = {'characters': 100000, 'pieces': 10000, 'units': 10000, 'mentions': 2048}
KINDS = {'EXACT_SOURCE_COPY', 'GENERATED_SEPARATOR', 'SUPPLIED_OR_TRANSFORMED'}
SECTION = re.compile(r'(?<!§)§{1,2}\s*[0-9]+[a-z]?(?!\w)|\bSections?\s+[0-9]+[a-z]?(?!\w)', re.I)
SECTION_CUE = re.compile(r'(?<!§)§{1,2}|\bSections?\b', re.I)
COMPONENT = re.compile(r'\s*(?:\([0-9A-Za-z]+\)|\[[0-9A-Za-z]+\])')
PARAGRAPH_INTRO = re.compile(r'\s+(?:Absatzes|Absatz|Unterabsätzen)\b', re.I)
NUMBERED = re.compile(r'\s*,\s*Nr\.\s*[0-9]+(?:\s+bis\s+Nr\.\s*[0-9]+)?', re.I)
SENTENCE = re.compile(r'\s+Satz\s+[0-9]+\b', re.I)
GERMAN_LAW = r'(?:[A-ZÄÖÜ][\wÄÖÜäöüß]*-\s+und\s+)?[A-ZÄÖÜ][\wÄÖÜäöüß-]*(?:gesetz(?:es)?|G)\b|BGB\b'
ENGLISH_LAW = r'(?:U\.S\.\s+)?(?:[A-Z][A-Za-z]*\s+){0,6}Code\b(?:\s+von\s+[0-9]{4})?'
LAW_TAIL = re.compile(r'\s+(?:(?:des|der|of(?:\s+the)?)\s+)?(?:' + GERMAN_LAW + '|' + ENGLISH_LAW + r')(?:\s+\([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*\))?')
IMPLICIT = re.compile(
    r'\b(?:wie\s+(?:nachstehend|unten|oben|vorstehend)\s+definiert|'
    r'im\s+oben\s+genannten\s+Sinn|Für\s+die\s+Zwecke\s+des\s+Vorstehenden|'
    r'vorstehend\s+unter\s+\([a-z0-9]+\)(?:\s+(?:und|oder)\s+\([a-z0-9]+\))*|'
    r'as\s+defined\s+(?:below|above))\b', re.I)
# The final word boundary cannot follow a closing parenthesis.
IMPLICIT_LIST = re.compile(r'\bvorstehend\s+unter\s+\([a-z0-9]+\)(?:\s+(?:und|oder)\s+\([a-z0-9]+\))*', re.I)
NAMED_LAW = re.compile(r'\bVorschriften\s+(?:des|der)\s+(?:' + GERMAN_LAW + r')|'
    r'\bGesetz(?:es)?\s+zur\s+[^.;()]{1,180}\([A-ZÄÖÜ][\wÄÖÜäöüß-]*gesetz\)')
UNSPECIFIED = re.compile(r'\bzwingende\s+gesetzliche\s+Bestimmungen\b|\bU\.S\.\s+Steuerrecht\b', re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(value, required, label):
    require(isinstance(value, dict) and set(value) == set(required), label + ' fields differ')


def integer(value):
    return type(value) is int


def checksum(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def validate(request):
    fields(request, ('version', 'text', 'text_sha256', 'source_pieces', 'raw_units', 'section_headers'), 'Request')
    text = request['text']
    require(request['version'] == 'reference-mention-request.v1', 'Request version differs')
    require(isinstance(text, str) and 0 < len(text) <= LIMITS['characters'], 'Bounded nonempty text required')
    require(digest(text.encode()) == request['text_sha256'], 'Selected text identity differs')
    for key, limit in (('source_pieces', 'pieces'), ('raw_units', 'units'), ('section_headers', 'pieces')):
        require(isinstance(request[key], list) and len(request[key]) <= LIMITS[limit], 'Bounded ' + key + ' required')
    units = {}
    for unit in request['raw_units']:
        fields(unit, ('id', 'document', 'source_sha256', 'raw', 'text_sha256'), 'Raw unit')
        require(isinstance(unit['id'], str) and unit['id'] and unit['id'] not in units, 'Unique raw unit required')
        require(isinstance(unit['document'], str) and unit['document'] and checksum(unit['source_sha256']), 'Raw document identity differs')
        require(isinstance(unit['raw'], str) and len(unit['raw']) <= LIMITS['characters'], 'Bounded raw text required')
        require(digest(unit['raw'].encode()) == unit['text_sha256'], 'Raw text identity differs')
        units[unit['id']] = unit
    position = 0
    for piece in request['source_pieces']:
        fields(piece, ('start', 'end', 'text', 'kind', 'raw_binding'), 'Source piece')
        a, b = piece['start'], piece['end']
        require(integer(a) and integer(b) and a == position and a < b <= len(text), 'Source partition differs')
        require(piece['text'] == text[a:b] and piece['kind'] in KINDS, 'Source piece content or kind differs')
        raw = piece['raw_binding']
        require((raw is not None) == (piece['kind'] == 'EXACT_SOURCE_COPY'), 'Raw-copy classification differs')
        if raw is not None:
            fields(raw, ('unit', 'document', 'source_sha256', 'start', 'end', 'quote'), 'Raw binding')
            require(isinstance(raw['unit'], str) and raw['unit'] in units, 'Raw binding unit missing')
            unit = units[raw['unit']]
            left, right = raw['start'], raw['end']
            require(integer(left) and integer(right) and 0 <= left < right <= len(unit['raw']), 'Raw offsets differ')
            require(right - left == b - a and unit['raw'][left:right] == raw['quote'] == piece['text'], 'Raw slice differs')
            require(raw['document'] == unit['document'] and raw['source_sha256'] == unit['source_sha256'], 'Raw identity differs')
        position = b
    require(position == len(text), 'Incomplete source partition')
    headers = set()
    for row in request['section_headers']:
        fields(row, ('start', 'end', 'unit'), 'Section header')
        a, b = row['start'], row['end']
        require(integer(a) and integer(b) and 0 <= a < b <= len(text), 'Header offsets differ')
        require(re.fullmatch(r'§\s*[0-9]+', text[a:b]) is not None, 'Only exact full section labels can be excluded')
        matching = [p for p in request['source_pieces'] if p['start'] == a and p['end'] == b and p['raw_binding']]
        require(len(matching) == 1 and matching[0]['raw_binding']['unit'] == row['unit'], 'Header source differs')
        require(units[row['unit']]['raw'].strip() == text[a:b], 'Header unit contains operative prose')
        require((a, b) not in headers, 'Duplicate header')
        headers.add((a, b))
    return text, headers


def projection(request, a, b):
    result = []
    for piece in request['source_pieces']:
        left, right = max(a, piece['start']), min(b, piece['end'])
        if left >= right:
            continue
        source = None
        if piece['raw_binding'] is not None:
            raw = piece['raw_binding']
            shift = raw['start'] - piece['start']
            source = {k: raw[k] for k in ('unit', 'document', 'source_sha256')}
            source.update(start=left + shift, end=right + shift, quote=request['text'][left:right])
        result.append({'start': left, 'end': right, 'kind': piece['kind'], 'source': source})
    return result


def discover(request):
    """Return exact mentions and raw projections, retaining unresolved destinations."""
    text, headers = validate(request)
    paragraph = paragraph_discover(text, text_sha256=request['text_sha256'])
    paragraphs = {r['start']: r for r in paragraph['candidates']}
    spans = []

    def end_section(match):
        end = match.end()
        while component := COMPONENT.match(text, end):
            end = component.end()
        intro = PARAGRAPH_INTRO.match(text, end)
        if intro:
            # Match by the actual intro start without changing literal parser output.
            p = next((r for a, r in paragraphs.items() if end <= a < intro.end()), None)
            if p:
                end = p['end']
        numbered = NUMBERED.match(text, end)
        if numbered:
            end = numbered.end()
        sentence = SENTENCE.match(text, end)
        if sentence:
            end = sentence.end()
        onward = re.match(r'\s+ff\.', text[end:])
        if onward:
            end += onward.end()
        return end

    section_matches = list(SECTION.finditer(text))
    consumed = set()
    for match in section_matches:
        if match.start() in consumed or (match.start(), match.end()) in headers:
            continue
        end = end_section(match)
        follow = re.match(r'\s+(?:bis|to|through)\s+', text[end:], re.I)
        if follow:
            other = SECTION.match(text, end + follow.end())
            if other:
                end = end_section(other)
                consumed.add(other.start())
        law = LAW_TAIL.match(text, end)
        if law:
            end = law.end()
        spans.append((match.start(), end, 'SECTION_REFERENCE'))
    for row in paragraph['candidates']:
        a, b = row['start'], row['end']
        if any(left <= a < right for left, right, _ in spans):
            continue
        qualifier = re.match(r'\s+dieses\s+', text[b:], re.I)
        if qualifier:
            other = next((s for s in spans if s[0] == b + qualifier.end()), None)
            if other:
                b = other[1]
                spans.remove(other)
        spans.append((a, b, 'PARAGRAPH_REFERENCE'))
    for pattern, kind in ((IMPLICIT, 'IMPLICIT_REFERENCE'), (IMPLICIT_LIST, 'IMPLICIT_REFERENCE'),
                          (NAMED_LAW, 'NAMED_LAW_REFERENCE'), (UNSPECIFIED, 'UNSPECIFIED_LAW_REFERENCE')):
        for match in pattern.finditer(text):
            if not any(a <= match.start() and match.end() <= b for a, b, _ in spans):
                spans.append((match.start(), match.end(), kind))
    spans = sorted(set(spans))
    require(len(spans) <= LIMITS['mentions'], 'Mention bound exceeded')
    mentions = []
    for a, b, kind in spans:
        row = {'start': a, 'end': b, 'raw': text[a:b], 'kind': kind}
        row.update(id=digest(row), source_projection=projection(request, a, b), target=None, review_required=True)
        row['raw_copy_complete'] = all(p['source'] is not None for p in row['source_projection'])
        mentions.append(row)
    issues = deepcopy(paragraph['issues'])
    for cue in SECTION_CUE.finditer(text):
        if (cue.start(), cue.end()) not in headers and not any(a <= cue.start() < b for a, b, _ in spans):
            if not any(a == cue.start() for a, _ in headers):
                issues.append({'start': cue.start(), 'end': cue.end(), 'kind': 'MALFORMED_OR_UNSUPPORTED_SECTION'})
    result = {'version': VERSION, 'text_sha256': request['text_sha256'], 'request_sha256': digest(request),
        'mentions': mentions, 'issues': issues, 'excluded_section_headers': deepcopy(request['section_headers']),
        'general_recall_established': False, 'target_resolution_established': False,
        'legal_interpretation_established': False, 'document_authenticity_established': False,
        'unsupported': ['unlisted citation grammars', 'target resolution', 'definition scope', 'legal meaning'],
        'limits': deepcopy(LIMITS)}
    return {**result, 'report_sha256': digest(result)}
