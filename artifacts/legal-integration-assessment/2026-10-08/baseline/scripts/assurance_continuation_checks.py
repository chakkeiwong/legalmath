"""Real retained-input checks and explicitly bounded live continuation."""
from copy import deepcopy
from datetime import datetime, timezone
import math
from pathlib import Path
import time

from run_assurance_continuation import ROOT, OUT, DOC, read, save, sha, relative
from legalmath.canonical import digest, canonical
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import source_references, single_reader, fidelity_v2
from legalmath.interpretation.assurance.decomposition import compact_request
from legalmath.sources.extract import extract

OLD = ROOT/'artifacts/assurance-successor/2026-09-28'
GRANT = OLD/'grant.json'
JDK = ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
AT = '2026-09-28T00:00:00.000000Z'
TOOLCHAIN = {'compiler': ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
    'upstream': ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
    'lock': ROOT/'docs/implementation/catala/toolchain-lock.json'}


def baseline(work):
    from zipfile import ZipFile
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    b=read(OUT/'baseline.json')
    if sha(OUT/'baseline.zip')!=b['archive_sha256']:raise LegalMathError('E_INTEGRITY')
    if sha(ROOT/b['baseline_report']['path'])!=b['baseline_report']['sha256']:raise LegalMathError('E_INTEGRITY')
    for path,h in b['ledgers'].items():
        if sha(ROOT/path)==h:continue
        if path!=relative(OLD/'live-allowance.json'):
            raise LegalMathError('E_INTEGRITY',details='Exhausted predecessor ledger changed')
        with ZipFile(OUT/'baseline.zip') as archive:
            original=__import__('json').loads(archive.read(path))
        current=read(ROOT/path)
        if (set(current)!=set(original) or current['maximum']!=original['maximum'] or
                current['calls'][:len(original['calls'])]!=original['calls']):
            raise LegalMathError('E_INTEGRITY',details='Original reservations were changed or refunded')
        GrantedAllowance(GRANT).verify()
    frozen=read(OLD/'study-source-freeze.json');rows=[]
    for task in frozen['tasks']:
        packet=task['packet']
        if digest(packet)!=task['packet_hash']:raise LegalMathError('E_INTEGRITY')
        binding=digest({'task':'REFERENCE_INTEGRITY_PREFLIGHT','packet':packet})
        references=source_references.table(packet,binding)
        source_references.verify_table(references,packet,binding)
        for unit in packet['units']:
            span=next(s for s in references['spans'] if s['unit_id']==unit['unit_id'])
            result=source_references._resolve({'span_ids':[span['span_id']]},references,packet)
            if result!={'unit_id':unit['unit_id'],'quote':unit['text']}:raise LegalMathError('E_INTEGRITY')
        partition=single_reader.partitions(packet)
        save(work/(task['task_id']+'-references.json'),references)
        rows.append({'task_id':task['task_id'],'source_units':len(packet['units']),'source_hash':digest(packet),
            'coverage_pieces':len(partition),'partition':partition,'every_whole_unit_resolved':True})
    result={'status':'BASELINE_AND_ALL_FROZEN_SOURCES_PRESERVED','tasks':rows,
            'historical_study_complete':False,'legal_correctness':'NOT_ESTABLISHED'}
    save(work/'result.json',result);return result


def retained(task_id):
    study=read(OLD/'unfamiliar-study/result.json')
    task=next(t for t in study['tasks'] if t['task_id']==task_id)
    ref=task['ensemble']['dossier']
    if sha(ROOT/ref['path'])!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
    dossier=read(ROOT/ref['path'])
    values=[]
    for name in ('packet','claims','candidates'):
        ref=dossier[name]
        if sha(ROOT/ref['path'])!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
        values.append(read(ROOT/ref['path']))
    return task,dossier,*values


