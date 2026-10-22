"""Real closure registry/status/receipt checks, with isolated temporary roots."""
import json
from types import SimpleNamespace
import pytest
from legalmath.prospectus.successor import closure_program as c
from legalmath.prospectus.successor.contracts import digest, write


def scaffold(root):
    files = {"scripts/prospectus_delivery.py", c.PLAN,
             "src/legalmath/prospectus/successor/closure_program.py",
             "src/legalmath/prospectus/successor/basf_scope_review.json",
             "src/legalmath/cli.py", "tests/conftest.py"}
    files.update(path for tests, _ in c.JOBS.values() for path in tests.split())
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("{}" if path.suffix == ".json" else "# fixture\n")
    (root / "pyproject.toml").write_text("[project]\nname = 'legalmath'\nversion = '0'\n")


def receipt(root, phase, outcome="PASS", parents=None):
    scaffold(root)
    folder = root / c.REL / "phases" / phase / "attempt-001"
    folder.mkdir(parents=True)
    write(folder / "result.json", {"criterion": outcome})
    row = {"phase": phase, "method": digest(c.bindings(root, phase)), "parents": parents or {},
           "execution": "COMPLETED", "engineering_checks": outcome, "primary_criterion": outcome,
           "consumer_integration": "NOT_CHECKED", "remaining": [] if outcome == "PASS" else ["Repair candidate"],
           "outputs": {"result.json": digest((folder / "result.json").read_bytes())}}
    write(folder / "receipt.json", {**row, "sha256": digest(row)})
    return folder, digest(row)


def test_status_is_readonly_and_registered_is_not_complete(tmp_path):
    before = list(tmp_path.rglob("*"))
    rows = c.status(tmp_path)["phases"]
    assert list(tmp_path.rglob("*")) == before
    assert not next(r for r in rows if r["phase"] == "R8")["current"]
    assert all(r["primary_criterion"] == "NOT_CHECKED" for r in rows)


def test_runtime_changes_invalidate_before_recovery_marker(tmp_path, monkeypatch):
    interpreter = tmp_path / 'ocr-python'
    interpreter.write_bytes(b'first-runtime')
    monkeypatch.setenv('LEGALMATH_OCR_PYTHON', str(interpreter))
    monkeypatch.setenv('LC_ALL', 'C')
    receipt(tmp_path, 'R0')
    assert c.status(tmp_path)['phases'][0]['current']
    monkeypatch.setenv('LC_ALL', 'C.UTF-8')
    assert not c.status(tmp_path)['phases'][0]['current']
    monkeypatch.setenv('LC_ALL', 'C')
    assert c.status(tmp_path)['phases'][0]['current']
    interpreter.write_bytes(b'changed-runtime')
    assert not c.status(tmp_path)['phases'][0]['current']
    interpreter.write_bytes(b'first-runtime')
    assert c.status(tmp_path)['phases'][0]['current']
    interpreter.unlink()
    assert not c.status(tmp_path)['phases'][0]['current']


def test_partial_phase_refresh_retains_concrete_repairs(tmp_path):
    parents={}
    for phase,deps in c.DAG.items():
        _,sha=receipt(tmp_path,phase,parents={p:parents[p] for p in deps})
        parents[phase]=sha
    result=c.refresh(tmp_path)
    assert result['next_command'] is None
    assert not result['program_complete']
    assert any('Compass' in text for row in result['unfinished_capabilities'] for text in row['gaps'])


def test_valid_failed_trial_is_current_evidence_not_success(tmp_path):
    receipt(tmp_path, "R0", "FAIL")
    rows = c.status(tmp_path)["phases"]
    assert rows[0]["current"] and rows[0]["artifact_valid"]
    assert rows[0]["primary_criterion"] == "FAIL" and not rows[1]["can_dispatch"]
    c.refresh(tmp_path)
    assert (tmp_path / c.REL / "next-phase.json").exists()


