"""Printed citation qualifiers and source context; no automatic legal targets."""
from copy import deepcopy
import json,re
from pathlib import Path
from .anchors import fields
from .contracts import digest

VERSION='reference-scope-context.v1'
KEY='reference_scope_context'
SPEC_SHA256 = 'f579d85e624891819005910a2b39909038d6d78d555e13fd4b98aaf727e1d321'
PREFIX=re.compile(r'§[ \t]*([0-9]+)[ \t]*(?:\r?\n[ \t]*)?\Z')
SUFFIX=re.compile(r'\s+dieses\s+§[ \t]*([0-9]+)\b',re.I)
LAW=re.compile(r'(?:\s+Satz\s+[0-9]+)?(?:,\s*Nr\.\s*[0-9]+\s+bis\s+Nr\.\s*[0-9]+)?'
    r'\s+(?:des\s+)?(?P<law>Wertpapiererwerbs-\s+und\s+Übernahmegesetzes(?:\s+\(WpÜG\))?'
    r'|Wertpapierhandelsgesetzes|SchVG|BGB)(?=\s|[.,;:)]|\Z)',re.I)
HEADER=re.compile(r'§\s*([0-9]+)\Z')

def require(condition,message):
    if not condition:raise ValueError(message)

def qualify(text,candidate,section_headers=()):
    require(isinstance(text,str) and 0<len(text)<=100000,'Bounded source required')
    a,b=candidate['start'],candidate['end']
    require(type(a) is int and type(b) is int and 0<=a<b<=len(text)
        and candidate['raw']==text[a:b],'Paragraph source interval differs')
    issues=[] if candidate['syntax_complete'] is True else ['INCOMPLETE_PARAGRAPH']
    prefix=PREFIX.search(text[:a]);suffix=SUFFIX.match(text,b)
    left=prefix.group(1) if prefix else None
    right=suffix.group(1) if suffix else None
    start=prefix.start() if prefix else a
    end=suffix.end() if suffix else b
    explicit=left or right
    if left and right and left!=right:
        issues.append('CONFLICTING_SECTION_QUALIFIERS');explicit=None
    if prefix and any(h['start']<=prefix.start()<h['end'] for h in section_headers):
        issues.append('SECTION_HEADER_IS_NOT_CITATION');explicit=None
    law=LAW.match(text,end);statute=None
    if law:
        printed=law.group('law')
        folded=printed.casefold()
        statute=('WpÜG' if folded.startswith('wertpapiererwerbs') else
            'WpHG' if folded=='wertpapierhandelsgesetzes' else
            'SchVG' if folded=='schvg' else 'BGB')
        end=law.end()
        if explicit is None:issues.append('STATUTE_WITHOUT_SECTION')
    elif re.match(r'\s+(?:des\s+[A-ZÄÖÜ]|Satz\s|,\s*Nr\.)',text[end:]):
        issues.append('UNRECOGNIZED_SUFFIX')
    kind='EXPLICIT_STATUTE' if statute else ('EXPLICIT_SECTION' if explicit else 'RELATIVE_PARAGRAPH')
    if 'CONFLICTING_SECTION_QUALIFIERS' in issues or 'SECTION_HEADER_IS_NOT_CITATION' in issues:
        kind='AMBIGUOUS_QUALIFIER'
    return {'paragraph_start':a,'start':start,'end':end,'raw':text[start:end],
        'explicit_section':explicit,'statute':statute,'scope_kind':kind,'issues':issues,
        'target':None,'target_resolution_established':False,'review_required':True,
        'prefix_section':left,'suffix_section':right}

def projection(text,pieces,raw_units,start,end):
    out=[];position=start
    for index,p in enumerate(pieces):
        a,b=max(p['start'],start),min(p['end'],end)
        if a>=b:continue
        require(a==position,'Citation projection has a gap or overlap')
        source=p.get('raw_binding');anchor=None
        if source is None:
            require(p['kind']=='GENERATED_SEPARATOR' and text[a:b].isspace(),
                'Citation has unbound non-separator text')
        else:
            require(p['end']-p['start']==source['end']-source['start'],'Citation source lengths differ')
            delta=source['start']-p['start']
            anchor={k:source[k] for k in ('unit','document','source_sha256')}
            anchor.update(start=a+delta,end=b+delta,quote=text[a:b])
            u=raw_units.get(anchor['unit'])
            require(u is not None and u['document']==anchor['document']
                and u['source_sha256']==anchor['source_sha256']
                and u['raw'][anchor['start']:anchor['end']]==anchor['quote'],
                'Citation raw-source projection differs')
        out.append({'piece_index':index,'selected_start':a,'selected_end':b,
            'text':text[a:b],'kind':p['kind'],'source':anchor})
        position=b
    require(position==end,'Citation projection incomplete')
    return out

