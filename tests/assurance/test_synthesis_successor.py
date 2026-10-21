"""A mixed settled phase must reuse successes and dispatch only missing output."""
from copy import deepcopy
from pathlib import Path
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


def fixture(root, *, source_records=None, locator_bindings=None):
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
        request = {'task': 'SYNTHESIZE_FINDINGS', 'records': deepcopy(source_records or []), 'payload': {'case': i}}
        if locator_bindings is not None:
            request['verified_locator_bindings'] = deepcopy(locator_bindings)
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


@pytest.mark.parametrize('change', [None, 'unreviewed', 'text', 'missing', 'duplicate',
    'binding', 'payload', 'schema'])
def test_reviewed_reconstruction_restores_only_exact_source_and_locator_order(tmp_path, change):
    records = [{'id': 's'+str(i), 'text': 'Original source '+str(i)} for i in range(2)]
    bindings = [{'record_id': r['id'], 'index_hash': 'source-index',
        'quote_ranges': [{'start': 0, 'end': 4}]} for r in records]
    f = fixture(tmp_path, source_records=records, locator_bindings=bindings)
    manifest = {**f.manifest, 'profile': recovery.REVIEWED}
    request, schema = deepcopy(f.requests[0]), deepcopy(f.schema)
    request['records'].reverse()
    request['verified_locator_bindings'].reverse()
    if change == 'unreviewed': manifest['profile'] = recovery.SYNTHESIS
    elif change == 'text': request['records'][0]['text'] = 'Changed source'
    elif change == 'missing': request['records'].pop()
    elif change == 'duplicate': request['records'][1] = deepcopy(request['records'][0])
    elif change == 'binding': request['verified_locator_bindings'][0]['quote_ranges'][0]['end'] = 5
    elif change == 'payload': request['payload']['case'] = 99
    elif change == 'schema': schema['properties']['conclusion']['maxLength'] = 5
    pointer = f.put('reviewed-order.json', manifest)
    if change is not None:
        with pytest.raises(LegalMathError):
            recovery.rewrite(tmp_path, pointer, 'reduce-q-0-0', request, schema, 'source')
    else:
        restored = recovery.rewrite(tmp_path, pointer, 'reduce-q-0-0', request, schema, 'source')
        assert restored == f.requests[0]
        held = recovery.retained(tmp_path, pointer, 'reduce-q-0-0', restored, schema,
            f.dispatch.request_identity(restored, schema), 'source')
        assert held[0]['status'] == 'VALIDATED'
    assert not f.provider.calls


def reviewed_retry_fixture(root):
    """The same stage paid for a no-output failure, then one exact success."""
    f = fixture(root)
    value = deepcopy(f.manifest)
    key = 'reduce-q-0-0'
    original = value['rows'][key]
    held = json.loads((root / original['receipt']['path']).read_text())
    first_directory = Path(original['receipt']['path']).parent
    last_directory = Path('provider') / ('0003-' + held['request_hash'][:16])
    for name in held['files']:
        source = root / first_directory / name
        destination = root / last_directory / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    f.put(last_directory / 'manifest.json', {**held, 'allowance_slot': 3})
    failed = {**held, 'complete_output_present': False,
        'files': {n: v for n, v in held['files'].items() if n != 'result.json'}}
    message = 'stream disconnected before completion: Our servers are currently overloaded. Please try again later.'
    events = [{'type': 'error', 'message': message},
        {'type': 'turn.failed', 'error': {'message': message}}]
    event_path = root / first_directory / 'events.jsonl'
    event_path.write_text(''.join(json.dumps(e) + '\n' for e in events))
    failed['files']['events.jsonl'] = {'bytes': event_path.stat().st_size,
        'retained_sha256': evidence_file(event_path, root)['sha256']}
    f.put(first_directory / 'manifest.json', failed)
    ledger = json.loads((root / value['ledger']['path']).read_text())
    ledger['calls'].append(deepcopy(ledger['calls'][0]))
    ledger_ref = f.put('retry-ledger.json', ledger)
    result = json.loads((root / original['result']['path']).read_text())
    result['provenance']['allowance_slot'] = 3
    f.put(original['result']['path'], result)
    dispatch = json.loads((root / value['dispatch']['path']).read_text())
    dispatch['calls'][key]['result_hash'] = digest(result)
    dispatch_ref = f.put('old/calls/dispatch.json', dispatch)
    phase_value = json.loads((root / value['phase']['path']).read_text())
    outcome = json.loads((root / phase_value['outcome']['path']).read_text())
    outcome['results'][0].update(result=result, dispatch_result_hash=digest(result))
    phase_value['outcome'] = f.put('retry-outcome.json', outcome)
    phase_ref = f.put('retry-phase.json', phase_value)
    manifest = recovery.build(root, phase_ref, dispatch_ref, ledger_ref,
        f.dispatch.provider_binding, 'provider', profile=recovery.REVIEWED)
    return f, manifest


def test_reviewed_historical_retry_authenticates_all_charges_and_reuses_success(tmp_path):
    f, manifest = reviewed_retry_fixture(tmp_path)
    pointer = f.put('reviewed.json', manifest)
    recovery.load(tmp_path, pointer, 'source')
    result, slots = recovery.checked_row(tmp_path, recovery.metadata(tmp_path, pointer, 'source'), 'reduce-q-0-0')
    assert slots == [1, 3] and result['provenance']['allowance_slot'] == 3
    assert not f.provider.calls


