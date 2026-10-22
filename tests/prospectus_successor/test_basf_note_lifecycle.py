"""Selected section-12 meanings cannot become actual transaction findings."""
import pytest

from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.basf_note_lifecycle import RULES
from legalmath.prospectus.successor.contracts import VERSION, digest

TIME = '2026-01-01T00:00:00Z'


def request(tmp_path):
    path = tmp_path / 'source.txt'
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
                           'reason': 'Explicit synthetic section-12 rule scope',
                           'source_text_sha256': unit['text_sha256'], 'context': 'whole'})
        nodes.append({'id': kind, 'units': [unit['id']],
                      'spans': [{'unit': unit['id'], 'start': 0, 'end': len(unit['raw'])}],
                      'quote': unit['raw'], 'effect': 'basf_note_lifecycle',
                      'lifecycle_kind': kind, 'legal_reading': rule['reading'],
                      'rule_scope': rule['scope'], 'actor': 'issuer', 'affected': 'holder',
                      'modality': 'statement', 'election': 'none', 'assets': [],
                      'role': 'OPERATIVE', 'polarity': True, 'questions': ['Q1', 'Q2'],
                      'conditions': [], 'exceptions': []})
    return {'version': VERSION, 'bundle': bundle, 'assembly': {'operations': operations},
            'clauses': nodes, 'scope': {'Q1': {'complete': False}, 'Q2': {'complete': False}}}


def current(data, root):
    p1 = service.source_product(data, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    p4, p5 = service.law_product(p1, p3), service.financial_product(p1, p2, p3)
    return service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), root, mode='current')


def test_five_rules_reach_current_answer_without_actual_events(tmp_path):
    answer = current(request(tmp_path), tmp_path)
    rows = answer['basf_note_lifecycle']
    assert [row['kind'] for row in rows] == list(RULES)
    for row in rows:
        assert row['reading'] == RULES[row['kind']]['reading']
        assert row['rule_scope'] == RULES[row['kind']]['scope']
        assert row['sources'][0]['quote'] == row['quote']
        assert row['actual_event'] == row['actual_outstanding_balance'] == 'NOT_ESTABLISHED'
        assert row['independent_legal_acceptance'] is False
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'
    assert answer['questions']['Q2']['status'] == 'UNKNOWN'
    assert not answer['may_execute_transaction']


@pytest.mark.parametrize('field,value', [
    ('actor', 'holder'), ('affected', 'issuer'), ('election', 'issuer'),
    ('assets', ['principal']), ('role', 'UNKNOWN'), ('polarity', False),
    ('modality', 'performed'), ('conditions', ['bought']),
    ('exceptions', ['unpaid']), ('lifecycle_kind', 'loss'),
    ('legal_reading', 'The issuer already cancelled the notes.'),
    ('rule_scope', 'ANY_PURCHASE'), ('actual_event', True),
    ('outstanding_balance', 0), ('independent_legal_acceptance', True),
])
def test_wrong_rule_or_factual_claim_refused(tmp_path, field, value):
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


def test_omission_restores_unknown_without_changing_prior_rows(tmp_path):
    data = request(tmp_path)
    before = current(data, tmp_path)
    removed = data['clauses'].pop(3)
    after = current(data, tmp_path)
    assert after['basf_note_lifecycle'] == before['basf_note_lifecycle'][:3] + before['basf_note_lifecycle'][4:]
    assert removed['units'][0] in after['questions']['Q1']['unresolved']


def test_no_typed_rule_means_no_lifecycle_finding(tmp_path):
    data = request(tmp_path)
    for node in data['clauses']:
        node['effect'] = 'unknown'
        node.pop('lifecycle_kind')
        node.pop('legal_reading')
        node.pop('rule_scope')
    assert 'basf_note_lifecycle' not in current(data, tmp_path)
