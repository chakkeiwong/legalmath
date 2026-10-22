"""The real source premise enters reporting without inventing an appointment."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf_initial_agents as core
from legalmath.prospectus.successor.basf_agent_report import explain


@pytest.fixture
def case():
    value = json.loads((Path(__file__).parent / 'fixtures/basf-agent-source.json').read_text())
    units = {u['unit']: u for u in value['assembly']['units']}
    assert {k: units[k]['text'] for k in core.INTRO_TEXT} == core.INTRO_TEXT
    for key in core.INTRO_TEXT:
        units[key]['role'] = 'OPERATIVE'
    node = core.expected_node(value['graph'], units)
    value['clauses']['nodes'] = [node if n['id'] == core.IDENTITY else n for n in value['clauses']['nodes']]
    return value


def report(case):
    return explain(case['clauses'], case['graph'], case['assembly'], case['dependencies'])


def test_intro_is_exact_selected_and_raw_source_not_caption(case):
    result = report(case)
    row = next(r for r in result['readings'] if r['id'] == core.IDENTITY)
    spans = row['source_spans'][:3]
    assert [s['occurrence'] for s in spans] == core.introduction_spans({u['unit']: u for u in case['assembly']['units']})
    assert spans[0]['occurrence']['start'] == 45
    assert ''.join(s['quote'] for s in spans[0]['sources']).startswith('Der anfänglich')
    assert row['reading']['appointment_wording'] == core.APPOINTMENT_WORDING
    assert row['actual_appointment_or_change'] == 'NOT_ESTABLISHED'
    assert result['calculation_agent_office'] == 'UNRESOLVED'
    assert not result['independent_legal_acceptance']


@pytest.mark.parametrize('change', ['omit-line', 'caption', 'raw-offset', 'word', 'office', 'appointment', 'version', 'unknown-role'])
def test_incomplete_or_promoted_core_reading_refused(case, change):
    node = next(n for n in case['clauses']['nodes'] if n['id'] == core.IDENTITY)
    if change == 'omit-line': node['spans'].pop(1)
    elif change == 'caption': node['spans'][0]['start'] = 0
    elif change == 'raw-offset': node['source_uses'][0]['source']['start'] += 1
    elif change == 'word': node['agent_reading']['appointment_wording'] = 'The agent is currently appointed.'
    elif change == 'office': node['agent_reading']['calculation_agent_office'] = 'London'
    elif change == 'appointment': node['actual_appointment'] = True
    elif change == 'version': node['initial_agent_provenance'] = None
    else: next(u for u in case['assembly']['units'] if u['unit'] in core.INTRO_TEXT)['role'] = 'UNKNOWN'
    with pytest.raises(ValueError): report(case)


def test_legacy_reading_does_not_invent_intro_when_omitted(case):
    units = {u['unit']: u for u in case['assembly']['units']}
    legacy = core.expected_node(case['graph'], units, include_introduction=False)
    case['clauses']['nodes'] = [legacy if n['id'] == core.IDENTITY else n for n in case['clauses']['nodes']]
    row = next(r for r in report(case)['readings'] if r['id'] == core.IDENTITY)
    assert 'appointment_wording' not in row['reading']
    assert all(s['occurrence']['unit'] not in core.INTRO_TEXT for s in row['source_spans'])
