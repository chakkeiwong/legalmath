"""Source and geometry checks for dated, mixed-unit employee-benefit tables."""
from decimal import Decimal
import re
from scripts import prospectus_h1_employee_benefits_notes_mapping as mapping


def require(ok, message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        unit=lookup[page,order]
        return {'id':unit['id'],'quote':unit['raw']}
    def cell(page,order,unit):
        if order is None:
            return {'source':None,'value':None,'unit':unit,'status':'UNPRINTED_UNKNOWN'}
        source=ref(page,order);token=normal(source['quote'])
        if token=='-':
            value,status=None,'PRINTED_DASH_UNKNOWN'
        elif unit=='PRINTED_TEXT':
            value,status=token,'PRINTED_TEXT'
        elif unit in ('PERCENT','EUR'):
            numeric=token[:-1] if unit=='PERCENT' else token
            require(unit!='PERCENT' or token.endswith('%'),'Missing percent sign')
            require(bool(re.fullmatch(r'\d+(?:\.\d+)?',numeric)),'Invalid printed decimal')
            value,status=numeric,'REPORTED_DECIMAL_STRING'
        else:
            numeric=token.removesuffix('months') if unit=='MONTHS' else token
            require(bool(re.fullmatch(r'\d+|\(\d+\)',numeric)),'Invalid printed integer')
            value=-int(numeric[1:-1]) if numeric.startswith('(') else int(numeric)
            status='REPORTED_INTEGER'
        return {'source':source,'value':value,'unit':unit,'status':status}
    output=[]
    for spec in mapping.TABLES:
        page=spec['page'];rows=[]
        for index,(key,labels,positions) in enumerate(spec['rows']):
            units_for_row=(spec['column_units'] if 'column_units' in spec else
                [spec['row_units'][index] if 'row_units' in spec else spec['unit']]*len(positions))
            rows.append({'key':key,'label_sources':[ref(page,n) for n in labels],
                'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                'cells':[cell(page,n,u) for n,u in zip(positions,units_for_row)]})
        output.append({'key':spec['key'],'page':page,'unit':spec['unit'],
            'columns':spec.get('columns',spec['dates']),'dates':spec['dates'],
            'period_months':spec['period_months'],
            'unit_source':ref(page,spec['unit_order']) if spec['unit_order'] is not None else None,
            'headers':[[ref(page,n) for n in group] for group in spec['headers']],
            'date_sources':[ref(page,n) for n in spec['date_orders']],'rows':rows})
    return output


def arithmetic(actual):
    bykey={t['key']:t for t in actual};result=[]
    def relation(table,target,parts,columns=None):
        t=bykey[table];rows={r['key']:r for r in t['rows']}
        for col in range(len(t['rows'][0]['cells'])) if columns is None else columns:
            cells=[rows[k]['cells'][col] for k in [target,*parts]]
            require(len({c['unit'] for c in cells})==1,'Arithmetic mixed units')
            values=[c['value'] for c in cells]
            result.append({'table':table,'relation':target,'parts':parts,'column':col,
                'status':'UNKNOWN_PROPAGATED' if None in values else 'COMPUTED',
                'residual':None if None in values else sum(Decimal(str(v)) for v in values[1:])-Decimal(str(values[0]))})
            if result[-1]['residual'] is not None:result[-1]['residual']=str(result[-1]['residual'])
    relation('covered-persons','total',['employees','pensioners'])
    for target,parts in [('pension-total',['pension-pensioners','pension-employees']),
                         ('health-total',['health-pensioners','health-employees']),
                         ('total-obligation',['pension-total','health-total']),
                         ('funding',['total-obligation','plan-assets']),
                         ('recognised-asset',['funding','unrecognised-losses'])]:
        relation('recognised-balance',target,parts)
    for name in ('obligation-movement','plan-assets-movement','funding-movement','recognised-asset-movement','siba-share-movement'):
        relation(name,'ending',[r['key'] for r in bykey[name]['rows'] if r['key']!='ending'])
    relation('actuarial-loss-movement','ending',['beginning','assumptions','experience','amortisation','other'])
    relation('actuarial-loss-movement','ending',['within-corridor','outside-corridor'])
    relation('plan-assets-allocation','total',['shares','bonds','property','other'])
    relation('group-assets','total',['shares','bonds','property'])
    relation('benefit-cost','total',['service','interest','expected-return','amortisation'])
    relation('benefit-history','total',['pension','health'])
    relation('benefit-history','funding',['total','assets'])
    for row in bykey['obligation-movement']['rows']:
        for offset in (0,3):
            vals=[c['value'] for c in row['cells'][offset:offset+3]]
            result.append({'table':'obligation-movement','relation':row['key'],'column_group':offset//3,
                'status':'UNKNOWN_PROPAGATED' if None in vals else 'COMPUTED',
                'residual':None if None in vals else str(vals[0]+vals[1]-vals[2])})
    return result


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(units)==len(lookup),'Duplicate source occurrence')
    require(actual==tables(units),'Reviewed table association changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing typed image table')
    def box(ref):
        u=lookup[ref['id']]
        require(u['raw']==ref['quote'],'Changed source quote')
        return u['bbox']
    ids=[];offsets=[];row_count=0;blanks=0;dashes=0
    for table in actual:
        typed=manual['tables'][table['key']]
        for key in ('unit','columns','dates','period_months'):
            require(table[key]==typed[key],'Image '+key+' differs: '+table['key'])
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value differs: '+table['key'])
        require([[c['unit'] for c in r['cells']] for r in table['rows']]==typed['cell_units'],
                'Image cell units differ: '+table['key'])
        if table['unit']=='EUR_THOUSANDS':
            require(normal(table['unit_source']['quote']) in ('(inthousandsofeuro)','(inthousandofeuro)'),
                    'Printed monetary unit differs')
        headers=[box(h[-1]) for h in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers]
        require(centers==sorted(centers) and len(set(centers))==len(centers),'Wrong column order')
        splits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        previous_y=None
        for row in table['rows']:
            row_count+=1;printed=[c for c in row['cells'] if c['source'] is not None]
            y=box(printed[0]['source'])[1]
            require(previous_y is None or y>previous_y,'Wrong row order')
            previous_y=y
            for col,cell in enumerate(row['cells']):
                if cell['source'] is None:
                    blanks+=1
                    require(table['key']=='pprv-initial-valuation' and col==1,'Unreviewed blank')
                    # No source occurrence in this right-column row. Image review
                    # additionally distinguishes an unprinted position from a span.
                    require(not any(u['page']==table['page'] and abs(u['bbox'][1]-y)<=1 and
                                    u['bbox'][0]>splits[0] for u in units),'Blank contains source text')
                    continue
                b=box(cell['source']);center=(b[0]+b[2])/2
                require((col==0 or center>splits[col-1]) and
                        (col==len(headers)-1 or center<splits[col]),'Wrong column geometry')
                offset=abs(b[1]-y);offsets.append(offset)
                require(offset<=1 and b[1]>headers[col][3],'Wrong row geometry')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong table page')
                ids.append(cell['source']['id']);dashes+=cell['status']=='PRINTED_DASH_UNKNOWN'
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(box(c['source'])[0] for c in printed),
                        'Wrong label association')
    require(len(ids)==len(set(ids)),'Repeated value position')
    require(row_count==manual['row_count'] and len(ids)==manual['printed_positions'] and
            blanks==manual['unprinted_positions'] and dashes==manual['dash_positions'],'Missing typed position')
    return {'tables':len(actual),'table_rows':row_count,'printed_positions':len(ids),
        'unprinted_unknown_positions':blanks,'printed_unknown_dashes':dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY','arithmetic':arithmetic(actual)}
