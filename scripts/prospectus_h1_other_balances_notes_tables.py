"""Image-bound other balances with explicit unknowns and temporal ambiguity."""
import re
from scripts import prospectus_h1_other_balances_notes_mapping as mapping


def require(ok,message):
    if not ok:
        raise ValueError(message)


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
        u=lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    result=[]
    for spec in mapping.TABLES:
        page=spec['page']
        result.append({'key':spec['key'],'page':page,'unit':'EUR_THOUSANDS',
            'dates':['2010-06-30','2009-12-31']+(['2009-06-30'] if spec['key']=='debtor-impairment' else []),
            'period_months':spec['periods'],
            'unit_source':ref(page,spec['unit_order']),
            'date_sources':[ref(page,n) for n in spec['date_orders']],
            'section_sources':[ref(page,n) for n in spec['section_orders']],
            'caption_source':ref(page,spec['caption_order']) if 'caption_order' in spec else None,
            'rows':[{'key':key,'label_sources':[ref(page,n) for n in labels],
                     'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_ROW',
                     'cells':[parsed(ref(page,n)) for n in positions]}
                    for key,labels,positions in spec['rows']]})
    return result


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate source occurrence')
    require(actual==tables(units),'Reviewed table association changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    specs={s['key']:s for s in mapping.TABLES}
    def box(source):
        u=lookup[source['id']]
        require(u['raw']==source['quote'],'Source quote changed')
        return u['bbox']
    numeric_ids,offsets,diagnostics=[],[],[]
    row_count,dashes=0,0
    for table in actual:
        typed=manual['tables'][table['key']]
        require(table['unit']==typed['unit']=='EUR_THOUSANDS' and table['dates']==typed['dates']
                and table['period_months']==typed['period_months'],'Image dates/period/unit mismatch')
        require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Printed unit changed')
        require([normal(q['quote']) for q in table['date_sources']]==
                ['30.06.2010','31.12.2009']+(['30.06.2009'] if table['key']=='debtor-impairment' else []),
                'Wrong printed date')
        if table['key']=='debtor-impairment':
            require(table['caption_source']['quote']==typed['printed_caption']=='Six month period ended',
                    'Printed period caption changed')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value mismatch')
        headers=[box(q) for q in table['date_sources']]
        require(all(a[2]<b[0] for a,b in zip(headers,headers[1:])),'Date order changed')
        limits=[(a[2]+b[0])/2 for a,b in zip(headers,headers[1:])]
        previous_y=None
        for row in table['rows']:
            row_count+=1
            cells=row['cells']
            require(len(cells)==len(headers),'Missing numeric column')
            boxes=[box(c['source']) for c in cells]; y=boxes[0][1]
            require(previous_y is None or y>previous_y,'Wrong table row order')
            previous_y=y
            for col,(cell,b) in enumerate(zip(cells,boxes)):
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong source page')
                offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row geometry')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(boxes)-1 or b[2]<limits[col]),'Wrong date/value column')
                numeric_ids.append(cell['source']['id'])
                dashes+=int(cell['status']=='PRINTED_DASH_UNKNOWN_NOT_ZERO')
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels); offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),
                        'Wrong label/value row')
        values={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        for terms,total in specs[table['key']]['subtotals']:
            for col in range(len(headers)):
                unknown=[k for k in [*terms,total] if values[k][col] is None]
                diagnostics.append({'table':table['key'],'total':total,'date':table['dates'][col],
                    'unknown_rows':unknown,'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED',
                    'residual':None if unknown else sum(values[k][col] for k in terms)-values[total][col]})
    require(row_count==44 and len(numeric_ids)==len(set(numeric_ids))==94 and dashes==2,
            'Missing or duplicate numeric position')
    return {'table_rows':row_count,'numeric_positions':len(numeric_ids),
        'printed_unknown_dashes':dashes,'maximum_row_offset_points':max(offsets),
        'geometry_tolerance_points':1,'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION',
        'arithmetic':diagnostics}
