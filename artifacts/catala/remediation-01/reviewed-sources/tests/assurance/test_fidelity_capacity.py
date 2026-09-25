"""Whole-investigation capacity, exact repair feedback and no discarded batches."""
from copy import deepcopy
import pytest
from legalmath.canonical import canonical, digest, loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.engine import Assurance
from legalmath.interpretation.assurance.semantics import (
    Fidelity, fidelity_request, validate_fidelity, validate_fidelity_aggregate)
from legalmath.interpretation.search.models import commitment
from tests.search.support import FunctionProvider
from .support import packet, inventory, reading, fidelity
from .test_integration import settings, responder, source, AT


def matrix(n_claims=1, n_candidates=2):
    template = inventory()['claims'][0]
    claims = [{**deepcopy(template), 'claim_id': f'claim.{i}'} for i in range(n_claims)]
    candidates = {f'candidate.{i}': reading() for i in range(n_candidates)}
    return claims, candidates


def engine(root, tmp_path, provider, **config):
    return Assurance(tmp_path/'run', provider,
        root/'.localresources/java-toolchain/jdk-17.0.20.1+1', AT,
        settings().model_copy(update=config))


def test_pair_errors_separate_missing_extra_and_repeated_with_exact_counts():
    claims, candidates = matrix()
    value = fidelity(claims, candidates)
    value['checks'] = [value['checks'][0], deepcopy(value['checks'][0])]
    extra = deepcopy(value['checks'][0]); extra['candidate_id'] = 'unexpected'
    value['checks'].append(extra)
    with pytest.raises(LegalMathError) as exc:
        validate_fidelity(value, packet(), claims, candidates)
    d = exc.value.details
    assert d['missing_pairs'] == [{'claim_id': 'claim.0', 'candidate_id': 'candidate.1', 'occurrences': 0}]
    assert d['unexpected_pairs'] == [{'claim_id': 'claim.0', 'candidate_id': 'unexpected', 'occurrences': 1}]
    assert d['repeated_pairs'] == [{'claim_id': 'claim.0', 'candidate_id': 'candidate.0', 'occurrences': 2}]
    assert d['expected_count'] == 2 and d['received_count'] == 3
    assert d['repeated_extra_rows'] == 1 and not d['truncated']


def test_large_pair_mismatch_bounds_feedback_but_preserves_totals():
    claims, candidates = matrix(n_candidates=100)
    value = fidelity(claims, {'unexpected': reading()})
    with pytest.raises(LegalMathError) as exc:
        validate_fidelity(value, packet(), claims, candidates)
    d = exc.value.details
    assert d['counts'] == {'missing_pairs': 100, 'unexpected_pairs': 1, 'repeated_pairs': 0}
    assert d['truncated'] and sum(len(d[k]) for k in d['counts']) == 64


@pytest.mark.parametrize('repair_succeeds', [True, False])
def test_output_repair_uses_exact_pair_feedback_and_preserves_both_outputs(root, tmp_path, repair_succeeds):
    claims, candidates = matrix(); correct = fidelity(claims, candidates)
    broken = deepcopy(correct); broken['checks'].pop()
    def respond(request):
        if request['task'] == 'REPAIR_OUTPUT':
            assert request['validation_error_data']['missing_pairs'][0]['candidate_id'] == 'candidate.1'
            assert request['invalid_response'] == broken
            return correct if repair_succeeds else broken
        return broken
    provider = FunctionProvider(respond); run = engine(root, tmp_path, provider)
    value = run.invoke(fidelity_request(packet(), claims, candidates), Fidelity,
                       lambda v: validate_fidelity(v, packet(), claims, candidates))
    assert value == (correct if repair_succeeds else None)
    assert len(provider.requests) == 2
    assert loads((tmp_path/'run/calls/call-000/response.json').read_bytes())['value'] == broken
    assert loads((tmp_path/'run/calls/call-001/response.json').read_bytes())['value'] == (correct if repair_succeeds else broken)


def test_response_limits_remain_strict_and_aggregate_preserves_1088_rows_and_34_concerns():
    claims, candidates = matrix(32, 34)
    value = fidelity(claims, candidates); value['additional_concerns'] = ['Same concern'] * 34
    with pytest.raises(LegalMathError):
        validate_fidelity(value, packet(), claims, candidates)
    assert validate_fidelity_aggregate(value, packet(), claims, candidates) == value
    # A wider aggregate must retain every per-row source/evidence check.
    value['checks'][-1]['source_evidence'][0]['quote'] = 'Fabricated source rule.'
    with pytest.raises(LegalMathError):
        validate_fidelity_aggregate(value, packet(), claims, candidates)


