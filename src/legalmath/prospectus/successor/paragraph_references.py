"""Literal German paragraph-expression proposals; no automatic target resolution."""
from copy import deepcopy
import json,re
from pathlib import Path
from .anchors import fields
from .contracts import digest

VERSION='paragraph-reference-discovery.v1'
KEY='paragraph_reference_discovery'
SPEC_SHA256 = '867d741eb12c17e9a1cf0f68988eaae1dfb64c848e21159f8cb4adb508012b42'
INTRO=re.compile(r'\b(?:Unterabsätzen|Absatzes|Absatz)\b',re.I)
LABEL=re.compile(r'(?:[0-9]+|[A-Za-z]|[ivxlcdm]+)\Z',re.I)
CONNECTOR=re.compile(r'(?:und/oder|und|oder|bis)\b|,',re.I)
LIMITS={'characters':100000,'candidates':2048,'components':64}

def require(condition,message):
    if not condition:raise ValueError(message)

def _space(text,pos):
    while pos<len(text) and text[pos].isspace():pos+=1
    return pos

def _label(text,pos,*,bare):
    if pos>=len(text):return None
    start=pos;char=text[pos]
    if char=='[':
        end=text.find(']',pos+1)
        if end<0 or end-pos>24:return None
        value=text[pos+1:end].strip()
        if value.startswith('(') and value.endswith(')'):value=value[1:-1].strip()
        if not LABEL.fullmatch(value):return None
        return value,start,end+1
    if char=='(':
        end=text.find(')',pos+1)
        if end<0 or end-pos>24:return None
        value=text[pos+1:end].strip()
        if not LABEL.fullmatch(value):return None
        return value,start,end+1
    if not bare:return None
    end=pos
    while end<len(text) and text[end].isalnum():end+=1
    value=text[pos:end]
    if not value.isascii() or not value.isdigit():return None
    return value,start,end

def discover(text,*,text_sha256):
    require(isinstance(text,str) and 0<len(text)<=LIMITS['characters'],'Bounded nonempty source text required')
    require(digest(text.encode())==text_sha256,'Source text identity differs')
    candidates=[];issues=[]
    for intro in INTRO.finditer(text):
        require(len(candidates)<LIMITS['candidates'],'Paragraph candidate bound exceeded')
        position=_space(text,intro.end());first=_label(text,position,bare=True)
        if first is None:
            issues.append({'start':intro.start(),'end':max(position,intro.end()),'kind':'MALFORMED_OR_UNSUPPORTED_LABEL'})
            continue
        value,a,end=first;paths=[[value]];tokens=[{'start':a,'end':end,'raw':text[a:end],'value':value}]
        connectors=[];complete=True
        while True:
            position=_space(text,end)
            if position<len(text) and text[position] in '([':
                component=_label(text,position,bare=False)
                if component is None:
                    issues.append({'start':intro.start(),'end':position+1,'kind':'MALFORMED_OR_UNSUPPORTED_LABEL'});complete=False;break
                value,a,end=component;paths[-1].append(value);tokens.append({'start':a,'end':end,'raw':text[a:end],'value':value})
            else:
                connector=CONNECTOR.match(text,position)
                if connector is None:break
                next_start=_space(text,connector.end());component=_label(text,next_start,bare=True)
                if component is None:
                    # A comma can terminate a citation before another prose phrase.
                    if connector.group()==',' and (next_start>=len(text) or text[next_start] not in '(['):break
                    issues.append({'start':intro.start(),'end':connector.end(),'kind':'INCOMPLETE_LIST'});complete=False;break
                connectors.append(connector.group().lower());value,a,end=component;paths.append([value])
                tokens.append({'start':a,'end':end,'raw':text[a:end],'value':value})
            require(len(tokens)<=LIMITS['components'],'Paragraph component bound exceeded')
        candidates.append({'start':intro.start(),'end':end,'raw':text[intro.start():end],
            'paths':paths,'connectors':connectors,'tokens':tokens,'syntax_complete':complete,
            'kind':'PARAGRAPH_EXPRESSION_CANDIDATE','review_required':True,'target':None})
    return {'version':VERSION,'text_sha256':text_sha256,'candidates':candidates,'issues':issues,
        'general_recall_established':False,'target_resolution_established':False,
        'unsupported':['implicit anaphora','target resolution','parent inheritance','range expansion','unlisted citation grammars'],
        'limits':deepcopy(LIMITS)}

