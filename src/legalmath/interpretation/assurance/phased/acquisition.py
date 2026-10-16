"""One reviewed recovery of the settled original acquisition."""
from copy import deepcopy
from collections import Counter
from ..bounded_context import require
from ..monitor import save
from legalmath.canonical import digest
from .inventory import preserve, verify
from .phase import execute
from .evidence_store import save_exact


def plan(product, prior):
    require(prior['revision'] == product.route.input_hash, 'Recovery source input differs', 'E_INTEGRITY')
    packets, references = [], []
    for index, output in enumerate(prior['outputs']):
        if output['result']['status'] == 'VALIDATED':
            continue
        request = output['request']
        if request['task'] == 'REVIEW_REQUIREMENTS':
            references.append({'original_output': index, 'method': 'EXACT_INVENTORY',
                'result_hash': digest(output['result']),
                'scope': 'Original failure preserved; exact metadata inventory only. Substantive accounts still mandatory.'})
            continue
        ids = [r['id'] for r in request['records']]
        if request['task'] == 'READ_SOURCE':
            # An explicit changed-input recovery, not transient retry of the
            # failed generic invalid_request response. Preserve every source.
            groups = [[rid] for rid in ids]
            require(len(ids) > 1, 'Failed atomic source requires another reviewed remedy')
        else:
            require(request['task'] == 'REVIEW_SOURCE_DEPENDENCY' and
                'circuit' in output['result'].get('reason', '').lower(),
                'Completed invalid/adverse bridge cannot be automatically resampled', 'E_AUTHORITY')
            groups = [ids]
        for number, group in enumerate(groups):
            packet = product.route.make_packet(request['task'], group, reader=request['reader'],
                question_ids=[q['question_id'] for q in request['original_questions']],
                dependency=request.get('dependency'))
            packets.append({'key': f'acquisition-recovery-{index}-{number}',
                'packet': packet, 'original_output': index, 'original_result_hash': digest(output['result']),
                'method': 'REDESIGNED_INDIVIDUAL_SOURCE' if request['task'] == 'READ_SOURCE'
                    else 'PREVIOUSLY_NOT_DISPATCHED_JOINT_BRIDGE'})
    return packets, references


def recover(product, prior, *, admit, implementation_identity):
    inventory = preserve(product)
    verify(product, inventory)
    save_exact(product.directory / 'exact-inventory.json', inventory)
    packets, inventory_replacements = plan(product, prior)
    calls = [{'key': row['key'], 'request': row['packet']['request'], 'schema': row['packet']['schema'],
        'validate': lambda value, packet=row['packet']: product.route.validate_response(packet, value,
            decoded=getattr(product.provider, 'reference_transport', False))} for row in packets]
    save(product.directory / 'recovery-population.json', {'calls': [
        {k:v for k,v in row.items() if k != 'packet'} for row in packets],
        'inventory_replacements': inventory_replacements, 'logical_calls': len(calls),
        'prior_output_hashes': [digest(o) for o in prior['outputs']]})
    phase = execute(product, 'source-recovery', calls, implementation_identity=implementation_identity, admit=admit)
    results = {row['key']: row['result'] for row in phase['results']}
    outputs = deepcopy(prior['outputs'])
    recovered_by_index = {}
    for row in packets:
        result = results.get(row['key'], phase.get('resource_refusal',
            {'status':'FAILED','error':'E_DEPENDENCY','reason':'Recovery request not completed'}))
        recovered_by_index.setdefault(row['original_output'], []).append(result['status'] == 'VALIDATED')
        outputs.append({'packet_hash': row['packet']['packet_hash'], 'request': row['packet']['request'],
                        'result': result, 'recovery_of': row['original_output']})
    pending = {}
    for output in outputs:
        if output['result']['status'] != 'VALIDATED':
            continue
        for reading in output['result']['value']['records']:
            source = product.route.records[reading['id']]
            if source['kind'] != 'source':
                continue
            for text in reading['open_dependencies']:
                for qid in sorted(set(product.active_questions) & product.acquisition_questions(source)):
                    key = digest([qid, reading['id'], text])
                    pending.setdefault(key, {'id': 'dependency-' + key[:24], 'question_id': qid,
                        'origin_id': reading['id'], 'dependency': text, 'origin_readings': []})['origin_readings'].append(reading)
    previous = {r['id']: r for r in prior['discovered_dependencies']}
    dependencies = []
    for row in pending.values():
        old = previous.get(row['id'])
        if old:
            require(row['origin_readings'][:len(old['origin_readings'])] == old['origin_readings'],
                    'Recovery changed prior reading occurrences', 'E_INTEGRITY')
            row = {**deepcopy(old), **row}
        else:
            row.update(disposition='UNRESOLVED', execution_disposition='REQUIRES_INDIVIDUAL_GROUP_REVIEW',
                result={'status':'FAILED','error':'E_DEPENDENCY',
                    'reason':'Newly discovered dependency; no renewed exploratory allowance. Mandatory answer review remains.'})
        dependencies.append(row)
    require(set(previous) <= {r['id'] for r in dependencies}, 'Recovery lost old dependencies', 'E_INTEGRITY')
    affected = set()
    for index, output in enumerate(prior['outputs']):
        if output['result']['status'] == 'VALIDATED' or output['request']['task'] == 'REVIEW_REQUIREMENTS':
            continue
        if recovered_by_index.get(index) and all(recovered_by_index[index]):
            continue
        for record in output['request']['records']:
            affected.update(product.acquisition_questions(record))
    if prior['blocked']:
        affected.update(product.active_questions)
    result = {**deepcopy(prior), 'outputs': outputs, 'discovered_dependencies': dependencies,
        'execution_complete': not affected,
        'question_acquisition_complete': {q: q not in affected for q in product.active_questions},
        'recovery': {'profile':'reviewed-original-acquisition-recovery.v1', 'provider_calls_requested':len(calls),
            'original_failures_preserved':True, 'exact_inventory_substitutions':inventory_replacements,
            'source_recovery':[{k:v for k,v in r.items() if k != 'packet'} for r in packets],
            'exploratory_dependency_allowance_reset':False, 'legal_acceptance':False}}
    save_exact(product.directory / 'investigation.json', result)
    return result