def test_concern_limit_is_per_response_and_internal_ceiling_is_still_enforced():
    claims, candidates = matrix(n_candidates=1)
    value = fidelity(claims, candidates); value['additional_concerns'] = ['Unresolved'] * 31
    with pytest.raises(LegalMathError):
        validate_fidelity(value, packet(), claims, candidates)
    value['additional_concerns'] *= 34  # 1,054: valid aggregate, unchanged duplicates.
    assert validate_fidelity_aggregate(value, packet(), claims, candidates) == value
    value['additional_concerns'] += ['Unresolved'] * 27  # 1,081: above the hard ceiling.
    with pytest.raises(LegalMathError):
        validate_fidelity_aggregate(value, packet(), claims, candidates)


def test_runtime_combines_valid_batches_above_old_limits_without_losing_duplicates(root, tmp_path):
    claims, candidates = matrix(32, 34)
    normal = responder()
    def respond(request):
        value = normal(request)
        value['additional_concerns'] = ['Repeated concern; keep every occurrence.'] * 2
        return value
    provider = FunctionProvider(respond)
    run = engine(root, tmp_path, provider, total_model_calls=36, max_fidelity_pairs_per_call=64)
    result, findings = run._fidelity(packet(), claims, candidates)
    assert len(provider.requests) == 17
    assert len(result['checks']) == 1088 and len(result['additional_concerns']) == 34
    assert len({(r['claim_id'], r['candidate_id']) for r in result['checks']}) == 1088
    assert len(findings) == 34
    plan = loads((tmp_path/'run/fidelity-rounds/round-000/plan.json').read_bytes())
    assert plan['status'] == 'VALIDATED_COMPLETE' and len(plan['validated_batches']) == 17
    assert loads((tmp_path/'run/fidelity-rounds/round-000/complete.json').read_bytes()) == result


@pytest.mark.parametrize('config,constraint', [
    ({'max_total_fidelity_pairs': 1}, 'pairs'),
    ({'max_total_fidelity_concerns': 29}, 'concerns'),
    ({'max_total_fidelity_bytes': 1000}, 'bytes'),
    ({'total_model_calls': 7, 'max_fidelity_pairs_per_call': 1}, 'minimum_model_calls'),
])
def test_impossible_matrix_is_reported_before_any_fidelity_dispatch(root, tmp_path, config, constraint):
    claims, candidates = matrix(n_candidates=7)
    provider = FunctionProvider(responder()); run = engine(root, tmp_path, provider, **config)
    result, findings = run._fidelity(packet(), claims, candidates)
    assert result is None and not provider.requests
    assert findings[0]['kind'] == 'FIDELITY_CAPACITY_EXCEEDED'
    assert findings[0]['diagnostic']['constraint'] == constraint
    plan = loads((tmp_path/'run/fidelity-rounds/round-000/plan.json').read_bytes())
    assert not plan['execution_complete'] and plan['status'] == 'INCOMPLETE'


def test_pair_preflight_counts_unsupported_candidates_before_encoding(root, tmp_path, monkeypatch):
    claims, candidates = matrix(); candidates['candidate.0']['formalization'] = None
    provider = FunctionProvider(responder())
    run = engine(root, tmp_path, provider, max_total_fidelity_pairs=1)
    def unexpected(*args):
        pytest.fail('Over-capacity matrix must be rejected before bundle allocation')
    monkeypatch.setattr('legalmath.interpretation.assurance.engine.bundle', unexpected)
    assert run._fidelity(packet(), claims, candidates)[0] is None
    assert not provider.requests


@pytest.mark.parametrize('n_candidates', [32, 33])
def test_actual_aggregate_pair_ceiling_preserves_unknowns_or_stops_before_dispatch(root, tmp_path, n_candidates):
    claims, candidates = matrix(128, n_candidates)
    for r in candidates.values():
        r['formalization'] = None
    provider = FunctionProvider(responder()); run = engine(root, tmp_path, provider)
    result, findings = run._fidelity(packet(), claims, candidates)
    assert not provider.requests
    if n_candidates == 32:
        assert len(result['checks']) == 4096
        assert all(r['label'] == 'NOT_ESTABLISHED' for r in result['checks'])
        assert len(findings) == 4096
    else:
        assert result is None
        assert findings[0]['diagnostic'] == {'constraint': 'pairs', 'required': 4224, 'maximum': 4096}


