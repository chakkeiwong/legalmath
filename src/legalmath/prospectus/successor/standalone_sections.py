"""Explicit standalone section syntax with source-bound structural destinations."""
from copy import deepcopy
import json,re
from pathlib import Path
from .contracts import digest
from .anchors import fields
from .reference_scope import require,current_headers,projection
from .reference_addresses import body_projection

KEY='standalone_sections'
VERSION='standalone-sections.v1'
SPEC_SHA256 = 'fe79a981e645b932ed10fa986eeb7801d481e40333bf8261dd304071aa185586'
SIGN=re.compile(r'(?<!§)(?P<sign>§{1,2})[ \t\r\n]*(?P<number>[0-9]+)(?![0-9A-Za-z])')
ONWARD=re.compile(r'\s+ff\.')
CHAIN=re.compile(r'\s+und\s+(?=§)')
LAW=re.compile(r'\s+(?:des\s+)?(?P<law>Aktiengesetz(?:es)?|AktG|SchVG|BGB|WpHG|WpÜG)(?=\s|[.,;:)]|$)')

def parse(text,start):
    require(isinstance(text,str) and 0<len(text)<=100000 and type(start) is int,'Bounded section text required')
    position=start;members=[];issues=[]
    while True:
        match=SIGN.match(text,position)
        require(match is not None,'Invalid section start')
        end=match.end();onward=ONWARD.match(text,end)
        if onward:end=onward.end()
        number=match.group('number')
        if number!='0' and number.startswith('0'):issues.append('NONCANONICAL_NUMBER')
        members.append({'start':match.start(),'end':end,'sign':match.group('sign'),
            'number':number,'onward_scope':onward is not None,'raw':text[match.start():end]})
        require(len(members)<=16,'Section chain exceeds bound')
        connector=CHAIN.match(text,end)
        if connector:
            if SIGN.match(text,connector.end()) is None:
                issues.append('INCOMPLETE_CHAIN');break
            position=connector.end();continue
        break
    law=LAW.match(text,end);statute=None
    if law:
        printed=law.group('law');statute='AktG' if printed.startswith('Aktiengesetz') else printed
        end=law.end()
    elif re.match(r'\s+(?:des\s+[A-ZÄÖÜ]|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß]*(?:gesetz|gesetzes)|Absatz\b)',text[end:]):
        issues.append('UNRECOGNIZED_QUALIFIER')
    if any(m['sign']=='§§' or m['onward_scope'] for m in members) and statute is None:
        issues.append('ONWARD_OR_PLURAL_SCOPE_UNRESOLVED')
    if len(members)>1 and statute is None:issues.append('CHAIN_SCOPE_UNRESOLVED')
    return {'start':start,'end':end,'raw':text[start:end],'members':members,'statute':statute,
        'onward_scope':any(m['onward_scope'] for m in members),'issues':issues}

def discover(text,headers,paragraph_contexts):
    signs=[];groups=[];consumed_until=-1
    for match in SIGN.finditer(text):
        row={'start':match.start(),'end':match.end(),'raw':match.group()}
        if any(h['start']<=match.start()<h['end'] for h in headers):
            row['classification']='SECTION_HEADER'
        elif any(c['start']<=match.start()<c['end'] for c in paragraph_contexts):
            row['classification']='PARAGRAPH_CONTEXT'
        else:
            row['classification']='STANDALONE_EXPRESSION'
            if match.start()>=consumed_until:
                group=parse(text,match.start());groups.append(group);consumed_until=group['end']
            row['expression_start']=groups[-1]['start']
        signs.append(row)
        require(len(signs)<=2048,'Section sign bound exceeded')
    return signs,groups

def section_index(products,ordinary):
    assembly=products['P2']['payload']['assembly'];text=assembly['continuous_text']
    units={u['unit']:u for u in assembly['units']}
    raw={u['id']:u for u in products['P1']['payload']['graph']['units']}
    pieces=ordinary['definition_sources']['source_pieces']
    headers=current_headers(text,pieces,units,raw);sections=[]
    for h in headers:
        end=min((other['start'] for other in headers if other['start']>h['start']),default=len(text))
        sources=body_projection(text,pieces,raw,assembly['operations'],h['start'],end)
        sections.append({**deepcopy(h),'end':end,'heading_end':h['end'],
            'text_sha256':digest(text[h['start']:end].encode()),'source_projection':sources,
            'unknown_source_units':sorted({s['source']['unit'] for s in sources
                if s['source'] and units[s['source']['unit']]['role']=='UNKNOWN'}),
            'legal_meaning_established':False})
    return text,pieces,raw,headers,sections

def resolve(expression,header,sections):
    if expression['issues']:
        return {'status':'UNRESOLVED','section':None,'targets':[]}
    if expression['statute']:
        return {'status':'EXTERNAL_STATUTE','section':None,'targets':[]}
    if header is None or len(expression['members'])!=1:
        return {'status':'UNRESOLVED','section':None,'targets':[]}
    member=expression['members'][0]
    matches=[s for s in sections if s['section']==member['number'] and s['document']==header['document']
             and s['context']==header['context']]
    if len(matches)!=1:return {'status':'UNRESOLVED','section':None,'targets':[]}
    return {'status':'STRUCTURAL_SECTION','section':member['number'],'targets':deepcopy(matches)}

def content(products,ordinary):
    text,pieces,raw,headers,sections=section_index(products,ordinary)
    signs,groups=discover(text,headers,ordinary['reference_scope_context']['contexts'])
    units={u['unit']:u for u in products['P2']['payload']['assembly']['units']}
    rows=[]
    for expression in groups:
        mapped=projection(text,pieces,raw,expression['start'],expression['end'])
        contexts={(p['source']['document'],units[p['source']['unit']]['context']) for p in mapped if p['source']}
        applicable=[h for h in headers if h['start']<expression['start'] and (h['document'],h['context']) in contexts]
        header=max(applicable,key=lambda h:h['start']) if len(contexts)==1 and applicable else None
        rows.append({**expression,**resolve(expression,header,sections),'source_projection':mapped,
            'enclosing_header':deepcopy(header),'review_required':True,
            'legal_meaning_established':False,'historical_application_established':False})
    return {'signs':signs,'references':rows,'section_index':sections,'prior_answer_preserved':True,
        'original_semantic_targets_preserved':True,'whole_task_complete':False,'legal_truth_established':False,
        'general_recall_established':False,'automatic_legal_interpretation':False,
        'remaining':['unlisted citation grammar','implicit anaphora','historical editions and onward scope',
                     'semantic subsets','definition discovery','original source-to-answer acceptance']}

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys)
    spec=json.loads(Path(__file__).with_name('standalone_sections_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec)==SPEC_SHA256,'Standalone section specification differs')
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256
        and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False and profile['legal_truth_established'] is False,
        'Pinned standalone section baseline differs')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
                 'ordinary_answer_sha256':digest(ordinary),**content(products,ordinary)}}
