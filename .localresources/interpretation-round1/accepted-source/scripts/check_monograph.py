"""Check monograph structure, identities and layout evidence; not readability certification."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import re
import fitz

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'docs/monograph'
REVIEW=BOOK/'review'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(s):return s.replace('\\\\',' ').replace('\\','')

INPUT = re.compile(r'\\(?:input|include)\{(?:\\LegalMathRoot\s*)?([^}]+)\}')

def expanded_source(path):
    """Resolve only the explicit local chapter inputs in the canonical manuscript."""
    text = path.read_text()
    return INPUT.sub(lambda match: expanded_source(BOOK/(match[1]+'.tex')), text)

def main():
    errors=[]
    def require(c,msg):
        if not c:errors.append(msg)
    tex=(BOOK/'monograph.tex').read_text()
    includes=INPUT.findall(tex)
    require(len(includes)==10,'Expected ten chapters')
    chapter_files=[BOOK/(n+'.tex') for n in includes]
    supplemental_files=[BOOK/(n+'.tex') for p in chapter_files for n in INPUT.findall(p.read_text())]
    files=[BOOK/'monograph.tex',BOOK/'references.bib']+chapter_files+supplemental_files
    require(all(p.is_file() for p in files),'Missing manuscript source')
    full='\n'.join(p.read_text() for p in files if p.suffix=='.tex')
    labels=re.findall(r'\\label\{([^}]+)\}',full)
    require(len(labels)==len(set(labels)),'Duplicate labels')
    refs=re.findall(r'\\(?:eqref|ref)\{([^}]+)\}',full)
    require(set(refs)<=set(labels),'Unresolved internal reference')
    citations=[]
    for group in re.findall(r'\\cite[pt]?(?:\[[^\]]*\]){0,2}\{([^}]+)\}',full):citations.extend(group.split(','))
    bibkeys=re.findall(r'@\w+\s*\{\s*([^,\s]+)',(BOOK/'references.bib').read_text())
    require(len(bibkeys)==len(set(bibkeys)),'Duplicate bibliography key')
    require(set(citations)<=set(bibkeys),'Missing bibliography entry')
    require({'catala2021','arc2025','slaw2024','jurayj2026','stipula2021','stipulakey2025','reachability2026'}<=set(citations),'A user-named paper is not discussed/cited')
    log=(BOOK/'monograph.log').read_text()
    require(not re.search(r'Overfull|undefined|LaTeX Error|Package .* Error|Missing character',log),'Unresolved LaTeX diagnostic')
    pdf=fitz.open(BOOK/'monograph.pdf')
    require(len(pdf)>=153,'Unified PDF is shorter than the protected 153-page monograph; investigate content loss')
    pages=[];alltext=[]
    for i,page in enumerate(pdf):
        text=page.get_text();alltext.append(text)
        spans=[span for b in page.get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for span in line['spans']]
        outside=[s['text'] for s in spans if s['bbox'][0]<-1 or s['bbox'][2]>page.rect.width+1 or s['bbox'][1]<-1 or s['bbox'][3]>page.rect.height+1]
        require(not outside,f'Off-page text on page {i+1}')
        require(len(text.strip())>20,f'Blank/padding page {i+1}')
        pages.append({'pdf_page':i+1,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'characters':len(text),'off_page_spans':outside,'continuous_visual_read':'NOT_CLAIMED'})
    (REVIEW/'rendered-text.txt').write_text('\n\f\n'.join(alltext))
    nodes=[{'id':'document','parent':None,'kind':'document','title':'LegalMath: From SFC Circulars to Reviewed Specifications and Verified Java Controls','independent_reader':'PENDING'}]
    chapter_counts=[]
    for ch,p in enumerate(chapter_files,1):
        s=expanded_source(p);cid=f'ch{ch:02}';current=cid;section=0;sub=0
        title=re.search(r'\\chapter(?:\[[^\]]*\])?\{([^\n]+)\}',s).group(1)
        nodes.append({'id':cid,'parent':'document','kind':'chapter','title':plain(title),'source':str(p.relative_to(ROOT)),'source_sha256':sha(p),'line_coordinates':'expanded chapter including named inputs'})
        events=[]
        for m in re.finditer(r'\\(section|subsection|subsubsection)\{([^\n]+)\}',s):events.append((m.start(),'heading',m))
        for m in re.finditer(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}(.*?)\\end\{\1\}',s,re.S):events.append((m.start(),'equation',m))
        eqcount=0
        for pos,kind,m in sorted(events,key=lambda x:x[0]):
            if kind=='heading':
                if m[1]=='section':section+=1;sub=0;ident=f'{cid}.s{section:02}';parent=cid;section_id=ident
                else:sub+=1;ident=f'{section_id}.u{sub:02}';parent=section_id
                current=ident
                nodes.append({'id':ident,'parent':parent,'kind':m[1],'title':m[2],'line':s.count('\n',0,pos)+1,'scholarly_review':'AUTHOR_DRAFT; independent reconstruction pending'})
            else:
                eqcount+=1;els=re.findall(r'\\label\{([^}]+)\}',m[2]);require(bool(els),f'Unlabelled display in {p.name}')
                nodes.append({'id':f'{cid}.eq{eqcount:02}','parent':current,'kind':'displayed-equation','labels':els,'line':s.count('\n',0,pos)+1,'equation_role':'MECHANISM_BEARING','independent_math_review':'PENDING'})
        chapter_counts.append({'chapter':ch,'file':p.name,'source_words':len(s.split()),'sections':section,'displayed_groups':eqcount})
    require(all(n['parent'] is None or n['parent'] in {x['id'] for x in nodes} for n in nodes),'Broken hierarchy parent')
    baseline=json.loads((ROOT/'.localresources/monograph/baseline/input-manifest.json').read_text())
    # The user explicitly requested replacing the old proposal with the unified
    # edition. Verify those two protected originals at their frozen locations.
    archived={'docs/proposal/proposal.tex','docs/proposal/proposal.pdf'}
    protected_locations={p:('.localresources/unification/baseline/'+p if p in archived else p) for p in baseline}
    unchanged={p:sha(ROOT/protected_locations[p])==v for p,v in baseline.items()}
    require(all(unchanged.values()),'A protected prior input changed')
    library=json.loads((ROOT/'docs/papers/manifest.json').read_text())
    for paper in library['papers']:
        p=ROOT/'docs/papers'/paper['filename'];require(p.is_file() and sha(p)==paper['sha256'],'Paper identity: '+paper['id'])
    math_checks={'common_error':.02+(1-.02)*(.1**3),'zero_error_n100':1-.05**(1/100),'zero_error_n1000':1-.05**(1/1000),'conformal_n19_alpha01':math.ceil(20*.9),'conformal_n4_alpha01':math.ceil(5*.9)}
    require(abs(math_checks['common_error']-.02098)<1e-12,'Common-mode illustration')
    # Direct exhaustive truth-table check of the dual-indicator equations.
    values=[(1,0),(0,1),(0,0)];truth=[True,False,None]
    for i,a in enumerate(values):
        for j,b in enumerate(values):
            conj=False if False in (truth[i],truth[j]) else True if truth[i] is True and truth[j] is True else None
            disj=True if True in (truth[i],truth[j]) else False if truth[i] is False and truth[j] is False else None
            require((int(bool(a[0] and b[0])),int(bool(a[1] or b[1])))==values[truth.index(conj)],'Kleene conjunction')
            require((int(bool(a[0] or b[0])),int(bool(a[1] and b[1])))==values[truth.index(disj)],'Kleene disjunction')
    result={'status':'PASSED' if not errors else 'FAILED','errors':errors,'pdf_pages':len(pdf),'chapters':chapter_counts,'cited_entries':len(set(citations)),'bibliography_entries':len(bibkeys),'paper_editions':len(library['papers']),'paper_pages':sum(p['pages'] for p in library['papers']),'protected_inputs':unchanged,'protected_input_locations':protected_locations,'math_diagnostics':math_checks,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in files},'pdf_sha256':sha(BOOK/'monograph.pdf'),'review_status':'independent_reader_pending','limits':['Structure and rendering diagnostics do not establish readability or legal correctness.','Page-count check permits the user-requested combined work to exceed the earlier separate-volume target.','No live-model study, legal adjudication, product deployment or full compiler proof was performed.']}
    REVIEW.mkdir(exist_ok=True)
    (REVIEW/'document-check.json').write_text(json.dumps(result,indent=2)+'\n')
    (REVIEW/'hierarchy.json').write_text(json.dumps({'pdf_sha256':result['pdf_sha256'],'nodes':nodes,'acceptance':'AUTHOR_DRAFT; no exhaustive scholarly-read certification'},indent=2)+'\n')
    (REVIEW/'page-inventory.json').write_text(json.dumps({'pdf_sha256':result['pdf_sha256'],'pages':pages},indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','pdf_pages','cited_entries','paper_editions','errors')}))
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
