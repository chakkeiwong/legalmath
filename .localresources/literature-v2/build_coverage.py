"""Render the explicit dispositions of the preserved citation neighborhoods."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'.localresources/literature-review/metadata'
NEW=Path(__file__).parent/'metadata'
reviewed={
 'W4416354595':'eflint2026','W7172344004':'eflint2026',
 'W7127894717':'stipulaplatform2026','W4416232693':'stipulakey2025',
 'W4410344615':'contractcheck2025','W4410034013':'cutecat2025',
 'W4393955113':'dates2024','W4388827937':'slaw2024',
 'W4380634721':'amending2023','W4389519322':'connecting2023',
 'W4310791555':'stipula2021','W4293451998':'crafa2022',
 'W4221142907':'huttner2022','W7138835127':'reachability2026',
 'W4380884364':'liquidity2023'}
gaps={
 'W7211990122':'Policy2Code: relevant later code-generation comparator; full method not inspected.',
 'W7203755204':'Retrieval/codification explanations: relevant later drafting comparator; not used for performance claims.',
 'W7203555364':'ESG-as-Code: adjacent rule-validation application; full method not inspected.',
 'W7167853254':'Tax inconsistency formalization: relevant semantic-conflict comparator; full method not inspected.',
 'W7164479571':'CatalaBlocks: authoring usability lead; metadata located, no full-text experiment inspected.',
 'W7136177225':'Consumer-complaint intelligibility: relevant usability lead; no transfer claim.',
 'W7165397454':'Later deductive-verification edition: relationship to retained KeY preprint needs full-text confirmation.',
 'W4413415186':'Public-sector legal automation: adjacent formalization case; not used to predict bank results.',
 'W4386517469':'Obligation logic graphs: relevant extraction alternative; ACM retrieval failed.',
 'W3211780905':'Financial-regulation high-assurance software: UCL full-text route failed.',
 'W4297897028':'Formalization-methodology comparison: publisher route returned non-PDF HTML.',
 'W4416888247':'Statutory norms integrated in contracts: relevant extension beyond MVP; full method not inspected.',
 'W4399311116':'Programming Contract Amending (2024): publisher non-PDF and repository TLS failure; distinct 2023 author manuscript retained.',
 'W4214868062':'Automatically processable regulation typology: conceptual scoping lead; not primary execution evidence.',
 'W4254590041':'Philosophy of computational law: conceptual authority/interpretation lead; not used as an implementation theorem.'}
background={
 'W4399311051':'Wikidata exceptions may aid retrieval; does not establish legal authority or default semantics.',
 'W4394581589':'Alloy startup-finance formalization is an adjacent bounded-modeling example; no local adapter adopted.',
 'W4362650433':'Prioritized-defeasible complexity extension deferred; current semantic choice uses inspected foundation.',
 'W4411371412':'Micro-Stipula decidability precursor; retained 2026 reachability paper supplies checked result.',
 'W4402210691':'Micro-Stipula reachability precursor; retained 2026 paper/platform supply checked scope.',
 'W4399478948':'TRAC is a data-aware coordination alternative; no MVP dependency.',
 'W4400582885':'Legal practitioners/software licenses: useful human-factors follow-up; not a bank usability result.',
 'W4400912863':'Apparent alternate record of software-licensing practitioners study; no independent work count.',
 'W3178402543':'Legal expert-system NLG: explanation-generation lead; MVP uses deterministic traces.',
 'W7169168825':'Planning with legal/ethical checkers: optional future scheduling comparison, not rule execution.',
 'W4387412540':'Computational-law overview; mechanism claims use primary technical sources.',
 'W4396857543':'Computational legal studies overview; no direct MVP algorithm adopted.',
 'W4400286778':'Algorithmic decision conceptual lead; language/full-text reading not completed.'}
records={}
for name in ['catala-citing.json','stipula-citing.json']:
 for r in json.loads((OLD/name).read_text())['results']:
  ident=r['id'].split('/')[-1]
  if ident not in records:
   if ident in reviewed:
    status='technical source retained';reason='See '+reviewed[ident]+' and edition notes; indexed year/title may differ from retained edition.'
   elif ident in gaps: status='relevant unresolved follow-up';reason=gaps[ident]
   elif ident in background: status='screened background/deferred';reason=background[ident]
   else: status='excluded from core on title/metadata screen';reason='Different application, general collection or implementation topic; no additional mechanism required by the selected prototype established at screening.'
   records[ident]={'openalex_id':ident,'title':r.get('title'),'year':r.get('publication_year'),'doi':r.get('doi'),
                   'status':status,'reason':reason,'discovery_files':[]}
  records[ident]['discovery_files'].append(name)
out=ROOT/'docs/papers'
(out/'citation-screening.json').write_text(json.dumps(list(records.values()),ensure_ascii=False,indent=2)+'\n')
counts={}
for r in records.values():counts[r['status']]=counts.get(r['status'],0)+1
lines=['# Literature coverage and remaining gaps','',
'Snapshot: 21 September 2026. This is a bounded technical review, not an exhaustive systematic review or a census of citations. Its purpose is to supply inspected mechanisms for the chosen prototype and make omitted work visible.','',
'## Search protocol','',
'Seeds: all seven user links. Expansion: saved OpenAlex forward citations for Catala (52 records) and the later Stipula journal edition (13); backward references for default/deontic/process foundations; ResearchAssistant discovery; targeted searches for eFLINT, L4, LegalRuleML, Regorous, SPINdle, input/output logic, Symboleo, temporal compliance and Rules as Code. Inclusion prioritizes a needed semantics, algorithm, evaluation failure or reusable original tool. Non-banking benchmarks are included for mechanisms, not as estimates of banking performance.','',
'Broad captured queries: `defeasible`, `l4`, `rulesascode`, `temporal`, then targeted foundation/language queries, retained under `.localresources/literature-v2/metadata/`. Provider results contain irrelevant records and duplicate editions. Captured candidates are not all counted as screened or read. The explicit per-record screening below applies to the two forward-citation neighborhoods. Additional inspected works enter the PDF manifest separately.','',
'ResearchAssistant discovery was run with an explicit project-local root. The first request hit sandbox DNS restrictions and was rerun with trusted permissions; the resulting 30 OpenAlex records are preserved. Semantic Scholar returned 429. The browser search service repeatedly returned upstream 502/503 errors. Direct official/author HTTPS retrieval supplied primary texts. Publisher HTML responses were checked by PDF magic and were not counted as papers. No paywall or authentication was bypassed.','',
'The stop condition for this revision is architectural coverage: each of eight families below has an inspected primary mechanism, every requested seed has a local full text, and every retrieved forward-citation record has a disposition. Recent comparator and usability leads remain explicitly incomplete. Development should reopen them when selecting an adapter or designing the human study. No claim of citation-network saturation is made.','',
'## Coverage by design question','',
'| Family | Inspected anchors | Design/test consequence |',
'| --- | --- | --- |',
'| Executable statutes and collaboration | Sergot; Catala; Huttner–Merigoux; Logical English | Source-adjacent definitions, typed dependencies, controlled explanations |',
'| Defaults and priorities | Catala calculus; Antoniou et al. | Competing exceptions, explicit priority, no first-row fallback |',
'| Duties, permissions and violations | Input/Output Logics; Strong/Weak Permissions; Logic of Violations; normative taxonomy | Distinguish fact, permission, duty and breach; reject unsupported profiles |',
'| Temporal/process compliance | Ghose; Tosatto; Hashmi; LegalRuleML/Regorous; Stipula; Symboleo | Actor/event mapping, obligations in force, some-versus-all traces |',
'| Authority, provenance and amendments | LegalRuleML standard/interpretations; 2016 context mapping; Stipula amendment | Exact spans/versions, explicit migration and applicability |',
'| Compilers, calendars and tests | Catala; dates; CUTECat; StipulaKeY; reachability/liquidity; eFLINT stable model | Supported fragments, unknown results, implementation exclusions, boundary mutations |',
'| LLM formalization and evaluation | SARA; Connecting; ContractNLI; Logic-LM; LINC; ARc; Jurayj; Limits; LegalBench | Gold-rule fairness, abstention, independent sources/cases, exact local metrics |',
'| Reusable engines and integration | Catala/Drools/OpenFisca/OPA/Z3/Cicero/Blawx docs; L4 docs; Symboleo docs; eFLINT artifact | Pin version/semantics/license; conformance before integration |','',
'## Explicit retrieval and reading gaps','',
'Lawsky’s *A Logic for Statutes* and *Coding the Code*, the L4 2023 paper, the later Symboleo journal paper, *High Assurance Software for Financial Regulation and Business Platforms*, *An Evaluation of Methodologies for Legal Formalization*, the 2024 *Programming Contract Amending* chapter and *Computable Contracts by Extracting Obligation Logic Graphs* remain retrieval gaps. L4/Symboleo official software and a separate earlier Stipula amendment paper provide narrower inspected evidence. New Policy2Code, CatalaBlocks and explanation-codification papers remain relevant follow-ups, not silently excluded evidence or read sources.','',
'The proposal makes no efficacy claim that depends on those unretrieved works. If a later decision chooses their language/compiler/interface, obtaining the technical full text and auditing its original code becomes required work. The paper library does not contain failed HTML downloads.','',
f'## Forward-citation screening: {len(records)} distinct indexed records','',
'The 65 raw records overlap. Indexed-record count is not distinct-paper count. Status counts: '+', '.join(f'{k}: {v}' for k,v in counts.items())+'.','',
'| Record / year | Title | Disposition and reason |','| --- | --- | --- |']
for r in records.values():
 title=r['title'].replace('|','/').replace('\n',' ')
 lines.append(f"| [{r['openalex_id']}](https://openalex.org/{r['openalex_id']}) / {r['year']} | {title} | **{r['status']}**. {r['reason']} |")
(out/'coverage.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'unique_indexed_records':len(records),'status_counts':counts}))
