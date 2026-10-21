"""Six-call, non-promoting diagnostic; never changes the active P10 stage."""
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
from pathlib import Path
import copy
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from jsonschema import Draft202012Validator
from legalmath.canonical import canonical, digest
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
from legalmath.interpretation.assurance.monitor import save
from scripts.legal_mission_execution import process_alive, process_identity
from legalmath.interpretation.search.providers import (
    CodexProvider, TerminalServiceFailure, TerminatedCallTimeout,
    transient_service_details,
)
from legalmath.interpretation.search.schema import validate_output_schema

WORK = Path(__file__).resolve().parent
BASE = ROOT / 'artifacts/legal-mission-control/2026-10-13/master'
PLAN = ROOT / 'docs/plans/legal-request-variants-2026-10-18.md'
AUTH = WORK / 'authorization-reviewed.json'
PREFLIGHT = WORK / 'preflight-reviewed.json'
FIXTURES = {
    'p14': ('2341-3001f5cecd92e4ce',
        '3001f5cecd92e4ced66d276bb9d73b42677e37d559444f1733578dd4cb6611ee'),
    'gatecoin': ('2285-f68560b787abac49',
        'f68560b787abac495388e30e9eb36d76ee49aa295be19694e0e791fa15e7c62d'),
}
FORMS = ('original', 'inline-schema', 'pretty-json')
P10_EXECUTION = ROOT / 'artifacts/legal-mission-control/2026-10-17/gap-refresh/settled-recovery/execution'


def read(path):
    return json.loads(Path(path).read_bytes())


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(path):
    return dict(path=str(Path(path).relative_to(ROOT)), sha256=sha(Path(path).read_bytes()))


def verify(reference):
    path = ROOT / reference['path']
    need(sha(path.read_bytes()) == reference['sha256'], 'Changed evidence: ' + reference['path'])
    return path


def utc():
    return datetime.now(timezone.utc).isoformat()


def authority_hashes(authorization):
    return {sha(AUTH.read_bytes()), *(
        item['sha256'] for item in authorization.get('previous_authorizations', []))}


def expanded(schema):
    def visit(node, stack=()):
        if isinstance(node, list):
            return [visit(n, stack) for n in node]
        if not isinstance(node, dict):
            return node
        if '$ref' in node:
            target = node['$ref']
            need(set(node) == {'$ref'} and target.startswith('#/$defs/'), 'Unsupported reference')
            need(target not in stack, 'Recursive schema not admitted')
            key = target.removeprefix('#/$defs/')
            need('/' not in key and '~' not in key, 'Unexpected definition name')
            return visit(schema['$defs'][key], stack + (target,))
        return {k: visit(v, stack) for k, v in node.items() if k != '$defs'}
    result = visit(schema)
    need('$ref' not in json.dumps(result) and '$defs' not in json.dumps(result), 'Unexpanded schema')
    return result


def fixtures(ledger):
    result = {}
    for qid, (name, expected) in FIXTURES.items():
        directory = BASE / 'provider-evidence' / name
        manifest = read(directory / 'manifest.json')
        for filename, item in manifest['files'].items():
            need(sha((directory / filename).read_bytes()) == item['retained_sha256'], 'Corrupt original receipt')
        request = read(directory / 'request.json')
        need(digest(request) == expected == manifest['request_hash'], 'Wrong original request')
        need(ledger['calls'][manifest['allowance_slot'] - 1]['request_hash'] == expected, 'Missing original charge')
        result[qid] = (directory, request, read(directory / 'schema.json'))
    return result


def equivalence_checks(schema, inline):
    original, candidate = Draft202012Validator(schema), Draft202012Validator(inline)
    value = dict(conclusion='Diagnostic structural fixture', support=[dict(span_id=0)],
        contrary=[], assumptions=[], unresolved=[], alternatives=[],
        considered={k: v['enum'][0] for k, v in schema['properties']['considered']['properties'].items()},
        source_gaps=[], assertion_bindings=[])
    need(original.is_valid(value), 'Invalid structural control')
    controls = [value]
    for changed in (-1, schema['$defs']['ExactCitation']['properties']['span_id']['maximum'] + 1, '0'):
        other = copy.deepcopy(value); other['support'] = [dict(span_id=changed)]; controls.append(other)
    other = copy.deepcopy(value); other.pop('considered'); controls.append(other)
    other = copy.deepcopy(value); other['extra'] = True; controls.append(other)
    other = copy.deepcopy(value); other['support'][0]['extra'] = True; controls.append(other)
    for number, control in enumerate(controls):
        need(original.is_valid(control) == candidate.is_valid(control) == (number == 0),
             'Schema equivalence adverse check failed')
    return len(controls)