def real_source_replay(work):
    from legalmath.translation.model import from_reading
    from legalmath.interpretation.assurance import qualification_adapter
    from legalmath.interpretation.search.formal import Comparisons
    from legalmath.translation.ruleir import lower
    from legalmath.java.manifest import build_candidate,run_java
    from legalmath.ir.evaluate import evaluate
    from legalmath.interpretation.search.formal import project,RULE
    from legalmath.qualification import oracle
    task,dossier,packet,claims,candidates=retained('26ec55')
    # This reproducer is an observed unsupported expression; no legal answer
    # or circular-specific compiler behavior is introduced.
    ident='node.11d4e8e1976eb5b2900022be';reading=candidates[ident]
    assignment=next(q for q in dossier['questions']['assignments'] if q['candidate_id']==ident)
    m=from_reading(reading,packet,AT)
    # Declared mathematical challenges, deliberately including financially
    # inadmissible negative valuations. No bank fact or expected legal label.
    vectors=[(0,0,100),(24,25,100),(25,25,100),(10**40,10**40,4*10**40),(-1,1,100)]
    cases=[]
    for index,(direct,indirect,nav) in enumerate(vectors):
        values={'authorised_public_fund':True,'is_laf':False,'direct_exposure':str(direct),
                'indirect_exposure':str(indirect),'nav':str(nav),'operative_designation':False}
        facts={f['name']:{'status':'known','type':f['type'],'value':values[f['name']],
            'evidence_ids':['mathematical.'+f['name']], 'valid_from':AT,'valid_until':None,'recorded_at':AT} for f in m['facts']}
        cases.append({'id':'probe.'+str(index),'snapshot':{'subject_id':'mathematical','facts':facts},'valid_at':AT,'known_at':AT})
    for status in ('unknown','conflict'):
        case=deepcopy(cases[0]);case['id']=status
        case['snapshot']['facts']['direct_exposure']={'type':'integer','status':status,**(
            {'reason':'MISSING'} if status=='unknown' else {'evidence_ids':['conflict.a','conflict.b']})}
        cases.append(case)
    result=qualification_adapter.run(packet,reading,assignment['question'],cases,work/'retained-addition',JDK,AT,
        assignment_status=assignment['assignment_status'],toolchain=TOOLCHAIN)
    qualification_adapter.verify(work/'retained-addition',packet,reading,assignment['question'],JDK,
        assignment_status=assignment['assignment_status'],compiler=TOOLCHAIN['compiler'])
    if result['summary']['status']!='QUALIFIED' or result['summary']['formal_lowering']!='KERNEL_CHECKED':
        raise LegalMathError('E_INTEGRITY',details='Retained arithmetic failed formal qualification')
    # The shared product correctly keeps legal dependencies unresolved. Execute
    # the unchanged hypothetical expression separately under explicit test facts;
    # never erase review questions to pass the product's translation boundary.
    b=lower(m);runtime={}
    for backend in ('java','catala'):
        built=build_candidate(b,work/('conditional-'+backend),JDK,backend=backend,
            catala_toolchain=TOOLCHAIN if backend=='catala' else None)
        actual=run_java(built['jar'],[{**c,'bundle':b,'rule_id':RULE} for c in cases],JDK,built['class_name'])
        rows=[]
        for case,answer in zip(cases,actual):
            expected=evaluate(b,case['snapshot'],RULE,AT,AT)
            if project(answer)!=project(expected):raise LegalMathError('E_INTEGRITY')
            independent=None
            if case['id'].startswith('probe.'):
                independent=oracle.evaluate(reading['formalization'],case['snapshot'])[RULE]
                if project(answer)!=project(independent):raise LegalMathError('E_INTEGRITY')
            rows.append({'case':case,'actual':project(answer),'independent':independent})
        if len(actual)!=len(cases):raise LegalMathError('E_INTEGRITY')
        runtime[backend]={'cases':rows,'build':built['manifest'],'scope':'Hypothetical facts; unresolved legal premises retained.'}
    save(work/'conditional-runtime.json',runtime)
    binary=deepcopy(reading)
    binary['formalization']['result']=binary['formalization']['result'].replace(
        '(+ direct_exposure indirect_exposure direct_exposure indirect_exposure)',
        '(+ (+ (+ direct_exposure indirect_exposure) direct_exposure) indirect_exposure)')
    domain={f['name']:({'states':['T','F','U']} if f['type']=='bool' else
        {'min':'-10000000000000000000000000000000000000000000',
         'max':'10000000000000000000000000000000000000000000','allow_unknown':True}) for f in m['facts']}
    checker=Comparisons(work/'symbolic',JDK,AT,domain=domain)
    equivalence=checker.compare(reading,binary,packet)
    mutation=deepcopy(reading);mutation['formalization']['result']=mutation['formalization']['result'].replace(
        '(+ direct_exposure indirect_exposure direct_exposure indirect_exposure)', '(+ direct_exposure indirect_exposure)')
    witness=checker.compare(reading,mutation,packet)
    if equivalence['status']!='EQUIVALENT_WITHIN_DOMAIN' or witness['status']!='DIFFERENT':
        raise LegalMathError('E_INTEGRITY',details='Addition comparison or dropped-operand witness failed')
    save(work/'symbolic-equivalence.json',equivalence);save(work/'dropped-operand-witness.json',witness)
    report={'status':'RETAINED_ARITHMETIC_QUALIFIED','original_candidate':ident,
        'original_reading_hash':digest(reading),'machine_summary':result['summary'],
        'conditional_backend_cases':sum(len(r['cases']) for r in runtime.values()),
        'symbolic_comparison':equivalence['status'],'mutation_witness':witness['status'],
        'legal_correctness':'NOT_ESTABLISHED','historical_receipt_unchanged':True}
    save(work/'result.json',report);return report


