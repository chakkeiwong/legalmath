"""Preserve masked totals, joint source boxes and row-specific geographic dates."""
import re
from scripts import prospectus_h1_segment_notes_mapping as mapping


def require(ok,message):
    if not ok:
        raise ValueError(message)


def normal(value):
    return ''.join(value.split())


def tables(units):
    lookup={u['order']:u for u in units if u['page']==102}
    def ref(order):
        u=lookup[order];return {'id':u['id'],'quote':u['raw']}
    def cell(position):
        if isinstance(position,tuple):
            order,part=position;source=ref(order);pieces=mapping.JOINT_PARTS[order]
            require(normal(source['quote'])==normal(' '.join(pieces)),'Changed joint quote')
            starts=[];cursor=0
            for piece in pieces:
                start=source['quote'].find(piece,cursor)
                require(start>=0,'Missing disjoint source span')
                starts.append(start);cursor=start+len(piece)
            token=pieces[part];span=[starts[part],starts[part]+len(token)]
            geometry='SHARED_ORIGINAL_BOX_NOT_INDEPENDENT_CELL'
        else:
            source=ref(position);token=source['quote'];span=[0,len(token)]
            geometry='INDIVIDUAL_ORIGINAL_BOX'
        compact=normal(token)
        if compact=='-':
            value,status=None,'PRINTED_DASH_UNKNOWN'
        elif compact and set(compact)=={'#'}:
            value,status=None,'PRINTED_MASKED_UNKNOWN'
        else:
            require(bool(re.fullmatch(r'\d+|\(\d+\)',compact)),'Invalid printed integer')
            value=-int(compact[1:-1]) if compact.startswith('(') else int(compact)
            status='REPORTED_INTEGER'
        return {'source':source,'source_span':span,'printed_token':token,
                'value':value,'status':status,'geometry_basis':geometry}
    result=[]
    for spec in mapping.TABLES:
        rows=[]
        for key,labels,positions in spec['rows']:
            footnoted=spec['key']=='geography-2009' and key!='net-profit'
            rows.append({'key':key,'label_sources':[ref(n) for n in labels],
                'date':'2009-12-31' if footnoted else spec['caption_date'],
                'date_basis':'FOOTNOTE_A' if footnoted else 'TABLE_CAPTION',
                'aggregation_role':'INCLUDED_IN_EXPENSES' if key=='provisions' else
                    'SEPARATE_INTERSEGMENT_DISCLOSURE' if key=='intersegment-income' else 'REPORTED_ROW',
                'cells':[cell(p) for p in positions]})
        result.append({'key':spec['key'],'page':102,'unit':'EUR_THOUSANDS',
            'unit_source':ref(spec['unit_order']),'columns':spec['columns'],
            'headers':[[ref(n) for n in h] for h in spec['headers']],
            'caption_date':spec['caption_date'],'date_source':ref(spec['date_order']),
            'period_months':spec['period_months'],'period_sources':[ref(n) for n in spec['period_orders']],
            'footnote':ref(spec['footnote_order']) if 'footnote_order' in spec else None,'rows':rows})
    return result


def arithmetic(actual):
    results=[]
    def record(table,relation,target,parts):
        vals=[target,*parts]
        results.append({'table':table,'relation':relation,
            'status':'UNKNOWN_PROPAGATED' if None in vals else 'COMPUTED',
            'residual':None if None in vals else sum(parts)-target})
    for table in actual:
        rows={r['key']:[c['value'] for c in r['cells']] for r in table['rows']}
        for key,vals in rows.items():
            record(table['key'],key+'-columns',vals[-1],vals[:-1])
        if table['key'].startswith('operating'):
            for col in range(9):
                record(table['key'],'income-'+str(col),rows['operating-income'][col],
                       [rows['net-interest'][col],rows['other-income'][col]])
                record(table['key'],'pretax-'+str(col),rows['pretax-profit'][col],
                       [rows['operating-income'][col],
                        None if rows['expenses'][col] is None else -rows['expenses'][col],
                        rows['disposal-gains'][col],rows['associate-profit'][col]])
    return results


