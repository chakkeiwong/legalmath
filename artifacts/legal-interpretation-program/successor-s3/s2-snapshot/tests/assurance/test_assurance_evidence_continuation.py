from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"))
import pytest
import assurance_evidence_core as c
import assurance_evidence_continuation as run
import assurance_evidence_protocol as p
from legalmath.canonical import digest, raw_digest
from legalmath.errors import LegalMathError


def error(code):
    class Check:
        def __enter__(self):
            self.cm = pytest.raises(LegalMathError)
            self.value = self.cm.__enter__()
        def __exit__(self, *args):
            answer = self.cm.__exit__(*args)
            assert self.value.value.code == code
            return answer
    return Check()


@pytest.fixture
def root(tmp_path):
    baseline = tmp_path/"original-allowance.json"
    baseline.write_text("40 charged calls, immutable")
    now = datetime.now(timezone.utc)
    c.save(tmp_path/run.RUN/"amendment.json", {
        "baseline_used": 40, "maximum": 100, "additional_maximum": 60,
        "additional_attempts_per_issue": 2, "phase_limits": run.LIMITS, "repair_maximum": 16,
        "baseline_issue_spending": {"issue.0": 2}, "starts_at": (now-timedelta(minutes=10)).isoformat(),
        "ends_at": (now+timedelta(hours=48)).isoformat(),
        "allowed_issues": ["issue."+str(i) for i in range(100)],
        "protected_checkpoint": [c.receipt(baseline, tmp_path)]})
    return tmp_path


def task(i=0, phase="propagation"):
    request = {"kind": "review", "source_packet": {"units": [{"unit_id": "unit.original", "text": "Complete retained source."}]},
               "questions": [{"id": "question.original", "missing": "What remains?"}]}
    return p.make_task(phase, "structure-reader", ["issue."+str(i)], request)


def review_value(t):
    wire, _, _ = p.transport(t)
    return {"binding_hash": wire["binding_hash"], "findings": [{
        "question_id": wire["questions"][0]["id"], "status": "UNRESOLVED",
        "answer": "Date and actual case facts are missing.", "evidence": [],
        "qualifications": ["No full closure."], "needed_evidence": ["Actual period"],
        "original_question_answered": False}], "legal_correctness": "NOT_ESTABLISHED"}


def retained(root, t, value=None):
    wire, schema, _ = p.transport(t)
    slot = run.Allowance(root, t).reserve(digest(wire))
    folder = root/run.RUN/"provider-evidence"/f"{slot:04}-{digest(wire)[:16]}"
    c.save(folder/"request.json", wire)
    c.save(folder/"schema.json", schema)
    c.save(folder/"result.json", value or review_value(t))
    c.save(folder/"manifest.json", {"allowance_slot": slot, "request_hash": digest(wire),
        "files": {n: {"retained_sha256": raw_digest((folder/n).read_bytes())}
                  for n in ("request.json", "schema.json", "result.json")}})
    return folder


def test_combined_budget_cannot_be_reset(root):
    offset = 0
    for phase, n in run.LIMITS.items():
        for i in range(n):
            t = task(offset+i, phase)
            t["id"] += phase
            run.Allowance(root, t).reserve(digest([phase, i]))
        offset += n
    for i in range(60, 76):
        run.Allowance(root, task(i), correction=True).reserve(digest(i))
    status = run.Allowance(root).verify()
    assert status["used"] == 100 and status["continuation_used"] == 60
    with error("E_RESOURCE_LIMIT"):
        run.Allowance(root, task(99), correction=True).reserve("f"*64)


def test_same_canonical_issue_counts_survive_task_rename(root):
    run.Allowance(root, task()).reserve("1"*64)
    t = task()
    t["id"] = "renamed"
    run.Allowance(root, t, correction=True).reserve("2"*64)
    assert run.Allowance(root).verify()["combined_issue_spending"]["issue.0"] == 4
    with error("E_RESOURCE_LIMIT"):
        run.Allowance(root, t, correction=True).reserve("3"*64)


def test_old_checkpoint_unchanged_and_tamper_blocks(root):
    before = (root/"original-allowance.json").read_bytes()
    run.Allowance(root, task()).reserve("a"*64)
    assert (root/"original-allowance.json").read_bytes() == before
    (root/"original-allowance.json").write_text("tampered")
    with error("E_INTEGRITY"):
        run.Allowance(root)


def test_reservation_atomic_and_crash_does_not_refund(root):
    def reserve(i):
        try:
            t = task()
            t["id"] = str(i)
            return run.Allowance(root, t, correction=i > 0).reserve(digest(i))
        except LegalMathError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(reserve, range(4)))
    assert sorted(v for v in values if isinstance(v, int)) == [41, 42]
    assert values.count("E_RESOURCE_LIMIT") == 2
    (root/run.RUN/"allowance.json").unlink()
    assert run.Allowance(root).verify()["used"] == 42


