"""A mixed settled phase must reuse successes and dispatch only missing output."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.providers import Completion
from legalmath.interpretation.assurance.bounded_context import Limits
from legalmath.interpretation.assurance.bounded_product import BoundDispatch
from legalmath.interpretation.assurance.bounded_checkpoint import retained_response
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.phased import synthesis_recovery as recovery, phase


class Provider:
    live = False
    reference_transport = True
    def __init__(self): self.calls = []
    def complete(self, request, schema, settings):
        self.calls.append(request)
        return Completion({'conclusion': 'New missing response.'}, {'provider': 'scripted'})


def fixture(root):
    def put(path, value):
        save(root / path, value)
        return evidence_file(root / path, root)
    route = SimpleNamespace(check=lambda: None, input_hash='source', limits=Limits(), encode=list)
    provider = Provider()
    dispatch = BoundDispatch(provider, root / 'successor/calls', route)
    stage = put('stage.json', {'grant_hash': 'grant'})
    account = put('account.json', {'input_hash': 'source'})
    rows, contracts, outcomes, charges, requests = {}, [], [], [], []
    schema = {'type': 'object', 'additionalProperties': False,
        'properties': {'conclusion': {'type': 'string'}}, 'required': ['conclusion']}
    for i in range(3):
        key = 'reduce-q-0-' + str(i)
        request = {'task': 'SYNTHESIZE_FINDINGS', 'records': [], 'payload': {'case': i}}
        requests.append(request)
        prepared = prepare(request, schema)
        wire_hash = digest(prepared['request'])
        result = ({'status': 'VALIDATED', 'value': {'conclusion': 'Retained response.'},
            'provenance': {'allowance_slot': 1, 'request_hash': wire_hash}}
            if i == 0 else {'status': 'FAILED', 'error': 'E_RESOURCE_LIMIT',
                'reason': 'Shared service circuit open; continuation required'})
        identity = dispatch.request_identity(request, schema)
        rows[key] = {'identity': identity, 'status': result['status'], 'result_hash': digest(result)}
        contracts.append({'key': key, 'identity': identity})
        outcomes.append({'key': key, 'result': result, 'dispatch_result_hash': digest(result)})
        for name, content in (('request', request), ('schema', schema), ('reference-binding', prepared), ('result', result)):
            put('old/calls/' + key + '/' + name + '.json', content)
        if i < 2:
            slot = i + 1
            charges.append({'stage_hash': stage['sha256'], 'request_hash': wire_hash})
            directory = f'provider/{slot:04}-{wire_hash[:16]}'
            files = {'request.json': prepared['request'], 'schema.json': prepared['schema']}
            if i == 0: files['result.json'] = result['value']
            records = {}
            for name, content in files.items():
                ref = put(directory + '/' + name, content)
                records[name] = {'bytes': (root / ref['path']).stat().st_size, 'retained_sha256': ref['sha256']}
            event = {'type': 'turn.completed'} if i == 0 else {'type': 'turn.failed',
                'error': {'message': 'stream disconnected before completion: stream closed before response.completed'}}
            path = root / directory / 'events.jsonl'
            events = [event] if i == 0 else [{'type': 'error', 'message': event['error']['message']}, event]
            path.write_text(''.join(json.dumps(e) + '\n' for e in events))
            records['events.jsonl'] = {'bytes': path.stat().st_size, 'retained_sha256': evidence_file(path, root)['sha256']}
            put(directory + '/manifest.json', {'allowance_slot': slot, 'request_hash': wire_hash,
                'complete_output_present': i == 0, 'files': records})
    journal = put('old/calls/dispatch.json', {'input_hash': 'source', 'calls': rows})
    outcome = put('outcome.json', {'results': outcomes})
    old_phase = put('phase.json', {'status': 'INCOMPLETE', 'admission': stage, 'outcome': outcome,
        'contract': {'input_hash': 'source', 'calls': contracts}})
    ledger = put('ledger.json', {'grant_hash': 'grant', 'calls': charges})
    manifest = recovery.build(root, old_phase, journal, ledger, dispatch.provider_binding, 'provider')
    pointer = put('synthesis.json', manifest)
    combined = put('combined.json', {'profile': recovery.PROFILE, 'input_hash': 'source',
        'account': account, 'synthesis': pointer})
    return SimpleNamespace(put=put, route=route, provider=provider, dispatch=dispatch,
        manifest=manifest, pointer=pointer, combined=combined, account=account, requests=requests, schema=schema)


def test_complete_mixed_census_and_exact_success_reuse(tmp_path):
    f = fixture(tmp_path)
    recovery.load(tmp_path, f.pointer, 'source', provider_binding=f.dispatch.provider_binding)
    for i, request in enumerate(f.requests):
        result = retained_response(tmp_path, f.combined, 'reduce-q-0-' + str(i), request,
            f.schema, f.dispatch.request_identity(request, f.schema), 'source', limits=f.route.limits)
        assert (result is not None) == (i == 0)
    assert not f.provider.calls


def test_phase_budgets_missing_requests_and_reload_does_not_redispatch(tmp_path):
    f = fixture(tmp_path)
    f.dispatch.retained_initial = (tmp_path, f.combined)
    product = SimpleNamespace(root=tmp_path, directory=tmp_path / 'successor', route=f.route,
        dispatch=f.dispatch, requirement_account_recovery=f.account,
        failure=lambda exc: {'status': 'FAILED', 'reason': str(exc)})
    admitted = []
    def admit(name, count):
        admitted.append(count)
        return {'test': True}
    calls = [{'key': 'reduce-q-0-' + str(i), 'request': request, 'schema': f.schema,
        'validate': lambda value: None} for i, request in enumerate(f.requests)]
    out = phase.execute(product, 'reduction-q-0', calls, implementation_identity='successor', admit=admit)
    assert out['execution_complete'] and admitted == [2] and len(f.provider.calls) == 2
    assert out['results'][0]['result']['value']['conclusion'] == 'Retained response.'
    assert phase.execute(product, 'reduction-q-0', calls, implementation_identity='successor', admit=admit) == out
    assert len(f.provider.calls) == 2 and admitted == [2]


@pytest.mark.parametrize('change', ['source', 'schema', 'provider', 'input', 'partial', 'charged_as_unsent',
    'unsent_as_charged', 'reserved', 'receipt_output', 'receipt_bytes', 'hidden_charge', 'result', 'wire'])
def test_adverse_evidence_refused_before_provider_call(tmp_path, change):
    f = fixture(tmp_path)
    value = deepcopy(f.manifest)
    if change in ('source', 'schema', 'provider', 'input'):
        request, schema = deepcopy(f.requests[0]), deepcopy(f.schema)
        identity = f.dispatch.request_identity(request, schema)
        if change == 'source': request['payload'] = {'case': 'changed'}
        if change == 'schema': schema['properties']['conclusion']['maxLength'] = 10
        if change == 'provider': identity = 'different-provider'
        with pytest.raises(LegalMathError):
            retained_response(tmp_path, f.combined, 'reduce-q-0-0', request, schema, identity,
                'changed' if change == 'input' else 'source')
        return
    if change == 'partial': del value['rows']['reduce-q-0-2']
    elif change == 'charged_as_unsent': value['rows']['reduce-q-0-1'].update(slot=None, receipt=None)
    elif change == 'unsent_as_charged': value['rows']['reduce-q-0-2']['slot'] = 2
    elif change in ('receipt_output', 'receipt_bytes'):
        ref = value['rows']['reduce-q-0-1']['receipt']
        data = json.loads((tmp_path / ref['path']).read_text())
        if change == 'receipt_output': data['complete_output_present'] = True
        else: data['files']['request.json']['retained_sha256'] = '0' * 64
        value['rows']['reduce-q-0-1']['receipt'] = f.put('changed-receipt.json', data)
    elif change == 'reserved':
        journal = json.loads((tmp_path / value['dispatch']['path']).read_text())
        journal['calls']['reduce-q-0-2']['status'] = 'RESERVED'
        value['dispatch'] = f.put('changed-dispatch.json', journal)
    elif change == 'hidden_charge':
        ledger = json.loads((tmp_path / value['ledger']['path']).read_text())
        ledger['calls'].append({**ledger['calls'][0], 'request_hash': 'unaccounted'})
        value['ledger'] = f.put('changed-ledger.json', ledger)
    elif change == 'result': value['rows']['reduce-q-0-0']['result'] = f.put('bad-result.json', {'status': 'FAILED'})
    elif change == 'wire': value['rows']['reduce-q-0-0']['reference_binding'] = f.put('bad-wire.json', {})
    pointer = f.put('changed.json', value)
    with pytest.raises(LegalMathError): recovery.load(tmp_path, pointer, 'source')
    assert not f.provider.calls


def test_composite_rejects_other_accounts_and_new_key_in_old_phase(tmp_path):
    f = fixture(tmp_path)
    with pytest.raises(LegalMathError): recovery.composite(tmp_path, f.combined, {'wrong': True}, 'source')
    with pytest.raises(LegalMathError):
        recovery.retained(tmp_path, f.pointer, 'reduce-q-0-99', {}, {}, 'unknown', 'source')
    assert recovery.retained(tmp_path, f.pointer, 'reduce-q-1-0', {}, {}, 'future', 'source') is None
