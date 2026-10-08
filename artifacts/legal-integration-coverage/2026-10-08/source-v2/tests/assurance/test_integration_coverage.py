"""Continuation authority, exact scope and fail-closed retained execution."""
from copy import deepcopy
import json

import pytest

from legalmath.errors import LegalMathError
from scripts import legal_integration_coverage as program
from tests.search.support import FunctionProvider
from .test_integration_assessment import limited_fixture


def grant(tmp_path, monkeypatch):
    monkeypatch.setattr(program, 'ROOT', tmp_path)
    monkeypatch.setattr(program.time, 'time', lambda: program.DEADLINE - 1000)
    old = tmp_path / 'old.json'; old.write_text('{"maximum":96,"calls":[]}')
    path = tmp_path / 'authorization.json'
    path.write_text(json.dumps({'schema': 'legalmath.integration-coverage-grant.v1',
        'authorization': program.AUTHORIZATION, 'maximum': 100, 'repair_maximum': 20,
        'purpose_limits': program.LIMITS, 'deadline_epoch': program.DEADLINE,
        'predecessor': [{'path': 'old.json', 'sha256': program.raw_digest(old.read_bytes())}]}))
    return path


def test_new_grant_enforces_combined_baseline_repair_and_total_caps(tmp_path, monkeypatch):
    path = grant(tmp_path, monkeypatch)
    for purpose, maximum in program.LIMITS.items():
        allowance = program.CoverageGrant(purpose, 0, path)
        for _ in range(maximum): allowance.reserve('a' * 64)
        with pytest.raises(LegalMathError) as exc: allowance.reserve('b' * 64)
        assert exc.value.code == 'E_RESOURCE_LIMIT'
    assert len(program.read(tmp_path / 'allowance.json')['calls']) == 100
    assert program.read(tmp_path / 'old.json') == {'maximum': 96, 'calls': []}


def test_grant_keeps_original_expiry_and_rejects_changed_history(tmp_path, monkeypatch):
    path = grant(tmp_path, monkeypatch)
    allowance = program.CoverageGrant('combined', 0, path)
    allowance.reserve('a' * 64)
    monkeypatch.setattr(program.time, 'time', lambda: program.DEADLINE)
    with pytest.raises(LegalMathError): allowance.reserve('b' * 64)
    assert allowance.verify()['used'] == 1
    (tmp_path / 'old.json').write_text('{"maximum":96,"calls":[1]}')
    with pytest.raises(LegalMathError) as error: allowance.verify()
    assert error.value.code == 'E_INTEGRITY'


@pytest.mark.parametrize('fault', ['grant', 'purpose', 'batch', 'hash'])
def test_invalid_authority_or_reservation_fails_before_new_call(tmp_path, monkeypatch, fault):
    path = grant(tmp_path, monkeypatch)
    allowance = program.CoverageGrant('combined', 0, path)
    if fault == 'grant': path.write_text('{}')
    elif fault == 'purpose': allowance.purpose = 'other'
    elif fault == 'batch': allowance.batch = 41
    with pytest.raises(LegalMathError): allowance.reserve('bad' if fault == 'hash' else 'a' * 64)
    assert not (tmp_path / 'allowance.json').exists()


def test_full_partition_keeps_context_and_unavailable_readings():
    p, claims, candidates, questions, _ = limited_fixture('UNAVAILABLE')
    claims = [{**claims[0], 'claim_id': f'claim.{i:02}', 'relevance': 'CONTEXT' if i < 6 else 'CONTROL'}
              for i in range(41)]
    encoded = deepcopy(candidates['candidate'])
    from .test_round16 import scoped_fixture
    encoded = scoped_fixture()[2]['candidate']
    candidates = {f'candidate.{i:02}': candidates['candidate'] if i < 6 else encoded for i in range(12)}
    inputs = {'claims': claims, 'candidates': candidates}
    batches = program.partition(inputs)
    assert len(batches) == 41 and all(len(b) == 12 for b in batches)
    pairs = [tuple(pair) for b in batches for pair in b]
    assert len(set(pairs)) == 492
    assert sum(c.startswith('claim.0') and int(c[-2:]) < 6 for c, _ in pairs) == 72
    unavailable, executable = program.pilots(inputs, batches)
    assert all(candidates[c]['formalization'] is None for _, c in batches[unavailable])
    assert all(candidates[c]['formalization'] is not None for _, c in batches[executable])


def test_completion_recomputed_from_proposals_and_source_not_summary(tmp_path):
    p, claims, candidates, questions, answer = limited_fixture('UNAVAILABLE')
    pairs = [[claims[0]['claim_id'], 'candidate']]
    inputs = dict(packet=p, claims=claims, candidates=candidates, questions=questions)
    result = program.scoped.investigate(p, claims, candidates, questions, FunctionProvider(lambda r: answer),
        tmp_path, maximum_rounds=1, maximum_actions=2)
    assert program.validate_result(result, inputs, pairs)
    changed = deepcopy(result); changed['assessment_coverage']['executable_compared_pairs'] = 1
    with pytest.raises(ValueError): program.validate_result(changed, inputs, pairs)
    changed = deepcopy(result)
    changed['batches'][0]['proposals'][0]['checks'][0]['question_relation']['question_hash'] = '0' * 64
    with pytest.raises(LegalMathError): program.validate_result(changed, inputs, pairs)
    changed = deepcopy(result); changed['batches'][0]['attempts'].pop(); changed['batches'][0]['proposals'].pop()
    changed['assessment_coverage'] = program.scoped.assessment_coverage(changed['batches'])
    assert not program.validate_result(changed, inputs, pairs)


def test_completed_batch_reuses_evidence_and_interrupted_batch_never_dispatches(tmp_path, monkeypatch):
    monkeypatch.setattr(program, 'OUT', tmp_path)
    monkeypatch.setattr(program, 'checked_review', lambda: {})
    monkeypatch.setattr(program, 'check_ref', lambda r: tmp_path / r['path'])
    monkeypatch.setattr(program, 'CoverageProvider', lambda **kw: pytest.fail('Unexpected provider construction'))
    p, claims, candidates, questions, answer = limited_fixture('UNAVAILABLE')
    pairs = [[claims[0]['claim_id'], 'candidate']]
    (tmp_path / 'inputs.json').write_text(json.dumps(dict(packet=p, claims=claims, candidates=candidates, questions=questions)))
    (tmp_path / 'partition.json').write_text(json.dumps({'batches': [pairs, pairs]}))
    folder = tmp_path / 'batches/combined/00'
    result = program.scoped.investigate(p, claims, candidates, questions, FunctionProvider(lambda r: answer),
        folder / 'scoped', maximum_rounds=1, maximum_actions=2)
    (folder / 'receipt.json').write_text(json.dumps({'complete': True, 'evidence': [],
        'result': {'path': 'batches/combined/00/scoped/result.json'}}))
    assert program.run_batch('combined', 0)['complete']
    interrupted = tmp_path / 'batches/combined/01'; interrupted.mkdir()
    (interrupted / 'started.json').write_text('{}')
    with pytest.raises(LegalMathError) as error: program.run_batch('combined', 1)
    assert error.value.code == 'E_JOB_STATE'
