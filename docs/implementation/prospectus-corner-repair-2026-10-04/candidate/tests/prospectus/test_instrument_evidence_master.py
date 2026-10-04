import json
from pathlib import Path
import runpy

import pytest


@pytest.fixture
def master(monkeypatch):
    scripts=Path(__file__).resolve().parents[2]/"scripts";monkeypatch.syspath_prepend(str(scripts))
    run=runpy.run_path(str(scripts/"run_instrument_evidence_closure.py"))["execute"]
    env=run.__globals__
    monkeypatch.setitem(env,"identity",lambda phase:{"files":{},"tools":{}})
    for phase in env["PHASES"]:monkeypatch.setitem(env,phase,lambda out:{"checked":True})
    return run,env


def test_failed_attempt_preserved_repair_and_plan_refresh(master,monkeypatch,tmp_path):
    run,env=master
    def fail(out):
        assert json.loads((out/"manifest.json").read_text())["status"]=="RESERVED"
        raise ValueError("corrupt source")
    monkeypatch.setitem(env,"E0",fail)
    with pytest.raises(ValueError,match="corrupt"):run("E0",output=tmp_path)
    saved=(tmp_path/"E0/attempt-001/manifest.json").read_bytes()
    with pytest.raises(ValueError,match="repair note"):run("E0",output=tmp_path)
    monkeypatch.setitem(env,"E0",lambda out:{"repaired":True})
    run("E0",output=tmp_path,repair_note="Source identity restored and checked")
    assert (tmp_path/"E0/attempt-001/manifest.json").read_bytes()==saved
    assert json.loads((tmp_path/"next-phase-plan.json").read_text())["next_phase"]=="E1"


def test_predecessor_and_output_revalidation(master,monkeypatch,tmp_path):
    run,env=master;run("E0",output=tmp_path);run("E1",output=tmp_path)
    assert run("E1",output=tmp_path)["reused"]
    (tmp_path/"E0/attempt-001/result.json").write_text("{}")
    with pytest.raises(ValueError,match="Changed phase output"):run("E1",output=tmp_path)


def test_phase_specific_identity_does_not_reuse_stale_method(master,monkeypatch,tmp_path):
    run,env=master
    run("E0",output=tmp_path)
    monkeypatch.setitem(env,"identity",lambda phase:{"changed":True})
    with pytest.raises(ValueError,match="changed predecessor"):run("E1",output=tmp_path)


def test_mid_phase_mutation_fails_and_reserves_history(master,monkeypatch,tmp_path):
    run,env=master
    def mutate(out):
        monkeypatch.setitem(env,"identity",lambda phase:{"changed":True})
        return {"apparently":"passed"}
    monkeypatch.setitem(env,"E0",mutate)
    with pytest.raises(ValueError,match="changed during"):run("E0",output=tmp_path)
    assert json.loads((tmp_path/"E0/attempt-001/manifest.json").read_text())["status"]=="FAILED"
