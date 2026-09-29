import importlib.util
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import run_closure_master as master


def test_fixed_vectors_and_authorisation_are_audited(monkeypatch):
    # This historical policy names its approved checkout explicitly. Exercise
    # those reviewed interpreter vectors even when the test suite is relocated;
    # this does not authorize running the old controller from the new checkout.
    allow = master.read(master.DOC/'allowlist.json')
    for name, interpreter in zip(('PY', 'TOOLPY', 'DOCPY'), allow['interpreters']):
        monkeypatch.setattr(master, name, Path(interpreter))
    report = master.audit()
    assert report['remaining_this_round'] >= 0 and not report['independent_review']
    assert len(master.PHASES) == 6
    for phase in master.PHASES:
        commands = master.commands(phase, ROOT/'artifacts/interpretation/round12/audit')
        assert commands and all(isinstance(argv, list) for _, argv in commands)
    monkeypatch.setattr(master, 'PY', ROOT/'unapproved-checkout/bin/python')
    with pytest.raises(ValueError, match='Interpreter denied'):
        master.audit()


def test_final_report_refuses_incomplete_phases(tmp_path, monkeypatch):
    monkeypatch.setattr(master, 'OUT', tmp_path)
    with pytest.raises(ValueError, match='Incomplete'): master.finalize(master.state())
    assert not (tmp_path/'final-report.json').exists()


def test_manifest_verification_rejects_altered_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(master, 'ROOT', tmp_path)
    evidence = tmp_path/'answer.json'; evidence.write_text('{}')
    manifest = tmp_path/'run-manifest.json'
    master.write(manifest, {'artifacts': {'answer.json': master.sha(evidence)}})
    entry = {'path': 'run-manifest.json', 'sha256': master.sha(manifest)}
    master.verify_attempt(entry)
    evidence.write_text('{"false_success": true}')
    with pytest.raises(ValueError, match='artifact changed'): master.verify_attempt(entry)


def test_interrupted_supervisor_recovery_preserves_failed_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(master, 'ROOT', tmp_path)
    monkeypatch.setattr(master, 'OUT', tmp_path/'runs')
    monkeypatch.setattr(master, 'refresh', lambda phase, s: None)
    s = master.state(); s['phases']['P4']['status'] = 'RUNNING'
    out = master.OUT/'P4/attempt-01'; out.mkdir(parents=True)
    master.write(out/'in-progress.json', {'phase': 'P4', 'status': 'RUNNING', 'inputs': {}})
    (out/'retained.txt').write_text('partial evidence')
    master.recover('P4', s)
    assert s['phases']['P4']['status'] == 'REPAIR_REQUIRED'
    attempts = s['phases']['P4']['attempts']
    assert len(attempts) == 1 and attempts[0]['status'] == 'FAILED'
    assert master.verify_attempt(attempts[0])['error'] == 'SUPERVISOR_INTERRUPTED'
    with pytest.raises(ValueError, match='No interrupted'): master.recover('P4', s)


def test_final_report_labels_live_incompleteness_without_hiding_it(tmp_path, monkeypatch):
    monkeypatch.setattr(master, 'OUT', tmp_path)
    monkeypatch.setattr(master, 'material', lambda phase: {'scope': phase})
    monkeypatch.setattr(master, 'audit', lambda: {})
    monkeypatch.setattr(master, 'verify_attempt', lambda entry: {'inputs': {'scope': entry['phase']}})
    s = master.state()
    for phase in master.PHASES:
        s['phases'][phase].update(status='PASSED', attempts=[{'phase': phase}])
    s['phases']['P4']['status'] = master.LIVE_INCOMPLETE
    report = master.finalize(s)
    assert report['engineering_status'] == 'ENGINEERING_CHECKS_PASSED_LIVE_EVIDENCE_INCOMPLETE'
    assert not report['live_execution_complete'] and not report['legal_correctness_established']
    s['phases']['P3']['status'] = master.LIVE_INCOMPLETE
    with pytest.raises(ValueError, match='Incomplete'): master.finalize(s)


def test_material_inputs_bind_transfer_references_fixtures_and_tool_versions():
    inputs = master.material('P3')
    assert 'docs/implementation/interpretation-round12/transfer-reference-packets.json' in inputs
    assert '.localresources/assurance-tools/tool-lock.json' in inputs
    assert any(p.startswith('docs/specs/v0.1/fixtures/') for p in inputs)
