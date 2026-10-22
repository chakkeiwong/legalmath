"""Retain one inspected bilingual source conflict; never choose an amount."""
from copy import deepcopy
import re
from .admissions import review
from .anchors import fields
from .contracts import digest

PROFILE='bes2008-note46-en-pt.v1'
_PASSAGES={
    'en': ('Note 46 - SUBSEQUENT EVENTS',
        'On the 9th of January 2009, BES placed a 3 year euro 1 500 000 million debt guaranteed by the Portuguese Republic. '
        'International investors subscribed around 80% of this amount, originating a pro-rata allocation, '
        'since the total order book reached euro 1,900 million.', 'euro 1 500 000 million'),
    'pt': ('Nota 46 - Eventos Subsequentes',
        'Em 9 de Janeiro de 2009 o BES colocou, na sua totalidade, uma emissão de dívida a 3 anos garantida pelo Estado '
        'no montante de 1,5 mil milhões de euros. Cerca de 80% deste montante foi subscrito por investidores internacionais '
        'tendo obrigado a rateio com a procura registada a elevar-se a 1,9 mil milhões de euros.', '1,5 mil milhões de euros'),
}

def _pattern(text):
    return r'\s+'.join(re.escape(word) for word in text.split())

def _origins(reading,graph,start,end,language):
    units={u['id']:u for u in graph['units']}
    if len(units)!=len(graph['units']):
        raise ValueError('Duplicate source occurrence identity')
    origins=[c for c in reading['characters'] if start<=c['output']<end]
    seen=set();positions=set()
    for c in origins:
        unit=units.get(c['unit']);out=c['output'];offset=c['source_offset']
        if (type(out) is not int or type(offset) is not int or unit is None or
            not unit.get('visible',False) or unit['document']!=reading['document'] or
            unit['source_sha256']!=reading['source_sha256'] or unit['language']!=language or
            not 0<=offset<len(unit['raw']) or out in seen or (c['unit'],offset) in positions or
            c['character']!=reading['text'][out] or c['character']!=unit['raw'][offset]):
            raise ValueError('Discrepancy source characters, edition or language changed')
        seen.add(out);positions.add((c['unit'],offset))
    if any(i not in seen for i in range(start,end) if not reading['text'][i].isspace()):
        raise ValueError('Unmapped discrepancy context character')
    return deepcopy(origins)

def _bound_span(reading,graph,start,end,language):
    return {'start':start,'end':end,'quote':reading['text'][start:end],
            'source_characters':_origins(reading,graph,start,end,language)}

def admit(graph,selected,admission):
    keys={'version','graph_sha256','readings_sha256','review','discrepancies'}
    fields(admission,keys,keys)
    if (admission['version']!='source-discrepancies.v1' or admission['graph_sha256']!=digest(graph) or
        not selected or selected.get('version')!='admitted-report-readings.v1' or
        selected['graph_sha256']!=digest(graph) or admission['readings_sha256']!=digest(selected)):
        raise ValueError('Discrepancy graph or report readings changed')
    review(admission['review'])
    rows=admission['discrepancies']
    if not isinstance(rows,list) or len(rows)!=1:
        raise ValueError('Exactly one inspected Note46 discrepancy required')
    row,=rows
    fields(row,{'id','profile','sides'},{'id','profile','sides'})
    if not isinstance(row['id'],str) or not row['id'].strip() or row['profile']!=PROFILE:
        raise ValueError('Unsupported discrepancy identity or profile')
    if not isinstance(row['sides'],list) or len(row['sides'])!=2:
        raise ValueError('Both distinct English and Portuguese contexts required')
    indexed={r['id']:r for r in selected['reports']}
    if len(indexed)!=len(selected['reports']):
        raise ValueError('Duplicate discrepancy reading identity')
    output=[];languages=set();documents=set();reading_ids=set()
    for side in row['sides']:
        fields(side,{'reading','reading_sha256','language','context'},
                    {'reading','reading_sha256','language','context'})
        language=side['language'];reading=indexed.get(side['reading'])
        if (language not in _PASSAGES or language in languages or reading is None or
            reading['id'] in reading_ids or reading['document'] in documents or
            side['reading_sha256']!=reading['sha256'] or
            reading['sha256']!=digest({k:v for k,v in reading.items() if k!='sha256'})):
            raise ValueError('Discrepancy side identity, language or content changed')
        languages.add(language);documents.add(reading['document']);reading_ids.add(reading['id'])
        supplied=side['context'];fields(supplied,{'start','end','quote'},{'start','end','quote'})
        a,b=supplied['start'],supplied['end'];text=reading['text']
        if (type(a) is not int or type(b) is not int or not 0<=a<b<=len(text) or text[a:b]!=supplied['quote']):
            raise ValueError('Discrepancy context quote or interval changed')
        heading,context,literal=_PASSAGES[language]
        pattern=re.compile(r'(?P<heading>'+_pattern(heading)+r')\s*•\s*(?P<context>'+_pattern(context)+r')(?=\s*•|\s*$)')
        matches=list(pattern.finditer(text))
        if len(matches)!=1 or matches[0].span('context')!=(a,b):
            raise ValueError('Complete inspected Note46 first-bullet context required')
        literal_matches=list(re.finditer(_pattern(literal),text[a:b]))
        if len(literal_matches)!=1:
            raise ValueError('Unique inspected monetary wording required')
        token=literal_matches[0]
        output.append({'reading':reading['id'],'reading_sha256':reading['sha256'],
            'document':reading['document'],'source_sha256':reading['source_sha256'],
            'pages':deepcopy(reading['pages']),'language':language,
            'heading':_bound_span(reading,graph,*matches[0].span('heading'),language),
            'context':_bound_span(reading,graph,a,b,language),
            'monetary_wording':_bound_span(reading,graph,a+token.start(),a+token.end(),language)})
    return {'version':'admitted-source-discrepancies.v1','graph_sha256':digest(graph),
        'readings_sha256':digest(selected),'input_sha256':digest(admission),'review':deepcopy(admission['review']),
        'discrepancies':[{'id':row['id'],'profile':PROFILE,'status':'UNRESOLVED_SOURCE_DISCREPANCY',
            'sides':sorted(output,key=lambda x:x['language']),
            'explanation':'The inspected English and Portuguese Note46 passages give different monetary wording for the described issue. Both source statements remain unresolved.',
            'resolved_amount':None,'controlling_edition':None,'automatic_discovery':False,
            'independent_legal_acceptance':False,'financial_calculation_authorized':False}]}

def explain(admitted):
    return deepcopy(admitted['discrepancies'])
