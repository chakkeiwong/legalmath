"""Authenticate one reviewed account continuation; no dispatch or new grant."""
from pathlib import Path
import json
from scripts.legal_mission_execution import read, verify, require
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_checkpoint import (
    retained_response, verify_no_output_receipts,
)
from legalmath.interpretation.assurance.bounded_references import prepare
from legalmath.interpretation.assurance.phased.synthesis_recovery import receipt

PROFILE = 'one-explicit-account-continuation.v1'
CHECKPOINT = 'exact-account-service-checkpoint.v1'
SCOPE = 'exact-account-service-continuation'


def checked(root, reference):
    """Require complete current census, exact reuse, and one charged outage."""
    verify(root, reference)
    value = read(root / reference['path'])
    require(value.get('profile') == CHECKPOINT and value.get('question') == 'p14',
        'Foreign account continuation checkpoint')
    for key in ('dispatch', 'phase', 'ledger', 'recovery', 'receipt'):
        verify(root, value[key])
    dispatch, phase, ledger = (read(root / value[key]['path'])
        for key in ('dispatch', 'phase', 'ledger'))
    require(dispatch['input_hash'] == phase['contract']['input_hash'] == value['input_hash']
        and phase['status'] == 'INCOMPLETE', 'Unsettled account continuation')
    key = value['failed_key']
    require(key == 'detail-87' and set(value['rows']) == set(dispatch['calls'])
        and len(value['rows']) == 36, 'Incomplete or foreign account census')
    require(len(phase['contract']['calls']) == 1
        and phase['contract']['calls'][0]['key'] == key,
        'Account failure phase includes another request')
    verify(root, phase['admission'])
    stage = read(root / phase['admission']['path'])
    verify(root, phase['outcome'])
    outcome = read(root / phase['outcome']['path'])
    require(stage['grant_hash'] == ledger['grant_hash']
        and outcome['execution_complete'] is False
        and len(outcome['results']) == 1 and outcome['results'][0]['key'] == key,
        'Account continuation changed stage or outcome')
    successes = []
    for name, row in value['rows'].items():
        require(set(row) == ({'request', 'schema', 'result', 'reference_binding', 'production_request'}
            if name == key else {'request', 'schema', 'result'}),
            'Account continuation has missing or invented evidence')
        for pointer in row.values():
            verify(root, pointer)
        request, schema, result = (read(root / row[k]['path'])
            for k in ('request', 'schema', 'result'))
        saved = dispatch['calls'][name]
        identity = digest({'request': request, 'schema': schema,
            'provider_binding': value['provider_binding']})
        require(saved['identity'] == identity and saved['status'] == result['status']
            and saved['result_hash'] == digest(result)
            and result['request_hash'] == digest(request), 'Account dispatch/result changed')
        if name == key:
            prepared = read(root / row['reference_binding']['path'])
            wire_request = read(root / row['production_request']['path'])
            require(wire_request == request and prepare(wire_request, schema) == prepared,
                'Account wire contract differs from its stored request')
            slots = [i for i, charge in enumerate(ledger['calls'], 1)
                if charge.get('stage_hash') == phase['admission']['sha256']
                and charge['request_hash'] == digest(prepared['request'])]
            require(result['status'] == 'FAILED'
                and result.get('error') == 'E_RESOURCE_LIMIT'
                and 'service circuit open' in result.get('reason', '')
                and slots == [value['failed_slot']]
                and phase['contract']['calls'][0]['identity'] == identity
                and outcome['results'][0]['result'] == result
                and outcome['results'][0]['dispatch_result_hash'] == saved['result_hash'],
                'Account continuation lacks its exact failed dispatch')
            held, data = receipt(root, value['receipt'], value['failed_slot'], prepared)
            require(held['complete_output_present'] is False,
                'Completed account cannot receive a transport continuation')
            events = [json.loads(line) for line in data['events.jsonl'].splitlines() if line.strip()]
            messages = [str(e.get('message', '')) + ' ' + str(e.get('error', {}).get('message', ''))
                for e in events if e.get('type') in ('error', 'turn.failed')]
            require(any(e.get('type') == 'turn.failed' for e in events)
                and not any(any(marker in message.lower() for marker in (
                    'safety system', 'potentially unintended activity', 'policy violation', 'content policy'))
                    for message in messages),
                'Policy refusal or nonterminal receipt is not an account service continuation')
            verify_no_output_receipts(root, {'receipts': [value['receipt']]}, wire_request, schema)
        else:
            require(result['status'] == 'VALIDATED',
                'Account continuation changed the successful population')
            retained = retained_response(root, value['recovery'], name, request, schema,
                identity, value['input_hash'])
            require(retained is not None and retained[0] == result
                and saved.get('retained_initial') == retained[1],
                'Account successor changed a saved successful response')
            successes.append(name)
    require(len(successes) == 35
        and [i for i, row in enumerate(ledger['calls'], 1)
            if row.get('stage_hash') == phase['admission']['sha256']] == [value['failed_slot']],
        'Account continuation charge census differs')
    return value


def validate(root, revision, spec):
    service = revision['service_continuation']
    require(spec.get('execution_scope') == SCOPE
        and service == spec['service_continuation']
        and service.get('profile') == PROFILE
        and service.get('question') == 'p14'
        and service.get('failed_key') == 'detail-87'
        and service.get('failed_slot') == 2333
        and service.get('maximum_explicit_redispatches') == 1
        and service.get('automatic_replacements') == 0
        and not service.get('maximum_response_corrections')
        and not revision.get('synthesis_successors')
        and revision['account_successor'] == spec.get('account_successor')
        and revision['successor_replay'] == spec.get('successor_replay'),
        'Unreviewed exact account continuation')
    verify(root, revision['prior_binding'])
    prior = read(root / revision['prior_binding']['path'])
    require(service['prior_scope'] == prior['phase_service_scope'], 'Foreign account service predecessor')
    for key in ('prior_scope', 'prior_circuit', 'prior_replacements'):
        verify(root, service[key])
    circuit, replacements = (read(root / service[k]['path']) for k in ('prior_circuit', 'prior_replacements'))
    require(circuit['open'] and circuit['stage_hash'] == service['prior_scope']['sha256']
        and circuit['failed_slots'] == [service['failed_slot']]
        and len(replacements['charges']) == replacements['maximum'] == 48,
        'Account continuation changed circuit or replacement charges')
    value = checked(root, revision['account_successor'])
    require(value['ledger'] == revision['prior_ledger']
        and value['recovery'] == revision['recoveries']['p14']
        and value['failed_key'] == service['failed_key']
        and value['failed_slot'] == service['failed_slot'], 'Account continuation changed predecessor')
    verify(root, revision['successor_replay'])
    replay = read(root / revision['successor_replay']['path'])
    require(replay.get('verdict') == 'PASS' and replay.get('provider_calls') == 0
        and replay.get('ledger_unchanged') is True
        and replay.get('ledger') == revision['prior_ledger']
        and replay.get('checkpoint') == revision['account_successor']
        and replay.get('production_reconstruction') is True
        and replay.get('exact_contracts') == 36 and replay.get('exact_successes') == 35
        and replay.get('first_missing_key') == service['failed_key']
        and replay.get('wire_contract_preserved') is True,
        'Account continuation lacks actual exact production replay')
    require(set(revision['round_reopened_nodes']) == {
            'current-binding', 'continuation-review', 'acquire-p14', 'acquire-p10', 'acquire-evidence'}
        and revision['attempt_increments'] == {
            'current-binding': 1, 'continuation-review': 1, 'acquire-p14': 1},
        'Account continuation reopened another owner or changed attempts')
    return value
