"""Focused regression controls for the answer/tool successor."""
from copy import deepcopy
from pathlib import Path
import json
from tempfile import TemporaryDirectory

import pytest

from scripts import legal_mission_answer_tools as trial


PROPOSAL = Path('artifacts/legal-mission-control/2026-10-11/continuous-execution/qualification/answer-correction/proposal-response.json')
PREPARED = Path('artifacts/legal-mission-control/2026-10-09/continuation/product-contribution/reviewed/prepared.json')


def candidate():
    inputs = trial.common_inputs()
    value = deepcopy(json.loads(PROPOSAL.read_text())['value'])
    # Historical response uses the original extraction IDs; the current lossless
    # product projection has other IDs. Remap to an exact retained occurrence.
    for answer in value['answers']:
        for ground in answer['grounds']:
            matches = [u['unit_id'] for u in inputs['source_packet']['units']
                       if ground['quote'] in u['text']]
            assert matches
            ground['unit_id'] = matches[0]
    value['obligation_account'] = [
        {'obligation_id': item['id'], 'answer_quote': value['answers'][0]['answer'][:40],
         'reason': 'Structural account only; semantic source review still required.'}
        for item in inputs['acceptance_obligations']]
    value['premise_account'] = [
        {'case_id': item['case_id'], 'stated_facts': item['facts'],
         'p11_applicability': 'UNESTABLISHED', 'additional_assumptions': []}
        for item in inputs['cases']]
    value['tool_account'] = []
    return inputs, value


def test_exact_case_and_obligation_account_rejects_prior_protocol_faults():
    inputs, value = candidate()
    trial.validate_proposal(value, inputs)
    wrong = deepcopy(value)
    next(row for row in wrong['premise_account'] if row['case_id'] == 'supervised-defect')['p11_applicability'] = 'ESTABLISHED'
    with pytest.raises(Exception, match='P11'):
        trial.validate_proposal(wrong, inputs)
    missing = deepcopy(value)
    missing['obligation_account'] = [
        row for row in missing['obligation_account'] if row['obligation_id'] != 'p14-confidence-scope']
    with pytest.raises(Exception, match='obligation'):
        trial.validate_proposal(missing, inputs)


def test_tool_account_requires_actual_delivered_checks():
    inputs, value = candidate()
    inputs['external_tool_context'] = {'checks': [{'key': 'source-bound-bm25'}]}
    with pytest.raises(Exception, match='Tool consideration'):
        trial.validate_proposal(value, inputs)
    value['tool_account'] = [{'check_key': 'source-bound-bm25', 'disposition': 'UNRESOLVED',
                              'reason': 'Retrieval alone cannot establish the legal warrant.'}]
    trial.validate_proposal(value, inputs)


def test_source_projection_and_timeout_are_explicit():
    inputs = trial.common_inputs()
    assert len(inputs['source_packet']['units']) == 55
    assert sum(len(u['text']) for u in inputs['source_packet']['units']) == 54910
    assert trial.TIMEOUT == 300
    assert len(trial.STAGES) == 20
    trial.attach_questions(trial.reader_request(inputs, 'reader-one'), inputs['original_questions'])


def test_failed_formal_generation_does_not_block_baseline_or_retrieval(tmp_path, monkeypatch):
    inputs, value = candidate()
    monkeypatch.setattr(trial, 'BASE', tmp_path)
    monkeypatch.setattr(trial, 'ALLOWANCE', tmp_path / 'allowance.json')
    trial.save(tmp_path / 'common.json', inputs)
    trial.save(tmp_path / 'allowance.json', {'calls': []})
    monkeypatch.setattr(trial, 'verify', lambda: None)
    values, called = {}, []
    def dispatch(stage, request, schema, **kwargs):
        called.append(stage)
        state = 'FAILED' if stage in {'reader-one', 'representations', 'baseline.review'} else 'SUCCEEDED'
        trial.save(trial.stage_path(stage), {'stage': stage, 'status': state})
        if state == 'SUCCEEDED':
            values[stage] = value
            trial.save(tmp_path / 'requests' / (stage + '.json'), request)
        return {'status': state}
    monkeypatch.setattr(trial, 'dispatch', dispatch)
    monkeypatch.setattr(trial, 'response', lambda stage: values.get(stage))
    monkeypatch.setattr(trial, 'arm_tools', lambda *args: None)
    monkeypatch.setattr(trial, 'input_reviewed', lambda *args: {
        'readings_status': 'UNAVAILABLE', 'graph_status': 'UNAVAILABLE'})
    trial._run()
    assert 'reader-two' in called
    assert 'baseline.answer' in called and 'baseline.review' in called
    assert 'bm25.answer' in called and 'bm25.review' in called
    assert 'argument-graph' not in called
    assert trial.read(trial.stage_path('clingo.answer'))['status'] == 'DEPENDENCY_BLOCKED'


