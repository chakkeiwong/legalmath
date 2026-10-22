"""Preserve original reserve rows, structural blanks and NCI table scopes."""
import re
from scripts import prospectus_h1_reserves_nci_notes_mapping as mapping

COLUMNS={
 'reserves':['AVAILABLE_FOR_SALE','DEFERRED_TAX','TOTAL_FAIR_VALUE','LEGAL_RESERVE','EXCHANGE_DIFFERENCES','OTHER_RESERVES_RETAINED_EARNINGS','TOTAL_OTHER_RESERVES_RETAINED_EARNINGS'],
 'fair-value-movement':['JUNE_2010','DECEMBER_2009'],
 'nci-subsidiaries':['BALANCE_SHEET_2010','INCOME_STATEMENT_2010','BALANCE_SHEET_2009','INCOME_STATEMENT_2009'],
 'nci-movement':['JUNE_2010','DECEMBER_2009','JUNE_2009']}
DATES={'reserves':[],'fair-value-movement':['2010-06-30','2009-12-31'],
 'nci-subsidiaries':['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],
 'nci-movement':['2010-06-30','2009-12-31','2009-06-30']}
PERIODS={'reserves':None,'fair-value-movement':[6,12],
 'nci-subsidiaries':[None,None,None,None],'nci-movement':[6,None,6]}


def require(ok,message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def parsed(source):
    if source is None:
        return {'source':None,'value':None,'status':'UNPRINTED_POSITION_NOT_ZERO'}
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
        u=lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    result=[]
    for spec in mapping.TABLES:
        key,page=spec['key'],spec['page']
        rows=[]
        for rowkey,labels,positions in spec['rows']:
            row={'key':rowkey,'label_sources':[ref(page,n) for n in labels],
                'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                'cells':[parsed(None if n is None else ref(page,n)) for n in positions]}
            if key=='reserves':
                row['movement_role']=('BALANCE' if rowkey.startswith('balance-') else
                    'COMPONENT_OF_CAPITAL_INCREASE' if rowkey in ('capital-decrease','special-reserve') else
                    'AGGREGATE_WITH_COMPONENTS' if rowkey=='capital-increase' else 'MOVEMENT')
            rows.append(row)
        result.append({'key':key,'page':page,'unit':'EUR_THOUSANDS','columns':COLUMNS[key],
            'dates':DATES[key],'period_months':PERIODS[key],
            'unit_source':ref(page,spec['unit_order']),
            'headers':[[ref(page,n) for n in group] for group in spec['headers']],
            'group_headers':[[ref(page,n) for n in group] for group in spec.get('group_headers',[])],
            'date_sources':[ref(page,n) for n in spec['date_orders']],'rows':rows})
    return result


def arithmetic(actual):
    output=[]
    for table in actual:
        values={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        key=table['key']
        def residual(name,terms,target):
            unknown=[i for i,v in enumerate([*terms,target]) if v is None]
            output.append({'table':key,'relation':name,
                'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED',
                'unknown_positions':unknown,'residual':None if unknown else sum(terms)-target})
        if key=='reserves':
            for row,values_ in values.items():
                residual(row+':fair-value',values_[:2],values_[2])
                residual(row+':other-reserves',values_[3:6],values_[6])
            for col in range(7):
                residual('capital-components:'+str(col),
                    [values[k][col] for k in ('capital-decrease','special-reserve')],
                    values['capital-increase'][col])
            for opening,changes,closing in [
                ('balance-2008',['capital-increase','siba-h1-2009','dividends-h1-2009',
                    'fair-value-h1-2009','exchange-h1-2009','transfer-h1-2009'],'balance-h1-2009'),
                ('balance-h1-2009',['siba-h2-2009','fair-value-h2-2009','exchange-h2-2009'],'balance-2009'),
                ('balance-2009',['siba-h1-2010','dividends-h1-2010','fair-value-h1-2010',
                    'exchange-h1-2010','transfer-h1-2010'],'balance-h1-2010')]:
                for col in range(7):
                    residual(opening+':to:'+closing+':'+str(col),
                        [values[k][col] for k in [opening,*changes]],values[closing][col])
        elif key=='nci-subsidiaries':
            for col in range(4):
                residual('subsidiaries:'+str(col),
                    [values[k][col] for k in values if k!='total'],values['total'][col])
        else:
            for col in range(len(table['columns'])):
                residual('movement:'+str(col),[v[col] for k,v in values.items() if k!='closing'],
                         values['closing'][col])
    by_key={t['key']:t for t in actual}
    subsidiaries=by_key['nci-subsidiaries']['rows'][-1]['cells'][3]['value']
    movement=by_key['nci-movement']['rows'][-2]['cells']
    output.append({'relation':'December subsidiary income minus December movement profit',
        'difference':subsidiaries-movement[1]['value'],
        'June_2009_movement_profit':movement[2]['value'],
        'period_or_correction_inferred':False,'role':'EXPLANATORY_ONLY'})
    return output


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate source occurrence')
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
    ids,offsets=[],[]
    rowcount,positions,blanks,dashes=0,0,0,0
    for table in actual:
        typed=manual['tables'][table['key']]
        for name in ('unit','columns','dates','period_months'):
            require(table[name]==typed[name],'Image '+name+' differs')
        require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Printed unit differs')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value differs')
        headers=[bounds(group) for group in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(all(a<b for a,b in zip(centers,centers[1:])),'Wrong column order')
        limits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        previous_y=None
        for row in table['rows']:
            rowcount+=1; cells=row['cells']; positions+=len(cells)
            require(len(cells)==len(headers),'Wrong column count')
            printed=[(c,box(c['source'])) for c in cells if c['source'] is not None]
            require(printed,'Unprinted whole row')
            y=printed[0][1][1]
            require(previous_y is None or y>previous_y,'Wrong row order');previous_y=y
            for col,cell in enumerate(cells):
                if cell['source'] is None:
                    blanks+=1
                    require(cell['status']=='UNPRINTED_POSITION_NOT_ZERO','Blank became number')
                    continue
                b=box(cell['source']);offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(cells)-1 or b[2]<limits[col]),'Wrong column geometry')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong source page')
                ids.append(cell['source']['id']);dashes+=int(cell['status']=='PRINTED_DASH_UNKNOWN_NOT_ZERO')
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for _,b in printed),
                        'Wrong label/value row')
    require(rowcount==49 and positions==236 and len(ids)==len(set(ids))==234 and blanks==2,
            'Missing or duplicated numeric position')
    return {'table_rows':rowcount,'table_positions':positions,'numeric_positions':len(ids),
        'unprinted_positions':blanks,'printed_unknown_dashes':dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION','arithmetic':arithmetic(actual)}
