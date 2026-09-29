from pathlib import Path
import pytest
from legalmath.canonical import canonical, loads
from tests.assurance.test_fidelity_capacity import matrix, engine
from tests.assurance.test_integration import responder
from tests.assurance.support import packet
from tests.search.support import FunctionProvider


@pytest.fixture
def root():
    return Path(__file__).resolve().parents[2]


def test_small_actual_parts_complete_despite_large_projected_upper_bound(root, tmp_path):
    claims, candidates = matrix(3, 4)
    provider = FunctionProvider(responder())
    run = engine(root, tmp_path, provider, incremental_fidelity_admission=True,
        max_fidelity_pairs_per_call=1, total_model_calls=36)
    run.settings.search.max_output_bytes = 200000
    result, _ = run._fidelity(packet(), claims, candidates)
    plan = loads((run.directory/'fidelity-rounds/round-000/plan.json').read_bytes())
    assert plan['byte_upper_bound'] > plan['limits']['bytes']
    assert plan['execution_complete'] and len(result['checks']) == 12
    assert len(provider.requests) == 12
    assert all(p['admitted'] for p in plan['validated_batches'])
    assert len(canonical(result)) < plan['limits']['bytes']


@pytest.mark.parametrize('kind', ['concerns', 'bytes'])
def test_late_overflow_preserves_unadmitted_part_and_stops_without_completing(root, tmp_path, kind):
    claims, candidates = matrix(1, 4)
    normal = responder()
    def respond(request):
        value = normal(request)
        value['additional_concerns'] = ['Unresolved qualification'] * 2
        return value
    provider = FunctionProvider(respond)
    from legalmath.interpretation.assurance.semantics import fidelity_request
    one = respond(fidelity_request(packet(), claims, candidates, [('claim.0', 'candidate.0')]))
    # Allow one known fixture response plus envelope overhead, but not two.
    settings = {'max_total_fidelity_concerns': 3} if kind == 'concerns' else {
        'max_total_fidelity_bytes': len(canonical(one)) + 200}
    run = engine(root, tmp_path, provider, incremental_fidelity_admission=True,
        max_fidelity_pairs_per_call=1, **settings)
    result, findings = run._fidelity(packet(), claims, candidates)
    d = run.directory/'fidelity-rounds/round-000'; plan = loads((d/'plan.json').read_bytes())
    assert result is None and not plan['execution_complete'] and not (d/'complete.json').exists()
    assert plan['failure']['constraint'] == kind and plan['failure']['bound'] == 'ACTUAL_VALIDATED_PARTS'
    assert plan['validated_batches'][-1]['admitted'] is False
    part = loads((d/plan['failure']['unaggregated_part']).read_bytes())
    partial = loads((d/'partial.json').read_bytes())
    assert part['checks'] and len(partial['checks']) < plan['total_pairs']
    assert len(provider.requests) == 2
    assert len(partial['additional_concerns']) == 2
    assert len(canonical(partial)) <= plan['limits']['bytes']


def test_incremental_policy_keeps_pair_and_call_limits_as_pre_dispatch_vetoes(root, tmp_path):
    claims, candidates = matrix(3, 4)
    provider = FunctionProvider(responder())
    run = engine(root, tmp_path, provider, incremental_fidelity_admission=True,
        max_fidelity_pairs_per_call=1, total_model_calls=7)
    assert run._fidelity(packet(), claims, candidates)[0] is None
    assert not provider.requests
