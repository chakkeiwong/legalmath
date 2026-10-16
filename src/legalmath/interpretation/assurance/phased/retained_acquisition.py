"""Validate an explicit source-acquisition checkpoint at the product boundary."""
from collections import defaultdict
from legalmath.canonical import digest
from ..bounded_context import require
from ..bounded_product import PROFILE
from ..integration_contract import read_evidence
from ..monitor import save


def load(product, reference):
    value = read_evidence(reference, product.root)
    product.route.check()
    require(value.get('profile') == PROFILE and value.get('revision') == product.route.input_hash,
            'Retained acquisition belongs to another input', 'E_INTEGRITY')
    outputs = value.get('outputs')
    require(isinstance(outputs, list) and outputs, 'Empty retained acquisition', 'E_INTEGRITY')
    complete = value.get('question_acquisition_complete', {})
    require(all(complete.get(q) is True for q in product.active_questions),
            'Retained acquisition is incomplete for selected questions', 'E_DEPENDENCY')
    original = [row for row in outputs if 'recovery_of' not in row]
    packets, blocked = product.reading_packets()
    expected = {row['packet_hash'] for row in packets if any(
        set(product.active_questions) & product.acquisition_questions(r) for r in row['request']['records'])}
    original_hashes = [row.get('packet_hash') for row in original]
    require(len(original_hashes) == len(set(original_hashes)) and expected <= set(original_hashes),
            'Retained acquisition omits planned source or bridge requests', 'E_INTEGRITY')
    for block in blocked:
        identities = block.get('record_ids', [block.get('id')])
        affected = set()
        if identities and all(i in product.route.records for i in identities):
            for identity in identities:
                affected.update(product.acquisition_questions(product.route.records[identity]))
        else:
            affected.update(block.get('question_ids', product.active_questions))
        require(not set(product.active_questions) & affected,
                'Blocked required source claimed complete', 'E_INTEGRITY')
    recovery = defaultdict(list)
    validated = 0
    for index, output in enumerate(outputs):
        request = output['request']
        packet = product.route.make_packet(request['task'], [r['id'] for r in request['records']],
            reader=request['reader'], question_ids=[q['question_id'] for q in request['original_questions']],
            dependency=request.get('dependency'))
        require(packet['request'] == request and packet['packet_hash'] == output['packet_hash'],
                'Retained acquisition request changed', 'E_INTEGRITY')
        result = output['result']
        require(result.get('status') in ('VALIDATED', 'FAILED'),
                'Unsettled retained acquisition', 'E_AUTHORITY')
        if result['status'] == 'VALIDATED':
            product.route.validate_response(packet, result['value'],
                decoded=getattr(product.provider, 'reference_transport', False))
            validated += 1
        if 'recovery_of' in output:
            prior = output['recovery_of']
            require(type(prior) is int and 0 <= prior < len(original) and prior < index,
                    'Foreign acquisition recovery parent', 'E_INTEGRITY')
            parent = original[prior]
            require(parent['result']['status'] == 'FAILED' and
                    all(request[k] == parent['request'][k] for k in
                        ('task', 'reader', 'original_questions', 'dependency')),
                    'Recovery changed original reading duty', 'E_INTEGRITY')
            recovery[prior].append(output)
    for index, output in enumerate(original):
        if output['packet_hash'] not in expected or output['result']['status'] == 'VALIDATED':
            continue
        if output['request']['task'] == 'REVIEW_REQUIREMENTS':
            # Deterministic metadata is checked separately; substantive accounts
            # are still mandatory before any conditional answer is prepared.
            substitutions = value.get('recovery', {}).get('exact_inventory_substitutions', [])
            require(any(r.get('original_output') == index and r.get('method') == 'EXACT_INVENTORY'
                        and r.get('result_hash') == digest(output['result']) for r in substitutions),
                    'Failed requirement observation lacks reviewed disposition', 'E_INTEGRITY')
            continue
        children = recovery[index]
        actual = [r['id'] for child in children for r in child['request']['records']]
        required = [r['id'] for r in output['request']['records']]
        require(children and len(actual) == len(set(actual)) and set(actual) == set(required) and
                all(child['result']['status'] == 'VALIDATED' for child in children),
                'Unrecovered source reading claimed complete', 'E_INTEGRITY')
    product.trace.append('CompleteInvestigation.run')
    save(product.directory / 'retained-acquisition-validation.json', {
        'profile': 'validated-retained-acquisition.v1', 'acquisition': reference,
        'input_hash': product.route.input_hash, 'active_questions': list(product.active_questions),
        'planned_requests': len(expected), 'retained_requests': len(outputs),
        'validated_responses': validated, 'new_provider_calls': 0,
        'legal_correctness_established': False})
    return value
