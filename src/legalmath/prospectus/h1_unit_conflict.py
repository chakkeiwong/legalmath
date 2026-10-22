"""Supplied original H1 unit conflict; no correction or financial equality."""
from copy import deepcopy
from pathlib import Path
import re
from .successor.anchors import bind, fields
from .successor.contracts import bound_path, digest
from .successor.occurrences import anchor

VERSION='bes-h1-individual-unit-conflict.v1'
DOCUMENT='bes-interim-h1-2010'
SOURCE='b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7'
IMAGES={53:'5910add8fb17f5b74bbbb7c486638aa8eea36f125e472e16f2e567e43b862653',
        54:'c8618e339ebdb98b6a4e547f58e33635c13016210c7d1cdfdd740248c1bdd474'}
# Complete original native occurrences; the image shows S.A. whereas native
# extraction repeats .A. Keep the literal, never silently repair source text.
HEADERS={53:{1:'BANCO ESPÍRITO SANTO, S.A..A.',2:'INDIVIDUAL BALANCE SHEET AT 30 JUNE 2010',
    3:'EUR million',4:'Jun, 10',5:'Prior to provisions,',6:'Provisions,',
    7:'impairments and impairments and',8:'depreciation',9:'depreciation',10:'Net amount',11:'Jun, 09',243:'Net Profit'},
    54:{1:'BANCO ESPÍRITO SANTO, S.A..A.',2:'INDIVIDUAL INCOME STATEMENT FOR 1H10',
        3:'Jun, 09',4:'Jun, 10',5:"(eur '000)",6:"(eur '000)",80:'Net income'}}
CELLS={53:[199,207,215,223],54:[73,74]}
COLUMNS={53:['2010-06-30 before provisions,impairments,depreciation',
    '2010-06-30 provisions,impairments,depreciation','2010-06-30 net','2009-06-30 net'],
    54:['2009H1','2010H1']}

def numeral(text):
    if not isinstance(text,str):raise ValueError('Printed numeral required')
    value=text.strip()
    if value=='-':return None
    if not re.fullmatch(r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?: [0-9]{3})+)',value,re.ASCII):
        raise ValueError('Unsupported original H1 profit numeral')
    return int(value.replace(' ',''))

def make_profile(graph,prior,images):
    units={u['id']:u for u in graph['units']}
    return {'version':VERSION,'graph_sha256':digest(graph),'prior_sha256':digest(prior),
        'review':{'kind':'DEVELOPMENT','basis':'Supplied original016 reading and original page images',
                  'independent':False},
        'pages':[{'page':page,'headers':[anchor(units[f'{DOCUMENT}:p{page}:l{n}']) for n in HEADERS[page]],
                  'cells':[anchor(units[f'{DOCUMENT}:p{page}:l{n}']) for n in CELLS[page]],
                  'columns':deepcopy(COLUMNS[page]),
                  'image':deepcopy(next(i for i in images if i['page']==page))} for page in (53,54)]}

