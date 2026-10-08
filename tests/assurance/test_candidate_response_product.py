"""Product routing and adversarial boundaries, using synthetic judgments only."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from legalmath.canonical import digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import candidate_responses as codec
from legalmath.interpretation.assurance import executable_references_v2 as expressions
from legalmath.interpretation.assurance import fidelity_v2, investigation_observations as obs
from legalmath.interpretation.assurance import scoped_investigation as scoped
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from tests.catala.backend_support import TOOLCHAIN
from .test_coverage_aliases import fixture
from .test_round16 import scoped_fixture
from .test_integration import source, settings
from .test_continuation_references import encode_quotes
from .test_successor_workflow import complete_responder


def synthetic_response(value, wire):
    """Select full-unit/result spans for this synthetic fixture only."""
    encoded = encode_quotes(deepcopy(value), wire['source_references'])
    for row in encoded['checks']:
        row['executable_correspondence']['representation_quotes'] = [next(
            s['span_id'] for s in wire['executable_references']['spans']
            if s['candidate_id'] == row['candidate_id'] and s['expression_kind'] == 'result')
            for _ in row['executable_correspondence']['representation_quotes']]
        target = next(t for t in wire['pair_targets'] if
            (t['claim_id'], t['candidate_id']) == (row['claim_id'], row['candidate_id']))
        row.pop('claim_id'); row.pop('candidate_id')
        row['question_relation'].pop('question_hash')
        row['pair'] = target['pair']
    return encoded


def mixed():
    p, c, r, q, value = scoped_fixture()
    r['unformalized'] = deepcopy(r['candidate']); r['unformalized']['formalization'] = None
    q['unformalized'] = deepcopy(q['candidate']); q['unformalized']['control_id'] = 'unformalized'
    row = deepcopy(value['checks'][0])
    row.update(candidate_id='unformalized', followup_questions=['Which meaning remains to be encoded?'])
    row['question_relation']['question_hash'] = digest(q['unformalized'])
    row['executable_correspondence'].update(status='UNAVAILABLE', representation_quotes=[])
    value['checks'].append(row)
    value['additional_concerns'] = ['Synthetic uncertainty is preserved.']
    return p, c, r, q, value


OPTIONS = dict(maximum_rounds=1, reference_protocol=expressions.PROTOCOL, response_profile=codec.PROFILE)


@pytest.mark.parametrize('status', ['PRESERVES', 'UNAVAILABLE', 'BLOCKED'])
def test_package_codec_matches_reviewed_runner(status):
    from scripts import legal_coverage_candidates as historical
    from scripts import legal_coverage_aliases as historical_aliases
    wire, schema, original, _, _ = fixture(status)
    assert codec.prepare(wire, schema) == historical.prepare(wire, schema)
    _, _, binding = codec.prepare(wire, schema)
    value = historical_aliases.encode_response(original, wire, schema)
    assert codec.resolve(value, wire, schema, binding) == original


def test_mixed_product_dispatch_provenance_and_zero_call_restart(tmp_path):
    p, c, r, q, value = mixed()
    provider = FunctionProvider(lambda wire: synthetic_response(value, wire))
    result = scoped.investigate(p, c, r, q, provider, tmp_path, **OPTIONS)
    assert scoped.execution_complete(result)
    assert result['assessment_coverage']['unavailable_pairs'] == 1
    assert len(provider.requests) == 2
    journal = loads((tmp_path/'model/journal.json').read_bytes())
    assert journal['value']['binding']['inputs']['response_profile'] == codec.PROFILE
    work = tmp_path/'model/action-0001/source-references'
    raw = loads((work/'raw-response.json').read_bytes())['value']
    assert 'pair' in raw['checks'][0] and 'candidate_id' not in raw['checks'][0]
    assert (work/'candidate-response-binding.json').exists()
    provenance = loads((tmp_path/'model/action-0001/raw-response.json').read_bytes())['provenance']
    assert provenance['candidate_response_profile'] == codec.PROFILE
    assert provenance['semantic_support'] == 'NOT_ESTABLISHED'
    for proposal in result['batches'][0]['proposals']:
        assert proposal['additional_concerns'] == value['additional_concerns']
        assert proposal['checks'][1] == value['checks'][1]
    assert scoped.execution_complete(scoped.investigate(p, c, r, q, provider, tmp_path, **OPTIONS))
    assert len(provider.requests) == 2
    before = (tmp_path/'model/journal.json').read_bytes()
    with pytest.raises(LegalMathError):
        scoped.investigate(p, c, r, q, provider, tmp_path, **{**OPTIONS, 'response_profile': 'literal'})
    assert len(provider.requests) == 2 and (tmp_path/'model/journal.json').read_bytes() == before


@pytest.mark.parametrize('fault', ['foreign_executable', 'unavailable_comparison', 'missing', 'duplicate', 'foreign_pair'])
def test_invalid_candidate_response_is_retained_and_rejected_by_product(tmp_path, fault):
    p, c, r, q, value = mixed()
    def respond(wire):
        answer = synthetic_response(value, wire)
        row = answer['checks'][1]
        if fault == 'foreign_executable': row['executable_correspondence']['representation_quotes'] = ['e0']
        elif fault == 'unavailable_comparison': row['executable_correspondence']['status'] = 'OMITS'
        elif fault == 'missing': answer['checks'].pop()
        elif fault == 'duplicate': answer['checks'].append(deepcopy(row))
        else: row['pair'] = 'p999'
        return answer
    provider = FunctionProvider(respond)
    result = scoped.investigate(p, c, r, q, provider, tmp_path, stop_on_rejection=True, **OPTIONS)
    assert result['stopped']['kind'] == 'RESPONSE_REJECTED'
    assert not scoped.execution_complete(result) and len(provider.requests) == 1
    sequence = result['batches'][0]['attempts'][0]['receipt']['sequence']
    work = tmp_path/f'model/action-{sequence:04}/source-references'
    assert loads((work/'raw-response.json').read_bytes())['value']['checks']
    assert loads((work/'validation.json').read_bytes())['status'] == 'REJECTED'


@pytest.mark.parametrize('relation', ['UNCERTAIN', 'UNASSESSED', 'NOT_APPLICABLE_TO_THIS_QUESTION'])
def test_product_preserves_unfinished_and_out_of_scope_judgments(tmp_path, relation):
    p, c, r, q, value = scoped_fixture()
    row = value['checks'][0]
    row['question_relation']['status'] = relation
    row['executable_correspondence'].update(
        status='NOT_APPLICABLE' if relation.startswith('NOT_APPLICABLE') else 'UNASSESSED',
        representation_quotes=[])
    provider = FunctionProvider(lambda wire: synthetic_response(value, wire))
    result = scoped.investigate(p, c, r, q, provider, tmp_path, **OPTIONS)
    assert result['batches'][0]['proposals'] == [value, value]
    assert scoped.execution_complete(result) == relation.startswith('NOT_APPLICABLE')


@pytest.mark.parametrize('change', [{'reference_protocol': 'literal'}, {'response_profile': 'unknown'},
                                 {'input_profile': 'readable-tables.v1'}])
def test_incompatible_profile_fails_before_dispatch(tmp_path, change):
    p, c, r, q, _ = mixed()
    provider = FunctionProvider(lambda _: pytest.fail('Invalid configuration dispatched'))
    with pytest.raises(LegalMathError):
        scoped.investigate(p, c, r, q, provider, tmp_path, **{**OPTIONS, **change})
    assert not provider.requests and not (tmp_path/'model').exists()
    with pytest.raises(LegalMathError):
        CompleteInvestigation(tmp_path, tmp_path/'whole', provider, tmp_path, AT,
            **{k: v for k, v in {**OPTIONS, **change}.items() if k != 'maximum_rounds'})


def test_complete_product_uses_candidate_profile_and_observes_actual_configuration(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    def respond(wire):
        if wire.get('candidate_response_profile') == codec.PROFILE:
            request = {**wire, 'task': 'SCOPED_SOURCE_FIDELITY', 'required_pairs': [
                {k: t[k] for k in ('claim_id', 'candidate_id')} for t in wire['pair_targets']]}
            return synthetic_response(complete_responder(request), wire)
        return encode_quotes(complete_responder(wire), wire['source_references'])
    with TemporaryDirectory(prefix='candidate-product-', dir=root/'artifacts') as directory:
        provider = FunctionProvider(respond)
        runner = CompleteInvestigation(root, directory, provider,
            root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT, settings=settings(),
            maximum_scoped_actions=12, scoped_rounds=1, machine_qualification=True, catala=TOOLCHAIN,
            reference_protocol=expressions.PROTOCOL, response_profile=codec.PROFILE)
        result = runner.run([source()], 'Selected gift control')
        assert result['execution_complete']
        assert verify(root, result)['status'] == 'FILE_BOUND_INVESTIGATION_VERIFIED'
        bound = obs.method(runner)
        assert bound['transports']['scoped_response'] == codec.PROFILE
        assert obs.check_stages(root, result, bound, runner)['legal_correctness'] == 'NOT_ESTABLISHED'
        assert any(r.get('candidate_response_profile') == codec.PROFILE for r in provider.requests)
        count = len(provider.requests)
        assert runner.run([source()], 'Selected gift control')['revision'] == result['revision']
        assert len(provider.requests) == count
        monkeypatch.setattr(runner, 'response_profile', 'literal')
        with pytest.raises(LegalMathError): obs.check_stages(root, result, bound, runner)
