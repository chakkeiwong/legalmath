import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_assurance_continuation as runner


def test_master_binds_actual_input_and_output_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'inputs',lambda:{'code.py':'unchanged'})
    output=tmp_path/'result.json';output.write_text('{}')
    manifest=tmp_path/'manifest.json'
    runner.save(manifest,{'status':'PASSED','inputs':{'code.py':'unchanged'},'outputs':{'result.json':runner.sha(output)}})
    receipt={'path':'manifest.json','sha256':runner.sha(manifest)}
    assert runner.valid(receipt)
    output.write_text('{"mutated":true}')
    assert not runner.valid(receipt)


def test_stale_source_cannot_reuse_success(tmp_path, monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'inputs',lambda:{'code.py':'changed'})
    manifest=tmp_path/'manifest.json';runner.save(manifest,{'status':'PASSED','inputs':{'code.py':'old'},'outputs':{}})
    assert not runner.valid({'path':'manifest.json','sha256':runner.sha(manifest)})


def test_stale_success_requires_revalidation_without_fabricated_repair(tmp_path, monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'inputs',lambda:{'code.py':'changed'})
    manifest=tmp_path/'manifest.json'
    runner.save(manifest,{'phase':'C4','status':'PASSED','inputs':{'code.py':'old'},'outputs':{}})
    prior={'path':'manifest.json','sha256':runner.sha(manifest)}
    assert runner.retry_evidence([prior])=={'kind':'SOURCE_REVALIDATION','prior_manifest':prior}
    assert not runner.valid(prior)


def test_failed_receipt_cannot_be_bypassed_as_source_revalidation(tmp_path, monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'DOC',tmp_path)
    manifest=tmp_path/'manifest.json'
    runner.save(manifest,{'phase':'C5','status':'FAILED','inputs':{},'outputs':{}})
    with pytest.raises(FileNotFoundError):
        runner.retry_evidence([{'path':'manifest.json','sha256':runner.sha(manifest)}])


def test_failed_command_has_durable_receipt_and_nonzero_outcome(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    with pytest.raises(RuntimeError):
        runner.command([sys.executable,'-c','raise SystemExit(3)'],tmp_path,'failure',timeout=10)
    receipt=json.loads((tmp_path/'failure-command.json').read_text())
    assert receipt['exit_code']==3 and (tmp_path/'failure.log').exists()


@pytest.mark.parametrize('prior_status', ['PASSED', 'FAILED'])
def test_exhausted_phase_never_recommends_an_impossible_retry(tmp_path, monkeypatch, prior_status):
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    monkeypatch.setattr(runner, 'PHASES', ('C0',))
    monkeypatch.setattr(runner, 'inputs', lambda: {'source': 'new'})
    attempts = []
    for i in range(3):
        path = tmp_path/f'attempt-{i}.json'
        runner.save(path, {'status': prior_status, 'phase': 'C0', 'inputs': {'source': 'old'}, 'outputs': {}})
        attempts.append({'path': path.name, 'sha256': runner.sha(path)})
    state = {'phases': {'C0': attempts}}; runner.save(tmp_path/'state.json', state)
    result = runner.refresh(state)
    assert result['phase_status']['C0']['status'] == 'ATTEMPTS_EXHAUSTED'
    assert result['phase_status']['C0']['attempts_remaining'] == 0
    assert not result['phase_status']['C0']['retry_allowed']
    assert result['retry_exhausted'] and not result['source_revalidation_required']
    assert not result['repair_required'] and 'do not retry or reset' in result['action']
    assert json.loads((tmp_path/'state.json').read_text()) == state
