"""Conditional page coverage for the retained March2011 BES supplement.

Original evidence: source-bes-dep-08/001 and006. This finite rule checks the
inspected edition and supplied selection; it does not authenticate the source.
"""
from .contracts import digest
from .occurrences import anchor, segments

PROFILE = 'bes-fy2010-statement-scope.v1'
INTRO = 'f30984751f4f2e7a2cb3a6729ccd3eb3fe67e50784282ea33be437551b4d1fd1'
RELEASE = 'b28420dced99cbb219a3f447ed43fa603d6ae1bc0086fb7705876e25631a569f'
PAGES = {
    (INTRO, 1): (40, '687ebcb432582ed351804dba366b724c44761360472c7851c45a9c33605a33c2'),
    (INTRO, 2): (47, 'e0b880e83265212fac76869577b1232dd48c906b0fd95585b71e721dcd9aac2b'),
    (RELEASE, 1): (59, '92a0b312178cec0eeb8898993f31bced45091342ceafda63a91b323e13c6e0b8'),
    (RELEASE, 41): (206, 'cff41cdb6c87f858e55342612cc23e5c48c4b980cfbe71c71c0bd33b23497fef'),
    (RELEASE, 42): (94, '75ed8354aa4830355b73a84416a0911b76e0dad06a181ad4cef399477dde34be'),
}
# Source order in the authenticated retained page inventory, not arbitrary line
# numbers in a new edition. Whole-page checks below precede use of these indices.
CLAUSE = {1: (22, 23, 24, 25, 33, 34, 35, 36), 2: (0, 1, 2, 3, 8, 9, 10)}
RESTRICTION = (37, 38)


def _page(raw, document, source, page):
    rows = sorted((u for u in raw.values() if u['document'] == document and u['page'] == page),
                  key=lambda u: u['order'])
    count, expected = PAGES[(source, page)]
    if (len(rows) != count or {u['order'] for u in rows} != set(range(count)) or
            any(not u.get('visible') or u['source_sha256'] != source or u['language'] != 'en' or
                u['text_sha256'] != digest(u['raw'].encode()) for u in rows) or
            digest('\n'.join(u['raw'] for u in rows).encode()) != expected):
        raise ValueError('FY2010 statement scope requires complete unchanged original page units')
    return rows


def check(graph, assembly, row):
    raw = {u['id']: u for u in graph['units']}
    referring = raw.get(row['source']['unit'])
    if not referring or referring['source_sha256'] != INTRO or referring['page'] not in CLAUSE:
        return None
    first = _page(raw, referring['document'], INTRO, 1)
    second = _page(raw, referring['document'], INTRO, 2)
    clause = [first[i] for i in CLAUSE[1]] + [second[i] for i in CLAUSE[2]]
    restriction = [first[i] for i in RESTRICTION]
    if referring['id'] not in {u['id'] for u in clause + restriction}:
        return None
    if len(raw) != len(graph['units']) or row['form'] != 'external':
        raise ValueError('FY2010 statement scope requires unique occurrences and external source role')
    docs = {u['document'] for u in raw.values() if u['source_sha256'] == RELEASE}
    if len(docs) != 1:
        raise ValueError('FY2010 statement scope requires the unique retained release edition')
    document, = docs
    cover = _page(raw, document, RELEASE, 1)
    targets = _page(raw, document, RELEASE, 41) + _page(raw, document, RELEASE, 42)
    selected = {u['unit']: u for u in assembly['units']}
    if len(selected) != len(assembly['units']):
        raise ValueError('FY2010 statement scope requires unique selected occurrences')
    for unit in clause + restriction + targets:
        found = selected.get(unit['id'])
        if (found is None or found['role'] != 'OPERATIVE' or found['text'] != unit['raw'] or
                not set(row['questions']) <= set(found['questions']) or
                segments(graph, found, _raw=raw) != [{'source': anchor(unit), 'start': 0, 'end': len(unit['raw'])}]):
            raise ValueError('FY2010 statement scope needs unchanged operative clause, restriction and targets')
    expected = {u['id']: u for u in targets}
    supplied = row['targets']
    if not isinstance(supplied, list) or len(supplied) != len(expected):
        raise ValueError('FY2010 statement scope requires all300 target units exactly once')
    seen = set()
    for value in supplied:
        source = value.get('source', {})
        identity = source.get('unit')
        if (identity not in expected or identity in seen or value.get('use') != identity or
                value.get('language') != 'en' or source != anchor(expected[identity])):
            raise ValueError('FY2010 statement scope target omitted, duplicated, partial or outside selected pages')
        seen.add(identity)
    return {'profile': PROFILE, 'status': 'COMPLETE_RETAINED_PAGE_TARGETS',
            'target_units': len(targets), 'source_sha256': RELEASE, 'pages': [41, 42],
            'page_text_sha256': {str(p): PAGES[(RELEASE, p)][1] for p in (41, 42)},
            'source_clause': [anchor(u) for u in clause], 'restriction': [anchor(u) for u in restriction],
            'release_identity_and_qualification': [anchor(u) for u in cover[:5]],
            'context_pages_do_not_expand_incorporation': True,
            'source_authenticity': 'NOT_ESTABLISHED', 'incorporation_status': 'UNRESOLVED',
            'independent_legal_acceptance': False,
            'limit': 'Exact retained source pages under supplied dispositions; no general recognition, historical authority or financial-truth conclusion'}
