"""Coverage of explicitly required source regions, without page-completeness claims."""
from pathlib import Path
import math

from .successor.anchors import fields
from .successor.contracts import digest
from .successor.layout_adapter import project_layout
from .successor.occurrences import anchor

VERSION='declared-region-coverage.v1'


def _box(value):
    return (isinstance(value,(list,tuple)) and len(value)==4 and
            all(type(x) in (int,float) and math.isfinite(x) for x in value) and
            value[0]<value[2] and value[1]<value[3])


def _text(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError('Nonempty region review text required')


def _file(root,name,expected):
    if not isinstance(name,str) or Path(name).is_absolute():
        raise ValueError('Relative evidence path required')
    target=(root/name).resolve()
    if not target.is_relative_to(root) or not target.is_file() or digest(target.read_bytes())!=expected:
        raise ValueError('Source/render identity changed or unavailable')


def evaluate_regions(graph,inventory,root,*,expected_inventory_sha256):
    """Check all declared regions against retained words and actual projection.

    The caller must pin a reviewed inventory, including displayed-page geometry.
    File integrity does not prove render fidelity, complete inventory or source
    authenticity. A matched supplied reading never certifies a whole table/page.
    """
    keys={'version','source_graph_sha256','reviewer','scope','pages'}
    fields(inventory,keys,keys)
    if (digest(inventory)!=expected_inventory_sha256 or inventory['version']!=VERSION or
            inventory['source_graph_sha256']!=digest(graph)):
        raise ValueError('Pinned inventory or source graph changed')
    if inventory['scope']!='DECLARED_REGIONS_ONLY':
        raise ValueError('Unsupported whole-page coverage claim')
    reviewer=inventory['reviewer']
    fields(reviewer,{'identity','basis','independent'},{'identity','basis','independent'})
    _text(reviewer['identity'])
    if reviewer['basis']!='AGENT_EXPOSED_DEVELOPMENT_REVIEW' or reviewer['independent'] is not False:
        raise ValueError('Unsupported independent review claim')
    units=graph['units'];by_id={u['id']:u for u in units}
    if len(units)!=len(by_id):raise ValueError('Duplicate source occurrence')
    if any(u['text_sha256']!=digest(u['raw'].encode()) for u in units):
        raise ValueError('Source transcription changed')
    root=Path(root).resolve();seen_pages=set();seen_regions=set();out=[]
    if not isinstance(inventory['pages'],list) or not inventory['pages']:
        raise ValueError('Nonempty required-region inventory needed')
    for page in inventory['pages']:
        keys={'document','source_path','source_sha256','page','display_rect',
              'render_path','render_sha256','regions'}
        fields(page,keys,keys)
        key=(page['document'],page['page']);rect=page['display_rect']
        if (type(page['page']) is not int or page['page']<1 or key in seen_pages or
                not _box(rect) or rect[:2]!=[0,0]):
            raise ValueError('Invalid or duplicate source-page descriptor')
        seen_pages.add(key)
        raw=[u for u in units if u['document']==page['document']]
        current=[u for u in raw if u['page']==page['page']]
        if not current or any(u['source_sha256']!=page['source_sha256'] for u in raw):
            raise ValueError('Foreign source edition or unrepresented page')
        _file(root,page['source_path'],page['source_sha256'])
        _file(root,page['render_path'],page['render_sha256'])
        if not isinstance(page['regions'],list) or not page['regions']:
            raise ValueError('Every reviewed page requires declared regions')
        for region in page['regions']:
            fields(region,{'id','bbox','kind','reason','reading'},
                   {'id','bbox','kind','reason','reading'})
            _text(region['id']);_text(region['reason'])
            box=region['bbox']
            if (region['id'] in seen_regions or region['kind'] not in {'table','paragraph','heading','figure'} or
                    not _box(box) or not (0<=box[0]<box[2]<=rect[2] and 0<=box[1]<box[3]<=rect[3])):
                raise ValueError('Duplicate or invalid required region')
            seen_regions.add(region['id'])
            if region['reading'] is not None:_text(region['reading'])
            anchors=[];partial=[];unknown=[]
            for unit in current:
                words=unit.get('words',[])
                if unit['raw'].strip() and (not unit.get('visible') or not words or not _box(unit.get('bbox')) or unit.get('geometry_issues')):
                    unknown.append(unit['id'])
                previous=-1
                for word in sorted(words,key=lambda w:w['start']):
                    start,end=word['start'],word['end']
                    if (type(start) is not int or type(end) is not int or
                            not 0<=start<end<=len(unit['raw']) or start<previous or
                            unit['raw'][start:end]!=word['text']):
                        raise ValueError('Invalid retained word interval or transcription')
                    previous=end
                    wb=word.get('bbox')
                    if not _box(wb):
                        unknown.append(unit['id']);continue
                    intersects=(max(box[0],wb[0])<min(box[2],wb[2]) and
                                max(box[1],wb[1])<min(box[3],wb[3]))
                    if not intersects:continue
                    a=anchor(unit,start,end)
                    if box[0]<=wb[0] and box[1]<=wb[1] and wb[2]<=box[2] and wb[3]<=box[3]:
                        anchors.append(a)
                    else:partial.append(a)
            projection=None
            if unknown:status='UNRESOLVED_WORD_GEOMETRY'
            elif partial:status='PARTIAL_WORD_INTERSECTION'
            elif not anchors:status='REQUIRED_CONTENT_UNAVAILABLE'
            elif region['reading'] is None:status='RETAINED_WORDS_WITHOUT_REVIEWED_TRANSCRIPTION'
            else:
                l,t,r,b=box
                proposal={'texts':[{'self_ref':region['id'],'label':region['kind'],
                    'text':region['reading'],'prov':[{'page_no':page['page'],
                        'bbox':{'l':l,'t':t,'r':r,'b':b,'coord_origin':'TOPLEFT'}}]}]}
                projection=project_layout(raw,proposal,source_sha256=page['source_sha256'])
                status=('MATCHED_DECLARED_TEXT' if len(projection['mappings'])==1 and not projection['failures']
                        and not projection['mappings'][0]['candidate_changes'] else 'TRANSCRIPTION_OR_PROJECTION_UNRESOLVED')
            out.append({'id':region['id'],'document':page['document'],'source_sha256':page['source_sha256'],
                'page':page['page'],'bbox':box,'render_sha256':page['render_sha256'],'kind':region['kind'],
                'reason':region['reason'],'status':status,'retained_word_anchors':anchors,
                'partial_word_anchors':partial,'unknown_geometry_units':sorted(set(unknown)),
                'supplied_reading':region['reading'],'projection':projection,
                'native_page_nonspace_characters':sum(len(''.join(u['raw'].split())) for u in current if u.get('method')=='pdftotext-bbox-layout')})
    return {'version':VERSION,'source_graph_sha256':digest(graph),
            'inventory_sha256':expected_inventory_sha256,'scope':'DECLARED_REGIONS_ONLY','regions':out,
            'declared_readings_matched':all(r['status']=='MATCHED_DECLARED_TEXT' for r in out),
            'page_complete':False,'document_complete':False,'may_claim_coverage':False,
            'independent_legal_acceptance':False,'raw_replaced':False,'legal_scope_inferred':False}


def consume_with_region_coverage(products,inventory,root,*,expected_inventory_sha256):
    from .successor.service import consume
    coverage=evaluate_regions(products['P1']['payload']['graph'],inventory,root,
                              expected_inventory_sha256=expected_inventory_sha256)
    return {'answer':consume(products,root,include_artifacts=True),'region_coverage':coverage}
