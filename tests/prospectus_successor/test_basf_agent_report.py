"""Real retained passages: reporting cannot erase qualifications or invent offices."""
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor.basf_agent_report import explain


@pytest.fixture
def case():
    return json.loads((Path(__file__).parent / 'fixtures/basf-agent-source.json').read_text())


def report(case):
    return explain(case['clauses'], case['graph'], case['assembly'], case['dependencies'])


def test_exact_sources_and_conditional_agent_rules(case):
    result = report(case)
    rows = {r['id']:r for r in result['readings']}
    assert len(rows) == 5
    assert rows['basf-agents:initial-agent']['reading']['calculation_agent_office'] == 'UNRESOLVED'
    assert rows['basf-agents:office-replacement']['reading']['same_country']
    assert rows['basf-agents:appointment-change']['reading']['maintain_calculation_agent_if_selected']
    assert rows['basf-agents:effectiveness-reference']['reading']['notice_window_days'] == [30,45]
    assert rows['basf-agents:effectiveness-reference']['notice_dependency']['status'] == 'RESOLVED'
    assert rows['basf-agents:contractual-capacity']['reading']['statutory_duties'] == 'NOT_EVALUATED'
    for row in rows.values():
        assert ' '.join(''.join(s['quote'] for s in g['sources']) for g in row['source_spans']) == row['quote']
        assert row['actual_appointment_or_change'] == 'NOT_ESTABLISHED'
        assert not row['independent_legal_acceptance']
    assert all(r['role'] == 'UNKNOWN' for r in result['unresolved_context'])


@pytest.mark.parametrize('identity,field,value', [
    ('initial-agent','calculation_agent_office','Amsterdam dealer address'),
    ('initial-agent','final_term_calculation_agent','Deutsche Bank Aktiengesellschaft'),
    ('office-replacement','same_country',False),
    ('appointment-change','maintain_calculation_agent_if_selected',False),
    ('effectiveness-reference','notice_window_days',[0,45]),
    ('effectiveness-reference','insolvency_immediate_effect',False),
    ('effectiveness-reference','actual_change_validity','VALID'),
    ('contractual-capacity','holder_trust_created',True),
    ('contractual-capacity','statutory_duties','NONE'),
])
def test_changed_meaning_or_fact_is_refused(case, identity, field, value):
    node = next(n for n in case['clauses']['nodes'] if n['id'] == 'basf-agents:' + identity)
    node['capacity_reading' if identity == 'contractual-capacity' else 'agent_reading'][field] = value
    with pytest.raises(ValueError, match='condition or authority'):
        report(case)


@pytest.mark.parametrize('mutation', ['truncated-span','missing-source','wrong-quote','wrong-role',
    'wrong-authority-label','wrong-authority-span','replaced-office','actual-event','duplicate'])
def test_changed_source_or_promotion_is_refused(case, mutation):
    node = case['clauses']['nodes'][0]
    if mutation == 'truncated-span':
        node['spans'][-1]['end'] -= 1
    elif mutation == 'missing-source':
        node['source_uses'].pop()
    elif mutation == 'wrong-quote':
        node['quote'] += ' altered'
    elif mutation == 'wrong-role':
        next(u for u in case['assembly']['units'] if u['unit'] == node['units'][0])['role'] = 'UNKNOWN'
    elif mutation == 'wrong-authority-label':
        next(u for u in case['graph']['units'] if u['id'] == 'basf-2032-final:p7:l24')['raw'] = 'Lead Manager'
    elif mutation == 'wrong-authority-span':
        node['selection_authority'][-1]['end'] -= 1
    elif mutation == 'replaced-office':
        next(u for u in case['assembly']['units'] if u['unit'].endswith(':p124:l44'))['text'] = 'Amsterdam'
    elif mutation == 'actual-event':
        node['actual_appointment'] = True
    else:
        case['clauses']['nodes'].append(node)
    with pytest.raises(ValueError):
        report(case)


def test_omitted_meaning_is_not_regenerated(case):
    before = report(case)
    identity = 'basf-agents:effectiveness-reference'
    case['clauses']['nodes'] = [n for n in case['clauses']['nodes'] if n['id'] != identity]
    after = report(case)
    assert after['readings'] == [r for r in before['readings'] if r['id'] != identity]


def test_missing_actual_notice_dependency_stays_unresolved(case):
    case['dependencies'] = []
    row = next(r for r in report(case)['readings'] if r['id'] == 'basf-agents:effectiveness-reference')
    assert row['notice_dependency']['status'] == 'UNRESOLVED'
