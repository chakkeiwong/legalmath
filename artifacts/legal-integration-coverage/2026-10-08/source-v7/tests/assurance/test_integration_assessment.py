"""Review completion is distinct from legal closure and evidence applicability."""
from copy import deepcopy

import pytest

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import fidelity_v2 as fv, scoped_investigation as scoped
from legalmath.interpretation.assurance import executable_references_v2 as executable
from legalmath.interpretation.assurance.optional_tools import ToolSession, report, PROFILE, LEGACY_PROFILE
from legalmath.interpretation.assurance.workflow import EvidenceJournal
from legalmath.interpretation.assurance.semantics import fidelity_request
from tests.search.support import FunctionProvider
from .test_round16 import scoped_fixture
from .test_integration_repair import Backend, unassessed
from .test_arguments import argument, value


def limited_fixture(status):
    p, claims, candidates, questions, answer = scoped_fixture()
    row = answer['checks'][0]
    if status == 'UNAVAILABLE':
        candidates['candidate']['formalization'] = None
    else:
        row['source_support'].update(status='NOT_ESTABLISHED', evidence=[], rationale='The premise remains unestablished.')
    row['executable_correspondence'].update(status=status, representation_quotes=[],
        rationale='No program exists.' if status == 'UNAVAILABLE' else 'The source premise prevents a supported comparison.')
    row['followup_questions'] = ['What executable expresses this reading?' if status == 'UNAVAILABLE'
                                 else 'What source establishes this premise?']
    return p, claims, candidates, questions, answer


@pytest.mark.parametrize('status', ['UNAVAILABLE', 'BLOCKED'])
def test_reviewed_limitation_finishes_assessment_without_executable_or_legal_promotion(tmp_path, status):
    p, claims, candidates, questions, answer = limited_fixture(status)
    result = scoped.investigate(p, claims, candidates, questions, FunctionProvider(lambda r: answer), tmp_path,
                               maximum_rounds=1, maximum_actions=2)
    assert scoped.execution_complete(result)
    coverage = result['assessment_coverage']
    assert coverage['assessed_pairs'] == coverage[status.lower() + '_pairs'] == 1
    assert coverage['executable_compared_pairs'] == coverage['unassessed_pairs'] == 0
    assert result['status'] == 'UNCERTAINTY_REPORTED'
    assert not result['release_eligible'] and not result['legal_accuracy_established']
    assert result['batches'][0]['reconciliation']['disputes'][0]['unresolved']
    altered = deepcopy(result); altered['assessment_coverage']['executable_compared_pairs'] = 1
    assert not scoped.execution_complete(altered)


@pytest.mark.parametrize('status', ['UNAVAILABLE', 'BLOCKED'])
@pytest.mark.parametrize('fault', ['no_followup', 'no_reason', 'quote', 'false_precondition', 'not_applicable'])
def test_limitations_cannot_be_used_to_hide_a_comparison_or_unfinished_review(status, fault):
    p, claims, candidates, questions, answer = limited_fixture(status)
    row = answer['checks'][0]
    if fault == 'no_followup': row['followup_questions'] = []
    elif fault == 'no_reason': row['executable_correspondence']['rationale'] = ''
    elif fault == 'quote': row['executable_correspondence']['representation_quotes'] = ['true']
    elif fault == 'not_applicable': row['question_relation']['status'] = 'NOT_APPLICABLE_TO_THIS_QUESTION'
    elif status == 'UNAVAILABLE': candidates = scoped_fixture()[2]
    else: row['source_support'].update(status='SUPPORTED', evidence=claims[0]['evidence'])
    with pytest.raises(LegalMathError): fv.validate(answer, p, claims, candidates, questions)


def test_unassessed_stays_incomplete_and_both_perspectives_are_required(tmp_path):
    p, claims, candidates, questions, answer = limited_fixture('UNAVAILABLE')
    result = scoped.investigate(p, claims, candidates, questions, FunctionProvider(lambda r: unassessed(answer)),
                               tmp_path, maximum_rounds=1, maximum_actions=2)
    assert not scoped.execution_complete(result)
    assert result['assessment_coverage']['assessed_pairs'] == 0
    assert all(r['executable_correspondence']['status'] == 'UNASSESSED'
               for b in result['batches'] for proposal in b['proposals'] for r in proposal['checks'])


def test_stop_on_rejection_retains_failure_without_dispatching_another_perspective(tmp_path):
    p, claims, candidates, questions, answer = scoped_fixture()
    answer['checks'][0]['question_relation']['question_hash'] = '0' * 64
    provider = FunctionProvider(lambda r: answer)
    result = scoped.investigate(p, claims, candidates, questions, provider, tmp_path,
                               maximum_rounds=1, maximum_actions=2, stop_on_rejection=True)
    assert len(provider.requests) == 1 and result['stopped']['kind'] == 'RESPONSE_REJECTED'
    assert not scoped.execution_complete(result)
    again = scoped.investigate(p, claims, candidates, questions, provider, tmp_path,
                              maximum_rounds=1, maximum_actions=2, stop_on_rejection=True)
    assert again['stopped'] == result['stopped'] and len(provider.requests) == 1


