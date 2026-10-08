"""Bounded source acquisition, located PDF review, and exact-ratio development checks."""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from html import escape
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import re
import subprocess
import sys

from resolution_support import ROOT, AT, JDK, read, save, sha
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.ir.evaluate import evaluate
from legalmath.java.manifest import build_candidate, verify_candidate

SOURCE_URLS = {
    '23ec52-appendix.pdf': 'https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?appendix=0&lang=EN&refNo=23EC52',
    '23ec44-terms.pdf': 'https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?appendix=0&lang=EN&refNo=23EC44',
}


def acquire_public(out):
    """Capture two exact official dependencies; download success does not close meaning."""
    from pypdf import PdfReader
    out.mkdir(parents=True, exist_ok=True)
    records = []
    for filename, url in SOURCE_URLS.items():
        path = out/filename
        receipt = out/(filename+'.receipt.json')
        if receipt.exists():
            row = read(receipt)
            if row.get('sha256') and sha(path) != row['sha256']:
                raise LegalMathError('E_INTEGRITY', details='Changed acquisition')
            records.append(row)
            continue
        cmd = ['curl', '--fail', '--location', '--proto', '=https', '--proto-redir', '=https',
               '--max-redirs', '2', '--connect-timeout', '15', '--max-time', '60',
               '--max-filesize', '20000000', '--silent', '--show-error', '--output', str(path),
               '--write-out', '%{url_effective}', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
        row = {'url': url, 'command': cmd, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
               'exit_code': result.returncode, 'final_url': result.stdout.strip(),
               'status': 'UNAVAILABLE', 'legal_sufficiency_established': False}
        if result.returncode == 0:
            if urlparse(row['final_url']).hostname != 'apps.sfc.hk' or not path.read_bytes().startswith(b'%PDF-'):
                raise LegalMathError('E_INTEGRITY', details='Unexpected official PDF response')
            pages = [{'page': i+1, 'text': p.extract_text() or ''} for i, p in enumerate(PdfReader(path).pages)]
            save(out/(filename+'.text.json'), {'source_sha256': sha(path), 'pages': pages})
            row.update(status='ACQUIRED_NOT_ADJUDICATED', sha256=sha(path), path=str(path.relative_to(ROOT)),
                       pages=len(pages), extraction=str((out/(filename+'.text.json')).relative_to(ROOT)))
        else:
            row['error'] = result.stderr[-1000:]
        save(receipt, row)
        records.append(row)
    return records


def footer_evidence(issue, page, layout):
    """Resolve only a unique, exact footer phrase already located on the raster."""
    change = issue['original']['change']
    a, b = change['left_tokens'], change['right_tokens']
    tokens = a or b
    if a and b or not tokens or change['kind'] not in ('delete', 'insert'):
        return None
    footer = page.get('footer', {})
    if (' '.join(tokens) != footer.get('text') or not footer.get('visual_inspection')
            or not re.fullmatch(r'Page [1-9][0-9]* of [1-9][0-9]*', footer['text'])
            or footer.get('raster_sha256') != page['raster_sha256']):
        return None
    words = layout['words']
    matches = [words[i:i+len(tokens)] for i in range(len(words)-len(tokens)+1)
               if [w['text'] for w in words[i:i+len(tokens)]] == tokens]
    if len(matches) != 1: return None
    x0, top, x1, bottom = footer['bbox']
    if top < page['height'] * .9: return None
    if any(w['x0'] < x0 or w['x1'] > x1 or w['top'] < top or w['bottom'] > bottom for w in matches[0]):
        return None
    return {'rule': 'EXACT_UNIQUE_LOCATED_PAGE_FOOTER', 'text': footer['text'], 'bbox': footer['bbox'],
            'raster_sha256': page['raster_sha256'], 'prior_visual_basis': footer.get('review_basis'),
            'limit': 'Only this page-number phrase is layout; no body text or footnote is removed.'}


def pdf_review(source, out, pages):
    """Create inspectable source-linked crops; ambiguous locations retain whole pages."""
    out.mkdir(parents=True, exist_ok=True)
    by_page = {(p['document'], p['page']): p for p in pages}
    rows = []; crops=[]; html = ['<!doctype html><meta charset="utf-8"><title>Round 15 PDF disputes</title>',
        '<style>body{font:16px sans-serif;margin:2rem;max-width:1000px}img{max-width:900px;width:100%}details{margin:1rem 0}pre{white-space:pre-wrap}</style>',
        '<h1>PDF differences requiring source review</h1><p>Crop locations are parser-derived. '
        'Multiple or uncertain locations retain wider context. A crop does not establish legal materiality.</p>']
    for page in pages:
        for key in ('layout', 'raster', 'previous'):
            if sha(ROOT/page[key]) != page[key+'_sha256']:
                raise LegalMathError('E_INTEGRITY', details='PDF source reference changed')
    for issue in source['issues']:
        page = by_page[(issue['document'], issue['page'])]
        if (issue['original']['source_sha256']!=page['source_sha256'] or
                issue['original']['raster_sha256']!=page['raster_sha256'] or
                issue['layout_sha256']!=page['layout_sha256']):
            raise LegalMathError('E_INTEGRITY',details='Issue refers to a different source page')
        layout = read(ROOT/page['layout'])
        row = deepcopy(issue)
        resolution = footer_evidence(issue, page, layout) if issue['status'] == 'MATERIALITY_UNRESOLVED' else None
        if resolution:
            row.update(status='FOOTER_LAYOUT_RESOLVED', resolution=resolution)
        boxes = [r['bbox'] for r in issue['locations']]
        if boxes:
            bbox = [max(0, min(b[0] for b in boxes)-30), max(0, min(b[1] for b in boxes)-45),
                    min(page['width'], max(b[2] for b in boxes)+30),
                    min(page['height'], max(b[3] for b in boxes)+45)]
        else: bbox = [0, 0, page['width'], page['height']]
        # Full-width context preserves columns and headings surrounding a local hit.
        bbox[0], bbox[2] = 0, page['width']
        crop = out/(issue['issue_id']+'.png')
        raster = os.path.relpath(ROOT/issue['raster'], crop.parent)
        crops.append({'source':str(ROOT/issue['raster']),'output':str(crop),'bbox':bbox,
                      'width':page['width'],'height':page['height']})
        row.update(review_crop=str(crop.relative_to(ROOT)),
                   crop_bbox=bbox, full_page=str((ROOT/issue['raster']).relative_to(ROOT)),
                   localization='TOKEN_HIT_CONTEXT_NOT_UNIQUE_ANCHOR',
                   materiality_adjudicated=False)
        rows.append(row)
        html += [f'<details><summary>{escape(issue["document"])} p.{issue["page"]} — '
                 f'{escape(issue["issue_id"])} — {row["status"]}</summary>',
                 '<pre>'+escape(json.dumps(issue['original']['change'], ensure_ascii=False, indent=2))+'</pre>',
                 f'<a href="{escape(raster, quote=True)}">Full retained page</a>',
                 f'<img src="{crop.name}" alt="Surrounding page region"><p>Original source SHA-256: '
                 f'{issue["original"]["source_sha256"]}</p></details>']
    (out/'index.html').write_text('\n'.join(html))
    save(out/'crop-input.json',crops)
    cmd=[str(ROOT/'.localresources/assurance-tools/venv/bin/python'),str(Path(__file__).resolve()),
         'render-crops',str(out/'crop-input.json')]
    subprocess.run(cmd,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
                   'CUDA_VISIBLE_DEVICES':'-1'},check=True,timeout=180)
    save(out/'crop-command.json',{'argv':cmd,'CPU_GPU':'CPU; CUDA_VISIBLE_DEVICES=-1'})
    for row in rows:row['crop_sha256']=sha(ROOT/row['review_crop'])
    return rows


