from copy import deepcopy
import json
import pytest

from scripts import legal_integration_account_successor as successor
from scripts.legal_mission_execution import save, ref, read, Refused
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.bounded_checkpoint import retained_response


def fixture(root, failure='service'):
    def put(name, value):
        save(root / name, value)
        return ref(root, name)
    stage = put('stage.json', {'grant_hash': 'grant'})
    provider = {'provider': 'retained-provider'}
    schema = {'type': 'object', 'additionalProperties': False,
        'properties': {'conclusion': {'type': 'string'}}, 'required': ['conclusion']}
    rows, old, current, good = {}, {}, {}, {}
    for i in [*range(35), 87]:
        key = 'detail-' + str(i)
        request = {'task': 'ASSESS_ORIGINAL_REQUIREMENT', 'records': [], 'payload': {'case': i}}
        prepared = prepare(request, schema)
        identity = digest({'request': request, 'schema': schema, 'provider_binding': provider})
        result = ({'status': 'VALIDATED', 'request_hash': digest(request),
            'value': {'conclusion': 'Retained response ' + str(i)}} if i != 87 else
            {'status': 'FAILED', 'request_hash': digest(request), 'error': 'E_RESOURCE_LIMIT',
             'reason': 'Shared service circuit open; reviewed continuation required'})
        row = {k: put(f'calls/{key}/{k}.json', v) for k, v in {
            'request': request, 'schema': schema, 'result': result}.items()}
        if i == 87:
            row['reference_binding'] = put(f'calls/{key}/reference-binding.json', prepared)
            path = root / f'calls/{key}/production-request.json'
            path.write_text(json.dumps(request) + '\n')
            row['production_request'] = ref(root, path)
        rows[key] = row
        current[key] = {'identity': identity, 'status': result['status'], 'result_hash': digest(result)}
        if i != 87:
            old[key] = deepcopy(current[key])
            good[key] = {k: row[k] for k in ('request', 'schema', 'result')}
        else:
            failed = result
            failed_identity = identity
            wire = prepared
    original = put('old-dispatch.json', {'input_hash': 'source', 'calls': old})
    recovery = put('recovery.json', {'profile': 'bounded-exact-checkpoint.v2',
        'input_hash': 'source', 'dispatch': original, 'calls': good})
    for key in good:
        req, sch = (read(root / rows[key][name]['path']) for name in ('request', 'schema'))
        _, provenance = retained_response(root, recovery, key, req, sch, current[key]['identity'], 'source')
        current[key]['retained_initial'] = provenance
    dispatch = put('dispatch.json', {'input_hash': 'source', 'calls': current})
    outcome = put('outcome.json', {'execution_complete': False, 'results': [{
        'key': 'detail-87', 'result': failed, 'dispatch_result_hash': digest(failed)}]})
    phase = put('phase.json', {'status': 'INCOMPLETE', 'admission': stage, 'outcome': outcome,
        'contract': {'input_hash': 'source', 'calls': [{'key': 'detail-87', 'identity': failed_identity}]}})
    ledger = put('ledger.json', {'grant_hash': 'grant', 'calls':
        [{'stage_hash': 'historical', 'request_hash': str(i)} for i in range(2332)] +
        [{'stage_hash': stage['sha256'], 'request_hash': digest(wire['request'])}]})
    records = {}
    for name, val in {'request.json': wire['request'], 'schema.json': wire['schema']}.items():
        pointer = put('provider/' + name, val)
        records[name] = {'bytes': (root / pointer['path']).stat().st_size,
            'retained_sha256': pointer['sha256']}
    message = ('stream disconnected before completion: The service is temporarily unavailable. Please retry later.'
        if failure == 'service' else 'This request was blocked by our safety systems. Reason: Potentially unintended activity.')
    events = [{'type': 'error', 'message': message}, {'type': 'turn.failed', 'error': {'message': message}}]
    if failure == 'mixed':
        events.insert(0, {'type': 'error', 'message': 'stream disconnected before completion: temporarily unavailable'})
    path = root / 'provider/events.jsonl'
    path.write_text(''.join(json.dumps(e) + '\n' for e in events))
    records['events.jsonl'] = {'bytes': path.stat().st_size, 'retained_sha256': ref(root, path)['sha256']}
    receipt = put('provider/manifest.json', {'allowance_slot': 2333,
        'complete_output_present': False, 'request_hash': digest(wire['request']), 'files': records})
    checkpoint = put('checkpoint.json', {'profile': successor.CHECKPOINT, 'question': 'p14',
        'input_hash': 'source', 'provider_binding': provider, 'failed_key': 'detail-87', 'failed_slot': 2333,
        'dispatch': dispatch, 'phase': phase, 'ledger': ledger, 'recovery': recovery,
        'receipt': receipt, 'rows': rows})
    scope = put('scope.json', {'profile': 'test'})
    circuit = put('circuit.json', {'open': True, 'stage_hash': scope['sha256'], 'failed_slots': [2333]})
    replacements = put('replacements.json', {'maximum': 48, 'charges': list(range(48))})
    binding = put('binding.json', {'phase_service_scope': scope})
    service = {'profile': successor.PROFILE, 'question': 'p14', 'failed_key': 'detail-87',
        'failed_slot': 2333, 'maximum_explicit_redispatches': 1, 'automatic_replacements': 0,
        'prior_scope': scope, 'prior_circuit': circuit, 'prior_replacements': replacements}
    replay = put('replay.json', {'verdict': 'PASS', 'provider_calls': 0, 'ledger_unchanged': True,
        'ledger': ledger, 'checkpoint': checkpoint, 'production_reconstruction': True,
        'exact_contracts': 36, 'exact_successes': 35, 'first_missing_key': 'detail-87',
        'wire_contract_preserved': True})
    revision = {'service_continuation': service, 'account_successor': checkpoint, 'successor_replay': replay,
        'prior_binding': binding, 'prior_ledger': ledger, 'recoveries': {'p14': recovery},
        'round_reopened_nodes': ['current-binding', 'continuation-review', 'acquire-p14', 'acquire-p10', 'acquire-evidence'],
        'attempt_increments': {'current-binding': 1, 'continuation-review': 1, 'acquire-p14': 1}}
    spec = {'execution_scope': successor.SCOPE,
        **{k: deepcopy(revision[k]) for k in ('service_continuation', 'account_successor', 'successor_replay')}}
    return revision, spec, put


