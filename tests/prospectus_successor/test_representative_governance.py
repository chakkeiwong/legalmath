"""Supplied governance meanings must remain sourced rules, not fulfilled duties."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.contracts import VERSION, digest
from legalmath.prospectus.successor.representative_governance import READINGS

TIME = '2026-01-01T00:00:00Z'


def request(tmp_path):
    path = tmp_path / 'source.txt'
    path.write_text('\f'.join(READINGS.values()))
    bundle = {'instrument_id': 'synthetic', 'purpose': 'review', 'issue_date': TIME,
              'effective_at': TIME, 'known_at': TIME, 'dependencies': [],
              'documents': [{'id': 'd', 'path': str(path), 'sha256': digest(path.read_bytes()),
                             'format': 'text', 'language': 'en', 'authority': 'Synthetic development source',
                             'document_date': TIME, 'known_from': TIME}]}
    graph = source_graph.build(bundle, tmp_path)
    nodes, operations = [], []
    for kind, unit in zip(READINGS, graph['units']):
        operations.append({'unit': unit['id'], 'role': 'OPERATIVE', 'reason': 'Explicit synthetic rule scope',
                           'source_text_sha256': unit['text_sha256'], 'context': 'whole'})
        node = {'id': kind, 'units': [unit['id']], 'spans': [{'unit': unit['id'], 'start': 0, 'end': len(unit['raw'])}],
                'quote': unit['raw'], 'effect': 'representative_governance', 'governance_kind': kind,
                'legal_reading': READINGS[kind], 'actor': 'common_representative', 'affected': 'holder',
                'modality': 'statement', 'election': 'none', 'assets': [], 'role': 'OPERATIVE',
                'polarity': True, 'questions': ['Q1', 'Q2'], 'conditions': [], 'exceptions': []}
        if kind == 'statutory_reference':
            node['references'] = [{'kind': 'reference', 'target': 'applicable-statute',
                                   'reason': 'Applicable historical statute not established'}]
        nodes.append(node)
    return {'version': VERSION, 'bundle': bundle, 'assembly': {'operations': operations},
            'clauses': nodes, 'scope': {'Q1': {'complete': False}, 'Q2': {'complete': False}}}


def current(data, root):
    p1 = service.source_product(data, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    p4, p5 = service.law_product(p1, p3), service.financial_product(p1, p2, p3)
    return service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), root, mode='current')


def test_four_supplied_rules_reach_current_answer_with_sources_and_limits(tmp_path):
    result = current(request(tmp_path), tmp_path)
    rows = result['representative_governance']
    assert [r['kind'] for r in rows] == list(READINGS)
    for row in rows:
        assert row['reading'] == READINGS[row['kind']]
        assert row['sources'][0]['quote'] == row['quote']
        assert row['actual_authority'] == row['actual_compliance'] == 'NOT_ESTABLISHED'
        assert row['applicable_statutory_requirements'] == 'NOT_ESTABLISHED'
        assert row['reading_status'] == 'SUPPLIED_CONTRACTUAL_INTERPRETATION'
        assert row['independent_legal_acceptance'] is False
    assert rows[-1]['references'][0]['resolved'] is False
    for q in ('Q1', 'Q2'):
        assert result['questions'][q]['status'] == 'UNKNOWN'
        assert 'Missing reference target: applicable-statute' in result['questions'][q]['unresolved']
    assert result['questions']['Q3']['status'] == 'PARTIAL'
    assert not result['may_execute_transaction']


@pytest.mark.parametrize('field,value', [
    ('actor', 'issuer'), ('affected', 'issuer'), ('election', 'holder'),
    ('assets', ['common']), ('role', 'UNKNOWN'), ('polarity', False),
    ('modality', 'performed'), ('conditions', ['mandate']), ('exceptions', ['exception']),
    ('governance_kind', 'exercised_power'), ('legal_reading', 'An effective mandate exists.'),
    ('actual_authority', True), ('actual_compliance', True), ('independent_legal_acceptance', True),
])
def test_wrong_typed_rule_or_actual_claim_refused(tmp_path, field, value):
    data = request(tmp_path)
    data['clauses'][0][field] = value
    with pytest.raises(ValueError):
        current(data, tmp_path)


@pytest.mark.parametrize('change', ['quote', 'start', 'end', 'excluded'])
def test_changed_source_or_excluded_clause_refused(tmp_path, change):
    data = request(tmp_path)
    node = data['clauses'][0]
    if change == 'quote':
        node['quote'] = 'A different rule.'
    elif change == 'start':
        node['spans'][0]['start'] = 1
    elif change == 'end':
        node['spans'][0]['end'] += 1
    else:
        data['assembly']['operations'][0]['role'] = 'EXCLUDED'
    with pytest.raises(ValueError):
        current(data, tmp_path)


def test_statutory_dependency_cannot_be_silently_dropped(tmp_path):
    data = request(tmp_path)
    data['clauses'][-1].pop('references')
    with pytest.raises(ValueError, match='onward dependency'):
        current(data, tmp_path)


def test_omitted_rule_is_uncovered_and_existing_readings_remain(tmp_path):
    data = request(tmp_path)
    before = current(data, tmp_path)
    removed = data['clauses'].pop()
    after = current(data, tmp_path)
    assert after['representative_governance'] == before['representative_governance'][:-1]
    assert removed['units'][0] in after['questions']['Q1']['unresolved']
    assert after['questions']['Q3']['status'] == 'PARTIAL'


def test_old_unknown_clauses_do_not_gain_a_governance_claim(tmp_path):
    data = request(tmp_path)
    for node in data['clauses']:
        node['effect'] = 'unknown'
        node.pop('governance_kind')
        node.pop('legal_reading')
    result = current(data, tmp_path)
    assert 'representative_governance' not in result
    assert result['questions']['Q1']['status'] == 'UNKNOWN'
