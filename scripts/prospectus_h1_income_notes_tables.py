"""Source-bound income tables with image comparisons and explanatory arithmetic."""
from copy import deepcopy
import re
from scripts import prospectus_h1_income_notes_mapping as mapping

def require(ok, message):
    if not ok:
        raise ValueError(message)

def number(raw):
    token=''.join(raw.split())
    if token=='-':
        return None
    require(bool(re.fullmatch(r'[0-9]+',token)),'Unreviewed numeric form')
    return int(token)

def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        u=lookup[page,order]
        return {'id':u['id'],'quote':u['raw']}
    result=[]
    for spec in mapping.TABLES:
        p=spec['page']
        rows=[]
        for key,label,left,right in spec['rows']:
            cells=[ref(p,i) for i in (left,right)]
            rows.append({'key':key,'label_source':None if label is None else ref(p,label),
                'label_role':'INTERPRETIVE_UNLABELLED_ROW' if label is None else 'PRINTED_ROW_LABEL',
                'cells':[{'source':q,'value':number(q['quote']),
                          'status':'UNKNOWN_PRINTED_DASH' if number(q['quote']) is None else 'REPORTED_INTEGER'}
                         for q in cells]})
        result.append({'key':spec['key'],'page':p,'unit':'EUR_THOUSANDS','period_months':6,
            'period_ends':['2010-06-30','2009-06-30'],
            'unit_source':ref(p,spec['unit_order']),'period_source':ref(p,spec['period_order']),
            'date_sources':[ref(p,i) for i in spec['date_orders']],
            'section_sources':[ref(p,i) for i in spec['section_orders']],'rows':rows})
    return result

def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(actual==tables(units),'Reviewed table association changed')
    require(manual['columns']==['2010-06-30','2009-06-30'] and
            manual['period_months']==6 and manual['unit']=='EUR_THOUSANDS',
            'Image date or unit transcript changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    numeric_ids=[];unknowns=[];residuals=[]
    for table in actual:
        p=table['page'];keys=[r['key'] for r in table['rows']]
        require(len(keys)==len(set(keys)),'Duplicate table row key')
        values=[[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]
        require(values==manual['tables'][table['key']],'Image row/value mismatch')
        require(''.join(table['unit_source']['quote'].split())=='(inthousandsofeuro)',
                'Wrong printed units')
        require(''.join(table['period_source']['quote'].split())=='Sixmonthperiodended',
                'Wrong printed period')
        require([''.join(q['quote'].split()) for q in table['date_sources']]
                ==['30.06.2010','30.06.2009'],'Wrong printed dates')
        headers=[lookup[q['id']]['bbox'] for q in table['date_sources']]
        require(headers[0][2]<headers[1][0] and abs(headers[0][1]-headers[1][1])<=1,
                'Date header alignment changed')
        middle=(headers[0][2]+headers[1][0])/2
        previous_y=None
        for row in table['rows']:
            refs=[c['source'] for c in row['cells']]
            boxes=[lookup[q['id']]['bbox'] for q in refs]
            require(all(lookup[q['id']]['page']==p for q in refs),'Wrong source page')
            require(abs(boxes[0][1]-boxes[1][1])<=1,'Date values on different rows')
            require(boxes[0][2]<middle<boxes[1][0],'Wrong value/date column')
            require(boxes[0][1]>headers[0][3],'Value above date header')
            require(previous_y is None or boxes[0][1]>previous_y,'Wrong row sequence')
            previous_y=boxes[0][1]
            if row['label_source'] is not None:
                label=lookup[row['label_source']['id']]
                require(label['page']==p and abs(label['bbox'][1]-boxes[0][1])<=1,
                        'Wrong label/value row')
                require(label['bbox'][2]<boxes[0][0],'Label overlaps numeric column')
            for column,cell in enumerate(row['cells']):
                numeric_ids.append(cell['source']['id'])
                if cell['value'] is None:
                    require(cell['source']['quote'].strip()=='-' and cell['status']=='UNKNOWN_PRINTED_DASH',
                            'Unknown dash converted to number')
                    unknowns.append({'table':table['key'],'row':row['key'],
                                     'period_end':table['period_ends'][column]})
        by_key={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        def subtotal(component_keys,total_key):
            rows=[]
            for c in range(2):
                amounts=[by_key[k][c] for k in component_keys]
                known=sum(v for v in amounts if v is not None)
                missing=sum(v is None for v in amounts)
                rows.append({'period_end':table['period_ends'][c],'known_component_sum':known,
                    'unknown_count':missing,'reported_total':by_key[total_key][c],
                    'full_sum':None if missing else known,
                    'full_residual':None if missing else known-by_key[total_key][c]})
            return {'table':table['key'],'total_row':total_key,'columns':rows}
        if table['key']=='administrative':
            residuals.append(subtotal([k for k in keys if k!='total'],'total'))
        else:
            for part in ('income','expense'):
                residuals.append(subtotal([k for k in keys if k.startswith(part+'-') and k!=part+'-total'],
                                         part+'-total'))
            net_key='net-interest' if table['key']=='interest' else 'net-fees'
            residuals.append({'table':table['key'],'net_using_reported_totals':[
                by_key['income-total'][c]-by_key['expense-total'][c]-by_key[net_key][c]
                for c in range(2)]})
    require(len(numeric_ids)==len(set(numeric_ids))==92,'Missing or duplicate numeric position')
    require(unknowns==[{'table':'interest','row':'expense-other-printed-income','period_end':'2009-06-30'}],
            'Printed unknown coverage changed')
    return {'table_rows':46,'numeric_or_unknown_positions':92,'printed_unknowns':unknowns,
        'geometry_tolerance_points':1,'arithmetic_role':'EXPLANATORY_ONLY',
        'arithmetic':residuals,'unknowns_not_inferred_from_totals':True}
