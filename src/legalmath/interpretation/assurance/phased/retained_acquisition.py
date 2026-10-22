"""Validate an explicit source-acquisition checkpoint at the product boundary."""
from collections import defaultdict
from legalmath.canonical import digest
from ..bounded_context import require
from ..bounded_product import PROFILE
from ..integration_contract import read_evidence
from ..monitor import save


def retained_parents(product, packets, original):
    """Match current duties to exact retained packets, allowing smaller batches.

    Capacity estimates govern future dispatch. A completed larger observation
    batch can cover a newly planned child without being sampled again. Every
    child must occur wholly in one original request with identical context;
    joint dependency readings cannot use this substitution. The caller still
    validates the complete parent response or all of its recorded recoveries.
    """
    hashes = [row.get('packet_hash') for row in original]
    require(len(hashes) == len(set(hashes)), 'Duplicate retained acquisition request', 'E_INTEGRITY')
    available = set(hashes)
    parents, substitutions = set(), []
    for packet in packets:
        if packet['packet_hash'] in available:
            parents.add(packet['packet_hash'])
            continue
        request = packet['request']
        candidates = []
        if (product.common_capacity_profile is not None and
                request['task'] in ('READ_SOURCE', 'REVIEW_REQUIREMENTS')):
            context = {k: v for k, v in request.items() if k != 'records'}
            for row in original:
                retained = row['request']
                if {k: v for k, v in retained.items() if k != 'records'} == context:
                    records = {r['id']: r for r in retained['records']}
                    if all(records.get(r['id']) == r for r in request['records']):
                        candidates.append(row['packet_hash'])
        require(len(candidates) == 1,
                'Retained acquisition omits planned source or bridge requests', 'E_INTEGRITY')
        parents.add(candidates[0])
        substitutions.append({'planned_packet': packet['packet_hash'], 'retained_parent': candidates[0]})
    return parents, substitutions


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
    selected = [row for row in packets if any(
        set(product.active_questions) & product.acquisition_questions(r) for r in row['request']['records'])]
    expected, substitutions = retained_parents(product, selected, original)
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
            inventory_substitutions = value.get('recovery', {}).get('exact_inventory_substitutions', [])
            require(any(r.get('original_output') == index and r.get('method') == 'EXACT_INVENTORY'
                        and r.get('result_hash') == digest(output['result']) for r in inventory_substitutions),
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
        'planned_requests': len(selected), 'required_retained_parents': len(expected),
        'capacity_rebatching': substitutions, 'retained_requests': len(outputs),
        'validated_responses': validated, 'new_provider_calls': 0,
        'legal_correctness_established': False})
    return value
