"""Independent checks against frozen destination readings and original source bytes."""
from legalmath.prospectus.successor.contracts import digest

KEY = 'reference_addresses'


def verify_projection(projected, start, end, text, pieces, raw, operations=()):
    expected, cursor = [], start
    for index, piece in enumerate(pieces):
        a, b = max(start, piece['start']), min(end, piece['end'])
        if a >= b:
            continue
        assert a == cursor
        if piece['kind'] == 'SUPPLIED_OR_TRANSFORMED':
            assert piece['raw_binding'] is None and piece['operation'] == 'SUBSTITUTE'
            assert piece['text'] == text[piece['start']:piece['end']]
            prior = piece['replaced_raw_interval']
            candidates = []
            for operation in operations:
                if (operation['start'], operation['end'], operation['old'], operation['new'], operation['basis']) == (
                        prior['start'], prior['end'], prior['quote'], piece['text'], piece['basis']):
                    candidates.append(operation)
            assert len(candidates) == 1
            expected.append({'piece_index': index, 'selected_start': a, 'selected_end': b,
                'text': text[a:b], 'kind': piece['kind'], 'source': None,
                'transformation': {'operation': candidates[0], 'basis': piece['basis'],
                    'replaced_raw_interval': prior, 'piece_start': piece['start'],
                    'piece_end': piece['end'], 'raw_quotation_established': False}})
            cursor = b
            continue
        source = piece.get('raw_binding')
        bound = None
        if source:
            assert source['end'] - source['start'] == piece['end'] - piece['start']
            left = source['start'] + a - piece['start']
            right = source['start'] + b - piece['start']
            original = raw[source['unit']]
            assert original['raw'][left:right] == text[a:b]
            assert original['text_sha256'] == digest(original['raw'].encode())
            assert all(original[k] == source[k] for k in ('document', 'source_sha256'))
            bound = {k: source[k] for k in ('unit', 'document', 'source_sha256')}
            bound.update(start=left, end=right, quote=text[a:b])
        else:
            assert piece['kind'] == 'GENERATED_SEPARATOR' and text[a:b].isspace()
        expected.append({'piece_index': index, 'selected_start': a, 'selected_end': b,
                         'text': text[a:b], 'kind': piece['kind'], 'source': bound})
        cursor = b
    assert cursor == end and projected == expected


def verify(actual, baseline, products, expected):
    assert {k: v for k, v in actual.items() if k not in (KEY, 'report_sha256')} == {
        k: v for k, v in baseline.items() if k != 'report_sha256'}
    assert actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'})
    report = actual[KEY]
    assert report['products_sha256'] == digest(products)
    assert report['ordinary_answer_sha256'] == digest(baseline)
    for name in ('whole_task_complete', 'legal_truth_established', 'automatic_legal_interpretation', 'general_recall_established'):
        assert report[name] is False
    assert report['prior_answer_preserved'] is True and report['original_semantic_targets_preserved'] is True
    assert report['index_issues'] == []
    assembly = products['P2']['payload']['assembly']
    text = assembly['continuous_text']
    units = {u['unit']: u for u in assembly['units']}
    raw = {u['id']: u for u in products['P1']['payload']['graph']['units']}
    pieces = baseline['definition_sources']['source_pieces']
    contexts = {r['paragraph_start']: r for r in baseline['reference_scope_context']['contexts']}
    lexical = {r['start']: r for r in baseline['paragraph_reference_discovery']['discovery']['candidates']}
    refs = report['references']
    assert len(refs) == expected['logical_expressions'] == 29
    assert sorted(i for row in refs for i in row['paragraph_starts']) == sorted(contexts)
    matched = []
    for row, want in zip(refs, expected['references']):
        assert {k: row[k] for k in ('paragraph_starts', 'start', 'end', 'raw', 'statute')} == {
            k: want[k] for k in ('paragraph_starts', 'start', 'end', 'raw', 'statute')}
        assert row['raw'] == text[row['start']:row['end']]
        assert row['review_required'] is True
        assert row['legal_meaning_established'] is False and row['logical_meaning_established'] is False
        assert row['connectors'] == lexical[want['paragraph_starts'][0]]['connectors']
        verify_projection(row['source_projection'], row['start'], row['end'], text, pieces, raw)
        if want['statute']:
            assert row['status'] == 'EXTERNAL_STATUTE' and row['targets'] == [] and row['paths'] == []
            continue
        targets = [expected['targets'][i] for i in want['target_indices']]
        assert row['status'] == 'STRUCTURAL_ADDRESS' and row['issues'] == []
        assert row['section'] == targets[0]['section']
        assert row['paths'] == [target['path'] for target in targets]
        assert len(row['targets']) == len(targets)
        for target, wanted in zip(row['targets'], targets):
            assert {k: target[k] for k in wanted} == wanted
            assert target in report['index']
            assert target['text_sha256'] == digest(text[target['start']:target['end']].encode())
            assert target['heading_role'] == units[target['unit']]['role']
            assert target['context'] == units[target['unit']]['context']
            assert target['document'] == units[target['unit']]['source']['document']
            assert target['legal_meaning_established'] is False
            verify_projection(target['source_projection'], target['start'], target['end'], text, pieces, raw, assembly['operations'])
            unknown = sorted({p['source']['unit'] for p in target['source_projection']
                              if p['source'] and units[p['source']['unit']]['role'] == 'UNKNOWN'})
            assert target['unknown_source_units'] == unknown
            matched.append(target)
    exception = next(r for r in refs if r['paragraph_starts'] == [31593])
    f = next(n for n in exception['targets'] if n['path'] == ['1', 'f'])
    assert f['heading_role'] == 'UNKNOWN' and f['unknown_source_units']
    assert len([r for r in refs if r['status'] == 'EXTERNAL_STATUTE']) == 4
    return {'status': 'PASS', 'lexical_expressions': 30, 'logical_expressions': 29,
            'structural_expressions': 25, 'external_statutes': 4,
            'destination_occurrences': len(matched), 'unique_containers': len(expected['targets']),
            'complete_prior_answer_equal': True, 'unknown_default_f_preserved': True,
            'legal_truth_established': False}
