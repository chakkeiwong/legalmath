"""Independent finite cases and adverse source/graph controls for resolution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.reference_resolution import resolve, reconcile

PREP = Path(__file__).resolve().parents[2] / 'docs/implementation/prospectus-execution-authority/reviews/reference-resolution-356'
CASES = json.loads((PREP / 'independent-cases.json').read_text())['cases']


@pytest.mark.parametrize('case', CASES, ids=[r['id'] for r in CASES])
def test_pre_candidate_fixtures(case):
    report = resolve(case['request'])
    assert len(report['mentions']) == len(case['expected'])
    for row, expected in zip(report['mentions'], case['expected']):
        assert row['raw'] == expected['raw']
        assert {k: row['resolution'][k] for k in ('status', 'section', 'paths')} == {
            k: expected[k] for k in ('status', 'section', 'paths')}
    assert report['legal_truth_established'] is report['whole_task_complete'] is False


def case(name):
    return deepcopy(next(c['request'] for c in CASES if c['id'] == name))


def graph_for(request):
    report = resolve(request)
    mention = report['mentions'][0]
    target = next(n for n in report['index'] if n['id'] in mention['resolution']['target_ids'])
    anchor = next(p['source'] for p in target['source_projection'] if p['source'])
    return {'version': 'reviewed-reference-graph.v1', 'raw_units': deepcopy(request['source']['raw_units']),
            'references': [{'id': 'edge', 'source': deepcopy(mention['source_projection'][0]['source']),
                            'targets': [deepcopy(anchor)]}]}


def test_graph_cannot_change_source_resolution():
    request = case('explicit')
    before = resolve(request)
    graph = graph_for(request)
    result = reconcile(request, before, graph)
    assert result['edges'][0]['reviewed_edge'] == graph['references'][0]
    assert result['edges'][0]['matches'][0]['source_relation'] == 'EXACT_SOURCE_MATCH'
    graph['references'][0]['targets'] = [graph['references'][0]['source']]
    alternate = reconcile(request, before, graph)
    assert alternate['resolution_sha256'] == result['resolution_sha256']
    assert alternate != result
    assert resolve(request) == before


@pytest.mark.parametrize('mutation', ['quote', 'offset', 'hash', 'raw', 'duplicate'])
def test_forged_graph_refused(mutation):
    request = case('explicit')
    graph = graph_for(request)
    if mutation == 'quote':
        graph['references'][0]['source']['quote'] += '!'
    elif mutation == 'offset':
        graph['references'][0]['source']['end'] += 1
    elif mutation == 'hash':
        graph['references'][0]['source']['source_sha256'] = '0' * 64
    elif mutation == 'raw':
        graph['raw_units'][0]['raw'] += '!'
        graph['raw_units'][0]['text_sha256'] = digest(graph['raw_units'][0]['raw'].encode())
    else:
        graph['references'].append(deepcopy(graph['references'][0]))
    with pytest.raises(ValueError):
        reconcile(request, resolve(request), graph)


def test_forged_resolution_refused_even_with_recomputed_digest():
    request = case('explicit')
    report = resolve(request)
    report['mentions'][0]['resolution']['section'] = '999'
    report['report_sha256'] = digest({k: v for k, v in report.items() if k != 'report_sha256'})
    with pytest.raises(ValueError, match='recomputed'):
        reconcile(request, report, graph_for(request))


def test_partial_source_is_not_promoted_to_complete_match():
    request = case('explicit')
    graph = graph_for(request)
    anchor = graph['references'][0]['source']
    unit = next(u for u in request['source']['raw_units'] if u['id'] == anchor['unit'])
    anchor['start'] -= 2
    anchor['end'] -= 4
    anchor['quote'] = unit['raw'][anchor['start']:anchor['end']]
    row = reconcile(request, resolve(request), graph)['edges'][0]['matches'][0]
    assert row['source_relation'] == 'PARTIAL_SOURCE_INTERSECTION'


def test_narrow_semantic_target_and_outside_target_preserved():
    request = case('explicit')
    graph = graph_for(request)
    target = graph['references'][0]['targets'][0]
    target['start'] += 1
    target['quote'] = target['quote'][1:]
    result = reconcile(request, resolve(request), graph)
    actual = result['edges'][0]['matches'][0]['targets'][0]
    assert actual['anchor'] == target
    assert actual['printed_destinations'][0]['relation'] == 'CONTAINED_IN_PRINTED_DESTINATION'
    # A supplied target that extends beyond a destination must remain intact.
    mention_unit = next(u for u in request['source']['raw_units'] if u['id'] == graph['references'][0]['source']['unit'])
    graph['references'][0]['targets'] = [{
        'unit': mention_unit['id'], 'document': mention_unit['document'],
        'source_sha256': mention_unit['source_sha256'], 'start': 0, 'end': len(mention_unit['raw']),
        'quote': mention_unit['raw']}]
    result = reconcile(request, resolve(request), graph)
    actual = result['edges'][0]['matches'][0]['targets'][0]
    assert actual['anchor'] == graph['references'][0]['targets'][0]
    assert actual['printed_destinations'][0]['relation'] == 'OUTSIDE_PRINTED_DESTINATION'


def test_partially_intersecting_target_not_called_contained():
    request = case('explicit')
    unit = request['source']['raw_units'][-1]
    prefix = 'Nicht ausgewählt. '
    unit['raw'] = prefix + unit['raw']
    unit['text_sha256'] = digest(unit['raw'].encode())
    for piece in request['source']['source_pieces']:
        if piece['raw_binding'] and piece['raw_binding']['unit'] == unit['id']:
            piece['raw_binding']['start'] += len(prefix)
            piece['raw_binding']['end'] += len(prefix)
    graph = graph_for(request)
    target = graph['references'][0]['targets'][0]
    target.update(start=0, end=len(unit['raw']), quote=unit['raw'])
    result = reconcile(request, resolve(request), graph)
    actual = result['edges'][0]['matches'][0]['targets'][0]
    assert actual['anchor'] == target
    assert actual['union_relation'] == 'PARTIAL_PRINTED_UNION_INTERSECTION'


def test_list_targets_checked_against_the_union():
    request = case('relative-list')
    graph = graph_for(request)
    report = resolve(request)
    for node in report['index']:
        if node['id'] in report['mentions'][0]['resolution']['target_ids'][1:]:
            graph['references'][0]['targets'].append(next(p['source'] for p in node['source_projection'] if p['source']))
    result = reconcile(request, report, graph)
    assert all(t['union_relation'] == 'CONTAINED_IN_PRINTED_DESTINATION_UNION'
               for t in result['edges'][0]['matches'][0]['targets'])
    assert any(c['relation'] == 'OUTSIDE_PRINTED_DESTINATION'
               for t in result['edges'][0]['matches'][0]['targets'] for c in t['printed_destinations'])


def test_cross_context_destination_refused():
    request = case('explicit')
    for row in request['layout'][2:]:
        row['context'] = 'other'
    assert resolve(request)['mentions'][0]['resolution']['status'] == 'UNRESOLVED_STRUCTURE'


def test_cross_document_destination_refused():
    request = case('explicit')
    changed = {u['id'] for u in request['source']['raw_units'][2:]}
    for unit in request['source']['raw_units'][2:]:
        unit['document'] = 'other'
    for piece in request['source']['source_pieces']:
        if piece['raw_binding'] and piece['raw_binding']['unit'] in changed:
            piece['raw_binding']['document'] = 'other'
    assert resolve(request)['mentions'][0]['resolution']['status'] == 'UNRESOLVED_STRUCTURE'


def test_supplied_citation_is_not_raw_evidence():
    request = case('explicit')
    piece = request['source']['source_pieces'][2]
    piece.update(kind='SUPPLIED_OR_TRANSFORMED', raw_binding=None)
    assert resolve(request)['mentions'][0]['resolution']['status'] == 'UNRESOLVED_SOURCE'


def test_shared_law_qualifier_preserved():
    request = case('shared-law')
    report = resolve(request)
    assert report['mentions'][0]['resolution']['law_qualifier']['shared'] is True
    assert all(not r['resolution']['target_ids'] for r in report['mentions'])


def test_unbound_shared_law_qualifier_cannot_authorize_resolution():
    request = case('shared-law')
    source = request['source']
    piece = source['source_pieces'][-1]
    split = piece['text'].index('BeispielG')
    prefix, suffix = deepcopy(piece), deepcopy(piece)
    prefix['end'] = piece['start'] + split
    prefix['text'] = piece['text'][:split]
    prefix['raw_binding']['end'] = split
    prefix['raw_binding']['quote'] = prefix['text']
    suffix.update(start=prefix['end'], text=piece['text'][split:], kind='SUPPLIED_OR_TRANSFORMED', raw_binding=None)
    source['source_pieces'][-1:] = [prefix, suffix]
    assert all(r['resolution']['status'] == 'UNRESOLVED_SOURCE' for r in resolve(request)['mentions'])


def test_layout_coverage_and_headers_validated():
    request = case('explicit')
    request['layout'][0]['role'] = 'OPERATIVE'
    with pytest.raises(ValueError, match='header role'):
        resolve(request)
    request = case('explicit')
    request['layout'].pop()
    with pytest.raises(ValueError, match='coverage'):
        resolve(request)