def test_expired_original_window_blocks_new_call(root):
    path = root/run.RUN/"amendment.json"
    a = c.read(path)
    a["ends_at"] = "2020-01-01T00:00:00+00:00"
    c.save(path, a)
    with error("E_RESOURCE_LIMIT"):
        run.Allowance(root, task()).reserve("a"*64)


def test_resume_exact_response_no_spend(root):
    t = task()
    retained(root, t)
    def forbidden(**kw):
        pytest.fail("provider replay forbidden")
    assert run.attempt(root, t, provider_factory=forbidden)["status"] == "VALIDATED"
    assert run.attempt(root, t, provider_factory=forbidden)["status"] == "VALIDATED"
    assert run.Allowance(root).verify()["used"] == 41


def test_resume_changed_provider_rejected(root):
    t = task()
    folder = retained(root, t)
    run.attempt(root, t)
    c.save(folder/"result.json", {})
    with error("E_INTEGRITY"):
        run.attempt(root, t)


def test_interrupted_call_is_counted_and_never_repeated(root):
    t = task()
    wire, _, _ = p.transport(t)
    run.Allowance(root, t).reserve(digest(wire))
    row = run.attempt(root, t, provider_factory=lambda **kw: pytest.fail("must not replay"))
    assert row["error"] == "E_DEPENDENCY"
    assert run.Allowance(root).verify()["used"] == 41


def test_real_packets_preserve_sources_identities_and_bounded_size():
    repo = Path(__file__).resolve().parents[2]
    # Frozen-test cwd differs from live evidence root. Production source paths are fixed.
    if not (repo/c.OLD).exists():
        repo = Path("/home/chakwong/python/legalmath")
    tasks = p.propagation_tasks(repo)
    assert len(tasks) == 36
    for t in tasks:
        wire, schema, reverse = p.transport(t)
        assert len(wire["question_inventory"]) == len(reverse["questions"])
        assert len({q["question_id"] for q in wire["question_inventory"]}) == len(wire["question_inventory"])
        source = t["request"]["source_packet"]["units"]
        assert [u["text"] for u in source] == [u["text"] for u in wire["source_packet"]["units"]]
        assert p.translate(wire["readings"], reverse["tokens"]) == t["request"]["readings"]
    assert len(p.scope_tasks(repo)) == 4


def propagation_example():
    t = task()
    r = t["request"]
    r.update(kind="propagation", selected=["reading.original"], reading_hashes={"reading.original": "d"*64},
        prior_assessments={"reading.original": {"formalization": None}},
        question_inventory=[{"reading_id": "reading.original", "question_id": "question.1", "text": "Date?"},
                            {"reading_id": "reading.original", "question_id": "question.2", "text": "Facts?"}],
        obligations=[])
    r.pop("binding_hash")
    r["binding_hash"] = digest(r)
    wire, _, aliases = p.transport(t)
    value = {"binding_hash": r["binding_hash"], "legal_correctness": "NOT_ESTABLISHED",
        "readings": [{"id": "transport.reading0", "disposition": "unformalized", "reason": "No established standards.",
            "evidence": [{"unit_id": "transport.source00", "quote": "Complete retained source."}],
            "assumptions": [], "remaining": ["Date and facts."], "repairs": []}],
        "questions": [{"ids": ["transport.q00", "transport.q01"], "status": "open", "reason": "Missing dated case evidence.", "evidence": []}],
        "obligations": []}
    return t, value, aliases


def test_complete_dispositions_exact_original_ids():
    t, value, aliases = propagation_example()
    row = p.validate(value, t, aliases)
    assert [x["question_id"] for x in row["question_updates"]] == ["question.1", "question.2"]
    for ids in (["transport.q00"], ["transport.q00", "transport.q00"], ["transport.q00", "foreign"]):
        bad = deepcopy(value)
        bad["questions"][0]["ids"] = ids
        with error("E_REFERENCE"):
            p.validate(bad, t, aliases)


def test_exact_quote_and_cannot_retain_missing_program():
    t, value, aliases = propagation_example()
    value["readings"][0]["evidence"][0]["quote"] = "Invented quotation"
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)
    value["readings"][0]["evidence"][0]["quote"] = "Complete retained source."
    value["readings"][0]["disposition"] = "conditional"
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)


def test_incomplete_phase_cannot_reach_final(root, monkeypatch):
    monkeypatch.setattr(run.phases, "context", lambda r: {"candidates": {"reading.original": {}}})
    with error("E_REFERENCE"):
        run.check_coverage(root)


