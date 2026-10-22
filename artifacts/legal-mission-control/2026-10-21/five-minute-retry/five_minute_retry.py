"""User-directed five-minute timing, preserving the current master and ledger."""
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import fcntl
import importlib.util
import json
import math
import os
import signal
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import read, save, ref, verify, require, process_identity, process_alive
from legalmath.canonical import digest
from legalmath.interpretation.assurance import bounded_provider as bp
from legalmath.interpretation.search import providers
from legalmath.interpretation.search.models import Settings

WORK = Path(__file__).resolve().parent
OLD = WORK.parent / 'capacity-time-continuation'
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
PROGRAM = ROOT / 'docs/implementation/legal-mission-control/integration-master.json'
PLAN = ROOT / 'docs/plans/legal-five-minute-retry-2026-10-21.md'
AUTH = WORK / 'authority.json'
USER = 'I think waiting 5 minutes to retry is good enough.  If Astra is working working Sol should be'
spec = importlib.util.spec_from_file_location('retained_service_resume', OLD / 'service_resume.py')
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)
ORIGINAL_DELAY = bp.recovery_delay


def utc():
    return datetime.now(timezone.utc)


def retry_delay(policy, used, details):
    if policy != bp.SERVICE_DELAYED_POLICY:
        return ORIGINAL_DELAY(policy, used, details)
    require(0 <= used < policy['maximum_replacements'], 'Replacement allowance exhausted')
    require(not details.get('unparsed_retry_after'), 'Unparsed server retry delay')
    requested = details.get('retry_after_seconds') or 0
    require(isinstance(requested, (float, int)) and not isinstance(requested, bool)
        and math.isfinite(requested) and requested >= 0, 'Invalid server retry delay')
    return math.ceil(max(300, requested))


def authority():
    value = read(AUTH)
    require(value['profile'] == 'user-five-minute-retry.v1' and value['user_instruction'] == USER
        and value['interval_seconds'] == 300 and value['calls_added'] == 0
        and value['attempts_added'] == 0 and value['replacements_added'] == 0, 'Changed timing authority')
    for pointer in value['bindings']:
        verify(ROOT, pointer)
    before = read(WORK / 'baseline.json')
    ledger = read(BASE / 'live-calls.json')
    recovery = read(resume.SERVICE / 'service-recovery.json')
    require(ledger['maximum'] == before['ledger']['maximum'] == 8100
        and ledger['calls'][:len(before['ledger']['calls'])] == before['ledger']['calls'], 'Lost original call charges')
    require(recovery['maximum'] == before['recovery']['maximum'] == 24
        and recovery['charges'][:len(before['recovery']['charges'])] == before['recovery']['charges'], 'Lost replacement charges')
    return value


def ended_receipt(allowance, failure, charge):
    path = allowance.root / charge['evidence']
    manifest = read(path)
    require(sha256(path.read_bytes()).hexdigest() == charge['receipt_sha256']
        and manifest['allowance_slot'] == failure.allowance_slot
        and manifest['request_hash'] == failure.request_hash == allowance.expected
        and not manifest['complete_output_present'], 'Changed or completed failure receipt')
    for name, metadata in manifest['files'].items():
        require(Path(name).name == name and sha256((path.parent / name).read_bytes()).hexdigest()
            == metadata['retained_sha256'], 'Changed failure bytes')
    require(digest(read(path.parent / 'request.json')) == allowance.expected
        and digest(read(path.parent / 'schema.json')) == allowance.expected_schema, 'Changed retry inputs')
    events = [json.loads(line) for line in (path.parent / 'events.jsonl').read_bytes().splitlines() if line.strip()]
    require(not any(e.get('type') == 'turn.completed' or e.get('item', {}).get('type') == 'agent_message'
        for e in events), 'Completed or partial output cannot be retried')
    details = resume.classify(events, output_present=False,
        allow_terminal_499=allowance.terminal_cancellation_enabled())
    if isinstance(failure, providers.TerminatedCallTimeout):
        require('termination.json' in manifest['files'], 'Missing timeout termination receipt')
        ended = read(path.parent / 'termination.json')
        require(ended.get('reason') == 'LOCAL_DEADLINE' and ended.get('process_terminated') is True
            and ended.get('returncode') is not None and not ended.get('complete_output_present')
            and not ended.get('completed_turn_present'), 'Uncertain timeout termination')
        require(not any(e.get('type') == 'error' for e in events) or details is not None,
            'Timeout contains a nonservice failure')
        details = details or {}
    require(details is not None, 'Failure is not an eligible transient failure')
    return details