def residuals(work):
    from assurance_successor_resume import ResumingCodex, scoped_issues
    from legalmath.interpretation.assurance.grants import GrantedAllowance, GrantSlice
    from legalmath.qualification import prospective, assurance
    grant=GrantedAllowance(GRANT).verify();study=read(OLD/'unfamiliar-study/result.json');rows=[]
    for task in study['tasks']:
        row={'task_id':task['task_id'],'historical_complete':False,'arms':{}}
        for arm in ('single','ensemble'):
            p=OLD/'unfamiliar-study'/task['task_id']/(arm+'-allowance.json');budget=read(p)
            row['arms'][arm]={'used':len(budget['reservations']),'maximum':budget['maximum'],
                             'remaining':budget['maximum']-len(budget['reservations'])}
        rows.append(row)
    task,dossier,packet,claims,candidates=retained('25ec66')
    case=OLD/'unfamiliar-study/25ec66';provider=ResumingCodex(allowance=GrantSlice(GRANT,case/'ensemble-allowance.json',120,
        global_ceiling=500),prior_directory=case/'ensemble')
    questions={r['candidate_id']:r['question'] for r in dossier['questions']['assignments']}
    eligible=[];blocked=[];details=[]
    for pair in dossier['scoped']['pending_pairs']:
        base=fidelity_v2.request(packet,[c for c in claims if c['claim_id']==pair[0]],
            {pair[1]:candidates[pair[1]]},{pair[1]:questions[pair[1]]},[pair]);admitted=True;roles={}
        for role in ('source-first','qualification-first'):
            req=compact_request({**base,'investigation':{'perspective':role}},profile='v2')
            key=scoped_issues(req)[0];spent=provider.scoped_spent.get(key,0)
            age=time.time()-provider.scoped_started.get(key,time.time())
            roles[role]={'spent':spent,'deadline_expired':age>=86400,'remaining_attempts':max(0,6-spent)}
            admitted &= spent<6 and age<86400
        (eligible if admitted else blocked).append(pair);details.append({'pair':pair,'roles':roles})
    prior_live=[p for p in sorted((OUT/'C6').glob('attempt-*/manifest.json'))
                if read(p)['status']!='RUNNING' and (p.parent/'scoped/model/journal.json').exists()]
    max_calls=min(27 if prior_live else 30,grant['maximum']-grant['used'])
    selection={'task_id':'25ec66','original_dossier':task['ensemble']['dossier'],'pairs':eligible,
        'excluded_pairs':blocked,'pair_history':details,'batch_size':12,'schedule':'round-first',
        'maximum_rounds':2 if prior_live else 1,'maximum_new_calls':max_calls,
        'maximum_actions':60 if prior_live else max_calls,
        'prior_live_manifests':[{'path':relative(p),'sha256':sha(p)} for p in prior_live],
        'calls_needed_for_initial_perspectives':2*math.ceil(len(eligible)/12),
        'scope':'Previously missing scoped perspectives only; all historical source questions and tasks remain open.',
        'issue_history':'ResumingCodex reconstructs prior transport reservations; no per-issue reset.',
        'selection_reason':'The private-market arm is exhausted; eDDA/authentication inventory-unit limits remain. UCITS retains a complete source inventory and unanswered eligible pairs.',
        'inference':'Conditional processing continuation; unequal remaining workload, no comparative accuracy ranking.'}
    save(OUT/'live-selection.json',selection)
    authority=read(OLD/'live-backlog/authority/result.json')
    questions_open=[{'id':q['id'],'missing':q['proposition_missing'],'required_authority':q['required_authority'],
                     'status':'NOT_ESTABLISHED'} for q in authority['questions']]
    # Availability inventory must consult acquired sources, not only the old
    # selected prompt. A previous prompt omission is a processing defect.
    appendix=ROOT/'artifacts/interpretation/round15/execution/action-0005/sources/23ec52-appendix.pdf'
    appendix_receipt=read(str(appendix)+'.receipt.json')
    if sha(appendix)!=appendix_receipt['sha256']:raise LegalMathError('E_INTEGRITY')
    appendix_text,appendix_parser=extract(appendix.read_bytes(),'application/pdf')
    pages=[{'page':i+1,'text':text} for i,text in enumerate(appendix_text.split('\f'))]
    save(work/'available-23ec52-appendix.json',{'source':appendix_receipt,'pages':pages,'parser':appendix_parser})
    for q in questions_open:
        if q['id']=='23ec52-appendix':
            q.update(availability='APPENDIX_ALREADY_ACQUIRED_OLD_PROMPT_OMITTED_IT',
                source={'path':relative(appendix),'sha256':sha(appendix)},
                remaining='Reassess with this appendix and each applicable incorporated provision; source availability does not settle applicability or legal meaning.')
    current_source=OUT/'official-sources/jfiu-current.html';source_receipt=read(current_source.with_suffix('.receipt.json'))
    if sha(current_source)!=source_receipt['sha256']:raise LegalMathError('E_INTEGRITY')
    text,html_parser=extract(current_source.read_bytes(),'text/html')
    position=text.find('XML schema')
    if position<0:raise LegalMathError('E_REFERENCE',details='Expected XML schema announcement absent from acquired source')
    save(work/'jfiu-source-recheck.json',{'source':source_receipt,'parser':html_parser,'xml_schema_mention':text[max(0,position-100):position+350],
        'schema_bytes_acquired':False,'legal_sufficiency':'NOT_ESTABLISHED',
        'finding':'The public announcement identifies a separately supplied schema; it is not the schema itself.'})
    save(work/'authority-premises.json',questions_open)
    window=ROOT/'artifacts/proof-qualified-generalization/2026-09-28/attempt-02/future-window'
    freeze=read(window/'freeze.json');window_hash=read(window.parent/'future-window-report.json')['window_hash']
    prospect=prospective.report(window,window_hash)
    save(work/'prospective-report.json',prospect)
    result={'status':'ALL_FROZEN_TASKS_AND_PREMISES_ACCOUNTED','tasks':rows,'global_used':grant['used'],
        'global_remaining':grant['maximum']-grant['used'],'live_selection':selection,
        'authority_questions':questions_open,'prospective':prospect,
        'current_method_matches_frozen_window':digest(assurance.method_manifest())==prospect['method_hash'],
        'legal_correctness':'NOT_ESTABLISHED','historical_study_complete':False}
    save(work/'result.json',result);save(OUT/'residuals.json',result);return result


