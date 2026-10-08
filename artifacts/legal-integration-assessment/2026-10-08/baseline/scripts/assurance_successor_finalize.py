"""No-skip full regression and evidence-qualified per-gap closure report."""
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET
from run_assurance_successor import ROOT,OUT,DOC,GRANT,read,save,sha,rel,now,phase_result,incomplete_assessment_basis
from assurance_successor_phases import command,JDK
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.errors import LegalMathError


def material_hashes():
    return {rel(p):sha(p) for base in ('src','tests','scripts') for p in sorted((ROOT/base).rglob('*'))
            if p.is_file() and p.suffix in ('.py','.java','.lean','.json') and '__pycache__' not in p.parts}


def run(work):
    before=material_hashes();save(work/'tested-inputs.json',before)
    from assurance_successor_regression import current_receipt
    prior_regression=current_receipt()
    if prior_regression:
        (work/'full-regression.xml').write_bytes((ROOT/prior_regression['result']['files']['xml']['path']).read_bytes())
        save(work/'regression-reuse.json',prior_regression)
    else:
        command([ROOT/'.venv/bin/python','-m','pytest','tests','-q','-o','faulthandler_timeout=0',
                 '--junitxml='+str(work/'full-regression.xml')],work,'full-regression',timeout=3600)
    tree=ET.parse(work/'full-regression.xml').getroot();suites=[tree] if tree.tag=='testsuite' else list(tree)
    counts={k:sum(int(s.get(k,'0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    if counts['tests']<1029 or any(counts[k] for k in ('failures','errors','skipped')):
        raise RuntimeError('Required full regression is not a no-skip pass')
    if before!=material_hashes():raise RuntimeError('Implementation changed during full verification')
    state=read(OUT/'state.json');results={}
    assessment=read(work/'start-manifest.json').get('incomplete_study_assessment')
    if assessment and assessment!=incomplete_assessment_basis(state):raise RuntimeError('Changed incomplete-study assessment basis')
    for phase in ('S0','S1','S2','S3','S4','S5','S6','S7','S8','S9','S10'):
        p=state['phases'][phase];m=read(ROOT/p['attempts'][-1]['manifest'])
        if m['status']!='PASSED' and not (phase=='S8' and assessment):raise RuntimeError('Incomplete phase '+phase)
        results[phase]=phase_result(m)
    grant=GrantedAllowance(GRANT).verify()
    # Bind accepted live dossiers and every surviving backlog item again.
    from assurance_successor_revalidate import verify_retained
    from assurance_successor_study import CATALA
    from legalmath.interpretation.assurance import proof_certificate,scoped_investigation
    from legalmath.interpretation.search.formal import bundle
    from assurance_successor_audit import audit_journals,check_scoped_result,check_pdf_result
    dossier_checks=[];proof_checks=[];live_limits=[]
    study_manifest=read(ROOT/state['phases']['S8']['attempts'][-1]['manifest'])
    for case in results['S8']['tasks']:
        ref=case['ensemble'].get('dossier')
        if ref:
            if sha(ROOT/ref['path'])!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
            dossier=read(ROOT/ref['path'])
            checked=verify_retained(ROOT,dossier,study_manifest['implementation_archive'],
                work/'current-runtime-replay'/case['task_id'],JDK,catala=CATALA)
            dossier_checks.append({'task_id':case['task_id'],**checked})
            packet=read(ROOT/dossier['packet']['path']);candidates=read(ROOT/dossier['candidates']['path'])
            questions={r['candidate_id']:r['question'] for r in dossier['questions']['assignments']}
            check_scoped_result(ROOT/dossier['component_refs']['scoped']['path'],packet,
                read(ROOT/dossier['claims']['path']),candidates,questions)
            for index,row in enumerate(dossier['proofs']):
                if row['status']=='CHECKED':
                    reading=candidates[row['candidate_id']]
                    receipt=proof_certificate.verify(row['certificate'],reading,
                        bundle(reading,packet,dossier['binding']['at']),
                        work/'certificate-replay'/case['task_id']/str(index),JDK)
                    proof_checks.append({'task_id':case['task_id'],'candidate_id':row['candidate_id'],'receipt':receipt})
                    if row['certificate']['runtime']['status']!='EXHAUSTIVE_FINITE_JAVA_CHECK':
                        live_limits.append({'task_id':case['task_id'],'candidate_id':row['candidate_id'],
                            'kind':'JAVA_CERTIFICATE_DOMAIN_NOT_ENUMERATED',
                            'evidence':row['certificate']['runtime']})
                else:live_limits.append({'task_id':case['task_id'],'candidate_id':row['candidate_id'],
                                        'kind':'UNSUPPORTED_CERTIFICATE_PROFILE','evidence':row})
            live_limits.extend({'task_id':case['task_id'],'kind':'UNCERTAIN_QUESTION_ASSIGNMENT','evidence':r}
                               for r in dossier['questions']['assignments'] if r['assignment_status']=='UNCERTAIN')
            for index,batch in enumerate(dossier['scoped']['batches']):
                if batch['missing_perspectives'] or not batch['reconciliation'] or batch['reconciliation']['status']!='PROPOSED_JUDGMENTS_AGREE':
                    live_limits.append({'task_id':case['task_id'],'kind':'UNRESOLVED_SCOPED_JUDGMENTS','batch':index,
                        'required_pairs':batch['required_pairs'],'missing_perspectives':batch['missing_perspectives'],
                        'reconciliation':batch['reconciliation']})
    save(work/'dossier-checks.json',dossier_checks)
    save(work/'certificate-rechecks.json',proof_checks)
    save(work/'journal-rechecks.json',audit_journals(OUT))
    prior=read(ROOT/'artifacts/interpretation/round15/remaining-work.json')
    backlog=read(OUT/'live-backlog/scoped-unlisted-authority-repair/result.json')
    inherited={(r['case_id'],r['claim_id'],r['candidate_id']) for r in prior['restored_pair_rows']}
    retained={(j['case_id'],*pair) for j in backlog['jobs'] for pair in j['result']['required_pairs']}
    if inherited!=retained:raise LegalMathError('E_INTEGRITY',details='Backlog denominator changed')
    from decision_live import load_case
    case_inputs={cid:load_case(cid) for cid in ('26ec2','23ec46')}
    scoped_checks=[]
    for job in backlog['jobs']:
        path=ROOT/job['prior_evidence']['path'] if 'prior_evidence' in job else OUT/'live-backlog/scoped-unlisted-authority-repair'/job['case_id']/f"batch-{job['batch']:03}"/'result.json'
        if read(path)!=job['result']:raise LegalMathError('E_INTEGRITY',details='Detached backlog result')
        data=case_inputs[job['case_id']]
        scoped_checks.append(check_scoped_result(path,data['packet'],data['claims'],data['candidates'],
            backlog['question_assignments'][job['case_id']]['questions']))
    save(work/'backlog-rechecks.json',scoped_checks)
    pdf=read(OUT/'live-backlog/pdf/result.json');authority=read(OUT/'live-backlog/authority/result.json')
    issues=[r for r in read(ROOT/'artifacts/interpretation/round14/pdf-resolution.json')['issues']
            if r['issue_id'] in set(prior['pdf_pending_ids'])]
    save(work/'pdf-recheck.json',check_pdf_result(OUT/'live-backlog/pdf/result.json',ROOT,issues))
    if {r['issue_id'] for r in pdf['items']}!=set(prior['pdf_pending_ids']):
        raise LegalMathError('E_INTEGRITY')
    remaining={'study_execution_complete':results['S8']['execution_complete'],
        'unfinished_study_tasks':[t for t in results['S8']['tasks'] if t['single']['status']!='EXECUTED' or not t['ensemble'].get('execution_complete',False)],
        'inherited_pending_pairs':backlog['pending_pairs'],
        'inherited_unassessed_dimensions':[{'case_id':j['case_id'],'pair':list(p)} for j in backlog['jobs']
            for p in sorted(set(map(tuple,j['result']['required_pairs']))-
                scoped_investigation.fully_assessed_pairs(j['result']['batches']))],
        'unresolved_question_assignments':{cid:v['unresolved_question_assignments'] for cid,v in backlog['question_assignments'].items()},
        'inherited_unresolved_scoped':[{'case_id':j['case_id'],'batch':j['batch'],'required_pairs':b['required_pairs'],
            'reconciliation':b['reconciliation'],'missing_perspectives':b['missing_perspectives']}
            for j in backlog['jobs'] for b in j['result']['batches']
            if b['missing_perspectives'] or not b['reconciliation'] or b['reconciliation']['status']!='PROPOSED_JUDGMENTS_AGREE'],
        'inherited_proposed_followups':[{'case_id':j['case_id'],'claim_id':r['claim_id'],'candidate_id':r['candidate_id'],
            'questions':r['followup_questions']} for j in backlog['jobs'] for b in j['result']['batches']
            for p in b['proposals'] for r in p['checks'] if r['followup_questions']],
        'unencoded_parents':prior['parents'],'pdf_uncertainty':[r for r in pdf['items'] if r['status']!='TWO_VISUAL_PROPOSALS_AGREE'],
        'pdf_materiality_not_certified_ids':[r['issue_id'] for r in pdf['items'] if not r['source_materiality_certified']],
        'authority_questions':authority['questions'],'authority_proposals':authority['proposals'],
        'unfamiliar_investigation_limits':live_limits,'conditional_evaluation':results['S9'],
        'legal_materiality_closed_by_visual_agreement':False,'bank_release_eligible':False}
    save(OUT/'remaining-work.json',remaining)
    successor={'profile':'assurance-successor-next.v1','basis':{'path':rel(OUT/'remaining-work.json'),
        'sha256':sha(OUT/'remaining-work.json')},'remaining_authorized_calls':500-grant['used'],
        'must_not_reset_grant_or_attempts':True,'tasks':[
        {'id':'N0','question':'Which frozen investigations did not complete, and which exact source obligations remain?',
         'inputs':['unfinished_study_tasks','unfamiliar_investigation_limits'],
         'required_action':'Inspect each active source/method revision, initial inventories, current claims, candidate files and producer journals. Preserve failed and interrupted work; apply the reviewed capacity-repair contract to the measured unfinished stage only.',
         'acceptance':'All frozen tasks and original source obligations remain accounted for; resumed processing completes or records an explicit unchanged resource/source limit. Partial candidate execution never counts as a completed source investigation.',
         'implementation_contract':'docs/implementation/assurance-successor/capacity-repair-contract.md'},
        {'id':'N1','question':'Which inherited dimensions lack executed judgments?',
         'inputs':['inherited_pending_pairs','inherited_unassessed_dimensions','unresolved_question_assignments',
                   'inherited_unresolved_scoped','inherited_proposed_followups'],
         'required_action':'Decompose only the measured unfinished work into exact source/question pairs; preserve prior responses and execute a reviewed bounded continuation.',
         'acceptance':'All required dimensions have a supported disposition or an explicit exhausted-resource/source-premise reason; no automatic pruning.'},
        {'id':'N2','question':'Which source dependencies can be resolved from additional official text?',
         'inputs':['authority_questions','authority_proposals','pdf_uncertainty'],
         'required_action':'Acquire the specifically named missing official document or higher-quality page, bind edition and applicability, then reopen only affected judgments.',
         'acceptance':'Exact new passages or pixels answer the stated question; unresolved institutional or legal premises remain explicit.'},
        {'id':'N3','question':'Which proposed rules omit conditions or answer the wrong question?',
         'inputs':['conditional_evaluation','unfamiliar_investigation_limits','unencoded_parents','unfinished_study_tasks'],
         'required_action':'Investigate each contrary decisive result with its unchanged program, stipulated facts, proposed mapping and source qualification. Preserve rival schemas and duties.',
         'acceptance':'An executed discriminating case explains the discrepancy; corrected code passes the original and added cases without changing the frozen reference.'},
        {'id':'N4','question':'Which formal language and host semantics are unsupported?',
         'inputs':['unfamiliar_investigation_limits','unencoded_parents'],
         'required_action':'Implement the smallest source-motivated missing semantic profile with an explicit proof target and actual Java/Catala boundary checks.',
         'acceptance':'Unsupported cases gain a checked implementation and negative mutation evidence; the supported proof scope is declared exactly.',
         'implementation_contract':'docs/implementation/assurance-successor/next-arithmetic-profile-spec.md'},
        {'id':'N5','question':'Which propositions generalize to unseen inputs and amended sources?',
         'inputs':['conditional_evaluation','unfamiliar_investigation_limits'],
         'required_action':'Connect the remaining investigation outputs to the existing shared proof-qualified route. Bind each promoted proposition to its exact source edition, facts, semantic premises, method version and quantified domain. Extend the checked proof and generated-challenge domains where measured cases require it. Verify eligibility under the existing frozen prospective window before adding any observation; retain every unfinished, unsupported or abstained case and keep later repairs in a separate development window.',
         'acceptance':'Every selected result has either a checked proposition with an explicit domain or an explicit qualification. Prospective generalization remains NOT_ESTABLISHED until eligible observations exist; no human answer key, adjudication, rating or acceptance gate is used.',
         'implementation_contract':'docs/implementation/proof-qualified-generalization/product.md',
         'existing_increment':'docs/implementation/proof-qualified-generalization/results.md',
         'external_decision':'Set the publication and operating scope and authenticate source editions; these are provenance and deployment decisions, not human quality labels.'},
        {'id':'N6','question':'Can every normative conclusion be traced to exact source spans?',
         'inputs':['unfinished_study_tasks','unfamiliar_investigation_limits','authority_questions'],
         'required_action':'Implement closed source-unit and precomputed-span identifiers bound to the packet digest, unchanged Unicode text and half-open codepoint coordinates. Resolve quotation strings deterministically; reject missing, altered or foreign references. Keep substantive relevance and source-role judgments separate from exact quotation integrity.',
         'acceptance':'Every retained proposition and unresolved alternative has an integrity-checked source-span set or an explicit missing-source qualification.',
         'implementation_contract':'docs/implementation/assurance-successor/source-reference-protocol-spec.md'},
        {'id':'N7','question':'Does bounded capacity give each source and method a fair chance to complete?',
         'inputs':['unfinished_study_tasks','inherited_pending_pairs','conditional_evaluation'],
         'required_action':'Use a round-first scheduler with per-source and per-method reservations, explicit retry budgets and a complete attempt ledger. Process every eligible review batch before allocating additional depth to any one batch.',
         'acceptance':'The scheduler reports complete denominators, no starvation, preserved partials and an explicit resource/source limit when it cannot finish. A high score cannot be produced by leaving other eligible batches unattempted.',
         'implementation_contract':'docs/implementation/assurance-successor/capacity-repair-contract.md'}],
        'automatic_release':False}
    save(OUT/'successor-plan.json',successor)
    closure=[
      {'gap':'G1','capability':'Persistent complete source/search/scoped-proof/Java workflow and revision invalidation',
       'evidence':['S5','S6','S8','S11'],'status':'IMPLEMENTED_WITH_CASE_LIMITS',
       'remaining':'Unencoded or unfinished live readings and unresolved source judgments cannot be promoted.'},
      {'gap':'G2','capability':'Multiple extractors, actual page imagery, OCR and complete retained source backlog',
       'evidence':['S1','S6'],'status':'IMPLEMENTED_WITH_OPEN_SOURCE_EVIDENCE',
       'remaining':'PDF materiality, authority applicability and completeness of incorporated sources require supported dispositions.'},
      {'gap':'G3','capability':'Explicit factual models and conditional cross-schema bridges with original Java comparisons',
       'evidence':['S3','S8'],'status':'IMPLEMENTED_CONDITIONAL_PROFILE',
       'remaining':'A successful conditional mapping does not establish its classification or frame premises.'},
      {'gap':'G4','capability':'Source-bound applicability, text role, treatment and priority-cycle checks',
       'evidence':['S3','S6','S8'],'status':'IMPLEMENTED_BOUNDED_PROFILE',
       'remaining':'Judicial-corpus coverage, authoritative treatment and legal-priority dispositions are not established.'},
      {'gap':'G5','capability':'Blind contexts, complementary formal/source routes, controlled common errors and joint-miss reporting',
       'evidence':['S6','S9','S11'],'status':'MECHANISMS_IMPLEMENTED_EMPIRICAL_CLOSURE_OPEN',
       'remaining':'No machine-independent evidence yet establishes natural-language legal correctness, cross-model independence or future error rates; the product must not claim review-cost reduction.'},
      {'gap':'G6','capability':'Registered Boolean Lean lowering certificate, actual finite Java enumeration and retained Catala route',
       'evidence':['S4','S5','S8','S11'],'status':'NARROW_FORMAL_PROFILE_CHECKED',
       'remaining':'Whole Java compiler theorem, temporal/arithmetic theorem and English entailment are outside the certificate.'},
      {'gap':'G7','capability':'Attributed raw contact-history Java boundary and exact decimal host boundary',
       'evidence':['S7','S11'],'status':'CONTACT_AND_NUMERIC_PROFILES_IMPLEMENTED',
       'remaining':'Urgency, timezone, completeness and substantive performance remain explicit premises; other duties and bank integration are not closed.'},
      {'gap':'G8','capability':'Four frozen unfamiliar-source tasks, sixteen conditional probes, retained failures and source-change reopening',
       'evidence':['S1','S8','S9','S11'],'status':'RETROSPECTIVE_EVIDENCE_ONLY',
       'remaining':'Eligible future-source observations in the existing frozen prospective window, checked propositions covering the target domain and calibrated future-error evidence remain open.'}]
    if before!=material_hashes():raise RuntimeError('Implementation changed during final evidence reconstruction')
    evidence={rel(p):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in
              ('state.json','next-phase-plan.json','final-report.json','grant-checkpoint.json','.master.lock')
              and not p.name.endswith(('.lock','-wal','-shm'))}
    report={'status':'ENGINEERING_VERIFIED_STUDY_INCOMPLETE' if assessment else 'ENGINEERING_EXECUTION_COMPLETED_WITH_RETAINED_UNCERTAINTY',
        'overall_execution_complete':not bool(assessment),'assessment_complete':True,
        'incomplete_study_assessment':assessment,'at':now(),'regression':counts,
        'retained_evidence':evidence,'evidence_inventory_scope':'All stable campaign files present before final reporting; mutable controller status and this self-referential report excluded',
        'phase_results':results,'grant':grant,'closure':closure,'material_inputs':before,
        'remaining_work':{'path':rel(OUT/'remaining-work.json'),'sha256':sha(OUT/'remaining-work.json')},
        'retained_dossier_revalidation':{'path':rel(work/'dossier-checks.json'),'sha256':sha(work/'dossier-checks.json')},
        'independent_certificate_replays':len(proof_checks),
        'decision_table':{'decision':'Accept verification of the available engineering increment; retain incomplete study' if assessment else 'Accept executed engineering increment; do not promote legal correctness or bank release',
          'primary_criterion':'Full regression passed; complete study criterion failed' if assessment else 'Executed phases and no-skip full regression',
          'veto_status':'Study resource veto and unresolved legal/source premises remain' if assessment else 'Open legal/source premises veto interpretive promotion',
          'main_uncertainty':'Conditional source/fact interpretation and unfamiliar-task coverage',
          'next_justified_action':'Use the measured residual ledger; resolve source premises and implement unsupported semantics',
          'not_concluded':'Universal English correctness, reviewer elimination, method independence or production readiness'},
        'inference_status':{'hard_veto_screen':'Full engineering regression passed',
          'statistically_supported_ranking':False,'descriptive_only':'Four retrospective tasks and conditional source-case outcomes',
          'default_readiness':False,'next_evidence':'Kernel-checked propositions, source-preserving executable challenges, independent runtime checks and a frozen prospective source-change window'},
        'post_run_red_team':{'strongest_alternative':'Shared source classification or model factual mapping can make all methods agree incorrectly',
           'overturning_evidence':'A supported omitted qualification or unsafe decisive result on a held-out case',
           'weakest_evidence':'Semantic factual mappings and non-independent conditional reference outcomes'},
        'all_scientific_gaps_closed':False,'release_eligible':False}
    save(work/'final-report.json',report);save(OUT/'final-report.json',report)
    save(OUT/'grant-checkpoint.json',{'calls':grant['used'],'sha256':sha(OUT/'live-allowance.json'),'predecessor_sha256':grant['predecessor_hash']})
    lines=['# Successor execution and remaining work','',
        'The engineering verification and incomplete-study assessment finished. S8 remains failed; the complete campaign acceptance criterion has not been met.' if assessment else
        'The engineering campaign executed its reviewed phases. Its result is conditional assurance, not automatic legal approval.','',
        f"Full regression: {counts['tests']} tests; zero failures, errors or skips. Additional model calls: {grant['used']}/500.",'',
        '| Gap | Executed capability | Remaining closure evidence |','|---|---|---|']
    lines.extend(f"| {r['gap']} | {r['capability']} | {r['remaining']} |" for r in closure)
    lines+=['','The exact phase results and source/program identities are in `artifacts/assurance-successor/2026-09-28/final-report.json`.',
            'Keep the old and additional allowance histories; never reset either to make an unfinished investigation look complete.','',
            'Candidate failure is not research-direction failure. Source, schema and implementation failures trigger the corresponding bounded repair; unresolved legal premises veto promotion.']
    (DOC/'execution-result.md').write_text('\n'.join(lines)+'\n')
    (DOC/'reset-memo.md').write_text('# Successor reset memo\n\nContinue from the final report and exact source/task identities. The next work is evidence-specific, not another generic assurance checklist.\n\n'+
        '\n'.join('- '+r['gap']+': '+r['remaining'] for r in closure)+'\n')
    (DOC/'next-phase-plan.md').write_text('# Measured continuation after the successor\n\n'+
        'The exact input identities and acceptance conditions are in `artifacts/assurance-successor/2026-09-28/successor-plan.json`.\n'+
        f"Remaining authorized model calls: {500-grant['used']}; neither ledger is reset.\n\n"+
        '\n\n'.join('## '+t['id']+' — '+t['question']+'\n\n'+t['required_action']+'\n\nAcceptance: '+t['acceptance'] for t in successor['tasks'])+'\n')
    return {'status':report['status'],'overall_execution_complete':report['overall_execution_complete'],
            'assessment_complete':True,'regression':counts,'grant':grant,'closure':closure,
            'open_evidence':[r['remaining'] for r in closure],'release_eligible':False}