@pytest.mark.parametrize("mutation", ["changed", "extra", "missing"])
def test_receipt_corruption_is_never_reused(tmp_path, mutation):
    folder, _ = receipt(tmp_path, "R0")
    if mutation == "changed":
        (folder / "result.json").write_text("changed")
    elif mutation == "extra":
        (folder / "unexpected").write_text("extra")
    else:
        (folder / "result.json").unlink()
    assert c.verified_attempt(tmp_path, folder) is None
    assert not c.status(tmp_path)["phases"][0]["current"]


def test_parent_change_invalidates_real_controller_descendant(tmp_path):
    folder, sha = receipt(tmp_path, "R0")
    receipt(tmp_path, "R1", parents={"R0": sha})
    assert c.status(tmp_path)["phases"][1]["current"]
    (folder / "result.json").write_text("corrupt parent")
    assert not c.status(tmp_path)["phases"][1]["current"]


def test_interrupted_attempt_and_lock_contention(tmp_path):
    folder = tmp_path / c.REL / "phases/R0/attempt-001"
    folder.mkdir(parents=True)
    write(folder / "started.json", {"method": "incomplete"})
    assert c.verified_attempt(tmp_path, folder) is None
    with c.lock(tmp_path):
        with pytest.raises(BlockingIOError):
            with c.lock(tmp_path):
                pass


