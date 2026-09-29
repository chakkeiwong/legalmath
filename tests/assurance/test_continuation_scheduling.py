from copy import deepcopy
import json

import pytest

from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.scoped_investigation import investigate
from legalmath.interpretation.assurance import source_references as refs
from tests.search.support import FunctionProvider
from .test_round16 import scoped_fixture
from .test_continuation_references import encode_quotes


def workload():
    p, c, r, q, v = scoped_fixture()
    c = [{**deepcopy(c[0]), 'claim_id': 'claim.'+str(i)} for i in range(3)]
    def answer(req):
        result = deepcopy(v)
        result['checks'][0]['claim_id'] = req['required_pairs'][0]['claim_id']
        result['checks'][0]['followup_questions'] = ['Retain the late-batch exception and investigate its scope.']
        return result
    return p, c, r, q, answer


def test_fixed_budget_round_first_reaches_every_initial_pair_before_followups(tmp_path):
    p, c, r, q, response = workload(); results = {}
    for schedule in ('batch-first', 'round-first'):
        provider = FunctionProvider(response)
        result = investigate(p, c, r, q, provider, tmp_path/schedule, batch_size=1,
                             maximum_rounds=2, maximum_actions=6, schedule=schedule)
        results[schedule] = result
        assert result['journal_actions'] == 6 and len(result['required_pairs']) == 3
        for req in provider.requests:
            if req['investigation']['round'] == 1:
                assert req['investigation']['prior_round_evidence'] is None
        if schedule == 'round-first':
            assert [req['investigation']['batch'] for req in provider.requests] == [0, 0, 1, 1, 2, 2]
            assert all(b['proposals'] for b in result['batches'])
    assert results['batch-first']['pairs_with_two_validated_proposals'] == 2
    assert results['round-first']['pairs_with_two_validated_proposals'] == 3
    assert not results['round-first']['legal_accuracy_established']


def test_same_round_blindness_and_exact_cached_resume(tmp_path):
    p, c, r, q, response = workload(); provider = FunctionProvider(response)
    kwargs = dict(batch_size=1, maximum_rounds=2, maximum_actions=12, schedule='round-first')
    first = investigate(p, c, r, q, provider, tmp_path, **kwargs)
    for a, b in zip(provider.requests[::2], provider.requests[1::2]):
        assert a['investigation']['prior_round_evidence'] == b['investigation']['prior_round_evidence']
    assert len(provider.requests) == 12
    resumed = investigate(p, c, r, q, provider, tmp_path, **kwargs)
    assert len(provider.requests) == 12 and resumed['pending_pairs'] == first['pending_pairs']
    with pytest.raises(LegalMathError):
        investigate(p, c, r, q, provider, tmp_path, **{**kwargs, 'batch_size': 2})


def test_rejected_response_does_not_starve_late_initial_review(tmp_path):
    p, c, r, q, response = workload()
    def invalid(req):
        return {'checks': [], 'additional_concerns': []} if req['investigation']['batch'] == 0 else response(req)
    provider = FunctionProvider(invalid)
    result = investigate(p, c, r, q, provider, tmp_path, batch_size=1, maximum_actions=6,
                         maximum_rounds=2, schedule='round-first')
    assert len(provider.requests) == 6 and result['pairs_with_two_validated_proposals'] == 2
    assert result['pending_pairs'] == [['claim.0', 'candidate']]
    assert len(result['batches'][0]['diagnostics']) == 2


def test_interruption_keeps_spending_and_every_undispatched_pair(tmp_path):
    p, c, r, q, response = workload()
    def interrupted(req):
        if req['investigation']['batch'] == 1: raise RuntimeError('Transport interrupted')
        return response(req)
    provider = FunctionProvider(interrupted)
    kw = dict(batch_size=1, maximum_actions=12, maximum_rounds=2, schedule='round-first')
    first = investigate(p, c, r, q, provider, tmp_path, **kw)
    second = investigate(p, c, r, q, provider, tmp_path, **kw)
    assert len(provider.requests) == 3 and first['journal_actions'] == second['journal_actions'] == 3
    assert first['pending_pairs'] == second['pending_pairs'] == [['claim.1', 'candidate'], ['claim.2', 'candidate']]


def test_span_protocol_integrates_with_scoped_review_and_preserves_rejections(tmp_path):
    p, c, r, q, response = workload()
    def answer(req): return encode_quotes(response(req), req['source_references'])
    provider = FunctionProvider(answer)
    result = investigate(p, c, r, q, provider, tmp_path, batch_size=1, maximum_actions=6,
                         maximum_rounds=1, schedule='round-first', reference_protocol=refs.PROTOCOL)
    assert result['pairs_with_two_validated_proposals'] == 3
    assert result['source_reference_protocol'] == refs.PROTOCOL
    assert len(list(tmp_path.glob('model/action-*/source-references/validation.json'))) == 6
