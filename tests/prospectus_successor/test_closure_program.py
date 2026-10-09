"""Real closure registry/status/receipt checks, with isolated temporary roots."""
import pytest
from legalmath.prospectus.successor import closure_program as c
from legalmath.prospectus.successor.contracts import digest, write


def receipt(root, phase, outcome="PASS", parents=None):
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