def current_headers(text,pieces,units,raw_units):
    headers=[]
    for p in pieces:
        source=p.get('raw_binding')
        if not source:continue
        u=units.get(source['unit'])
        if u is None or u['role']!='HEADER':continue
        match=HEADER.fullmatch(u['text'])
        if not match:continue
        raw=raw_units.get(u['unit'])
        require(raw is not None and source['unit']==u['unit']
            and source['document']==raw['document']==u['source']['document']
            and raw['page']==u['source']['page']
            and source['source_sha256']==raw['source_sha256']
            and source['start']==0 and source['end']==len(raw['raw'])
            and source['quote']==raw['raw']==u['text']==p['text']
            and text[p['start']:p['end']]==u['text']
            and u['original_sha256']==raw['text_sha256']==digest(raw['raw'].encode()),
            'Current section header source differs')
        if 'character_map' in u:
            maps=u['character_map']
            require(len(maps)==1 and maps[0]['start']==0 and maps[0]['end']==len(u['text'])
                and all(maps[0].get('source',{}).get(k)==source[k]
                    for k in ('unit','document','source_sha256','start','end','quote')),
                'Current section header map differs')
        headers.append({'start':p['start'],'end':p['end'],'section':match.group(1),
            'unit':u['unit'],'context':u['context'],'document':u['source']['document']})
    require(len({h['start'] for h in headers})==len(headers),'Duplicate section context')
    return headers

def content(products,ordinary):
    assembly=products['P2']['payload']['assembly'];text=assembly['continuous_text']
    raw_units={u['id']:u for u in products['P1']['payload']['graph']['units']}
    units={u['unit']:u for u in assembly['units']}
    pieces=ordinary['definition_sources']['source_pieces']
    headers=current_headers(text,pieces,units,raw_units)
    refs=products['P3']['payload']['interpretation_input']['reference_admission']['references']
    rows=[]
    for candidate in ordinary['paragraph_reference_discovery']['discovery']['candidates']:
        row=qualify(text,candidate,headers)
        contexts={(use['context'],p['raw_binding']['document']) for p in pieces
            if p.get('raw_binding') and p['start']<candidate['end'] and candidate['start']<p['end']
            for use in p['assembly_uses']}
        enclosing=[h for h in headers if h['start']<candidate['start']
            and (h['context'],h['document']) in contexts]
        selected_header=max(enclosing,key=lambda h:h['start']) if len(contexts)==1 and enclosing else None
        row['enclosing_section']=selected_header['section'] if selected_header else None
        row['enclosing_header']=deepcopy(selected_header)
        row['enclosing_section_resolves_target']=False
        row['source_projection']=projection(text,pieces,raw_units,row['start'],row['end'])
        matches=[]
        for reference in refs:
            s=reference['source']
            if any(p['source'] and all(p['source'][k]==s[k] for k in ('unit','document','source_sha256'))
                and p['source']['start']<s['end'] and s['start']<p['source']['end']
                for p in row['source_projection']):matches.append(reference['id'])
        row['overlapping_reviewed_references']=matches
        row['overlap_establishes_target']=False
        rows.append(row)
    return {'contexts':rows,'section_headers':headers,'prior_answer_preserved':True,
        'target_resolution_established':False,'whole_task_complete':False,
        'automatic_legal_interpretation':False,'general_recall_established':False,
        'unresolved':['legal target selection','parent inheritance','range expansion',
            'implicit anaphora','historical statute validity','unlisted qualifier grammar']}

def specification():
    spec=json.loads(Path(__file__).with_name('reference_scope_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec)==SPEC_SHA256,'Citation specification differs')
    return spec

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False
        and profile['legal_truth_established'] is False,'Pinned citation baseline differs')
    result=content(products,ordinary)
    actual=[{k:r[k] for k in wanted} for r,wanted in zip(result['contexts'],spec['source_contexts'])]
    require(len(result['contexts'])==len(spec['source_contexts']) and actual==spec['source_contexts']
        and all(not r['issues'] for r in result['contexts']),'Frozen citation context differs')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),
        'products_sha256':digest(products),'ordinary_answer_sha256':digest(ordinary),**result}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    expected={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    require(actual==expected,'Complete citation-context answer differs')
    return {'status':'PASS','whole_answer_equal':True,'target_resolution_established':False}
