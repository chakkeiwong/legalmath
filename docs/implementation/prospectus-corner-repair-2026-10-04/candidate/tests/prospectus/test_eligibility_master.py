from pathlib import Path
import json
import runpy

import pytest


@pytest.fixture
def master(monkeypatch):
    module = runpy.run_path(str(Path(__file__).parents[2]/'scripts/run_eligibility_gap_closure.py'))
    run = module['execute']
    env = run.__globals__
    monkeypatch.setitem(env, 'identity', lambda: {'files': {}, 'tools': {}})
    monkeypatch.setitem(env, 'G0', lambda out: {'checked': True})
    monkeypatch.setitem(env, 'G1', lambda out: {'checked': True})
    return run, env


def test_reservation_failure_requires_causal_repair_and_preserves_attempt(master, monkeypatch, tmp_path):
    run, env = master
    def fail(out):
        assert json.loads((out/'manifest.json').read_text())['status'] == 'RESERVED'
        raise ValueError('deliberate corruption probe')
    monkeypatch.setitem(env, 'G0', fail)
    with pytest.raises(ValueError, match='corruption'): run('G0', output=tmp_path)
    first = (tmp_path/'G0/attempt-001/manifest.json').read_bytes()
    with pytest.raises(ValueError, match='causal repair'): run('G0', output=tmp_path)
    monkeypatch.setitem(env, 'G0', lambda out: {'repaired': True})
    assert run('G0', output=tmp_path, repair_note='Restored source identity; focused corruption probe passed')['status'] == 'PASS'
    assert (tmp_path/'G0/attempt-001/manifest.json').read_bytes() == first
    assert json.loads((tmp_path/'next-phase-plan.json').read_text())['next_phase'] == 'G1'


def test_success_reuse_requires_unchanged_predecessor_and_outputs(master, tmp_path):
    run, _ = master
    run('G0', output=tmp_path)
    run('G1', output=tmp_path)
    assert run('G1', output=tmp_path)['reused']
    (tmp_path/'G0/attempt-001/result.json').write_text('{}')
    with pytest.raises(ValueError, match='Changed predecessor'): run('G1', output=tmp_path)


def test_changed_method_requires_new_predecessor(master, monkeypatch, tmp_path):
    run, env = master
    run('G0', output=tmp_path)
    monkeypatch.setitem(env, 'identity', lambda: {'files': {}, 'tools': {'revised': 'tool'}})
    with pytest.raises(ValueError, match='Stale'): run('G1', output=tmp_path)
    assert not list((tmp_path/'G1').glob('attempt-*'))


def test_method_change_during_work_is_not_accepted(master, monkeypatch, tmp_path):
    run, env = master
    def mutate(out):
        monkeypatch.setitem(env, 'identity', lambda: {'changed': True})
        return {'apparently': 'successful'}
    monkeypatch.setitem(env, 'G0', mutate)
    with pytest.raises(ValueError, match='changed during'): run('G0', output=tmp_path)
    manifest = json.loads((tmp_path/'G0/attempt-001/manifest.json').read_text())
    assert manifest['status'] == 'FAILED'
    assert json.loads((tmp_path/'next-phase-plan.json').read_text())['repair_required']


def test_challenge_inputs_pass_evidence_integrity_before_abstaining(master):
    from legalmath.translation.policy import prepare
    from legalmath.prospectus.eligibility import models, specifications
    _, env = master
    for name, spec in specifications().items():
        model = models()[name]
        cases = env['joined_cases'](name, spec)
        for c in cases[:-2]:
            assert not prepare(model, c['snapshot'], c['valid_at'], c['known_at'])['reason']
        for c in cases[-2:]:
            assert prepare(model, c['snapshot'], c['valid_at'], c['known_at'])['reason']


def test_archive_dates_and_precise_retrieval_timestamps_keep_their_precision(master):
    _, env = master
    convert = env['legal_recorded_at']
    assert convert('2026-09-29') == '2026-09-29T00:00:00Z'
    precise = '2026-09-28T16:27:39.016492+00:00'
    assert convert(precise) == precise
    for row in env['read'](env['ROOT']/'docs/prospectus/legal/manifest.json')['sources']:
        convert(row['retrieved_on'])