def specification():
    spec=json.loads(Path(__file__).with_name('paragraph_references_spec.json').read_text())
    require(SPEC_SHA256 is not None and digest(spec)==SPEC_SHA256,'Registered paragraph specification differs')
    return spec

def content(products,ordinary):
    text=products['P2']['payload']['assembly']['continuous_text']
    report=discover(text,text_sha256=digest(text.encode()))
    pieces=ordinary['definition_sources']['source_pieces']
    refs=products['P3']['payload']['interpretation_input']['reference_admission']['references']
    rows=[]
    for candidate in report['candidates']:
        source_pieces=[];matches=[]
        for i,piece in enumerate(pieces):
            a,b=max(piece['start'],candidate['start']),min(piece['end'],candidate['end'])
            if a<b:
                clipped=None;raw=piece.get('raw_binding')
                if raw and raw.get('unit') and piece['end']-piece['start']==raw['end']-raw['start']:
                    left,right=a-piece['start'],b-piece['start']
                    clipped={k:deepcopy(raw[k]) for k in ('unit','document','source_sha256')}
                    clipped.update(start=raw['start']+left,end=raw['start']+right,quote=raw['quote'][left:right])
                    require(clipped['quote']==text[a:b],'Paragraph source projection differs')
                source_pieces.append({'index':i,'piece':deepcopy(piece),'selected_start':a,'selected_end':b,'clipped_source':clipped})
        require(source_pieces,'Paragraph expression lacks retained source projection')
        for reference in refs:
            s=reference['source']
            for row in source_pieces:
                raw=row['clipped_source']
                if raw and raw.get('unit')==s['unit'] and max(raw['start'],s['start'])<min(raw['end'],s['end']):
                    matches.append(reference['id']);break
        rows.append({**candidate,'source_pieces':source_pieces,'overlapping_reviewed_references':matches,
            'overlap_establishes_target':False})
    return {'discovery':report,'source_candidates':rows,'candidate_count':len(rows),
        'prior_answer_preserved':True,'target_resolution_established':False,
        'automatic_legal_interpretation':False,'whole_task_complete':False}

def evaluate(products,ordinary,profile,root,*,expected_profile_sha256):
    keys={'version','products_sha256','ordinary_answer_sha256','specification_sha256','whole_task_complete','legal_truth_established'}
    fields(profile,keys,keys);spec=specification()
    require(profile['version']==VERSION and digest(profile)==expected_profile_sha256
        and profile['specification_sha256']==SPEC_SHA256 and profile['products_sha256']==digest(products)==spec['products_sha256']
        and profile['ordinary_answer_sha256']==digest(ordinary)==spec['ordinary_answer_sha256']
        and ordinary.get('report_sha256')==digest({k:v for k,v in ordinary.items() if k!='report_sha256'})
        and KEY not in ordinary and profile['whole_task_complete'] is False and profile['legal_truth_established'] is False,
        'Pinned paragraph baseline differs')
    result=content(products,ordinary)
    projection=[{k:r[k] for k in ('start','end','raw','paths','connectors')} for r in result['discovery']['candidates']]
    require(projection==spec['source_expressions'] and not result['discovery']['issues']
        and all(r['syntax_complete'] for r in result['discovery']['candidates']),'Frozen source paragraph expectations differ')
    return {KEY:{'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),**result}}

def verify_answer(actual,ordinary,profile,products,root,*,expected_profile_sha256):
    expected={**ordinary,**evaluate(products,ordinary,profile,root,expected_profile_sha256=expected_profile_sha256)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    require(actual==expected,'Complete paragraph-discovery answer differs')
    return {'status':'PASS','whole_answer_equal':True,'target_resolution_established':False}
