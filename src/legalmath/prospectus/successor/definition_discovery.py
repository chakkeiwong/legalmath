"""Review-only lexical proposals; no legal declarations or scope resolution."""
import hashlib
import unicodedata


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalized(text, offset):
    """A whitespace character maps to its entire original whitespace run."""
    chars, spans = [], []
    cursor = 0
    while cursor < len(text):
        end = cursor + 1
        if text[cursor].isspace():
            while end < len(text) and text[end].isspace():
                end += 1
            char = ' '
        else:
            char = text[cursor]
        chars.append(char)
        spans.append([cursor + offset, end + offset])
        cursor = end
    return ''.join(chars), spans


def attached(char):
    # Combining marks, connectors, dash compounds, possessives and slash
    # compounds cannot turn a component into a standalone literal occurrence.
    return bool(char) and (unicodedata.category(char)[0] in 'LNM' or
        unicodedata.category(char) in {'Pc', 'Pd'} or char in "\u00ad/'\u2019")


def discover(request):
    require(isinstance(request, dict), 'Request must be a mapping')
    text = request.get('text')
    require(isinstance(text, str) and 0 < len(text) <= 100000, 'Unsupported source size/type')
    identity = hashlib.sha256(text.encode()).hexdigest()
    require(request.get('text_sha256') == identity, 'Changed source identity')
    language = request.get('language')
    require(isinstance(language, str) and language, 'Missing selected language')
    regions = request.get('regions')
    require(isinstance(regions, list) and 0 < len(regions) <= 256, 'Missing/big region partition')
    cursor, ids = 0, set()
    for r in regions:
        require(isinstance(r, dict), 'Invalid region')
        require(isinstance(r.get('id'), str) and r['id'] and r['id'] not in ids, 'Invalid region identity')
        ids.add(r['id'])
        require(type(r.get('start')) is int and type(r.get('end')) is int and
                r['start'] == cursor < r['end'] <= len(text), 'Changed/nonpartitioning region offsets')
        require(type(r.get('selected')) is bool and isinstance(r.get('language'), str), 'Invalid region selection')
        cursor = r['end']
    require(cursor == len(text), 'Incomplete source partition')
    names, uses, issues, views = [], [], [], []
    for r in regions:
        if not r['selected'] or r['language'] != language:
            continue
        plain, spans = normalized(text[r['start']:r['end']], r['start'])
        views.append((r, plain, spans))
        quotes = [i for i, c in enumerate(plain) if c == '"']
        for i in range(0, len(quotes) - 1, 2):
            left, right = quotes[i] + 1, quotes[i + 1]
            while left < right and plain[left].isspace():
                left += 1
            while right > left and plain[right - 1].isspace():
                right -= 1
            if left == right:
                issues.append({'kind': 'EMPTY_ASCII_QUOTE', 'region': r['id'],
                               'start': spans[quotes[i]][0], 'end': spans[quotes[i + 1]][1]})
                continue
            a, b = spans[left][0], spans[right - 1][1]
            names.append({'id': f'q:{len(names)}:{a}:{b}', 'region': r['id'],
                'start': a, 'end': b, 'raw': text[a:b], 'label': plain[left:right],
                'quote_start': spans[quotes[i]][0], 'quote_end': spans[quotes[i + 1]][1],
                'normalization_map': spans[left:right], 'kind': 'QUOTED_LABEL_CANDIDATE',
                'review_required': True})
        if len(quotes) % 2:
            a, b = spans[quotes[-1]]
            issues.append({'kind': 'UNBALANCED_ASCII_QUOTE', 'region': r['id'], 'start': a, 'end': b})
        for i, char in enumerate(plain):
            if char in '\u201c\u201d\u201e\u00ab\u00bb\u301d\u301e':
                issues.append({'kind': 'UNSUPPORTED_QUOTE', 'region': r['id'],
                               'start': spans[i][0], 'end': spans[i][1]})
    require(len(names) <= 2048, 'Quoted candidate bound exceeded')
    labels = {}
    for name in names:
        labels.setdefault(name['label'], []).append(name['id'])
    for r, plain, spans in views:
        for label, candidates in labels.items():
            cursor = 0
            while True:
                start = plain.find(label, cursor)
                if start < 0:
                    break
                end = start + len(label)
                cursor = start + 1
                if attached(plain[start - 1] if start else '') or attached(plain[end:end + 1]):
                    continue
                a, b = spans[start][0], spans[end - 1][1]
                uses.append({'region': r['id'], 'start': a, 'end': b,
                    'raw': text[a:b], 'label': label, 'normalization_map': spans[start:end],
                    'name_candidates': list(candidates), 'kind': 'LITERAL_USE_CANDIDATE',
                    'review_required': True, 'governing_scope': None})
    order = lambda row: (row['start'], row['end'], row['label'])
    names.sort(key=order)
    uses.sort(key=order)
    return {'version': 'quoted-label-discovery.v1', 'text_sha256': identity,
            'language': language, 'names': names, 'uses': uses, 'issues': issues,
            'scope_admitted': False, 'meaning_admitted': False,
            'unsupported_mechanisms': ['unquoted declarations', 'morphology',
                'hyphen repair', 'legal scope and precedence', 'implicit definitions']}