def exact_ratio(percent):
    """Losslessly encode a decimal percentage as rational basis points; never accept a float."""
    if not isinstance(percent, str) or len(percent)>64 or not re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', percent):
        raise LegalMathError('E_SCHEMA', details='A bounded exact decimal percentage string is required')
    ratio = Fraction(percent)*100
    return {'va_bps_numerator': str(ratio.numerator), 'va_bps_denominator': str(ratio.denominator)}


def rational_bundle(base):
    """For denominator d>0, n/d >=1000 iff n >=1000*d. Other semantics are unchanged."""
    value = deepcopy(base)
    for fact in value['facts']:
        if fact['name']=='intended_va_bps':
            fact['name']='va_bps_numerator'
            fact['description']='Numerator of exact intended qualifying VA exposure in basis points; supplied classifications unchanged.'
    value['facts'].append({'name':'va_bps_denominator','type':'integer',
                          'description':'Positive denominator of intended qualifying VA basis points; validated by exact-ratio adapter.'})
    changed = 0
    def walk(node):
        nonlocal changed
        if not isinstance(node, dict): return
        if node.get('op')=='compare' and node['left'].get('name')=='intended_va_bps':
            if node.get('cmp')!='ge' or node['right'].get('value')!='1000':
                raise LegalMathError('E_REFERENCE', details='Unexpected ratio comparator')
            node['left']['name']='va_bps_numerator'
            node['right']={'node_id':'ratio.threshold','op':'scale','numerator':'1000','denominator':'1',
                           'arg':{'node_id':'ratio.denominator','op':'fact','name':'va_bps_denominator'}}
            changed += 1
        for child in node.values():
            if isinstance(child,dict): walk(child)
            elif isinstance(child,list):
                for sub in child:walk(sub)
    walk(value['rules'][0])
    if changed!=1: raise LegalMathError('E_REFERENCE')
    value['bundle_id']='ratio.'+digest(base)[:20]
    value['interpretations'][0]['statement'] += ' Exact-ratio representation under a validated positive denominator.'
    return value