def test_exact_account_continuation_preserves_successes_and_limits(tmp_path):
    revision, spec, _ = fixture(tmp_path)
    assert successor.validate(tmp_path, revision, spec)['failed_slot'] == 2333


@pytest.mark.parametrize('failure', ['safety', 'mixed'])
def test_safety_refusal_is_not_service_recovery(tmp_path, failure):
    revision, spec, _ = fixture(tmp_path, failure)
    with pytest.raises(Refused, match='Policy refusal'):
        successor.validate(tmp_path, revision, spec)


@pytest.mark.parametrize('change', ['extra_retry', 'replacement', 'reopen_gatecoin', 'extra_attempt',
    'lost_branch', 'closed_circuit', 'lost_charges', 'different_owner', 'first_request', 'bad_replay',
    'changed_result', 'missing_success', 'completed_output', 'unknown_reservation', 'hidden_charge',
    'wire_schema', 'receipt_bytes', 'invented_binding', 'missing_binding', 'changed_production'])
def test_unreviewed_or_unproven_continuation_is_rejected(tmp_path, change):
    revision, spec, put = fixture(tmp_path)
    service = revision['service_continuation']
    checkpoint = read(tmp_path / revision['account_successor']['path'])
    if change == 'extra_retry': service['maximum_explicit_redispatches'] = 2
    elif change == 'replacement': service['automatic_replacements'] = 1
    elif change == 'reopen_gatecoin': revision['round_reopened_nodes'].append('acquire-gatecoin')
    elif change == 'extra_attempt': revision['attempt_increments']['acquire-p10'] = 1
    elif change == 'lost_branch': revision['round_reopened_nodes'].remove('acquire-evidence')
    elif change == 'different_owner': service['question'] = 'gatecoin'
    elif change == 'first_request': service['failed_key'] = 'detail-0'
    elif change == 'closed_circuit':
        circuit = read(tmp_path / service['prior_circuit']['path']); circuit['open'] = False
        service['prior_circuit'] = put('closed.json', circuit)
    elif change == 'lost_charges': service['prior_replacements'] = put('lost.json', {'maximum': 48, 'charges': []})
    elif change == 'bad_replay':
        replay = read(tmp_path / revision['successor_replay']['path']); replay['exact_successes'] = 34
        revision['successor_replay'] = put('bad-replay.json', replay)
    elif change == 'missing_success': del checkpoint['rows']['detail-0']
    elif change == 'changed_result':
        checkpoint['rows']['detail-0']['result'] = put('changed-result.json', {'status': 'VALIDATED', 'value': {}})
    elif change == 'unknown_reservation':
        dispatch = read(tmp_path / checkpoint['dispatch']['path']); dispatch['calls']['detail-87']['status'] = 'RESERVED'
        checkpoint['dispatch'] = put('uncertain.json', dispatch)
    elif change == 'hidden_charge':
        ledger = read(tmp_path / checkpoint['ledger']['path']); ledger['calls'].append({**ledger['calls'][-1], 'request_hash': 'hidden'})
        checkpoint['ledger'] = put('hidden-charge.json', ledger)
    elif change in ('completed_output', 'receipt_bytes'):
        receipt = read(tmp_path / checkpoint['receipt']['path'])
        if change == 'completed_output': receipt['complete_output_present'] = True
        else: receipt['files']['events.jsonl']['retained_sha256'] = '0' * 64
        checkpoint['receipt'] = put('provider/bad-receipt.json', receipt)
    elif change == 'wire_schema':
        wire = read(tmp_path / checkpoint['rows']['detail-87']['reference_binding']['path'])
        wire['schema']['required'] = []
        checkpoint['rows']['detail-87']['reference_binding'] = put('bad-wire.json', wire)
    elif change == 'invented_binding':
        checkpoint['rows']['detail-0']['reference_binding'] = checkpoint['rows']['detail-87']['reference_binding']
    elif change == 'missing_binding':
        del checkpoint['rows']['detail-87']['reference_binding']
    elif change == 'changed_production':
        checkpoint['rows']['detail-87']['production_request'] = put('bad-production.json', {})
    revision['account_successor'] = put('candidate.json', checkpoint)
    # Keep reviewed pointers coherent, so rejection exercises the actual guard.
    replay = read(tmp_path / revision['successor_replay']['path'])
    replay['checkpoint'] = revision['account_successor']
    revision['successor_replay'] = put('candidate-replay.json', replay)
    spec.update({k: deepcopy(revision[k]) for k in ('service_continuation', 'account_successor', 'successor_replay')})
    with pytest.raises((Refused, LegalMathError)):
        successor.validate(tmp_path, revision, spec)


def test_master_routes_reviewed_account_scope(tmp_path):
    from scripts import legal_integration_repair_execution as repair
    revision, spec, _ = fixture(tmp_path)
    assert repair.validate_synthesis_successor(tmp_path, revision, spec)['failed_slot'] == 2333