@pytest.mark.parametrize('change', ['unreviewed', 'missing_receipt', 'earlier_output', 'wrong_slot', 'unknown_failure'])
def test_historical_retry_rejects_lost_charges_or_unclassified_output(tmp_path, change):
    f, manifest = reviewed_retry_fixture(tmp_path)
    row = manifest['rows']['reduce-q-0-0']
    if change == 'unreviewed': manifest['profile'] = recovery.SYNTHESIS
    elif change == 'missing_receipt': del row['prior_transport_receipts']
    elif change == 'wrong_slot': row['prior_transport_receipts'][0]['slot'] = 2
    else:
        pointer = row['prior_transport_receipts'][0]['receipt']
        receipt_value = json.loads((tmp_path / pointer['path']).read_text())
        if change == 'earlier_output': receipt_value['complete_output_present'] = True
        else:
            path = tmp_path / Path(pointer['path']).parent / 'events.jsonl'
            path.write_text(json.dumps({'type': 'turn.failed', 'error': {'message': 'unknown failure'}}) + '\n')
            receipt_value['files']['events.jsonl'] = {'bytes': path.stat().st_size,
                'retained_sha256': evidence_file(path, tmp_path)['sha256']}
        row['prior_transport_receipts'][0]['receipt'] = f.put('changed-prior/manifest.json', receipt_value)
        parent = tmp_path / Path(row['prior_transport_receipts'][0]['receipt']['path']).parent
        source = tmp_path / Path(pointer['path']).parent
        for name in receipt_value['files']:
            (parent / name).write_bytes((source / name).read_bytes())
    with pytest.raises(LegalMathError):
        recovery.load(tmp_path, f.put('changed-reviewed.json', manifest), 'source')
    assert not f.provider.calls


def alias_binding(tmp_path, *, citations=False):
    from tests.assurance.test_downstream_capacity import product
    from tests.assurance.test_bounded_product import envelope
    from legalmath.interpretation.assurance.bounded_product import NOTE
    from legalmath.interpretation.assurance.phased.downstream_input import PROFILE
    p = product(tmp_path)
    records = [r for r in p.route.records.values() if r['kind'] == 'source']
    if citations:
        quotes = [{'record_id':r['id'], 'quote':r['text'], 'locator':''} for r in records[:2]]
        payload = {'z': [quotes[0], quotes[0]], 'a': [quotes[1], quotes[1]]}
    else:
        payload = {'z': ['a' * 64, 'a' * 64], 'a': ['b' * 64, 'b' * 64]}
    request = p.request('SYNTHESIZE_FINDINGS', envelope()['original_questions'][0], records,
        payload=payload, expected=['one'])
    request['downstream_input_profile'] = PROFILE
    saved = json.loads(json.dumps(prepare(request, NOTE), sort_keys=True))
    assert prepare(saved['original_request'], NOTE) != saved
    return saved


@pytest.mark.parametrize('citations', [False, True])
def test_reviewed_historical_hash_permutation_preserves_exact_saved_wire(tmp_path, citations):
    saved = alias_binding(tmp_path, citations=citations)
    snapshot = deepcopy(saved)
    assert recovery.historical_request(saved, reviewed=True) == saved['original_request']
    assert saved == snapshot
    with pytest.raises(LegalMathError):
        recovery.historical_request(saved)


@pytest.mark.parametrize('change', ['citation', 'alias_use', 'unused', 'duplicate'])
def test_citation_permutation_rejects_changed_quote_or_use(tmp_path, change):
    saved = alias_binding(tmp_path, citations=True)
    table = saved['request']['account_input_citations']
    if change == 'citation': table['q0']['locator'] = 'Wrong locator'
    elif change == 'alias_use': saved['request']['payload']['z'][0] = saved['request']['payload']['a'][0]
    elif change == 'unused': table['q' + str(len(table))] = {'quote':'unused'}
    else: table['q0'] = deepcopy(table['q1'])
    with pytest.raises(LegalMathError): recovery.historical_request(saved, reviewed=True)


@pytest.mark.parametrize('change', ['hash', 'alias_use', 'unused', 'duplicate', 'source', 'schema', 'decoder'])
def test_hash_permutation_does_not_accept_semantic_or_contract_changes(tmp_path, change):
    saved = alias_binding(tmp_path)
    table = saved['request']['account_identity_hashes']
    if change == 'hash': table['h0'] = 'f' * 64
    elif change == 'alias_use': saved['request']['payload']['z'][0] = saved['request']['payload']['a'][0]
    elif change == 'unused': table['h' + str(len(table))] = 'f' * 64
    elif change == 'duplicate': table['h0'] = table['h1']
    elif change == 'source': saved['original_request']['records'][0]['text'] = 'Changed source.'
    elif change == 'schema': saved['schema']['description'] = 'Changed schema'
    else: saved['selections']['s0'] = 'changed-span-identity'
    with pytest.raises(LegalMathError):
        recovery.historical_request(saved, reviewed=True)


def test_missing_synthesis_replays_saved_wire_and_success_cannot_be_dispatched(tmp_path):
    f = fixture(tmp_path)
    key = 'reduce-q-0-1'
    saved = json.loads((tmp_path / f.manifest['rows'][key]['reference_binding']['path']).read_text())
    assert recovery.replay_wire(tmp_path, f.combined, key, f.requests[1], f.schema, 'source') == saved
    with pytest.raises(LegalMathError):
        recovery.replay_wire(tmp_path, f.combined, 'reduce-q-0-0', f.requests[0], f.schema, 'source')
    assert not f.provider.calls
