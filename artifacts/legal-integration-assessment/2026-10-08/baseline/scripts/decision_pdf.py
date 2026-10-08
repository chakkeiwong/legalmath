"""Review located PDF structure and preserve every unresolved token difference."""
from pathlib import Path
import json
from copy import deepcopy
from legalmath.canonical import raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.source_structure import compare_region,reconcile_footer
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/implementation/interpretation-round13'
BASE=ROOT/'artifacts/interpretation/round11/M2/attempt-01/sources'
OLD=ROOT/'artifacts/interpretation/round12/P1/attempt-05/sources'

def region(words,box):
    selected=[w for w in words if w['x0']>=box[0]-0.1 and w['x1']<=box[2]+0.1 and w['top']>=box[1]-0.1 and w['bottom']<=box[3]+0.1]
    return ' '.join(w['text'] for w in selected)

def freeze():
    records=[]
    for path in sorted(OLD.glob('*/page-*/page.json')):
        old=json.loads(path.read_text());p=old['regions'];doc=path.parent.parent.name;num=p['page']
        layout=BASE/doc/f'pdfplumber-{num:02}.json';words=json.loads(layout.read_text())
        raster=BASE/doc/f'page-{num:02}'/'raster.png'
        if raw_digest(raster.read_bytes())!=p['raster_sha256']:raise ValueError('Raster binding differs')
        label=next(w for w in reversed(words['words']) if w['text']=='Page')
        footer_box=[label['x0']-1,label['top']-1,words['width'],label['bottom']+1]
        footer={'text':region(words['words'],footer_box),'bbox':footer_box,'raster_sha256':p['raster_sha256'],
                'visual_inspection':True,'review_basis':'Author inspected retained page contact sheets; independent human review pending'}
        # A full body region keeps footnotes. Only the located running footer is
        # outside it; no numbers or negations are deleted to obtain agreement.
        box=[0,0,words['width'],label['top']-2]
        ref={'source_sha256':p['source_sha256'],'raster_sha256':p['raster_sha256'],'page':num,
             'bbox':box,'text':region(words['words'],box)}
        links=[]
        if doc=='23EC35-annex1' and num==1:
            body=next(w for w in words['words'] if w['text']=='obligations1')
            links.append({'kind':'FOOTNOTE_ATTACHMENT','marker':'1','from_bbox':[body[k] for k in ('x0','top','x1','bottom')],
                          'to_bbox':[72,729,540,774],'meaning':'superscript 1 defines suitability obligations',
                          'review_basis':'Visible superscript and bottom note on retained pixels'})
        if doc=='23EC35-annex1' and num==5:
            links += [{'kind':'FOOTNOTE_ATTACHMENT','marker':'2','from_bbox':[96,140,534,227],
                       'to_bbox':[72,720,540,751],'meaning':'paragraph 11.1 product summary refers to prevailing FAQ guidance',
                       'review_basis':'Visible superscript after investment product'},
                      {'kind':'FOOTNOTE_ATTACHMENT','marker':'3','from_bbox':[96,202,534,241],
                       'to_bbox':[72,750,540,775],'meaning':'paragraph 11.1 permits written/verbal combination with records',
                       'review_basis':'Visible superscript after public domain or data providers'}]
        if doc=='23EC35-annex2' and num==2:
            links.append({'kind':'FOOTNOTE_ATTACHMENT','marker':'1','from_bbox':[96,200,535,290],
                          'to_bbox':[72,740,540,780],'meaning':'VA-related products definition qualifies product categories',
                          'review_basis':'Visible superscript after VA-related products'})
        if doc=='23EC49-appendix':
            top=466 if num==1 else 440
            for col,(a,b,label) in enumerate([(80,185,'7-day'),(188,295,'1-day'),(297,405,'30-day'),(406,535,'Most recent 1-year')]):
                cell=[a,top,b,top+28]
                links.append({'kind':'COLUMN_HEADER','column':col,'bbox':cell,'text':region(words['words'],cell),
                              'expected_prefix':label,'review_basis':'Visible four-column return/yield display, left to right'})
        records.append({'document':doc,'page':num,'layout':str(layout.relative_to(ROOT)),
                        'layout_sha256':raw_digest(layout.read_bytes()),'raster':str(raster.relative_to(ROOT)),
                        'previous':str(path.relative_to(ROOT)), 'previous_sha256':raw_digest(path.read_bytes()),
                        'width':words['width'],'height':words['height'],'source_sha256':p['source_sha256'],
                        'raster_sha256':p['raster_sha256'],'reference':ref,'footer':footer,'relationships':links})
    save(DOC/'pdf-structure-reference.json',{'basis':'Author-visible development reference frozen before footer reconciliation',
         'independent_legal_reference':False,'pages':records})