def validate(actual,units,manual):
    lookup={u['id']:u for u in units};require(len(lookup)==len(units),'Duplicate source')
    require(actual==tables(units),'Reviewed source association changed')
    require({t['key'] for t in actual}==set(manual['tables']),'Missing typed table')
    def box(source):
        u=lookup[source['id']];require(u['raw']==source['quote'],'Changed quote')
        require(u['page']==102,'Wrong source page')
        return u['bbox']
    seen={};offsets=[];positions=0;unknown_dashes=0;masked=0;row_count=0
    for table in actual:
        typed=manual['tables'][table['key']]
        for key in ('unit','columns','caption_date','period_months'):
            require(table[key]==typed[key],'Image '+key+' differs')
        require([[r['key'],*[c['value'] for c in r['cells']]] for r in table['rows']]==typed['rows'],
                'Image row values differ')
        require([r['date'] for r in table['rows']]==typed['row_dates'],'Image row dates differ')
        require(normal(table['unit_source']['quote'])=='(inthousandsofeuro)','Changed printed units')
        if table['key']=='geography-2009':
            require(normal(table['footnote']['quote'])=='(a)Informationasat31December2009.','Changed date footnote')
        heads=[box(h[0]) for h in table['headers']]
        centers=[(b[0]+b[2])/2 for b in heads]
        require(centers==sorted(centers),'Wrong header columns')
        splits=[(a+b)/2 for a,b in zip(centers,centers[1:])]
        prev_y=None
        for row in table['rows']:
            row_count+=1;boxes=[box(c['source']) for c in row['cells']];y=boxes[0][1]
            require(prev_y is None or y>prev_y,'Wrong row order');prev_y=y
            groups={}
            for col,(c,b) in enumerate(zip(row['cells'],boxes)):
                positions+=1;unknown_dashes+=c['status']=='PRINTED_DASH_UNKNOWN';masked+=c['status']=='PRINTED_MASKED_UNKNOWN'
                sid=c['source']['id'];start,end=c['source_span']
                require(c['source']['quote'][start:end]==c['printed_token'],'Changed text span')
                require(0<=start<end<=len(c['source']['quote']),'Invalid span')
                for oldstart,oldend in seen.get(sid,[]):
                    require(end<=oldstart or start>=oldend,'Reused or overlapping source span')
                seen.setdefault(sid,[]).append((start,end));groups.setdefault(sid,[]).append(col)
                offset=abs(b[1]-y);offsets.append(offset)
                require(offset<=1 and b[1]>max(box(h)[3] for h in table['headers'][col]),'Wrong row geometry')
            for sid,cols in groups.items():
                b=lookup[sid]['bbox'];left,right=cols[0],cols[-1]
                if len(cols)==1:
                    center=(b[0]+b[2])/2
                    require((left==0 or center>splits[left-1]) and
                            (right==len(heads)-1 or center<splits[right]),'Wrong individual column')
                else:
                    require(table['key']=='geography-2009' and row['key']=='net-assets' and
                            len(cols)==2 and right==left+1,'Unreviewed shared box')
                    require((left==0 or b[0]>splits[left-1]) and
                            (right==len(heads)-1 or b[2]<splits[right]) and
                            b[0]<splits[left]<b[2],'Shared box does not span reviewed adjacent columns')
                    spans=sorted(seen[sid]);raw=lookup[sid]['raw']
                    cursor=0
                    for start,end in spans:
                        require(not raw[cursor:start].strip(),'Unmapped joint text');cursor=end
                    require(not raw[cursor:].strip(),'Unmapped joint suffix')
            labels=[box(q) for q in row['label_sources']]
            distance=min(abs(b[1]-y) for b in labels);offsets.append(distance)
            require(distance<=1 and max(b[2] for b in labels)<min(b[0] for b in boxes),'Wrong label row')
    require(row_count==26 and positions==250 and len(seen)==246,'Missing table position')
    require(masked==2 and sum(len(v)>1 for v in seen.values())==4,'Masked/joint positions changed')
    require(unknown_dashes==manual['printed_unknown_dashes'],'Changed dash count')
    return {'tables':4,'table_rows':row_count,'value_positions':positions,'native_value_occurrences':len(seen),
        'shared_native_occurrences':4,'masked_unknown_totals':masked,'printed_unknown_dashes':unknown_dashes,
        'maximum_row_offset_points':max(offsets),'geometry_tolerance_points':1,
        'independent_geometry_for_joint_cells':False,'arithmetic_role':'EXPLANATORY_ONLY',
        'arithmetic':arithmetic(actual)}
