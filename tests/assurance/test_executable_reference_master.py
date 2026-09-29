import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('executable_reference_master', Path(__file__).resolve().parents[2]/'scripts/run_executable_reference_master.py')
runner = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)


def configure(tmp_path, monkeypatch):
    for name in ('ROOT', 'OUT', 'DOC'):
        monkeypatch.setattr(runner, name, tmp_path)
    monkeypatch.setattr(runner, 'inputs', lambda: {'code': 'current'})


def receipt(tmp_path, status='PASSED', inputs=None):
    p = tmp_path/'prior.json'
    runner.save(p, {'status': status, 'inputs': inputs or {'code': 'current'}, 'outputs': {}})
    return {'path': p.name, 'sha256': runner.sha(p)}


def test_intact_but_stale_receipt_requires_source_revalidation(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    prior = receipt(tmp_path, inputs={'code': 'old'})
    assert not runner.valid(prior) and runner.valid(prior, current=False)
    assert runner.retry_evidence('D2', [prior])['kind'] == 'SOURCE_REVALIDATION'


def test_failed_retry_needs_an_executed_successful_repair(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    prior = receipt(tmp_path, status='FAILED')
    with pytest.raises(FileNotFoundError): runner.retry_evidence('D2', [prior])
    focused = tmp_path/'focused.json'; runner.save(focused, {'exit_code': 3})
    def note():
        runner.save(tmp_path/'D2-repair-1.json', {'prior_manifest': prior, 'change': 'Causal repair',
            'focused_result': {'path': focused.name, 'sha256': runner.sha(focused)}})
    note()
    with pytest.raises(RuntimeError): runner.retry_evidence('D2', [prior])
    (tmp_path/'focused.log').write_text('Executed focus passed')
    runner.save(focused, {'exit_code': 0, 'argv': ['pytest', 'focused'], 'input_hashes': runner.inputs(),
        'log': 'focused.log', 'log_sha256': runner.sha(tmp_path/'focused.log')}); note()
    assert runner.retry_evidence('D2', [prior])['kind'] == 'IMPLEMENTATION_REPAIR'
    runner.save(focused, {'exit_code': 1})
    with pytest.raises(RuntimeError): runner.retry_evidence('D2', [prior])


def test_exhaustion_preserves_history_and_never_starts_fourth_attempt(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    prior = receipt(tmp_path, status='FAILED')
    state = {'phases': {'D2': [prior]*3}}; runner.save(tmp_path/'state.json', state)
    report = runner.refresh()
    assert report['retry_exhausted'] and report['next_phase'] == 'D2'
    with pytest.raises(RuntimeError, match='exhausted'): runner.phase('D2')
    assert runner.read(tmp_path/'state.json') == state
    assert not (tmp_path/'D2').exists()


def test_successful_increment_refreshes_to_date_audit_without_claiming_live_completion(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    prior = receipt(tmp_path)
    runner.save(tmp_path/'state.json', {'phases': {p: [prior] for p in runner.PHASES}})
    value = runner.refresh()
    assert value['next_phase'] == 'D3-audit' and value['live_authorized_remaining'] == 0
    assert not value['historical_study_complete'] and value['legal_correctness'] == 'NOT_ESTABLISHED'


def test_changed_output_invalidates_successful_phase(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    output = tmp_path/'result.json'; runner.save(output, {'concerns': 263})
    manifest = tmp_path/'prior.json'
    runner.save(manifest, {'status': 'PASSED', 'inputs': runner.inputs(), 'outputs': {output.name: runner.sha(output)}})
    prior = {'path': manifest.name, 'sha256': runner.sha(manifest)}
    assert runner.valid(prior)
    runner.save(output, {'concerns': 262})
    assert not runner.valid(prior, current=False)


def test_attempt_is_reserved_before_a_failed_snapshot(tmp_path, monkeypatch):
    configure(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, 'PLAN', tmp_path/'plan.md')
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *a, **k: 'test-commit')
    def fail(work, name):
        assert len(runner.state()['phases']['D2']) == 1
        raise RuntimeError('Controlled freeze failure')
    monkeypatch.setattr(runner, 'snapshot', fail)
    with pytest.raises(SystemExit): runner.phase('D2')
    saved = runner.state(); manifest = runner.read(tmp_path/saved['phases']['D2'][0]['path'])
    assert manifest['status'] == 'FAILED' and 'Controlled freeze failure' in manifest['details']
    with pytest.raises(FileNotFoundError): runner.phase('D2')
    assert runner.state() == saved
