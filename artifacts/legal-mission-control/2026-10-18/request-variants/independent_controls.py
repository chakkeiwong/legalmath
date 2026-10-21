"""Production reservation/circuit controls with isolated accounting, no API calls."""
from concurrent.futures import ThreadPoolExecutor
import copy
import fcntl
import importlib.util
import json
from pathlib import Path
import time

WORK = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, WORK / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


p = module('independent_probe_controls', 'probe-independent.py')
r = module('retained_receipt_controls', 'receipt_controls.py')
from legalmath.interpretation.assurance.bounded_provider import SERVICE_DELAYED_POLICY


def main():
    directory = WORK / 'offline-independent-controls-final'
    directory.mkdir(exist_ok=False)
    old = p.read(WORK / 'authorization-final.json')
    p.AUTH = directory / 'authorization.json'
    base = directory / 'isolated-service'
    base.mkdir()
    p.save(base / 'current-binding.json', dict(isolated=True))
    p.save(base / 'live-grant.json', dict(isolated=True))
    p.save(base / 'scope.json', dict(isolated=True))
    empty = dict(grant_hash=p.digest(p.read(base / 'live-grant.json')), maximum=50, calls=[])
    p.save(base / 'before.json', empty)
    stage = dict(profile='integration-current-stage.v2', grant_hash=empty['grant_hash'],
                 binding_hash=p.digest(p.read(base / 'current-binding.json')),
                 ledger_before=p.ref(base / 'before.json'), maximum_calls=6)
    p.save(base / 'stage.json', stage)
    p.save(base / 'current-stage.json', p.ref(base / 'stage.json'))
    auth = dict(old, grant=p.ref(base / 'live-grant.json'), binding=p.ref(base / 'current-binding.json'),
                service_scope=p.ref(base / 'scope.json'), ledger_before=p.ref(base / 'before.json'),
                source=p.ref(WORK / 'probe-independent.py'), plan=p.ref(p.PLAN),
                original_plan=old['plan'], stop_receipt=p.ref(WORK / 'independent-stop.json'),
                previous_authorizations=[p.ref(WORK / name) for name in (
                    'authorization-initial.json', 'authorization.json',
                    'authorization-reviewed.json', 'authorization-final.json')])
    p.save(p.AUTH, auth)
    auth = p.read(p.AUTH)
    scope = auth['service_scope']
    closed = dict(stage_hash=scope['sha256'], consecutive_failures=0, failed_slots=[], open=False)

    class IsolatedAllowance(p.CampaignAllowance):
        # Isolate global grant validation and scope resolution. Reservation locking,
        # stage accounting, authority references and circuit transitions are real.
        def check(self):
            return p.read(self.path)

        def service_scope(self):
            return scope, base, p.read(base / 'scope.json')

        def service_recovery_policy(self):
            return SERVICE_DELAYED_POLICY

    def allowance():
        return IsolatedAllowance(base, p.CodexProvider().routing, root=p.ROOT)

    def reset(calls=None, circuit=None):
        p.save(base / 'live-calls.json', dict(empty, calls=calls or []))
        p.save(base / 'service-circuit.json', circuit or closed)

    row = old['arms'][0]
    checks = []
    reset()
    with (base / 'service-worker.lock').open('a') as master:
        fcntl.flock(master, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p.need(p.reserve(allowance(), auth, row) == 1, 'Diagnostic waited on master lock')
        with (base / 'service-worker.lock').open('a') as contender:
            try:
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise AssertionError('Master lock was released by diagnostic')
    checks.append('Diagnostic reserves while master service-worker lock stays occupied')

    reset()
    def competing(i):
        a = allowance()
        if i % 2:
            a.expected, a.expected_schema = 'isolated-master-' + str(i), 'isolated-master-schema'
            return a.reserve(a.expected)
        return p.reserve(a, auth, row)
    with ThreadPoolExecutor(max_workers=12) as pool:
        slots = list(pool.map(competing, range(12)))
    ledger = p.read(base / 'live-calls.json')
    p.need(sorted(slots) == list(range(1, 13)) and len(ledger['calls']) == 12,
           'Concurrent reservation lost a row or duplicated a slot')
    master_stage = p.ref(base / 'stage.json')['sha256']
    p.need(sum(x['stage_hash'] == master_stage for x in ledger['calls']) == 6,
           'Diagnostic consumed master per-stage allowance')
    checks.append('Six concurrent diagnostic and six production master charges retain twelve distinct slots')
    checks.append('All six production master reservations pass despite diagnostic charges')

    def rejected(label):
        before = (base / 'live-calls.json').read_bytes()
        try:
            p.reserve(allowance(), auth, row)
        except Exception as error:
            p.need((base / 'live-calls.json').read_bytes() == before, 'Rejected call was charged')
            checks.append(label + ': ' + str(error))
        else:
            raise AssertionError(label + ' failed to stop dispatch')

    reset(circuit=dict(closed, open=True, consecutive_failures=1, failed_slots=[1]))
    rejected('Open circuit blocks dispatch')
    for request_hash in ('isolated-master-request', row['request_hash']):
        reset(circuit=dict(closed, half_open_request_hash=request_hash,
                           half_open_schema_hash=row['schema_hash'], half_open_reserved=False))
        rejected('Existing half-open probe cannot be borrowed, including an identical request')
    reset()
    failure = p.TerminalServiceFailure('HTTP 503', allowance_slot=1, request_hash=row['request_hash'])
    allowance().service_circuit(failure=failure)
    p.need(p.read(base / 'service-circuit.json')['open'], 'Real terminal failure did not open circuit')
    checks.append('Production terminal-failure transition opens the isolated shared circuit')

    history = [dict(request_hash='historical', issued_at_ns=str(i), stage_hash=entry['sha256'])
               for i, entry in enumerate(auth['previous_authorizations'])]
    reset(calls=history)
    p.need(p.reserve(allowance(), auth, row) == 5 and p.reserve(allowance(), auth, row) == 6,
           'Historical diagnostic allocation not aggregated')
    rejected('Four predecessor authorities plus two new calls exhaust the same six-call ceiling')
    reset()
    p.save(base / 'stage.json', dict(stage, profile='integration-current-stage.v1'))
    p.save(base / 'current-stage.json', p.ref(base / 'stage.json'))
    rejected('Legacy stage accounting blocks concurrent dispatch')
    p.save(base / 'stage.json', stage)
    p.save(base / 'current-stage.json', p.ref(base / 'stage.json'))

    # Recheck actual receipt writer and changed success behavior with local children.
    p.WORK = directory / 'receipts'
    p.WORK.mkdir()
    schema = p.read(p.verify(row['original_schema']))
    value = dict(conclusion='Offline structural control', support=[dict(span_id=0)], contrary=[],
                 assumptions=[], unresolved=[], alternatives=[],
                 considered={k:v['enum'][0] for k,v in schema['properties']['considered']['properties'].items()},
                 source_gaps=[], assertion_bindings=[])
    value_path = directory / 'synthetic-answer.json'
    p.save(value_path, value)
    real_reserve = p.reserve
    p.reserve = lambda *args: 1
    receipts = []
    try:
        for scenario, expected in (('valid', 'VALID_STRUCTURED_RESPONSE'),
                                   ('invalid', 'INVALID_REQUEST'), ('safety', 'EXPLICIT_SAFETY_BLOCK'),
                                   ('service', 'TERMINAL_SERVICE_FAILURE')):
            arm = p.WORK / scenario / 'original'
            arm.mkdir(parents=True)
            (arm / 'request.json').write_bytes(p.verify(row['request']).read_bytes())
            (arm / 'schema.json').write_bytes(p.verify(row['schema']).read_bytes())
            local_row = dict(row, qid=scenario, form='original', request=p.ref(arm / 'request.json'),
                             schema=p.ref(arm / 'schema.json'))
            a = r.LocalAllowance()
            outcome = p.dispatch(r.LocalProvider(scenario, value_path), a, auth, local_row,
                                 time.monotonic() + 3600)
            p.need(outcome['classification'] == expected, 'Wrong terminal classification')
            p.need(len(a.events) == int(scenario == 'service'), 'Diagnostic reset a circuit on success')
            p.need(p.read(arm / 'outcome.json') == outcome, 'Operational receipt failed round trip')
            for reference in p.read(arm / 'manifest.json')['files'].values():
                p.verify(reference)
            receipts.append(p.ref(arm / 'outcome.json'))
    finally:
        p.reserve = real_reserve
    checks.append('Valid/invalid-request/safety/503 receipts persist; success never mutates circuit')
    p.save(directory / 'result.json', dict(status='PASS', source=p.ref(__file__),
           tested_source=p.ref(WORK / 'probe-independent.py'), checks=checks, receipt_outcomes=receipts,
           real_provider_calls=0, production_ledger_writes=0,
           isolation_seams=['Allowance.check reads synthetic ledger', 'Scope/policy resolve isolated service',
                            'Receipt-only calls use local child and simulated reservation'],
           checked_at_utc=p.utc()))
    print(json.dumps(p.read(directory / 'result.json')))


if __name__ == '__main__':
    main()
