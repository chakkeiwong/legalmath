"""Apply one explicit user timing instruction to an authenticated pending call.

Production source and request identities are unchanged. Runtime timing hooks
exist only inside this supervised process and are bound in authorization.json.
"""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_provider import (
    BoundedCodexProvider, CampaignAllowance, SERVICE_DELAYED_POLICY,
)
from legalmath.interpretation.search.providers import TerminalServiceFailure, transient_service_details
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive

WORK = ROOT / 'artifacts/legal-mission-control/2026-10-20/user-retry-schedule'
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
OLD = ROOT / 'artifacts/legal-mission-control/2026-10-19/synthesis-resolution'
CALLS = OLD / 'live/p14/product/calls'
PLAN = ROOT / 'docs/plans/legal-user-retry-schedule-2026-10-20.md'
PROGRAM = ROOT / 'docs/implementation/legal-mission-control/integration-master.json'
AUTH = WORK / 'authorization.json'
KEY = 'reduce-p14-2-2'
TARGET = '02ec07bf29736c9aaa3a1e3d7c7c83b72146850aaeac7b00820103df182ac75f'
SCHEMA = '8a20f2792b6a1d86ace5187b9b00933ab6877805f99c21ce19b466cde7111387'
SLOT = 3403
ORIGINAL_WAIT = CampaignAllowance.wait_service_recovery
ORIGINAL_COMPLETE = BoundedCodexProvider._complete


def utc():
    return datetime.now(timezone.utc)


def authority():
    value = read(AUTH)
    for item in value['bindings']:
        verify(ROOT, item)
    require(value['target'] == TARGET and value['schema'] == SCHEMA
        and value['original_slot'] == SLOT and value['maximum_early_probes'] == 3,
        'Changed user timing authority')
    return value


def terminal_receipt(root, manifest_path, request_hash, schema_hash):
    manifest = read(manifest_path)
    require(manifest['request_hash'] == request_hash and not manifest['complete_output_present'],
        'Only terminal no-output failures may be retried')
    for name, entry in manifest['files'].items():
        require(sha256((manifest_path.parent / name).read_bytes()).hexdigest() == entry['retained_sha256'],
            'Changed failure receipt')
    require(digest(read(manifest_path.parent / 'request.json')) == request_hash
        and digest(read(manifest_path.parent / 'schema.json')) == schema_hash, 'Changed retry request/schema')
    events = [json.loads(line) for line in (manifest_path.parent / 'events.jsonl').read_bytes().splitlines() if line.strip()]
    require(not any(e.get('type') == 'turn.completed' or e.get('item', {}).get('type') == 'agent_message'
        for e in events), 'Completed or partial model output cannot be resampled')
    details = transient_service_details(events, output_present=False, allow_terminal_499=True)
    require(details is not None and not details.get('unparsed_retry_after'), 'Unclassified failure or retry wait')
    return manifest, details


def requested_due(times, index, charge, details):
    require(0 <= index < len(times) == 3, 'Early timing allowance exhausted')
    delay = details.get('retry_after_seconds') or 0
    require(isinstance(delay, (int, float)) and math.isfinite(delay) and delay >= 0,
        'Invalid provider retry delay')
    requested = datetime.fromisoformat(times[index])
    scheduled = datetime.fromisoformat(charge['scheduled_at_utc'])
    require(requested.tzinfo is not None and scheduled.tzinfo is not None, 'Retry time lacks timezone')
    return max(requested, scheduled + timedelta(seconds=math.ceil(delay)))