def test_pilot_failure_blocks_breadth_and_refreshes(root, monkeypatch):
    monkeypatch.setattr(run, "attempt", lambda *a, **kw: {"status": "FAILED", "error": "E_RESOURCE_LIMIT",
        "details": "Codex call deadline"})
    monkeypatch.setattr(run, "consecutive_failures", lambda r: 2)
    assert not run.run_tasks(root, [task(0), task(1)], pilot=True)
    saved = c.read(root/run.RUN/"next-phase-plan.json")
    assert saved["halt"] and saved["next_phase"] == "pilot"
    assert not run.state(root)["phases"]


def test_completed_phase_receipt_and_plan_refresh(root):
    run.phase_done(root, "pilot", {"tasks": ["pair"]})
    saved = c.read(root/run.RUN/"next-phase-plan.json")
    assert saved["next_phase"] == "scope"
    assert saved["allowance"]["used"] == 40
    assert len(list((root/run.RUN/"plan-history").glob("*.json"))) == 1



def test_actual_provider_settings_are_preflight_validated():
    settings = run.provider_settings()
    assert settings.timeout_seconds == 300
    assert settings.max_output_bytes == 80000


def test_local_failure_without_reservation_never_triggers_model_retry(root, monkeypatch):
    calls = []
    def fail_local(*args, **kwargs):
        calls.append(1)
        return {"status": "FAILED", "error": "E_SCHEMA", "details": "Local settings", "allowance_slot": None}
    monkeypatch.setattr(run, "attempt", fail_local)
    assert not run.run_tasks(root, [task(0), task(1)], pilot=True)
    assert len(calls) == 2
    assert run.Allowance(root).verify()["used"] == 40


def test_rejected_aliases_are_canonical_before_corrective_transport():
    t, value, aliases = propagation_example()
    canonical_value = run.canonical_prior_output(t, value)
    assert canonical_value["readings"][0]["id"] == "reading.original"
    t["request"]["correction"] = {"prior_output": canonical_value}
    t["request"].pop("binding_hash")
    t["request"]["binding_hash"] = digest(t["request"])
    p.transport(t)


def test_conservative_repair_disposition_does_not_promote_program():
    t, value, aliases = propagation_example()
    value["readings"][0]["repairs"] = ["Establish a standard before adding a program."]
    result = p.validate(value, t, aliases)
    row = result["reading_updates"][0]
    assert row["disposition"] == "RETAIN_UNFORMALIZED"
    assert "Establish a standard" in row["remaining_questions"][-1]
    t["request"]["prior_assessments"]["reading.original"]["formalization"] = {"result": "true"}
    value["readings"][0]["disposition"] = "conditional"
    result = p.validate(value, t, aliases)
    assert result["reading_updates"][0]["disposition"] == "CHALLENGED"
    assert result["reading_updates"][0]["required_program_repairs"]


def test_failed_historical_scope_does_not_block_unrelated_readings(root, monkeypatch):
    monkeypatch.setattr(run, "attempt", lambda *a, **kw: {"status": "FAILED", "error": "E_SCHEMA", "allowance_slot": None})
    assert run.run_tasks(root, [task(0, "scope"), task(1, "scope")])
    run.phase_done(root, "pilot", {"tasks": ["pair"]})
    run.phase_done(root, "scope", {"status": "COMPLETED_WITH_OPEN_TASKS", "unaccepted_tasks": ["historical"]})
    assert run.state(root)["phases"]["scope"]["status"] == "COMPLETED_WITH_OPEN_TASKS"
    assert c.read(root/run.RUN/"next-phase-plan.json")["next_phase"] == "propagation"


def paired_task():
    t, value, aliases = propagation_example()
    r = t["request"]
    second = "reading.second"
    first = r["selected"][0]
    r["selected"].append(second)
    r["readings"] = {first: {"subject": "first"}, second: {"subject": "second"}}
    r["questions"] = {first: {"question": "first"}, second: {"question": "second"}}
    r["reading_hashes"][second] = "e"*64
    r["prior_assessments"][second] = {"formalization": None}
    r["question_inventory"].append({"reading_id": second, "question_id": "question.1", "text": "Date?"})
    r["obligations"] = [{"id": "obligation.shared", "candidate_ids": [first, second], "dimension": "time"}]
    t["issues"] = ["reading."+cid+"."+t["role"] for cid in r["selected"]]
    r.pop("binding_hash")
    r["binding_hash"] = digest(r)
    return t


def test_timeout_split_preserves_complete_sources_and_pair_question_ids():
    original = paired_task()
    children = run.split_timeout_task(original)
    assert len(children) == 2
    assert {i for child in children for i in child["issues"]} == set(original["issues"])
    assert all(child["counted_repair"] for child in children)
    assert all(child["request"]["source_packet"] == original["request"]["source_packet"] for child in children)
    assert sum(len(t["request"]["question_inventory"]) for t in children) == 3
    assert all(len(t["request"]["selected"]) == 1 for t in children)
    assert children == run.split_timeout_task(original)