def test_uncertain_question_blocks_comparison_and_unavailable_codec_preserves_label():
    p, claims, candidates, questions, answer = limited_fixture('BLOCKED')
    row = answer['checks'][0]
    row['source_support'].update(status='SUPPORTED', evidence=claims[0]['evidence'])
    row['question_relation']['status'] = 'UNCERTAIN'
    assert fv.validate(answer, p, claims, candidates, questions)
    p, claims, candidates, questions, answer = limited_fixture('UNAVAILABLE')
    request = fv.request(p, claims, candidates, questions); schema = fv.FidelityV2.model_json_schema()
    wire, _, references = executable.prepare(request, schema, readings=candidates, questions=questions)
    assert 'UNAVAILABLE' in wire['executable_reference_instructions'] and not references['spans']
    decoded = executable.resolve(answer, request, schema, references, readings=candidates, questions=questions)
    assert fv.validate(decoded, p, claims, candidates, questions) == answer


class GraphBackend(Backend):
    def criticism(self, p, inputs, work):
        self.calls.append('criticism')
        return {'status': 'PASS', 'tool': 'graph', 'evaluation': inputs['evaluation']}


def test_same_id_changed_formula_loses_old_candidate_and_graph_feedback(tmp_path):
    p, claims, candidates, questions, _ = scoped_fixture()
    backend = GraphBackend(); session = ToolSession(backend, tmp_path)
    session.candidates(p, candidates); session.criticism(p, candidates, value(argument()))
    old_request = fv.request(p, claims, candidates, questions)
    old = session.augment(old_request)
    assert {r['kind'] for r in old['external_tool_context']['checks']} == {'candidates', 'criticism', 'retrieval'}
    revised = deepcopy(candidates); revised['candidate']['formalization']['result'] = 'gift'
    request = fv.request(p, claims, revised, questions)
    changed = session.augment(request)
    assert {r['kind'] for r in changed['external_tool_context']['checks']} == {'retrieval'}
    session.candidates(p, revised)
    # An issued request is immutable even if new checks arrive later.
    assert session.augment(request) == changed
    next_request = {**request, 'investigation': {'round': 2}}
    current = session.augment(next_request)
    assert {r['kind'] for r in current['external_tool_context']['checks']} == {'candidates', 'retrieval'}
    bound = next(r for r in current['external_tool_context']['checks'] if r['kind'] == 'candidates')
    assert bound['candidate_hashes'] == {'candidate': digest(revised['candidate'])}
    before = list(backend.calls)
    restarted = ToolSession(backend, tmp_path)
    assert restarted.augment(old_request) == old and restarted.augment(next_request) == current
    assert backend.calls == before
    assert restarted.report()['profile'] == PROFILE and restarted.report()['backend'] == backend.identity()


def test_partial_candidate_context_cannot_reuse_whole_graph_and_broad_fidelity_binds_readings(tmp_path):
    p, claims, candidates, _, _ = scoped_fixture()
    backend = GraphBackend(); session = ToolSession(backend, tmp_path)
    all_candidates = {**candidates, 'second': deepcopy(candidates['candidate'])}
    session.candidates(p, all_candidates)
    request = fidelity_request(p, claims, candidates)
    assert request['candidates'][0]['reading_hash'] == digest(candidates['candidate'])
    context = session.augment(request)['external_tool_context']
    assert all(r['kind'] == 'retrieval' for r in context['checks'])
    assert all(r['kind'] == 'retrieval' for r in session.augment({'task': 'no-candidates', 'source_packet': p})['external_tool_context']['checks'])


@pytest.mark.parametrize('key', ['kind', 'packet_hash', 'inputs_hash', 'candidate_hashes', 'key', 'result_hash', 'profile', 'backend'])
def test_backend_cannot_overwrite_authoritative_fields(tmp_path, key):
    class Forging(Backend):
        def candidates(self, p, inputs, work): return {'status': 'PASS', key: 'forged'}
    p, _, candidates, _, _ = scoped_fixture(); session = ToolSession(Forging(), tmp_path)
    with pytest.raises(LegalMathError) as error: session.candidates(p, candidates)
    assert error.value.code == 'E_INTEGRITY' and not session.report()['execution_complete']


def test_backend_cannot_mutate_product_readings_and_report_rejects_other_backend(tmp_path):
    class Mutating(Backend):
        def candidates(self, p, inputs, work):
            p['units'][0]['text'] = 'changed'
            inputs['candidate']['formalization']['result'] = 'false'
            return {'status': 'PASS'}
    p, _, candidates, _, _ = scoped_fixture(); original = deepcopy((p, candidates))
    backend = Mutating(); session = ToolSession(backend, tmp_path)
    session.candidates(p, candidates)
    assert (p, candidates) == original
    with pytest.raises(LegalMathError): report(tmp_path, expected_backend={'fixture': True, 'revision': 99})


def test_legacy_report_verifies_unchanged_but_cannot_be_resumed_as_v2(tmp_path):
    backend = Backend()
    journal = EvidenceJournal(tmp_path, {'profile': LEGACY_PROFILE, 'backend': backend.identity()},
                              maximum_actions=200, maximum_per_issue=1, deadline_seconds=86400)
    journal.execute('tool-check', {'kind': 'retrieval', 'packet_hash': 'old', 'inputs_hash': 'old'},
                    lambda w: {'status': 'PASS', 'kind': 'retrieval', 'packet_hash': 'old', 'inputs_hash': 'old'})
    expected = report(tmp_path, expected_backend=backend.identity())
    assert expected['profile'] == LEGACY_PROFILE and 'backend' not in expected and expected['execution_complete']
    with pytest.raises(LegalMathError): ToolSession(backend, tmp_path)
    assert report(tmp_path) == expected
