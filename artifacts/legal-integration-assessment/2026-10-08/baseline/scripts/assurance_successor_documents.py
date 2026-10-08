"""Preserve scholarly content, bind reviewed citations and build the unified books."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zipfile
from run_assurance_successor import ROOT,OUT,DOC,read,save,sha,rel,phase_result
from assurance_successor_phases import command


def citation_review():
    # Fixed reviewed contexts; this is never an automatic support classifier.
    from check_reader_facing_monograph import occurrences,BOOK
    path=BOOK/'review/reader-facing/citation-occurrence-review.json';review=read(path)
    allrows=[r for name in ('monograph','technical-companion') for r in occurrences(BOOK/(name+'.tex'),BOOK)]
    source='docs/monograph/chapters/06h-successor-assurance.tex'
    current=[r for r in allrows if r['source']==source]
    old=[r for r in review['occurrences'] if not r['id'].startswith(source+':')]
    expected=[r for r in allrows if r['source']!=source]
    ident=lambda r:(r['key'],r['context_sha256'])
    if Counter(map(ident,old))!=Counter(map(ident,expected)):raise RuntimeError('Unrelated citation context changed')
    if {r['key'] for r in current}!={'aspic2010','carneades2007','catala2021','knight1986diversity','littlewood2001diversity'}:
        raise RuntimeError('Unexpected successor citation; specific review required')
    reading=read(BOOK/'review/revision/citation-reading.json')['sources']
    archive={r['key']:r for r in read(ROOT/'docs/papers/monograph-citation-archive.json')['sources']}
    scopes={
      'aspic2010':'Definitions 3.1–3.16 and retained correction limits; structured arguments, attack and premise distinctions.',
      'carneades2007':'Definitions 5–10, premise types and acceptability; no legal burden is inferred from a local threshold.',
      'catala2021':'Sections 2–4, simulation proof and its distinction from the separately implemented production compiler.',
      'knight1986diversity':'Sections 4–8, random test inputs, null independence model, coincident failures and study limitations.',
      'littlewood2001diversity':'Section 4.1, equations 4.1–4.4; variable input difficulty permits correlated failures despite conditional independence.'}
    judgments={
      'aspic2010':'Supports separating structured inference from premise acceptability and defeat; local authority checks are explicitly bounded.',
      'carneades2007':'Supports explicit premise status and burdens rather than authentic-quotation-as-truth; no full Carneades implementation is asserted.',
      'catala2021':'Supports the language and scoped formal compilation work. The successor distinguishes formal translation from English meaning and actual production Java.',
      'knight1986diversity':'Supports warning that separate versions can have coincident failures; no experimental failure rate is transferred to LLMs.',
      'littlewood2001diversity':'Supports the possibility of common misses under shared demand difficulty; no local independence or fitted reliability claim follows.'}
    result=[]
    for row in current:
        k=row['key'];rr=reading[k]
        result.append({'id':row['id'],'key':k,'context_sha256':row['context_sha256'],
            'source_sha256':archive[k]['sha256'],
            'reading_record_sha256':hashlib.sha256(json.dumps(rr,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
            'review_group':999,'decision':'supported_in_stated_scope','judgment':judgments[k],
            'migration':'M06:27 author review against inspected technical sections and retained scoped reading record',
            'review_scope':scopes[k]})
    review['occurrences']=old+result
    review['m06_27_addition']={'status':'SCOPED_AUTHOR_REVIEW','occurrences':len(result),'independent_legal_review':False}
    save(DOC/'citation-review-prior.json',read(path));save(path,review)
    save(DOC/'citation-review.json',{'records':result,'scope':'Source-specific author review; reader comprehension is not certified by this check'})


def preservation(work):
    baseline=OUT/'S0/attempt-01/baseline.zip'
    features={'labels':re.compile(r'\\label\{[^}]+\}'),
      'equations':re.compile(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|displaymath)\}.*?\\end\{\1\}|\\\[.*?\\\]',re.S),
      'listings':re.compile(r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}',re.S),
      'citations':re.compile(r'\\cite\w*\*?(?:\[[^\]]*\])*\{[^}]+\}')}
    result={};changed=[]
    with zipfile.ZipFile(baseline) as z:
        before=[];after=[]
        for name in z.namelist():
            if name.startswith('docs/monograph/') and name.endswith('.tex') and '/review/' not in name:
                a=z.read(name).decode();p=ROOT/name
                if not p.exists():raise RuntimeError('Original LaTeX file lost: '+name)
                b=p.read_text();before.append(a);after.append(b)
                if a!=b:changed.append(name)
        for key,pattern in features.items():
            collect=lambda values:Counter(re.sub(r'\s+',' ',m[0]).strip() for text in values for m in pattern.finditer(text))
            missing=collect(before)-collect(after)
            result[key]={'before':sum(collect(before).values()),'missing':dict(missing)}
            if missing:raise RuntimeError('Substantive baseline feature lost: '+key)
    record={'status':'BASELINE_FEATURES_PRESERVED','features':result,'changed_existing_files':changed,
            'new_section':'docs/monograph/chapters/06h-successor-assurance.tex',
            'prose_review':'Existing statement about no certificate adapter qualified by its historical date; new successor account added.',
            'not_a_proof_of_semantic_identity':True}
    save(work/'preservation.json',record);return record


def results_section():
    state=read(OUT/'state.json');rows=[]
    for name in ('S0','S1','S2','S3','S4','S5','S6','S7','S8','S9'):
        phase=state['phases'][name];m=read(ROOT/phase['attempts'][-1]['manifest']);r=phase_result(m)
        rows.append({'phase':name,'status':phase['status'],'result':r,'manifest':phase['attempts'][-1]})
    save(DOC/'executed-phase-results.json',rows)
    s6=rows[6]['result'];s7=rows[7]['result'];s8=rows[8]['result'];s9=rows[9]['result']
    text=r'''
\subsection{Recorded successor execution}
The following figures describe the bounded successor run of 28 September 2026.
They are observations of executed software and proposed interpretations, with
the separate evidential limits stated above.
\begin{table}[H]\centering\small
\begin{tabularx}{\textwidth}{Y r}
\toprule Recorded observation & Count \\\midrule
'''
    pairs=[('Retained claim--candidate pairs',s6['scoped_pairs']),
        ('Pairs with both validated scoped perspectives',s6['two_perspective_pairs']),
        ('Pairs with all four scoped dimensions assessed',s6['pairs_with_four_dimensions_assessed']),
        ('Retained PDF materiality issues',s6['pdf_items']),
        ('PDF issues retaining visual uncertainty',s6['pdf_dispositions'].get('VISUAL_UNCERTAINTY_RETAINED',0)),
        ('Authority questions investigated',s6['authority_questions']),
        ('Attributed-contact Java cases',s7['contact_java_cases']),
        ('Raw-history Java host cases',s7['contact_host_java_cases']),
        ('Exact-decimal Java host cases',s7['decimal_java_cases']),
        ('Unfamiliar circular tasks retained',s8['selected_tasks']),
        ('Complete joined unfamiliar investigations',s8['complete_ensemble_investigations']),
        ('Conditional source cases in the denominator',s9['total_selected_cases']),
        ('Cases lacking a reference answer in both arms',s9['shared_reference_misses']),
        ('Java case executions after proposed fact mapping',s9['actual_generated_java_case_runs'])]
    text+=''.join(f'{label} & {count} \\\\\n' for label,count in pairs)
    text+=r'''\bottomrule\end{tabularx}
\caption{Executed successor evidence; counts do not establish legal accuracy.}
\end{table}
Both initial contexts in the first scoped batch incorrectly proposed that
unbound authority was available. The validator rejected those responses and
the bounded repair loop retained the correction and original failures. The
complete report retains unanswered source and performance questions; it grants
no automatic release or unconditional legal-correctness claim. Human answers or
approval are not quality evidence under the current product requirement.
The source-case comparisons are
descriptive and conditional on proposed factual mappings. No statistically
supported ranking or future-error probability follows.
The missing reference answers include different-question programs, incomplete
generation and unresolved facts. Their count is therefore a coverage finding,
not an estimate of English interpretation error. An unaligned program does not
earn credit for abstaining from a question it never implemented.
'''
    if not s8['execution_complete']:
        text+=r'''
The unfamiliar-source study did not complete its required investigations within
the executed limits. Its failed phase remains failed. The later assessment
preserves all selected tasks and reports unfinished processing; successful
software regression or document production cannot turn that failure into a
completed study. The complete execution record identifies the exact resource
veto and the remaining claim--reading pairs.
'''
    (ROOT/'docs/monograph/chapters/06h-successor-results.tex').write_text(text)


def run(work):
    from assurance_successor_phases import command
    results_section();preserved=preservation(work)
    command(['python3','scripts/assurance_successor_documents.py','citations'],work,'citation-review',timeout=60)
    command(['python3','scripts/build_reader_facing_monograph.py'],work,'document-build',timeout=1200)
    checked=read(ROOT/'docs/monograph/review/reader-facing/document-check.json')
    if checked['status']!='PASS':raise RuntimeError('Document checks failed')
    # Render targeted pages; human/model inspection is recorded separately.
    command(['python3','scripts/assurance_successor_documents.py','render'],work,'render',timeout=120)
    result={'status':'UNIFIED_DOCUMENTS_BUILT','pages':{k:v['pages'] for k,v in checked['documents'].items()},
         'preservation':preserved,'document_check':rel(ROOT/'docs/monograph/review/reader-facing/document-check.json'),
         'open_evidence':['Build checks and targeted rendering do not establish reader comprehension.'],'release_eligible':False}
    save(work/'result.json',result);return result


def render():
    import fitz
    directory=DOC/'rendered';directory.mkdir(exist_ok=True)
    selected=[]
    with fitz.open(ROOT/'docs/monograph/monograph.pdf') as doc:
        for i,page in enumerate(doc):
            text=page.get_text()
            if ('continuing investigation' in text.lower() or 'the Lean certificate' in text or
                'Recorded successor execution' in text or 'Investigate the exact disagreement' in text):
                for n in range(max(0,i-1),min(len(doc),i+3)):
                    if n not in selected:selected.append(n)
        for n in selected:doc[n].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(directory/f'page-{n+1:03}.png')
    save(DOC/'rendered-pages.json',{'pages':[n+1 for n in selected],'pending_visual_inspection':True})


if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['citations']:citation_review()
    elif sys.argv[1:] == ['render']:render()
    else:raise SystemExit('Use fixed citations or render action')