def test_packaging_binding_ignores_unrelated_package_data(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('''[build-system]\nrequires = ["setuptools"]\n[project]\nname = "legalmath"\nversion = "0"\n[tool.setuptools.package-data]\nlegalmath = ["prospectus/*.lean", "interpretation/semantics/*.lean"]\n''')
    first = c.packaging_binding(tmp_path)
    pyproject.write_text('''[build-system]\nrequires = ["setuptools"]\n[project]\nname = "legalmath"\nversion = "0"\n[tool.setuptools.package-data]\nlegalmath = ["prospectus/*.lean", "interpretation/semantics/*.lean", "interpretation/assurance/*.lean"]\n''')
    assert c.packaging_binding(tmp_path) == first
    pyproject.write_text('''[build-system]\nrequires = ["setuptools"]\n[project]\nname = "legalmath"\nversion = "0"\n[tool.setuptools.package-data]\nlegalmath = ["prospectus/*.lean", "prospectus/successor/*.json"]\n''')
    assert c.packaging_binding(tmp_path) != first


def test_newest_invalid_attempt_is_not_hidden_by_older_valid_receipt(tmp_path):
    folder, _ = receipt(tmp_path, "R0")
    newer = tmp_path / c.REL / "phases" / "R0" / "attempt-002"
    newer.mkdir()
    write(newer / "started.json", {"method": "interrupted", "parents": {}})
    rows = c.status(tmp_path)["phases"]
    assert rows[0]["artifact_valid"] is False
    assert rows[0]["execution"] == "INVALID_ATTEMPT"
    assert rows[0]["current"] is False


def test_changed_parent_receipt_allows_new_attempt_with_same_method(tmp_path):
    folder = tmp_path / c.REL / "phases" / "R1" / "attempt-001"
    folder.mkdir(parents=True)
    method = c.digest(c.bindings(tmp_path, "R1"))
    write(folder / "started.json", {"method": method, "parents": {"R0": "old"}})
    assert c.unchanged_attempt(folder, method, {"R0": "new"}) is False
    assert c.unchanged_attempt(folder, method, {"R0": "old"}) is True


def test_phase_binding_tracks_transitive_project_imports_without_all_tests():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    r1 = c.bindings(root, "R1")["files"]
    r4 = c.bindings(root, "R4")["files"]
    assert "src/legalmath/prospectus/legal_review.py" in r1
    assert "scripts/prospectus_closure_basf_amount_holder.py" in r4
    assert "tests/prospectus_successor/test_closure_finance.py" not in r1
    assert "tests/prospectus_successor/test_closure_finance.py" not in r4
    assert "src/legalmath/cli.py" not in r1
    assert "src/legalmath/cli.py" in c.bindings(root, "R6")["files"]
    assert "src/legalmath/prospectus/successor/basf_scope_review.json" in r4
    assert "tests/conftest.py" in r1
    assert "src/legalmath/prospectus/__init__.py" in r1


def test_binding_changes_for_autoloaded_inputs_but_not_unrelated_metadata(tmp_path):
    scaffold(tmp_path)
    phase = "R4"
    before = c.digest(c.bindings(tmp_path, phase))
    fixture = tmp_path / "tests/conftest.py"
    fixture.write_text("# changed fixture\n")
    assert c.digest(c.bindings(tmp_path, phase)) != before
    fixture.write_text("# fixture\n")
    assert c.digest(c.bindings(tmp_path, phase)) == before
    resource = tmp_path / "src/legalmath/prospectus/successor/basf_scope_review.json"
    resource.write_text('{"new": true}')
    assert c.digest(c.bindings(tmp_path, phase)) != before
    resource.write_text("{}")
    config = tmp_path / "pyproject.toml"
    config.write_text(config.read_text() + "\n[tool.pytest.ini_options]\naddopts = '-x'\n")
    assert c.digest(c.bindings(tmp_path, phase)) != before
    config.write_text(config.read_text() + "\n[tool.setuptools.package-data]\nlegalmath = ['interpretation/semantics/*.lean']\n")
    with_pytest = c.digest(c.bindings(tmp_path, phase))
    config.write_text(config.read_text().replace("interpretation/semantics", "interpretation/assurance"))
    assert c.digest(c.bindings(tmp_path, phase)) == with_pytest


def test_package_initializer_and_relative_import_closure(tmp_path):
    root = tmp_path / "src/legalmath/prospectus"
    (root / "successor").mkdir(parents=True)
    (tmp_path / "src/legalmath/__init__.py").write_text("# root package\n")
    (root / "__init__.py").write_text("# prospectus package\n")
    (root / "successor/__init__.py").write_text("from .. import legal_review\n")
    (root / "legal_review.py").write_text("# transitive code\n")
    seed = root / "successor/seed.py"
    seed.write_text("from . import module\n")
    (root / "successor/module.py").write_text("# local module\n")
    paths = {str(path.relative_to(tmp_path)) for path in c.imported_project_files(tmp_path, [seed])}
    assert paths == {"src/legalmath/__init__.py", "src/legalmath/prospectus/__init__.py",
                     "src/legalmath/prospectus/legal_review.py",
                     "src/legalmath/prospectus/successor/__init__.py",
                     "src/legalmath/prospectus/successor/seed.py",
                     "src/legalmath/prospectus/successor/module.py"}


def test_malformed_receipt_and_started_record_fail_closed(tmp_path):
    folder, _ = receipt(tmp_path, "R0")
    (folder / "receipt.json").write_text("[]")
    assert c.status(tmp_path)["phases"][0]["execution"] == "INVALID_ATTEMPT"
    (folder / "started.json").write_text("[]")
    assert c.unchanged_attempt(folder, "any", {}) is True


def test_missing_or_malformed_execution_inputs_are_visible(tmp_path):
    first = c.status(tmp_path)["phases"][0]
    assert first["binding_issues"] and not first["can_dispatch"]
    scaffold(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname = []\n")
    assert c.packaging_binding(tmp_path)["status"] == "INVALID"
    (tmp_path / "pyproject.toml").write_text("[tool]\npytest = []\n")
    assert c.packaging_binding(tmp_path)["status"] == "INVALID"
    assert c.status(tmp_path)["phases"][0]["binding_issues"]


def test_malformed_installed_auxiliary_result_is_invalid_not_a_crash(tmp_path):
    folder = tmp_path / c.REL / "installed/attempt-001"
    folder.mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps([]))
    rows = c.auxiliary_evidence(tmp_path, "R6")
    assert any(row["status"] == "INVALID" and row["path"].endswith("attempt-001") for row in rows)


def test_nested_script_imports_use_full_module_name(tmp_path):
    scripts = tmp_path / "scripts/nested"
    scripts.mkdir(parents=True)
    seed = tmp_path / "scripts/start.py"
    seed.write_text("from scripts.nested import worker\n")
    (scripts / "__init__.py").write_text("# nested package\n")
    (scripts / "worker.py").write_text("# worker\n")
    paths = {path.relative_to(tmp_path).as_posix() for path in c.imported_project_files(tmp_path, [seed])}
    assert paths == {"scripts/start.py", "scripts/nested/__init__.py", "scripts/nested/worker.py"}


def fake_test_runner(monkeypatch, calls):
    def run(argv, **kwargs):
        from pathlib import Path
        calls.append(argv)
        output = next(arg.split("=", 1)[1] for arg in argv if arg.startswith("--junitxml="))
        Path(output).write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"/></testsuites>')
        return SimpleNamespace(returncode=0, stdout=b"controller scheduling fixture", stderr=b"")
    monkeypatch.setattr(c.subprocess, "run", run)
    monkeypatch.setattr(c.subprocess, "check_output", lambda *args, **kwargs: "fixture-commit\n")


def test_execute_allows_changed_parents_and_reuses_success(tmp_path, monkeypatch):
    _, parent_sha = receipt(tmp_path, "R0")
    folder = tmp_path / c.REL / "phases/R1/attempt-001"
    folder.mkdir(parents=True)
    write(folder / "started.json", {"method": digest(c.bindings(tmp_path, "R1")),
                                    "parents": {"R0": "previous-parent"}})
    calls = []
    fake_test_runner(monkeypatch, calls)
    result = c.execute(tmp_path, "R1")
    assert result["engineering_checks"] == "PASS" and len(calls) == 1
    retained = c.verified_attempt(tmp_path, tmp_path / result["directory"])
    assert retained["parents"] == {"R0": parent_sha}
    assert c.execute(tmp_path, "R1")["reused"] is True
    assert len(calls) == 1


def test_refresh_does_not_offer_unchanged_interrupted_retry(tmp_path, monkeypatch):
    scaffold(tmp_path)
    folder = tmp_path / c.REL / "phases/R0/attempt-001"
    folder.mkdir(parents=True)
    write(folder / "started.json", {"method": digest(c.bindings(tmp_path, "R0")), "parents": {}})
    calls = []
    fake_test_runner(monkeypatch, calls)
    refreshed = c.refresh(tmp_path)
    assert refreshed["next_command"] is None
    assert "R0" in refreshed["next_action"]
    assert c.execute(tmp_path, "R0")["execution"] == "REPAIR_REQUIRED"
    assert calls == []


def test_completed_tests_with_invalid_auxiliary_do_not_pass(tmp_path, monkeypatch):
    scaffold(tmp_path)
    monkeypatch.setattr(c, "auxiliary_evidence", lambda *args: [{"status": "INVALID"}])
    calls = []
    fake_test_runner(monkeypatch, calls)
    result = c.execute(tmp_path, "R0")
    assert result["execution"] == "COMPLETED"
    assert result["engineering_checks"] == "FAIL"
    assert c.execute(tmp_path, "R0")["execution"] == "REPAIR_REQUIRED"
    assert len(calls) == 1


@pytest.mark.parametrize("result", [
    {"execution": "COMPLETED", "engineering_checks": "FAIL"},
    {"execution": "REPAIR_REQUIRED", "engineering_checks": "NOT_CHECKED"},
])
def test_dispatcher_returns_nonzero_on_failed_criterion(monkeypatch, result):
    import sys
    from scripts import prospectus_delivery
    monkeypatch.setattr(sys, "executable", str(prospectus_delivery.ROOT / ".venv/bin/python"))
    monkeypatch.setattr(sys, "argv", ["prospectus_delivery", "--program", "closure", "phase", "--phase", "R0"])
    monkeypatch.setattr(c, "execute", lambda *args: result)
    with pytest.raises(SystemExit) as exc:
        prospectus_delivery.main()
    assert exc.value.code == 1
