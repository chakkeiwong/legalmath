"""Fixed reconciliation of the ended slot 3485, then ordinary master continuation."""
from contextlib import ExitStack
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive
from scripts.legal_integration_master import BASE, PROGRAM, STATE
from legalmath.canonical import digest
from legalmath.interpretation.search import providers
from legalmath.interpretation.search.models import Settings
from legalmath.interpretation.assurance.phased.admission import admit
from legalmath.interpretation.assurance.bounded_provider import SERVICE_DELAYED_POLICY

WORK = Path(__file__).resolve().parent
SERVICE = ROOT/'artifacts/legal-mission-control/2026-10-16/delayed-service/service'
RECEIPT = ROOT/BASE/'provider-evidence/3485-b097f303873fc2f9'
TARGET = 'b097f303873fc2f9cff0f847160b2c0c461e8675a2a969937d8f51bf09ad409c'
SCHEMA = 'b1e5ece6bf519913981886396d0e36e56dd69952854d5dfa7d3d3b3c6346f6d1'
SLOT = 3485
ORIGINAL_CLASSIFY = providers.transient_service_details


def classify(events, *, output_present, allow_terminal_499=False):
    original = ORIGINAL_CLASSIFY(events,output_present=output_present,allow_terminal_499=allow_terminal_499)
    if original is not None:
        return original
    if output_present or any(e.get('type') == 'turn.completed'
            or e.get('item',{}).get('type') == 'agent_message' for e in events):
        return None
    errors = [str(e.get('message','')) for e in events if e.get('type') == 'error']
    failed = [str(e.get('error',{}).get('message','')) for e in events
        if e.get('type') == 'turn.failed' and isinstance(e.get('error'),dict)]
    if errors and failed and all(message.strip().lower() == 'request timed out' for message in errors + failed):
        return dict(message='request timed out', retry_after_seconds=None, unparsed_retry_after=False)
    return None


def terminal_receipt(folder, *, slot=SLOT, request_hash=TARGET, schema_hash=SCHEMA):
    manifest = read(folder/'manifest.json')
    require(manifest['allowance_slot'] == slot and manifest['request_hash'] == request_hash
        and manifest['complete_output_present'] is False, 'Wrong or completed timeout receipt')
    for name, metadata in manifest['files'].items():
        require(Path(name).name == name and sha256((folder/name).read_bytes()).hexdigest() == metadata['retained_sha256'],
            'Changed timeout receipt bytes: ' + name)
    request,schema = read(folder/'request.json'),read(folder/'schema.json')
    require(digest(request) == request_hash and digest(schema) == schema_hash, 'Changed exact probe input')
    events = [json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines() if line.strip()]
    require(classify(events,output_present=False) == dict(message='request timed out',retry_after_seconds=None,
        unparsed_retry_after=False), 'Receipt is not the reviewed ended timeout')
    return request,schema


def authority():
    value = read(WORK/'service-resume-authority.json')
    require(value['profile'] == 'exact-ended-timeout-resume.v1' and value['slot'] == SLOT
        and value['request_hash'] == TARGET and value['schema_hash'] == SCHEMA
        and value['calls_added'] == value['attempts_added'] == value['replacement_allowance_added'] == 0,
        'Changed service resumption scope')
    for pointer in value['bindings']:
        verify(ROOT,pointer)
    require(read(ROOT/PROGRAM).get('time_continuation') and read(WORK/'registration.json')['status'] == 'COMMITTED',
        'Time continuation not registered')
    before = read(WORK/'service-before.json')
    ledger = read(ROOT/BASE/'live-calls.json')
    require(ledger['maximum'] == before['ledger']['maximum'] == 8100
        and ledger['calls'][:len(before['ledger']['calls'])] == before['ledger']['calls'], 'Lost prior charges')
    recovery = read(SERVICE/'service-recovery.json')
    require(recovery['maximum'] == before['recovery']['maximum'] == 24
        and recovery['charges'][:len(before['recovery']['charges'])] == before['recovery']['charges'], 'Lost replacement history')
    terminal_receipt(RECEIPT)
    return value