def prepare():
    need(not (WORK / 'authorization.json').exists(),
         'Original preparation is retained; use the reviewed offline revalidation, never overwrite it')
    need(not AUTH.exists(), 'Authorization already exists; inspect instead of resetting')
    provider = CodexProvider()
    allowance = CampaignAllowance(BASE, provider.routing, root=ROOT)
    ledger = allowance.check()
    need(provider.routing['model'] == 'gpt-6.1-sol', 'Model changed')
    scope, directory, _ = allowance.service_scope()
    save(WORK / 'ledger-before.json', ledger)
    rows = []
    for qid, (source, request, schema) in fixtures(ledger).items():
        inline = expanded(schema)
        checks = equivalence_checks(schema, inline)
        for form in FORMS:
            arm = WORK / qid / form
            arm.mkdir(parents=True, exist_ok=False)
            payload = (json.dumps(request, ensure_ascii=False, sort_keys=True, indent=2).encode()
                       if form == 'pretty-json' else (source / 'request.json').read_bytes())
            shape = canonical(inline) if form == 'inline-schema' else (source / 'schema.json').read_bytes()
            need(json.loads(payload) == request and digest(request) == FIXTURES[qid][1], 'Legal payload changed')
            parsed_shape = json.loads(shape)
            validate_output_schema(parsed_shape)
            Draft202012Validator.check_schema(parsed_shape)
            need(expanded(parsed_shape) == inline, 'Schema constraints changed')
            (arm / 'request.json').write_bytes(payload)
            (arm / 'schema.json').write_bytes(shape)
            rows.append(dict(qid=qid, form=form, request=ref(arm / 'request.json'),
                schema=ref(arm / 'schema.json'), original_manifest=ref(source / 'manifest.json'),
                original_schema=ref(source / 'schema.json'), request_hash=digest(request),
                schema_hash=digest(parsed_shape), input_bytes=len(payload),
                equivalence_controls_passed=checks))
    grant = read(BASE / 'live-grant.json')
    authorization = dict(profile='integration-diagnostic-stage.v1',
        user_instruction='for both P14 and gatecoin can you test if you get the same problem if you different ways?',
        task_id='product-contribution', maximum_calls=6, created_at_utc=utc(),
        grant=ref(BASE / 'live-grant.json'), grant_hash=digest(grant),
        binding=ref(BASE / 'current-binding.json'), routing_hash=digest(provider.routing),
        model=provider.routing['model'], deadline_utc=grant['deadline_utc'],
        ledger_before=ref(WORK / 'ledger-before.json'), service_scope=scope,
        service_directory=str(directory.relative_to(ROOT)), source=ref(__file__), plan=ref(PLAN),
        arms=rows, automatic_retries=0, production_promotion=False)
    AUTH.write_bytes(canonical(authorization))
    save(WORK / 'preflight.json', dict(status='PASS', fixture_authentication=True,
        schema_equivalence_controls=14, arms=len(rows), authorization=ref(AUTH),
        original_owner_attempts_reopened=False, global_calls_added=0))
    print(json.dumps(read(WORK / 'preflight.json')), flush=True)


@contextmanager
def service_lock(path, deadline, label):
    with path.open('a') as lock:
        need(time.monotonic() < deadline, 'Campaign deadline reached before provider lock')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Unexpected provider-lock owner; no diagnostic call sent') from exc
        yield


def master_owner_state():
    state = read(BASE / 'execution-state.json')
    running = sorted(k for k, value in state['tasks'].items() if value.get('status') == 'RUNNING')
    identities = []
    for filename, key in (('worker-start.json', 'process'), ('worker-live-process.json', 'process')):
        path = P10_EXECUTION / filename
        need(path.exists(), 'Missing active P10 worker identity')
        record = read(path)
        identity = record.get(key)
        need(isinstance(identity, dict) and set(identity) == {'pid', 'start'}, 'Invalid worker identity')
        identities.append(identity)
    alive = [identity for identity in identities if process_alive(identity)]
    return running, alive, identities


