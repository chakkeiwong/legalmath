"""One authenticated replay repair for the existing Gatecoin reboot reservation.

This operational adapter changes no production source, grant or product limit.
"""
from copy import deepcopy
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import json
import os
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.canonical import digest
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.bounded_context import ContextRoute, Limits, tokenizer
from legalmath.interpretation.assurance.bounded_product import BoundDispatch
from legalmath.interpretation.assurance.phased import product as product_module
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import downstream_input, downstream_instructions
from legalmath.interpretation.assurance.phased.account_recovery import restore_record_order
from legalmath.interpretation.assurance.phased.synthesis_recovery import historical_request
from legalmath.interpretation.assurance.phased.evidence_store import load_exact
from scripts import legal_integration_reboot_resume as reboot
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive

WORK = reboot.WORK / 'replay-repair'
SOURCE = reboot.CALLS.parent
REVIEW = reboot.WORK / 'replay-repair-review.md'
ORIGINAL_EXECUTE = product_module.execute
ORIGINAL_BOOT_IDENTITY = reboot.boot_identity


def authenticated_boot():
    current = ORIGINAL_BOOT_IDENTITY()
    recorded = read(reboot.WORK/'authorization.json')['boot']
    require(current['id'] == recorded['id'], 'A different boot requires another reviewed recovery')
    # The kernel boot UUID is the identity. Its derived UTC timestamp changed
    # on the same observed boot; it must not falsely imply a machine restart.
    return recorded


def parent_authority():
    with patch.object(reboot,'boot_identity',authenticated_boot):
        return reboot.authority()


def restored_calls(product, name, calls, source):
    """Restore order only after comparing complete unique source populations."""
    source = Path(source)
    prepared = product.prepare_calls(calls)
    phase_file = source / 'phases' / name / 'phase.json'
    if not phase_file.exists():
        return prepared
    phase = read(phase_file)
    expected = {r['key']: r['identity'] for r in phase['contract']['calls']}
    require(len(expected) == len(prepared) and set(expected) == {r['key'] for r in prepared},
            'Reboot replay changed phase population')
    restored = []
    for call in prepared:
        directory = source / 'calls' / call['key']
        if source == SOURCE and call['key'] == reboot.KEY:
            directory = reboot.WORK / 'before' / reboot.KEY
        if (directory / 'request.json').exists():
            old, schema = read(directory / 'request.json'), read(directory / 'schema.json')
            require(schema == call['schema']
                    and product.dispatch.request_identity(old, schema) == expected[call['key']],
                    'Retained reboot request or schema changed')
            request = restore_record_order(old, call['request'])
            call = {**call, 'request': request}
        require(product.dispatch.request_identity(call['request'], call['schema']) == expected[call['key']],
                'Reboot replay changed a phase request')
        restored.append(call)
    return restored


def hydrate_outcome(source, outcome):
    """Recover original field order from authenticated messages, not new text."""
    value = deepcopy(outcome)
    for row in value.get('results', []):
        folder = Path(source) / 'calls' / row['key']
        if row['result'].get('status') != 'VALIDATED' or not (folder / 'wire-response.json').exists():
            continue  # Imported phase-zero results already had their stored order.
        retained = read(folder / 'result.json')
        require(row['result'] == retained and row.get('dispatch_result_hash') == digest(retained),
                'Retained phase response changed')
        wire, response = read(folder / 'reference-binding.json'), read(folder / 'wire-response.json')
        require(wire['original_request'] == read(folder / 'request.json')
                and wire['original_schema'] == read(folder / 'schema.json'), 'Retained response contract changed')
        original = historical_request(wire, reviewed=True)
        events = [json.loads(line) for line in response['provenance']['events_jsonl'].splitlines() if line]
        messages = [e['item']['text'] for e in events if e.get('item', {}).get('type') == 'agent_message']
        require(len(messages) == 1, 'Ambiguous retained response message')
        payload = json.loads(messages[0])
        require(payload == response['value'], 'Retained message differs from wire response')
        def exact(request, schema):
            require(request == original and schema == wire['original_schema'], 'Changed response decoder request')
            return deepcopy(wire)
        with patch.object(bounded_references, 'prepare', exact):
            decoded = bounded_references.resolve(payload, wire, maximum_bytes=Limits().decoded_output_bytes)
        require(decoded == retained['value'], 'Decoded response differs from validated value')
        row['result']['value'] = decoded
    return value