def checkpoint_history():
    path = ROOT/'docs/implementation/legal-mission-control/mission.json'
    with path.with_name('mission.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        mission = read(path)
        if any(row['id'] == 'ended-timeout-resume-2026-10-21' for row in mission['history']):
            return
        reason = ('Reconcile ended no-output slot 3485 using one of four remaining service replacements; '
            'retain the two-hour wait, then continue installed capacity work and independent original answers. '
            'No owner attempt, repair limit, grant or historical result reset.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id='ended-timeout-resume-2026-10-21',task_id='product-contribution',
            kind='product_evaluation',outcome='no_advance',decision=reason,next_task='product-contribution',
            next_task_reason=reason,recorded_at_utc=datetime.now(timezone.utc).isoformat(),result_evidence=[
                ref(ROOT,WORK/name) for name in ('service-resume-authority.json','service-resume-review.md','service-reservation.json')]))
        save(path,mission)


def command(name, args):
    began = datetime.now(timezone.utc).isoformat()
    with (WORK/(name+'.stdout')).open('w') as out, (WORK/(name+'.stderr')).open('w') as err:
        child = subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=err)
        save(WORK/'service-active-command.json',dict(command=args,process=process_identity(child.pid)))
        code = child.wait()
    result = dict(command=args,exit_code=code,started_at_utc=began,ended_at_utc=datetime.now(timezone.utc).isoformat(),
        stdout=ref(ROOT,WORK/(name+'.stdout')),stderr=ref(ROOT,WORK/(name+'.stderr')))
    save(WORK/(name+'.json'),result)
    return result


