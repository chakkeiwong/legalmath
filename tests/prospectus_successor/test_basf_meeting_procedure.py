"""Supplied meeting rules do not prove a meeting, vote or publication."""
import pytest

from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.basf_meeting_procedure import RULES, REFERENCES
from legalmath.prospectus.successor.contracts import VERSION, digest

TIME = '2026-01-01T00:00:00Z'


def request(tmp_path):
    path = tmp_path / 'meeting.txt'
    path.write_text('\f'.join(rule['reading'] for rule in RULES.values()))
    bundle = {'instrument_id': 'synthetic', 'purpose': 'review', 'issue_date': TIME,
              'effective_at': TIME, 'known_at': TIME, 'dependencies': [],
              'documents': [{'id': 'd', 'path': str(path), 'sha256': digest(path.read_bytes()),
                             'format': 'text', 'language': 'en',
                             'authority': 'Synthetic development source',
                             'document_date': TIME, 'known_from': TIME}]}
    graph = source_graph.build(bundle, tmp_path)
    nodes, operations = [], []
    for (kind, rule), unit in zip(RULES.items(), graph['units']):
        operations.append({'unit': unit['id'], 'role': 'OPERATIVE',
                           'reason': 'Explicit synthetic meeting rule scope',
                           'source_text_sha256': unit['text_sha256'], 'context': 'whole'})
        node = {'id': kind, 'units': [unit['id']],
                'spans': [{'unit': unit['id'], 'start': 0, 'end': len(unit['raw'])}],
                'quote': unit['raw'], 'effect': 'basf_meeting_procedure',
                'procedure_kind': kind, 'legal_reading': rule['reading'],
                'rule_scope': rule['scope'], 'actor': rule['actor'], 'affected': 'holder',
                'modality': 'statement', 'election': 'none', 'assets': [],
                'role': 'OPERATIVE', 'polarity': True, 'questions': ['Q1', 'Q2'],
                'conditions': [], 'exceptions': []}
        if kind in REFERENCES:
            node['references'] = [{'kind': 'reference', 'target': target,
                                   'reason': 'Named rule or historical source requires review'}
                                  for target in REFERENCES[kind]]
        nodes.append(node)
    return {'version': VERSION, 'bundle': bundle, 'assembly': {'operations': operations},
            'clauses': nodes, 'scope': {'Q1': {'complete': False}, 'Q2': {'complete': False}}}


def current(data, root):
    p1 = service.source_product(data, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    p4, p5 = service.law_product(p1, p3), service.financial_product(p1, p2, p3)
    return service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), root, mode='current')


def test_all_rules_reach_answer_without_actual_effect(tmp_path):
    answer = current(request(tmp_path), tmp_path)
    rows = answer['basf_meeting_procedure']
    assert [r['kind'] for r in rows] == list(RULES)
    for row in rows:
        assert row['reading'] == RULES[row['kind']]['reading']
        assert row['rule_scope'] == RULES[row['kind']]['scope']
        assert row['sources'][0]['quote'] == row['quote']
        assert row['actual_compliance'] == row['meeting_and_vote_effectiveness'] == 'NOT_ESTABLISHED'
        assert row['historical_statutory_requirements'] == 'NOT_ESTABLISHED'
        assert row['independent_legal_acceptance'] is False
    assert len(rows[2]['references']) == 1
    assert len(rows[4]['references']) == 2
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'
    assert answer['questions']['Q2']['status'] == 'UNKNOWN'
    assert not answer['may_execute_transaction']


@pytest.mark.parametrize('field,value', [
    ('actor', 'holder'), ('affected', 'issuer'), ('election', 'issuer'),
    ('assets', ['principal']), ('role', 'UNKNOWN'), ('polarity', False),
    ('modality', 'performed'), ('conditions', ['meeting']),
    ('exceptions', ['notice']), ('procedure_kind', 'effective_resolution'),
    ('legal_reading', 'The vote was counted.'), ('rule_scope', 'ANY_TIME'),
    ('actual_compliance', True), ('effective_resolution', True),
    ('counted_votes', 100), ('independent_legal_acceptance', True),
])
def test_wrong_rule_or_actual_claim_refused(tmp_path, field, value):
    data = request(tmp_path)
    data['clauses'][0][field] = value
    with pytest.raises(ValueError):
        current(data, tmp_path)


@pytest.mark.parametrize('change', ['quote', 'start', 'end', 'excluded'])
def test_changed_source_refused(tmp_path, change):
    data = request(tmp_path)
    node = data['clauses'][0]
    if change == 'quote':
        node['quote'] = 'Different words.'
    elif change == 'start':
        node['spans'][0]['start'] = 1
    elif change == 'end':
        node['spans'][0]['end'] += 1
    else:
        data['assembly']['operations'][0]['role'] = 'EXCLUDED'
    with pytest.raises(ValueError):
        current(data, tmp_path)


@pytest.mark.parametrize('kind', ['shareholder_vote_rules', 'german_seat_publication'])
def test_required_reference_cannot_disappear(tmp_path, kind):
    data = request(tmp_path)
    node = next(n for n in data['clauses'] if n['procedure_kind'] == kind)
    node['references'].pop()
    with pytest.raises(ValueError, match='dependencies'):
        current(data, tmp_path)


def test_omission_restores_unknown_and_preserves_other_rows(tmp_path):
    data = request(tmp_path)
    before = current(data, tmp_path)
    removed = data['clauses'].pop(7)
    after = current(data, tmp_path)
    assert after['basf_meeting_procedure'] == before['basf_meeting_procedure'][:7] + before['basf_meeting_procedure'][8:]
    assert removed['units'][0] in after['questions']['Q1']['unresolved']
