"""Supplied complete Note26.5 with explicit mixed cells and shared headers."""
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path

from . import basf_statement, basf_equity, basf_oci_notes
from . import basf_hedge_spec as spec
from .successor.anchors import bind, fields
from .successor.contracts import digest

VERSION='basf-hedge-note-review.v1'
DOCUMENT=basf_equity.DOCUMENT


def numeric(literal, marker=None):
    """A footnote can qualify an unknown dash as well as a printed number."""
    if not isinstance(literal,str):
        raise ValueError('Original numeric-cell literal required')
    actual='a' if literal.endswith(' a') else None
    if actual!=marker:
        raise ValueError('Original table footnote marker changed')
    number=literal[:-2] if actual else literal
    return {**basf_statement.integer_millions(number),'literal':literal,'amount_literal':number,'footnote_marker':actual}


def text_cell(fragments, *, blank_allowed=False):
    if not fragments:
        if not blank_allowed:
            raise ValueError('Missing printed text cell')
        return {'literal':None,'status':'BLANK_ORIGINAL_NO_PRINTED_VALUE','integer_millions':None}
    literal=' '.join(a['quote'] for a in fragments)
    return {'literal':literal,'status':'PRINTED_NOT_APPLICABLE' if literal=='n/a' else 'PRINTED_STATEMENT_CAPTION',
            'integer_millions':None}


def arithmetic(fair,effects,prior):
    out=[]
    f={r['id']:r for r in fair['rows']}
    for year in ('2022','2021'):
        for target,parts in [('fx_total',['fx_forwards','fx_options']),
                             ('total',['fx_total','interest_total','commodity_total'])]:
            out.append(basf_equity.comparison('fair:'+year+':'+target,[f[target]['cells'][year]],
                                             [f[p]['cells'][year] for p in parts]))
    for table in effects:
        rows={r['id']:r for r in table['rows']}
        for column in spec.COLUMNS:
            if column not in spec.TEXT_COLUMNS:
                out.append(basf_equity.comparison('effects:'+table['year']+':'+column,
                    [rows['total']['cells'][column]],
                    [r['cells'][column] for r in table['rows'] if r['id']!='total']))
    statements={r['id']:r for r in prior['statement_review']['rows']}
    for table in effects:
        year=table['year'];total=table['rows'][-1]['cells']
        out.append(basf_oci_notes.scoped_comparison(year+':table-effects-vs-statement',
            [total['oci_change']],[statements['hedges']['cells'][year]],matched_scope=False,
            explanation='The detailed designated-instrument effect and statement aggregate are not established to share complete scope; source tables and timing qualifications do not supply a unique bridge.'))
    total22=effects[0]['rows'][-1]['cells']
    net=prior['oci_note_review']['amounts']['hedge_net_2022']
    for name,left in [('fair-value-balance',f['total']['cells']['2022']),('reserve-balance',total22['reserve'])]:
        out.append(basf_oci_notes.scoped_comparison(name+'-vs-net-movement',[left],[net],matched_scope=False,
            explanation='A dated balance and a period movement are different financial quantities; numerical comparison would not establish financial agreement.'))
    return out


