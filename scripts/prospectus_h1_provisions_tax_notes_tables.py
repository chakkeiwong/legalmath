"""Preserve original tax/provision numbers, unknowns and conflicting diagnostics."""
from fractions import Fraction
import re
from scripts import prospectus_h1_provisions_tax_notes_mapping as mapping

COLUMNS = {
    'provisions':['RESTRUCTURING','OTHER','TOTAL'],
    'deferred-balances':['ASSETS_2010_06_30','ASSETS_2009_12_31','LIABILITIES_2010_06_30',
                         'LIABILITIES_2009_12_31','NET_2010_06_30','NET_2009_12_31'],
    'deferred-movement':['SIX_MONTHS_2010_06_30','YEAR_2009_12_31'],
    'tax-recognition':['P_AND_L_SIX_MONTHS_2010_06_30','RESERVES_SIX_MONTHS_2010_06_30',
                       'P_AND_L_YEAR_2009_12_31','RESERVES_YEAR_2009_12_31'],
    'tax-reconciliation':['PERCENT_2010_06_30','AMOUNT_2010_06_30',
                          'PERCENT_2009_12_31','AMOUNT_2009_12_31']}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def parsed(ref, percent):
    unit = 'PERCENT' if percent else 'EUR_THOUSANDS'
    if ref is None:
        return {'source':None,'value':None,'status':'UNPRINTED_POSITION_NOT_ZERO','unit':unit}
    token = normal(ref['quote'])
    if token == '-':
        return {'source':ref,'value':None,'status':'PRINTED_DASH_UNKNOWN_NOT_ZERO','unit':unit}
    negative = token.startswith('(') and token.endswith(')')
    number = token[1:-1] if negative else token
    require(bool(re.fullmatch(r'[0-9]+\.[0-9]+' if percent else r'[0-9]+', number)),
            'Unsupported printed number')
    value = ('-' if negative else '') + number
    return {'source':ref,'value':value if percent else int(value),
            'status':'REPORTED_DECIMAL_STRING' if percent else 'REPORTED_INTEGER','unit':unit}


def tables(units):
    lookup = {(u['page'],u['order']):u for u in units}
    def ref(page, order):
        u = lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    output = []
    for spec in mapping.TABLES:
        key, page = spec['key'],spec['page']
        rows = []
        for rowkey, labels, positions in spec['rows']:
            rows.append({'key':rowkey,'label_sources':[ref(page,n) for n in labels],
                'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                'cells':[parsed(None if n is None else ref(page,n),
                                key=='tax-reconciliation' and col%2==0)
                         for col,n in enumerate(positions)]})
        output.append({'key':key,'page':page,'columns':COLUMNS[key],
            'unit':'MIXED_PERCENT_AND_EUR_THOUSANDS' if key=='tax-reconciliation' else 'EUR_THOUSANDS',
            'dates':spec['dates'],'period_months':spec['periods'],
            'unit_source':ref(page,spec['unit_order']),
            'headers':[[ref(page,n) for n in group] for group in spec['headers']],
            'group_headers':[[ref(page,n) for n in group] for group in spec.get('group_headers',[])],
            'period_headers':[[ref(page,n) for n in group] for group in spec.get('period_headers',[])],
            'date_sources':[ref(page,n) for n in spec.get('date_orders',[])],'rows':rows})
    return output


