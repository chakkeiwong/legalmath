from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from contextlib import contextmanager
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"))
import pytest
import assurance_evidence_core as c
import assurance_evidence_master as m
import assurance_evidence_sources as sources
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import supplemental_repair as codec

@contextmanager
def raises_code(code):
    with pytest.raises(LegalMathError) as caught:
        yield
    assert caught.value.code == code

@pytest.fixture
def root(tmp_path):
    (tmp_path/"baseline").write_text("unchanged")
    c.save(tmp_path/c.BASE/"authorization.json", {
        "profile": c.PROFILE, "maximum": 100, "phase_limits": c.LIMITS,
        "repair_reserve": 16, "maximum_attempts_per_issue": 2, "window_hours": 48,
        "predecessors": [c.receipt(tmp_path/"baseline", tmp_path)],
        "allowed_issues": ["issue."+str(i) for i in range(120)]})
    (tmp_path/c.PLAN).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path/c.PLAN).write_text("fixed plan")
    return tmp_path

def allowance(root, i=0, phase="P1", correction=False, task="task"):
    return c.EvidenceAllowance(root, task=task, phase=phase, issues=["issue."+str(i)], correction=correction)

def test_phase_and_task_renaming_cannot_reset_canonical_issue(root):
    allowance(root).reserve("1"*64)
    allowance(root, phase="P2", correction=True, task="renamed").reserve("2"*64)
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(root, phase="P3", task="new-name").reserve("3"*64)

def test_unknown_alias_is_not_new_authorization(root):
    with raises_code("E_AUTHORITY"):
        c.EvidenceAllowance(root, task="x", phase="P1", issues=["phase.alias"]).reserve("a"*64)

def test_all_budget_limits(root, monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(c, "datetime", FixedDatetime)
    i = 0
    for phase, n in c.LIMITS.items():
        for _ in range(n):
            allowance(root, i, phase).reserve(digest(i))
            i += 1
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(root, 119).reserve("a"*64)
    for _ in range(16):
        allowance(root, i, correction=True).reserve(digest(i))
        i += 1
    assert c.EvidenceAllowance(root).verify()["used"] == 100
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(root, 118, correction=True).reserve("b"*64)

def test_concurrent_issue_reservations_are_atomic(root):
    def run(i):
        try:
            return allowance(root, task=str(i)).reserve(digest(i))
        except LegalMathError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(run, range(5)))
    assert sorted(r for r in rows if isinstance(r, int)) == [1, 2]
    assert rows.count("E_RESOURCE_LIMIT") == 3

def test_durable_journal_recovers_crash_before_projection(root):
    allowance(root).reserve("a"*64)
    path = root/c.BASE/"allowance.json"
    path.unlink()
    assert c.EvidenceAllowance(root).verify()["used"] == 1
    allowance(root, 1).reserve("b"*64)
    assert c.read(path)["calls"][0]["request_hash"] == "a"*64

def test_changed_ledger_predecessor_and_middle_journal_rejected(root):
    allowance(root).reserve("a"*64)
    allowance(root, 1).reserve("b"*64)
    path = root/c.BASE/"reservations/0001.json"
    value = c.read(path)
    value["call"]["request_hash"] = "c"*64
    c.save(path, value)
    with raises_code("E_INTEGRITY"):
        c.EvidenceAllowance(root)

def test_baseline_mutation_veto(root):
    a = allowance(root)
    (root/"baseline").write_text("changed")
    with raises_code("E_INTEGRITY"):
        a.reserve("a"*64)

