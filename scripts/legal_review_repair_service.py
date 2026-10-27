"""Reconcile an authenticated ended failure, then resume ordinary work.

No response from this transport probe is substituted into a product answer.
The inherited recovery ledger and per-request counts remain cumulative.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json

from scripts.legal_mission_execution import read, save, ref, verify, require
from scripts.legal_integration_master import ROOT, BASE, PROGRAM, STATE, MasterExecution
from scripts.legal_review_repair import WORK, KEY
from legalmath.canonical import digest
from legalmath.interpretation.search import providers
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.assurance.phased.admission import admit
from legalmath.interpretation.assurance.bounded_provider import review_service_policy


def terminal_receipt(root, base, slot, request_hash, *, allow_terminal_499=False):
    folder = Path(root)/base/'provider-evidence'/f'{slot:04}-{request_hash[:16]}'
    manifest = read(folder/'manifest.json')
    require(manifest['allowance_slot'] == slot and manifest['request_hash'] == request_hash
        and manifest['complete_output_present'] is False, 'Wrong or completed probe receipt')
    require({'events.jsonl', 'request.json', 'schema.json'} <= set(manifest['files']),
        'Incomplete probe receipt')
    for name, metadata in manifest['files'].items():
        require(Path(name).name == name and sha256((folder/name).read_bytes()).hexdigest()
            == metadata['retained_sha256'], 'Changed probe receipt: '+name)
    request, schema = read(folder/'request.json'), read(folder/'schema.json')
    require(digest(request) == request_hash, 'Changed exact probe input')
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines() if line.strip()]
    require(not (folder/'result.json').exists() and 'result.json' not in manifest['files']
        and not providers.retry_output_present(events, allow_blank_messages=True),
        'Completed, partial or ambiguous model output cannot be retried by this adapter')
    details = providers.transient_service_details(events, output_present=False,
        allow_terminal_499=allow_terminal_499, allow_terminal_timeout=True)
    if 'termination.json' in manifest['files']:
        ended = read(folder/'termination.json')
        require(ended.get('reason') == 'LOCAL_DEADLINE' and ended.get('process_terminated') is True
            and ended.get('returncode') is not None and not ended.get('complete_output_present')
            and not ended.get('completed_turn_present')
            and (not any(e.get('type') in ('error','turn.failed') for e in events) or details is not None),
            'Timeout termination or service classification not established')
        failure = providers.TerminatedCallTimeout('Authenticated ended no-output deadline',
            allowance_slot=slot, request_hash=request_hash)
    else:
        require(details is not None and any(e.get('type') == 'turn.failed' for e in events),
            'No authenticated terminal service failure')
        failure = providers.TerminalServiceFailure(details['message'], allowance_slot=slot, request_hash=request_hash)
    return request, schema, failure, folder/'manifest.json'


def restore_deferred(execution, response):
    """Reopen only unstarted service deferrals; attempts are never replenished."""
    verify(execution.root, response)
    restored = []
    with execution.locked() as state:
        latest = {}
        for event in state['events']:
            if event.get('action') == 'PREREQUISITE_BLOCKED':
                latest[event['task_id']] = event
        for tid, row in state['tasks'].items():
            if row.get('service_checkpoint') and not row.get('service_resume'):
                from scripts.legal_review_service_checkpoint import checked
                checked(execution.root, tid, row)
                proof = read(execution.root / response['path'])
                require(proof.get('legal_acceptance') is False and proof.get('substituted_into_product') is False
                    and proof.get('provenance', {}).get('response_hash') == digest(proof.get('value')),
                    'Paused owner needs saved service response evidence')
                row['service_resume'] = response
                execution.event(state, tid, 'SERVICE_CHECKPOINT_READY', evidence=[response],
                    attempt=len(row['attempts']), new_attempt=False)
                restored.append(tid)
                continue
            if row.get('dispatch_status') != 'NOT_DISPATCHED' or row['status'] != 'BLOCKED':
                continue
            event = latest.get(tid, {})
            if event.get('shared_scope') != ['provider-service']:
                continue
            require(len(row['attempts']) < execution.tasks[tid]['maximum_attempts'],
                'Deferred owner has no unspent attempt')
            row.update(status='PENDING', reason='Exact service probe succeeded; original owner remains unstarted')
            for name in ('dispatch_status', 'prerequisite_evidence', 'shared_scope'):
                row.pop(name, None)
            execution.event(state, tid, 'SERVICE_PREREQUISITE_RESTORED', evidence=[response], attempt_consumed=False)
            restored.append(tid)
    return restored


def reconcile_completed_probe(execution, folder, circuit, scope):
    """Finish a saved successful probe without making another provider call."""
    path = folder/'response.json'
    require(path.exists(), 'Closed recovery circuit lacks its saved probe response; reconcile receipt')
    response = read(path)
    scheduled = read(folder/'scheduled.json')
    started = read(folder/'started.json')
    charge = scheduled['charge']
    require(not circuit['open'] and not circuit.get('half_open_request_hash')
        and response['service_scope'] == scope
        and response['failed_slot'] == int(folder.name) == charge['failed_slot']
        and started['stage'] == charge['stage']
        and response['provenance']['request_hash'] == charge['request_hash']
        and response['provenance']['response_hash'] == digest(response['value'])
        and response['provenance']['allowance_slot'] > circuit['failed_slots'][-1]
        and response['legal_acceptance'] is False and response['substituted_into_product'] is False,
        'Saved probe response does not establish this recovery')
    verify(execution.root, scheduled['original_failure'])
    restored = restore_deferred(execution, ref(execution.root, path))
    return dict(required=False, recovered=True, restored=restored,
        evidence=ref(execution.root, path), legal_acceptance=False)


def probe_settings(service,request):
    from legalmath.interpretation.assurance.phased.downstream_input import input_byte_limit
    from legalmath.interpretation.assurance.phased.capacity_policy import output_bytes
    # Match the ordinary BoundDispatch contract, including reviewed larger output.
    return Settings(timeout_seconds=300).model_copy(update={
        'max_input_bytes':input_byte_limit(request,service.limits),
        'max_output_bytes':output_bytes(request,service.limits)})


def resume_undispatched_probe(service,folder,circuit,binding):
    """Caller owns supervisor/service locks. Never repeat a reserved call."""
    scheduled,started=read(folder/'scheduled.json'),read(folder/'started.json')
    charge=scheduled['charge'];slot=charge['failed_slot']
    require(not circuit['open'] and circuit.get('half_open_reserved') is False
        and circuit.get('half_open_request_hash')==charge['request_hash']
        and circuit.get('half_open_schema_hash')==charge['schema_hash']
        and started['stage']==charge['stage'],
        'Scheduled probe is not safely undispatched')
    verify(ROOT,started['ledger_before']);verify(ROOT,scheduled['original_failure'])
    require(read(ROOT/BASE/'live-calls.json')==read(ROOT/started['ledger_before']['path']),
        'Probe may have dispatched; retain and diagnose')
    from scripts.legal_mission_execution import process_alive
    repair=binding['repaired_retry_continuation']['probe_capacity_repair']
    require(charge['stage']==repair['prior_stage'] and not process_alive(charge['worker']),
        'Original probe worker is active or stage changed')
    verify(ROOT,repair['prior_stage']);verify(ROOT,repair['prior_binding'])
    verify(ROOT,repair['prior_calls'])
    require(ref(ROOT,BASE/'live-calls.json')['sha256']==repair['prior_calls']['sha256'],
        'Charged probe cannot be adopted')
    stage_pointer=read(ROOT/BASE/'current-stage.json');verify(ROOT,stage_pointer)
    previous=read(ROOT/repair['prior_stage']['path'])
    current=read(ROOT/stage_pointer['path'])
    require(previous['binding_hash']==digest(read(ROOT/repair['prior_binding']['path']))
        and stage_pointer['path']==repair['successor_stage_path']
        and current=={**previous,'binding_hash':digest(binding)},
        'Probe stage adoption changed capacity or authority')
    ledger=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-recovery.json')
    require(charge in ledger['charges'],'Lost scheduled probe reservation')
    request,schema,_,manifest=terminal_receipt(ROOT,BASE,slot,charge['request_hash'],
        allow_terminal_499=bool(binding.get('terminal_cancellation_recovery')))
    require(ref(ROOT,manifest)==scheduled['original_failure'] and digest(schema)==charge['schema_hash'],
        'Changed scheduled probe payload')
    settings=probe_settings(service,request)
    save(folder/'resumed-before-dispatch.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
        stage=stage_pointer,prior_stage=charge['stage'],ledger_before=started['ledger_before'],settings=settings.model_dump(),
        reason='Retained scheduled request never reserved a provider call; correct capacity selection'))
    response=service._complete(request,schema,settings)
    save(folder/'response.json',dict(value=response.value,provenance=response.provenance,
        failed_slot=slot,service_scope=binding['phase_service_scope'],
        legal_acceptance=False,substituted_into_product=False))
    execution=MasterExecution(ROOT,PROGRAM,STATE)
    restored=restore_deferred(execution,ref(ROOT,folder/'response.json'));execution.sync_mission()
    return dict(required=True,recovered=True,restored=restored,evidence=ref(ROOT,folder/'response.json'),legal_acceptance=False)


def recover():
    from scripts import legal_integration_phased_live as live
    from scripts.legal_integration_campaign import provider
    program = read(ROOT/PROGRAM)
    require(program.get(KEY), 'Source-review repair is not registered')
    deployment = program[KEY].get('deployment')
    successor = program.get('repaired_retry_continuation')
    service_work = Path(successor['work']) if successor else (Path(deployment['runtime']).parent if deployment else WORK)
    service_policy = successor['service_policy'] if successor else program[KEY]['service_policy']
    binding = read(ROOT/BASE/'current-binding.json')
    require(binding['program'] == ref(ROOT, PROGRAM) and binding['execution_review'] == program[KEY]['review']
        and review_service_policy(binding['service_recovery_policy'])
        and binding['service_recovery_policy'] == service_policy,
        'Wrong repair recovery authority')
    verify(ROOT, binding['phase_service_scope'])
    service_dir = ROOT/Path(binding['phase_service_scope']['path']).parent
    with ExitStack() as stack:
        for path in dict.fromkeys((ROOT/live.active_live(program)/'supervisor.lock',
                ROOT/live.LIVE/'supervisor.lock', service_dir/'service-worker.lock')):
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(ROOT/STATE)
        running = [r for r in state['tasks'].values() if r['status'] == 'RUNNING']
        if running and program[KEY].get('timeout_correction'):
            from scripts.legal_review_timeout_correction import verify_orphans
            verify_orphans(ROOT, state, ROOT/live.active_live(program))
        else:
            require(not running, 'A product owner is active; do not probe beside it')
        circuit = read(service_dir/'service-circuit.json')
        require(circuit['stage_hash'] == binding['phase_service_scope']['sha256'], 'Wrong recovery circuit')
        if not circuit['open'] and circuit.get('half_open_request_hash'):
            require(successor and successor.get('probe_capacity_repair'),
                'Unreviewed half-open probe continuation')
            slot=circuit['failed_slots'][-1]
            return resume_undispatched_probe(provider(),ROOT/service_work/'service-resumption'/str(slot),circuit,binding)
        if not circuit['open']:
            require(not circuit.get('half_open_request_hash'),
                'Half-open probe needs reconciliation before unrelated dispatch')
            # A crash after saving the response must not leave unstarted
            # owners blocked. The latest failed slot identifies this probe.
            if circuit.get('failed_slots'):
                latest = circuit['failed_slots'][-1]
                candidates = sorted((ROOT/service_work/'service-resumption').glob('*/response.json'),
                    key=lambda p: int(p.parent.name), reverse=True)
                for path in candidates:
                    folder = path.parent
                    if int(folder.name) <= latest < read(path)['provenance']['allowance_slot']:
                        execution = MasterExecution(ROOT, PROGRAM, STATE)
                        result = reconcile_completed_probe(execution, folder, circuit, binding['phase_service_scope'])
                        if result['restored']:
                            execution.sync_mission()
                        return result
                for started in (ROOT/service_work/'service-resumption').glob('*/started.json'):
                    require((started.parent/'response.json').exists()
                        or (started.parent/'ended-failure.json').exists(),
                        'Ended probe lacks a reconciled response; inspect retained provider receipt')
            return dict(required=False, recovered=True)
        require(not circuit.get('half_open_reserved'), 'Probe dispatch is uncertain')
        ledger = read(ROOT/BASE/'live-calls.json')
        slot = circuit['failed_slots'][-1]
        require(0 < slot <= len(ledger['calls']), 'Failure lacks its charged request')
        request_hash = ledger['calls'][slot-1]['request_hash']
        request, schema, failure, manifest = terminal_receipt(ROOT, BASE, slot, request_hash,
            allow_terminal_499=bool(binding.get('terminal_cancellation_recovery')))
        folder = ROOT/service_work/'service-resumption'/str(slot)
        require(not (folder/'started.json').exists() or (folder/'response.json').exists()
            or (folder/'ended-failure.json').exists(),
            'Previous probe may have dispatched; reconcile before redispatch')
        service = provider()
        service.check()
        stage = admit(ROOT, BASE, service_work/'service-live', 'exact-ended-'+str(slot), 1,
            owner='service-requalification')
        allowance = service.allowance
        allowance.expected, allowance.expected_schema = request_hash, digest(schema)
        require(allowance.service_recovery_policy() == binding['service_recovery_policy'], 'Changed recovery policy')
        charges = read(service_dir/'service-recovery.json')['charges']
        existing = next((r for r in charges if r['failed_slot'] == slot), None)
        if existing is None:
            allowance.service_circuit(failure=failure)
            allowance.reserve_service_recovery(failure)
            existing = read(service_dir/'service-recovery.json')['charges'][-1]
        require(existing['stage'] == stage and existing['request_hash'] == request_hash,
            'Changed scheduled exact probe')
        save(folder/'scheduled.json', dict(charge=existing, original_failure=ref(ROOT, manifest),
            legal_acceptance=False, substituted_into_product=False))
        allowance.wait_service_recovery(failure)
        service.check()
        save(folder/'started.json', dict(at_utc=datetime.now(timezone.utc).isoformat(), stage=stage,
            ledger_before=ref(ROOT, BASE/'live-calls.json')))
        try:
            # The ordinary provider owns its finite retries. Its worker lock
            # is held here; do not reacquire it recursively in complete().
            response = service._complete(request, schema, probe_settings(service,request))
            save(folder/'response.json', dict(value=response.value, provenance=response.provenance,
                failed_slot=slot, service_scope=binding['phase_service_scope'],
                legal_acceptance=False, substituted_into_product=False))
        except BaseException as exc:
            after = read(service_dir/'service-circuit.json')
            if after['open'] and after['failed_slots'][-1] > slot:
                last = after['failed_slots'][-1]
                charged = read(ROOT/BASE/'live-calls.json')['calls'][last-1]
                _, _, _, ended = terminal_receipt(ROOT, BASE, last, charged['request_hash'],
                    allow_terminal_499=allowance.terminal_cancellation_enabled())
                save(folder/'ended-failure.json', dict(error=type(exc).__name__,
                    reason=str(getattr(exc, 'details', None) or exc), receipt=ref(ROOT, ended)))
            raise
        execution = MasterExecution(ROOT, PROGRAM, STATE)
        restored = restore_deferred(execution, ref(ROOT, folder/'response.json'))
        execution.sync_mission()
        return dict(required=True, recovered=True, exact_failed_slot=slot, restored=restored,
            evidence=ref(ROOT, folder/'response.json'), legal_acceptance=False)
