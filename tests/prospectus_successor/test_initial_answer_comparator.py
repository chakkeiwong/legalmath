"""A demonstrated nested-answer defect, with full-answer adverse controls."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from scripts import prospectus_initial_agent_runner as checks
from legalmath.prospectus.successor import basf_initial_agents as core
from legalmath.prospectus.successor import basf_agent_report
from legalmath.prospectus.successor.contracts import digest

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / ('docs/implementation/prospectus-execution-authority/attempts/'
                 'basf-meanings/attempt-017/methods/scripts/prospectus_initial_agent_runner.py')
NAMES = ('compulsory_common', 'possible_common', 'common_only')


@pytest.fixture
def case():
    fixture = json.loads((Path(__file__).parent / 'fixtures/basf-agent-source.json').read_text())
    graph, assembly, clauses = fixture['graph'], fixture['assembly'], fixture['clauses']
    legacy = basf_agent_report.explain(clauses, graph, assembly, fixture['dependencies'])
    ids = [core.UNKNOWN_ID, 'preserved-caption', *core.INTRO_TEXT, 'preserved-unknown']
    question = {'status': 'UNKNOWN', 'unresolved': ids, 'reasoning': ['preserved reasoning']}
    questions = {'Q1': deepcopy(question), 'Q2': {**deepcopy(question),
        'subquestions': {n: deepcopy(question) for n in NAMES}},
        'Q3': {'value': {q: {'unresolved': deepcopy(ids)} for q in ('Q1', 'Q2')},
               'status': 'INCOMPLETE'}}
    units = {u['unit']: u for u in assembly['units']}
    spans = core.introduction_spans(units)
    counts = {s['unit']: sum(not c.isspace() for c in units[s['unit']]['text'][s['start']:s['end']]) for s in spans}
    coverage = {'assembly_sha256': digest(assembly), 'clauses_sha256': digest(clauses),
        'source_categories': {'BODY_CANDIDATE': {'assembly_roles': {'UNKNOWN': 4, 'OPERATIVE': 1},
            'active_characters': {'unknown_only': sum(counts.values()) + 9, 'known_only': 12}}},
        'selected_body_pending': [{'unit': k, 'role_unresolved': True,
            'unknown_characters': n, 'uncovered_characters': 0} for k, n in counts.items()] + [
                {'unit': 'preserved-caption', 'role_unresolved': True,
                 'unknown_characters': 9, 'uncovered_characters': 0}]}
    old = {'questions': questions, 'basf_agents': legacy, 'meaning_coverage': coverage,
        'request_sha256': 'old', 'consumed_products': {}, 'report_sha256': 'old',
        'independent_legal_acceptance': False, 'may_execute_transaction': False,
        'unrelated_report': {'status': 'UNKNOWN', 'sources': ['preserved']}}
    for key in core.INTRO_TEXT:
        units[key]['role'] = 'OPERATIVE'
    clauses['nodes'] = [core.expected_node(graph, units) if n['id'] == core.IDENTITY else n
                        for n in clauses['nodes']]
    new = deepcopy(old)
    # Independent expected transformation, not a call to the comparator helper.
    removed = {core.UNKNOWN_ID, *core.INTRO_TEXT}
    for q in ('Q1', 'Q2'):
        new['questions'][q]['unresolved'] = [x for x in ids if x not in removed]
        new['questions']['Q3']['value'][q]['unresolved'] = [x for x in ids if x not in removed]
    for name in NAMES:
        new['questions']['Q2']['subquestions'][name]['unresolved'] = [x for x in ids if x not in removed]
    new['basf_agents'] = basf_agent_report.explain(clauses, graph, assembly, fixture['dependencies'])
    coverage = new['meaning_coverage']
    coverage.update(assembly_sha256=digest(assembly), clauses_sha256=digest(clauses))
    body = coverage['source_categories']['BODY_CANDIDATE']
    body['assembly_roles'].update(UNKNOWN=1, OPERATIVE=4)
    body['active_characters'].update(unknown_only=9, known_only=12 + sum(counts.values()))
    coverage['selected_body_pending'] = [coverage['selected_body_pending'][-1]]
    products = {'P1': {'payload': {'graph': graph}},
                'P2': {'payload': {'assembly': assembly}}, 'P3': {'payload': {'clauses': clauses}}}
    return old, new, products


def test_frozen017_rejects_exact_nested_delta_and_corrected_comparator_accepts(case):
    spec = importlib.util.spec_from_file_location('frozen017_initial_answer_checker', FROZEN)
    frozen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frozen)
    old, new, products = case
    before = deepcopy(case)
    with pytest.raises(AssertionError, match='Unexpected question change'):
        frozen.compare_answers(old, new, products)
    assert checks.compare_answers(old, new, products)['exact_question_delta']
    assert case == before


@pytest.mark.parametrize('name', NAMES)
@pytest.mark.parametrize('change', ('missed', 'extra-removal', 'extra-addition', 'status', 'reasoning', 'order'))
def test_nested_answer_changes_are_not_hidden(case, name, change):
    old, new, products = case
    row = new['questions']['Q2']['subquestions'][name]
    if change == 'missed': row['unresolved'] = deepcopy(old['questions']['Q2']['subquestions'][name]['unresolved'])
    elif change == 'extra-removal': row['unresolved'].pop()
    elif change == 'extra-addition': row['unresolved'].append('invented')
    elif change == 'status': row['status'] = 'TRUE'
    elif change == 'reasoning': row['reasoning'].append('invented reason')
    else: row['unresolved'].reverse()
    with pytest.raises(AssertionError, match='Unexpected question change'):
        checks.compare_answers(old, new, products)


@pytest.mark.parametrize('change', ('main', 'completeness', 'outside-answer', 'appointment', 'office',
                                  'coverage', 'quote', 'source', 'initial-extra-field'))
def test_full_answer_checks_survive_nested_repair(case, change):
    old, new, products = case
    if change == 'main': new['questions']['Q1']['unresolved'].pop()
    elif change == 'completeness': new['questions']['Q3']['value']['Q2']['unresolved'].append('extra')
    elif change == 'outside-answer': new['unrelated_report']['status'] = 'TRUE'
    elif change == 'appointment': new['basf_agents']['readings'][0]['actual_appointment_or_change'] = 'ESTABLISHED'
    elif change == 'office': new['basf_agents']['calculation_agent_office'] = 'London'
    elif change == 'quote': new['basf_agents']['readings'][0]['quote'] += ' invented'
    elif change == 'source': new['basf_agents']['readings'][0]['sources'][0]['quote'] += ' invented'
    elif change == 'initial-extra-field': new['basf_agents']['readings'][0]['invented'] = True
    else: new['meaning_coverage']['source_categories']['BODY_CANDIDATE']['active_characters']['known_only'] += 1
    with pytest.raises(AssertionError): checks.compare_answers(old, new, products)
