"""Fixed continuation of the current master; no grant or deadline resets."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import fcntl
import json
import time

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, TOKENIZER, QUESTIONS, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require
from scripts.legal_integration_phased_repair import WORK, REVIEW, PREVIOUS_WORK, USER
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased.evidence_store import load_exact, save_exact
from legalmath.interpretation.assurance.phased.admission import admit

LIVE = WORK / 'live'
FAIRNESS_PROFILE = 'independent-acquisition-before-answer-drain.v1'
FAIRNESS_FIELD = 'acquisition_fairness_profile'


def active_live(program):
    if program.get('repaired_retry_continuation'):
        return Path(program['repaired_retry_continuation']['runtime'])
    if program.get('baseline_corpus_repair'):
        return Path(program['baseline_corpus_repair']['runtime'])
    if program.get('window_continuation'):
        return Path(program['window_continuation'].get('service_inheritance',program['window_continuation'])['runtime'])
    if program.get('review_repair'):
        if program['review_repair'].get('optional_quote_validation'):
            return Path(program['review_repair']['optional_quote_validation']['runtime'])
        if program['review_repair'].get('deployment'):
            return Path(program['review_repair']['deployment']['runtime'])
        if program['review_repair'].get('timeout_correction'):
            return Path(program['review_repair']['timeout_correction']['runtime'])
        if program['review_repair'].get('receipt_correction'):
            return Path(program['review_repair']['receipt_correction']['runtime'])
        return Path(program['review_repair']['work']) / 'live'
    if program.get('common_capacity'):
        return Path(program['common_capacity']['work']) / 'live'
    if program.get('candidate_capacity_retry'):
        return Path(program['candidate_capacity_retry']['work']) / 'live'
    if program.get('synthesis_resolution'):
        return Path(program['synthesis_resolution']['work']) / 'live'
    if program.get('synthesis_continuation'):
        return Path(program['synthesis_continuation']['work']) / 'live'
    if program.get('gap_preservation'):
        return Path(program['gap_preservation']['work']) / 'live'
    if program.get('failure_recovery'):
        return Path(program['failure_recovery']['work']) / 'live'
    if program.get('settled_recovery'):
        return Path(program['settled_recovery']['work']) / 'live'
    if program.get('frontier_refresh'):
        return Path(program['frontier_refresh']['work']) / 'live'
    if program.get('repair_execution'):
        return Path(program['repair_execution']['work']) / 'live'
    if program.get('complete_account_capacity_repair'):
        from scripts.legal_integration_complete_account_capacity import WORK
        return WORK / 'live'
    if program.get('account_reconstruction_repair'):
        from scripts.legal_integration_account_reconstruction import WORK as RECONSTRUCTION_WORK
        return RECONSTRUCTION_WORK / 'live'
    if program.get('account_instruction_repair'):
        from scripts.legal_integration_account_instruction_repair import WORK as INSTRUCTION_WORK
        return INSTRUCTION_WORK / 'live'
    if program.get('qualification_continuation'):
        from scripts.legal_integration_qualification_continuation import WORK as QUALIFICATION_WORK
        return QUALIFICATION_WORK / 'live'
    if program.get('lossless_account_repair'):
        from scripts.legal_integration_lossless_repair import WORK as LOSSLESS_WORK
        return LOSSLESS_WORK / 'live'
    if program.get('response_schema_repair'):
        from scripts.legal_integration_schema_repair import WORK as SCHEMA_WORK
        return SCHEMA_WORK / 'live'
    if program.get('account_capacity_repair'):
        from scripts.legal_integration_account_repair import WORK as ACCOUNT_WORK
        return ACCOUNT_WORK / 'live'
    return LIVE


def question_live(program, q):
    if program.get('common_capacity'):
        return active_live(program)
    if q in program.get('candidate_capacity_retry', {}).get('checkpoints', {}):
        return Path(program['candidate_capacity_retry']['work']) / 'live'
    if q in program.get('synthesis_resolution', {}).get('recoveries', {}):
        return Path(program['synthesis_resolution']['work']) / 'live'
    if program.get('synthesis_continuation') and q == 'p10':
        return Path(program['synthesis_continuation']['work']) / 'live'
    if program.get('gap_preservation') and q == 'p10':
        return Path(program['gap_preservation']['work']) / 'live'
    if program.get('failure_recovery') and q == 'p10':
        return Path(program['failure_recovery']['work']) / 'live'
    if q in program.get('settled_recovery', {}).get('live_directories', {}):
        return Path(program['settled_recovery']['live_directories'][q])
    revision = program.get('repair_execution') or program.get('complete_account_capacity_repair')
    return Path(revision['live_directories'][q]) if revision else active_live(program)


def common_directory(program, q):
    if program.get('common_capacity'):
        return active_live(program) / q / 'product'
    if q in program.get('candidate_capacity_retry', {}).get('checkpoints', {}):
        return Path(program['candidate_capacity_retry']['work']) / 'live' / q / 'product'
    if q in program.get('synthesis_resolution', {}).get('recoveries', {}):
        return Path(program['synthesis_resolution']['work']) / 'live' / q / 'product'
    if program.get('synthesis_continuation') and q == 'p10':
        from scripts.legal_integration_synthesis_continuation import completion
        done = completion()
        if done is not None:
            return Path(done['common_directory'])
    if program.get('gap_preservation') and q == 'p10':
        from scripts.legal_integration_gap_preservation import completion
        done = completion()
        if done is not None:
            return Path(done['common_directory'])
    if program.get('failure_recovery') and q == 'p10':
        from scripts.legal_integration_failure_recovery import completion
        done = completion()
        if done is not None:
            return Path(done['common_directory'])
    if q in program.get('settled_recovery', {}).get('common_directories', {}):
        return Path(program['settled_recovery']['common_directories'][q])
    revision = program.get('repair_execution') or program.get('complete_account_capacity_repair')
    return Path(revision['common_directories'][q]) if revision else active_live(program) / 'common' / q


def configure(q=None):
    from scripts import legal_integration_campaign as campaign
    program=read(ROOT/PROGRAM)
    campaign.LIVE=question_live(program,q) if q is not None else active_live(program)
    campaign.ENVELOPE=Path(program['prerequisite_repair']['source']['path'])
    campaign.LIMITS=Limits()
    return campaign


def prepare(directory):
    campaign=configure()
    revision=read(ROOT/PROGRAM)['phased_acquisition_repair']
    baseline=read(ROOT/revision['baseline']['path'])
    old=read(ROOT/revision['prior_binding']['path'])
    require(ref(ROOT,BASE/'current-binding.json') == {
        'path':str(BASE/'current-binding.json'),'sha256':revision['prior_binding']['sha256']},
        'Current binding is not the reviewed predecessor')
    service=campaign.provider()
    grant=read(ROOT/BASE/'live-grant.json');ledger=read(ROOT/BASE/'live-calls.json')
    save(directory/'ledger-before.json',ledger)
    scope={'profile':'reviewed-shared-phase-service.v1','grant_hash':digest(grant),
        'review':ref(ROOT,REVIEW),'prior_circuit':ref(ROOT,PREVIOUS_WORK/'live/stages/acquisition/service-circuit.json'),
        'prior_replacements':ref(ROOT,PREVIOUS_WORK/'live/stages/acquisition/service-recovery.json'),
        'requalification':'One reviewed scoped grouped-review continuation; no automatic circuit reset.',
        'prior_replacement_count':13,'maximum_replacements_including_prior':48}
    save(ROOT/LIVE/'service/scope.json',scope)
    scope_ref=ref(ROOT,LIVE/'service/scope.json')
    prior=read(ROOT/scope['prior_replacements']['path'])
    save(ROOT/LIVE/'service/service-recovery.json',{**prior,'stage_hash':scope_ref['sha256']})
    # All old failures remain in their original open circuit. This reviewed
    # continuation gets one finite shared circuit, which every phase uses.
    save(ROOT/LIVE/'service/service-circuit.json',{'stage_hash':scope_ref['sha256'],
        'consecutive_failures':0,'failed_slots':[],'open':False,'prior_circuit':scope['prior_circuit']})
    binding=deepcopy(old)
    binding.update(user_instruction=USER,review=ref(ROOT,REVIEW),predecessor=revision['prior_binding'],
        ledger_before=ref(ROOT,directory/'ledger-before.json'),program=ref(ROOT,PROGRAM),
        phase_service_scope=scope_ref,resources=revision['population'],
        preflight_stage_maximum=48,acquisition_requires='Retained successful controls and own-question canary; current binding. New grouped qualification gates answer reviews.')
    binding.pop('retained_initial',None)
    bindings=[ref(ROOT,p) for p in sorted((ROOT/'src/legalmath').rglob('*.py'))]
    bindings += [ref(ROOT,p) for p in sorted((ROOT/'scripts').glob('legal_*.py'))]
    bindings += [ref(ROOT,p) for p in (PROGRAM,PLAN,REVIEW,campaign.ENVELOPE,BASE/'campaign-routing.toml',
        Path('requirements-context.lock'),Path('pyproject.toml'))]
    bindings += [revision[k] for k in ('baseline','local_review','census','reconstructed','population','prior_binding')]
    bindings += [scope_ref,scope['prior_circuit'],scope['prior_replacements'],
        ref(ROOT,PREVIOUS_WORK/'settled-acquisition/reconstruction/investigation.json')]
    binding['bindings']=bindings
    archives={(r['previous']['path'],r['previous']['sha256']):r for r in old['historical_archives']}
    for r in baseline['archived']:
        archives[(r['previous']['path'],r['previous']['sha256'])]=r
    binding['historical_archives']=list(archives.values())
    save(ROOT/BASE/'current-binding.json',binding)
    service.check()
    return {'binding':ref(ROOT,BASE/'current-binding.json'),'scoped_qualification_pending':True,
        '_conclusion':'Exact current product and shared service scope bound; original grant and 1,507 prior charges preserved.'}


def phase_admit(owner):
    live=active_live(read(ROOT/PROGRAM))
    return lambda name,count:admit(ROOT,BASE,live,name,count,owner=owner)


def session(directory,service,*,owner,q=None,tool=None,shared=None,envelope=None,maximum_calls=8100):
    campaign=configure()
    value=envelope or read(ROOT/campaign.ENVELOPE)
    capacity = read(ROOT/PROGRAM).get('common_capacity', {}).get('capacity_profile')
    product=PhasedProduct(ROOT,directory,service,value,tokenizer(ROOT/TOKENIZER),limits=Limits(),
        maximum_calls=maximum_calls,maximum_corrections=1,selected_tools=[] if tool is None else [tool],
        active_questions=[q] if q else [x['question_id'] for x in value['original_questions']],
        shared_prefix=shared,phase_admit=phase_admit(owner),phase_identity=ref(ROOT,BASE/'current-binding.json')['sha256'],
        common_capacity_profile=capacity)
    product.install_dispatch_admission()
    return product


def qualification(service):
    if read(ROOT/PROGRAM).get('account_capacity_repair'):
        from scripts.legal_integration_account_controls import qualify_reviewer
        return qualify_reviewer(service)
    if read(ROOT/PROGRAM).get('route_context_repair'):
        from scripts.legal_integration_route_controls import qualify
        return qualify(service)
    from scripts.legal_integration_reopening_live import fixture
    cases=[(False,False,'remote-exception'),(True,False,'changed-exception'),(False,True,'missing-incorporated-rule')]
    rows=[]
    for mutation,missing,name in cases:
        value=fixture(mutation,explicit_scope=True,missing_authority=missing)
        product=session(ROOT/LIVE/'qualification'/name,service,owner='qualification-'+name,envelope=value,maximum_calls=16)
        question=value['original_questions'][0]
        expected='DUTY_UNRESOLVED' if missing else 'DUTY_REQUIRED' if mutation else 'DUTY_NOT_REQUIRED'
        opposite='DUTY_REQUIRED' if not mutation else 'DUTY_NOT_REQUIRED'
        records=[r for r in product.route.records.values() if r['kind']=='source']
        # Fixed control answers do not replace model-generated product answers.
        # They test the newly introduced reviewer, its exception sensitivity and
        # its genuine missing-authority behavior on the same retained fixture.
        verdicts={}
        from legalmath.interpretation.assurance.phased.controls import control_answers
        for label,answer in control_answers(records,mutation=mutation,missing=missing):
            reviews=product.audit_answer('p14',question,answer,[],prefix=label+'-')
            verdicts[label]=reviews
        good=verdicts['supported'];bad=verdicts['unsupported']
        passed=(bool(good) and all(r['status']=='VALIDATED' and r['value']['verdict']=='ACCEPT' for r in good)
            and any(r['status']=='VALIDATED' and r['value']['verdict'] in ('REJECT','UNRESOLVED') for r in bad))
        context_control = None
        if name == 'remote-exception':
            from legalmath.interpretation.assurance.phased.context_bridge import review
            item={'id':'control-remote','question_id':'p14','origin_id':records[0]['id'],
                'dependency':'Read the distant court-order exception jointly with the reconciliation duty.'}
            initial={'status':'VALIDATED','value':{'verdict':'UNRESOLVED','considered':[item['id']],
                'reason':'The distant exception has not been delivered in this initial control.',
                'support':[],'issues':[],'source_gaps':[],'assertion_bindings':[]}}
            context_control=review(product,'p14',question,
                {'conclusion':'DUTY_REQUIRED: Reconciliation mismatch always requires blocking.'},
                item,initial,[{'kind':'SOURCE_TEXT','record_ids':[records[-1]['id']]}],
                prefix='control-',admit=phase_admit('qualification-'+name))
            passed = passed and context_control['result'].get('status')=='VALIDATED' and \
                context_control['result']['value']['verdict']=='REJECT'
        rows.append({'case':name,'passed':passed,'reviews':verdicts,'context_control':context_control})
        save_exact(ROOT/LIVE/'qualification/result.json',{'rows':rows,'qualified':False,'complete':False})
    qualified=all(r['passed'] for r in rows)
    result={'rows':rows,'qualified':qualified,'complete':True,'scope':'Scoped grouped-review controls; not general legal accuracy'}
    save_exact(ROOT/LIVE/'qualification/result.json',result)
    return {'qualification':ref(ROOT,LIVE/'qualification/result.json'),
        '_node_status':'SUCCEEDED' if qualified else 'BLOCKED',
        '_conclusion':'Grouped review controls '+('passed.' if qualified else 'remain unqualified; independent source recovery may continue.')}


def acquisition(service):
    from legalmath.interpretation.assurance.phased.acquisition import recover
    campaign=configure()
    folder=ROOT/LIVE/'acquisition'
    path=folder/'investigation.json'
    if path.exists():
        return load_exact(path)
    failure=folder/'shared-failure.json'
    if failure.exists():
        raise LegalMathError('E_DEPENDENCY',details=read(failure)['reason'])
    folder.mkdir(parents=True,exist_ok=True)
    save(folder/'shared-operation.json',{'status':'RUNNING','owners':['acquire-'+q for q in QUESTIONS],
        'started_at_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()})
    try:
        prior=load_exact(ROOT/PREVIOUS_WORK/'settled-acquisition/reconstruction/investigation.json')
        product=BoundedProduct(ROOT,folder,service,read(ROOT/campaign.ENVELOPE),tokenizer(ROOT/TOKENIZER),
            limits=Limits(),maximum_calls=60,
            common_capacity_profile=read(ROOT/PROGRAM).get('common_capacity', {}).get('capacity_profile'))
        result=recover(product,prior,admit=phase_admit('acquisition'),
            implementation_identity=ref(ROOT,BASE/'current-binding.json')['sha256'])
        save(folder/'shared-operation.json',{'status':'SETTLED',
            'owners':['acquire-'+q for q in QUESTIONS],'result':ref(ROOT,path),
            'question_acquisition_complete':result['question_acquisition_complete']})
        return result
    except Exception as exc:
        save(failure,{'status':'FAILED','error':getattr(exc,'code',type(exc).__name__),
            'reason':str(getattr(exc,'details',None) or exc),'owners':['acquire-'+q for q in QUESTIONS]})
        raise


def product_route(q,tool,service,*,preparation_only=False,recovery_context=None):
    from scripts.legal_product_completion import run_product
    from legalmath.interpretation.assurance.bounded_product import PROFILE
    campaign=configure()
    value=read(ROOT/campaign.ENVELOPE)
    program=read(ROOT/PROGRAM)
    revision=(program.get('repair_execution') or program.get('complete_account_capacity_repair') or program.get('account_reconstruction_repair') or program.get('account_instruction_repair') or program.get('lossless_account_repair')
        or program.get('account_capacity_repair'))
    route_live=active_live(program)
    options={}
    if revision:
        from legalmath.interpretation.assurance.phased import account_contract, account_input
        options={'bounded_requirement_account_profile':account_contract.PROFILE,
            'bounded_requirement_account_input_profile':account_input.PROFILE,
            'bounded_requirement_account_recovery':revision['recoveries'][q]}
        if program.get('account_instruction_repair'):
            from legalmath.interpretation.assurance.phased.account_instructions import PROFILE as INSTRUCTION_PROFILE
            options['bounded_requirement_account_instruction_profile'] = INSTRUCTION_PROFILE
        if program.get('repair_execution') or (program.get('complete_account_capacity_repair') and q in revision['failed_questions']):
            options['bounded_requirement_account_capacity_profile'] = account_input.CAPACITY_PROFILE
            from legalmath.interpretation.assurance.phased.account_output import PROFILE as OUTPUT_PROFILE
            options['bounded_requirement_account_output_profile'] = OUTPUT_PROFILE
        if program.get('repair_execution'):
            options['bounded_downstream_input_profile'] = revision['downstream_input_profile']
            if revision.get('downstream_instruction_profile'):
                options['bounded_downstream_instruction_profile'] = revision['downstream_instruction_profile']
            if q in revision.get('synthesis_successors', {}):
                options['retained_initial'] = revision['synthesis_successors'][q]
        if program.get('lossless_account_repair'):
            from legalmath.interpretation.assurance.phased import account_encoding
            options['bounded_requirement_account_input_profile'] = account_encoding.PROFILE
    if q in program.get('settled_recovery', {}).get('recoveries', {}):
        options['bounded_requirement_account_recovery'] = program['settled_recovery']['recoveries'][q]
        options.pop('retained_initial', None)
    common=common_directory(program,q)
    route_live=question_live(program,q)
    admission=phase_admit('prepare-'+q if preparation_only else q+'-'+(tool or 'baseline'))
    if program.get('failure_recovery') and q=='p10' and not program.get('synthesis_resolution'):
        if recovery_context is None:
            if program.get('synthesis_continuation'):
                from scripts.legal_integration_synthesis_continuation import completion
            elif program.get('gap_preservation'):
                from scripts.legal_integration_gap_preservation import completion
            else:
                from scripts.legal_integration_failure_recovery import completion
            done=completion()
            require(done is not None, 'P10 requires completed recovery or explicit active repair pass')
            options['bounded_requirement_account_recovery']=done['recovery']
        else:
            require(preparation_only and tool is None,'Repair context is preparation-only')
            options['bounded_requirement_account_recovery']=recovery_context['recovery']
            common=Path(recovery_context['common_directory'])
            admission=lambda name,count:admit(ROOT,BASE,Path(recovery_context['phase_directory']),name,count,owner='prepare-'+q)
        options.pop('retained_initial',None)
    if q in program.get('synthesis_resolution', {}).get('recoveries', {}):
        resolved = program['synthesis_resolution']
        options.update(bounded_requirement_account_recovery=resolved['recoveries'][q],
            retained_initial=resolved['successors'][q],
            bounded_downstream_capacity_profile=resolved['downstream_capacity_profile'])
        if recovery_context is not None:
            require(preparation_only and tool is None, 'Resolution context is preparation-only')
            common = Path(recovery_context['common_directory'])
            admission = lambda name,count:admit(ROOT,BASE,Path(recovery_context['phase_directory']),name,count,owner='prepare-'+q)
    if q in program.get('candidate_capacity_retry', {}).get('checkpoints', {}):
        require(recovery_context is None, 'Completed preparation has no mutable recovery context')
        options.pop('retained_initial', None)
        options.pop('bounded_requirement_account_recovery', None)
        options['bounded_retained_preparation'] = program['candidate_capacity_retry']['checkpoints'][q]
    if program.get('common_capacity'):
        options['bounded_common_capacity_profile'] = program['common_capacity']['capacity_profile']
        options['bounded_capacity_checkpoint'] = program['common_capacity']['checkpoints'][q]
        if not preparation_only:
            options['bounded_capacity_checkpoint'] = program['common_capacity']['arm_checkpoints'].get(q, {}).get(
                tool or 'baseline', options['bounded_capacity_checkpoint'])
    if program.get('review_repair'):
        repaired = program['review_repair']
        options['bounded_review_repair_profile'] = repaired['review_profile']
        options['bounded_review_assignment_profile'] = repaired.get('review_assignment_profile')
        options['bounded_service_prerequisite_profile'] = repaired.get('service_prerequisite_profile')
        options['bounded_capacity_checkpoint'] = repaired['checkpoints'][q]
        if not preparation_only:
            options['bounded_capacity_checkpoint'] = repaired['arm_checkpoints'].get(q, {}).get(
                tool or 'baseline', options['bounded_capacity_checkpoint'])
            if repaired.get('deployment'):
                options['bounded_capacity_checkpoint'] = repaired['deployment']['arm_checkpoints'].get(q, {}).get(
                    tool or 'baseline', options['bounded_capacity_checkpoint'])
            if repaired.get('optional_quote_validation'):
                options['bounded_capacity_checkpoint'] = repaired['optional_quote_validation']['arm_checkpoints'].get(q, {}).get(
                    tool or 'baseline', options['bounded_capacity_checkpoint'])
    if program.get('window_continuation') and not preparation_only:
        options['bounded_capacity_checkpoint'] = program['window_continuation']['arm_checkpoints'].get(q, {}).get(
            tool or 'baseline', options['bounded_capacity_checkpoint'])
    if program.get('repaired_retry_continuation') and not preparation_only:
        options['bounded_capacity_checkpoint'] = program['repaired_retry_continuation']['arm_checkpoints'].get(q, {}).get(
            tool or 'baseline', options['bounded_capacity_checkpoint'])
    if program.get('baseline_corpus_repair') and not preparation_only:
        repair = program['baseline_corpus_repair']
        require(repair.get('profile') == 'reviewed-baseline-corpus-repair.v1',
            'Unknown baseline/corpus repair selection')
        options.update(bounded_context_reference_profile=repair['context_reference_profile'],
            bounded_warrant_reference_profile=repair['warrant_reference_profile'],
            bounded_correction_input_profile=repair['correction_input_profile'])
    if program.get('product_closure') and not preparation_only:
        options['bounded_capacity_checkpoint']=program['product_closure'].get('arm_checkpoints',{}).get(q,{}).get(
            tool or 'baseline',options.get('bounded_capacity_checkpoint'))
    runtime = program.get('product_closure', {}).get('runtime', {})
    if runtime:
        options['bounded_review_budget_yield_profile'] = runtime['review_budget_yield_profile']
    directory=ROOT/common if preparation_only else ROOT/route_live/'arms'/q/(tool or 'baseline')
    shared=None if preparation_only else ROOT/common/'calls'
    return run_product(ROOT,directory,service,ROOT/'jdk','2026-10-15T00:00:00+08:00',
        sources=[],questions=value['original_questions'],acceptance_ref=None,qualification={},
        required={'maximum_calls':8100,'maximum_corrections':1},
        deadline_utc=campaign.effective_deadline(),
        selected_tools=[] if tool is None else [tool],settings=None,consumer_profile=PROFILE,
        bounded_envelope=value,bounded_encode=tokenizer(ROOT/TOKENIZER),bounded_limits=Limits(),
        active_questions=[q],shared_prefix=shared,
        bounded_phase='prepare' if preparation_only else 'answer',bounded_execution='phased',
        bounded_acquisition_ref=ref(ROOT,LIVE/'acquisition/investigation.json'),
        bounded_phase_admit=admission,
        bounded_phase_identity=program.get('product_closure',{}).get('phase_identity',
            ref(ROOT,BASE/'current-binding.json')['sha256']),**options)


def acquire(q,service):
    if read(ROOT/PROGRAM).get('common_capacity'):
        from scripts.legal_integration_common_capacity import acquire as common_acquire
        return common_acquire(q, service)
    if q in read(ROOT/PROGRAM).get('candidate_capacity_retry', {}).get('checkpoints', {}):
        from scripts.legal_integration_candidate_retry import acquire as retry_candidates
        return retry_candidates(q,service)
    if q in read(ROOT/PROGRAM).get('synthesis_resolution', {}).get('recoveries', {}):
        from scripts.legal_integration_synthesis_resolution import acquire as resolve_synthesis
        return resolve_synthesis(q,service)
    if q=='p10' and read(ROOT/PROGRAM).get('synthesis_continuation'):
        from scripts.legal_integration_synthesis_continuation import acquire as continue_synthesis
        return continue_synthesis(q,service)
    if q=='p10' and read(ROOT/PROGRAM).get('gap_preservation'):
        from scripts.legal_integration_gap_preservation import acquire as recover_failed
        return recover_failed(q,service)
    if q=='p10' and read(ROOT/PROGRAM).get('failure_recovery'):
        from scripts.legal_integration_failure_recovery import acquire as recover_failed
        return recover_failed(q,service)
    investigation=acquisition(service)
    require(investigation['question_acquisition_complete'][q],'Source recovery failed for '+q)
    result=product_route(q,None,service,preparation_only=True)
    require(result['answers'][q].get('status')=='PREPARED','Common preparation failed for '+q)
    common=common_directory(read(ROOT/PROGRAM),q)
    save(ROOT/common/'downstream-budget.json',{'question':q,'maximum_calls_each_arm':8100,
        'admission':'Each actual phase only; original global grant checked before every wire call.',
        'preparation':ref(ROOT,common/'result.json')})
    return {'question':q,'preparation':ref(ROOT,common/'result.json'),
            'acquisition':ref(ROOT,LIVE/'acquisition/investigation.json')}


def answer(q,tool,service):
    from scripts.legal_independent_tools import IndependentProductToolBackend
    campaign=configure()
    require(tool is None or tool in campaign.eligible_tools(q),'Tool lacks reviewed applicability')
    folder=ROOT/question_live(read(ROOT/PROGRAM),q)/'arms'/q/(tool or 'baseline')
    outcome=product_route(q,tool,service)
    row=outcome['answers'][q]
    require(row.get('answer',{}).get('status')=='VALIDATED','Product answer failed for '+q)
    return {'question':q,'tool':tool,'product':ref(ROOT,folder/'result.json'),
        'review_accepted':row['review_accepted'],
        '_node_status':'SUCCEEDED' if tool is not None or row['review_accepted'] else 'FAILED',
        '_conclusion':'Actual product answer retained; '+('review accepted.' if row['review_accepted'] else 'review remains open.') }


def defer_open_service(execution, tid):
    """A known outage is an unmet prerequisite, not an owner attempt."""
    from legalmath.interpretation.assurance.integration_contract import read_evidence
    view = execution.summary()
    if tid not in view['ready'] and not (
            execution.program.get('review_repair', {}).get('timeout_correction') and tid in view['running']):
        return False  # A reserved owner must follow its existing recovery path.
    binding = read(ROOT / BASE / 'current-binding.json')
    scope = binding.get('phase_service_scope')
    if not scope:
        return False
    read_evidence(scope, ROOT)
    path = ROOT / Path(scope['path']).parent / 'service-circuit.json'
    if not path.exists():
        return False
    circuit = read(path)
    require(circuit.get('stage_hash') == scope['sha256'], 'Changed shared service circuit identity')
    if not circuit.get('open'):
        return False
    # Freeze the observed prerequisite; later service evidence may legitimately
    # evolve, while this non-dispatch decision must remain independently auditable.
    directory = ROOT / active_live(execution.program) / 'deferred-service' / tid
    save(directory / 'circuit.json', circuit)
    reason = 'Deferred before owner reservation: shared service circuit is open; reviewed requalification required.'
    evidence = [scope, ref(ROOT, directory / 'circuit.json')]
    if execution.program.get('review_repair'):
        affected = [node for node in view['ready'] if node.startswith(('acquire-', 'baseline-', 'tool-', 'compare-'))
            or node in ('semantic-preflight', 'account-qualification')]
        if affected:
            execution.block_before_dispatch_many(affected, reason, evidence, shared_scope=['provider-service'])
    else:
        execution.block_before_dispatch(tid, reason, evidence, shared_scope=['provider-service'])
    try:
        execution.sync_mission()
    except __import__('subprocess').TimeoutExpired as exc:
        # The deferral is durable. A refresh timeout must not prevent the
        # remaining independent owners from recording their own deferrals.
        # Authority/integrity failures are deliberately not caught here.
        with execution.locked() as state:
            state['mission_sync_error'] = str(exc)
            execution.event(state, tid, 'MISSION_SYNC_FAILED', reason=str(exc))
    return True


def drain_answers(execution, campaign, service, *, maximum_nodes=None, yield_to_acquisitions=False):
    """Run ready consumers without waiting for another question's acquisition."""
    require(maximum_nodes is None or (type(maximum_nodes) is int and maximum_nodes > 0),
        'Invalid answer scheduling bound')
    completed = 0
    while True:
        view=execution.summary()
        if yield_to_acquisitions and any(t.startswith('acquire-') for t in view['ready']):
            return
        if maximum_nodes is not None and completed >= maximum_nodes:
            return
        ready=[t for t in view['ready']+view['running'] if t.startswith(('baseline-','tool-','compare-'))]
        if not ready:
            return
        tid=ready[0]
        if defer_open_service(execution, tid):
            if execution.program.get('review_repair', {}).get('timeout_correction'):
                return  # Shared deferral yields to counted recovery; retained owners are not dispatched.
            continue
        if tid.startswith('compare-'):
            q,tool=tid[8:].split('-',1)
            def action(q=q,tool=tool):
                if not execution.program.get('common_capacity'):
                    phase_admit('compare-'+q+'-'+tool)('effect',6)
                configure(q)
                return campaign.compare(q,tool,service)
        else:
            if tid.startswith('baseline-'):
                q,tool=tid[9:],None
            else:
                q,tool=tid[5:].split('-',1)
            action=lambda q=q,tool=tool:answer(q,tool,service)
        outcome = campaign.complete_node(execution,tid,action)
        completed += 1
        if isinstance(outcome, dict) and outcome.get('service_deferred'):
            return  # Existing owner retained; yield to checked service recovery.