def five_minute_wait(self, failure):
    auth = authority()
    require(self.service_recovery_policy() == bp.SERVICE_DELAYED_POLICY, 'Different service policy')
    pointer, directory, _ = self.service_scope()
    require(pointer == auth['service_scope'], 'Different service scope')
    path = directory / 'service-recovery.json'
    ledger = read(path)
    require(ledger['profile'] == bp.SERVICE_DELAYED_POLICY['profile']
        and ledger['stage_hash'] == pointer['sha256'] and ledger['maximum'] == 24
        and 0 < len(ledger['charges']) <= 24, 'Changed replacement ledger')
    matches = [r for r in ledger['charges'] if r['failed_slot'] == failure.allowance_slot]
    require(len(matches) == 1, 'Missing or duplicated reservation')
    charge = matches[0]
    require(charge['request_hash'] == failure.request_hash == self.expected
        and charge['schema_hash'] == self.expected_schema, 'Different reserved request')
    details = ended_receipt(self, failure, charge)
    delay = retry_delay(bp.SERVICE_DELAYED_POLICY, ledger['charges'].index(charge), details)
    scheduled = datetime.fromisoformat(charge['scheduled_at_utc'])
    require(scheduled.tzinfo is not None and scheduled <= utc(), 'Invalid failure reservation time')
    original_due = datetime.fromisoformat(charge['next_retry_at_utc'])
    require(original_due.tzinfo is not None and (original_due - scheduled).total_seconds()
        == charge['backoff_seconds'], 'Changed recorded schedule')
    due = scheduled + timedelta(seconds=delay)
    from legalmath.interpretation.assurance.time_authority import effective_deadline
    require(max(due, utc()) + timedelta(seconds=305)
        <= datetime.fromisoformat(effective_deadline(self.root, self.grant_path.parent)), 'Retry exceeds current deadline')
    decision_path = WORK / ('timing-' + str(failure.allowance_slot) + '.json')
    require(not decision_path.exists(), 'Timing decision already used; inspect before restart')
    decision = dict(charge=charge, original_due_utc=original_due.isoformat(), effective_due_utc=due.isoformat(),
        authority=ref(ROOT, AUTH), worker=process_identity(os.getpid()), started_at_utc=utc().isoformat())
    save(decision_path, decision)

    def unchanged():
        authority()
        require(read(path) == ledger and read(self.grant_path.with_name('current-stage.json')) == charge['stage'],
            'Retry ownership changed during wait')
        ended_receipt(self, failure, charge)

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
        circuit_path = directory / 'service-circuit.json'
        circuit = read(circuit_path)
        require(circuit['stage_hash'] == pointer['sha256'] and circuit['open']
            and circuit['failed_slots'][-1] == failure.allowance_slot, 'Another owner changed the circuit')
        circuit.update(open=False, half_open_request_hash=self.expected, half_open_schema_hash=self.expected_schema,
            half_open_reserved=False, resumed_after_slot=failure.allowance_slot,
            resumed_at_utc=utc().isoformat(), user_timing_authority=ref(ROOT, AUTH))
        save(circuit_path, circuit)
    decision['released_at_utc'] = utc().isoformat()
    save(decision_path, decision)


def active_children(pid):
    children = set()
    for thread in Path('/proc', str(pid), 'task').iterdir():
        try:
            children.update(int(x) for x in (thread / 'children').read_text().split())
        except FileNotFoundError:
            pass
    return [p for p in children if process_alive(process_identity(p))]