def exact_execute(product, name, calls, **kwargs):
    if product.directory != SOURCE:
        return ORIGINAL_EXECUTE(product, name, calls, **kwargs)
    prepared = restored_calls(product, name, calls, SOURCE)
    with patch.object(product, 'prepare_calls', lambda value: value):
        outcome = ORIGINAL_EXECUTE(product, name, prepared, **kwargs)
    return hydrate_outcome(SOURCE, outcome)


def replay():
    """Run real grouping and request constructors, stopping before any dispatch."""
    from scripts.legal_integration_master import TOKENIZER
    from scripts import legal_integration_phased_live as live
    campaign = live.configure()
    program = read(reboot.PROGRAM)
    envelope = read(ROOT / program['prerequisite_repair']['source']['path'])
    route = ContextRoute(envelope, tokenizer(ROOT / TOKENIZER), limits=Limits())
    require(route.records == read(SOURCE / 'source-store.json'), 'Source store changed')
    p = object.__new__(PhasedProduct)
    p.root, p.directory, p.route = ROOT, WORK / 'probe', route
    p.downstream_input_profile = downstream_input.PROFILE
    p.downstream_capacity_profile = downstream_input.CAPACITY_PROFILE
    p.downstream_instruction_profile = downstream_instructions.PROFILE
    p.active_questions = ('gatecoin',)
    p.retained_acquisition = load_exact(ROOT / live.LIVE / 'acquisition/investigation.json')
    p.retained_details = load_exact(SOURCE / 'requirement-details.json')
    p.dispatch = BoundDispatch(campaign.provider(), p.directory / 'calls', route, maximum_calls=8100)
    p.dispatch.retained_initial = ROOT, program['synthesis_resolution']['successors']['gatecoin']
    phases = []
    ledger_before = read(reboot.BASE / 'live-calls.json')
    journal_before = ref(ROOT, reboot.CALLS / 'dispatch.json')

    class ReachedPending(Exception):
        pass

    def phase(name, calls):
        calls = restored_calls(p, name, calls, SOURCE)
        saved = read(SOURCE / 'phases' / name / 'phase.json')
        contract = {'profile': 'bounded-persisted-phase.v1', 'name': name,
            'input_hash': route.input_hash, 'implementation_identity': ref(ROOT,reboot.BASE/'current-binding.json')['sha256'],
            'calls': [{'key':c['key'],'identity':p.dispatch.request_identity(c['request'],c['schema'])} for c in calls]}
        require(contract == saved['contract'], 'Full replay changed saved phase')
        phases.append(dict(name=name,status=saved['status'],calls=len(calls)))
        if saved['status'] == 'COMPLETE':
            verify(ROOT,saved['outcome'])
            outcome = load_exact(ROOT/saved['outcome']['path'])
            for row in outcome['results']:
                retained = read(SOURCE/'calls'/row['key']/'result.json')
                require(digest(retained)==row['dispatch_result_hash'] and retained==row['result'],
                        'Completed result changed')
                next(c for c in calls if c['key']==row['key'])['validate'](retained['value'])
            return hydrate_outcome(SOURCE,outcome)
        require(name == 'reduction-gatecoin-5' and saved['status']=='RUNNING', 'Unexpected pending phase')
        with patch.object(bounded_references,'prepare',reboot.exact_prepare):
            measured=[dict(key=c['key'],measurement=p.dispatch.measure(c['request'],c['schema'])) for c in calls]
        require(saved['measurements']==measured and not saved['input_blocks'], 'Pending measurement changed')
        raise ReachedPending()

    p.run_phase = phase
    question = next(q for q in envelope['original_questions'] if q['question_id']=='gatecoin')
    try:
        p.reduce('gatecoin',question,[])
    except ReachedPending:
        pass
    else:
        raise AssertionError('Replay did not reach the reserved phase')
    require(read(reboot.BASE/'live-calls.json') == ledger_before
            and ref(ROOT,reboot.CALLS/'dispatch.json') == journal_before, 'No-call replay changed production evidence')
    value=dict(verdict='PASS',phases=phases,provider_calls=0,ledger_unchanged=True,
        dispatch_unchanged=True,full_production_reconstruction=True,pending_measurements_unchanged=True,
        pending_request_hash=reboot.TARGET,legal_acceptance=False)
    save(WORK/'replay.json',value)
    print(json.dumps(value,indent=2))


