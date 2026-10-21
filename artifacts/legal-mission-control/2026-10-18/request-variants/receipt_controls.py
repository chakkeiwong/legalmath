"""Offline dispatch/receipt controls. No real allowance or provider is invoked."""
import importlib.util
import json
from pathlib import Path
import sys
import time

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('receipt_probe', WORK / 'probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

CHILD = '''import json, pathlib, sys, time
scenario, output, value = sys.argv[1:]
time.sleep(0.05)
if scenario == 'valid':
    pathlib.Path(output).write_bytes(pathlib.Path(value).read_bytes())
    print(json.dumps({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':10}}))
else:
    messages = {
        'invalid': 'invalid_request: The request could not be processed. Please check the request parameters.',
        'safety': 'This request was blocked by our safety systems. Reason: Potentially unintended activity.',
        'service': 'HTTP status 503 Service Unavailable',
    }
    print(json.dumps({'type':'turn.failed','error':{'message':messages[scenario]}}))
    sys.exit(1)
'''


class LocalProvider:
    def __init__(self, scenario, value):
        self.scenario, self.value = scenario, value

    def command(self, directory, schema, output):
        return [sys.executable, '-c', CHILD, self.scenario, str(output), str(self.value)]


class LocalAllowance:
    def __init__(self):
        self.events = []

    def service_circuit(self, **kwargs):
        self.events.append(kwargs)


def main():
    directory = WORK / 'offline-receipt-controls'
    directory.mkdir(exist_ok=False)
    protected = [p.BASE / name for name in
                 ('live-calls.json', 'current-binding.json', 'live-grant.json')]
    protected += [p.ROOT / 'docs/implementation/legal-mission-control/mission.json',
                  p.ROOT / 'artifacts/legal-mission-control/2026-10-16/delayed-service/service/service-circuit.json']
    before = {str(path):p.sha(path.read_bytes()) for path in protected}
    authorization = p.read(WORK / 'authorization-reviewed.json')
    template = next(row for row in authorization['arms']
                    if row['qid'] == 'p14' and row['form'] == 'original')
    schema = p.read(p.verify(template['original_schema']))
    value = dict(conclusion='Offline structural control only', support=[dict(span_id=0)],
        contrary=[], assumptions=[], unresolved=[], alternatives=[],
        considered={k:v['enum'][0] for k,v in schema['properties']['considered']['properties'].items()},
        source_gaps=[], assertion_bindings=[])
    p.need(p.Draft202012Validator(schema).is_valid(value), 'Invalid synthetic answer')
    value_path = directory / 'synthetic-answer.json'
    p.save(value_path, value)
    reservations, results = [], []
    old_work, old_auth, old_reserve = p.WORK, p.AUTH, p.reserve
    try:
        p.WORK = directory
        p.AUTH = WORK / 'authorization-reviewed.json'
        def fake_reserve(allowance, authority, row):
            reservations.append((row['qid'], row['form']))
            return len(reservations)
        p.reserve = fake_reserve
        for scenario, expected in (
            ('valid', 'VALID_STRUCTURED_RESPONSE'),
            ('invalid', 'INVALID_REQUEST'),
            ('safety', 'EXPLICIT_SAFETY_BLOCK'),
            ('service', 'TERMINAL_SERVICE_FAILURE'),
        ):
            arm = directory / scenario / 'original'
            arm.mkdir(parents=True)
            (arm / 'request.json').write_bytes(p.verify(template['request']).read_bytes())
            (arm / 'schema.json').write_bytes(p.verify(template['schema']).read_bytes())
            row = dict(template, qid=scenario, form='original',
                       request=p.ref(arm / 'request.json'), schema=p.ref(arm / 'schema.json'))
            allowance = LocalAllowance()
            outcome = p.dispatch(LocalProvider(scenario, value_path), allowance,
                                 authorization, row, time.monotonic()+3600)
            p.need(outcome['classification'] == expected, 'Incorrect receipt classification')
            p.need(type(outcome['elapsed_seconds']) is float, 'Elapsed float lost')
            p.need(p.read(arm / 'outcome.json') == outcome, 'Outcome round-trip failed')
            manifest = p.read(arm / 'manifest.json')
            for reference in manifest['files'].values():
                p.verify(reference)
            p.need(len(allowance.events) == int(scenario in ('valid','service')),
                   'Unexpected synthetic circuit event')
            if scenario == 'valid':
                p.need(allowance.events == [dict(success=True)], 'Success event missing')
            if scenario == 'service':
                p.need(isinstance(allowance.events[0].get('failure'), p.TerminalServiceFailure),
                       'Terminal service event missing')
            results.append(dict(scenario=scenario, classification=expected,
                                outcome=p.ref(arm / 'outcome.json'),
                                manifest=p.ref(arm / 'manifest.json'),
                                elapsed_seconds=outcome['elapsed_seconds']))
    finally:
        p.WORK, p.AUTH, p.reserve = old_work, old_auth, old_reserve
    aggregate = dict(profile='offline-receipt-controls.v1', synthetic=True,
                     real_provider_calls=0, simulated_reservations=len(reservations), outcomes=results)
    p.save(directory / 'aggregate.json', aggregate)
    p.need(p.read(directory / 'aggregate.json') == aggregate, 'Aggregate round-trip failed')
    mission = p.read(protected[3])
    p.save(directory / 'mission-copy.json', mission)
    p.need(p.read(directory / 'mission-copy.json') == mission, 'Mission round-trip failed')
    p.need(before == {str(path):p.sha(path.read_bytes()) for path in protected},
           'Protected live state changed during offline controls')
    p.save(directory / 'result.json', dict(status='PASS', source=p.ref(__file__),
        tested_source=p.ref(WORK / 'probe.py'), aggregate=p.ref(directory / 'aggregate.json'),
        mission_copy_round_trip=True, protected_live_state_unchanged=True,
        real_provider_calls=0, checked_at_utc=p.utc()))
    print(json.dumps(p.read(directory / 'result.json')))


if __name__ == '__main__':
    main()
