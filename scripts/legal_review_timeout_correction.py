"""Reconcile the proved empty-message timeout inside the existing R4 repair."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import signal
import time

from scripts.legal_integration_master import ROOT, BASE, DOC, PROGRAM, STATE, PLAN
from scripts.legal_mission_execution import read, save, ref, verify, require, digest, historical_evidence
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_review_receipt_correction import mapped as prior_mapping, seed_runtime

WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
HERE = WORK/'timeout-correction'
SOURCE = WORK/'continued-live'
RUNTIME = WORK/'recovered-live'
KEY = 'timeout_correction'
REASON = 'Ended timeout contains model output; inspect before retry'
SLOT = 3591
REQUEST = '118fd8849999262fa6a0fe38d53976e38f417b0d5551155014e5a4365dbc233a'
FAILED_KEY = 'audit-group-p14-eacf7d53747af05befb5a8e1'
CHANGED = ('scripts/legal_review_repair.py', 'scripts/legal_review_repair_service.py',
    'scripts/legal_integration_phased_live.py',
    'src/legalmath/interpretation/assurance/bounded_provider.py',
    'src/legalmath/interpretation/search/providers.py')
ADDED = ('scripts/legal_review_timeout_correction.py', 'tests/tooling/test_review_timeout_correction.py')


def mapped(rows, *, mission=False):
    # Unchanged mutable ledgers can have identical hashes in two snapshots.
    # Only replaced sources need projection; keep older archive identities.
    allowed=set(CHANGED)|{str(PLAN)}|({str(PROGRAM)} if mission else set())
    return prior_mapping([r for r in rows if r['previous']['path'] in allowed],mission=mission)


def exact_failure(root):
    from scripts.legal_review_repair_service import terminal_receipt
    from legalmath.interpretation.search.providers import TerminatedCallTimeout
    request, schema, failure, receipt = terminal_receipt(root, BASE, SLOT, REQUEST)
    require(isinstance(failure, TerminatedCallTimeout), 'Not the reviewed local timeout')
    folder = root/SOURCE/'arms/p14/baseline/calls'/FAILED_KEY
    wire, result = read(folder/'reference-binding.json'), read(folder/'result.json')
    require(digest(wire['request']) == digest(request) == REQUEST
        and digest(wire['schema']) == digest(schema)
        and result.get('continuation_veto') is True and result.get('error') == 'E_AUTHORITY'
        and result.get('reason') == REASON, 'No exact empty-message product failure')
    ledger = read(root/BASE/'live-calls.json')
    require(ledger['calls'][SLOT-1]['request_hash'] == REQUEST, 'Timeout charge changed')
    return dict(slot=SLOT, request_hash=REQUEST, schema_hash=digest(schema),
        receipt=ref(root,receipt), dispatch_result=ref(root,folder/'result.json'),
        reference_binding=ref(root,folder/'reference-binding.json'),
        provider_calls=0, legal_acceptance=False)


def verify_orphans(root, state, runtime):
    from scripts.legal_mission_execution import process_alive
    from scripts.legal_review_service_checkpoint import checked
    from scripts.legal_mission_execution import process_identity
    running = []
    for tid, row in state['tasks'].items():
        if row['status'] != 'RUNNING':
            continue
        if row.get('service_checkpoint'):
            checked(root, tid, row)
            require(row.get('live_supervisor') == process_identity(os.getpid()) or
                not process_alive(row.get('live_supervisor')), 'Paused checkpoint has a different active owner')
        else:
            running.append(row)
    require(all(r.get('master_live') and r.get('live_supervisor')
        and not process_alive(r['live_supervisor']) for r in running),
        'A retained product reservation still has a live or unknown owner')
    for path in runtime.rglob('calls/dispatch.json'):
        require(not any(r['status'] == 'RESERVED' for r in read(path)['calls'].values()),
            'Retained owner has uncertain dispatch')


def settle_once(root=ROOT, *, expected):
    from scripts.legal_mission_execution import process_identity, process_alive
    root = Path(root)
    owner = read(root/WORK/'worker.json')['process']
    require(owner == expected and process_identity(owner['pid']) == owner, 'Worker identity changed')
    with ExitStack() as stack:
        journals = sorted((root/SOURCE).rglob('calls/dispatch.json'))
        locks = [root/STATE.with_suffix('.lock'), root/DOC/'mission.execution.lock',
            root/WORK/'service/service-worker.lock'] + [p.with_name('dispatch.lock') for p in journals]
        try:
            for path in locks:
                handle = stack.enter_context(path.open('a'))
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(settled=False, reason='Shared state or provider still owned')
        state = read(root/STATE)
        require(state['tasks']['baseline-p14']['status'] == 'FAILED'
            and len(state['tasks']['baseline-p14']['attempts']) == 3
            and state['tasks']['baseline-gatecoin']['status'] == 'RUNNING'
            and len(state['tasks']['baseline-gatecoin']['attempts']) == 4,
            'Different owner state; review again')
        require(all(r.get('master_live') and r.get('live_supervisor') and
            (r['live_supervisor']==owner or not process_alive(r['live_supervisor']))
            for r in state['tasks'].values() if r['status']=='RUNNING'),
            'A different active supervisor owns retained work')
        require(all(r['status']!='RESERVED' for p in journals for r in read(p)['calls'].values()),
            'A provider dispatch remains uncertain')
        circuit = read(root/WORK/'service/service-circuit.json')
        require(circuit['open'] and circuit['failed_slots'][-1] == SLOT
            and not circuit.get('half_open_reserved'), 'Service state changed')
        children = Path(f'/proc/{owner["pid"]}/task/{owner["pid"]}/children')
        if children.read_text().strip():
            return dict(settled=False, reason='Supervisor has a child; no signal sent')
        before = ref(root,BASE/'live-calls.json')
        stopped = False
        try:
            os.kill(owner['pid'], signal.SIGSTOP)
            stopped = True
            for _ in range(100):
                fields = Path(f'/proc/{owner["pid"]}/stat').read_text().rsplit(') ',1)[1].split()
                if fields[0] in ('T','t'): break
                time.sleep(.01)
            require(fields[0] in ('T','t') and process_identity(owner['pid']) == owner
                and not children.read_text().strip() and ref(root,BASE/'live-calls.json') == before,
                'Supervisor did not reach an idle stable boundary')
            evidence = dict(settled=True, process=owner, at_utc=datetime.now(timezone.utc).isoformat(),
                ledger=before, calls=len(read(root/BASE/'live-calls.json')['calls']),
                dispatches=[ref(root,p) for p in journals], reserved_dispatches=0, provider_children=[])
            save(root/HERE/'handover.json',evidence)
            os.kill(owner['pid'],signal.SIGTERM)
            os.kill(owner['pid'],signal.SIGCONT)
            stopped=False
            for _ in range(100):
                if process_identity(owner['pid']) is None: break
                time.sleep(.05)
            require(process_identity(owner['pid']) is None, 'Supervisor still alive')
            evidence['supervisor_ended']=True
            save(root/HERE/'handover.json',evidence)
            return evidence
        finally:
            if stopped: os.kill(owner['pid'],signal.SIGCONT)


def freeze(root=ROOT):
    from scripts.legal_mission_execution import process_alive
    root=Path(root)
    require(not (root/HERE/'baseline.json').exists(), 'Timeout predecessor already frozen')
    ended=read(root/HERE/'handover.json')
    require(ended['supervisor_ended'] and not process_alive(ended['process']), 'Supervisor remains active')
    require(ref(root,BASE/'live-calls.json') == ended['ledger'], 'Charges changed after handover')
    rows=[]
    paths=[*CHANGED,str(PLAN),str(PROGRAM),str(STATE),str(DOC/'mission.json'),
        str(BASE/'current-binding.json'),str(BASE/'live-calls.json'),str(BASE/'live-grant.json'),
        str(WORK/'worker.json'),str(WORK/'service/service-circuit.json'),str(WORK/'service/service-recovery.json')]
    for relative in paths:
        archive=HERE/'before'/relative
        target=root/archive
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream: stream.write((root/relative).read_bytes())
        rows.append(dict(previous=ref(root,relative),archive=ref(root,archive)))
    baseline=dict(settled=True,archived=rows,handover=ref(root,HERE/'handover.json'),calls=ended['calls'])
    save(root/HERE/'baseline.json',baseline)
    return baseline


def seed(root, provider):
    root=Path(root)
    failure=exact_failure(root)
    manifest=seed_runtime(root,root/SOURCE,root/RUNTIME,provider)
    excluded=root/RUNTIME/'arms/p14/baseline/calls'/FAILED_KEY
    held=root/HERE/'excluded-dispatch'
    excluded.rename(held)
    manifest['files']=[r for r in manifest['files']
        if not Path(r['copy']['path']).is_relative_to(excluded.relative_to(root))]
    journal=root/RUNTIME/'arms/p14/baseline/calls/dispatch.json'
    value=read(journal)
    row=value['calls'].pop(FAILED_KEY)
    save(journal,value)
    for item in manifest['files']:
        if item['copy']['path']==str(journal.relative_to(root)):
            item.update(copy=ref(root,journal), reviewed_exclusion=FAILED_KEY)
    manifest['excluded']=[dict(key=FAILED_KEY,prior=row,proof=failure,
        files=[ref(root,p) for p in sorted(held.iterdir()) if p.is_file()])]
    save(root/HERE/'seed.json',manifest)
    return manifest


def expected_program(old, correction, root, plan_reference):
    rows=read(root/correction['baseline']['path'])['archived']
    value=historical_projection(old,mapped(rows))
    value['review_repair'][KEY]=correction
    task=next(t for t in value['tasks'] if t['id']=='baseline-p14')
    require(task['maximum_attempts']==3, 'Different P14 continuation baseline')
    task.update(maximum_attempts=4,deliverable=str(BASE/'baseline-p14/attempt-4/result.json'))
    task['inputs'] += [correction['review'],correction['result']]
    value['protected_evidence'] += [correction[k] for k in ('review','result','baseline','seed')]
    value['protected_evidence'] += list(correction['implementation'].values())+[plan_reference]
    return value


def project_state(before, program, now):
    correction=program['review_repair'][KEY]
    state=deepcopy(before)
    vetoes=[v for v in before.get('continuation_vetoes',[]) if v['code']=='E_AUTHORITY' and v['reason']==REASON]
    require(len(vetoes)==1 and state['tasks']['baseline-p14']['status']=='FAILED'
        and len(state['tasks']['baseline-p14']['attempts'])==3, 'Different failure/veto to reconcile')
    row=state['tasks']['baseline-p14']
    row.update(status='PENDING',reason='Reviewed empty-message timeout correction; retain all three failed attempts')
    row.pop('result',None)
    state['continuation_vetoes']=[v for v in before['continuation_vetoes'] if v not in vetoes]
    state.setdefault('resolved_continuation_vetoes',[]).append(dict(veto=vetoes[0],
        resolution=correction['result'],review=correction['review'],at_utc=now))
    state['program_hash']=digest(program)
    state['events'].append(dict(task_id='baseline-p14',action='EMPTY_TIMEOUT_CORRECTION',at_utc=now,
        review=correction['review'],attempt_additions=1,calls_added=0,detours_added=0))
    return state


def validate(program, root, plan_reference):
    from scripts.legal_mission_execution import validate_program
    correction=program['review_repair'][KEY]
    require(correction['profile']=='empty-message-timeout-correction.v1'
        and correction['runtime']==str(RUNTIME) and correction['calls_added']==0
        and correction['detours_added']==0 and correction['attempt_additions']=={'baseline-p14':1}
        and set(correction['implementation'])==set(CHANGED+ADDED), 'Changed R4 correction scope')
    for name in ('review','result','baseline','seed','prior_program','prior_state','prior_binding'):
        verify(root,correction[name])
    for item in correction['implementation'].values(): verify(root,item)
    baseline=read(root/correction['baseline']['path'])
    require(baseline['settled'] and baseline['calls']==SLOT, 'Wrong R4 comparator')
    for row in baseline['archived']:
        require(row['previous']['sha256']==row['archive']['sha256'],'Changed R4 predecessor bytes')
        verify(root,row['archive'])
    held={r['previous']['path']:r['archive'] for r in baseline['archived']}
    require(correction['prior_program']==held[str(PROGRAM)] and correction['prior_state']==held[str(STATE)]
        and correction['prior_binding']==held[str(BASE/'current-binding.json')], 'Wrong R4 predecessor')
    old=read(root/correction['prior_program']['path'])
    require(KEY not in old['review_repair'], 'Duplicate timeout correction')
    with historical_evidence(root,mapped(baseline['archived'])): validate_program(old,root)
    result=read(root/correction['result']['path'])
    require(result['verdict']=='PASS' and result['provider_calls']==0 and result['legal_acceptance'] is False,
        'R4 correction lacks local passing evidence')
    for item in result['evidence']: verify(root,item)
    require(program==expected_program(old,correction,root,plan_reference),'Changed graph or allowance beyond reviewed P14 continuation')
    return {t['id']:t['maximum_attempts'] for t in program['tasks']}


def validate_history(program, state, root):
    correction=program['review_repair'][KEY]
    before=read(root/correction['prior_state']['path'])
    require(state['events'][:len(before['events'])]==before['events'],'Lost R4 event history')
    for tid,row in before['tasks'].items():
        current=state['tasks'][tid]
        require(len(current['attempts'])>=len(row['attempts']),'Lost R4 attempt')
        for a,b in zip(row['attempts'],current['attempts']):
            require(all(b.get(k)==v for k,v in a.items()),'Changed R4 attempt '+tid)
        if row['status']=='SUCCEEDED': require(current==row,'Resampled successful owner')
    prior=before.get('resolved_continuation_vetoes',[])
    require(state.get('resolved_continuation_vetoes',[])[:len(prior)]==prior,'Lost earlier veto resolutions')
    for veto in before.get('continuation_vetoes',[]):
        require(veto in state.get('continuation_vetoes',[]) or any(r.get('veto')==veto
            and r.get('resolution')==correction['result'] and veto['reason']==REASON
            for r in state.get('resolved_continuation_vetoes',[])), 'Lost unresolved veto')


def register():
    from scripts.legal_integration_post_review import finish_transaction
    from scripts.legal_integration_phased_live import LIVE
    from scripts.legal_integration_repair_execution import validate_staged_mission
    journal=HERE/'registration.json'
    with ExitStack() as stack:
        for path in (WORK/'worker.lock',LIVE/'supervisor.lock',SOURCE/'supervisor.lock',
                RUNTIME/'supervisor.lock',WORK/'service/service-worker.lock',STATE.with_suffix('.run.lock'),
                DOC/'mission.execution.lock',STATE.with_suffix('.lock')):
            (ROOT/path).parent.mkdir(parents=True,exist_ok=True)
            handle=stack.enter_context((ROOT/path).open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/journal).exists():
            if read(ROOT/journal)['status']!='COMMITTED': finish_transaction(ROOT,journal)
            require(read(ROOT/PROGRAM)['review_repair'].get(KEY),'Different timeout correction registered')
            return dict(registered=True,resumed=True)
        baseline=read(ROOT/HERE/'baseline.json')
        held={r['previous']['path']:r['archive'] for r in baseline['archived']}
        for path in (PROGRAM,STATE,DOC/'mission.json',BASE/'current-binding.json',BASE/'live-calls.json',BASE/'live-grant.json'):
            require(ref(ROOT,path)['sha256']==held[str(path)]['sha256'],'R4 predecessor changed: '+str(path))
        old,before=read(ROOT/PROGRAM),read(ROOT/STATE)
        verify_orphans(ROOT,before,ROOT/SOURCE)
        exact_failure(ROOT)
        correction=dict(profile='empty-message-timeout-correction.v1',runtime=str(RUNTIME),
            calls_added=0,detours_added=0,attempt_additions={'baseline-p14':1},
            review=ref(ROOT,HERE/'review.md'),result=ref(ROOT,HERE/'result.json'),
            baseline=ref(ROOT,HERE/'baseline.json'),seed=ref(ROOT,HERE/'seed.json'),
            prior_program=held[str(PROGRAM)],prior_state=held[str(STATE)],prior_binding=held[str(BASE/'current-binding.json')],
            implementation={p:ref(ROOT,p) for p in CHANGED+ADDED})
        program=expected_program(old,correction,ROOT,ref(ROOT,PLAN))
        validate(program,ROOT,ref(ROOT,PLAN))
        now=datetime.now(timezone.utc).isoformat()
        state=project_state(before,program,now)
        validate_history(program,state,ROOT)
        stage=HERE/'registration-stage'
        save(ROOT/stage/'program.json',program)
        save(ROOT/stage/'state.json',state)
        pointer=dict(path=str(PROGRAM),sha256=ref(ROOT,stage/'program.json')['sha256'])
        binding=deepcopy(read(ROOT/BASE/'current-binding.json'))
        binding['bindings']=historical_projection(binding['bindings'],mapped(baseline['archived'],mission=True))
        binding['program']=pointer
        binding['bindings'] += [pointer,ref(ROOT,PLAN),correction['review'],correction['result'],
            correction['baseline'],correction['seed'],*correction['implementation'].values()]
        known={(r['previous']['path'],r['previous']['sha256']) for r in binding['historical_archives']}
        binding['historical_archives'] += [r for r in baseline['archived']
            if (r['previous']['path'],r['previous']['sha256']) not in known]
        binding['timeout_correction']=correction['review']
        binding['predecessor']=correction['prior_binding']
        save(ROOT/stage/'binding.json',binding)
        mission=historical_projection(read(ROOT/DOC/'mission.json'),mapped(baseline['archived'],mission=True))
        master=mission['integration_master']
        for key in master:
            if key in program and isinstance(program[key],dict) and program[key].get('profile'):
                master[key]=deepcopy(program[key])
        master.update(program=pointer,plan=ref(ROOT,PLAN),review_repair=program['review_repair'])
        reason='Recover exact ended empty-message timeout, continue P14 with its failed attempts preserved, resume Gatecoin attempt 4 and drain independent original owners.'
        mission['next_task_reason']=reason
        mission['history'].append(dict(id='review-timeout-correction-2026-10-21',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=now,result_evidence=[pointer,correction['review'],correction['result']]))
        save(ROOT/stage/'mission.json',mission)
        save(ROOT/HERE/'registration-check.json',validate_staged_mission(ROOT,stage,mission,62))
        from unittest.mock import patch
        from scripts.legal_integration_campaign import provider
        targets={ROOT/PROGRAM:ROOT/stage/'program.json',ROOT/BASE/'current-binding.json':ROOT/stage/'binding.json'}
        rt,rb=Path.read_text,Path.read_bytes
        with patch.object(Path,'read_text',lambda path,*a,**k:rt(targets.get(path,path),*a,**k)), \
             patch.object(Path,'read_bytes',lambda path,*a,**k:rb(targets.get(path,path),*a,**k)):
            require(len(provider().check()['calls'])==baseline['calls'],'R4 authority changed charges')
        writes=[dict(path=str(path),before=ref(ROOT,path),replacement=ref(ROOT,stage/name)) for path,name in (
            (PROGRAM,'program.json'),(STATE,'state.json'),(BASE/'current-binding.json','binding.json'),(DOC/'mission.json','mission.json'))]
        save(ROOT/journal,dict(profile='legal-master-registration-transaction.v1',status='PREPARED',writes=writes))
        finish_transaction(ROOT,journal)
    return dict(registered=True,calls_added=0,detours_added=0,attempt_additions={'baseline-p14':1})
