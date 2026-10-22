"""Check original asset categories, printed discrepancies and unknown cells."""
import re
from scripts import prospectus_h1_property_intangible_notes_mapping as mapping


def require(ok,message):
    if not ok:
        raise ValueError(message)


def normal(text):
    return ''.join(text.split())


def parsed(source):
    token=normal(source['quote'])
    if token=='-':
        return {'source':source,'value':None,'status':'PRINTED_DASH_UNKNOWN_NOT_ZERO'}
    negative=token.startswith('(') and token.endswith(')')
    token=token[1:-1] if negative else token
    require(bool(re.fullmatch(r'[0-9]+',token)),'Unsupported printed integer')
    return {'source':source,'value':(-1 if negative else 1)*int(token),'status':'REPORTED_INTEGER'}


def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        u=lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    output=[]
    for spec in mapping.TABLES:
        key,page=spec['key'],spec['page']
        balance=key.endswith('-balance')
        columns=(['JUNE_2010','DECEMBER_2009'] if balance else
                 ['PROPERTY','EQUIPMENT','OTHER','WORK_IN_PROGRESS','TOTAL'] if key.startswith('property-') else
                 ['GOODWILL','SOFTWARE','OTHER','WORK_IN_PROGRESS','TOTAL'])
        rows=[]
        for rowkey,labels,positions in spec['rows']:
            row={'key':rowkey,'label_sources':[ref(page,n) for n in labels],
                 'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                 'cells':[parsed(ref(page,n)) for n in positions]}
            if rowkey=='printed-depreciation-in-cost':
                row['source_label_discrepancy']='PRINTED_DEPRECIATION_LABEL_IN_ACQUISITION_COST_SECTION_UNRESOLVED'
            rows.append(row)
        output.append({'key':key,'page':page,'unit':'EUR_THOUSANDS','columns':columns,
             'dates':['2010-06-30','2009-12-31'] if balance else [],'period_months':None,
             'unit_source':ref(page,spec['unit_order']),
             'headers':[[ref(page,n) for n in group] for group in spec['headers']],
             'date_sources':[ref(page,n) for n in spec['date_orders']],'rows':rows})
    return output


def arithmetic(actual):
    output=[]
    indexed={t['key']:{r['key']:[c['value'] for c in r['cells']] for r in t['rows']} for t in actual}
    def residual(table,relation,terms,target):
        unknown=[i for i,v in enumerate([*terms,target]) if v is None]
        output.append({'table':table,'relation':relation,
            'status':'UNRESOLVED_UNKNOWN' if unknown else 'COMPUTED','unknown_positions':unknown,
            'residual':None if unknown else sum(terms)-target})
    for table in actual:
        key=table['key']; rows=indexed[key]
        if key.endswith('-balance'):
            sums=({'property-total':['own-property','leasehold','property-other'],
                   'equipment-total':['computer','fixtures','furniture','security','office','vehicles','equipment-other'],
                   'operating-gross':['property-total','equipment-total','other'],
                   'wip-total':['wip-leasehold','wip-property','wip-equipment','wip-other'],
                   'gross':['operating-gross','wip-total'],'net':['gross','depreciation']}
                  if key.startswith('property') else
                  {'third-party-total':['third-party-software','third-party-other'],
                   'gross':['goodwill','internal-software','third-party-total','wip'],
                   'net':['gross','amortisation','impairment']})
            for total,components in sums.items():
                for col in range(2):
                    residual(key,total+':'+str(col),[rows[k][col] for k in components],rows[total][col])
        else:
            for row,values in rows.items():
                residual(key,'categories:'+row,values[:-1],values[-1])
            if not key.endswith('-net'):
                names=list(rows); balances=[i for i,k in enumerate(names) if k.startswith('balance-')]
                for start,stop in zip(balances,balances[1:]):
                    for col in range(5):
                        residual(key,names[start]+':to:'+names[stop]+':'+str(col),
                                 [rows[k][col] for k in names[start:stop]],rows[names[stop]][col])
    for family in ('property','intangible'):
        for period in ('h1-2010','2009','h1-2009'):
            for col in range(5):
                terms=[indexed[family+'-cost']['balance-'+period][col]]
                for section in (['depreciation'] if family=='property' else ['amortisation','impairment']):
                    value=indexed[family+'-'+section]['balance-'+period][col]
                    terms.append(None if value is None else -value)
                residual(family+'-net',period+':'+str(col),terms,indexed[family+'-net']['net-'+period][col])
    output.append({'relation':'Goodwill acquisition row less Aman footnote',
       'difference':indexed['intangible-cost']['acquired-b'][0]-mapping.DISTINCTIONS['aman_goodwill_footnote_thousands'],
       'role':'EXPLANATORY_ONLY','footnote_equals_whole_row_inferred':False})
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
    ids,offsets=[],[]; rowcount=0
    for table in actual:
        typed=manual['tables'][table['key']]
        for key in ('unit','columns','dates','period_months'):
            require(table[key]==typed[key],'Image '+key+' differs')
        require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Printed unit differs')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value differs: '+table['key'])
        headers=[bounds(group) for group in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(all(a<b for a,b in zip(centers,centers[1:])),'Wrong column order')
        limits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        previous_y=None
        for row in table['rows']:
            rowcount+=1; cells=row['cells']; boxes=[box(c['source']) for c in cells]
            require(len(cells)==len(headers),'Wrong column count')
            y=boxes[0][1]
            require(previous_y is None or y>previous_y,'Wrong row order'); previous_y=y
            for col,(cell,b) in enumerate(zip(cells,boxes)):
                offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row')
                require((col==0 or b[0]>limits[col-1]) and
                        (col==len(cells)-1 or b[2]<limits[col]),'Wrong column geometry')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong source page')
                ids.append(cell['source']['id'])
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),
                        'Wrong label/value row: '+row['key'])
    require(rowcount==111 and len(ids)==len(set(ids))==459,'Missing or duplicated numeric position')
    return {'table_rows':rowcount,'numeric_positions':len(ids),
            'printed_unknown_dashes':sum(c['value'] is None for t in actual for r in t['rows'] for c in r['cells']),
            'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
            'arithmetic_role':'EXPLANATORY_ONLY_WITH_UNKNOWN_PROPAGATION','arithmetic':arithmetic(actual)}