def run(out):
    value=json.loads((DOC/'pdf-structure-reference.json').read_text());rows=[]
    for page in value['pages']:
        for path,sha in [(page['layout'],page['layout_sha256']),(page['previous'],page['previous_sha256']),
                         (page['raster'],page['raster_sha256'])]:
            if raw_digest((ROOT/path).read_bytes())!=sha:raise ValueError('Source structure evidence changed')
        data=json.loads((ROOT/page['layout']).read_text())
        text=region(data['words'],page['reference']['bbox'])
        checked=compare_region(page['reference'],text,page)
        previous=json.loads((ROOT/page['previous']).read_text())['regions']
        reconciliation=reconcile_footer(previous,page['footer'])
        relationships=[]
        for link in page['relationships']:
            if link['kind']=='COLUMN_HEADER':
                actual=region(data['words'],link['bbox'])
                if actual!=link['text'] or not actual.startswith(link['expected_prefix']):raise ValueError('Column header attachment changed')
            else:
                actual=region(data['words'],link['to_bbox'])
                if not actual.startswith(link['marker']+' '):raise ValueError('Footnote target marker differs')
            relationships.append({**link,'actual_region_text':actual,'status':'LOCATED_RELATION_CHECKED',
                                  'independent_semantic_approval':False})
        rows.append({'document':page['document'],'page':page['page'],'region':checked,
                     'reconciliation':reconciliation,'relationships':relationships})
    # Plant substantive changes into actual page text. These are separate from
    # benign formatting and each must be detected against the frozen reference.
    faults=[]
    ref=value['pages'][0];text=ref['reference']['text']
    changes=[('negation','not',''),('quantity','HK$40','HK$41'),('unit','million','billion'),
             ('exception','excluding primary residence','including primary residence')]
    for kind,before,after in changes:
        target=next(p for p in value['pages'] if before in p['reference']['text'])
        changed=target['reference']['text'].replace(before,after,1)
        result=compare_region(target['reference'],changed,target)
        if result['status']!='REGION_DISCREPANCY':raise ValueError('Undetected source fault')
        faults.append({'kind':kind,'result':result['status']})
    header_page=next(p for p in value['pages'] if any(l['kind']=='COLUMN_HEADER' for l in p['relationships']))
    header=next(l for l in header_page['relationships'] if l['kind']=='COLUMN_HEADER')
    header_reference={k:header_page[k] for k in ('source_sha256','raster_sha256','page')}
    header_reference.update(bbox=header['bbox'],text=header['text'])
    header_fault=compare_region(header_reference,header['text'].replace('7-day','1-day'),header_page)
    if header_fault['status']!='REGION_DISCREPANCY':raise ValueError('Undetected column header fault')
    faults.append({'kind':'column_header','result':header_fault['status']})
    wrap=compare_region(ref['reference'],ref['reference']['text'].replace(' ','\n'),ref)
    if wrap['status']!='REGION_TEXT_MATCH':raise ValueError('Benign wrapping rejected')
    report={'status':'EXECUTED_SOURCE_STRUCTURE_REVIEW','pages':len(rows),'rows':rows,
            'resolved_footer_issues':sum(len(r['reconciliation']['resolved']) for r in rows),
            'remaining_issues':sum(len(r['reconciliation']['remaining']) for r in rows),
            'checked_relations':sum(len(r['relationships']) for r in rows),
            'faults':faults,'wrapping':wrap['status'],'release_eligible':False}
    save(Path(out)/'result.json',report);return report
if __name__=='__main__':freeze()