def test_missing_obligation_is_not_a_passing_review():
    inputs, value = candidate()
    review = {'verdict': 'PASS_WITH_LIMITS', 'findings': [],
              'case_findings': value['case_assessments'], 'remaining_uncertainty': [],
              'obligation_findings': [
                  {'obligation_id': o['id'], 'status': 'UNRESOLVED', 'answer_quote': '',
                   'reason': 'Required source reasoning is absent.'}
                  for o in inputs['acceptance_obligations']]}
    with pytest.raises(Exception, match='contradicts'):
        trial.validate_review(review, {**inputs, 'proposed_answer': value})


def test_actual_bm25_context_reaches_original_answer_request(monkeypatch):
    inputs = trial.common_inputs()
    with TemporaryDirectory(prefix='answer-tools-test-', dir=trial.ROOT / 'artifacts/legal-mission-control') as folder:
        work = Path(folder)
        monkeypatch.setattr(trial, 'BASE', work)
        trial.save(work / 'common.json', inputs)
        session = trial.arm_tools('bm25', inputs['source_packet'], {}, None)
        augmented = session.augment(trial.answer_request(inputs, [], {}, None))
        context = augmented['external_tool_context']
        checks = [row for row in context['checks'] if row['kind'] == 'retrieval']
        assert len(checks) == 2
        assert {row['query'] for row in checks} == {q['text'] for q in inputs['original_questions']}
        assert all(row['status'] == 'PASS' and row['passages'] for row in checks)


def test_six_installed_tools_reach_same_answer_request(monkeypatch):
    inputs = trial.common_inputs()
    old = json.loads(PREPARED.read_text())
    candidates, graph = old['candidates'], old['proposals']['questioned']
    with TemporaryDirectory(prefix='answer-tools-six-', dir=trial.ROOT / 'artifacts/legal-mission-control') as folder:
        work = Path(folder)
        monkeypatch.setattr(trial, 'BASE', work)
        trial.save(work / 'common.json', inputs)
        session = trial.arm_tools('combined', inputs['source_packet'], candidates, graph)
        request = trial.answer_request(inputs, [], candidates, graph)
        augmented = session.augment(request)
        checks = augmented['external_tool_context']['checks']
        assert {row['kind'] for row in checks} == {'retrieval', 'candidates', 'criticism'}
        assert len([row for row in checks if row['kind'] == 'retrieval']) == 2
        wire = trial.compact_request(augmented, profile='v2')
        assert len(trial.canonical(wire)) <= 200000
        assert session.report()['legal_premises_established'] is False


def test_dispatch_reserves_the_actual_compact_wire_hash(monkeypatch):
    from legalmath.interpretation.search.providers import Completion
    inputs, value = candidate()
    reserved = []
    class Allowance:
        def check(self):
            return {'calls': []}
        def reserve(self, request_hash):
            assert request_hash == self.expected
            reserved.append((self.stage, request_hash))
    class Provider:
        provider_id, live = 'receipt-sink', False
        def __init__(self, allowance):
            self.allowance = allowance
            self.routing = {}
        def complete(self, request, schema, settings):
            self.allowance.reserve(trial.digest(request))
            return Completion(value, {'source': 'scripted transport control'})
    with TemporaryDirectory(prefix='answer-tools-wire-', dir=trial.ROOT / 'artifacts/legal-mission-control') as folder:
        work = Path(folder)
        monkeypatch.setattr(trial, 'BASE', work)
        monkeypatch.setattr(trial, 'PROTOCOL', work / 'protocol.json')
        monkeypatch.setattr(trial, 'Allowance', Allowance)
        monkeypatch.setattr(trial.q, 'CodexProvider', Provider)
        trial.save(work / 'common.json', inputs)
        trial.save(work / 'protocol.json', {'route': {}})
        result = trial.dispatch('reader-one', trial.reader_request(inputs, 'reader-one'),
                                trial.ANSWER_SCHEMA, validator=trial.validate_proposal)
        assert result['status'] == 'SUCCEEDED'
        assert len(reserved) == 1
        trial.dispatch('reader-one', trial.reader_request(inputs, 'reader-one'),
                       trial.ANSWER_SCHEMA, validator=trial.validate_proposal)
        assert len(reserved) == 1
