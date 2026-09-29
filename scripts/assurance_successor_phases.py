"""Executed phases of the reviewed assurance successor (fixed entry points)."""
from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from run_assurance_successor import ROOT, OUT, DOC, GRANT, read, save, sha, rel, now
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError

JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
SIDE=ROOT/'.localresources/assurance-tools/venv/bin/python'
AT='2026-09-28T00:00:00.000000Z'
TASKS={
 '26EC55': ('private-market-complexity',
    'Under the retained circular, when must an SFC-authorised fund be treated as a complex product for distribution? '
    'Distinguish mandatory classification, discretionary designation, exclusions and missing classification evidence.',
    ['50% or more','case-by-case basis','Except for listed closed-ended','less than 50%','irrespective of whether solicitation']),
 '26EC51': ('edda-verification',
    'Before processing a new simplified eDDA setup request, what account-owner authorisation and identification checks '
    'are required, what alternative methods are described, and what facts prevent a determinate processing decision?',
    ['before processing any new','where (i) cannot be satisfied','obtained by the licensed firm from its bank',
     'identification information','relying solely on deposit record documents provided by clients','where appropriate']),
 '25EC66': ('ucits-transition',
    'Does a material change in a UCITS fund investment objective, policy or restriction require prior SFC approval '
    'under this circular, taking account of product features, home requirements and the application transition?',
    ['home jurisdiction requirements','except for changes','28 November 2025','before the Effective Date',
     'United Kingdom authorised as UK UCITS','post-vetting']),
 '26EC35': ('authentication-transition',
    'What authentication changes are required for internet trading login and device binding, and by when? '
    'Preserve existing-device exceptions, large-broker timing, alternative authentication and any unresolved performance criteria.',
    ['not required to request existing clients to rebind','should not use it','no later than',
     'large internet brokers','more than three','may only allow a longer idle timeout'])}