def rational_check(base, out):
    b = rational_bundle(base)
    cases=[]
    specs=[('9.999',False,'FALSE'),('10',False,'TRUE'),('10.001',False,'TRUE'),
           ('9.999999999999',False,'FALSE'),('10.000000000001',False,'TRUE'),
           ('0',True,'TRUE'),('0',False,'FALSE')]
    for i,(percentage,objective,status) in enumerate(specs):
        vals={'fund_manager':True,'va_objective':objective,**exact_ratio(percentage)}
        facts={f['name']:{'type':f['type'],'status':'known','value':vals[f['name']],
                         'evidence_ids':['ratio.fixture.'+str(i)], 'valid_from':AT,'valid_until':None,'recorded_at':AT}
               for f in b['facts']}
        cases.append({'id':'ratio.'+str(i),'bundle':b,'snapshot':{'subject_id':'ratio.'+str(i),'facts':facts},
                      'rule_id':'selected.control','valid_at':AT,'known_at':AT,
                      'expected':{'status':status,'value':status=='TRUE'}})
    built=build_candidate(b,out/'java',JDK)
    report=verify_candidate(built,cases,JDK)
    return {'status':'EXACT_RATIO_CONFORMANCE', 'cases':cases,'build':built,'verification':report,
            'relation':'For positive d, n/d >= 1000 is equivalent to n >= 1000*d; d is produced by Fraction.',
            'reference_basis':'Author-derived arithmetic witnesses; not independent legal adjudication',
            'original_integer_policy_preserved':True,'release_eligible':False}


def diverse_backends(cases, build, out):
    """Run installed cvc5 and Catala on actual compiled bundles and the same cases."""
    out.mkdir(parents=True, exist_ok=True)
    save(out/'formal-input.json', {'jdk':str(JDK),'cases':[
        {**c,'jar':build['jar'],'class_name':build['class_name']} for c in cases]})
    command=[str(ROOT/'.localresources/assurance-tools/venv/bin/python'),'-m',
             'legalmath.interpretation.assurance.sidecar','formal-cases','--input',str(out/'formal-input.json'),
             '--output',str(out/'formal-result.json')]
    with (out/'cvc5.log').open('w') as log:
        subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
                       'CUDA_VISIBLE_DEVICES':'-1'},stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
    cvc5=read(out/'formal-result.json')
    if cvc5['status']!='PASS':raise LegalMathError('E_INTEGRITY',details='cvc5 differs on actual cases')
    try:
        catala=build_candidate(cases[0]['bundle'],out/'catala',JDK,backend='catala',catala_toolchain={
            'compiler':ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
            'upstream':ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
            'lock':ROOT/'docs/implementation/catala/toolchain-lock.json'})
        checked=verify_candidate(catala,cases,JDK)
        alternate={'status':'PASS','build':catala,'verification':checked}
    except LegalMathError as exc:
        if exc.code!='E_UNSUPPORTED_PROFILE':raise
        alternate={'status':'UNSUPPORTED','details':exc.details}
    return {'cvc5':cvc5,'catala':alternate,'command':command,'case_count':len(cases),
            'legal_correctness_established':False}


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='render-crops':raise SystemExit('Expected render-crops manifest')
    from PIL import Image
    images={}
    for row in read(Path(sys.argv[2])):
        if row['source'] not in images:images[row['source']]=Image.open(row['source'])
        image=images[row['source']]
        x0,y0,x1,y1=row['bbox'];sx=image.width/row['width'];sy=image.height/row['height']
        image.crop((int(x0*sx),int(y0*sy),min(image.width,int(x1*sx)+1),
                    min(image.height,int(y1*sy)+1))).save(row['output'])
