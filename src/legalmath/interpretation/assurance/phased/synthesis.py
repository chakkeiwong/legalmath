"""Source readings once, with exact dependency occurrence and follow-up mapping.

No semantic deduplication: each original occurrence and original dependency ID
is checked. Only redundant copies of an already supplied reading are removed.
"""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require
from legalmath.interpretation.assurance.monitor import save


def prepare(product, qid, investigation, details):
    require(investigation['revision'] == product.route.input_hash, 'Wrong acquisition input')
    product.route.check()
    notes, expected, occurrence_rows = [], {}, {}
    for oi, output in enumerate(investigation['outputs']):
        if output['result']['status'] != 'VALIDATED':
            continue
        for ri, row in enumerate(output['result']['value']['records']):
            source = product.route.records.get(row['id'])
            require(source is not None, 'Unknown acquired record')
            if source['kind'] != 'source' or qid not in product.acquisition_questions(source):
                continue
            identity = f'source-reading-{oi}-{ri}'
            note = {'id': identity, 'value': deepcopy(row),
                'role': 'Original source reading, including every proposed open dependency.',
                'dependency_checks': []}
            notes.append(note)
            occurrence_rows[identity] = note
            for di, text in enumerate(row['open_dependencies']):
                key = 'dependency-' + digest([qid, row['id'], text])[:24]
                item = expected.setdefault(key, {'id': key, 'question_id': qid,
                    'origin_id': row['id'], 'dependency': text,
                    'origin_readings': [], 'occurrences': []})
                require(item['dependency'] == text and item['origin_id'] == row['id'],
                        'Dependency identity collision')
                item['origin_readings'].append(deepcopy(row))
                item['occurrences'].append({'note_id': identity, 'dependency_position': di})

    actual = [r for r in investigation.get('discovered_dependencies', [])
              if r['question_id'] == qid]
    require(len(actual) == len({r['id'] for r in actual}) and
            {r['id'] for r in actual} == set(expected), 'Incomplete original dependency population')
    followups, mappings = [], []
    for row in actual:
        original = expected[row['id']]
        require(all(row[k] == original[k] for k in
                    ('id', 'question_id', 'origin_id', 'dependency', 'origin_readings')),
                'Dependency does not match its original reading occurrences')
        result = row['result']
        require(result['status'] in ('VALIDATED', 'FAILED'), 'Unsettled dependency result')
        mapping = {'id': row['id'], 'origin_id': row['origin_id'],
            'question_id': qid, 'dependency': row['dependency'],
            'occurrences': original['occurrences'],
            'original_dependency_hash': digest(row), 'result_hash': digest(result),
            'disposition': row['disposition']}
        check = {'dependency_id': row['id'], 'result_status': result['status'],
            'disposition': row['disposition']}
        if result['status'] == 'VALIDATED':
            require(isinstance(result.get('value'), dict), 'Missing dependency analysis')
            followups.append({'id': row['id'], 'value': deepcopy(result['value']),
                'origin_id': row['origin_id'], 'dependency': row['dependency'],
                'role': 'Actual follow-up analysis; original source reading is separately retained.'})
            mapping['followup_note_id'] = row['id']
            check['followup_note_id'] = row['id']
        else:
            check['failure'] = {k: deepcopy(result[k]) for k in ('error', 'reason') if k in result}
        for occurrence in original['occurrences']:
            occurrence_rows[occurrence['note_id']]['dependency_checks'].append({
                **deepcopy(check), 'dependency_position': occurrence['dependency_position']})
        mappings.append(mapping)

    requirements = [r for r in details if product.applicable(product.route.records[r['id']], qid)]
    require(all(r['result']['status'] == 'VALIDATED' for r in requirements),
            'Relevant requirement analysis incomplete', 'E_DEPENDENCY')
    account_notes = [{'id': r['id'], 'value': deepcopy(r['result']['value'])}
                     for r in requirements]
    rows = notes + account_notes + followups
    require(len(rows) == len({r['id'] for r in rows}), 'Synthesis identities collide')
    receipt = {'profile': 'source-reading-synthesis-representation.v1',
        'input_hash': product.route.input_hash, 'question_id': qid,
        'investigation_identity': {'revision': investigation['revision'],
            'output_hashes': [digest(r) for r in investigation['outputs']],
            'dependency_hashes': [digest(r) for r in investigation.get('discovered_dependencies', [])]},
        'rows_hash': digest(rows),
        'source_reading_count': len(notes), 'requirement_count': len(requirements),
        'followup_count': len(followups), 'dependency_count': len(actual),
        'dependency_mapping': mappings,
        'scope': 'Exact original occurrences and follow-up reasoning; no semantic dependency merger.'}
    save(product.directory / ('synthesis-representation-' + qid + '.json'), receipt)
    return rows, receipt