def wait_for_master_owners(authorization, deadline):
    gate = WORK / 'owner-gate-reviewed.json'
    _, _, identities = master_owner_state()
    record = dict(profile='no-active-master-owner-before-diagnostic.v1',
        p10_execution_start=ref(P10_EXECUTION / 'worker-start.json'),
        p10_live_process=ref(P10_EXECUTION / 'worker-live-process.json'),
        observed_identities=identities, authorization=ref(AUTH), checked_at_utc=utc())
    if gate.exists():
        previous = read(gate)
        need(previous['p10_execution_start'] == record['p10_execution_start']
            and previous['p10_live_process'] == record['p10_live_process']
            and previous['authorization'] == record['authorization'], 'Owner gate identity changed')
    else:
        save(gate, record)
    last = time.monotonic()
    while True:
        verify(record['p10_execution_start']); verify(record['p10_live_process'])
        running, alive, current_identities = master_owner_state()
        if not running and not alive:
            save(WORK / 'owner-settled.json', dict(gate=ref(gate), running_tasks=running,
                live_workers=alive, checked_at_utc=utc()))
            return
        need(time.monotonic() < deadline, 'Grant deadline reached while a master owner remains active')
        if time.monotonic() - last >= 60:
            progress = dict(status='WAITING_FOR_MASTER_OWNER', running_tasks=running,
                live_worker_pids=[x['pid'] for x in alive], checked_at_utc=utc())
            save(WORK / 'progress.json', progress)
            print(json.dumps(progress), flush=True)
            last = time.monotonic()
        time.sleep(min(10, max(0, deadline-time.monotonic())))


def reserve(allowance, authorization, row):
    with allowance.path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for field in ('grant', 'binding', 'source', 'plan', 'review', 'ledger_before', 'service_scope'):
            verify(authorization[field])
        for previous in authorization['previous_authorizations']:
            verify(previous)
        need(read(AUTH) == authorization, 'Authorization changed')
        need(digest(allowance.routing) == authorization['routing_hash'], 'Route changed')
        remaining = (datetime.fromisoformat(authorization['deadline_utc'])
                     - datetime.now(timezone.utc)).total_seconds()
        need(remaining >= 305, 'Insufficient approved time for another diagnostic request')
        state = allowance.check()
        before = read(verify(authorization['ledger_before']))
        need(state['calls'][:len(before['calls'])] == before['calls'], 'Prior charges changed')
        stage_hash = sha(AUTH.read_bytes())
        used = sum(r.get('stage_hash') in authority_hashes(authorization) for r in state['calls'])
        need(used < authorization['maximum_calls'] and len(state['calls']) < state['maximum'], 'Call ceiling reached')
        allowance.expected = row['request_hash']; allowance.expected_schema = row['schema_hash']
        pointer, directory, _ = allowance.service_scope()
        need(pointer == authorization['service_scope'], 'Service scope changed')
        circuit = read(directory / 'service-circuit.json')
        need(not circuit.get('half_open_request_hash'), 'Scheduled half-open probe belongs to its existing worker')
        allowance.service_circuit(reserving=True)
        state['calls'].append(dict(request_hash=row['request_hash'], issued_at_ns=str(time.time_ns()),
                                   stage_hash=stage_hash))
        save(allowance.path, state)
        return len(state['calls'])