def test_expiry_begins_at_first_dispatch(root, monkeypatch):
    assert allowance(root).verify()["starts_at"] is None
    allowance(root).reserve("a"*64)
    class Future(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(tz)+timedelta(hours=49)
    monkeypatch.setattr(c, "datetime", Future)
    with raises_code("E_RESOURCE_LIMIT"):
        allowance(root, 1).reserve("b"*64)
    assert allowance(root).verify()["used"] == 1

def test_locator_identity_retains_all_repeated_occurrences():
    parent = {"unit_id": "parent", "text": "section one: word; section two: word; exceptions apply."}
    loc = c.locate_repeated_quotes(parent, ["word"])
    packet = {"units": [parent, *loc]}
    assert len(loc) == 2
    assert len({u["unit_id"] for u in loc}) == 2
    c.verify_packet(packet)
    tampered = deepcopy(packet)
    tampered["units"][1]["start"] += 1
    with raises_code("E_INTEGRITY"):
        c.verify_packet(tampered)
    with raises_code("E_INTEGRITY"):
        c.verify_packet({"units": loc})

def task():
    request = {"kind": "review", "source_packet": {"units": [{"unit_id": "u", "text": "Full source text."}]},
               "questions": [{"id": "q", "missing": "What follows?"}], "binding_hash": "a"*64}
    return {"id": "test", "phase": "P1", "role": "structure-reader", "issues": ["issue.0"], "request": request}

def valid(request):
    return {"binding_hash": request["binding_hash"], "findings": [{"question_id": "q",
        "status": "PARTIALLY_SUPPORTED", "answer": "Full source exists; applicability remains open.",
        "evidence": [{"unit_id": "u", "quote": "Full source text."}], "qualifications": ["Scope limited."],
        "needed_evidence": ["Dated authority"], "original_question_answered": False}],
        "legal_correctness": "NOT_ESTABLISHED"}

def retained_provider(root, t):
    wire, schema, _ = m.preflight_task(t)
    slot = allowance(root, task=t["id"]).reserve(digest(wire))
    folder = root/c.BASE/"provider-evidence"/f"{slot:04}-{digest(wire)[:16]}"
    c.save(folder/"request.json", wire)
    c.save(folder/"schema.json", schema)
    c.save(folder/"result.json", valid(t["request"]))
    c.save(folder/"manifest.json", {"allowance_slot": slot, "request_hash": digest(wire),
        "files": {p.name: {"retained_sha256": raw_digest(p.read_bytes())}
                  for p in folder.iterdir() if p.is_file()}})
    return folder

def test_resume_saved_response_uses_zero_new_calls(root):
    t = task()
    retained_provider(root, t)
    def forbidden(**kwargs):
        raise AssertionError("must recover, not call provider")
    row = m.attempt(root, t, 1, provider_factory=forbidden)
    assert row["status"] == "VALIDATED"
    assert row["provenance"]["offline_recovery"] is True
    assert m.attempt(root, t, 1, provider_factory=forbidden)["status"] == "VALIDATED"
    assert allowance(root).verify()["used"] == 1

def test_resume_detects_changed_provider_bytes(root):
    t = task()
    folder = retained_provider(root, t)
    m.attempt(root, t, 1)
    (folder/"result.json").write_text("{}")
    with raises_code("E_INTEGRITY"):
        m.attempt(root, t, 1)

def test_interrupted_reservation_is_spent_without_blind_retry(root):
    t = task()
    wire, _, _ = m.preflight_task(t)
    allowance(root, task=t["id"]).reserve(digest(wire))
    row = m.attempt(root, t, 1, provider_factory=lambda **kw: pytest.fail("no replay"))
    assert row["status"] == "INTERRUPTED"
    assert allowance(root).verify()["used"] == 1

def test_refresh_advances_past_completed_with_open_evidence(root):
    c.save(root/c.BASE/"state.json", {"phases": {"P0": {"status": "COMPLETED_WITH_OPEN_EVIDENCE"}},
                                     "dependency_failure_streak": 0})
    row = m.refresh(root, "concrete known source repair completed")
    assert row["next_phase"] == "P1"
    text = (root/c.BASE/"next-phase-plan.md").read_text()
    assert text.startswith("# Refreshed")
    assert "Acquire bounded official sources" in text
    assert "\\n" not in text
    assert list((root/c.BASE/"plan-history").glob("*.json"))

def test_two_dependency_failures_halt_next_plan(root):
    c.save(root/c.BASE/"state.json", {"phases": {}, "dependency_failure_streak": 2})
    assert m.refresh(root, "failures")["continuation_veto"]

def test_exact_allowlist_does_not_authorize_arbitrary_flags_or_shell():
    policy = {"requested_prefix": [".venv/bin/python", "scripts/assurance_evidence_master.py"],
              "commands": [[".venv/bin/python", "scripts/assurance_evidence_master.py", "run"]]}
    assert m.check_command(policy, policy["commands"][0])
    for argv in (policy["commands"][0]+["--repo", "/elsewhere"], ["bash", "-c", "anything"]):
        with raises_code("E_AUTHORITY"):
            m.check_command(policy, argv)

def test_official_host_redirect_and_credential_boundary():
    assert sources.allowed_url("https://apps.sfc.hk/edistributionWeb/api/circular/list-content?refNo=26EC22")
    for url in ("http://www.sfc.hk/a", "https://www.sfc.hk.evil.test/a",
                "https://name:secret@www.sfc.hk/a", "https://www.sfc.hk:8443/a"):
        assert not sources.allowed_url(url)

def test_partial_or_conditional_answer_cannot_claim_original_closure():
    req = task()["request"]
    value = valid(req)
    value["findings"][0]["original_question_answered"] = True
    with raises_code("E_REFERENCE"):
        c.validate_response(value, req)

def test_acquisition_decimal_metadata_has_lossless_string_transport():
    import assurance_evidence_phases as phases
    req = {"kind": "review", "source_packet": {"units": [{"unit_id": "u", "text": "source"}]},
           "questions": [{"id": "q"}], "receipt": {"elapsed_seconds": 1.234}}
    value = phases.task("P1", "structure-reader", ["authority.q"], req)
    assert value["request"]["receipt"]["elapsed_seconds"] == "1.234"
    assert m.preflight_task(value)[2] < 200000

def test_frozen_snapshot_covers_java_and_non_python_resources(tmp_path):
    (tmp_path/"src/runtime").mkdir(parents=True)
    (tmp_path/"src/runtime/Engine.java").write_text("class Engine {}")
    hashes = c.code_material(tmp_path)
    assert "src/runtime/Engine.java" in hashes

def test_oversized_phase_stops_before_dependent_final_review(root):
    t = task()
    t["request"]["oversized_context"] = "x"*210000
    result = m.run_tasks(root, "P1", [t])
    assert result["status"] == "BLOCKED_PHASE_INPUT"
    assert result["pending_tasks"] == [t["id"]]
    assert allowance(root).verify()["used"] == 0

def test_provider_deadline_counts_as_dependency_failure_but_quota_does_not():
    assert m.dependency_failure({"error": "E_RESOURCE_LIMIT", "details": "Codex call deadline"})
    assert m.dependency_failure({"error": "E_DEPENDENCY"})
    assert not m.dependency_failure({"error": "E_RESOURCE_LIMIT", "details": "Phase allocation exhausted"})

def test_grouped_dispositions_must_cover_each_original_question_once():
    value = {"binding_hash": "a"*64, "reading_updates": [], "question_groups": [
        {"reading_id": "r", "question_ids": ["q1", "q1"], "status": "REMAINS_OPEN",
         "evidence": [], "explanation": "No dated evidence."}],
         "obligation_updates": [], "legal_correctness": "NOT_ESTABLISHED"}
    request = {"kind": "propagation_grouped", "binding_hash": "a"*64,
         "source_packet": {"units": [{"unit_id":"u","text":"source"}]}, "selected": ["r"],
         "question_inventory": [{"reading_id":"r","question_id":"q1"},{"reading_id":"r","question_id":"q2"}],
         "reading_hashes":{"r":"b"*64}, "prior_assessments":{"r":{"formalization":None}}, "obligations":[]}
    value["reading_updates"] = [{"reading_id":"r","reading_hash":"b"*64,
         "disposition":"RETAIN_UNFORMALIZED","explanation":"Still unresolved",
         "evidence":[{"unit_id":"u","quote":"source"}],"added_assumptions":[],
         "remaining_questions":["Which date?"],"required_program_repairs":[]}]
    with raises_code("E_REFERENCE"):
        c.validate_response(value,request)
    value["question_groups"][0]["question_ids"]=["q1","q2"]
    checked=c.validate_response(value,request)
    assert [r["question_id"] for r in checked["question_updates"]]==["q1","q2"]
