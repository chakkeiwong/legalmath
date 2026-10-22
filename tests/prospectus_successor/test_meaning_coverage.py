from copy import deepcopy

import pytest

from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.meaning_coverage import explain


def fixture():
    graph = {'units': [{'id': key, 'page': page} for key, page in [('body', 1), ('context', 2), ('header', 1)]]}
    construction = {'unit_accounting': [
        {'unit': 'body', 'role': 'BODY_CANDIDATE'},
        {'unit': 'context', 'role': 'OTHER_DOSSIER_SOURCE'},
        {'unit': 'header', 'role': 'PAGE_HEADER'}]}
    assembly = {'source_graph_sha256': digest(graph), 'units': [
        {'unit': 'body', 'text': 'A B.', 'role': 'OPERATIVE'},
        {'unit': 'context', 'text': 'C D', 'role': 'UNKNOWN'},
        {'unit': 'header', 'text': '1', 'role': 'HEADER'}]}
    def node(identity, unit, start, end, quote, effect):
        return {'id': identity, 'units': [unit], 'quote': quote, 'effect': effect,
                'spans': [{'unit': unit, 'start': start, 'end': end}]}
    clauses = {'assembly_sha256': digest(assembly), 'nodes': [
        node('known', 'body', 0, 1, 'A', 'none'),
        node('unknown', 'body', 2, 4, 'B.', 'unknown'),
        node('context', 'context', 0, 3, 'C D', 'unknown')]}
    return graph, construction, assembly, clauses


def test_other_sources_are_preserved_separately_without_promoting_scope():
    inputs = fixture()
    before = deepcopy(inputs)
    result = explain(*inputs)
    assert inputs == before
    groups = result['source_categories']
    assert groups['BODY_CANDIDATE']['active_characters'] == {
        'nonspace': 3, 'known_only': 1, 'unknown_only': 2, 'mixed': 0, 'uncovered': 0}
    assert groups['OTHER_DOSSIER_SOURCE']['active_characters']['unknown_only'] == 2
    assert groups['PAGE_HEADER']['active_characters']['nonspace'] == 0
    assert result['selected_body_pending'] == [{'unit': 'body', 'page': 1,
        'role_unresolved': False, 'unknown_characters': 2, 'uncovered_characters': 0}]
    assert not result['legal_scope_resolved'] and not result['independent_legal_acceptance']


def test_mixed_coverage_and_missing_punctuation_remain_visible():
    graph, construction, assembly, clauses = fixture()
    clauses['nodes'][1]['spans'][0]['end'] = 3
    clauses['nodes'][1]['quote'] = 'B'
    overlap = deepcopy(clauses['nodes'][0])
    overlap.update(id='overlap', effect='unknown')
    clauses['nodes'].append(overlap)
    result = explain(graph, construction, assembly, clauses)
    assert result['source_categories']['BODY_CANDIDATE']['active_characters'] == {
        'nonspace': 3, 'known_only': 0, 'unknown_only': 1, 'mixed': 1, 'uncovered': 1}


@pytest.mark.parametrize('change', ['missing-accounting', 'duplicate-accounting', 'duplicate-source',
    'unknown-category', 'stale-source', 'stale-assembly', 'wrong-quote', 'bad-interval', 'duplicate-node'])
def test_inconsistent_evidence_is_rejected(change):
    graph, construction, assembly, clauses = fixture()
    if change == 'missing-accounting': construction['unit_accounting'].pop()
    elif change == 'duplicate-accounting': construction['unit_accounting'].append(construction['unit_accounting'][0])
    elif change == 'duplicate-source': graph['units'].append(graph['units'][0])
    elif change == 'unknown-category': construction['unit_accounting'][0]['role'] = 'ADJUDICATED'
    elif change == 'stale-source': assembly['source_graph_sha256'] = '0' * 64
    elif change == 'stale-assembly': clauses['assembly_sha256'] = '0' * 64
    elif change == 'wrong-quote': clauses['nodes'][0]['quote'] = 'Z'
    elif change == 'bad-interval': clauses['nodes'][0]['spans'][0]['end'] = 9
    elif change == 'duplicate-node': clauses['nodes'].append(clauses['nodes'][0])
    with pytest.raises(ValueError):
        explain(graph, construction, assembly, clauses)