def live(work):
    from assurance_successor_resume import ResumingCodex
    from legalmath.interpretation.assurance.grants import GrantSlice, GrantedAllowance
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    from legalmath.interpretation.search.models import Settings
    selected=read(OUT/'live-selection.json');before=GrantedAllowance(GRANT).verify()['used']
    if selected['maximum_new_calls']<1 or not selected['pairs']:
        result={'status':'LIVE_RESOURCE_QUALIFICATION','new_calls':0,'selection':selected,'historical_study_complete':False}
        save(work/'result.json',result);return result
    task,dossier,packet,claims,candidates=retained(selected['task_id'])
    if task['ensemble']['dossier']!=selected['original_dossier']:raise LegalMathError('E_INTEGRITY')
    case=OLD/'unfamiliar-study'/selected['task_id'];ceiling=min(500,before+selected['maximum_new_calls'])
    prior_journals=[]
    for ref in selected.get('prior_live_manifests',[]):
        path=ROOT/ref['path']
        if sha(path)!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
        manifest=read(path)
        if manifest['status']=='RUNNING' or any(sha(ROOT/p)!=h for p,h in manifest['outputs'].items()):
            raise LegalMathError('E_INTEGRITY',details='Prior live phase is active or evidence changed')
        prior_journals.append(path.parent/'scoped/model/journal.json')
    provider=ResumingCodex(allowance=GrantSlice(GRANT,case/'ensemble-allowance.json',120,global_ceiling=ceiling),
                          prior_directory=case/'ensemble',additional_scoped_journals=prior_journals)
    q={r['candidate_id']:r['question'] for r in dossier['questions']['assignments']}
    result=investigate(packet,claims,candidates,q,provider,work/'scoped',required_pairs=selected['pairs'],
        batch_size=selected['batch_size'],maximum_rounds=selected['maximum_rounds'],
        maximum_actions=selected.get('maximum_actions',selected['maximum_new_calls']),deadline_seconds=10800,
        schedule=selected['schedule'],reference_protocol=source_references.PROTOCOL,
        settings=Settings(timeout_seconds=300,max_input_bytes=200000,max_output_bytes=200000))
    old_completed=set(map(tuple,dossier['scoped']['required_pairs']))-set(map(tuple,dossier['scoped']['pending_pairs']))
    new_completed=set(map(tuple,result['required_pairs']))-set(map(tuple,result['pending_pairs']))
    combined=old_completed|new_completed
    report={'status':'BOUNDED_LIVE_PROCESSING_RECORDED','new_calls':GrantedAllowance(GRANT).verify()['used']-before,
        'prior_pairs_with_two_perspectives':len(old_completed),'combined_pairs_with_two_perspectives':len(combined),
        'required_pair_count':len(dossier['scoped']['required_pairs']),
        'remaining_pairs':sorted(set(map(tuple,dossier['scoped']['required_pairs']))-combined),
        'new_scoped_result':result,'historical_study_complete':False,
        'legal_correctness':'NOT_ESTABLISHED','release_eligible':False,
        'qualification':'This continuation does not complete other frozen sources, unresolved questions, or whole-source legal meaning.'}
    save(work/'result.json',report);save(OUT/'live-result.json',report);return report


