"""Exact retained Q1 statement coverage under the fourth BES supplement."""
from .contracts import digest
from .occurrences import anchor, segments

PROFILE='bes-q12011-statement-scope.v1'
INTRO='4a5cf216f46148a0dd1c37ed72b0b13f77e7df20dae1d6705f167a7a9ba313c2'
RELEASE='4c7067274ff3eb8f812a8a98d23c4fd2d4b159ed0259f066069b2416ae2e75ec'
PAGES={
    (INTRO,1):(41,'f8d8d75f6c0e577d889d3bc7a8e957e1486a430f8a3c44dd0524bc072ae16fc9'),
    (INTRO,3):(43,'c687593025e9d4a196e3f91b27c9eec45bd8563916bb0adcd6fd209bd1b49834'),
    (RELEASE,1):(57,'2aeda49aceb52990aca167258c9561b494a8faea01bfe44e9eeb034e92c754b9'),
    (RELEASE,36):(206,'c67d5097830d9d03eb3f06d5914b498cbdd621944e0592cfc033a9d23f088a97'),
    (RELEASE,37):(93,'305b36b20ba7469a97f31f652b863b10b9599f7858e5de794fa95c3bf150427e'),
}


def _page(raw,document,source,page):
    rows=sorted((u for u in raw.values() if u['document']==document and u['page']==page),key=lambda u:u['order'])
    count,expected=PAGES[(source,page)]
    if (len(rows)!=count or {u['order'] for u in rows}!=set(range(count)) or
            any(not u.get('visible') or u['source_sha256']!=source or u['language']!='en' or
                u['text_sha256']!=digest(u['raw'].encode()) for u in rows) or
            digest('\n'.join(u['raw'] for u in rows).encode())!=expected):
        raise ValueError('Q1 statement scope requires complete unchanged original page units')
    return rows


def check(graph,assembly,row):
    raw={u['id']:u for u in graph['units']}
    referring=raw.get(row['source']['unit'])
    # The shared purpose paragraph also names the annual Bank/BES Finance
    # accounts. Only the Q1-specific clause and table select this profile.
    if not referring or (referring['source_sha256'],referring['page'])!=(INTRO,3):
        return None
    third=_page(raw,referring['document'],INTRO,3)
    if referring['id'] not in {u['id'] for u in third[25:38]}:
        return None
    first=_page(raw,referring['document'],INTRO,1)
    if len(raw)!=len(graph['units']) or row['form']!='external':
        raise ValueError('Q1 statement scope requires unique occurrences and external source role')
    docs={u['document'] for u in raw.values() if u['source_sha256']==RELEASE}
    if len(docs)!=1:
        raise ValueError('Q1 statement scope requires the unique retained release edition')
    document,=docs
    cover=_page(raw,document,RELEASE,1)
    targets=_page(raw,document,RELEASE,36)+_page(raw,document,RELEASE,37)
    selected={u['unit']:u for u in assembly['units']}
    if len(selected)!=len(assembly['units']):
        raise ValueError('Q1 statement scope requires unique selected occurrences')
    for unit in first[22:31]+third[25:38]+targets:
        found=selected.get(unit['id'])
        if (found is None or found['role']!='OPERATIVE' or found['text']!=unit['raw'] or
                not set(row['questions'])<=set(found['questions']) or
                segments(graph,found,_raw=raw)!=[{'source':anchor(unit),'start':0,'end':len(unit['raw'])}]):
            raise ValueError('Q1 statement scope needs unchanged operative clause, restriction and targets')
    expected={u['id']:u for u in targets}; supplied=row['targets']
    if not isinstance(supplied,list) or len(supplied)!=len(expected):
        raise ValueError('Q1 statement scope requires all299 target units exactly once')
    seen=set()
    for value in supplied:
        source=value.get('source',{}); identity=source.get('unit')
        if (identity not in expected or identity in seen or value.get('use')!=identity or
                value.get('language')!='en' or source!=anchor(expected[identity])):
            raise ValueError('Q1 statement scope target omitted, duplicated, partial or outside selected pages')
        seen.add(identity)
    return {'profile':PROFILE,'status':'COMPLETE_RETAINED_PAGE_TARGETS','target_units':len(targets),
            'source_sha256':RELEASE,'pages':[36,37],
            'page_text_sha256':{str(p):PAGES[(RELEASE,p)][1] for p in (36,37)},
            'source_clause':[anchor(u) for u in third[25:29]+third[31:38]],
            'restriction':[anchor(u) for u in third[29:31]],
            'release_identity_and_qualification':[anchor(u) for u in cover[:5]],
            'context_pages_do_not_expand_incorporation':True,'source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','independent_legal_acceptance':False,
            'limit':'Exact retained Q1 pages under supplied dispositions; no general recognition, historical authority or financial-truth conclusion'}
