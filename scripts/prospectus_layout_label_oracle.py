"""Check against authored raw pieces; do not call projection or label scanners."""


def verify(case, report):
    assert case['expected_status'] == 'PASS'
    accounting = report['source_accounting']
    assert accounting['selected'] == case['expected_segments']
    assert accounting['excluded'] == case['expected_excluded']
    units = {u['id']: u for u in case['raw_units']}
    coverage = {identity: [] for identity in units}
    for part in accounting['selected'] + accounting['excluded']:
        assert part['quote'] == units[part['unit']]['raw'][part['start']:part['end']]
        coverage[part['unit']].extend(range(part['start'], part['end']))
    assert all(sorted(coverage[k]) == list(range(len(u['raw']))) for k, u in units.items())
    assert accounting['original_characters'] == sum(len(u['raw']) for u in units.values())
    expected_views = {item['self_ref']: item['text'] for item in case['layout']['texts']}
    generated = []
    for view in report['projection']['mappings']:
        assert view['text'] == expected_views[view['item']]
        expected_map = []
        offset = 0
        for index, part in enumerate(view['segments']):
            if index:
                generated.append({'item': view['item'], 'start': offset, 'end': offset + 1, 'text': '\n'})
                offset += 1
            assert part['output_start'] == offset
            assert part['quote'] == units[part['unit']]['raw'][part['start']:part['end']]
            expected_map.extend({'output': offset + i, 'unit': part['unit'],
                'source_offset': part['start'] + i, 'character': char}
                for i, char in enumerate(part['quote']))
            offset += len(part['quote'])
            assert part['output_end'] == offset
        assert view['characters'] == expected_map and offset == len(view['text'])
    assert accounting['generated'] == generated
    names = [name for region in report['regions'] for name in region['name_provenance']]
    assert [{k: r[k] for k in ('label', 'source_pieces')} for r in names] == case['expected_names']
    assert [r['label'] for region in report['regions'] for r in region['use_provenance']] == case['expected_use_labels']
    assert sorted({i['kind'] for r in report['regions'] for i in r['labels']['issues']}) == sorted(case['expected_issue_kinds'])
    for region, view in zip(report['regions'], report['projection']['mappings']):
        assert region['item'] == view['item']
        for group, spans in (('name_provenance', 'names'), ('use_provenance', 'uses')):
            assert len(region[group]) == len(region['labels'][spans])
            for record, label in zip(region[group], region['labels'][spans]):
                a, b = label['start'], label['end']
                assert record['output_span'] == [a, b]
                assert record['formatting_spans'] == [
                    {k: s[k] for k in ('start', 'end', 'text')} for s in generated
                    if s['item'] == view['item'] and a <= s['start'] < s['end'] <= b]
                reconstructed = ''.join(p['quote'] for p in record['source_pieces'])
                # Formatting LFs have no original-PDF character. The authored
                # source pieces establish the remaining exact characters.
                source = ''.join(char for i, char in enumerate(view['text'])
                    if a <= i < b and not any(s['start'] <= i < s['end'] for s in record['formatting_spans']))
                assert reconstructed == source
    assert all(report[k] is False for k in
               ('raw_replaced', 'scope_admitted', 'meaning_admitted', 'extraction_completeness_established'))
    return {'status': 'PASS', 'source_characters': accounting['original_characters'],
            'names': len(names), 'source_accounting_exact': True}