def snapshot():
    resume.authority()
    old = read(OLD / 'service-worker.json')['process']
    require(old == read(OLD / 'service-armed.json')['process'] and process_alive(old), 'Original worker changed')
    require(not active_children(old['pid']), 'Original worker has an active child')
    require(not any((OLD / name).exists() for name in ('service-probe-started.json', 'service-worker-error.json',
        'service-finished.json')), 'Original probe may have started or settled')
    ledger = read(BASE / 'live-calls.json')
    recovery = read(resume.SERVICE / 'service-recovery.json')
    circuit = read(resume.SERVICE / 'service-circuit.json')
    require(len(ledger['calls']) == resume.SLOT and len(recovery['charges']) == 21
        and recovery['charges'][-1]['failed_slot'] == resume.SLOT
        and circuit['open'] and not circuit.get('half_open_reserved'), 'Original reservation advanced')
    state = read(BASE / 'execution-state.json')
    require(not any(row['status'] == 'RUNNING' for row in state['tasks'].values()), 'Master owner active')
    return dict(worker=old, ledger=ledger, recovery=recovery, circuit=circuit,
        state=ref(ROOT, BASE / 'execution-state.json'), stage=read(BASE / 'current-stage.json'))


def prepare():
    require(not AUTH.exists(), 'Timing authority already exists')
    require(read(WORK / 'local-result.json')['verdict'] == 'PASS', 'Local controls have not passed')
    preflight = read(WORK / 'mission-preflight.json')
    require(preflight['check'] == 'PASS' and preflight['admission'] == 'ADMITTED_MASTER_WORK', 'Mission not admitted')
    before = snapshot()
    save(WORK / 'baseline.json', before)
    binding = read(BASE / 'current-binding.json')
    paths = [Path(__file__), WORK / 'test_five_minute_retry.py', PLAN, WORK / 'local-result.json',
        WORK / 'tests.xml', WORK / 'mission-preflight.json', WORK / 'baseline.json', PROGRAM,
        BASE / 'current-binding.json', BASE / 'live-grant.json', BASE / 'campaign-routing.toml',
        OLD / 'service-resume-authority.json', OLD / 'service_resume.py']
    save(AUTH, dict(profile='user-five-minute-retry.v1', user_instruction=USER, interval_seconds=300,
        calls_added=0, attempts_added=0, replacements_added=0, approved_at_utc=utc().isoformat(),
        service_scope=binding['phase_service_scope'], bindings=[ref(ROOT, p) for p in paths]))
    return dict(prepared=True, old_worker=before['worker'], authority=ref(ROOT, AUTH))


def handover():
    authority()
    before = read(WORK / 'baseline.json')
    require(snapshot() == before, 'Original worker advanced before handover')
    identity = before['worker']
    # Freeze first: a timer expiring must never race a provider dispatch.
    os.kill(identity['pid'], signal.SIGSTOP)
    stopped = False
    try:
        for _ in range(100):
            raw = Path('/proc', str(identity['pid']), 'stat').read_text().rsplit(') ', 1)[1].split()
            require(raw[19] == identity['start'], 'Worker PID reused')
            if raw[0] in ('T', 't'):
                break
            time.sleep(0.01)
        else:
            raise RuntimeError('Worker did not freeze')
        require(snapshot() == before, 'Worker dispatched before freeze')
        save(WORK / 'handover-started.json', dict(before=before['worker'], at_utc=utc().isoformat(),
            active_provider_children=0, authority=ref(ROOT, AUTH)))
        os.kill(identity['pid'], signal.SIGTERM)
        os.kill(identity['pid'], signal.SIGCONT)
        for _ in range(100):
            if not process_alive(identity):
                stopped = True
                break
            time.sleep(0.1)
        require(stopped, 'Original worker did not terminate')
        verify(ROOT, before['state'])
        require(read(BASE / 'live-calls.json') == before['ledger']
            and read(resume.SERVICE / 'service-recovery.json') == before['recovery']
            and read(resume.SERVICE / 'service-circuit.json') == before['circuit']
            and read(BASE / 'current-stage.json') == before['stage'], 'State advanced during transfer')
        save(WORK / 'handover.json', dict(stopped_process=identity, at_utc=utc().isoformat(),
            charged_calls=len(before['ledger']['calls']), replacement_reservations=21, provider_calls_added=0))
    finally:
        if not stopped and process_alive(identity):
            os.kill(identity['pid'], signal.SIGCONT)