def live():
    campaign=configure();execution=MasterExecution(ROOT,PROGRAM,STATE)
    (ROOT/LIVE).mkdir(parents=True,exist_ok=True)
    with (ROOT/LIVE/'supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        service=campaign.provider();service.check()
        view=execution.summary()
        if 'semantic-preflight' in view['ready']+view['running'] and not defer_open_service(execution, 'semantic-preflight'):
            campaign.complete_node(execution,'semantic-preflight',lambda:qualification(service))
        view=execution.summary()
        if 'account-qualification' in view['ready']+view['running'] and not defer_open_service(execution, 'account-qualification'):
            if execution.program.get('complete_account_capacity_repair'):
                from scripts.legal_integration_complete_account_capacity import qualify_accounts
            elif execution.program.get('account_instruction_repair'):
                from scripts.legal_integration_account_instruction_repair import qualify_accounts
            elif execution.program.get('qualification_continuation'):
                from scripts.legal_integration_qualification_continuation import qualify_accounts
            else:
                from scripts.legal_integration_account_controls import qualify_accounts
            campaign.complete_node(execution,'account-qualification',lambda:qualify_accounts(service))
        # Own source canaries and old full semantic controls remain retained.
        # New grouped-review failure does not cancel source-only preparation.
        order=QUESTIONS
        current_program=read(ROOT/PROGRAM)
        fairness = current_program.get(FAIRNESS_FIELD)
        require(fairness in (None, FAIRNESS_PROFILE), 'Unknown acquisition fairness profile')
        account_revision=(current_program.get('repair_execution') or current_program.get('complete_account_capacity_repair') or current_program.get('account_reconstruction_repair') or current_program.get('account_instruction_repair')
            or current_program.get('lossless_account_repair') or current_program.get('account_capacity_repair'))
        if account_revision:
            recoveries = {**account_revision['recoveries'], **current_program.get('settled_recovery', {}).get('recoveries', {})}
            order=sorted(QUESTIONS,key=lambda q:len(read(ROOT/recoveries[q]['path'])['account_recovery']['roots']))
            if account_revision.get('service_continuation'):
                first = account_revision['service_continuation']['question']
                order = [first] + [q for q in order if q != first]
        for q in order:
            view=execution.summary();tid='acquire-'+q
            if tid in view['ready']+view['running'] and not defer_open_service(execution, tid):
                campaign.complete_node(execution,tid,lambda q=q:acquire(q,service))
            if current_program.get('settled_recovery'):
                if fairness is not None:
                    drain_answers(execution,campaign,service,maximum_nodes=1,yield_to_acquisitions=True)
                else:
                    drain_answers(execution, campaign, service)
        drain_answers(execution, campaign, service)
        return execution.summary()
