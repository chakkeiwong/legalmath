"""Current recovery keeps original complete evaluation and counts actual starts."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import types

import pytest
from legalmath.prospectus.successor import process_ledger
from legalmath.prospectus.execution_authority import write, read
from scripts import prospectus_recovery_current as check


def task():
    return {"id": "recovery", "handler": "agent", "current_recovery": deepcopy(check.SELECTOR)}


def test_current_recovery_keeps_original_evaluate_and_state_sequence():
    def evaluate(path):
        return next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "evaluate")
    assert ast.dump(evaluate(check.ROOT / check.PROBE)) == ast.dump(evaluate(check.ROOT / check.ORIGINAL_REVIEW / "probe.py"))
    original = read(check.ROOT / check.OLD / "started.json")
    assert list(check.STATES) == original["states"]


def test_current_recovery_selector_refuses_ambiguous_old_acceptance():
    check.selector(task())
    for key, wrong in (("id", "native-binding"), ("handler", "external"), ("validator", "recovery-sequence.v1"),
                       ("evidence_attempt", "old"), ("current_recovery", {})):
        with pytest.raises(ValueError, match="selector"):
            check.selector({**task(), key: wrong})
    assert check.command("attempt", "baseline") == [
        ".venv/bin/python", "-m", "scripts.prospectus_recovery_current", "run", "--attempt", "attempt", "--stage", "baseline"]


def probe_namespace(root, evaluate):
    tree = ast.parse((check.ROOT / check.PROBE).read_text())
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("commands", "counted_evaluate")]
    ns = dict(ROOT=root, Path=Path, read=read, process_ledger=process_ledger, subprocess=subprocess, evaluate=evaluate)
    exec(compile(ast.Module(body=functions, type_ignores=[]), check.PROBE, "exec"), ns)
    return ns


@pytest.mark.parametrize("state", ["baseline", "model-missing"])
def test_current_recovery_probe_records_exact_starts_and_missing_model_zero(tmp_path, monkeypatch, state):
    marker = tmp_path / "docs/implementation/prospectus-integration-closure/inputs/R0/recovery.json"
    write(marker, {"state": state})
    starts = []
    def launch(argv, **kwargs):
        starts.append(argv)
        return types.SimpleNamespace(pid=42)
    monkeypatch.setattr(subprocess, "Popen", launch)
    namespace = probe_namespace(tmp_path, lambda output: None)
    def evaluate(output):
        for command in namespace["commands"](tmp_path, state): subprocess.Popen(command)
        write(output, {"complete": {"unknown": None, "conflict": [True, False]}})
    namespace["evaluate"] = evaluate
    out = tmp_path / "clean/result.json"
    namespace["counted_evaluate"](out)
    value = process_ledger.checked(out.with_name(out.name + ".processes.json"))
    assert [r["argv"] for r in value["reservations"]] == starts
    assert len(starts) == (0 if state == "model-missing" else 2)
    assert read(out) == {"complete": {"unknown": None, "conflict": [True, False]}}
    with pytest.raises(FileExistsError):
        namespace["counted_evaluate"](out)


def test_current_recovery_probe_refuses_unreviewed_command_before_launch(tmp_path, monkeypatch):
    write(tmp_path / "docs/implementation/prospectus-integration-closure/inputs/R0/recovery.json", {"state": "baseline"})
    starts = []
    monkeypatch.setattr(subprocess, "Popen", lambda argv, **kwargs: starts.append(argv))
    namespace = probe_namespace(tmp_path, lambda output: subprocess.Popen(["unreviewed"]))
    out = tmp_path / "clean/result.json"
    with pytest.raises(RuntimeError, match="Unreviewed"):
        namespace["counted_evaluate"](out)
    assert starts == []
    assert process_ledger.checked(out.with_name(out.name + ".processes.json"))["reservations"] == []


def test_current_recovery_parent_accounting_refuses_failed_or_missing_start(tmp_path):
    process_ledger.create(tmp_path / "parent-ledger.json", 28, 0, "Incremental test; earlier count unknown")
    with pytest.raises(ValueError, match="accounting"):
        check.checked_parent(tmp_path, 1)
    index = process_ledger.reserve(tmp_path / "parent-ledger.json", ["git", "rev-parse", "HEAD"])
    process_ledger.transition(tmp_path / "parent-ledger.json", index, error="failed start")
    with pytest.raises(ValueError, match="accounting"):
        check.checked_parent(tmp_path, 1)


def test_current_recovery_storage_charges_failed_preparation_and_active_revision(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "ROOT", tmp_path)
    paths = [check.FAILED_REVIEW + "/failure.json", check.REVIEW + "/tests.xml",
             check.BASE + "/revisions/0247.json", check.BASE + "/proposals/current-recovery-247-r2.json",
             check.BASE + "/proposals/current-recovery-247.json", check.PROBE]
    total = 0
    for i, name in enumerate(paths):
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True)
        data = b"x" * (i + 1); path.write_bytes(data); total += len(data)
    assert check.charged_storage(tmp_path / "attempt")["unique_bytes"] == total
