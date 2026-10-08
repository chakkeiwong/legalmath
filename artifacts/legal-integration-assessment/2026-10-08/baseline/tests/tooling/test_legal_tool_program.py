import json
from pathlib import Path
import zipfile
import pytest
from scripts import legal_tool_program as p
from scripts.legal_tool_acquire import unpack_zip

def test_exact_command_rejects_arbitrary_arguments(monkeypatch):
    monkeypatch.chdir(p.ROOT)
    with pytest.raises(SystemExit):p.main(["execute","--url","https://example.invalid"])
    with pytest.raises(SystemExit):p.main(["shell"])

def test_reference_detects_changed_bytes(tmp_path,monkeypatch):
    monkeypatch.setattr(p,"ROOT",tmp_path)
    f=tmp_path/"record";f.write_text("original")
    r=p.ref(f)
    monkeypatch.setattr(p,"safe",lambda value:tmp_path/value)
    assert p.check_ref(r)==f
    f.write_text("changed")
    with pytest.raises(ValueError):p.check_ref(r)

def test_archive_traversal_rejected(tmp_path):
    z=tmp_path/"bad.zip"
    with zipfile.ZipFile(z,"w") as a:a.writestr("../escape","wrong")
    with pytest.raises(ValueError):unpack_zip(z,tmp_path/"expanded")
    assert not (tmp_path/"escape").exists()

def test_network_budget_consumed_before_action(tmp_path,monkeypatch):
    monkeypatch.setattr(p,"OUT",tmp_path)
    monkeypatch.setattr(p,"safe",lambda x:x)
    monkeypatch.setattr(p,"LIMITS",{"network_processes":1})
    assert p.reserve_network("first")==1
    with pytest.raises(RuntimeError):p.reserve_network("retry")
    assert len(json.loads((tmp_path/"network.json").read_text())["actions"])==1

def test_rules_only_fixed_program():
    text=p.rules_text()
    for action in p.ACTIONS:assert json.dumps(p.PREFIX+[action]) in text
    assert 'pattern=["python"]' not in text

def test_time_extension_requires_matching_user_grant(tmp_path,monkeypatch):
    from scripts import legal_tool_window as w
    monkeypatch.setattr(w,"OUT",tmp_path)
    state={"started":1000}
    original=1000+w.LIMITS["execution_seconds"]
    assert w.deadline(state)==original
    grant={"status":"PROPOSED","original_started":1000,"unchanged_limits":w.LIMITS,
           "seconds":14400,"accepted_at":20000,"user_instruction":"approved"}
    path=tmp_path/"time-extension.json"
    path.write_text(json.dumps(grant))
    with pytest.raises(ValueError):w.deadline(state)
    grant["status"]="AUTHORIZED_BY_USER"
    path.write_text(json.dumps(grant))
    assert w.deadline(state)==34400
    grant["original_started"]=2000
    path.write_text(json.dumps(grant))
    with pytest.raises(ValueError):w.deadline(state)

def test_24_hour_renewal_rejects_scope_and_duration_changes(tmp_path,monkeypatch):
    from scripts import legal_tool_window as w
    monkeypatch.setattr(w,"OUT",tmp_path)
    state={"started":1000}
    grant={"status":"AUTHORIZED_BY_USER","original_started":1000,
           "unchanged_limits":w.LIMITS,"seconds":86400,"accepted_at":20000,
           "scope":"T4_REPORT_AND_VERIFICATION_ONLY",
           "user_instruction":"you have 24 more hours.  continue"}
    path=tmp_path/"time-extension.json"
    path.write_text(json.dumps(grant))
    assert w.deadline(state)==106400
    grant["scope"]="LIVE_RETRY"
    path.write_text(json.dumps(grant))
    with pytest.raises(ValueError):w.deadline(state)
    grant["scope"]="T4_REPORT_AND_VERIFICATION_ONLY"
    grant["seconds"]=86401
    path.write_text(json.dumps(grant))
    with pytest.raises(ValueError):w.deadline(state)

def test_shared_allowance_preserves_spending(tmp_path,monkeypatch):
    from scripts import legal_tool_live as live, legal_tool_window as window
    monkeypatch.setattr(live,"OUT",tmp_path)
    monkeypatch.setattr(window,"remaining",lambda state:100)
    monkeypatch.setattr(live,"save",lambda p,v:p.write_text(json.dumps(v)))
    (tmp_path/"state.json").write_text("{}")
    first=live.ProgramAllowance("direct.baseline",1)
    first.reserve("first")
    with pytest.raises(RuntimeError):first.reserve("duplicate")
    live.ProgramAllowance("direct.tools",1).reserve("second")
    rows=json.loads((tmp_path/"provider-allowance.json").read_text())["calls"]
    assert [r["request_hash"] for r in rows]==["first","second"]
    assert first.maximum==first.reservation_ceiling==48


def test_accounting_rejects_changed_cap_and_combined_repairs(tmp_path,monkeypatch):
    from scripts import legal_tool_window as window
    monkeypatch.setattr(p,"OUT",tmp_path)
    monkeypatch.setattr(p,"check_ref",lambda item:None)
    monkeypatch.setattr(window,"deadline",lambda state:0)
    state={"limits":dict(p.LIMITS),"plan":{},"failures":[{}],"started":0}
    ledger=tmp_path/"network.json"
    ledger.write_text(json.dumps({"maximum":99,"actions":[]}))
    with pytest.raises(ValueError,match="budget ledger"):p.accounting(state)
    ledger.write_text(json.dumps({"maximum":12,"actions":[]}))
    (tmp_path/"repairs.json").write_text(json.dumps({"maximum":4,"repairs":[{}]*4}))
    with pytest.raises(ValueError,match="Repair cap"):p.accounting(state)


@pytest.mark.skipif(not (p.OUT/"T3/attempt-2/result.json").exists(),reason="Requires retained finite-program receipts")
def test_terminal_review_preserves_incomplete_evidence(monkeypatch):
    import shutil
    import tempfile
    from scripts import legal_tool_decide as decide
    checks=p.OUT/"checks"
    checks.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="terminal-preview-",dir=checks) as scratch:
        scratch=Path(scratch)
        doc=scratch/"docs"
        doc.mkdir()
        for name in ("substantive-review.json","t4-audit.md"):
            shutil.copyfile(p.DOC/name,doc/name)
        monkeypatch.setattr(decide,"DOC",doc)
        before=p.used_provider()
        result=decide.run(scratch/"report")
        assert p.used_provider()==before
        assert not result["evidence_complete"]
        assert result["live_direct_validated"]==0
        assert result["substantive_closures"]==0 and result["open_obligations"]==46
        assert not result["default_changed"] and result["next_phase"] is None
        rows={r["tool"]:r for r in result["decisions"]}
        assert rows["logical-english"]["decision"]=="DEFER_FAILED_CONTROL"
        assert rows["eyecite"]["decision"]=="DEFER_HK_CITATION_ROUTE"
        assert rows["pyarg"]["decision"]=="ADOPT_OPTIONAL_CHECKER"
        text=(scratch/"report/result.md").read_text()
        assert "no paired model answers were obtained" in text
        assert "actual product comparisons did not run" in text
        review=json.loads((doc/"substantive-review.json").read_text())
        review["question_reviews"]["p10"]["source_units"]=["invented-source-unit"]
        (doc/"substantive-review.json").write_text(json.dumps(review))
        with pytest.raises(ValueError,match="unknown source units"):
            decide.run(scratch/"invalid")

