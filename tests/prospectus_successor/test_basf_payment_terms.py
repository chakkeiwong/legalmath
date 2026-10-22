"""Payment conditions survive the current consumer and refuse event assertions."""
import pytest

from legalmath.prospectus.successor import service, source_graph
from legalmath.prospectus.successor.basf_payment_terms import RULES, REFERENCES
from legalmath.prospectus.successor.contracts import VERSION, digest

TIME = '2026-01-01T00:00:00Z'


def request(tmp_path):
    path = tmp_path / 'payments.txt'
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
                           'reason': 'Explicit synthetic payment rule scope',
                           'source_text_sha256': unit['text_sha256'], 'context': 'whole'})
        nodes.append({'id': 'basf-payment:' + kind, 'units': [unit['id']],
            'spans': [{'unit': unit['id'], 'start': 0, 'end': len(unit['raw'])}],
            'quote': unit['raw'], 'effect': 'basf_payment_terms', 'payment_kind': kind,
            'legal_reading': rule['reading'], 'rule_scope': rule['scope'],
            'actor': rule['actor'], 'affected': 'holder', 'modality': 'statement',
            'election': 'none', 'assets': [], 'role': 'OPERATIVE', 'polarity': True,
            'questions': ['Q1', 'Q2'], 'conditions': [], 'exceptions': [],
            'references': [{'kind': 'reference', 'target': target,
                            'reason': 'Supplied clause or unresolved historical law'}
                           for target in REFERENCES.get(kind, [])]})
    return {'version': VERSION, 'bundle': bundle, 'assembly': {'operations': operations},
            'clauses': nodes, 'scope': {'Q1': {'complete': False}, 'Q2': {'complete': False}}}


def current(data, root):
    p1 = service.source_product(data, root)
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    p4, p5 = service.law_product(p1, p3), service.financial_product(p1, p2, p3)
    return service.consume(dict(P1=p1, P2=p2, P3=p3, P4=p4, P5=p5), root, mode='current')


def test_payment_terms_preserve_qualifications_and_open_facts(tmp_path):
    answer = current(request(tmp_path), tmp_path)
    rows = {r['kind']: r for r in answer['basf_payment_terms']}
    assert len(rows) == 23
    assert 'right of withdrawal is waived' in rows['deposit_discharge']['reading']
    assert 'To the extent' in rows['deposit_discharge']['reading']
    assert all('(' + k + ')' in rows['gross_up']['reading'] for k in 'abcde')
    assert 'if later' in rows['gross_up']['reading']
    assert 'that payment-day delay' in rows['no_delay_interest']['reading']
    assert 'presentment' in rows['presentment']['reading']
    for row in rows.values():
        reconstructed = ' '.join(''.join(s['quote'] for s in g['sources']) for g in row['source_spans'])
        assert reconstructed == row['quote']
        assert row['actual_payment_tax_or_discharge'] == row['historical_law_applicability'] == 'NOT_ESTABLISHED'
        assert not row['independent_legal_acceptance']
    assert [(e['to'], e['resolved']) for e in rows['deposit_discharge']['references']] == [('basf-payment:court_deposit', True)]
    assert not rows['presentment']['references'][0]['resolved']
    assert answer['questions']['Q1']['status'] == answer['questions']['Q2']['status'] == 'UNKNOWN'
    assert not answer['may_execute_transaction']


@pytest.mark.parametrize('field,value', [
    ('actor', 'holder'), ('affected', 'issuer'), ('election', 'issuer'),
    ('assets', ['principal']), ('role', 'UNKNOWN'), ('polarity', False),
    ('modality', 'performed'), ('conditions', ['payment']),
    ('exceptions', ['tax']), ('payment_kind', 'actual_discharge'),
    ('legal_reading', 'All claims have been discharged.'), ('rule_scope', 'UNCONDITIONAL'),
    ('actual_payment', True), ('discharged_claims', True), ('paid_amount', 100),
    ('computed_interest', 100), ('independent_legal_acceptance', True),
])
def test_changed_condition_or_event_refused(tmp_path, field, value):
    data = request(tmp_path)
    data['clauses'][0][field] = value
    with pytest.raises(ValueError):
        current(data, tmp_path)


@pytest.mark.parametrize('change', ['quote', 'start', 'end', 'excluded'])
def test_changed_source_refused(tmp_path, change):
    data = request(tmp_path)
    node = data['clauses'][0]
    if change == 'quote':
        node['quote'] = 'The original text did not say this.'
    elif change == 'start':
        node['spans'][0]['start'] = 1
    elif change == 'end':
        node['spans'][0]['end'] += 1
    else:
        data['assembly']['operations'][0]['role'] = 'EXCLUDED'
    with pytest.raises(ValueError):
        current(data, tmp_path)


@pytest.mark.parametrize('kind', list(REFERENCES))
def test_required_dependency_cannot_disappear(tmp_path, kind):
    data = request(tmp_path)
    next(n for n in data['clauses'] if n['payment_kind'] == kind)['references'].pop()
    with pytest.raises(ValueError, match='dependencies'):
        current(data, tmp_path)


def test_deposit_does_not_supply_omitted_discharge_rule(tmp_path):
    data = request(tmp_path)
    before = current(data, tmp_path)
    removed = next(n for n in data['clauses'] if n['payment_kind'] == 'deposit_discharge')
    data['clauses'].remove(removed)
    after = current(data, tmp_path)
    assert after['basf_payment_terms'] == [r for r in before['basf_payment_terms'] if r['kind'] != 'deposit_discharge']
    assert removed['units'][0] in after['questions']['Q1']['unresolved']