def arithmetic(table):
    values = {r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
    out = []
    def residual(label, terms, target):
        unknown = [i for i,x in enumerate([*terms,target]) if x is None]
        out.append({'relation':label,'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED',
                    'unknown_positions':unknown,
                    'residual':None if unknown else sum(terms)-target})
    if table['key']=='provisions':
        for key,row in values.items():
            residual(key+':restructuring+other-total',row[:2],row[2])
        for opening,changes,closing in [
            ('balance-2008',['charge-h1-2009','charge-off-h1-2009','exchange-h1-2009'],'balance-h1-2009'),
            ('balance-h1-2009',['charge-h2-2009','charge-off-h2-2009','exchange-h2-2009'],'balance-2009'),
            ('balance-2009',['charge-h1-2010','charge-off-h1-2010','exchange-h1-2010'],'balance-h1-2010')]:
            for col in range(3):
                residual(opening+':to:'+closing+':'+str(col),
                         [values[k][col] for k in [opening,*changes]],values[closing][col])
    elif table['key']=='deferred-balances':
        for key,row in values.items():
            for col in range(2):
                residual(key+':assets+liabilities-net:'+str(col),[row[col],row[col+2]],row[col+4])
        for col in range(6):
            residual('gross+offset-net:'+str(col),
                     [values[k][col] for k in ('gross','offset')],values['net'][col])
    elif table['key']=='deferred-movement':
        for col in range(2):
            residual('movement:'+str(col),[values[k][col] for k in list(values)[:-1]],values['closing'][col])
    elif table['key']=='tax-recognition':
        for col in range(4):
            residual('components-deferred:'+str(col),
                     [values[k][col] for k in list(values)[:12]],values['deferred'][col])
            residual('deferred+current-total:'+str(col),
                     [values[k][col] for k in ('deferred','current')],values['total'][col])
    else:
        for key,row in values.items():
            if key in ('profit','statutory-rate','calculated-tax'):
                continue
            for pc,amount in ((0,1),(2,3)):
                if row[pc] is not None and row[amount] is not None:
                    ratio = Fraction(row[amount]*100,values['profit'][amount])
                    delta = ratio-Fraction(row[pc])
                    out.append({'row':key,'date':table['dates'][pc],'reported_percent':row[pc],
                        'amount_over_profit_percent_exact':str(ratio),
                        'difference_percentage_points_exact':str(delta),
                        'source_correction_inferred':False})
    return out


def validate(actual, units, manual):
    lookup = {u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate original occurrence')
    require(actual==tables(units),'Reviewed table association changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    def box(ref):
        u=lookup[ref['id']]
        require(u['raw']==ref['quote'],'Changed source quote')
        return u['bbox']
    def bounds(refs):
        boxes=[box(q) for q in refs]
        return [min(b[0] for b in boxes),min(b[1] for b in boxes),
                max(b[2] for b in boxes),max(b[3] for b in boxes)]
    ids, rowcount, positions, blanks, dashes, offsets, diagnostics = [],0,0,0,0,[],[]
    for table in actual:
        manual_table=manual['tables'][table['key']]
        require(table['columns']==manual_table['columns'] and table['unit']==manual_table['unit'],
                'Image column or unit mismatch')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==manual_table['rows'],
                'Image row/value mismatch')
        require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Printed unit changed')
        headers=[bounds(group) for group in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(all(a<b for a,b in zip(centers,centers[1:])),'Wrong column order')
        limits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        previous_y=None
        for row in table['rows']:
            rowcount+=1
            cells=row['cells']; positions+=len(cells)
            require(len(cells)==len(headers),'Missing table position')
            printed=[(c,box(c['source'])) for c in cells if c['source'] is not None]
            require(printed,'Entire row unprinted')
            y=printed[0][1][1]
            require(previous_y is None or y>previous_y,'Wrong table row sequence')
            previous_y=y
            for col,cell in enumerate(cells):
                if cell['source'] is None:
                    blanks+=1
                    require(cell['status']=='UNPRINTED_POSITION_NOT_ZERO','Blank inferred as number')
                    continue
                b=box(cell['source']); offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1,'Numeric values on different rows')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(cells)-1 or b[2]<limits[col]),'Wrong column geometry')
                require(b[1]>headers[col][3],'Value above column header')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong numeric page')
                ids.append(cell['source']['id'])
                dashes+=int(cell['status']=='PRINTED_DASH_UNKNOWN_NOT_ZERO')
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels)
                offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for _,b in printed),
                        'Wrong label/value row')
        diagnostics.append({'table':table['key'],'checks':arithmetic(table)})
    require(rowcount==63 and positions==257 and len(ids)==len(set(ids))==251 and blanks==6,
            'Missing/duplicate numeric position')
    return {'table_rows':rowcount,'table_positions':positions,'numeric_positions':len(ids),
        'unprinted_positions':blanks,'printed_unknown_dashes':dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION','arithmetic':diagnostics}
