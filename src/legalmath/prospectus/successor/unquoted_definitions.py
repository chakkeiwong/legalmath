"""Finite unquoted definition syntax; a candidate does not admit legal meaning."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from .anchors import fields
from .contracts import digest
from .definition_discovery import normalized
from .reference_addresses import body_projection

KEY = 'unquoted_definitions'
VERSION = 'unquoted-definitions.v1'
SPEC_SHA256 = '6f8b92caf0116d99dd7a9ccabc3c625f3132553ffe595b7c026ccb96897ee95d'
WORD = r'[A-ZÄÖÜ][\wÄÖÜäöüß-]{0,80}'
PATTERNS = (
    ('PARENTHETICAL_EXPLICATION', re.compile(
        r'\bDie (?P<term>' + WORD + r') (?P<scope>der ' + WORD + r') '
        r'\(unter denen die (?P<repeat>' + WORD + r') zu verstehen sind, '
        r'(?P<value>[^()]{1,1024})\)')),
    ('REFERENCE_EXPANSION', re.compile(
        r'\bBezugnahmen (?P<scope>in diesen Anleihebedingungen) auf (?P<term>' + WORD + r') '
        r'der Schuldverschreibungen schließen, (?P<condition>soweit anwendbar), '
        r'die folgenden Beträge ein: (?P<value>[^.]{1,2048})\.')),
    ('REFERENCE_EXPANSION', re.compile(
        r'\bBezugnahmen (?P<scope>in diesen Anleihebedingungen) auf (?P<term>' + WORD + r') '
        r'auf die Schuldverschreibungen sollen, (?P<condition>soweit anwendbar), '
        r'(?P<value>[^.]{1,1024}) einschließen\.')),
    ('PURPOSE_CONDITIONED_AMOUNT', re.compile(
        r'\b(?P<scope>Für die Zwecke des Absatzes (?P<paragraph>\[\([0-9]+\)\]|\([0-9]+\)) '
        r'dieses § (?P<section>[0-9]+)),? entspricht der '
        r'(?P<term>[a-zäöüß]{1,40} ' + WORD + r') einer Schuldverschreibung '
        r'(?P<value>[^.]{1,1024})\.')),
    ('LEGISLATIVE_ALIAS', re.compile(
        r'\b(?P<value>(?:[A-ZÄÖÜ][\w-]*(?:- und [A-ZÄÖÜ][\w-]*)?gesetz(?:es)?|'
        r'Gesetz(?:es)? zur [^().;]{1,180})) \((?P<term>' + WORD + r')\)')),
)
CUES = re.compile(r'\b(?:unter denen|Bezugnahmen|Für die Zwecke|Gesetz(?:es)? zur)\b')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def discover(request):
    fields(request, {'text', 'text_sha256', 'language', 'regions'},
           {'text', 'text_sha256', 'language', 'regions'})
    text, language, regions = (request[k] for k in ('text', 'language', 'regions'))
    require(isinstance(text, str) and 0 < len(text) <= 100000, 'Bounded unquoted source required')
    require(hashlib.sha256(text.encode()).hexdigest() == request['text_sha256'], 'Changed unquoted source')
    require(language == 'de', 'Unsupported unquoted definition language')
    require(isinstance(regions, list) and 0 < len(regions) <= 256, 'Bounded region partition required')
    cursor, identities = 0, set()
    for region in regions:
        fields(region, {'id', 'start', 'end', 'selected', 'language'},
               {'id', 'start', 'end', 'selected', 'language'})
        require(isinstance(region['id'], str) and region['id'] and region['id'] not in identities,
                'Repeated/invalid unquoted region identity')
        identities.add(region['id'])
        require(type(region['start']) is int and type(region['end']) is int
                and region['start'] == cursor < region['end'] <= len(text), 'Invalid region partition')
        require(type(region['selected']) is bool and isinstance(region['language'], str), 'Invalid region selection')
        cursor = region['end']
    require(cursor == len(text), 'Incomplete region partition')
    candidates, issues = [], []
    for region in regions:
        if not region['selected'] or region['language'] != language:
            continue
        # Blank paragraphs cannot become invisible whitespace during matching.
        boundaries = [region['start']]
        for match in re.finditer(r'(?:\r?\n)[ \t]*(?:\r?\n)', text[region['start']:region['end']]):
            boundaries.extend((region['start'] + match.start(), region['start'] + match.end()))
        boundaries.append(region['end'])
        for a, b in zip(boundaries[::2], boundaries[1::2]):
            if a == b:
                continue
            plain, spans = normalized(text[a:b], a)
            covered = []
            for kind, pattern in PATTERNS:
                for match in pattern.finditer(plain):
                    if 'repeat' in match.groupdict() and match['repeat'] != match['term']:
                        continue
                    def span(group):
                        x, y = match.span(group)
                        return {'start': spans[x][0], 'end': spans[y - 1][1],
                                'raw': text[spans[x][0]:spans[y - 1][1]]}
                    x, y = match.span()
                    row = {'kind': kind, 'start': spans[x][0], 'end': spans[y - 1][1],
                        'raw': text[spans[x][0]:spans[y - 1][1]], 'region': region['id'],
                        'label': match['term'], 'term': span('term'), 'value': span('value'),
                        'scope': span('scope') if 'scope' in match.groupdict() else None,
                        'condition': span('condition') if 'condition' in match.groupdict() else None,
                        'printed_scope_address': {'section': match['section'],
                            'paragraph': match['paragraph'].strip('[]()')}
                            if 'paragraph' in match.groupdict() else None,
                        'governing_scope': None, 'meaning': None, 'review_required': True,
                        'legal_meaning_established': False}
                    candidates.append(row)
                    covered.append((x, y))
                    require(len(candidates) <= 1024, 'Unquoted candidate bound exceeded')
            for match in CUES.finditer(plain):
                if not any(x <= match.start() < y for x, y in covered):
                    issues.append({'kind': 'UNSUPPORTED_DEFINITION_CUE', 'start': spans[match.start()][0],
                        'end': spans[match.end() - 1][1], 'raw': text[spans[match.start()][0]:spans[match.end() - 1][1]],
                        'region': region['id']})
                    require(len(issues) <= 2048, 'Unquoted issue bound exceeded')
    candidates.sort(key=lambda row: (row['start'], row['end'], row['kind']))
    require(len({(r['start'], r['end']) for r in candidates}) == len(candidates), 'Ambiguous unquoted syntax')
    return {'version': VERSION, 'text_sha256': request['text_sha256'], 'language': language,
        'candidates': candidates, 'issues': issues, 'scope_admitted': False, 'meaning_admitted': False,
        'general_recall_established': False, 'automatic_legal_interpretation': False,
        'unsupported': ['unlisted syntax', 'appointments', 'tables', 'implicit definitions',
                        'morphology', 'legal precedence and governing use scope']}


def content(products, ordinary):
    assembly = products['P2']['payload']['assembly']
    text = assembly['continuous_text']
    result = discover({'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'language': 'de', 'regions': [{'id': 'selected-contract', 'start': 0, 'end': len(text),
                                     'selected': True, 'language': 'de'}]})
    pieces = ordinary['definition_sources']['source_pieces']
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    for row in result['candidates']:
        for part in (row, row['term'], row['scope'], row['value'], row['condition']):
            if part is not None:
                part['source_projection'] = body_projection(text, pieces, raw, assembly['operations'],
                                                            part['start'], part['end'])
    return {**result, 'prior_answer_preserved': True, 'original_records_preserved': True,
            'whole_task_complete': False, 'legal_truth_established': False}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'specification_sha256',
            'whole_task_complete', 'legal_truth_established'}
    fields(profile, keys, keys)
    spec = json.loads(Path(__file__).with_name('unquoted_definitions_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec) == SPEC_SHA256, 'Unquoted specification differs')
    require(profile['version'] == VERSION and digest(profile) == expected_profile_sha256
        and profile['specification_sha256'] == SPEC_SHA256
        and profile['products_sha256'] == digest(products) == spec['products_sha256']
        and profile['ordinary_answer_sha256'] == digest(ordinary) == spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256') == digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False, 'Pinned unquoted baseline differs')
    return {KEY: {'profile_sha256': digest(profile), 'products_sha256': digest(products),
                  'ordinary_answer_sha256': digest(ordinary), **content(products, ordinary)}}
