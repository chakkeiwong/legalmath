"""Resume the authenticated Gatecoin wait after the 20 October machine reboot.

This adapter preserves the production classes, sources, attempts and budgets.
It is deliberately one-shot; an interrupted reconciliation requires review.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from legalmath.canonical import digest
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.bounded_provider import BoundedCodexProvider
from legalmath.interpretation.assurance.phased.synthesis_recovery import historical_request
from legalmath.interpretation.search.providers import TerminalServiceFailure
from scripts.legal_integration_retry_schedule import terminal_receipt
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive

BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
OLD = ROOT / 'artifacts/legal-mission-control/2026-10-19/synthesis-resolution'
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-20/reboot-recovery'
PLAN = ROOT / 'docs/plans/legal-user-retry-schedule-2026-10-20.md'
PROGRAM = ROOT / 'docs/implementation/legal-mission-control/integration-master.json'
CALLS = OLD / 'live/gatecoin/product/calls'
KEY = 'reduce-gatecoin-5-0'
TARGET = '5f314faaa345c9318c75cbf867d18fcce493dcf0c447c5c3a4b22c35a7b1fcb7'
SCHEMA = '189c33943896f0229aef032fc5c3e5563c066291e3ae49bf2318982f662facdf'
SLOT = 3436
ORIGINAL_COMPLETE = BoundedCodexProvider._complete
ORIGINAL_PREPARE = bounded_references.prepare


def now():
    return datetime.now(timezone.utc).isoformat()


def boot_identity():
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    started = next(int(line.split()[1]) for line in Path('/proc/stat').read_text().splitlines()
        if line.startswith('btime '))
    return {'id': boot, 'started_at_utc': datetime.fromtimestamp(started, timezone.utc).isoformat()}


def authority():
    value = read(WORK / 'authorization.json')
    for item in value['bindings']:
        verify(ROOT, item)
    require(value['boot'] == boot_identity(), 'Another reboot requires reviewed recovery')
    require(value['target'] == TARGET and value['schema'] == SCHEMA and value['slot'] == SLOT,
        'Recovery target changed')
    return value


def authenticated_wire(directory):
    wire = read(directory / 'reference-binding.json')
    request = historical_request(wire, reviewed=True)
    require(request == read(directory / 'request.json')
        and wire['original_schema'] == read(directory / 'schema.json'), 'Decoded pending request changed')
    require(digest(wire['request']) == TARGET and digest(wire['schema']) == SCHEMA,
        'Pending wire request changed')
    require(not any((directory / name).exists() for name in
        ('result.json', 'wire-response.json', 'raw.json')), 'Pending request already has output')
    return wire


def snapshot():
    binding = read(BASE / 'current-binding.json')
    service = ROOT / Path(binding['phase_service_scope']['path']).parent
    recovery = read(service / 'service-recovery.json')
    charge = recovery['charges'][-1]
    require(charge['failed_slot'] == SLOT and charge['request_hash'] == TARGET
        and charge['schema_hash'] == SCHEMA, 'A different request is pending')
    boot = boot_identity()
    require(datetime.fromisoformat(boot['started_at_utc']) > datetime.fromisoformat(charge['scheduled_at_utc']),
        'This recovery requires a boot after the retained service failure')
    state = read(BASE / 'execution-state.json')
    owner = state['tasks']['acquire-gatecoin']
    supervisor = read(OLD / 'execution/worker.json')['process']
    require(owner['status'] == 'RUNNING' and owner.get('master_live') and len(owner['attempts']) == 14
        and owner['live_supervisor'] == charge['worker'], 'Pending owner reservation changed')
    require(not process_alive(supervisor) and not process_alive(charge['worker']), 'Original worker is still alive')
    require([tid for tid, row in state['tasks'].items() if row['status'] == 'RUNNING'] == ['acquire-gatecoin'],
        'Another running owner requires reconciliation')
    ledger = read(BASE / 'live-calls.json')
    require(len(ledger['calls']) == SLOT and ledger['calls'][-1]['request_hash'] == TARGET,
        'Call ledger advanced since failure')
    verify(ROOT, charge['stage'])
    require(read(BASE / 'current-stage.json') == charge['stage'], 'Pending stage changed')
    wire = authenticated_wire(CALLS / KEY)
    slots = [i for i, row in enumerate(ledger['calls'], 1)
        if row.get('stage_hash') == charge['stage']['sha256'] and row['request_hash'] == TARGET]
    require(slots == [3435, SLOT], 'Unexpected pending request charge history')
    for slot in slots:
        path = BASE / 'provider-evidence' / f'{slot:04}-{TARGET[:16]}' / 'manifest.json'
        manifest, _ = terminal_receipt(ROOT, path, TARGET, SCHEMA)
        require(manifest['allowance_slot'] == slot, 'Wrong failure receipt slot')
    require(ref(ROOT, ROOT / charge['evidence'])['sha256'] == charge['receipt_sha256'],
        'Failure receipt changed')
    journal = read(CALLS / 'dispatch.json')
    require([key for key, row in journal['calls'].items() if row['status'] == 'RESERVED'] == [KEY]
        and all(row['status'] == 'VALIDATED' for key, row in journal['calls'].items() if key != KEY),
        'Pending dispatch is not unique or contains another failure')
    circuit = read(service / 'service-circuit.json')
    require(circuit['open'] and circuit['failed_slots'][-1] == SLOT
        and circuit['stage_hash'] == binding['phase_service_scope']['sha256'], 'Pending circuit changed')
    return dict(boot=boot, owner=owner['live_supervisor'], supervisor=supervisor, charge=charge,
        prior_calls=len(ledger['calls']), preserved_successes=len(journal['calls']) - 1,
        original_request_hash=digest(wire['original_request']),
        service_scope=binding['phase_service_scope'], references=[ref(ROOT, path) for path in (
            BASE / 'execution-state.json', BASE / 'live-calls.json', BASE / 'current-stage.json',
            CALLS / 'dispatch.json', CALLS / KEY / 'reference-binding.json',
            service / 'service-recovery.json', service / 'service-circuit.json')])


def reconcile():
    auth = authority()
    before = read(WORK / 'baseline.json')
    require(snapshot() == before, 'State changed after recovery was prepared')
    require(not (WORK / 'before').exists(), 'Reconciliation already started; review its result')
    service = ROOT / Path(before['service_scope']['path']).parent
    from scripts.legal_integration_phased_live import LIVE
    with ExitStack() as stack:
        for path in (ROOT / LIVE / 'supervisor.lock', service / 'service-worker.lock',
                CALLS / 'dispatch.lock', BASE / 'execution-state.lock'):
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(snapshot() == before, 'State changed while acquiring recovery locks')
        archive = WORK / 'before'
        archive.mkdir()
        for reference in before['references']:
            source = ROOT / reference['path']
            shutil.copy2(source, archive / source.name)
        journal = read(CALLS / 'dispatch.json')
        (CALLS / KEY).rename(archive / KEY)
        del journal['calls'][KEY]
        save(CALLS / 'dispatch.json', journal)
        save(WORK / 'reconciled.json', dict(at_utc=now(), authority=ref(ROOT, WORK / 'authorization.json'),
            preserved_successes=len(journal['calls']), original_attempt=14, charges_preserved=True,
            due_utc=before['charge']['next_retry_at_utc'], original_recovery_ledger_preserved=True))


def resume_complete(self, request, schema, settings):
    if digest(request) != TARGET:
        require((WORK / 'pending-call-settled.json').exists(), 'Another request preceded the pending recovery')
        return ORIGINAL_COMPLETE(self, request, schema, settings)
    authority()
    require(digest(schema) == SCHEMA, 'Changed pending schema')
    require(not (WORK / 'resume-started.json').exists(), 'Pending retry already started; inspect its receipt')
    save(WORK / 'resume-started.json', dict(at_utc=now(), worker=process_identity(os.getpid()),
        due_utc=read(WORK / 'baseline.json')['charge']['next_retry_at_utc']))
    self.allowance.expected, self.allowance.expected_schema = TARGET, SCHEMA
    self.allowance.wait_service_recovery(TerminalServiceFailure('Resume authenticated terminal service wait',
        allowance_slot=SLOT, request_hash=TARGET))
    try:
        response = ORIGINAL_COMPLETE(self, request, schema, settings)
    finally:
        save(WORK / 'pending-call-settled.json', dict(at_utc=now(),
            note='Dispatch ended; ordinary circuit, result and authority checks govern independent work.'))
    save(WORK / 'recovered-response.json', dict(at_utc=now(), request_hash=TARGET,
        provenance=response.provenance, ordinary_product_validation_pending=True))
    return response


def exact_prepare(request, schema):
    original = read(WORK / 'before' / KEY / 'request.json')
    if request != original:
        return ORIGINAL_PREPARE(request, schema)
    saved = authenticated_wire(WORK / 'before' / KEY)
    require(schema == saved['original_schema'], 'Pending decoded schema changed')
    # historical_request uses the production constructor and proves all decoder
    # maps and content equal; only input-side alias numbering may be permuted.
    return deepcopy(saved)


def record_checkpoint():
    mission_path = ROOT / 'docs/implementation/legal-mission-control/mission.json'
    with mission_path.with_name('mission.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        mission = read(mission_path)
        identity = 'machine-reboot-recovery-2026-10-20'
        require(not any(row['id'] == identity for row in mission['history']), 'Recovery history already exists')
        reason = ('Resume Gatecoin attempt 14 from its authenticated no-output HTTP 502 reservation; '
            'then continue independent P10/evidence and eligible answer/tool branches. '
            'P14 candidate capacity and corpus qualification remain open. No allowance or deadline reset.')
        mission['next_task_reason'] = reason
        mission['history'].append(dict(id=identity, task_id='product-contribution', kind='product_evaluation',
            outcome='no_advance', recorded_at_utc=now(), decision='Recovered machine-restart state; legal acceptance unchanged.',
            next_task='product-contribution', next_task_reason=reason, result_evidence=[
                ref(ROOT, WORK / name) for name in ('authorization.json', 'baseline.json', 'reconciled.json')]))
        save(mission_path, mission)


def worker():
    with ExitStack() as stack:
        for path in (WORK / 'worker.lock', OLD / 'execution/worker.lock'):
            handle = stack.enter_context(path.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(WORK / 'worker.json', dict(process=process_identity(os.getpid()), boot=boot_identity(), started_at_utc=now()))
        try:
            reconcile()
            record_checkpoint()
            with (WORK / 'checkpoint-refresh.stdout').open('w') as out, (WORK / 'checkpoint-refresh.stderr').open('w') as err:
                code = subprocess.run(['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh'],
                    cwd=ROOT, stdout=out, stderr=err).returncode
            save(WORK / 'checkpoint-refresh.json', dict(returncode=code, finished_at_utc=now()))
            require(code == 0, 'Mission rejected reboot checkpoint')
            from scripts import legal_integration_phased_live as live
            with patch.object(BoundedCodexProvider, '_complete', resume_complete), \
                    patch.object(bounded_references, 'prepare', exact_prepare):
                campaign = live.configure()
                execution = live.MasterExecution(ROOT, live.PROGRAM, live.STATE)
                with (ROOT / live.LIVE / 'supervisor.lock').open('a') as owner_lock:
                    fcntl.flock(owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    service = campaign.provider()
                    campaign.complete_node(execution, 'acquire-gatecoin', lambda: live.acquire('gatecoin', service))
                # The reserved owner precedes new work; then the ordinary graph
                # advances its independent original branches and attempts.
                outcome = live.live()
            save(WORK / 'live-result.json', outcome)
            for label, command in (
                ('refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
                ('status', ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'status']),
            ):
                with (WORK / (label + '.stdout')).open('w') as out, (WORK / (label + '.stderr')).open('w') as err:
                    result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err)
                save(WORK / (label + '.json'), dict(command=command, returncode=result.returncode))
            save(WORK / 'result.json', dict(ended_at_utc=now(), integration_complete=False,
                frontier=outcome, recovered_request=(WORK / 'recovered-response.json').exists()))
        except BaseException as exc:
            save(WORK / 'worker-error.json', dict(at_utc=now(), error=type(exc).__name__, reason=str(exc)))
            raise


def arm():
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK / 'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (WORK / 'armed.json').exists() and not (WORK / 'authorization.json').exists(),
            'Recovery already armed or prepared; inspect its receipts')
        checks = read(WORK / 'local-checks.json')
        require(checks['passed'] and read(WORK / 'preflight.json')['admission'] == 'ADMITTED_MASTER_WORK',
            'Recovery lacks passing local controls or mission admission')
        before = snapshot()
        save(WORK / 'baseline.json', before)
        save(WORK / 'authorization.json', dict(profile='exact-reboot-resume.v1', user_instruction='machine restarted. recover and continue',
            target=TARGET, schema=SCHEMA, slot=SLOT, boot=before['boot'], calls_added=0, attempts_added=0,
            deadline_extended=False, recovery_reserve_added=0, bindings=[ref(ROOT, path) for path in (
                Path(__file__), ROOT / 'scripts/legal_integration_retry_schedule.py', PLAN, PROGRAM,
                BASE / 'current-binding.json', BASE / 'live-grant.json', BASE / 'campaign-routing.toml',
                WORK / 'baseline.json', WORK / 'local-checks.json', WORK / 'preflight.json')]))
        with (WORK / 'supervisor.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python', 'scripts/legal_integration_reboot_resume.py', '_worker'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result = dict(process=process_identity(child.pid), boot=before['boot'], armed_at_utc=now(),
            authorization=ref(ROOT, WORK / 'authorization.json'))
        require(result['process'] is not None, 'Recovery worker did not start')
        save(WORK / 'armed.json', result)
        return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'arm', '_worker'))
    action = parser.parse_args().action
    print(json.dumps({'inspect': snapshot, 'arm': arm, '_worker': worker}[action](), indent=2))
