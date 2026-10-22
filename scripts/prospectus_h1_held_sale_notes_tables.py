"""Source-bound held-for-sale tables with separate sides and period ambiguity."""
import re
from scripts import prospectus_h1_held_sale_notes_mapping as mapping

COLUMNS={'held-sale-balances':['ASSETS_2010','LIABILITIES_2010','ASSETS_2009','LIABILITIES_2009'],
 'impairment-movement':['JUNE_2010','DECEMBER_2009','JUNE_2009'],
 'asset-movement':['JUNE_2010','DECEMBER_2009']}
DATES={'held-sale-balances':['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],
 'impairment-movement':['2010-06-30','2009-12-31','2009-06-30'],
 'asset-movement':['2010-06-30','2009-12-31']}
PERIODS={'held-sale-balances':None,'impairment-movement':[6,None,6],'asset-movement':[None,None]}


def require(ok,message):
    if not ok:raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def parsed(source):
    token=normal(source['quote'])
    if token=='-':
        return {'source':source,'value':None,'status':'PRINTED_DASH_UNKNOWN_NOT_ZERO'}
    negative=token.startswith('(') and token.endswith(')')
    number=token[1:-1] if negative else token
    require(bool(re.fullmatch(r'[0-9]+',number)),'Unsupported printed integer')
    return {'source':source,'value':(-1 if negative else 1)*int(number),'status':'REPORTED_INTEGER'}


def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        u=lookup[page,order];return {'id':u['id'],'quote':u['raw']}
    result=[]
    for spec in mapping.TABLES:
        key,page=spec['key'],spec['page']
        result.append({'key':key,'page':page,'unit':'EUR_THOUSANDS',
            'columns':COLUMNS[key],'dates':DATES[key],'period_months':PERIODS[key],
            'unit_source':ref(page,spec['unit_order']),
            'headers':[[ref(page,n) for n in g] for g in spec['headers']],
            'date_sources':[ref(page,n) for n in spec['date_orders']],
            'caption_sources':[ref(page,n) for n in spec.get('caption_orders',[])],
            'rows':[{'key':rowkey,'label_sources':[ref(page,n) for n in labels],
                     'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                     'cells':[parsed(ref(page,n)) for n in positions]}
                    for rowkey,labels,positions in spec['rows']]})
    return result


def arithmetic(actual):
    output=[]
    all_values={}
    for table in actual:
        key=table['key']
        values={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        all_values[key]=values
        terms=[(['property','equipment'],'property-equipment-gross'),
               (['property-equipment-gross','impairment'],'property-equipment-net'),
               (['resale-subsidiaries','property-equipment-net'],'total')] if key=='held-sale-balances' else [
               ([k for k in values if k!='closing'],'closing')]
        for rows,total in terms:
            for col in range(len(table['columns'])):
                unknown=[k for k in [*rows,total] if values[k][col] is None]
                output.append({'table':key,'total':total,'column':col,
                    'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED','unknown_rows':unknown,
                    'residual':None if unknown else sum(values[k][col] for k in rows)-values[total][col]})
    for move_col,balance_col in ((0,0),(1,2)):
        b=all_values['held-sale-balances'];m=all_values['asset-movement']
        output.append({'relation':'movement_closing_plus_signed_impairment_minus_net_assets',
            'date':DATES['asset-movement'][move_col],
            'residual':m['closing'][move_col]+b['impairment'][balance_col]-b['total'][balance_col],
            'source_label_rewritten':False,'role':'EXPLANATORY_ONLY'})
    return output


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate source occurrence')
    require(actual==tables(units),'Reviewed source association differs')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    def box(q):
        u=lookup[q['id']];require(u['raw']==q['quote'],'Wrong source quote');return u['bbox']
    def bounds(qs):
        bs=[box(q) for q in qs]
        return [min(b[0] for b in bs),min(b[1] for b in bs),
                max(b[2] for b in bs),max(b[3] for b in bs)]
    ids,offsets=[],[]
    rowcount,dashes=0,0
    for table in actual:
        typed=manual['tables'][table['key']]
        require(all(table[k]==typed[k] for k in ('unit','columns','dates','period_months')),
                'Image column/unit/date/period mismatch')
        require(normal(table['unit_source']['quote'])==
                ('(thousandsofeuro)' if table['key']=='asset-movement' else '(inthousandsofeuro)'),
                'Printed unit differs')
        expected_dates=['30.06.2010','31.12.2009']+(['30.06.2009'] if table['key']=='impairment-movement' else [])
        require([normal(q['quote']) for q in table['date_sources']]==expected_dates,'Printed date differs')
        if table['key']=='impairment-movement':
            require(table['caption_sources'][0]['quote']=='Six month period ended','Printed caption differs')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image numeric rows differ')
        headers=[bounds(g) for g in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(all(a<b for a,b in zip(centers,centers[1:])),'Wrong header order')
        limits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        previous_y=None
        for row in table['rows']:
            rowcount+=1;cells=row['cells'];boxes=[box(c['source']) for c in cells];y=boxes[0][1]
            require(len(cells)==len(headers),'Wrong column count')
            require(previous_y is None or y>previous_y,'Wrong row order');previous_y=y
            for col,(cell,b) in enumerate(zip(cells,boxes)):
                offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(cells)-1 or b[2]<limits[col]),'Wrong numeric column')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong numeric page')
                ids.append(cell['source']['id']);dashes+=int(cell['value'] is None)
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),
                        'Wrong label/value row')
    require(rowcount==18 and len(ids)==len(set(ids))==56 and dashes==10,'Missing/duplicate positions')
    return {'table_rows':rowcount,'numeric_positions':len(ids),'printed_unknown_dashes':dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION','arithmetic':arithmetic(actual)}