def redact(text):
    return re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|token)\s*[=:]\s*)[^\s,\"]+', r'\1[REDACTED]', text)


def dispatch(provider, allowance, authorization, row, batch_deadline):
    directory = WORK / row['qid'] / row['form']
    request = verify(row['request']); schema = verify(row['schema'])
    original_schema = read(verify(row['original_schema']))
    need(batch_deadline - time.monotonic() >= 305,
         'Insufficient batch time for another diagnostic request')
    slot = reserve(allowance, authorization, row)
    save(directory / 'reservation.json', dict(global_slot=slot, authority=ref(AUTH), reserved_at_utc=utc()))
    command = provider.command(directory, schema, directory / 'result.json')
    began = time.monotonic()
    save(directory / 'command.json', dict(command=command, global_slot=slot, started_at_utc=utc(),
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment=sys.executable, devices='CPU only; GPU intentionally hidden',
        sampling_seed='N/A: unavailable; no stochastic ranking', deadline_seconds=300,
        request_hash=row['request_hash'], schema_hash=row['schema_hash'], authorization=ref(AUTH)))
    timed_out = capped = False
    output = directory / 'result.json'
    events_path, stderr_path = directory / 'events.jsonl', directory / 'stderr.txt'
    try:
        with request.open('rb') as stdin, events_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
            child = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True)
            save(directory / 'process.json', dict(pid=child.pid,
                start=Path(f'/proc/{child.pid}/stat').read_text().rsplit(') ', 1)[1].split()[19]))
            try:
                while child.poll() is None:
                    timed_out = time.monotonic() - began >= 300 or time.monotonic() >= batch_deadline
                    capped = any(p.stat().st_size > 4_000_000 for p in (events_path, stderr_path)) or (
                        output.exists() and output.stat().st_size > 200000)
                    if timed_out or capped:
                        break
                    try:
                        child.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
    finally:
        if stderr_path.exists():
            stderr_path.write_text(redact(stderr_path.read_text(errors='replace')))
    events = [json.loads(line) for line in events_path.read_bytes().splitlines() if line.strip()]
    messages = [str(e.get('message', '')) for e in events if e.get('type') == 'error']
    messages += [str(e.get('error', {}).get('message', '')) for e in events if e.get('type') == 'turn.failed']
    forbidden = any(e.get('item', {}).get('type') in {'command_execution', 'mcp_tool_call', 'web_search', 'file_change'} for e in events)
    explicit_block = any(re.search(r'blocked by our safety systems|cannot (?:assist|comply)|can.t (?:assist|comply)', m, re.I) for m in messages)
    completed = any(e.get('type') == 'turn.completed' for e in events)
    details = transient_service_details(events, output_present=output.exists(), allow_terminal_499=True)
    validation_errors = []
    classification = 'UNCLASSIFIED_TERMINAL_FAILURE'
    if explicit_block:
        classification = 'EXPLICIT_SAFETY_BLOCK'
    elif forbidden or capped:
        classification = 'INVALID_DIAGNOSTIC'
    elif timed_out:
        classification = 'LOCAL_TIMEOUT'
    elif details:
        classification = 'TERMINAL_SERVICE_FAILURE'
    elif any('invalid_request' in m for m in messages):
        classification = 'INVALID_REQUEST'
    elif child.returncode == 0 and output.exists() and completed:
        try:
            value = read(output)
            for label, shape in (('original', original_schema), ('arm', read(schema))):
                validation_errors += [label + ': ' + e.message for e in Draft202012Validator(shape).iter_errors(value)]
            classification = 'VALID_STRUCTURED_RESPONSE' if not validation_errors else 'ORIGINAL_SCHEMA_FAILED'
        except (ValueError, UnicodeError) as error:
            validation_errors.append(str(error)); classification = 'INVALID_JSON'
    if classification in ('LOCAL_TIMEOUT', 'TERMINAL_SERVICE_FAILURE') and not output.exists() and not completed:
        failure_type = TerminatedCallTimeout if timed_out else TerminalServiceFailure
        failure = failure_type(details or 'Diagnostic subprocess ended at deadline without output',
                               allowance_slot=slot, request_hash=row['request_hash'])
        allowance.service_circuit(failure=failure)
    elif classification == 'VALID_STRUCTURED_RESPONSE':
        allowance.service_circuit(success=True)
    result = dict(qid=row['qid'], form=row['form'], global_slot=slot, classification=classification,
        returncode=child.returncode, elapsed_seconds=round(time.monotonic()-began, 3),
        error_messages=[redact(m)[:2500] for m in messages], original_schema_errors=validation_errors,
        completed_turn=completed, output_present=output.exists(), request=row['request'], schema=row['schema'],
        usage=[e['usage'] for e in events if e.get('type') == 'turn.completed' and 'usage' in e],
        production_promoted=False, finished_at_utc=utc())
    save(directory / 'outcome.json', result)
    save(directory / 'manifest.json', dict(global_slot=slot, authority=ref(AUTH),
        files={p.name:ref(p) for p in directory.iterdir() if p.is_file() and p.name != 'manifest.json'}))
    print(json.dumps(result), flush=True)
    return result


