"""Actual failure controls for the finite recovery, with no provider calls."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from legalmath.interpretation.assurance.answer_interface import answer_schema
from scripts import legal_mission_answer_tools_recovery as trial


def response():
    value = trial.read(trial.PREDECESSOR / 'responses/baseline.answer.json')['value']
    inputs = trial.common_inputs()
    facts = {c['case_id']: c['facts'] for c in inputs['cases']}
    for row in value['premise_account']:
        row['stated_facts'] = facts[row['case_id']]
    value['tool_account'] = []
    return inputs, value


def test_actual_metadata_failures_are_expressed_in_schema_without_constraining_prose():
    inputs, value = response()
    before = deepcopy(trial.ANSWER_SCHEMA)
    schema = answer_schema(trial.ANSWER_SCHEMA, inputs)
    Draft202012Validator(schema).validate(value)
    trial.validate_proposal(value, inputs)
    assert trial.ANSWER_SCHEMA == before
    assert schema['properties']['answers']['items']['properties']['answer'] == {'type': 'string'}
    raw = trial.read(trial.PREDECESSOR / 'responses/baseline.answer.json')['value']
    assert len(list(Draft202012Validator(schema).iter_errors(raw))) >= 2


def test_actual_check_keys_are_closed_and_baseline_has_no_tool_checks():
    inputs, value = response()
    supplied = deepcopy(inputs)
    supplied['external_tool_context'] = {'checks': [{'key': 'actual-delivered-check'}]}
    schema = answer_schema(trial.ANSWER_SCHEMA, supplied)
    value['tool_account'] = [{'check_key': 'actual-delivered-check', 'disposition': 'UNSUPPORTED',
                             'reason': 'The selected representation is not supported.'}]
    Draft202012Validator(schema).validate(value)
    trial.validate_proposal(value, supplied)
    value['tool_account'][0]['check_key'] = 'executor_input_review'
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(value)
    with pytest.raises(ValidationError):
        Draft202012Validator(answer_schema(trial.ANSWER_SCHEMA, inputs)).validate(value)


def test_enum_membership_does_not_replace_case_pairing_or_legal_premise_checks():
    inputs, value = response()
    value['premise_account'][0]['stated_facts'] = inputs['cases'][1]['facts']
    Draft202012Validator(answer_schema(trial.ANSWER_SCHEMA, inputs)).validate(value)
    with pytest.raises(Exception, match='Case facts changed'):
        trial.validate_proposal(value, inputs)
    inputs, value = response()
    next(r for r in value['premise_account'] if r['case_id'] == 'supervised-defect')['p11_applicability'] = 'ESTABLISHED'
    with pytest.raises(Exception, match='P11'):
        trial.validate_proposal(value, inputs)


def test_graph_repair_keeps_actual_failed_output_and_all_diagnostics():
    request = trial.graph_request(trial.common_inputs(), [], trial.retained_readings())
    assert len(request['reference_errors']) == 13
    assert request['failed_proposal'] == trial.read(trial.PREDECESSOR / 'responses/argument-graph.json')['value']
    assert len(request['source_packet']['units']) == 55
    assert len(trial.STAGES) == 17
    assert trial.offline()['verification'] == 'PASS'


def test_failed_repaired_graph_and_answer_do_not_block_independent_arms(tmp_path, monkeypatch):
    inputs, value = response()
    candidates = trial.retained_readings()
    monkeypatch.setattr(trial, 'BASE', tmp_path)
    monkeypatch.setattr(trial, 'ALLOWANCE', tmp_path / 'allowance.json')
    trial.save(tmp_path / 'common.json', inputs)
    trial.save(tmp_path / 'readings.json', candidates)
    trial.save(tmp_path / 'allowance.json', {'calls': []})
    monkeypatch.setattr(trial, 'verify', lambda: None)
    called = []
    def dispatch(stage, request, schema, **kwargs):
        called.append(stage)
        trial.save(trial.stage_path(stage), {'stage': stage, 'status': 'FAILED'})
    monkeypatch.setattr(trial, 'dispatch', dispatch)
    monkeypatch.setattr(trial, 'response', lambda stage: None)
    monkeypatch.setattr(trial, 'arm_tools', lambda *args: None)
    monkeypatch.setattr(trial, 'input_reviewed', lambda *args: {
        'readings_status': 'PASS', 'graph_status': 'UNAVAILABLE'})
    trial._run()
    assert set(called) == {'argument-graph', 'baseline.answer', 'bm25.answer',
                           'legalruleml.answer', 'logical-english.answer'}
    assert trial.read(trial.stage_path('clingo.answer'))['status'] == 'DEPENDENCY_BLOCKED'