def evaluate(graph,prior,profile,root,*,expected_profile_sha256):
    keys={'version','graph_sha256','prior_sha256','review','pages'};fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['graph_sha256']!=digest(graph) or profile['prior_sha256']!=digest(prior)):
        raise ValueError('H1 unit profile, graph or full previous answer changed')
    review=profile['review'];fields(review,{'kind','basis','independent'},{'kind','basis','independent'})
    if (review['kind']!='DEVELOPMENT' or review['independent'] is not False
            or not isinstance(review['basis'],str) or not review['basis'].strip()):
        raise ValueError('Supplied development reading required')
    index={u['id']:u for u in graph['units']}
    if len(index)!=len(graph['units']):raise ValueError('Duplicate H1 source occurrence')
    def source(a,page,line,literal=None):
        keys={'unit','document','source_sha256','start','end','quote'};fields(a,keys,keys)
        unit=index.get(f'{DOCUMENT}:p{page}:l{line}')
        if (unit is None or unit['page']!=page or unit['language']!='en'
            or unit['document']!=DOCUMENT or unit['source_sha256']!=SOURCE
            or a['unit']!=unit['id'] or a['start']!=0 or a['end']!=len(unit['raw'])
            or literal is not None and unit['raw']!=literal):
            raise ValueError('Original H1 unit source position, label or edition changed')
        return bind({'units':[unit]},a)
    if not isinstance(profile['pages'],list) or len(profile['pages'])!=2:
        raise ValueError('Both original individual pages required')
    pages=[]
    for supplied,page in zip(profile['pages'],(53,54)):
        keys={'page','headers','cells','columns','image'};fields(supplied,keys,keys)
        if (type(supplied['page']) is not int or supplied['page']!=page
            or supplied['columns']!=COLUMNS[page]
            or not isinstance(supplied['headers'],list) or len(supplied['headers'])!=len(HEADERS[page])
            or not isinstance(supplied['cells'],list) or len(supplied['cells'])!=len(CELLS[page])):
            raise ValueError('Complete ordered original unit columns and headers required')
        headers=[source(a,page,n,literal) for a,(n,literal) in zip(supplied['headers'],HEADERS[page].items())]
        image=supplied['image'];fields(image,{'page','path','sha256'},{'page','path','sha256'})
        if (type(image['page']) is not int or image['page']!=page or image['sha256']!=IMAGES[page]
            or digest(bound_path(root,image['path']).read_bytes())!=IMAGES[page]):
            raise ValueError('Original H1 unit image identity changed')
        cells=[]
        for a,n,column in zip(supplied['cells'],CELLS[page],COLUMNS[page]):
            evidence=source(a,page,n);value=numeral(evidence['quote'])
            cells.append({'column':column,'literal':evidence['quote'],'value':value,
                'status':'DASH_UNKNOWN' if value is None else 'SOURCE_NUMBER',
                'printed_unit':'EUR million' if page==53 else "(eur '000)",
                'scale_to_EUR':1000000 if page==53 else 1000,'source':evidence})
        pages.append({'page':page,'headers':headers,'cells':cells,'image':deepcopy(image)})
    comparisons=[]
    for year,left,right in [('2010H1',2,1),('2009H1',3,0)]:
        a,b=pages[0]['cells'][left],pages[1]['cells'][right]
        difference=None if a['value'] is None or b['value'] is None else a['value']-b['value']
        comparisons.append({'period':year,'balance_column':a['column'],'income_column':b['column'],
            'balance_numeral':a['value'],'income_numeral':b['value'],'raw_numeral_difference':difference,
            'numeral_status':'UNKNOWN_NUMERAL' if difference is None else 'MATCH' if difference==0 else 'DIFFER',
            'balance_scale_to_EUR':1000000,'income_scale_to_EUR':1000,
            'printed_scale_ratio':1000,'same_unit_financial_equality':False,
            'status':'UNRESOLVED_ORIGINAL_SOURCE_UNIT_CONFLICT'})
    membership=prior['h1_scope_review']['candidates']
    if not all({53,54}<=set(c['pages']) for c in membership):
        raise ValueError('Original H1 scope candidates omit conflict pages')
    return {'version':VERSION,'profile_sha256':digest(profile),'graph_sha256':digest(graph),
        'prior_sha256':digest(prior),'entity':'Banco Espírito Santo, S.A.; individual Bank statements',
        'document':DOCUMENT,'source_sha256':SOURCE,'pages':pages,'comparisons':comparisons,
        'scope_candidates':[{'id':c['id'],'pages53_54_included':True} for c in membership],
        'selected_incorporation_reading':None,'resolved_unit':None,'accounting_cause':None,
        'source_rescaled':False,'official_unit_correction_established':False,'automatic_discovery':False,
        'financial_calculation_authorized':False,'independent_legal_acceptance':False,
        'source_authenticity_established':False,'may_execute_transaction':False}

def explain(review):
    comparisons=' '.join(f'{r["period"]}: balance numeral {r["balance_numeral"]}, income numeral {r["income_numeral"]}; '
        f'raw numeral difference {r["raw_numeral_difference"]}.' for r in review['comparisons'])
    return ('The original individual Bank balance sheet on page53 prints EUR million; '
        "both date columns of the individual income statement on page54 print (eur '000). "
        +comparisons+' The printed unit scales differ by a factor of1000. Matching numerals do not establish '
        'same-unit financial equality. The adjustment dash remains unknown. Neither statement is rescaled, '
        'and no intended unit, official correction or accounting cause is selected. These are individual '
        'Banco Espírito Santo,S.A. statements, not BES Finance accounts or consolidated Group profit. '
        'Both retained incorporation readings include pages53–54; neither reading is selected. '
        'Source authenticity, general extraction and financial authorization remain unestablished.')