def finish(result):
    save(WORK / 'result.json', result)
    print(json.dumps(result), flush=True)
    mission_path = ROOT / 'docs/implementation/legal-mission-control/mission.json'
    try:
        with mission_path.with_name('mission.execution.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            mission = read(mission_path)
            entry_id = 'request-variants-20261018-final'
            need(not any(row['id'] == entry_id for row in mission['history']),
                 'Diagnostic final checkpoint already exists')
            need(mission['current_task'] == 'product-contribution', 'Mission selection changed')
            reason = ('Inspect the retained P14/Gatecoin diagnostic outcomes and existing master '
                      'frontier; no acquisition owner, call ceiling or deadline was renewed.')
            mission['history'].append(dict(id=entry_id, task_id='product-contribution',
                kind='product_evaluation', outcome='no_advance', next_task='product-contribution',
                next_task_reason=reason, recorded_at_utc=utc(),
                decision=f"Request-format diagnostic settled with {result['calls_used']} calls; "
                         'terminal and undispatched outcomes retained, without legal promotion.',
                result_evidence=[ref(WORK / 'result.json'), ref(AUTH), ref(PREFLIGHT)]))
            mission['next_task_reason'] = reason
            save(mission_path, mission)
        with (WORK / 'mission-refresh-final.json').open('x') as stdout, (
                WORK / 'mission-refresh-final.stderr').open('x') as stderr:
            checked = subprocess.run(['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh'],
                cwd=ROOT, stdout=stdout, stderr=stderr, timeout=900)
        save(WORK / 'mission-checkpoint.json', dict(recorded=True, refresh_exit_code=checked.returncode,
            refreshed_at_utc=utc()))
    except Exception as error:
        save(WORK / 'mission-checkpoint.json', dict(status='RECONCILIATION_REQUIRED',
            reason=redact(str(error)), recorded_at_utc=utc()))


def run():
    authorization = read(AUTH)
    preflight = read(PREFLIGHT)
    need(preflight['status'] == 'PASS' and preflight['authorization'] == ref(AUTH),
         'Missing reviewed preflight for this exact authorization')
    verify(preflight['authorization'])
    verify(authorization['plan'])
    verify(authorization['review'])
    verify(authorization['source'])
    need(authorization['maximum_calls'] == 6 and len(authorization['arms']) == 6,
         'Diagnostic allocation changed')
    provider = CodexProvider()
    allowance = CampaignAllowance(BASE, provider.routing, root=ROOT)
    with ExitStack() as master_locks, (WORK / 'worker.lock').open('a') as worker_lock:
        fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        need(not (WORK / 'result.json').exists(), 'Diagnostic already settled; inspect retained result')
        stage_hash = sha(AUTH.read_bytes())
        ledger = allowance.check()
        charged = [i+1 for i, r in enumerate(ledger['calls'])
                   if r.get('stage_hash') in authority_hashes(authorization)]
        reservations = list(WORK.glob('*/*/reservation.json'))
        need(not charged and not reservations,
             'Prior diagnostic reservation exists; reconcile before any continuation')
        attempt_path = WORK / 'worker-attempts.json'
        attempts = read(attempt_path) if attempt_path.exists() else []
        start_path = WORK / 'worker-start.json'
        if start_path.exists():
            previous = read(start_path)
            identity = previous.get('process') or previous
            need(isinstance(identity, dict) and type(identity.get('pid')) is int,
                 'Invalid prior diagnostic worker identity')
            current = process_identity(identity['pid'])
            normalized = dict(pid=identity['pid'], start=identity.get('start'))
            need(not current or (isinstance(normalized['start'], str) and current != normalized),
                 'Diagnostic worker already active or its PID identity cannot be reconciled')
            attempts.append(dict(previous=previous, disposition='STOPPED_BEFORE_ANY_RESERVATION',
                verified_global_charges=charged, verified_reservations=len(reservations),
                checked_at_utc=utc()))
            save(attempt_path, attempts)
        save(start_path, dict(pid=os.getpid(), start=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19],
            started_at_utc=utc(), authority=ref(AUTH)))
        grant_deadline = datetime.fromisoformat(read(BASE / 'live-grant.json')['deadline_utc'])
        remaining = (grant_deadline - datetime.now(timezone.utc)).total_seconds()
        need(remaining >= 305, 'Insufficient approved time for one diagnostic request')
        owner_wait_deadline = time.monotonic() + remaining - 305
        print(json.dumps(dict(waiting_for_owners=True, deadline_utc=grant_deadline.isoformat())), flush=True)
        save(WORK / 'progress.json', dict(status='WAITING_FOR_MASTER_OWNER',
            started_at_utc=utc(), deadline_utc=grant_deadline.isoformat(), authority=ref(AUTH)))
        rows = []
        shared_stop = None
        try:
            wait_for_master_owners(authorization, owner_wait_deadline)
            for path in (P10_EXECUTION.parent / 'live/supervisor.lock',
                         BASE / 'execution-state.run.lock'):
                handle = master_locks.enter_context(path.open('a'))
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            running, alive, _ = master_owner_state()
            need(not running and not alive, 'Master owner restarted; no diagnostic call sent')
            # Only execution of the six-call batch uses this one-hour clock.
            deadline = min(time.monotonic() + 3600,
                time.monotonic() + (grant_deadline - datetime.now(timezone.utc)).total_seconds() - 5)
            allowance.check()
            _, service_directory, _ = allowance.service_scope()
            circuit = read(service_directory / 'service-circuit.json')
            need(not circuit.get('open') and not circuit.get('half_open_request_hash'),
                 'Shared circuit is open or has an existing half-open probe; no diagnostic call sent')
        except Exception as error:
            shared_stop = redact(type(error).__name__ + ': ' + str(error))[:2500]
            rows = [dict(qid=qid, form=form, classification='NOT_DISPATCHED', reason=shared_stop)
                    for form in FORMS for qid in FIXTURES]
            state = read(BASE / 'live-calls.json')
            own = [(i+1, r) for i, r in enumerate(state['calls'])
                   if r.get('stage_hash') in authority_hashes(authorization)]
            result = dict(profile='request-variants-result.v1', authorization=ref(AUTH),
                outcomes=rows, calls_used=len(own), global_slots=[i for i, _ in own],
                shared_stop=shared_stop, finished_at_utc=utc(), integration_complete=False,
                legal_acceptance=False, statistically_supported_ranking=False)
            finish(result)
            return
        stopped = set()
        for form in FORMS:
            for qid in FIXTURES:
                row = next(r for r in authorization['arms'] if r['qid'] == qid and r['form'] == form)
                if qid in stopped or shared_stop:
                    rows.append(dict(qid=qid, form=form, classification='NOT_DISPATCHED',
                        reason=shared_stop or 'Prior explicit safety block in this branch'))
                    continue
                try:
                    directory = ROOT / authorization['service_directory']
                    with service_lock(directory / 'service-worker.lock', deadline, qid + '/' + form):
                        result = dispatch(provider, allowance, authorization, row, deadline)
                    rows.append(result)
                    if result['classification'] == 'EXPLICIT_SAFETY_BLOCK':
                        stopped.add(qid)
                    if result['classification'] in ('LOCAL_TIMEOUT', 'TERMINAL_SERVICE_FAILURE', 'INVALID_DIAGNOSTIC', 'UNCLASSIFIED_TERMINAL_FAILURE'):
                        shared_stop = result['classification'] + '; inspect shared service/evidence before more calls'
                except Exception as error:
                    shared_stop = redact(type(error).__name__ + ': ' + str(error))[:2500]
                    rows.append(dict(qid=qid, form=form, classification='DIAGNOSTIC_STOPPED', reason=shared_stop))
                save(WORK / 'progress.json', dict(outcomes=rows, shared_stop=shared_stop, updated_at_utc=utc()))
        state = read(BASE / 'live-calls.json')
        own = [(i+1, r) for i, r in enumerate(state['calls'])
               if r.get('stage_hash') in authority_hashes(authorization)]
        result = dict(profile='request-variants-result.v1', authorization=ref(AUTH),
            outcomes=rows, calls_used=len(own), global_slots=[i for i, _ in own],
            shared_stop=shared_stop, finished_at_utc=utc(), integration_complete=False,
            legal_acceptance=False, statistically_supported_ranking=False)
        finish(result)


if __name__ == '__main__':
    need(len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'run', 'status'), 'Use prepare, run or status')
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'run':
        run()
    else:
        print(json.dumps(read(WORK / ('result.json' if (WORK / 'result.json').exists() else 'progress.json'))))