def test_late_batch_failure_preserves_validated_rows_and_concerns_without_complete_result(root, tmp_path):
    claims, candidates = matrix(); count = 0
    normal = responder()
    def respond(request):
        nonlocal count
        count += 1
        if count == 2:
            raise LegalMathError('E_DEPENDENCY', details='Controlled transport failure')
        value = normal(request); value['additional_concerns'] = ['Still unresolved.']
        return value
    run = engine(root, tmp_path, FunctionProvider(respond), max_fidelity_pairs_per_call=1)
    result, findings = run._fidelity(packet(), claims, candidates)
    assert result is None and findings[0]['kind'] == 'FIDELITY_CHECK_UNAVAILABLE'
    directory = tmp_path/'run/fidelity-rounds/round-000'
    partial = loads((directory/'partial.json').read_bytes())
    assert len(partial['checks']) == 1 and partial['additional_concerns'] == ['Still unresolved.']
    assert not (directory/'complete.json').exists()
    assert loads((directory/'plan.json').read_bytes())['retained_pairs'] == 1
    assert loads((directory/'batch-000.json').read_bytes()) == partial


def test_cache_and_unsupported_rows_count_toward_the_complete_matrix(root, tmp_path):
    claims, candidates = matrix(n_candidates=1)
    provider = FunctionProvider(responder()); run = engine(root, tmp_path, provider)
    assert run._fidelity(packet(), claims, candidates)[0] is not None
    # Same cached commitment and source; only a new unsupported reading is added.
    bad = reading(); bad['formalization'] = None
    candidates['unsupported'] = bad
    result, _ = run._fidelity(packet(), claims, candidates)
    assert len(provider.requests) == 1
    assert {r['candidate_id']: r['label'] for r in result['checks']} == {
        'candidate.0': 'ENTAILED', 'unsupported': 'NOT_ESTABLISHED'}
    plan = loads((tmp_path/'run/fidelity-rounds/round-001/plan.json').read_bytes())
    assert plan['pending_pairs'] == 0 and plan['total_pairs'] == 2


def test_large_cached_part_is_preserved_without_building_over_capacity_aggregate(root, tmp_path):
    claims, candidates = matrix(n_candidates=1)
    provider = FunctionProvider(responder())
    run = engine(root, tmp_path, provider, max_total_fidelity_bytes=1000)
    value = fidelity(claims, candidates)
    value['checks'][0]['rationale'] = 'Long previously retained model explanation. ' * 100
    scope = {'source': digest(packet()), 'claims': digest(claims), 'candidate': commitment(reading()),
             'method': run.method_hash, 'provider': run.provider.provider_id}
    run.answers.record('Does this candidate retain the selected source claims?',
        canonical({'checks': value['checks']}).decode(), scope, claims[0]['evidence'], packet(),
        evidence_class='MACHINE_DIAGNOSTIC', limitations=['Controlled cache fixture'])
    result, findings = run._fidelity(packet(), claims, candidates)
    assert result is None and not provider.requests
    assert findings[0]['diagnostic']['constraint'] == 'retained_bytes'
    directory = tmp_path/'run/fidelity-rounds/round-000'
    plan = loads((directory/'plan.json').read_bytes())
    assert plan['retained_pairs'] == 1 and plan['aggregated_pairs'] == 0
    assert loads((directory/plan['retained_parts'][0]['path']).read_bytes()) == value


def test_integrated_capacity_failure_is_incomplete_and_never_clean(root, tmp_path):
    provider = FunctionProvider(responder())
    run = engine(root, tmp_path, provider, max_total_fidelity_concerns=0)
    result = run.drive([source()], 'Selected gift control')
    assert result['status'] == 'UNRESOLVED' and not result['execution_complete']
    assert result['fidelity'] is None and not result['release_eligible']
    assert not any(r['task'] == 'SOURCE_FIDELITY' for r in provider.requests)
    assert any(f['kind'] == 'FIDELITY_CAPACITY_EXCEEDED' for f in result['findings'])
    assert run.verify() == result