def command(argv, work, name, timeout=600):
    work.mkdir(parents=True,exist_ok=True)
    record={'argv':list(map(str,argv)),'started_at':now(),'cpu_only':True}
    save(work/(name+'.command.json'),record)
    env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1',
         'PYTHONPATH':str(ROOT/'src'),'TOKENIZERS_PARALLELISM':'false'}
    with (work/(name+'.log')).open('w') as log:
        p=subprocess.run(record['argv'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    record.update(exit_code=p.returncode,finished_at=now(),log_sha256=sha(work/(name+'.log')))
    save(work/(name+'.command.json'),record)
    if p.returncode:raise RuntimeError(f'{name} failed; see {work}/{name}.log')


def tests(work, paths, name='tests', timeout=1200):
    command([ROOT/'.venv/bin/python','-m','pytest',*paths,'-q','-o','faulthandler_timeout=0',
             '--junitxml='+str(work/(name+'.xml'))],work,name,timeout)
    tree=ET.parse(work/(name+'.xml')).getroot()
    counts={k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    if not counts['tests'] or any(counts[k] for k in ('failures','errors','skipped')):raise RuntimeError(str(counts))
    return counts


def source_phase(work):
    from legalmath.interpretation.assurance.sources import extract_document, references, packet_from_context, audit_packet
    frozen=[]
    for ref,(family,question,needles) in TASKS.items():
        path=OUT/f'source-{ref}.json';raw=path.read_bytes();meta=read(path)
        if meta['refNo']!=ref or not meta['html']:raise RuntimeError('Source identity mismatch')
        url='https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo='+ref
        document={'url':url,'media_type':'application/json','data':raw}
        document.update(extract_document(document))
        deps=references(document)
        # A source dependency remains open even if its title is intelligible.
        context={'documents':[document],'references':deps,
                 'findings':document['findings']+[
                     {'kind':'REFERENCE_APPLICABILITY_UNRESOLVED',**d} for d in deps]}
        packet=packet_from_context(context,question)
        missing=audit_packet(packet,context)
        if missing:raise RuntimeError('Frozen source text incomplete: '+str(missing))
        anchors=[]
        for needle in needles:
            matches=[u for u in packet['units'] if needle.casefold() in u['text'].casefold()]
            if not matches:raise RuntimeError('Reference condition missing: '+ref+' '+needle)
            anchors.append({'condition_id':family+'.'+str(len(anchors)), 'needle':needle,
                'evidence':[{'unit_id':u['unit_id'],'quote':u['text']} for u in matches],
                'basis':'Explicit source condition, selected before new generation; not an independently adjudicated case outcome'})
        task={'task_id':ref.lower(),'family':family,'selected_slice':question,'packet':packet,
              'source':{'path':rel(path),'sha256':sha(path),'url':url,'media_type':'application/json'},
              'source_metadata':{k:meta.get(k) for k in ('refNo','title','releasedDate','appendixDocList')},
              'reference_conditions':anchors,'unresolved_references':deps,
              'assessment_at':AT,'publication_design':'RETROSPECTIVE_UNFAMILIAR_SOURCE',
              'prior_exposure':'Index metadata was retained; no earlier source content or interpretation fixture located',
              'pretraining_exposure':'UNKNOWN','selected_before_new_model_answers':True,
              'all_selected_tasks_retained':True,'legal_reference_outcome':'NOT_ADJUDICATED'}
        save(work/(ref+'.task.json'),task); frozen.append({'task_id':task['task_id'],'path':rel(work/(ref+'.task.json')),
                                                       'sha256':sha(work/(ref+'.task.json'))})
    save(OUT/'task-freeze.json',{'at':now(),'tasks':frozen,'model_calls_before_freeze':len(read(OUT/'live-allowance.json')['calls']),
         'reference_conditions_are_not_model_accuracy_labels':True})
    save(work/'task-freeze.json',read(OUT/'task-freeze.json'))
    # Reuse the already installed independent extraction/OCR/region adapters.
    pdf=OUT/'source-26EC35-appendix.pdf'
    request=work/'appendix'/'input.json';save(request,{'path':str(pdf),'sha256':sha(pdf)})
    output=work/'appendix'/'output.json'
    command([SIDE,'-m','legalmath.interpretation.assurance.sidecar','source','--input',request,'--output',output],
            work/'appendix','source-ocr',timeout=1800)
    actual=read(output)
    if not actual['extraction']['pages']:raise RuntimeError('No executed page coverage')
    counts=tests(work,['tests/assurance/test_sources.py','tests/assurance/test_diverse_methods.py'])
    return {'status':'SOURCE_TASKS_AND_REFERENCES_FROZEN','tasks':len(frozen),
            'pdf_pages':len(actual['extraction']['pages']),'tests':counts,
            'open_evidence':['Source references require applicability review.',
                'Reference conditions are source-supported coverage probes, not independent legal outcome labels.',
                'PDF discrepancies retain materiality questions.'], 'release_eligible':False}


def grant_phase(work):
    counts=tests(work,['tests/assurance/test_successor_grants.py','tests/assurance/test_round16.py'])
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    return {'status':'LIVE_SCOPED_DISPATCH_AUTHORIZATION_TESTED','grant':GrantedAllowance(GRANT).verify(),
            'tests':counts,'release_eligible':False}


def meaning_phase(work):
    from legalmath.interpretation.assurance.meaning_bridges import compare_models
    from legalmath.interpretation.assurance.authority_arguments import evaluate
    from legalmath.interpretation.search.formal import Comparisons
    sys.path.insert(0,str(ROOT))
    from tests.assurance.test_successor_meaning import bridge_fixture,authority_fixture
    from tests.assurance.support import packet
    a,b,m=bridge_fixture()
    comparison=compare_models(a,b,packet(),m,Comparisons(work/'mapping-java',JDK,AT))
    save(work/'conditional-mapping.json',comparison)
    p,v=authority_fixture();v['authorities'][0]['applicability']='UNRESOLVED'
    authority=evaluate(v,p,at=AT,jurisdiction='Hong Kong',actor_class='Distributor')
    save(work/'authority-example.json',{'synthetic_fixture':True,'input':v,'result':authority})
    counts=tests(work,['tests/assurance/test_successor_meaning.py','tests/assurance/test_repair.py',
                       'tests/assurance/test_successor_grants.py'])
    return {'status':'CONDITIONAL_FACT_BRIDGES_AND_AUTHORITY_CHECKS_EXECUTED','tests':counts,
            'actual_java_mapping_cases':comparison['comparison']['cases'],
            'open_evidence':['Factual mapping premises and legal priorities require actual source-supported dispositions.'],
            'release_eligible':False}


def proof_phase(work):
    sys.path.insert(0,str(ROOT))
    from tests.assurance.support import packet,reading
    from legalmath.interpretation.search.formal import bundle
    from legalmath.interpretation.assurance.proof_certificate import produce,verify
    r=reading();b=bundle(r,packet(),AT);certificate=produce(r,b,AT,work/'certificate',JDK)
    checked=verify(certificate,r,b,work/'checked',JDK);save(work/'verified.json',checked)
    counts=tests(work,['tests/assurance/test_successor_proof.py'])
    return {'status':'REGISTERED_BOOLEAN_PROOF_PROFILE_EXECUTED','tests':counts,
            'kernel':checked,'runtime_cases':certificate['runtime']['cases'],
            'open_evidence':['Arithmetic, dates and the full Java/compiler semantics remain outside the registered Boolean theorem.',
                             'English meaning is a premise, not the conclusion of this certificate.'], 'release_eligible':False}


def workflow_phase(work):
    sys.path.insert(0,str(ROOT))
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation,verify
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source,settings
    from tests.search.support import FunctionProvider
    provider=FunctionProvider(complete_responder)
    runner=CompleteInvestigation(ROOT,work/'worked-investigation',provider,JDK,AT,settings=settings(),
                                 maximum_scoped_actions=12,scoped_rounds=1)
    result=runner.run([source()],'Selected gift control')
    receipt=verify(ROOT,result);save(work/'verified.json',receipt)
    if not result['execution_complete']:raise RuntimeError('Worked investigation did not execute completely')
    before=len(provider.requests);runner.run([source()],'Selected gift control')
    if len(provider.requests)!=before:raise RuntimeError('Resume spent additional model invocations')
    counts=tests(work,['tests/assurance/test_successor_workflow.py','tests/assurance/test_successor_grants.py',
                       'tests/assurance/test_integrated_workflow.py','tests/assurance/test_round16.py'])
    return {'status':'COMPLETE_LOCAL_INVESTIGATION_EXECUTED','tests':counts,
            'retained_local_provider_requests':before,'new_live_calls':0,
            'open_evidence':['Live circular investigations and independent source outcomes remain to be executed.'],
            'release_eligible':False}


def execute(name,work):
    from assurance_successor_live import run as live_phase
    from assurance_successor_duties import run as duty_phase
    from assurance_successor_study import run as study_phase
    from assurance_successor_evaluate import run as evaluation_phase
    from assurance_successor_documents import run as document_phase
    from assurance_successor_finalize import run as final_phase
    functions={'S1':source_phase,'S2':grant_phase,'S3':meaning_phase,'S4':proof_phase,'S5':workflow_phase,
               'S6':live_phase,'S7':duty_phase,'S8':study_phase,'S9':evaluation_phase,'S10':document_phase,'S11':final_phase}
    if name not in functions:raise RuntimeError('Required phase implementation not yet registered: '+name)
    return functions[name](work)
