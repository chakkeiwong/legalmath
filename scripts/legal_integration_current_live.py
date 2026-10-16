"""Current bounded preflight and question stages under the unchanged grant."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import hashlib
import math

from scripts.legal_integration_master import ROOT, BASE, PROGRAM, STATE, PLAN, TOKENIZER, QUESTIONS, MasterExecution
from scripts.legal_integration_execution_refresh import WORK, REVIEW, USER
from scripts.legal_integration_accounts import SOURCE
from scripts.legal_mission_execution import read, save, ref, verify, require
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundedProduct, AUDIT
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider

LIVE=WORK/'live'


def current_scope():
    canary_repair = read(ROOT/PROGRAM).get('canary_validation_repair')
    if canary_repair:
        from scripts.legal_integration_canary_validation import WORK as CANARY_WORK, REVIEW as CANARY_REVIEW
        return CANARY_WORK/'live', CANARY_REVIEW, 256, canary_repair['semantic_stage_maximum'], 1
    delay_repair = read(ROOT/PROGRAM).get('retry_delay_repair')
    if delay_repair:
        from scripts.legal_integration_service_continuation import DELAY_WORK, DELAY_REVIEW
        return DELAY_WORK/'live', DELAY_REVIEW, 256, delay_repair['semantic_stage_maximum'], 1
    if read(ROOT/PROGRAM).get('service_continuation'):
        from scripts.legal_integration_service_continuation import WORK as CONTINUATION_WORK,REVIEW as CONTINUATION_REVIEW,STAGE_CALLS
        return CONTINUATION_WORK/'live',CONTINUATION_REVIEW,256,STAGE_CALLS,1
    if read(ROOT/PROGRAM).get('execution_recovery'):
        from scripts.legal_integration_prerequisites import RECOVERY_WORK,RECOVERY_REVIEW,RECOVERY_STAGE_CALLS,CASE_CALLS
        return RECOVERY_WORK/'live',RECOVERY_REVIEW,CASE_CALLS,RECOVERY_STAGE_CALLS,1
    if read(ROOT/PROGRAM).get('prerequisite_repair'):
        from scripts.legal_integration_prerequisites import (
            WORK as PREREQUISITE_WORK, REVIEW as PREREQUISITE_REVIEW,
            CASE_CALLS, STAGE_CALLS,
        )
        return PREREQUISITE_WORK/'live', PREREQUISITE_REVIEW, CASE_CALLS, STAGE_CALLS, 1
    repair=read(ROOT/PROGRAM)['execution_refresh'].get('post_review')
    if repair:
        from scripts.legal_integration_execution_repair import WORK as REPAIR, REVIEW as REPAIR_REVIEW, SEMANTIC_CASE_CALLS, SEMANTIC_STAGE_CALLS
        if repair.get('response_repair'):
            if repair['response_repair'].get('account_correction'):
                return REPAIR/'response-repair/account-correction/live',REPAIR/'response-repair/account-correction-review.md',SEMANTIC_CASE_CALLS,SEMANTIC_STAGE_CALLS,1
            return REPAIR/'response-repair/live',REPAIR/'response-review-repair.md',SEMANTIC_CASE_CALLS,SEMANTIC_STAGE_CALLS,1
        return REPAIR/'live',REPAIR_REVIEW,SEMANTIC_CASE_CALLS,SEMANTIC_STAGE_CALLS,1
    return WORK/'live',REVIEW,62,128,0


def configure_scope():
    global LIVE, SOURCE
    if read(ROOT/PROGRAM).get('prerequisite_repair'):
        SOURCE = Path(read(ROOT/PROGRAM)['prerequisite_repair']['source']['path'])
    LIVE,review,case_calls,stage_calls,corrections=current_scope()
    return review,case_calls,stage_calls,corrections


def historical_archives():
    documents=[]
    canary_repair = read(ROOT/PROGRAM).get('canary_validation_repair')
    if canary_repair:
        documents.append(read(ROOT/canary_repair['prior_binding']['path']))
    delay_repair = read(ROOT/PROGRAM).get('retry_delay_repair')
    if delay_repair:
        documents.append(read(ROOT/delay_repair['prior_binding']['path']))
    continuation = read(ROOT/PROGRAM).get('service_continuation')
    if continuation:
        documents.append(read(ROOT/continuation['prior_binding']['path']))
    recovery = read(ROOT/PROGRAM).get('execution_recovery')
    if recovery:
        documents.append(read(ROOT/recovery['prior_binding']['path']))
    prerequisites = read(ROOT/PROGRAM).get('prerequisite_repair')
    if prerequisites:
        documents.append(read(ROOT/prerequisites['prior_binding']['path']))
    grant=read(ROOT/BASE/'live-grant.json')
    documents.append(read(ROOT/grant['proposal']['path']))
    for name in ('recovery-approval.json','reopening-binding.json','reopening-verification-correction.json'):
        path=ROOT/BASE/name
        if path.exists():
            doc=read(path); documents.append(doc)
            if doc.get('proposal'):documents.append(read(ROOT/doc['proposal']['path']))
    repair=read(ROOT/PROGRAM).get('execution_refresh',{}).get('post_review')
    if repair:
        documents.append(read(ROOT/repair['prior_binding']['path']))
        if repair.get('binding_fix'):
            documents.append(read(ROOT/repair['binding_fix']['prior_binding']['path']))
        if repair.get('response_repair'):
            documents.append(read(ROOT/repair['response_repair']['prior_binding']['path']))
            account = repair['response_repair'].get('account_correction')
            if account:
                documents.append(read(ROOT/account['prior_binding']['path']))
    references={}
    def walk(value):
        if isinstance(value,dict):
            if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):
                references[value['path'],value['sha256']]=value
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
    for doc in documents:walk(doc)
    missing={key:reference for key,reference in references.items() if not (ROOT/reference['path']).exists()
             or ref(ROOT,reference['path'])!=reference}
    wanted={Path(path).name for path,sha in missing}
    candidates={}
    # Read only candidates with a relevant filename, then require exact byte
    # identity. Existing historical binding files and grants are never edited.
    for path in (ROOT/'artifacts/legal-mission-control').rglob('*'):
        if path.is_file() and path.name in wanted:
            value=ref(ROOT,path);candidates.setdefault((path.name,value['sha256']),value)
    rows=[]
    for (path,sha),previous in sorted(missing.items()):
        archive=candidates.get((Path(path).name,sha))
        require(archive is not None,'Missing exact historical archive: '+path+' '+sha)
        rows.append({'previous':previous,'archive':archive})
    return rows


def prepare(directory):
    review,case_calls,stage_calls,corrections=configure_scope()
    grant=read(ROOT/BASE/'live-grant.json');ledger=read(ROOT/BASE/'live-calls.json')
    limits=Limits();encode=tokenizer(ROOT/TOKENIZER)
    service=BoundedCodexProvider(ROOT,ROOT/BASE,encode,limits,routing_file=ROOT/BASE/'campaign-routing.toml')
    envelope=read(ROOT/SOURCE)
    dry=BoundedProduct(ROOT,directory/'requests',service,envelope,encode,limits=limits,
                       maximum_corrections=corrections)
    packets,blocked=dry.reading_packets()
    require(not blocked,'Current source packet construction blocked')
    measurements=[dry.dispatch.measure(p['request'],p['schema']) for p in packets]
    canaries=[]
    for question in envelope['original_questions']:
        q=question['question_id'];ids=dry.route.retrieve(question['text'],expand=False)['record_ids'][:2]
        packet=dry.route.make_packet('READ_SOURCE',ids,question_ids=[q],reader='service-canary')
        request=dry.request('AUDIT_ANSWER_AGAINST_SOURCE',question,[dry.route.records[i] for i in ids],
            payload={'conclusion':'A recorded action alone conclusively establishes full compliance; no further standard, contrary passage or fact matters.',
                     'control':'Deliberately unsupported overstatement.'},expected=ids)
        save(ROOT/LIVE/'canary-inputs'/(q+'.json'),{'reading':packet,'review_request':request,
            'review_schema':AUDIT,'measurements':[dry.dispatch.measure(packet['request'],packet['schema']),dry.dispatch.measure(request,AUDIT)]})
        canaries.append(ref(ROOT,LIVE/'canary-inputs'/(q+'.json')))
    resources={'scope':{'semantic_preflight':stage_calls,'canaries':8,
                        'acquisition':len(packets)+len(QUESTIONS)*limits.dependency_requests},
        'semantic_case_calls':case_calls,'maximum_corrections':corrections,
        'acquisition_reading_calls':len(packets),
        'acquisition_dependency_reserve':len(QUESTIONS)*limits.dependency_requests,
        'stage_budgeting':'Actual generated demand and correction reserves are admitted before each question/answer stage; no all-arm completion promise.',
        'measurements':measurements,'limits':asdict(limits),'canaries':canaries}
    save(directory/'resources.json',resources);save(directory/'ledger-before.json',ledger)
    bindings=[ref(ROOT,p) for p in sorted((ROOT/'src/legalmath').rglob('*.py'))]
    bindings += [ref(ROOT,p) for p in sorted((ROOT/'scripts').glob('legal_*.py'))]
    bindings += [ref(ROOT,p) for p in (PROGRAM,PLAN,review,SOURCE,BASE/'campaign-routing.toml',
                                       Path('requirements-context.lock'),Path('pyproject.toml'))]
    bindings += [ref(ROOT,directory/'resources.json'),*canaries]
    binding={'profile':'integration-current-binding.v1','user_instruction':USER,'review':ref(ROOT,review),
        'grant_hash':digest(grant),'maximum_calls':grant['maximum_calls'],'deadline_utc':grant['deadline_utc'],
        'routing_hash':digest(service.routing),'source':ref(ROOT,SOURCE),'bindings':bindings,
        'historical_archives':historical_archives(),'ledger_before':ref(ROOT,directory/'ledger-before.json'),
        'resources':ref(ROOT,directory/'resources.json'), 'program':ref(ROOT,PROGRAM),
        'preflight_stage_maximum':stage_calls,'acquisition_requires':'semantic-preflight success plus own question canary',
        'all_arms_admitted':False}
    target=ROOT/BASE/'current-binding.json'
    repair=read(ROOT/PROGRAM)['execution_refresh'].get('post_review')
    if repair:
        fix=repair.get('binding_fix')
        response=repair.get('response_repair')
        account=response.get('account_correction') if response else None
        predecessor=response['prior_binding'] if response else fix['prior_binding'] if fix else repair['prior_binding']
        if account: predecessor=account['prior_binding']
        binding['predecessor']=predecessor
        binding['bindings'].append(repair['prior_binding'])
        if fix: binding['bindings'].append(predecessor)
        code_baseline=read(ROOT/WORK/'post-review/code-baseline.json')
        binding['bindings'].append(ref(ROOT,WORK/'post-review/code-baseline.json'))
        for row in code_baseline['archived']:
            require(row['previous']['sha256']==row['archive']['sha256'],
                    'Repaired code archive changed historical bytes')
            verify(ROOT,row['archive'])
        binding['historical_archives'] += code_baseline['archived']
        if fix:
            binding['bindings'] += [fix['review'],fix['baseline']]
            binding['historical_archives'] += read(ROOT/fix['baseline']['path'])['archived']
        if response:
            binding['bindings'] += [response['review'],response['baseline'],response['local_review'],response['prior_binding']]
            binding['historical_archives'] += read(ROOT/response['baseline']['path'])['archived']
        if account:
            binding['bindings'] += [account[k] for k in ('review','baseline','local_review','prior_binding','checkpoints','prior_terminal_recovery')]
            binding['historical_archives'] += read(ROOT/account['baseline']['path'])['archived']
            if not read(ROOT/PROGRAM).get('prerequisite_repair'):
                binding['retained_initial'] = account['checkpoints']
            for arms in read(ROOT/account['checkpoints']['path']).values():
                for reference in arms.values():
                    binding['bindings'].append(reference)
                    manifest=read(ROOT/reference['path'])
                    binding['bindings'].append(manifest['dispatch'])
                    for row in manifest['calls'].values():
                        binding['bindings'] += list(row.values())
        prerequisites = read(ROOT/PROGRAM).get('prerequisite_repair')
        if prerequisites:
            binding['predecessor'] = prerequisites['prior_binding']
            binding['bindings'] += [prerequisites[k] for k in ('review','baseline','local_review','prior_binding','source')]
            binding['historical_archives'] += read(ROOT/prerequisites['baseline']['path'])['archived']
            binding['terminal_recovery_policy'] = prerequisites['terminal_recovery_policy']
            binding['scope_controls'] = True
        recovery = (read(ROOT/PROGRAM).get('canary_validation_repair') or
            read(ROOT/PROGRAM).get('retry_delay_repair') or
            read(ROOT/PROGRAM).get('service_continuation') or read(ROOT/PROGRAM).get('execution_recovery'))
        if recovery:
            binding['predecessor'] = recovery['prior_binding']
            binding['user_instruction'] = recovery['user_instruction']
            binding['bindings'] += [recovery[k] for k in ('review','baseline','local_review','prior_binding','checkpoints')]
            binding['historical_archives'] += read(ROOT/recovery['baseline']['path'])['archived']
            binding['service_recovery_policy'] = recovery['service_recovery_policy']
            binding['retained_initial'] = recovery['checkpoints']
            if recovery.get('canaries'):
                binding['bindings'].append(recovery['canaries'])
            for arms in read(ROOT/recovery['checkpoints']['path']).values():
                for reference in arms.values():
                    binding['bindings'].append(reference)
                    manifest = read(ROOT/reference['path'])
                    binding['bindings'].append(manifest['dispatch'])
                    for row in manifest['calls'].values():binding['bindings'] += list(row.values())
                    for row in manifest.get('recoverable_failures', {}).values():
                        binding['bindings'] += [row['result'],*row['receipts']]
        unique_archives = {}
        for row in binding['historical_archives']:
            unique_archives[(row['previous']['path'],row['previous']['sha256'])] = row
        binding['historical_archives'] = list(unique_archives.values())
    if target.exists() and read(target)!=binding:
        latest=repair.get('response_repair',repair.get('binding_fix',repair)) if repair else None
        latest=latest.get('account_correction',latest) if latest else None
        latest=read(ROOT/PROGRAM).get('prerequisite_repair',latest)
        latest=read(ROOT/PROGRAM).get('execution_recovery',latest)
        latest=read(ROOT/PROGRAM).get('service_continuation',latest)
        latest=read(ROOT/PROGRAM).get('retry_delay_repair',latest)
        latest=read(ROOT/PROGRAM).get('canary_validation_repair',latest)
        predecessor=latest['prior_binding'] if latest else None
        require(predecessor and ref(ROOT,target)['sha256']==predecessor['sha256'],
                'Current binding already exists without the reviewed replacement baseline')
        verify(ROOT,predecessor)
    save(target,binding)
    try:
        service.check()
    except Exception:
        # Preserve the rejected binding; do not fall back to a historical live
        # route or mutate it into success. A repair needs a reviewed binding.
        raise
    return {'binding':ref(ROOT,target),'resources':binding['resources'],
        'dispatch_ready':True,'scope':'CURRENT_PREFLIGHT_ONLY',
        '_conclusion':'Current implementation/source/provider and historical archives verify under unchanged grant; semantic stage may execute, acquisition remains gated.'}


def admit_stage(name,maximum):
    review,_,_,_=configure_scope()
    binding=read(ROOT/BASE/'current-binding.json');grant=read(ROOT/BASE/'live-grant.json')
    policy = binding.get('service_recovery_policy')
    if policy and name != 'semantic-preflight':
        maximum += policy['maximum_replacements']
    directory=ROOT/LIVE/'stages'/name
    path=directory/'stage.json'
    if path.exists():
        stage=read(path)
        require(stage['maximum_calls']==maximum and stage['binding_hash']==digest(binding),'Stage resume identity changed')
    else:
        ledger=read(ROOT/BASE/'live-calls.json')
        require(0<maximum<=grant['maximum_calls']-len(ledger['calls']),'Insufficient remaining calls for stage')
        remaining=(datetime.fromisoformat(grant['deadline_utc'])-datetime.now(timezone.utc)).total_seconds()
        timeout = policy['timeout_seconds'] if policy else 120
        backoff = (policy['maximum_replacements']*(max(max(policy['backoff_seconds']),
            policy.get('maximum_retry_after_seconds',0))+policy.get('jitter_seconds',0)) if policy else 0)
        require(maximum*timeout+backoff+305<=remaining,'Insufficient original window for conservative serial stage bound')
        save(directory/'ledger-before.json',ledger)
        stage={'profile':'integration-current-stage.v1','name':name,'maximum_calls':maximum,
            'grant_hash':digest(grant),'binding_hash':digest(binding),'ledger_before':ref(ROOT,directory/'ledger-before.json'),
            'deadline_utc':grant['deadline_utc'],'review':ref(ROOT,review)}
        if name == 'semantic-preflight' and read(ROOT/PROGRAM)['execution_refresh'].get('post_review',{}).get('response_repair'):
            response=read(ROOT/PROGRAM)['execution_refresh']['post_review']['response_repair']
            account=response.get('account_correction')
            stage['terminal_recovery_maximum']=account['terminal_recovery_maximum'] if account else 2
            if account:
                stage['prior_terminal_recovery']=account['prior_terminal_recovery']
        prerequisites = read(ROOT/PROGRAM).get('prerequisite_repair')
        if name == 'semantic-preflight' and prerequisites:
            stage['terminal_recovery_policy'] = prerequisites['terminal_recovery_policy']
            stage['terminal_recovery_maximum'] = prerequisites['terminal_recovery_policy']['maximum_replacements']
        if policy:
            stage['service_recovery_policy'] = policy
            stage['service_recovery_maximum'] = policy['maximum_replacements']
        save(path,stage)
    save(ROOT/BASE/'current-stage.json',ref(ROOT,path))
    return stage


def activate():
    _,_,_,corrections=configure_scope()
    from scripts import legal_integration_campaign as campaign
    campaign.LIVE=LIVE;campaign.ENVELOPE=SOURCE
    campaign.CANARIES=LIVE/'canary-inputs'
    campaign.RESOURCES=Path(read(ROOT/BASE/'current-binding.json')['resources']['path'])
    campaign.LIMITS=Limits();campaign.COMMON_CAP=640
    campaign.ARM_BUFFER=32;campaign.SOURCE_REVIEW_GROUP_MINIMUM=1
    campaign.MAXIMUM_CORRECTIONS=corrections
    return campaign


def live():
    """Settle live owners, then drain ready local work even after a failed stage."""
    try:
        _live()
    finally:
        MasterExecution(ROOT,PROGRAM,STATE).run()
    return MasterExecution(ROOT,PROGRAM,STATE).summary()


def _live():
    if read(ROOT/PROGRAM).get('phased_acquisition_repair'):
        from scripts.legal_integration_phased_live import live
        return live()
    campaign=activate()
    execution=MasterExecution(ROOT,PROGRAM,STATE)
    (ROOT/LIVE).mkdir(parents=True,exist_ok=True)
    with (ROOT/LIVE/'supervisor.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        service=campaign.provider(); service.check()
        frontier=execution.summary()
        if 'semantic-preflight' in frontier['ready']+frontier['running']:
            _,_,case_calls,stage_calls,corrections=current_scope()
            admit_stage('semantic-preflight',stage_calls)
            def semantic():
                from scripts.legal_integration_reopening_live import semantic_control
                binding=read(ROOT/BASE/'current-binding.json')
                retained=read(ROOT/binding['retained_initial']['path']) if binding.get('retained_initial') else None
                value=semantic_control(service,directory=ROOT/LIVE/'semantic-control',limits=Limits(),
                    per_case_calls=case_calls,maximum_corrections=corrections,retained_initial=retained,
                    scope_controls=binding.get('scope_controls',False))
                return {'semantic':ref(ROOT,LIVE/'semantic-control/result.json'),
                    '_node_status':'SUCCEEDED' if value['qualified'] else 'BLOCKED',
                    '_conclusion':'Current remote/changed exception control '+('passed.' if value['qualified'] else 'did not qualify; retain stage failures, continue independent source/question work.')}
            campaign.complete_node(execution,'semantic-preflight',semantic)
        view=execution.summary()
        if view['tasks']['semantic-preflight']['status']!='SUCCEEDED':return view
        if 'live-approval' in view['ready']+view['running']:
            admit_stage('question-canaries',8)
            campaign.complete_node(execution,'live-approval',lambda:{
                'canaries':campaign.canaries(service),'binding':ref(ROOT,BASE/'current-binding.json'),
                '_conclusion':'Current semantic prerequisite and unchanged grant verified; own-question canaries gate each acquisition.'})
        frontier=execution.summary()
        ready=[t for t in frontier['ready']+frontier['running'] if t.startswith('acquire-')]
        if ready:
            outcomes=read(ROOT/LIVE/'canary-results.json')
            for tid in ready:
                if not outcomes[tid[8:]]['passed'] and tid in execution.summary()['ready']:
                    execution.block_before_dispatch(tid,'Own-question canary did not qualify.',[ref(ROOT,LIVE/'canary-results.json')])
            frontier=execution.summary()
            questions=[t[8:] for t in frontier['ready']+frontier['running'] if t.startswith('acquire-')]
            if questions:
                capacity=read(ROOT/campaign.RESOURCES)['scope']['acquisition']
                admit_stage('acquisition',capacity)
                campaign.product(ROOT/LIVE/'acquisition',service,phase='acquire',maximum=capacity,questions=questions)
                for q in questions:
                    def acquire(q=q):
                        admit_stage('prepare-'+q,640)
                        return campaign.acquire(q,service)
                    campaign.complete_node(execution,'acquire-'+q,acquire)
        # Drain all independent answer arms and comparisons; stage refusal is
        # retained for the affected owner rather than abandoning its siblings.
        while True:
            frontier=execution.summary()
            ready=[t for t in frontier['ready']+frontier['running'] if t.startswith(('baseline-','tool-','compare-'))]
            if not ready:break
            tid=ready[0]
            if tid.startswith('compare-'):
                q,tool=tid[8:].split('-',1);maximum=6;action=lambda:campaign.compare(q,tool,service)
            else:
                if tid.startswith('baseline-'):q=tid[9:];tool=None
                else:q,tool=tid[5:].split('-',1)
                budget=read(ROOT/LIVE/'common'/q/'downstream-budget.json')
                maximum=budget['maximum_calls_each_arm'];action=lambda:campaign.answer(q,tool,service)
            try:admit_stage(tid,maximum)
            except ValueError as exc:
                path=ROOT/LIVE/'stages'/tid/'refusal.json';save(path,{'reason':str(exc),'calls':len(read(ROOT/BASE/'live-calls.json')['calls'])})
                execution.block_before_dispatch(tid,str(exc),[ref(ROOT,path)])
                continue
            campaign.complete_node(execution,tid,action)
        return execution.summary()