def scheduled_wait(self, failure):
    if failure.request_hash != TARGET:
        return ORIGINAL_WAIT(self, failure)
    auth = authority()
    timeline_path = WORK / 'timing.json'
    timeline = read(timeline_path) if timeline_path.exists() else {'decisions': [], 'recovered': False}
    require(not timeline['recovered'], 'Successful request cannot be retried')
    if len(timeline['decisions']) >= auth['maximum_early_probes']:
        return ORIGINAL_WAIT(self, failure)
    require(self.expected == TARGET and self.expected_schema == SCHEMA
        and self.service_recovery_policy() == SERVICE_DELAYED_POLICY, 'Timing exception outside exact request')
    pointer, directory, _ = self.service_scope()
    require(pointer == auth['service_scope'], 'Service scope changed')
    ledger_path = directory / 'service-recovery.json'
    ledger = read(ledger_path)
    require(ledger['profile'] == SERVICE_DELAYED_POLICY['profile']
        and ledger['stage_hash'] == pointer['sha256']
        and ledger['maximum'] == SERVICE_DELAYED_POLICY['maximum_replacements']
        and 0 < len(ledger['charges']) <= ledger['maximum'], 'Recovery reserve changed')
    matches = [r for r in ledger['charges'] if r['failed_slot'] == failure.allowance_slot]
    require(len(matches) == 1, 'Missing or duplicate replacement reservation')
    charge = matches[0]
    require(charge['request_hash'] == TARGET and charge['schema_hash'] == SCHEMA,
        'Replacement reservation changed request')
    old_due = datetime.fromisoformat(charge['next_retry_at_utc'])
    scheduled = datetime.fromisoformat(charge['scheduled_at_utc'])
    require(old_due.tzinfo is not None and (old_due - scheduled).total_seconds() == charge['backoff_seconds']
        and charge['backoff_seconds'] >= SERVICE_DELAYED_POLICY['backoff_seconds'][ledger['charges'].index(charge)],
        'Historical recovery schedule changed')
    manifest_path = self.root / charge['evidence']
    manifest, details = terminal_receipt(self.root, manifest_path, TARGET, SCHEMA)
    require(manifest['allowance_slot'] == failure.allowance_slot, 'Receipt slot changed')
    require(not any(d['failed_slot'] == failure.allowance_slot for d in timeline['decisions']),
        'Timing decision already consumed; reconcile before restart')
    due = requested_due(auth['times_utc'], len(timeline['decisions']), charge, details)
    decision = dict(failed_slot=failure.allowance_slot, original_due_utc=old_due.isoformat(),
        effective_due_utc=due.isoformat(), authority=ref(ROOT, AUTH),
        charge=charge, started_at_utc=utc().isoformat(), worker=process_identity(os.getpid()))
    timeline['decisions'].append(decision)
    save(timeline_path, timeline)

    def unchanged():
        authority()
        require(read(ledger_path) == ledger
            and read(self.grant_path.with_name('current-stage.json')) == charge['stage']
            and sha256(manifest_path.read_bytes()).hexdigest() == charge['receipt_sha256'],
            'Retry evidence changed while waiting')
    while True:
        self.check()
        unchanged()
        remaining = (due - utc()).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(30, remaining))
    with (directory / 'service-circuit.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        unchanged()
        path = directory / 'service-circuit.json'
        circuit = read(path)
        require(circuit['stage_hash'] == pointer['sha256'] and circuit['open']
            and circuit['failed_slots'][-1] == failure.allowance_slot, 'Another owner changed the circuit')
        circuit.update(open=False, half_open_request_hash=TARGET, half_open_schema_hash=SCHEMA,
            half_open_reserved=False, resumed_after_slot=failure.allowance_slot,
            resumed_at_utc=utc().isoformat(), user_timing_authority=ref(ROOT, AUTH))
        save(path, circuit)
    decision['released_at_utc'] = utc().isoformat()
    save(timeline_path, timeline)


def resumed_complete(self, request, schema, settings):
    if digest(request) != TARGET:
        return ORIGINAL_COMPLETE(self, request, schema, settings)
    require(digest(schema) == SCHEMA, 'Target request has another schema')
    initial = WORK / 'initial-probe.json'
    require(not (WORK / 'recovered-response.json').exists(), 'Recovered request must not be sent again')
    if not initial.exists():
        save(initial, dict(worker=process_identity(os.getpid()), request_hash=TARGET, at_utc=utc().isoformat()))
        self.allowance.expected, self.allowance.expected_schema = TARGET, SCHEMA
        scheduled_wait(self.allowance, TerminalServiceFailure('Authenticated pending terminal overload',
            allowance_slot=SLOT, request_hash=TARGET))
    response = ORIGINAL_COMPLETE(self, request, schema, settings)
    save(WORK / 'recovered-response.json', dict(value=response.value, provenance=response.provenance,
        recovered_at_utc=utc().isoformat(), request_hash=TARGET, schema_hash=SCHEMA,
        ordinary_product_validation_pending=True))
    timeline = read(WORK / 'timing.json')
    timeline.update(recovered=True, recovered_at_utc=utc().isoformat(), unused_times_cancelled=True)
    save(WORK / 'timing.json', timeline)
    return response


def children(pid):
    found = set()
    for thread in Path(f'/proc/{pid}/task').iterdir():
        try:
            found.update(int(p) for p in (thread / 'children').read_text().split())
        except FileNotFoundError:
            pass
    return found


def snapshot():
    binding = read(BASE / 'current-binding.json')
    service = ROOT / Path(binding['phase_service_scope']['path']).parent
    recovery = read(service / 'service-recovery.json')
    pending = recovery['charges'][-1]
    require(pending['failed_slot'] == SLOT and pending['request_hash'] == TARGET
        and pending['schema_hash'] == SCHEMA, 'The pending failure has changed')
    terminal_receipt(ROOT, ROOT / pending['evidence'], TARGET, SCHEMA)
    ledger = read(BASE / 'live-calls.json')
    require(len(ledger['calls']) == SLOT and ledger['calls'][-1]['request_hash'] == TARGET,
        'A newer provider call exists')
    owner = read(BASE / 'execution-state.json')['tasks']['acquire-p14']
    require(owner['status'] == 'RUNNING' and owner['master_live'] and len(owner['attempts']) == 11,
        'Acquisition reservation changed')
    supervisor = read(OLD / 'execution/worker.json')['process']
    worker = owner['live_supervisor']
    require(worker == pending['worker'] and process_alive(supervisor) and process_alive(worker),
        'Expected waiting processes are not alive')
    require(children(supervisor['pid']) == {worker['pid']} and not children(worker['pid']),
        'A provider or unknown child is active')
    journal = read(CALLS / 'dispatch.json')
    require([k for k, row in journal['calls'].items() if row['status'] == 'RESERVED'] == [KEY]
        and all(row['status'] == 'VALIDATED' for k, row in journal['calls'].items() if k != KEY),
        'Pending dispatch is not unique')
    require(not (CALLS / KEY / 'result.json').exists() and not (CALLS / KEY / 'wire-response.json').exists(),
        'Pending product has output; review before resampling')
    wire = read(CALLS / KEY / 'reference-binding.json')
    require(digest(wire['request']) == TARGET and digest(wire['schema']) == SCHEMA,
        'Pending product does not match the failed wire request')
    return dict(supervisor=supervisor, worker=worker, charge=pending,
        service_scope=binding['phase_service_scope'], prior_calls=len(ledger['calls']),
        prior_validated=len(journal['calls']) - 1, journal=ref(ROOT, CALLS / 'dispatch.json'),
        state=ref(ROOT, BASE / 'execution-state.json'), ledger=ref(ROOT, BASE / 'live-calls.json'))


def prepare():
    require(not AUTH.exists(), 'Timing authorization already prepared')
    before = snapshot()
    WORK.mkdir(parents=True, exist_ok=True)
    save(WORK / 'baseline.json', before)
    require(read(WORK / 'local-checks.json')['passed'] is True, 'Local recovery controls have not passed')
    preflight = read(WORK / 'mission-preflight.json')
    require(preflight['check'] == 'PASS' and preflight['admitted_task'] == 'product-contribution',
        'Mission checks not retained')
    bindings = [ref(ROOT, p) for p in (Path(__file__), PLAN, PROGRAM, BASE / 'current-binding.json',
        BASE / 'live-grant.json', BASE / 'campaign-routing.toml', WORK / 'baseline.json',
        WORK / 'local-checks.json', WORK / 'mission-preflight.json')]
    save(AUTH, dict(profile='user-directed-exact-retry-timing.v1',
        user_instruction='try again.  and see if it works other wise try again at 2:37 and 3:37',
        target=TARGET, schema=SCHEMA, original_slot=SLOT, maximum_early_probes=3,
        times_utc=[utc().isoformat(), '2026-10-19T18:37:00+00:00', '2026-10-19T19:37:00+00:00'],
        timezone='Asia/Hong_Kong', service_scope=before['service_scope'], bindings=bindings,
        owner_attempts_added=0, calls_added=0, replacement_allowance_added=0, deadline_extended=False,
        original_recovery_ledger_preserved=True))
    return dict(prepared=True, baseline=before, authorization=ref(ROOT, AUTH))


def stop_and_reconcile():
    auth = authority()
    before = read(WORK / 'baseline.json')
    require(snapshot() == before, 'State advanced since preparation')
    require(not (WORK / 'stop.json').exists(), 'Restart already attempted; inspect receipt')
    # Stop the outer supervisor first so it cannot advance after the child exits.
    for identity in (before['supervisor'], before['worker']):
        require(process_alive(identity), 'Process identity changed before stop')
        os.kill(identity['pid'], signal.SIGTERM)
        until = time.monotonic() + 10
        while process_alive(identity) and time.monotonic() < until:
            time.sleep(0.1)
        require(not process_alive(identity), 'Waiting process did not stop')
    service = ROOT / Path(auth['service_scope']['path']).parent
    with ExitStack() as stack:
        for path in (service / 'service-worker.lock', CALLS / 'dispatch.lock'):
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ('journal', 'state', 'ledger'):
            verify(ROOT, before[name])
        terminal_receipt(ROOT, ROOT / before['charge']['evidence'], TARGET, SCHEMA)
        archive = WORK / 'before'
        archive.mkdir(exist_ok=False)
        for source in (CALLS / 'dispatch.json', BASE / 'execution-state.json',
                BASE / 'live-calls.json', service / 'service-recovery.json', service / 'service-circuit.json'):
            shutil.copy2(source, archive / source.name)
        save(WORK / 'stop.json', dict(at_utc=utc().isoformat(), original=before,
            provider_children=0, stopped=True, authority=ref(ROOT, AUTH)))
        journal = read(CALLS / 'dispatch.json')
        require(journal['calls'][KEY]['status'] == 'RESERVED', 'Reservation changed')
        (CALLS / KEY).rename(archive / KEY)
        del journal['calls'][KEY]
        save(CALLS / 'dispatch.json', journal)
        save(WORK / 'reconciled.json', dict(archived_pending=ref(ROOT, archive / KEY / 'reference-binding.json'),
            preserved_successes=len(journal['calls']), original_attempt=11,
            charges_preserved=True, ordinary_validation_required=True, at_utc=utc().isoformat()))


def worker():
    with (WORK / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(WORK / 'worker.json', dict(process=process_identity(os.getpid()), started_at_utc=utc().isoformat()))
        try:
            stop_and_reconcile()
            from scripts import legal_integration_phased_live as live
            with patch.object(CampaignAllowance, 'wait_service_recovery', scheduled_wait), \
                    patch.object(BoundedCodexProvider, '_complete', resumed_complete):
                outcome = live.live()
            save(WORK / 'live-result.json', outcome)
        except BaseException as exc:
            save(WORK / 'worker-error.json', dict(error=type(exc).__name__, reason=str(exc), at_utc=utc().isoformat()))
            raise
        finally:
            save(WORK / 'live-finished.json', dict(at_utc=utc().isoformat(), integration_complete=False))
        results = []
        for name, command in (
            ('refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
            ('verify', ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'verify']),
            ('status', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'status']),
        ):
            with (WORK / (name + '.stdout')).open('w') as out, (WORK / (name + '.stderr')).open('w') as err:
                result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err)
            results.append(dict(command=command, returncode=result.returncode))
            save(WORK / 'completion-steps.json', results)
        save(WORK / 'result.json', dict(steps=results, ended_at_utc=utc().isoformat(), integration_complete=False))


def arm():
    authority()
    with (WORK / 'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (WORK / 'armed.json').exists(), 'Already armed; never duplicate this restart')
        require(snapshot() == read(WORK / 'baseline.json'), 'Pending state changed')
        with (WORK / 'supervisor.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python', 'scripts/legal_integration_retry_schedule.py', '_worker'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result = dict(process=process_identity(child.pid), authorization=ref(ROOT, AUTH), armed_at_utc=utc().isoformat())
        require(result['process'] is not None, 'Restart worker failed to start')
        save(WORK / 'armed.json', result)
        return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'arm', '_worker'))
    action = parser.parse_args().action
    print(json.dumps({'prepare': prepare, 'arm': arm, '_worker': worker}[action](), indent=2))
