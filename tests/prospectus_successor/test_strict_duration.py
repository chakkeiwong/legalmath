"""Strict duration must reach complete clauses without inventing legal facts."""
from copy import deepcopy
from itertools import product
import pytest
from legalmath.prospectus import strict_duration as module
from legalmath.prospectus.successor import calendar_facts
from scripts import prospectus_duration_oracle as oracle

NODE = {'conditions': {'all': ['default.notice', 'default.b.other30', {'not': 'default.b.cured'},
        {'any': ['default.quorum', 'default.other_at_receipt']},
        {'any': [{'not': 'representative.b.entrusted'}, 'representative.b.express_permission']}]}}


@pytest.mark.parametrize('row', oracle.scenarios('bond'), ids=lambda r: r['id'])
def test_independent_integer_and_complete_formula(row):
    assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)


def test_complete_boolean_and_unknown_formula_ladder():
    for values in product((False, True), repeat=9):
        row = oracle.case('ladder')
        row.update(zip(oracle.QUALIFICATIONS, values[:3]))
        row['other_facts'] = dict(zip(oracle.FACTS, values[3:]))
        assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)
    for key in (*oracle.QUALIFICATIONS, *oracle.FACTS):
        for value in (None, 'conflict'):
            row = oracle.case('partial')
            (row if key in oracle.QUALIFICATIONS else row['other_facts'])[key] = value
            assert oracle.projection(module.analyze(row, NODE, 'bond')) == oracle.classify(row)


@pytest.mark.parametrize('kind', ['instrument', 'event', 'start-role', 'end-role', 'override',
    'wrong-convention', 'missing-convention', 'invalid-day', 'naive-time', 'precision',
    'offset', 'reversed', 'qualification', 'fact', 'extra-field'])
def test_invalid_and_overridden_inputs_refuse(kind):
    row = oracle.case('invalid')
    interval = row['interval']
    if kind == 'instrument': interval['instrument_id'] = 'wrong'
    elif kind == 'event': interval['event_id'] = 'wrong'
    elif kind == 'start-role': interval['start']['role'] = 'exercise_notice'
    elif kind == 'end-role': interval['end']['role'] = 'receipt'
    elif kind == 'override': row['other_facts'][module.COMPUTED] = True
    elif kind == 'wrong-convention': interval['convention'] = 'BUSINESS_DAYS'
    elif kind == 'missing-convention': interval['convention'] = None
    elif kind == 'invalid-day': interval['start']['value'] = '2024-02-30'
    elif kind in ('naive-time', 'precision', 'offset'):
        interval['convention'] = 'ELAPSED_24_HOUR_DAYS'
        interval['start'] = None
        interval['end']['value'] = {'naive-time': '2024-02-01T00:00:00',
            'precision': '2024-02-01T00:00:00.0000001Z', 'offset': '2024-02-01T00:00:00+01:60'}[kind]
    elif kind == 'reversed': interval['end']['value'] = '2023-12-31'
    elif kind == 'qualification': row['holder_notice_received'] = 1
    elif kind == 'fact': row['other_facts']['default.notice'] = 'yes'
    else: interval['days'] = 29
    with pytest.raises(ValueError): module.analyze(row, NODE, 'bond')


@pytest.mark.parametrize('operator,result', [('GE', True), ('LE', True), ('GT', False)])
def test_equal_boundary_preserves_existing_operators(operator, result):
    start = calendar_facts.operand_value('2024-01-01', 'CIVIL_DATE_GAP')
    end = calendar_facts.operand_value('2024-01-31', 'CIVIL_DATE_GAP')
    assert calendar_facts.compare(start, end, 'CIVIL_DATE_GAP', 30, operator)[0] is result


@pytest.mark.parametrize('end,status', [('2024-01-31', 'NO'), ('2024-02-01', 'YES')])
def test_gt_reaches_ordinary_law_consumer(tmp_path, end, status):
    from test_calendar_facts import world, answer
    products, data, _ = world(tmp_path, '2024-01-01', end, 30)
    data['calendar_facts'][0]['operator'] = 'GT'
    q = answer(products, data, tmp_path)
    assert q['status'] == status
    assert q['value'][0]['calendar_calculations'][0]['exact_comparison']['operator'] == 'GT'


def test_independent_oracle_detects_nonstrict_comparison(monkeypatch):
    original = calendar_facts.compare
    monkeypatch.setattr(calendar_facts, 'compare', lambda start,end,convention,days,operator:
                        original(start,end,convention,days,'GE'))
    row = oracle.case('equal', end='2024-01-31')
    assert oracle.projection(module.analyze(row, NODE, 'bond')) != oracle.classify(row)
