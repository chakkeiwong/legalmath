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


def test_selected_phase_never_reruns_s2(monkeypatch,tmp_path,capsys):
    p=tmp_path/"result.json"
    calls=[]
    monkeypatch.setattr(master,"selected",lambda:{"result":{},"verification":{},"next_phase":"S3","next_phase_plan":{}})
    monkeypatch.setattr(master,"checked",lambda ref:p)
    monkeypatch.setattr(master,"verify_attempt",lambda path: calls.append(path) or {"status":"PASS"})
    monkeypatch.setattr(master,"execute",lambda: (_ for _ in ()).throw(AssertionError("Unexpected rerun")))
    monkeypatch.setattr(master.sys,"argv",["master","resume"])
    master.main()
    assert calls == [tmp_path]
    assert json.loads(capsys.readouterr().out)["next_phase"]=="S3"
