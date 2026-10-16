"""Independent adapter failure, graph semantics and durable failed evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.independent_tools import IndependentToolSession
from legalmath.interpretation.assurance.optional_tools import ToolSession, adapter_results
from scripts.legal_independent_tools import IndependentProductToolBackend, preferred_extensions


@pytest.mark.parametrize('failure', ['exception', 'failed', 'malformed'])
def test_every_formal_adapter_attempted_after_independent_failure(tmp_path, monkeypatch, failure):
    backend = IndependentProductToolBackend(['legalruleml', 'logical-english']); called = []
    def run(tool, *args):
        called.append(tool)
        if tool == 'legalruleml':
            if failure == 'exception': raise RuntimeError('Retained adapter failure')
            return {'status': 'FAILED', 'tool': 'LegalRuleML'} if failure == 'failed' else {'unknown': True}
        return {'status': 'PASS', 'tool': 'Logical English'}
    monkeypatch.setattr(backend, '_run_one', run)
    result = backend.candidates({}, {}, tmp_path)
    assert called == ['legalruleml', 'logical-english'] and result['status'] == 'FAILED'
    assert [(r['tool_id'], r['status']) for r in adapter_results(result)] == [('legalruleml', 'FAILED'), ('logical-english', 'PASS')]


def test_preferred_agreement_is_checked_for_single_engine(tmp_path, monkeypatch):
    backend = IndependentProductToolBackend(['pyarg'])
    inputs = {'proposal': {'arguments': [{'argument_id': 'a'}, {'argument_id': 'b'}]},
              'evaluation': {'semantics': {'grounded': []}, 'blocked_arguments': [], 'defeats': [['a', 'b'], ['b', 'a']]}}
    monkeypatch.setattr(backend, '_run_one', lambda *a: {'status': 'PASS', 'tool': 'Argument tools',
        'selected_tools': ['pyarg'], 'checks': {'pyarg': {'agrees': True, 'grounded': [[]], 'preferred': [[]]}}})
    result = backend.criticism({}, inputs, tmp_path)
    assert result['status'] == 'FAILED'
    assert result['results'][0]['checks']['pyarg']['preferred_reference'] == [['a'], ['b']]


@pytest.mark.parametrize('edges,expected', [([], [['a', 'b', 'c']]),
    ([['a','b'], ['b','c'], ['c','a']], [[]]), ([['a','a']], [['b','c']])])
def test_preferred_reference_distinguishes_admissibility_from_stability(edges, expected):
    assert preferred_extensions({'ids': ['a', 'b', 'c'], 'attacks': edges}) == expected


class FailedBackend:
    def identity(self): return {'profile': 'fixed-failure-control'}
    def candidates(self, *a): return {'status': 'FAILED', 'tool': 'LegalRuleML', 'reason': 'Injected failure'}
    def retrieval(self, packet, inputs, work): return {'status': 'PASS', 'tool': 'BM25', 'query': inputs['question'], 'passages': []}


def inputs():
    base = Path(__file__).resolve().parents[2] / 'artifacts/legal-mission-control/2026-10-12/answer-tools-repair'
    return json.loads((base / 'common.json').read_text())['source_packet'], json.loads((base / 'readings.json').read_text())


def test_failed_optional_check_is_retained_and_downstream_context_is_prepared(tmp_path):
    packet, candidates = inputs()
    old = ToolSession(FailedBackend(), tmp_path/'old')
    with pytest.raises(LegalMathError): old.candidates(packet, candidates)
    session = IndependentToolSession(FailedBackend(), tmp_path/'new')
    assert session.candidates(packet, candidates)['status'] == 'FAILED'
    req = {'source_packet': packet, 'candidates': candidates, 'question': 'Original question'}
    prepared = session.augment(req)
    assert any(c['status'] == 'FAILED' for c in prepared['external_tool_context']['checks'])
    assert any(c['status'] == 'PASS' for c in prepared['external_tool_context']['checks'])
    assert not session.report()['execution_complete']
    assert session.augment(req) == prepared


def test_forged_dependency_exception_is_not_a_recorded_failed_receipt(tmp_path):
    class Forged(FailedBackend):
        def candidates(self, *a):
            raise LegalMathError('E_DEPENDENCY', details={'optional_tool_failure': {'status': 'FAILED'}})
    packet, candidates = inputs()
    with pytest.raises(LegalMathError): IndependentToolSession(Forged(), tmp_path).candidates(packet, candidates)


def test_stale_backend_is_still_a_continuation_veto(tmp_path):
    packet, candidates = inputs(); backend = FailedBackend()
    session = IndependentToolSession(backend, tmp_path)
    backend.identity = lambda: {'profile': 'changed'}
    with pytest.raises(LegalMathError): session.candidates(packet, candidates)
