"""One reviewed amendment for settled evidence correction and P10 resumption."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN, MasterExecution
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, validate_program, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_phased_repair import archives
from scripts.legal_integration_repair_execution import project_retained_plan, validate_staged_mission

KEY = 'settled_recovery'
WORK = Path('artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery')
REVIEW = DOC / 'results/settled-gap-recovery-2026-10-17.md'
USER = 'refresh the masteer program to close these gaps.   review the program.  execute'
REOPEN = ['acquire-evidence', 'acquire-p10']
MUTATED = {str(PLAN), 'scripts/legal_integration_master.py', 'scripts/legal_integration_phased_live.py',
    'scripts/legal_mission_execution.py', 'scripts/legal_mission_control.py',
    'scripts/legal_integration_settled_recovery.py',
    'scripts/legal_integration_campaign.py',
    'src/legalmath/interpretation/assurance/phased/account_recovery.py',
    'src/legalmath/interpretation/assurance/phased/account_receipt.py'}

def projection(baseline, *, mission=False):
    allowed = MUTATED | ({str(PROGRAM)} if mission else set())
    return archives([r for r in baseline['archived'] if r['previous']['path'] in allowed], mission=mission)

def expected_program(old, revision, root, *, plan_reference=None):
    value = deepcopy(old)
    for task in value['tasks']:
        if task['id'] in REOPEN:
            task['maximum_attempts'] += 1
            task['deliverable'] = str(BASE / task['id'] / ('attempt-' + str(task['maximum_attempts'])) / 'result.json')
            task['inputs'] += [revision['review'], revision['result']]
    value[KEY] = revision
    value['protected_evidence'] += [revision[k] for k in ('baseline','review','result')]
    value['protected_evidence'] += list(revision['implementation'].values()) + list(revision['recoveries'].values())
    value['protected_evidence'].append(plan_reference or ref(root,PLAN))
    return value

def validate_revision(program, root, *, plan_reference=None):
    r = program[KEY]
    require(r['profile'] == 'integration-settled-recovery.v1' and r['user_instruction'] == USER
        and r['work'] == str(WORK) and r['prior_detours'] == 53
        and r['additional_consolidated_revision'] == 1 and r['additional_task_attempts'] == 2
        and r['attempt_increments'] == {t:1 for t in REOPEN} and r['reopened_nodes'] == REOPEN
        and r['live_calls_added'] == r['additional_transport_replacements'] == 0
        and r['attempts_reset'] is False and r['service_scope_reset'] is False
        and r['local_repair_packages'] == 1, 'Unreviewed settled recovery authority')
    for key in ('baseline','review','result','prior_program','prior_state','prior_binding','prior_ledger','prior_grant'):
        verify(root,r[key])
    require(set(r['implementation']) == MUTATED - {str(PLAN)}, 'Changed recovery implementation scope')
    for pointer in r['implementation'].values(): verify(root,pointer)
    baseline = read(root / r['baseline']['path'])
    require(baseline['calls'] == 2734 and baseline['prior_detours'] == 53
        and baseline['running_owners'] == baseline['reserved_dispatches'] == 0, 'Changed settled comparator')
    held = {x['previous']['path']:x['archive'] for x in baseline['archived']}
    for row in baseline['archived']:
        require(row['previous']['sha256'] == row['archive']['sha256'], 'Changed predecessor bytes')
        verify(root,row['archive'])
    for key,path in (('prior_program',PROGRAM),('prior_state',STATE),('prior_binding',BASE/'current-binding.json'),
            ('prior_ledger',BASE/'live-calls.json'),('prior_grant',BASE/'live-grant.json')):
        require(r[key] == held[str(path)], 'Lost recovery predecessor '+key)
    old, before = read(root/r['prior_program']['path']), read(root/r['prior_state']['path'])
    require(not old.get(KEY) and before['program_hash'] == digest(old)
        and not any(t['status']=='RUNNING' for t in before['tasks'].values()), 'Unsettled recovery predecessor')
    for tid, maximum in (('acquire-evidence',6),('acquire-p10',8)):
        require(before['tasks'][tid]['status']=='FAILED' and len(before['tasks'][tid]['attempts'])==maximum
            and next(t['maximum_attempts'] for t in old['tasks'] if t['id']==tid)==maximum, 'Wrong exhausted owner')
    require(set(r['recoveries']) == {'evidence','p10'}, 'Foreign recovery question')
    from legalmath.interpretation.assurance.phased import account_recovery
    for q,pointer in r['recoveries'].items():
        verify(root,pointer); checkpoint=read(root/pointer['path'])
        account_recovery.load(root,pointer,checkpoint['input_hash'])
        require(checkpoint['predecessor_recovery']==old['repair_execution']['recoveries'][q], 'Recovery lost prior census')
    evidence = read(root/r['recoveries']['evidence']['path'])['account_recovery']
    require(evidence['roots']==['detail-25'] and set(evidence['corrections'])=={'detail-25-part-1'}, 'Changed evidence correction scope')
    require(r['common_directories']=={q:str(WORK/'live/common'/q) for q in ('evidence','p10')}
        and r['live_directories']=={q:str(WORK/'live') for q in ('evidence','p10')}, 'Foreign recovery outputs')
    result=read(root/r['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['ledger_unchanged']
        and result['legal_acceptance'] is False, 'Missing local recovery validation')
    for pointer in result['evidence']: verify(root,pointer)
    for q,pointer in result['replays'].items():
        verify(root,pointer); replay=read(root/pointer['path'])
        require(replay['verdict']=='PASS' and replay['provider_calls']==0 and replay['production_constructor']
            and replay['actual_phase_admission'] and replay['ledger_unchanged']
            and replay['old_dispatches_unchanged'] and replay['recovery']==r['recoveries'][q], 'Missing actual production replay '+q)
        if q == 'p10':
            require(replay.get('reused_receipt_slots') == [2190]
                and replay['first_missing']['key'] != 'detail-10',
                'P10 replay would resample its completed charged response')
    require(set(result['replays'])=={'evidence','p10'}, 'Missing independent replay')
    targets=r['resolved_vetoes']
    require(len(targets)==1 and targets[0] in before.get('continuation_vetoes',[])
        and targets[0]['code']=='E_INTEGRITY' and targets[0]['reason']=='Changed phase on resume'
        and all('p10' in t for t in targets[0]['scope']), 'Foreign veto resolution')
    mapping=projection(baseline); projected=historical_projection(old,mapping)
    with historical_evidence(root,mapping): validate_program(projected,root)
    require(program==project_retained_plan(expected_program(projected,r,root,plan_reference=plan_reference),root,plan_reference),
        'Recovery changed unrelated graph, authority or criteria')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}

def project_state(before,program,now):
    value=deepcopy(before); r=program[KEY]
    require(not any(t['status']=='RUNNING' for t in value['tasks'].values()), 'Running owner cannot migrate')
    for tid in REOPEN:
        row=value['tasks'][tid]
        require(row['status']=='FAILED','Changed recovery owner')
        row.update(status='PENDING',reason='Reviewed exact recovery; retain all successful predecessor work')
        for k in ('result','dispatch_status','prerequisite_evidence','shared_scope'): row.pop(k,None)
    for veto in r['resolved_vetoes']:
        value['continuation_vetoes'].remove(veto)
        value.setdefault('resolved_continuation_vetoes',[]).append(dict(veto=veto,review=r['review'],evidence=r['result'],
            at_utc=now,basis='Actual reconstruction uses authenticated responses and separate new phase records.',attempts_reset=False,calls_added=0))
    value['program_hash']=digest(program)
    value['events'].append(dict(action='REVIEWED_SETTLED_RECOVERY',task_id=None,at_utc=now,review=r['review'],
        attempts_reset=False,calls_added=0,additional_task_attempts=2))
    return value

def validate_state_history(program,state,root):
    r=program[KEY]; before=read(root/r['prior_state']['path'])
    for tid,row in before['tasks'].items():
        require(state['tasks'][tid]['attempts'][:len(row['attempts'])]==row['attempts'], 'Changed prior attempts '+tid)
        if tid not in REOPEN and row['status']!='PENDING': require(state['tasks'][tid]==row,'Changed unrelated owner '+tid)
    prior=before.get('resolved_continuation_vetoes',[])
    require(state.get('resolved_continuation_vetoes',[])[:len(prior)]==prior,'Lost prior veto history')
    for veto in r['resolved_vetoes']:
        require(any(x['veto']==veto and x['review']==r['review'] and x['evidence']==r['result']
            for x in state.get('resolved_continuation_vetoes',[])), 'Unrecorded resolved veto')
    require(all(v in state.get('continuation_vetoes',[]) for v in before.get('continuation_vetoes',[])
        if v not in r['resolved_vetoes']), 'Lost independent veto')

def candidate_binding(program,pointer,baseline):
    r=program[KEY]; prior=read(ROOT/r['prior_binding']['path']); value=deepcopy(prior)
    value.update(user_instruction=USER,review=r['review'],program=pointer,predecessor=r['prior_binding'],
        phase_service_predecessor=r['prior_binding'],ledger_before=r['prior_ledger'])
    paths=sorted((ROOT/'src/legalmath').rglob('*.py'))+sorted((ROOT/'scripts').glob('legal_*.py'))
    paths += [ROOT/p for p in (PLAN,REVIEW,Path(program['prerequisite_repair']['source']['path']),
        BASE/'campaign-routing.toml',Path('requirements-context.lock'),Path('pyproject.toml'))]
    value['bindings']=[ref(ROOT,p) for p in paths]+[pointer,prior['phase_service_scope']]
    value['bindings'] += [r[k] for k in ('baseline','result','prior_binding','prior_grant','prior_ledger')]
    value['bindings'] += list(r['recoveries'].values())
    historical={(x['previous']['path'],x['previous']['sha256']):x for x in prior['historical_archives']}
    for row in baseline['archived']: historical[(row['previous']['path'],row['previous']['sha256'])]=row
    value['historical_archives']=list(historical.values())
    return value

def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import active_live, LIVE
    from scripts.legal_integration_campaign import provider
    from unittest.mock import patch
    journal=WORK/'registration.json'
    with ExitStack() as stack:
        initial=read(ROOT/PROGRAM)
        for path in dict.fromkeys((active_live(initial)/'supervisor.lock',WORK/'live/supervisor.lock',LIVE/'supervisor.lock',
                STATE.with_suffix('.run.lock'),DOC/'mission.execution.lock',STATE.with_suffix('.lock'))):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a')); fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED': finish_transaction(ROOT,journal)
            require(read(ROOT/PROGRAM).get(KEY,{}).get('work')==str(WORK),'Different recovery registration')
            return {'registered':True,'resumed':True}
        baseline=read(ROOT/WORK/'baseline.json'); held={x['previous']['path']:x['archive'] for x in baseline['archived']}
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        for row in baseline['archived']:
            if row['previous']['path'] not in MUTATED: require(ref(ROOT,row['previous']['path'])==row['previous'],'Changed settled input')
        require(datetime.now(timezone.utc)<datetime.fromisoformat(read(ROOT/BASE/'live-grant.json')['deadline_utc']), 'Live deadline expired')
        r=dict(profile='integration-settled-recovery.v1',user_instruction=USER,work=str(WORK),prior_detours=53,
            additional_consolidated_revision=1,additional_task_attempts=2,attempt_increments={t:1 for t in REOPEN},
            reopened_nodes=REOPEN,live_calls_added=0,additional_transport_replacements=0,attempts_reset=False,
            service_scope_reset=False,local_repair_packages=1,
            baseline=ref(ROOT,WORK/'baseline.json'),review=ref(ROOT,REVIEW),result=ref(ROOT,WORK/'local-result.json'),
            implementation={p:ref(ROOT,p) for p in sorted(MUTATED-{str(PLAN)})},
            recoveries={q:ref(ROOT,WORK/('recovery-'+q+('-v2' if q=='p10' else '')+'.json')) for q in ('evidence','p10')},
            common_directories={q:str(WORK/'live/common'/q) for q in ('evidence','p10')},
            live_directories={q:str(WORK/'live') for q in ('evidence','p10')},
            resolved_vetoes=[v for v in before.get('continuation_vetoes',[]) if v['reason']=='Changed phase on resume'],
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            prior_ledger=held[str(BASE/'live-calls.json')],prior_grant=held[str(BASE/'live-grant.json')])
        program=expected_program(historical_projection(old,projection(baseline)),r,ROOT)
        validate_program(program,ROOT)
        now=datetime.now(timezone.utc).isoformat(); state=project_state(before,program,now)
        stage=WORK/'registration-stage'; save(ROOT/stage/'program.json',program); save(ROOT/stage/'state.json',state)
        pointer={'path':str(PROGRAM),'sha256':ref(ROOT,stage/'program.json')['sha256']}
        binding=candidate_binding(program,pointer,baseline); save(ROOT/stage/'binding.json',binding)
        targets={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        original_text,original_bytes=Path.read_text,Path.read_bytes
        def staged_text(path,*args,**kwargs): return original_text(targets.get(path,path),*args,**kwargs)
        def staged_bytes(path,*args,**kwargs): return original_bytes(targets.get(path,path),*args,**kwargs)
        with patch.object(Path,'read_text',staged_text),patch.object(Path,'read_bytes',staged_bytes):
            require(len(provider().check()['calls'])==2734,'Staged provider changed calls')
        mission=historical_projection(read(ROOT/DOC/'mission.json'),projection(baseline,mission=True))
        master=mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'): master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),**{KEY:r})
        reason='Continue exact evidence correction and independent P10 resumption, then original eligible answers and comparisons. P14 unknown parameter, Gatecoin refusal and source applicability retain separate unresolved dispositions. Preserve every call and deadline.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='integration-master-settled-recovery-2026-10-17',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision='Reviewed one bounded package and one additional attempt for each of evidence/P10; no shared allowance reset.',
            next_task='product-contribution',next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,r['review'],r['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/WORK/'registration-check.json',validate_staged_mission(ROOT,stage,mission,54))
        writes=[{'path':str(path),'before':ref(ROOT,path),'replacement':ref(ROOT,stage/name)}
            for path,name in ((PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal); provider().check()
    return {'registered':True,'reopened_nodes':REOPEN,'additional_task_attempts':2,'calls_added':0,'detours':54}

def verification(directory=None):
    p=read(ROOT/PROGRAM); validate_program(p,ROOT); r=p[KEY]
    state=read(ROOT/STATE); validate_state_history(p,state,ROOT)
    old=read(ROOT/r['prior_ledger']['path']); ledger=read(ROOT/BASE/'live-calls.json')
    require(ledger['calls'][:len(old['calls'])]==old['calls'],'Prior calls changed')
    require(ref(ROOT,BASE/'live-grant.json')['sha256']==r['prior_grant']['sha256'],'Grant changed')
    binding=read(ROOT/BASE/'current-binding.json'); prior=read(ROOT/r['prior_binding']['path'])
    require(binding['program']==ref(ROOT,PROGRAM) and binding['review']==r['review']
        and binding['predecessor']==binding['phase_service_predecessor']==r['prior_binding']
        and all(binding[k]==prior[k] for k in ('phase_service_scope','service_recovery_policy','terminal_cancellation_recovery')), 'Changed recovery binding')
    for pointer in binding['bindings']: verify(ROOT,pointer)
    view=MasterExecution(ROOT,PROGRAM,STATE).summary()
    result=dict(profile='integration-settled-recovery-verification.v1',calls=len(ledger['calls']),historical_calls=41,
        detours=54,additional_owner_attempts=2,prior_calls_preserved=True,prior_attempts_preserved=True,
        integration_complete=False,**{k:view[k] for k in ('execution','ready','running','blocked')})
    save((directory or ROOT/WORK)/'verification.json',result)
    return result