def now():
    return datetime.now(timezone.utc).isoformat()


def authority():
    parent_authority()
    value = read(WORK/'authorization.json')
    require(value['profile']=='exact-reboot-replay-repair.v1' and value['maximum_recovery_segments']==1
            and value['attempt']==14 and value['additional_owner_attempts']==0,
            'Changed replay recovery authority')
    for pointer in value['bindings']:
        verify(ROOT,pointer)
    return value


def project_recovery(state, review, evidence, process, at_utc):
    """Keep the failed segment and resume only its still-unused reservation."""
    value=deepcopy(state)
    require(not any(r['status']=='RUNNING' for r in value['tasks'].values()), 'An owner is still running')
    row=value['tasks']['acquire-gatecoin']
    require(row['status']=='FAILED' and len(row['attempts'])==14
            and row['reason']=='acquire-gatecoin failed: Changed phase on resume', 'Different settled owner')
    last=row['attempts'][-1]
    require(last['number']==14 and 'result' in last and not row.get('recovery_segments'),
            'This recovery segment is already used or the attempt changed')
    vetoes=[v for v in value.get('continuation_vetoes',[]) if 'acquire-gatecoin' in v['scope']]
    require(len(vetoes)==1 and vetoes[0]['code']=='E_INTEGRITY'
            and vetoes[0]['reason']=='Changed phase on resume'
            and all('gatecoin' in t for t in vetoes[0]['scope']), 'Different unresolved veto')
    failed=deepcopy(last)
    row['recovery_segments']=[dict(number=1,prior_terminal_attempt=failed,review=review,
        diagnostic=evidence,started_at_utc=at_utc,additional_owner_attempts=0,
        basis='Resume the interrupted unchanged phase; the failed replay dispatched no call.')]
    row.pop('result',None)
    row.update(status='RUNNING',master_live=True,live_supervisor=process,
        reason='One reviewed replay recovery segment of the original interrupted attempt 14.')
    value['continuation_vetoes'].remove(vetoes[0])
    value.setdefault('resolved_continuation_vetoes',[]).append(dict(veto=vetoes[0],review=review,evidence=evidence,
        at_utc=at_utc,basis='Full reconstruction preserves all phase identities and pending measurements.',
        attempts_reset=False,calls_added=0))
    value.setdefault('events',[]).append(dict(action='REBOOT_REPLAY_RECOVERY_SEGMENT',task_id='acquire-gatecoin',
        at_utc=at_utc,review=review,evidence=evidence,original_attempt=14,recovery_segment=1,
        additional_owner_attempts=0,prior_terminal_result=failed['result']))
    return value


