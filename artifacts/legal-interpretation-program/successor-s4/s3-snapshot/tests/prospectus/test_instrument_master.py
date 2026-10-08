import json
from pathlib import Path
import runpy

import pytest


@pytest.fixture
def master(monkeypatch):
    scripts=Path(__file__).resolve().parents[2]/"scripts"
    monkeypatch.syspath_prepend(str(scripts))
    run=runpy.run_path(str(scripts/"run_instrument_gap_closure.py"))["execute"]
    env=run.__globals__
    monkeypatch.setitem(env,"identity",lambda:{"files":{},"tools":{}})
    monkeypatch.setitem(env,"I0",lambda out:{"checked":True})
    monkeypatch.setitem(env,"I1",lambda out:{"checked":True})
    return run,env


def test_failure_is_reserved_preserved_and_requires_causal_repair(master,monkeypatch,tmp_path):
    run,env=master
    def fail(out):
        assert json.loads((out/"manifest.json").read_text())["status"] == "RESERVED"
        raise ValueError("source corruption")
    monkeypatch.setitem(env,"I0",fail)
    with pytest.raises(ValueError,match="source corruption"): run("I0",output=tmp_path)
    first=(tmp_path/"I0/attempt-001/manifest.json").read_bytes()
    with pytest.raises(ValueError,match="repair note"): run("I0",output=tmp_path)
    monkeypatch.setitem(env,"I0",lambda out:{"repaired":True})
    run("I0",output=tmp_path,repair_note="Restored correct edition; source hash diagnostic passed")
    assert (tmp_path/"I0/attempt-001/manifest.json").read_bytes() == first
    assert json.loads((tmp_path/"next-phase-plan.json").read_text())["next_phase"] == "I1"


def test_altered_predecessor_and_method_cannot_reuse_pass(master,monkeypatch,tmp_path):
    run,env=master
    run("I0",output=tmp_path); run("I1",output=tmp_path)
    assert run("I1",output=tmp_path)["reused"]
    (tmp_path/"I0/attempt-001/result.json").write_text("{}")
    with pytest.raises(ValueError,match="Changed phase output"): run("I1",output=tmp_path)
    monkeypatch.setitem(env,"identity",lambda:{"files":{"changed":"hash"},"tools":{}})
    with pytest.raises(ValueError,match="changed predecessor"): run("I1",output=tmp_path)


def test_change_during_work_preserves_failure(master,monkeypatch,tmp_path):
    run,env=master
    def mutate(out):
        monkeypatch.setitem(env,"identity",lambda:{"changed":True})
        return {"apparently":"successful"}
    monkeypatch.setitem(env,"I0",mutate)
    with pytest.raises(ValueError,match="changed during"): run("I0",output=tmp_path)
    assert json.loads((tmp_path/"I0/attempt-001/manifest.json").read_text())["status"] == "FAILED"


def test_pre_execution_abstention_is_not_counted_as_native_execution(master):
    _,env=master
    report={"targets":{"ruleir":{"cases":[{"result":{"status":"VALUE"}},{"result":{"status":"ABSTAIN"}}]},
                       "catala":{"cases":[{"result":{"status":"VALUE"}},{"result":{"status":"ABSTAIN"}}]}}}
    assert env["execution_counts"](report) == {"target_cases":4,"native_executions":2,"pre_execution_abstentions":2}