def documents(work, command):
    # A build preserves the unified work; machine checks cover typography and
    # source/citation retention, not a human readability claim.
    import shutil
    import re
    import os
    from collections import Counter
    from zipfile import ZipFile
    patterns={'labels':r'\\label\{[^}]+\}',
        'displays':r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?|displaymath)\}.*?\\end\{\1\}',
        'citations':r'\\cite\w*\*?(?:\[[^\]]*\])*\{[^}]+\}',
        'listings':r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}'}
    before=[];after=[]
    with ZipFile(OUT/'monograph-before-continuation.zip') as archive:
        for name in archive.namelist():
            if name.endswith('.tex'):
                before.append(archive.read(name).decode());after.append((ROOT/name).read_text())
    preserved={}
    for key,pattern in patterns.items():
        collect=lambda texts:Counter(re.sub(r'\s+',' ',m.group()).strip() for t in texts for m in re.finditer(pattern,t,re.S))
        old,new=collect(before),collect(after)
        if old-new:raise LegalMathError('E_INTEGRITY',details='Lost manuscript '+key)
        preserved[key]=sum(old.values())
    save(work/'manuscript-preservation.json',preserved)
    doc_python=os.environ.get('LEGALMATH_DOC_PY') or shutil.which('python3')
    if not doc_python:raise LegalMathError('E_RESOURCE_LIMIT',details='No document interpreter; set LEGALMATH_DOC_PY')
    command([doc_python,'-c','import sys, fitz; print(sys.executable); print(fitz.VersionBind)'],
            work,'document-environment',timeout=30)
    # The existing builder uses XeLaTeX for fontspec, settles cross-volume
    # references, checks both volumes and exports linked proposal/guide copies.
    command([doc_python,'scripts/build_reader_facing_monograph.py'],work,'monograph',timeout=1200)
    command([doc_python,'scripts/check_monograph.py'],work,'document-check',timeout=120)
    from pypdf import PdfReader
    pdf=PdfReader(ROOT/'docs/monograph/monograph.pdf')
    guide=PdfReader(ROOT/'docs/monograph/process-guide.pdf')
    report={'document_python':doc_python,'monograph_pages':len(pdf.pages),'guide_pages':len(guide.pages),'preservation':preserved,'pdf_sha256':sha(ROOT/'docs/monograph/monograph.pdf'),
            'proposal_copies_equal':sha(ROOT/'docs/proposal/proposal.pdf')==sha(ROOT/'docs/monograph/monograph.pdf'),
            'legal_correctness':'NOT_ESTABLISHED'}
    save(work/'documents.json',report);return report