def snapshot():
    parent_authority()
    require(not process_alive(read(reboot.WORK/'worker.json')['process']), 'Previous recovery supervisor is still alive')
    state=read(reboot.BASE/'execution-state.json')
    require(not any(r['status']=='RUNNING' for r in state['tasks'].values()), 'Another owner is running')
    calls=read(reboot.BASE/'live-calls.json')
    require(len(calls['calls'])==reboot.SLOT
            and calls==read(reboot.WORK/'before/live-calls.json'), 'Calls advanced after failed replay')
    require(not any((reboot.WORK/n).exists() for n in
            ('resume-started.json','pending-call-settled.json','recovered-response.json')), 'Pending dispatch was already resumed')
    reboot.authenticated_wire(reboot.WORK/'before'/reboot.KEY)
    journal=read(reboot.CALLS/'dispatch.json')
    require(len(journal['calls'])==146 and reboot.KEY not in journal['calls']
            and all(r['status']=='VALIDATED' for r in journal['calls'].values()), 'Changed reconciled dispatch journal')
    for key,row in journal['calls'].items():
        require(digest(read(reboot.CALLS/key/'result.json'))==row['result_hash'], 'Changed retained successful result')
    baseline=read(reboot.WORK/'baseline.json')
    verify(ROOT,baseline['charge']['stage'])
    require(read(reboot.BASE/'current-stage.json')==baseline['charge']['stage'], 'Pending stage changed')
    directory=ROOT/Path(baseline['service_scope']['path']).parent
    recovery=read(directory/'service-recovery.json')
    require(recovery['charges'][-1]==baseline['charge'], 'Changed pending recovery reservation')
    circuit=read(directory/'service-circuit.json')
    require(circuit['open'] and circuit['failed_slots'][-1]==reboot.SLOT, 'Changed pending service circuit')
    project_recovery(state,ref(ROOT,REVIEW),ref(ROOT,WORK/'replay.json'),{'pid':0,'start':'preflight'},now())
    return dict(state=ref(ROOT,reboot.BASE/'execution-state.json'),journal=ref(ROOT,reboot.CALLS/'dispatch.json'),
        calls=ref(ROOT,reboot.BASE/'live-calls.json'),service_recovery=ref(ROOT,directory/'service-recovery.json'),
        service_circuit=ref(ROOT,directory/'service-circuit.json'),boot=authenticated_boot())


