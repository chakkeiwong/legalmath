"""Master receipt selection faults; all checks use temporary local files."""
import json
import pytest
from scripts import run_legal_interpretation_master as master


def test_reference_tampering_is_detected_before_resume(tmp_path,monkeypatch):
    monkeypatch.setattr(master,"ROOT",tmp_path)
    p=tmp_path/"result.json";p.write_text('{"status":"qualified"}')
    reference=master.ref(p)
    assert master.checked(reference)==p
    p.write_text('{"status":"promoted"}')
    with pytest.raises(ValueError,match="Changed/missing"):
        master.checked(reference)


@pytest.mark.parametrize("action",["verify","resume"])
def test_selected_s2_dispatches_s3_without_rerunning_history(monkeypatch,tmp_path,capsys,action):
    from scripts import legal_interpretation_s3_execute as s3
    root=tmp_path/"artifacts/legal-interpretation-program/successor-s3"
    root.mkdir(parents=True);(root/"baseline.json").write_text("{}")
    monkeypatch.setattr(master,"ROOT",tmp_path)
    monkeypatch.setattr(master,"selected",lambda:{"completed_phase":"S2","master":{},"result":{"s2":"fixed"},
        "verification":{},"next_phase":"S3","next_phase_plan":{}})
    monkeypatch.setattr(master,"checked",lambda row:tmp_path/"result.json")
    calls=[]
    monkeypatch.setattr(s3,"historical",lambda:{"status":"PASS","s2":{"s2":"fixed"}})
    monkeypatch.setattr(s3,"execute",lambda:calls.append("S3"))
    monkeypatch.setattr(master,"verify_attempt",lambda p:(_ for _ in ()).throw(AssertionError("Stale S2 verification")))
    monkeypatch.setattr(master,"execute",lambda:(_ for _ in ()).throw(AssertionError("Unexpected S2 rerun")))
    monkeypatch.setattr(master.sys,"argv",["master",action])
    master.main()
    assert calls==(["S3"] if action=="resume" else [])


def test_completed_s3_resume_verifies_and_retains_next_phase(monkeypatch,tmp_path,capsys):
    monkeypatch.setattr(master,"ROOT",tmp_path)
    from scripts import legal_interpretation_s3_execute as s3
    monkeypatch.setattr(master,"selected",lambda:{"completed_phase":"S3","master":{},"result":{},
        "verification":{},"next_phase":"S4","next_phase_plan":{}})
    monkeypatch.setattr(master,"checked",lambda row:tmp_path/"result.json")
    monkeypatch.setattr(s3,"verify_attempt",lambda p:{"status":"PASS","phase":"S3"})
    monkeypatch.setattr(s3,"execute",lambda:(_ for _ in ()).throw(AssertionError("Repeated S3")))
    monkeypatch.setattr(master.sys,"argv",["master","resume"])
    master.main()
    assert json.loads(capsys.readouterr().out)["next_phase"]=="S4"


@pytest.mark.parametrize("action", ["verify", "resume"])
def test_selected_s3_dispatches_s4_without_stale_s3_verification(monkeypatch, tmp_path, capsys, action):
    from scripts import legal_interpretation_s3_execute as s3, legal_interpretation_s4_execute as s4
    folder = tmp_path / "artifacts/legal-interpretation-program/successor-s4"
    folder.mkdir(parents=True); (folder / "baseline.json").write_text("{}")
    monkeypatch.setattr(master, "ROOT", tmp_path)
    monkeypatch.setattr(master, "selected", lambda: {
        "completed_phase": "S3", "master": {}, "result": {"s3": "fixed"},
        "verification": {}, "next_phase": "S4", "next_phase_plan": {}})
    monkeypatch.setattr(master, "checked", lambda row: tmp_path / "result.json")
    calls = []
    monkeypatch.setattr(s4, "historical", lambda: {"status": "PASS", "s3": {"s3": "fixed"}})
    monkeypatch.setattr(s4, "execute", lambda: calls.append("S4"))
    monkeypatch.setattr(s3, "verify_attempt", lambda p: (_ for _ in ()).throw(AssertionError("Stale S3 method")))
    monkeypatch.setattr(s3, "execute", lambda: (_ for _ in ()).throw(AssertionError("Unexpected S3 rerun")))
    monkeypatch.setattr(master.sys, "argv", ["master", action])
    master.main()
    assert calls == (["S4"] if action == "resume" else [])


def test_completed_s4_resume_verifies_before_reporting_s5(monkeypatch, tmp_path, capsys):
    from scripts import legal_interpretation_s4_execute as s4
    monkeypatch.setattr(master, "selected", lambda: {"completed_phase": "S4", "master": {}, "result": {},
        "verification": {}, "next_phase": "S5", "next_phase_plan": {}})
    monkeypatch.setattr(master, "checked", lambda row: tmp_path / "result.json")
    monkeypatch.setattr(s4, "verify_attempt", lambda p: {"status": "PASS", "phase": "S4"})
    monkeypatch.setattr(s4, "execute", lambda: (_ for _ in ()).throw(AssertionError("Repeated S4")))
    monkeypatch.setattr(master.sys, "argv", ["master", "resume"])
    master.main()
    assert json.loads(capsys.readouterr().out)["next_phase"] == "S5"
