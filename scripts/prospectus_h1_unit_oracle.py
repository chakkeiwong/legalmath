"""Separate finite source map and dimensional check using retained016."""
import hashlib
import json

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def require(ok,message):
    if not ok:raise ValueError(message)

def integer(text):
    if text=='-':return None
    groups=text.split(' ')
    require(all(g and all('0'<=c<='9' for c in g) for g in groups),'Invalid independent digits')
    require(len(groups)==1 or 1<=len(groups[0])<=3 and all(len(g)==3 for g in groups[1:]),'Invalid independent grouping')
    raw=''.join(groups);require(raw=='0' or not raw.startswith('0'),'Leading zero')
    return int(raw)

def verify(actual,explanation,profile,graph,prior,original,root):
    units={u['id']:u for u in original['full_units']}
    require(original['source_units']==[{'id':u['id'],'quote':u['raw']} for u in original['full_units']],
            'Original abridged profile differs from full occurrence text')
    current={u['id']:u for u in graph['units']}
    require(len(current)==len(graph['units']),'Duplicate current source')
    def occurrence(a):
        u=units[a['unit']]
        expected={'unit':u['id'],'document':u['document'],'source_sha256':u['source_sha256'],
            'start':0,'end':len(u['raw']),'quote':u['raw']}
        require(fingerprint(current.get(u['id']))==fingerprint(u),'Original source occurrence changed')
        require(fingerprint(a)==fingerprint(expected),'Complete original occurrence required')
        return {**a,'page':u['page'],'bbox':u['bbox']}
    require(profile['graph_sha256']==fingerprint(graph) and profile['prior_sha256']==fingerprint(prior),'Input context mismatch')
    row_specs=[(53,'individual_equity',6,12),(54,'individual_income',22,7)]
    pages=[]
    for supplied,(page,key,row_index,header_count) in zip(profile['pages'],row_specs):
        table=original['reading']['tables'][key];row=table['rows'][row_index]
        require(supplied['page']==page and supplied['columns']==table['columns'],'Original year/column mapping differs')
        ids=([1,2,3,4,5,6,7,8,9,10,11,243] if page==53 else [1,2,3,4,5,6,80])
        require([a['unit'] for a in supplied['headers']]==[f'bes-interim-h1-2010:p{page}:l{n}' for n in ids]
            and len(supplied['headers'])==header_count,'Original header positions changed')
        headers=[occurrence(a) for a in supplied['headers']]
        require([a['unit'] for a in supplied['cells']]==[c['source_unit'] for c in row['cells']],
            'Original016 cell map differs')
        cells=[]
        for a,old,column in zip(supplied['cells'],row['cells'],table['columns']):
            source=occurrence(a);number=integer(source['quote'])
            require(fingerprint(number)==fingerprint(old['value']) and source['quote']==old['quote'],'Independent source numeral differs')
            cells.append({'column':column,'literal':source['quote'],'value':number,
                'status':'DASH_UNKNOWN' if number is None else 'SOURCE_NUMBER',
                'printed_unit':'EUR million' if page==53 else "(eur '000)",
                'scale_to_EUR':10**6 if page==53 else 10**3,'source':source})
        image=next(i for i in original['images'] if i['page']==page)
        require(fingerprint(supplied['image'])==fingerprint(image),'Original image metadata changed')
        path=(root/image['path']).resolve()
        require(path.is_relative_to(root.resolve()) and hashlib.sha256(path.read_bytes()).hexdigest()==image['sha256'],'Original image bytes changed')
        pages.append({'page':page,'headers':headers,'cells':cells,'image':image})
    require(fingerprint(actual['pages'])==fingerprint(pages),'Output source binding, unit, column or number differs')
    comparisons=[]
    for period,balance,income in [('2010H1',pages[0]['cells'][2],pages[1]['cells'][1]),('2009H1',pages[0]['cells'][3],pages[1]['cells'][0])]:
        require(type(balance['value']) is int and type(income['value']) is int,'Original finite numeral missing')
        difference=balance['value']-income['value']
        comparisons.append({'period':period,'balance_column':balance['column'],'income_column':income['column'],
            'balance_numeral':balance['value'],'income_numeral':income['value'],'raw_numeral_difference':difference,
            'numeral_status':'MATCH' if difference==0 else 'DIFFER',
            'balance_scale_to_EUR':1000000,'income_scale_to_EUR':1000,'printed_scale_ratio':1000,
            'same_unit_financial_equality':False,'status':'UNRESOLVED_ORIGINAL_SOURCE_UNIT_CONFLICT'})
    require(fingerprint(actual['comparisons'])==fingerprint(comparisons),'Dimensional comparison changed')
    for flag in ('source_rescaled','official_unit_correction_established','automatic_discovery',
                 'financial_calculation_authorized','independent_legal_acceptance','source_authenticity_established','may_execute_transaction'):
        require(actual[flag] is False,'Unsupported promotion: '+flag)
    for field in ('selected_incorporation_reading','resolved_unit','accounting_cause'):
        require(actual[field] is None,'Selected unresolved interpretation')
    require(actual['version']=='bes-h1-individual-unit-conflict.v1' and actual['profile_sha256']==fingerprint(profile)
        and actual['graph_sha256']==fingerprint(graph) and actual['prior_sha256']==fingerprint(prior)
        and actual['entity']=='Banco Espírito Santo, S.A.; individual Bank statements'
        and actual['document']=='bes-interim-h1-2010'
        and actual['source_sha256']=='b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7','Result scope changed')
    candidates=prior['h1_scope_review']['candidates']
    require(all({53,54}<=set(c['pages']) for c in candidates),'Original conditional scope changed')
    require(actual['scope_candidates']==[{'id':c['id'],'pages53_54_included':True} for c in candidates],'Source membership differs')
    expected=("The original individual Bank balance sheet on page53 prints EUR million; both date columns of the individual income statement on page54 print (eur '000). "
        '2010H1: balance numeral 138435, income numeral 138435; raw numeral difference 0. '
        '2009H1: balance numeral 94055, income numeral 94055; raw numeral difference 0. '
        'The printed unit scales differ by a factor of1000. Matching numerals do not establish same-unit financial equality. '
        'The adjustment dash remains unknown. Neither statement is rescaled, and no intended unit, official correction or accounting cause is selected. '
        'These are individual Banco Espírito Santo,S.A. statements, not BES Finance accounts or consolidated Group profit. '
        'Both retained incorporation readings include pages53–54; neither reading is selected. '
        'Source authenticity, general extraction and financial authorization remain unestablished.')
    require(explanation==expected,'Source-linked explanation differs')
    require(set(actual)=={'version','profile_sha256','graph_sha256','prior_sha256','entity','document','source_sha256',
        'pages','comparisons','scope_candidates','selected_incorporation_reading','resolved_unit','accounting_cause',
        'source_rescaled','official_unit_correction_established','automatic_discovery','financial_calculation_authorized',
        'independent_legal_acceptance','source_authenticity_established','may_execute_transaction'},'Unexpected output field')
    return {'source_cells':6,'source_headers':19,'period_comparisons':2,'unknown_dashes':1,
        'printed_scale_ratio':1000,'same_unit_financial_equality':False,'unit_correction_established':False,
        'original_task_complete':False}