def record_mission(identity, decision, references):
    path=ROOT/'docs/implementation/legal-mission-control/mission.json'
    with path.with_name('mission.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        mission=read(path)
        require(not any(r['id']==identity for r in mission['history']), 'Recovery checkpoint already recorded')
        mission['next_task_reason']=decision
        mission['history'].append(dict(id=identity,task_id='product-contribution',kind='product_evaluation',
            outcome='no_advance',decision=decision,next_task='product-contribution',next_task_reason=decision,
            recorded_at_utc=now(),result_evidence=references))
        save(path,mission)


def activate():
    authority()
    before=read(WORK/'baseline.json')
    require(snapshot()==before, 'Recovery baseline changed before activation')
    with (reboot.BASE/'execution-state.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(ref(ROOT,reboot.BASE/'execution-state.json')==before['state'], 'Concurrent owner change')
        state=read(reboot.BASE/'execution-state.json')
        save(WORK/'state-before.json',state)
        failed=state['tasks']['acquire-gatecoin']['result']
        save(WORK/'failed-segment.json',read(ROOT/failed['path']))
        for path in (SOURCE.parent/'diagnosis.json',reboot.OLD/'next-actions-gatecoin.json'):
            if path.exists(): save(WORK/('before-'+path.name),read(path))
        projected=project_recovery(state,ref(ROOT,REVIEW),ref(ROOT,WORK/'replay.json'),process_identity(os.getpid()),now())
        save(reboot.BASE/'execution-state.json',projected)
        save(WORK/'activated.json',dict(at_utc=now(),prior_terminal_result=failed,
            attempt=14,recovery_segment=1,calls_added=0,additional_owner_attempts=0))
    record_mission('machine-reboot-replay-repair-2026-10-20',
        'Resume the original Gatecoin reservation after exact phase replay; preserve its failed reconstruction segment. '
        'Then release only pre-dispatch service deferrals and continue the existing independent graph.',
        [ref(ROOT,WORK/name) for name in ('authorization.json','replay.json','activated.json')])


def checked_complete(self, request, schema, settings):
    authority()
    with patch.object(reboot,'boot_identity',authenticated_boot):
        return reboot.resume_complete(self,request,schema,settings)


def finish_segment(execution, result):
    pointer=ref(ROOT,WORK/'node-result.json')
    with execution.locked() as state:
        row=state['tasks']['acquire-gatecoin']
        require(row['status']=='RUNNING' and len(row.get('recovery_segments',[]))==1,
                'No unique active recovery segment')
        segment=row['recovery_segments'][0]
        require('finished_at_utc' not in segment
                and row['attempts'][-1]==segment['prior_terminal_attempt'],
                'Recovery changed the original terminal attempt')
        row.update(status=result['status'],result=pointer,reason=result['conclusion'])
        segment.update(finished_at_utc=now(),result=pointer)
        state['events'].append(dict(action='REBOOT_REPLAY_RECOVERY_SETTLED',task_id='acquire-gatecoin',
            at_utc=now(),result=pointer,original_attempt_preserved=True))
        save(execution.state_path,state)
    record_mission('machine-reboot-replay-gatecoin-settled-2026-10-20',result['conclusion'],[pointer])
    execution.sync_mission()


def release_deferrals(execution):
    binding=read(reboot.BASE/'current-binding.json')
    circuit=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-circuit.json')
    if circuit['open'] or not (reboot.WORK/'pending-call-settled.json').exists():
        return []
    released=[]
    with execution.locked() as state:
        for tid in ('acquire-p10','acquire-evidence'):
            row=state['tasks'][tid]
            events=[e for e in state['events'] if e.get('task_id')==tid and e.get('action')=='PREREQUISITE_BLOCKED']
            deferred=events[-1] if events else {}
            if (row['status']=='BLOCKED' and row.get('dispatch_status')=='NOT_DISPATCHED'
                    and deferred.get('shared_scope')==['provider-service']
                    and deferred.get('evidence')==row.get('prerequisite_evidence')
                    and binding['phase_service_scope'] in row.get('prerequisite_evidence',[])):
                for pointer in row['prerequisite_evidence']:
                    verify(ROOT,pointer)
                previous=deepcopy(row)
                row.update(status='PENDING',reason='The original shared service prerequisite recovered; existing unused attempt remains.')
                for key in ('dispatch_status','prerequisite_evidence','shared_scope'):
                    row.pop(key,None)
                state.setdefault('events',[]).append(dict(action='SERVICE_DEFERRAL_RELEASED',task_id=tid,
                    at_utc=now(),previous=previous,review=ref(ROOT,REVIEW),attempt_consumed=False))
                released.append(tid)
        save(execution.state_path,state)
    save(WORK/'deferrals-released.json',dict(at_utc=now(),tasks=released,attempts_added=0))
    return released


def worker():
    from scripts import legal_integration_phased_live as live
    with ExitStack() as stack:
        for path in (WORK/'worker.lock',reboot.WORK/'worker.lock',reboot.OLD/'execution/worker.lock'):
            handle=stack.enter_context(path.open('a'))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(WORK/'worker.json',dict(process=process_identity(os.getpid()),started_at_utc=now()))
        try:
            activate()
            with (WORK/'activation-refresh.stdout').open('w') as out, (WORK/'activation-refresh.stderr').open('w') as err:
                result=subprocess.run(['.venv/bin/python','scripts/legal_mission_control.py','refresh'],cwd=ROOT,stdout=out,stderr=err)
            require(result.returncode==0,'Mission rejected replay recovery registration')
            save(WORK/'activation-refresh.json',dict(returncode=0,at_utc=now()))
            execution=live.MasterExecution(ROOT,live.PROGRAM,live.STATE)
            with patch.object(product_module,'execute',exact_execute), \
                    patch.object(reboot.BoundedCodexProvider,'_complete',checked_complete), \
                    patch.object(bounded_references,'prepare',reboot.exact_prepare):
                with (ROOT/live.LIVE/'supervisor.lock').open('a') as owner_lock:
                    fcntl.flock(owner_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    try:
                        value=live.acquire('gatecoin',live.configure().provider())
                        status='SUCCEEDED'
                        conclusion='Gatecoin preparation resumed from its interrupted phase and passed ordinary preparation checks.'
                    except Exception as exc:
                        status='FAILED'
                        value=dict(error=getattr(exc,'code',type(exc).__name__),reason=str(getattr(exc,'details',None) or exc))
                        conclusion='Gatecoin recovered replay segment failed: '+value['reason'][:500]
                    save(WORK/'node-evidence.json',value)
                    if value.get('error') in ('E_AUTHORITY','E_INTEGRITY'):
                        execution.record_continuation_veto(value['error'],value['reason'],[ref(ROOT,WORK/'node-evidence.json')],
                            ['acquire-gatecoin'])
                    node_result=dict(task_id='acquire-gatecoin',status=status,conclusion=conclusion,
                        next_action='Refresh and continue independent authorized work.',evidence=[ref(ROOT,WORK/'node-evidence.json')],
                        plan=str(REVIEW.relative_to(ROOT)),legal_acceptance=False)
                    save(WORK/'node-result.json',node_result)
                    finish_segment(execution,node_result)
                release_deferrals(execution)
                outcome=live.live()
            save(WORK/'live-result.json',outcome)
            record_mission('machine-reboot-replay-settled-2026-10-20',
                'Replay recovery settled; retain actual Gatecoin result and continue the recorded dependency frontier.',
                [ref(ROOT,WORK/'node-result.json'),ref(ROOT,WORK/'live-result.json')])
            with (WORK/'refresh.stdout').open('w') as out, (WORK/'refresh.stderr').open('w') as err:
                result=subprocess.run(['.venv/bin/python','scripts/legal_mission_control.py','refresh'],cwd=ROOT,stdout=out,stderr=err)
            save(WORK/'result.json',dict(ended_at_utc=now(),frontier=outcome,refresh_returncode=result.returncode,
                pending_call_recovered=(reboot.WORK/'recovered-response.json').exists(),integration_complete=False))
        except BaseException as exc:
            save(WORK/'worker-error.json',dict(at_utc=now(),error=type(exc).__name__,reason=str(exc)))
            raise


def arm():
    WORK.mkdir(parents=True,exist_ok=True)
    with (WORK/'arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not (WORK/'authorization.json').exists() and not (WORK/'armed.json').exists(),
                'Replay repair already armed or partially prepared')
        replayed=read(WORK/'replay.json')
        checks=read(WORK/'local-checks.json')
        require(replayed['verdict']=='PASS' and replayed['provider_calls']==0
                and replayed['pending_measurements_unchanged'] and checks['passed']
                and checks['implementation']==ref(ROOT,Path(__file__))
                and checks['tests_source']==ref(ROOT,ROOT/'tests/tooling/test_reboot_replay_repair.py')
                and checks['review']==ref(ROOT,REVIEW) and checks['replay']==ref(ROOT,WORK/'replay.json'),
                'Replay repair lacks passing reconstruction and controls')
        before=snapshot()
        save(WORK/'boot-observation.json',dict(current=ORIGINAL_BOOT_IDENTITY(),
            recorded=read(reboot.WORK/'authorization.json')['boot'],identity='kernel boot UUID',
            deadline_changed=False,retry_schedule_changed=False))
        save(WORK/'baseline.json',before)
        save(WORK/'authorization.json',dict(profile='exact-reboot-replay-repair.v1',
            user_instruction='machine restarted. recover and continue',maximum_recovery_segments=1,attempt=14,
            additional_owner_attempts=0,calls_added=0,deadline_extended=False,bindings=[ref(ROOT,p) for p in (
                Path(__file__),REVIEW,reboot.WORK/'authorization.json',WORK/'baseline.json',WORK/'replay.json',WORK/'local-checks.json')]))
        with (WORK/'supervisor.log').open('ab') as log:
            child=subprocess.Popen(['.venv-context/bin/python','scripts/legal_integration_reboot_repair.py','_worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        value=dict(armed_at_utc=now(),process=process_identity(child.pid),authority=ref(ROOT,WORK/'authorization.json'))
        save(WORK/'armed.json',value)
        print(json.dumps(value,indent=2))


if __name__ == '__main__':
    require(len(sys.argv)==2 and sys.argv[1] in ('replay','arm','_worker'), 'Use a fixed replay recovery action')
    {'replay':replay,'arm':arm,'_worker':worker}[sys.argv[1]]()