def evaluate(graph,prior,profile,root,*,expected_profile_sha256):
    keys={'version','graph_sha256','prior_sha256','reviewer','source','metadata','prose','typographic',
          'fair_table','effects_tables','excluded_note27','selected_reading','financial_values_validated'}
    fields(profile,keys,keys)
    if (profile['version']!=VERSION or digest(profile)!=expected_profile_sha256
            or profile['graph_sha256']!=digest(graph) or profile['prior_sha256']!=digest(prior)):
        raise ValueError('Pinned hedge note,graph or complete prior consumer changed')
    if profile['selected_reading'] is not None or profile['financial_values_validated'] is not False:
        raise ValueError('Hedge note cannot select legal scope or validate financial accounts')
    reviewer=profile['reviewer']
    fields(reviewer,{'identity','basis','independent'},{'identity','basis','independent'})
    if (not isinstance(reviewer['identity'],str) or not reviewer['identity'].strip()
            or reviewer['basis']!='AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False):
        raise ValueError('Unsupported hedge-note review authority')
    source=profile['source']
    fields(source,{'document','path','sha256','images'},{'document','path','sha256','images'})
    if source['document']!=DOCUMENT or [i['page'] for i in source['images']]!=[279,280,281,282]:
        raise ValueError('Complete original hedge-note source pages required')
    root=Path(root).resolve()
    for item in [source,*source['images']]:
        name=item['path'];p=(root/name).resolve()
        if Path(name).is_absolute() or not p.is_relative_to(root) or not p.is_file() or digest(p.read_bytes())!=item['sha256']:
            raise ValueError('Original hedge-note PDF or inspected image changed')
    units={u['id']:u for u in graph['units']}
    pages=[u for u in graph['units'] if u['document']==DOCUMENT and 279<=u['page']<=282 and u['visible']]
    if len(units)!=len(graph['units']) or len(pages)!=452 or any(u['source_sha256']!=source['sha256'] or u['text_sha256']!=digest(u['raw'].encode()) for u in pages):
        raise ValueError('Complete original hedge-note inventory changed')
    used=[]
    def original(anchors,page,ids):
        if len(anchors)!=len(ids):
            raise ValueError('Complete source-fragment inventory required')
        out=[]
        for a,n in zip(anchors,ids):
            b=bind(graph,a)
            u=units[DOCUMENT+':p'+str(page)+':l'+str(n)]
            if (b['unit']!=u['id'] or b['document']!=DOCUMENT or b['page']!=page
                    or a['start']!=0 or a['end']!=len(u['raw']) or a['source_sha256']!=source['sha256']):
                raise ValueError('Exact full original occurrence required')
            box=b['bbox']
            if (not isinstance(box,list) or len(box)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in box)
                    or box[0]>=box[2] or box[1]>=box[3]):
                raise ValueError('Finite original source geometry required')
            used.append(u['id']);out.append(b)
        return out
    def span(anchors):
        return [min(a['bbox'][0] for a in anchors),min(a['bbox'][1] for a in anchors),
                max(a['bbox'][2] for a in anchors),max(a['bbox'][3] for a in anchors)]
    def ordered(anchors):
        if any(a['bbox'][3]>=b['bbox'][1] for a,b in zip(anchors,anchors[1:])):
            raise ValueError('Original fragment vertical order changed')
    def overlap(a,b,axis):
        return max(a[axis],b[axis])<min(a[axis+2],b[axis+2])
    fields(profile['metadata'],{str(p) for p in spec.METADATA},{str(p) for p in spec.METADATA})
    metadata={str(p):original(profile['metadata'][str(p)],p,ids) for p,ids in spec.METADATA.items()}
    if list(profile['prose'])!=list(spec.PROSE):
        raise ValueError('Complete prose and recognition qualifications required')
    prose={}
    for key,(page,ids,meaning) in spec.PROSE.items():
        row=profile['prose'][key]
        fields(row,{'meaning','anchors'},{'meaning','anchors'})
        if row['meaning']!=meaning:
            raise ValueError('Supplied recognition/scope meaning changed')
        anchors=original(row['anchors'],page,ids);ordered(anchors)
        prose[key]={'meaning':meaning,'anchors':anchors}
    fields(profile['typographic'],{'279'},{'279'})
    typographic=original(profile['typographic']['279'],279,[28,97])
    if any(a['quote']!='\xad' for a in typographic):
        raise ValueError('Original typographic occurrences changed')
    excluded=original(profile['excluded_note27'],282,list(range(10,86)))
    if excluded[0]['quote']!='27\u2003Capital structure management and statement' or excluded[1]['quote']!='of cash flows':
        raise ValueError('Actual Note27 boundary changed')

    fair_in=profile['fair_table']
    fkeys={'title','unit','years','rows','footnote'}
    fields(fair_in,fkeys,fkeys)
    title=original([fair_in['title']],279,[31])[0]
    unit=original([fair_in['unit']],279,[32])[0]
    fields(fair_in['years'],{'2022','2021'},{'2022','2021'})
    years={y:original([fair_in['years'][y]],279,[n])[0] for y,n in [('2022',33),('2021',34)]}
    if unit['quote']!='Million €' or [a['quote'] for a in years.values()]!=['December 31, 2022','December 31, 2021']:
        raise ValueError('Fair-value table units or dates changed')
    if [r['id'] for r in fair_in['rows']]!=[r[0] for r in spec.FAIR_ROWS]:
        raise ValueError('Complete fair-value rows required')
    fair_rows=[];last_bottom=max(a['bbox'][3] for a in years.values())
    for row,(name,label_ids,cell_ids,parent) in zip(fair_in['rows'],spec.FAIR_ROWS):
        fields(row,{'id','parent','label','cells'},{'id','parent','label','cells'})
        if row['parent']!=parent:
            raise ValueError('Subordinate of-which scope changed')
        label=original(row['label'],279,label_ids);lb=span(label)
        if lb[1]<=last_bottom:
            raise ValueError('Fair-value row order changed')
        last_bottom=lb[3]
        fields(row['cells'],{'2022','2021'},{'2022','2021'})
        cells={}
        for (year,head),ids in zip(years.items(),cell_ids):
            anchors=original(row['cells'][year],279,ids)
            b=span(anchors)
            if not overlap(lb,b,1) or not overlap(head['bbox'],b,0) or lb[2]>=b[0]:
                raise ValueError('Fair-value cell geometry changed')
            marker='a' if (name,year)==('commodity_designated','2021') else None
            cells[year]={**numeric(anchors[0]['quote'],marker),'source':anchors}
        fair_rows.append({'id':name,'parent':parent,'label':label,'cells':cells})
    fair_note=original([fair_in['footnote']],279,[65])[0]
    if fair_note['quote']!=spec.FOOTNOTES['fair'] or fair_note['bbox'][1]<=last_bottom:
        raise ValueError('Fair-value disposal-group footnote changed')
    fair_rows[8]['cells']['2021']['footnote']=deepcopy(fair_note)
    fair={'title':title,'unit':unit,'years':years,'rows':fair_rows,'footnote':fair_note}

    if [t['year'] for t in profile['effects_tables']]!=['2022','2021']:
        raise ValueError('Both ordered date-specific effects tables required')
    effects=[]
    for table in profile['effects_tables']:
        keys={'year','title','unit','group_headers','columns','shared_header','rows','footnote'}
        fields(table,keys,keys)
        year=table['year'];title_id,unit_id,note_id=(3,4,119) if year=='2022' else (120,121,213)
        title=original([table['title']],281,[title_id])[0]
        unit=original([table['unit']],281,[unit_id])[0]
        if title['quote']!='Cash flow hedge accounting effects in '+year or unit['quote']!='Million €':
            raise ValueError('Effects table date or unit changed')
        if len(table['group_headers'])!=4 or [c['id'] for c in table['columns']]!=spec.COLUMNS:
            raise ValueError('Complete grouped and individual column headings required')
        group_headers=[]
        for group,ids,members in zip(table['group_headers'],spec.GROUP_HEADERS[year],spec.HEADER_MEMBERS):
            fields(group,{'members','anchors'},{'members','anchors'})
            if group['members']!=members:
                raise ValueError('Grouped heading meaning changed')
            anchors=original(group['anchors'],281,ids);ordered(anchors)
            group_headers.append({'members':members,'anchors':anchors})
        shared=table['shared_header']
        fields(shared,{'original','associations','separator'},{'original','associations','separator'})
        shared_original=original([shared['original']],281,[spec.SHARED[year]])[0]
        if shared_original['quote']!='transaction ness amount':
            raise ValueError('Original joined header changed')
        expected={'hedged_change':(0,11,'transaction'),'ineffectiveness':(12,23,'ness amount')}
        fields(shared['associations'],expected,expected)
        associations={}
        for key,(start,end,quote) in expected.items():
            a=bind(graph,shared['associations'][key])
            if (a['unit'],a['start'],a['end'],a['quote'])!=(shared_original['unit'],start,end,quote):
                raise ValueError('Disjoint original shared-header character association changed')
            associations[key]=a
        separator=bind(graph,shared['separator'])
        if (separator['unit'],separator['start'],separator['end'],separator['quote'])!=(shared_original['unit'],11,12,' '):
            raise ValueError('Original shared-header separator must remain')
        columns=[];column_boxes={};last_right=0
        for column,ids in zip(table['columns'],spec.HEADERS[year]):
            fields(column,{'id','kind','headers'},{'id','kind','headers'})
            name=column['id'];kind='text' if name in spec.TEXT_COLUMNS else 'integer_millions'
            if column['kind']!=kind:
                raise ValueError('Caption,rate and monetary quantities cannot be interchanged')
            anchors=original(column['headers'],281,ids);ordered(anchors);b=span(anchors)
            if b[0]<=last_right or b[1]<=unit['bbox'][3]:
                raise ValueError('Effects column geometry/order changed')
            last_right=b[2];column_boxes[name]=b
            columns.append({'id':name,'kind':kind,'headers':anchors,'shared_header_part':associations.get(name),
                            'geometry_basis':'UNSHARED_ORIGINAL_HEADER_FRAGMENTS'})
        for group in group_headers:
            b=span(group['anchors'])
            selected=[column_boxes[c] for c in group['members']]
            if b[1]<=unit['bbox'][3] or b[3]>=min(c[1] for c in selected):
                raise ValueError('Grouped header vertical scope changed')
        row_specs=spec.EFFECT_ROWS[year]
        if [r['id'] for r in table['rows']]!=[r[0] for r in row_specs]:
            raise ValueError('Complete effects rows required')
        rows=[];last_bottom=max(b[3] for b in column_boxes.values())
        for row,(name,label_ids,cell_ids) in zip(table['rows'],row_specs):
            fields(row,{'id','label','cells'},{'id','label','cells'})
            label=original(row['label'],281,label_ids);ordered(label);lb=span(label)
            if lb[1]<=last_bottom or lb[2]>=min(b[0] for b in column_boxes.values()):
                raise ValueError('Effects row geometry/order changed')
            fields(row['cells'],spec.COLUMNS,spec.COLUMNS)
            cells={};row_bottom=lb[3]
            for column,ids in zip(spec.COLUMNS,cell_ids):
                anchors=original(row['cells'][column],281,ids)
                if anchors:
                    ordered(anchors);b=span(anchors)
                    if not overlap(lb,b,1) or not overlap(column_boxes[column],b,0) or lb[2]>=b[0]:
                        raise ValueError('Effects cell original row/column alignment changed')
                    row_bottom=max(row_bottom,b[3])
                if column in spec.TEXT_COLUMNS:
                    value=text_cell(anchors,blank_allowed=name=='total')
                else:
                    if len(anchors)!=1:
                        raise ValueError('Complete original numeric cell required')
                    value=numeric(anchors[0]['quote'],'a' if (name,column)==('commodity','reclassified') else None)
                cells[column]={**value,'source':anchors}
            rows.append({'id':name,'label':label,'cells':cells});last_bottom=row_bottom
        footnote=original([table['footnote']],281,[note_id])[0]
        if footnote['quote']!=spec.FOOTNOTES[year] or footnote['bbox'][1]<=last_bottom:
            raise ValueError('Inventory-cost and consumption footnote changed')
        next(r for r in rows if r['id']=='commodity')['cells']['reclassified']['footnote']=deepcopy(footnote)
        effects.append({'year':year,'title':title,'unit':unit,'group_headers':group_headers,'columns':columns,
            'shared_header':{'original':shared_original,'associations':associations,'separator':separator,
                             'substring_geometry_inferred':False},'rows':rows,'footnote':footnote})
    if Counter(used)!=Counter(u['id'] for u in pages):
        raise ValueError('Every original page occurrence must be accounted exactly once')
    incorporation=prior['answer']['incorporation']
    if incorporation['status']!='UNRESOLVED' or incorporation['selected_reading'] is not None:
        raise ValueError('Unresolved incorporation must be preserved')
    scopes=[{'id':r['id'],'condition':r['condition'],'all_note_pages_in_candidate':all(p in r['candidate_pages'] for p in range(279,283)),
             'legal_incorporation_established':False} for r in incorporation['readings']]
    if not all(r['all_note_pages_in_candidate'] for r in scopes):
        raise ValueError('Expected both candidate sets to include the note pages')
    return {'version':VERSION,'profile_sha256':digest(profile),'metadata':metadata,'prose':prose,'typographic':typographic,
        'fair_table':fair,'effects_tables':effects,'excluded_note27':excluded,
        'page_occurrences_accounted':452,'note_occurrences':376,'excluded_occurrences':76,
        'grid_positions':128,'numeric_positions':101,'printed_text_positions':21,'blank_positions':6,
        'shared_header_occurrences':2,'footnoted_numeric_positions':3,
        'comparisons':arithmetic(fair,effects,prior),'incorporation_alternatives':scopes,
        'recognition_rule':{'asset_cost_derecognition_is_immediate_profit_recycling':False,
            'source':prose['closing_rule'],'table_qualifications':[t['footnote'] for t in effects]},
        'earlier_hedge_net_difference':deepcopy(next(c for c in prior['oci_note_review']['comparisons'] if c['name']=='2022:hedge-net')),
        'unique_bridge_to_prior_net_established':False,'rounding_cause_established':False,
        'nonmonetary_prices_rates':'Retained in complete original prose with their units and periods;not parsed as integer-million amounts',
        'field_associations':'SUPPLIED_EXPOSED_REVIEW','independent_legal_acceptance':False,
        'financial_values_validated':False,'selected_reading':None,'profile':deepcopy(profile)}


def consume(products,prior_profiles,profile,root,*,expected_prior_profiles_sha256,expected_profile_sha256):
    fields(prior_profiles,{'statement','equity','oci'},{'statement','equity','oci'})
    if digest(prior_profiles)!=expected_prior_profiles_sha256:
        raise ValueError('Pinned complete preceding profiles changed')
    sp,ep,np=[prior_profiles[k] for k in ('statement','equity','oci')]
    prior=basf_oci_notes.consume(products,sp,ep,np,root,expected_statement_profile_sha256=digest(sp),
        expected_equity_profile_sha256=digest(ep),expected_profile_sha256=digest(np))
    review=evaluate(products['P1']['payload']['graph'],prior,profile,root,expected_profile_sha256=expected_profile_sha256)
    return {**prior,'hedge_note_review':review}
