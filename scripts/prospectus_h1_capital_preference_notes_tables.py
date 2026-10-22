"""Original ownership percentages and treasury counts with mixed units."""
from fractions import Fraction
import re
from scripts import prospectus_h1_capital_preference_notes_mapping as mapping


def require(ok,message):
    if not ok:raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        u=lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    output=[]
    for spec in mapping.TABLES:
        page,key=spec['page'],spec['key']
        cell_units=['PERCENT','PERCENT'] if key=='ownership' else ['SHARES','EUR_THOUSANDS','SHARES','EUR_THOUSANDS']
        rows=[]
        for rowkey,labels,positions in spec['rows']:
            cells=[]
            for col,n in enumerate(positions):
                source=ref(page,n);token=normal(source['quote'])
                if token=='-':
                    value,status=None,'PRINTED_DASH_UNKNOWN_NOT_ZERO'
                elif key=='ownership':
                    require(bool(re.fullmatch(r'[0-9]+\.[0-9]+%',token)),'Wrong printed percentage')
                    value,status=token[:-1],'REPORTED_DECIMAL_STRING'
                else:
                    negative=token.startswith('(') and token.endswith(')')
                    value=token[1:-1] if negative else token
                    require(bool(re.fullmatch(r'[0-9]+',value)),'Wrong printed integer')
                    value,status=(-1 if negative else 1)*int(value),'REPORTED_INTEGER'
                cells.append({'source':source,'value':value,'status':status,'unit':cell_units[col]})
            rows.append({'key':rowkey,'label_sources':[ref(page,n) for n in labels],'cells':cells})
        output.append({'key':key,'page':page,
            'unit':'PERCENT' if key=='ownership' else 'MIXED_SHARES_AND_EUR_THOUSANDS',
            'cell_units':cell_units,
            'dates':['2010-06-30','2009-12-31'] if key=='ownership' else
                    ['2010-06-30','2010-06-30','2009-12-31','2009-12-31'],
            'period_months':None if key=='ownership' else [6,6,12,12],
            'headers':[[ref(page,n) for n in group] for group in spec['headers']],
            'date_sources':[ref(page,n) for n in spec.get('date_orders',[])],
            'period_sources':[ref(page,n) for n in spec.get('period_orders',[])],
            'unit_sources':[ref(page,n) for n in spec.get('unit_orders',[])],
            'footnote_sources':[[ref(147,n) for n in group] for group in
                                ([10,17,35],[12,18,36],[14,37,38,39])] if key=='ownership' else
                                [[ref(148,n) for n in [31,46,47,48]]],
            'rows':rows})
    return output


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate source occurrence')
    require(actual==tables(units),'Reviewed table mapping changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    def box(q):
        u=lookup[q['id']]
        require(u['raw']==q['quote'],'Wrong source quote')
        return u['bbox']
    def bounds(refs):
        boxes=[box(q) for q in refs]
        return [min(b[0] for b in boxes),min(b[1] for b in boxes),
                max(b[2] for b in boxes),max(b[3] for b in boxes)]
    ids,offsets,diagnostics=[],[],[]
    count,dashes=0,0
    for table in actual:
        typed=manual['tables'][table['key']]
        require(all(table[k]==typed[k] for k in ('unit','dates','period_months')),'Image scope mismatch')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value mismatch')
        headers=[bounds(group) for group in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(all(a<b for a,b in zip(centers,centers[1:])),'Wrong column order')
        limits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        if table['key']=='ownership':
            require(normal(table['unit_sources'][0]['quote'])=='%Sharecapital','Ownership unit changed')
            require([normal(g[0]['quote']) for g in table['headers']]==['30.06.2010','31.12.2009'],
                    'Ownership dates changed')
        else:
            require(table['cell_units']==typed['cell_units'],'Treasury units changed')
            require([normal(q['quote']) for q in table['date_sources']]==['30.06.2010','31.12.2009'],
                    'Treasury dates changed')
            require([normal(q['quote']) for q in table['period_sources']]==
                    ['Sixmonthperiodended','Yearended'],'Treasury durations changed')
            require([''.join(normal(q['quote']) for q in g) for g in table['headers']]==
                    ['Numberofshares','Amount(thousandsofeuro)','Numberofshares','Amount(thousandsofeuro)'],
                    'Treasury printed units changed')
        previous_y=None
        for row in table['rows']:
            count+=1;cells=row['cells'];boxes=[box(c['source']) for c in cells];y=boxes[0][1]
            require(len(cells)==len(headers),'Missing column')
            require(previous_y is None or y>previous_y,'Wrong row order');previous_y=y
            for col,(cell,b) in enumerate(zip(cells,boxes)):
                offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row geometry')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(boxes)-1 or b[2]<limits[col]),'Wrong numeric column')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong numeric page')
                ids.append(cell['source']['id']);dashes+=int(cell['value'] is None)
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                offset=min(abs(b[1]-y) for b in labels);offsets.append(offset)
                require(offset<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),
                        'Wrong label/value association')
        for col in range(len(headers)):
            vals=[r['cells'][col]['value'] for r in table['rows']]
            unknown=[i for i,v in enumerate(vals) if v is None]
            residual=None if unknown else str(sum(Fraction(v) for v in vals[:-1])-Fraction(vals[-1]))
            diagnostics.append({'table':table['key'],'column':col,
                'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED','residual':residual})
    require(count==10 and len(ids)==len(set(ids))==26 and dashes==1,'Missing/duplicate numeric position')
    distinctions=manual['distinctions']
    diagnostics.append({'relation':'ordinary_count_times_nominal_minus_rounded_capital_eur',
        'residual':distinctions['ordinary_shares']*distinctions['ordinary_nominal_eur']-
                   distinctions['ordinary_capital_eur_millions']*1000000,
        'source_correction_inferred':False})
    return {'table_rows':count,'numeric_positions':len(ids),'printed_unknown_dashes':dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION','arithmetic':diagnostics}
