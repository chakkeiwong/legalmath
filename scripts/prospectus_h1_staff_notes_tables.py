"""Original staff costs and dated person counts with explicit row hierarchy."""
import re
from scripts import prospectus_h1_staff_notes_mapping as mapping


def require(ok,message):
    if not ok:
        raise ValueError(message)


def normal(text):
    return ''.join(text.split())


def tables(units):
    lookup={(u['page'],u['order']):u for u in units}
    def ref(page,order):
        u=lookup[page,order];return {'id':u['id'],'quote':u['raw']}
    def cell(source):
        token=normal(source['quote'])
        require(bool(re.fullmatch(r'[0-9]+',token)),'Unsupported printed integer')
        return {'source':source,'value':int(token),'status':'REPORTED_INTEGER'}
    output=[]
    for spec in mapping.TABLES:
        page,key=spec['page'],spec['key'];rows=[]
        for rowkey,labels,positions in spec['rows']:
            rows.append({'key':rowkey,'label_sources':[ref(page,n) for n in labels],
                'label_role':'PRINTED_ROW_LABEL' if labels else 'INTERPRETIVE_UNLABELLED_TOTAL',
                'aggregation_role':('PARENT_WITH_COMPONENTS' if rowkey=='wages-salaries' else
                    'COMPONENT_OF_WAGES' if rowkey in ('remuneration','long-service') else
                    'TOTAL' if rowkey=='total' else 'SEPARATE_CATEGORY'),
                'cells':[cell(ref(page,n)) for n in positions]})
        output.append({'key':key,'page':page,'unit':'EUR_THOUSANDS' if key=='staff-costs' else 'PERSONS',
            'columns':['JUNE_2010','JUNE_2009'],'dates':['2010-06-30','2009-06-30'],
            'period_months':[6,6] if key=='staff-costs' else None,
            'unit_source':ref(page,spec['unit_order']),
            'headers':[[ref(page,n) for n in group] for group in spec['headers']],
            'date_sources':[ref(page,n) for n in spec['date_orders']],'rows':rows})
    return output


def arithmetic(actual):
    result=[]
    for table in actual:
        rows={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        relations=({'wages-salaries':['remuneration','long-service'],
                    'total':['wages-salaries','social-charges','pensions','other-costs']}
                   if table['key']=='staff-costs' else {'total':['bes','subsidiaries']})
        for target,parts in relations.items():
            for col in range(2):
                result.append({'table':table['key'],'relation':target,'column':col,
                    'status':'COMPUTED','residual':sum(rows[k][col] for k in parts)-rows[target][col]})
    return result


def validate(actual,units,manual):
    lookup={u['id']:u for u in units}
    require(len(lookup)==len(units),'Duplicate source occurrence')
    require(actual==tables(units),'Reviewed table association changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing image table')
    def box(ref):
        u=lookup[ref['id']];require(u['raw']==ref['quote'],'Changed source quote');return u['bbox']
    ids,offsets=[],[];rows=0
    for table in actual:
        typed=manual['tables'][table['key']]
        for name in ('unit','columns','dates','period_months'):
            require(table[name]==typed[name],'Image '+name+' differs')
        if table['key']=='staff-costs':
            require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Printed cost unit differs')
        else:
            require('numberofemployeesoftheGroup' in normal(table['unit_source']['quote']),
                    'Headcount source unit missing')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row/value differs')
        headers=[box(group[0]) for group in table['headers']]
        centers=[(b[0]+b[2])/2 for b in headers];require(centers[0]<centers[1],'Wrong header order')
        split=sum(centers)/2;previous_y=None
        for row in table['rows']:
            rows+=1;boxes=[box(c['source']) for c in row['cells']];y=boxes[0][1]
            require(previous_y is None or y>previous_y,'Wrong row order');previous_y=y
            require(boxes[0][2]<split<boxes[1][0],'Wrong column geometry')
            for col,(b,cell) in enumerate(zip(boxes,row['cells'])):
                offsets.append(abs(b[1]-y))
                require(abs(b[1]-y)<=1 and b[1]>headers[col][3],'Wrong numeric row')
                require(lookup[cell['source']['id']]['page']==table['page'],'Wrong source page')
                ids.append(cell['source']['id'])
            if row['label_sources']:
                labels=[box(q) for q in row['label_sources']]
                distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
                require(distance<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),'Wrong label/value row')
    require(rows==10 and len(ids)==len(set(ids))==20,'Missing numeric position')
    return {'table_rows':rows,'numeric_positions':len(ids),'printed_unknown_dashes':0,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'arithmetic_role':'EXPLANATORY_ONLY','arithmetic':arithmetic(actual)}