def test_split_timeout_recovery_reuses_children_without_new_call(root, monkeypatch):
    t = paired_task()
    children = run.split_timeout_task(t)
    calls = []
    def attempt_child(root, task):
        calls.append(task["id"])
        return {"task": task["id"], "status": "VALIDATED"}
    monkeypatch.setattr(run, "attempt", attempt_child)
    failure = {"error": "E_RESOURCE_LIMIT", "details": "Codex call deadline"}
    assert len(run.recover_timeout(root, t, failure)) == 2
    saved = c.read(root/run.RUN/"timeout-repairs"/(t["id"]+".json"))
    assert saved == children
    assert len(calls) == 2


def test_split_acceptance_satisfies_original_task_without_merging_ids(root, monkeypatch):
    task = paired_task()
    rows = [{"task": "split."+str(i), "role": task["role"], "value": {"reading_updates": [{"reading_id": cid}]}}
            for i, cid in enumerate(task["request"]["selected"])]
    monkeypatch.setattr(run, "accepted_rows", lambda root: rows)
    assert run.unresolved_task_ids(root, [task]) == []
    rows.pop()
    assert run.unresolved_task_ids(root, [task]) == [task["id"]]


def test_lossless_unresolved_response_adapter_preserves_every_quote():
    t, value, aliases = propagation_example()
    value.pop("legal_correctness")
    value.pop("obligations")
    value["kind"] = "propagation"
    value["role"] = t["role"]
    value["questions"][0]["status"] = "unresolved"
    value["readings"][0]["assumptions"] = ["Assumption "+str(i) for i in range(7)]
    value["questions"][0]["evidence"] = [{"unit_id": "transport.source00", "quote": "Complete retained source."} for _ in range(5)]
    result = p.validate(value, t, aliases)
    assert len(result["reading_updates"][0]["added_assumptions"]) == 7
    assert all(len(q["evidence"]) == 5 for q in result["question_updates"])
    assert all(q["status"] == "REMAINS_OPEN" for q in result["question_updates"])
    value["questions"][0]["ids"] = ["transport.q00"]
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)


def test_adapter_cannot_infer_missing_obligation_or_mismatched_role():
    t, value, aliases = propagation_example()
    value.pop("legal_correctness")
    value.pop("obligations")
    value.update(kind="propagation", role="exception-challenger")
    value["questions"][0]["status"] = "unresolved"
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)
    value["role"] = t["role"]
    t["request"]["obligations"] = [{"id": "must-answer"}]
    with error("E_REFERENCE"):
        p.validate(value, t, aliases)


def test_existing_correction_reused_after_issue_quota_exhausted(root, monkeypatch):
    t = task()
    run.Allowance(root, t).reserve("a"*64)
    run.Allowance(root, t, correction=True).reserve("b"*64)
    c.save(root/run.RUN/"tasks"/t["id"]/"attempt-02/result.json", {})
    calls = []
    def replay(root, task, number=1, **kw):
        calls.append(number)
        return {"status": "FAILED", "error": "E_SCHEMA", "allowance_slot": 41} if number == 1 else {"status": "VALIDATED", "allowance_slot": 42}
    monkeypatch.setattr(run, "attempt", replay)
    monkeypatch.setattr(run, "refresh", lambda *args: None)
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 0)
    assert run.run_tasks(root, [t])
    assert calls == [1, 2]
    assert run.Allowance(root).verify()["used"] == 42


def test_exhausted_independent_review_does_not_reset_or_block_other_tasks(root, monkeypatch):
    t0, t1 = task(0), task(1)
    class Budget:
        def verify(self):
            return {"used": 90, "new_issue_spending": {"issue.0": 2, "issue.1": 1}}
    monkeypatch.setattr(run, "Allowance", lambda *a, **kw: Budget())
    monkeypatch.setattr(run, "refresh", lambda *a: None)
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 0)
    def response(root, t, **kw):
        return {"task": t["id"], "status": "FAILED" if t["issues"] == ["issue.0"] else "VALIDATED", "error": "E_DEPENDENCY"}
    monkeypatch.setattr(run, "attempt", response)
    assert run.run_tasks(root, [t0,t1])
    frontier=c.read(root/run.RUN/"exhausted-reading-frontier.json")
    assert frontier[0]["task"]==t0["id"]
    assert frontier[0]["status"]=="UNACCEPTED_ATTEMPTS_EXHAUSTED"


def test_two_provider_failures_still_veto_independent_frontier(root, monkeypatch):
    monkeypatch.setattr(run, "attempt", lambda root,t: {"task":t["id"],"status":"FAILED","error":"E_DEPENDENCY"})
    monkeypatch.setattr(run, "consecutive_failures", lambda root: 2)
    assert not run.run_tasks(root, [task(0),task(1)])
    assert "Two consecutive" in run.state(root)["halt"]
