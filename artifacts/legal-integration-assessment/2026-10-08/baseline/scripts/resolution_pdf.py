"""Locate all retained disputes and resolve only verified split-word typography."""
from collections import Counter
from resolution_support import *


def split_word_evidence(issue, words):
    """A single printed hyphenated word may be split into tokens by a parser.

    Whole-word matching must be unique on the located page. General removal of
    spaces (now here/nowhere) or punctuation is deliberately unsupported.
    """
    left=issue['change']['left_tokens'];right=issue['change']['right_tokens']
    if not left or not right or ''.join(left)!=''.join(right):return None
    one,many=(left,right) if len(left)==1 else (right,left)
    if len(one)!=1 or len(many)<2 or '-' not in one[0]:return None
    token=one[0]
    # At least one split must abut the preserved hyphen, never any space at all.
    if any(not (a.endswith('-') or b.startswith('-')) for a,b in zip(many,many[1:])):return None
    matches=[w for w in words if w['text']==token]
    if len(matches)!=1:return None
    w=matches[0]
    return {'rule':'LOCATED_HYPHEN_TOKEN_SPLIT','printed_word':token,
            'bbox':[w[k] for k in ('x0','top','x1','bottom')],
            'evidence_limit':'pdfplumber glyph layout and preserved source/raster; no legal meaning inference'}


def locate(issue, words):
    tokens=set(issue['change']['left_tokens']+issue['change']['right_tokens'])
    hits=[w for w in words if w['text'] in tokens]
    return [{'text':w['text'],'bbox':[w[k] for k in ('x0','top','x1','bottom')]} for w in hits]


def run(out):
    pages=read(ROOT/'docs/implementation/interpretation-round13/pdf-structure-reference.json')['pages']
    old=read(OLD/'execution-reviewed/action-0002/pdf/result.json');rows=[]
    for page in pages:
        for name,key in [('layout','layout_sha256'),('raster','raster_sha256'),('previous','previous_sha256')]:
            if sha(ROOT/page[name])!=page[key]:raise LegalMathError('E_INTEGRITY')
        words=read(ROOT/page['layout'])['words']
        prior=next(r for r in old['rows'] if r['document']==page['document'] and r['page']==page['page'])
        for issue in prior['reconciliation']['remaining']:
            evidence=split_word_evidence(issue,words)
            rows.append({'issue_id':issue['issue_id'],'original':issue,'document':page['document'],
                'page':page['page'],'layout_sha256':page['layout_sha256'],'raster':page['raster'],
                'locations':locate(issue,words),'resolution':evidence,
                'status':'TYPOGRAPHY_RESOLVED' if evidence else 'MATERIALITY_UNRESOLVED'})
    expected={i['issue_id'] for i in read(OUT/'issue-inventory.json')['pdf_issues']}
    if len(rows)!=339 or {r['issue_id'] for r in rows}!=expected:raise LegalMathError('E_INTEGRITY')
    value={'status':'EVERY_RESIDUAL_LOCATED_OR_RETAINED','issues':rows,'counts':dict(Counter(r['status'] for r in rows)),
           'unlocated':sum(not r['locations'] for r in rows),'prior_footer_resolutions':54,
           'independent_visual_adjudication':False,'release_eligible':False}
    save(out/'result.json',value);save(OUT/'pdf-resolution.json',value);return value
