"""Conservative resolution against retained, located page evidence."""
import re
from ...canonical import digest,raw_digest
from ...errors import LegalMathError
from .diversity import identity


def verify_region(region, page):
    if (region['source_sha256']!=page['source_sha256'] or region['raster_sha256']!=page['raster_sha256']
            or region['page']!=page['page']):raise LegalMathError('E_STALE_REVIEW')
    box=region['bbox']; width,height=page['width'],page['height']
    if (len(box)!=4 or not 0<=box[0]<box[2]<=width or not 0<=box[1]<box[3]<=height
            or not region['text'].strip()):raise LegalMathError('E_REFERENCE')
    return region


def compare_region(reference, actual_text, page):
    verify_region(reference,page)
    normalize=lambda s:re.sub(r'\s+',' ',s).strip()
    equal=normalize(reference['text'])==normalize(actual_text)
    return {'status':'REGION_TEXT_MATCH' if equal else 'REGION_DISCREPANCY',
            'reference_hash':identity(reference),'actual_text':actual_text,
            'materiality':'WHITESPACE_ONLY' if equal else 'REQUIRES_EVIDENCE',
            'page':page['page'],'release_eligible':False}


def reconcile_footer(page_report, footer):
    """Resolve only exact relocation of a visually confirmed running page label.

    Numeric requirements, superscripts and other text are never normalized away.
    The full residual issue set survives even when some pairs differ harmlessly.
    """
    if not footer['visual_inspection'] or footer['raster_sha256']!=page_report['raster_sha256']:
        raise LegalMathError('E_STALE_REVIEW')
    tokens=footer['text'].split();resolved=[];remaining=[]
    for issue in page_report['issues']:
        change=issue['change'];a,b=change['left_tokens'],change['right_tokens']
        if ((a==tokens and not b) or (b==tokens and not a)):
            partner=next((j for j in page_report['issues'] if j['issue_id']!=issue['issue_id']
                and j['routes']==issue['routes'] and j['change']['left_tokens']==b
                and j['change']['right_tokens']==a),None)
            if partner:
                resolved.append({'issue_id':issue['issue_id'],'partner':partner['issue_id'],
                    'disposition':'RUNNING_FOOTER_RELOCATED','evidence':footer});continue
        remaining.append(issue)
    return {'resolved':resolved,'remaining':remaining,'total':len(page_report['issues']),
            'status':'PARTIAL_SOURCE_RESOLUTION' if resolved else 'SOURCE_DISCREPANCIES_RETAINED',
            'release_eligible':False}