def worker():
    from scripts import legal_integration_phased_live as live
    from scripts.legal_integration_campaign import provider
    with (WORK/'service-worker.lock').open('a') as worker_lock:
        fcntl.flock(worker_lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(WORK/'service-worker.json',dict(process=process_identity(os.getpid()),started_at_utc=datetime.now(timezone.utc).isoformat()))
        authority()
        require(not (WORK/'service-probe-started.json').exists() or (WORK/'service-probe-response.json').exists(),
            'Prior probe may have dispatched; reconcile its receipt before redispatch')
        local = None
        try:
            if not (WORK/'service-probe-response.json').exists():
                with ExitStack() as stack:
                    for path in (ROOT/live.LIVE/'supervisor.lock', ROOT/live.active_live(read(ROOT/PROGRAM))/'supervisor.lock',
                            SERVICE/'service-worker.lock'):
                        path.parent.mkdir(parents=True,exist_ok=True)
                        handle = stack.enter_context(path.open('a'))
                        fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
                    require(not any(row['status'] == 'RUNNING' for row in read(ROOT/STATE)['tasks'].values()), 'Master owner is active')
                    service = provider()
                    service.check()
                    request,schema = terminal_receipt(RECEIPT)
                    stage = admit(ROOT,BASE,WORK.relative_to(ROOT)/'service-live','exact-ended-timeout',1,owner='service-requalification')
                    allowance = service.allowance
                    allowance.expected, allowance.expected_schema = TARGET,SCHEMA
                    require(allowance.service_recovery_policy() == SERVICE_DELAYED_POLICY, 'Different retry policy')
                    failure = providers.TerminalServiceFailure('request timed out',allowance_slot=SLOT,request_hash=TARGET)
                    with patch.object(providers,'transient_service_details',classify):
                        ledger = read(SERVICE/'service-recovery.json')
                        if not any(row['failed_slot'] == SLOT for row in ledger['charges']):
                            circuit = read(SERVICE/'service-circuit.json')
                            before = read(WORK/'service-before.json')['circuit']
                            # A recorded failure without its reservation can be resumed; the failure itself is idempotent.
                            require(circuit == before or (circuit['open'] and circuit['failed_slots'] == before['failed_slots']+[SLOT]),
                                'Another process changed the circuit')
                            allowance.service_circuit(failure=failure)
                            allowance.reserve_service_recovery(failure)
                        charge = next(row for row in read(SERVICE/'service-recovery.json')['charges'] if row['failed_slot'] == SLOT)
                        require(charge['stage'] == stage and charge['request_hash'] == TARGET, 'Changed scheduled probe')
                        save(WORK/'service-reservation.json',dict(charge=charge,stage=stage,original_failure=ref(ROOT,RECEIPT/'manifest.json'),
                            calls_added=0,replacement_allowance_added=0))
                        checkpoint_history()
                        # Local command work does not use the service stage and can proceed during its wait.
                        out = stack.enter_context((WORK/'independent-run.stdout').open('w'))
                        err = stack.enter_context((WORK/'independent-run.stderr').open('w'))
                        local = subprocess.Popen(['.venv-context/bin/python','scripts/legal_integration_master.py','run'],cwd=ROOT,stdout=out,stderr=err)
                        save(WORK/'independent-worker.json',dict(process=process_identity(local.pid)))
                        allowance.wait_service_recovery(failure)
                        authority()
                        save(WORK/'service-probe-started.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),stage=stage))
                        # service-worker.lock is already held; use the ordinary checked internal completion.
                        response = service._complete(request,schema,Settings(timeout_seconds=300))
                        save(WORK/'service-probe-response.json',dict(value=response.value,provenance=response.provenance,
                            legal_acceptance=False,substituted_into_product=False))
                        if local is not None:
                            save(WORK/'independent-run.json',dict(exit_code=local.wait()))
                # The transport prerequisite is settled; retain normal product semantics and graph.
            with patch.object(providers,'transient_service_details',classify):
                save(WORK/'service-live-result.json',live.live())
        except BaseException as exc:
            save(WORK/'service-worker-error.json',dict(error=type(exc).__name__,reason=str(exc),at_utc=datetime.now(timezone.utc).isoformat()))
            raise
        finally:
            if local is not None and local.poll() is None:
                save(WORK/'independent-run.json',dict(exit_code=local.wait()))
            results = [command(name,args) for name,args in (
                ('service-refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
                ('service-verify',['.venv-context/bin/python','scripts/legal_integration_master.py','verify']))]
            save(WORK/'service-finished.json',dict(steps=results,ended_at_utc=datetime.now(timezone.utc).isoformat(),integration_complete=False))


def arm():
    with (WORK/'service-arm.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (WORK/'service-armed.json').exists():
            prior = read(WORK/'service-armed.json')
            require(process_alive(prior['process']), 'Prior service worker ended; inspect its retained outcome')
            return dict(already_running=True,**prior)
        checks = read(WORK/'service-local-result.json')
        require(checks['verdict'] == 'PASS' and checks['provider_calls'] == 0, 'Service adapter not locally checked')
        require(read(WORK/'mission-admission.json')['admission'] == 'ADMITTED_MASTER_WORK', 'Mission not admitted')
        terminal_receipt(RECEIPT)
        require(not any(row['status'] == 'RUNNING' for row in read(ROOT/STATE)['tasks'].values()), 'Master owner still active')
        before = dict(ledger=read(ROOT/BASE/'live-calls.json'),circuit=read(SERVICE/'service-circuit.json'),
            recovery=read(SERVICE/'service-recovery.json'))
        require(len(before['ledger']['calls']) == SLOT and len(before['recovery']['charges']) == 20
            and before['circuit'].get('half_open_reserved') is True
            and before['circuit'].get('half_open_request_hash') == TARGET, 'Changed stranded probe baseline')
        save(WORK/'service-before.json',before)
        save(WORK/'service-resume-authority.json',dict(profile='exact-ended-timeout-resume.v1',slot=SLOT,request_hash=TARGET,
            schema_hash=SCHEMA,calls_added=0,attempts_added=0,replacement_allowance_added=0,
            user_authority='Existing capacity execution and delayed service recovery; 72-hour time-only extension.',
            bindings=[ref(ROOT,p) for p in (Path(__file__),WORK/'service-resume-review.md',WORK/'service-local-result.json',
                WORK/'service-before.json',WORK/'mission-admission.json',ROOT/PROGRAM,ROOT/BASE/'current-binding.json',
                ROOT/BASE/'live-grant.json',ROOT/BASE/'campaign-routing.toml',RECEIPT/'manifest.json')]))
        with (WORK/'service-supervisor.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python',str(Path(__file__).relative_to(ROOT)),'worker'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        value = dict(process=process_identity(child.pid),armed_at_utc=datetime.now(timezone.utc).isoformat())
        require(value['process'] is not None,'Service worker failed to start')
        save(WORK/'service-armed.json',value)
        return value


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('arm','worker'))
    args = parser.parse_args()
    print(json.dumps({'arm':arm,'worker':worker}[args.action](),indent=2))
