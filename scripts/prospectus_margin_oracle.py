"""Independent review/character-map oracle; does not call the production checker."""
from collections import Counter
from copy import deepcopy
import json

from scripts.prospectus_margin_preparation import read, MARGINS, PREP

PREFIX = {'listed': 'basf-listed-notices-margin-',
          'redemption': 'basf-redemption-margin:', 'remaining': 'basf-remaining-margin:'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def same(a, b, message):
    if canonical(a) != canonical(b):
        raise ValueError(message)


def family(identity):
    return next((f for f, prefix in PREFIX.items() if identity.startswith(prefix)), None)


def original_groups():
    listed = read(MARGINS / 'attempt-001/scope-review.json')
    redemption = read(MARGINS / 'attempt-002/v3/scope-review.json')
    remaining = read(MARGINS / 'attempt-003/scope-review.json.gz')
    groups = [{'family': 'listed', 'id': 'listed-notice', 'applies': True,
        'governors': listed['governors'], 'printed_governors': listed['governors'],
        'body_ids': [f'basf-base-september-2022-exchange:p132:l{i}' for i in range(20, 30)],
        'premises': listed['premises']}]
    for f, packet in (('redemption', redemption), ('remaining', remaining)):
        for g in packet['groups']:
            raw = g.get('raw_governors', g.get('governors'))
            groups.append({'family': f, 'id': g['id'],
                'applies': g['applicable_under_supplied_final_terms'],
                'governors': raw, 'printed_governors': g.get('printed_governors', raw),
                'body_ids': [a['unit'] for a in g['raw_body']], 'raw_body': g['raw_body'],
                'premises': g['premises']})
    return groups


def expected_targets(graph, assembly, ids):
    """Enumerate direct recorded maps; never call segments/uses or admissions."""
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    result = []
    for identity in ids:
        unit = units[identity]
        if unit['role'] == 'EXCLUDED':
            continue
        if unit['role'] not in ('OPERATIVE', 'UNKNOWN'):
            raise ValueError('Unexpected original body role')
        maps = unit.get('character_map')
        if maps is None:
            source = raw[identity]
            if source['raw'] != unit['text'] or not source['visible']:
                raise ValueError('Unmapped original body')
            result.append({'source': {'unit': identity, 'document': source['document'],
                'source_sha256': source['source_sha256'], 'start': 0, 'end': len(source['raw']), 'quote': source['raw']},
                'use': {'unit': identity, 'start': 0, 'end': len(unit['text'])}})
            continue
        quotes = []
        for mapping in maps:
            if mapping.get('operation') not in ('Text', 'Field'):
                continue
            if mapping.get('source') is not None:
                a = {k: mapping['source'][k] for k in ('unit', 'document', 'source_sha256', 'start', 'end', 'quote')}
            else:
                source = raw[mapping['unit']]
                start, end = mapping['source_start'], mapping['source_end']
                a = {'unit': source['id'], 'document': source['document'], 'source_sha256': source['source_sha256'],
                     'start': start, 'end': end, 'quote': source['raw'][start:end]}
            if a['start'] == a['end']:
                continue
            source = raw[a['unit']]
            assert source['document'] == a['document'] and source['source_sha256'] == a['source_sha256']
            assert source['raw'][a['start']:a['end']] == a['quote']
            start, end = mapping['start'], mapping['end']
            assert unit['text'][start:end] == a['quote']
            quotes.append(a['quote'])
            result.append({'source': a, 'use': {'unit': identity, 'start': start, 'end': end}})
        assert ''.join(quotes) == unit['text']
    return result


def verify(products, answer, *, missing=()):
    graph, assembly = products['P1']['payload']['graph'], products['P2']['payload']['assembly']
    semantic = products['P3']['payload']
    review = answer['printed_margin_review']
    expected_status = 'COMPLETE_REVIEWED_SCOPE' if not missing else 'UNREVIEWED' if len(missing) == 3 else 'PARTIAL'
    assert review['status'] == expected_status
    assert review['missing_families'] == [f for f in PREFIX if f in missing]
    originals = original_groups()
    assert len(review['groups']) == len(originals) == 54
    by_id = {(g['family'], g['id']): g for g in review['groups']}
    assert len(by_id) == 54
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    pending = {r['unit']: r for r in answer['meaning_coverage']['selected_body_pending']}
    expected_edges, expected_dependencies = {}, []
    for original in originals:
        g = by_id[(original['family'], original['id'])]
        for key in ('family', 'id', 'applies', 'governors', 'printed_governors', 'premises'):
            same(g[key], original[key], 'Original scope differs: ' + key)
        if 'raw_body' in original:
            same(g['body'], original['raw_body'], 'Raw body extent changed')
        assert [a['unit'] for a in g['body']] == original['body_ids']
        for a in g['body']:
            source = raw[a['unit']]
            assert a['start'] == 0 and a['end'] == len(source['raw']) and a['quote'] == source['raw']
        targets = expected_targets(graph, assembly, original['body_ids'])
        same(g['selected_targets'], targets, 'Current exact selected body differs from direct source maps')
        assert bool(targets) is original['applies']
        same(g['unresolved_body_meanings'], [pending[i] for i in original['body_ids'] if i in pending],
             'Unknown body meanings hidden or fabricated')
        assert g['review_present'] is (original['family'] not in missing)
        ids = []
        for governor in original['printed_governors'] if original['applies'] else []:
            f = original['family']
            suffix = governor['unit'].rsplit(':l', 1)[1] if f == 'listed' else original['id'] + ':' + governor['unit'].split(':', 1)[1]
            identity = PREFIX[f] + suffix
            ids.append(identity)
            if f in missing:
                continue
            expected_edges[identity] = {'from': governor, 'to': targets, 'questions': ['Q1', 'Q2'], 'kind': 'governs'}
            for q in ('Q1', 'Q2'):
                resolved = all(units[t['use']['unit']]['role'] == 'OPERATIVE' and q in units[t['use']['unit']]['questions'] for t in targets)
                expected_dependencies.append({'id': 'governing:' + identity + ':' + q,
                    'status': 'RESOLVED' if resolved else 'UNRESOLVED', 'questions': [q]})
        assert g['edge_ids'] == ids
    edges = semantic['interpretation_input']['governing_admission']['governing']
    actual_edges = {e['id']: {k: e[k] for k in ('from', 'to', 'questions', 'kind')} for e in edges if family(e['id'])}
    same(actual_edges, expected_edges, 'Actual consumer governing input differs from original scopes')
    for f in missing:
        expected_dependencies.append({'id': 'margin-scope:' + f, 'status': 'UNRESOLVED', 'questions': ['Q1', 'Q2']})
    all_deps = {d['id']: d for d in semantic['dependencies']}
    for d in expected_dependencies:
        same({k: all_deps[d['id']][k] for k in d}, d, 'Independent governing dependency status differs')
    expected_unknown = {d['id'] for d in expected_dependencies if d['status'] == 'UNRESOLVED'}
    assert set(review['unresolved_dependency_ids']) == expected_unknown
    for q in ('Q1', 'Q2'):
        expected_q = {d['id'] for d in expected_dependencies if d['status'] == 'UNRESOLVED' and q in d['questions']}
        assert expected_q <= set(answer['questions'][q]['unresolved'])
        for v in answer['questions'][q].get('subquestions', {}).values():
            assert expected_q <= set(v['unresolved'])
        assert answer['questions']['Q3']['value'][q]['complete'] is False
    ledger = read(MARGINS / 'attempt-003/cumulative-margin-ledger.json')['occurrences']
    expected_occurrences = [{k: row[k] for k in ('source', 'role', 'status', 'current_role')} for row in ledger]
    same(review['occurrences'], expected_occurrences, 'Original occurrence inventory changed')
    assert len(review['occurrences']) == 522
    assert sum(o['current_role'] == 'HEADER' for o in review['occurrences']) == 26
    for key in ('automatic_discovery', 'all_body_meanings_established', 'independent_legal_acceptance', 'actual_event_established'):
        assert review[key] is False
    assert answer['may_execute_transaction'] is False
    return {'groups': 54, 'occurrences': 522, 'selected_edges': len(expected_edges),
        'unresolved_governing_dependencies': len(expected_unknown), 'status': review['status'],
        'unresolved_body_groups': [g['id'] for g in review['groups'] if g['unresolved_body_meanings']]}