def checkpoint_history():
    path = ROOT / 'docs/implementation/legal-mission-control/mission.json'
    with path.with_name('mission.execution.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        value = read(path)
        key = 'five-minute-retry-2026-10-21'
        if any(row['id'] == key for row in value['history']):
            return
        reason = ('User-directed five-minute retries replace hourly waits in the current supervised master. '
            'Credit the existing reservation time, preserve all charges and attempts, then continue original answers and tool comparisons.')
        value['next_task_reason'] = reason
        value['history'].append(dict(id=key, task_id='product-contribution', kind='product_evaluation',
            outcome='no_advance', decision=reason, next_task='product-contribution', next_task_reason=reason,
            recorded_at_utc=utc().isoformat(), result_evidence=[ref(ROOT, p) for p in (AUTH, PLAN,
                WORK / 'local-result.json', WORK / 'handover.json')]))
        save(path, value)


def worker():
    from scripts import legal_integration_phased_live as live
    from scripts.legal_integration_campaign import provider
    with (WORK / 'worker.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(WORK / 'worker.json', dict(process=process_identity(os.getpid()), started_at_utc=utc().isoformat()))
        try:
            handover()
            checkpoint_history()
            with patch.object(bp, 'recovery_delay', retry_delay), \
                    patch.object(bp.CampaignAllowance, 'wait_service_recovery', five_minute_wait), \
                    patch.object(providers, 'transient_service_details', resume.classify):
                with ExitStack() as stack:
                    for path in dict.fromkeys((ROOT / live.LIVE / 'supervisor.lock',
                            ROOT / live.active_live(read(PROGRAM)) / 'supervisor.lock',
                            resume.SERVICE / 'service-worker.lock', OLD / 'service-worker.lock')):
                        handle = stack.enter_context(path.open('a'))
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    service = provider()
                    service.check()
                    before = read(WORK / 'baseline.json')
                    require(read(BASE / 'current-stage.json') == before['stage'], 'Reserved stage changed')
                    request, schema = resume.terminal_receipt(resume.RECEIPT)
                    service.allowance.expected, service.allowance.expected_schema = resume.TARGET, resume.SCHEMA
                    failure = providers.TerminalServiceFailure('request timed out', allowance_slot=resume.SLOT,
                        request_hash=resume.TARGET)
                    five_minute_wait(service.allowance, failure)
                    save(WORK / 'probe-started.json', dict(at_utc=utc().isoformat(), request_hash=resume.TARGET))
                    response = service._complete(request, schema, Settings(timeout_seconds=300))
                    save(WORK / 'probe-response.json', dict(value=response.value, provenance=response.provenance,
                        legal_acceptance=False, substituted_into_product=False))
                save(WORK / 'live-result.json', live.live())
        except BaseException as exc:
            save(WORK / 'worker-error.json', dict(error=type(exc).__name__, reason=str(exc), at_utc=utc().isoformat()))
            raise
        finally:
            results = []
            for name, args in (('refresh', ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']),
                    ('verify', ['.venv-context/bin/python', 'scripts/legal_integration_master.py', 'verify'])):
                with (WORK / (name + '.stdout')).open('w') as out, (WORK / (name + '.stderr')).open('w') as err:
                    code = subprocess.call(args, cwd=ROOT, stdout=out, stderr=err)
                results.append(dict(command=args, exit_code=code))
            save(WORK / 'finished.json', dict(steps=results, ended_at_utc=utc().isoformat(), integration_complete=False))


def arm():
    authority()
    with (WORK / 'arm.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (WORK / 'armed.json').exists(), 'Already armed; inspect current owner')
        require(snapshot() == read(WORK / 'baseline.json'), 'Original worker advanced')
        with (WORK / 'supervisor.log').open('ab') as log:
            child = subprocess.Popen(['.venv-context/bin/python', str(Path(__file__).relative_to(ROOT)), 'worker'],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result = dict(process=process_identity(child.pid), authority=ref(ROOT, AUTH), armed_at_utc=utc().isoformat())
        require(result['process'] is not None, 'Replacement worker failed to start')
        save(WORK / 'armed.json', result)
        return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'arm', 'worker'))
    args = parser.parse_args()
    print(json.dumps({'prepare': prepare, 'arm': arm, 'worker': worker}[args.action](), indent=2))
