import json
from pathlib import Path
import pytest
from scripts import legal_gap_program as p
from scripts.legal_gap_tools import validate_graph
from scripts.legal_gap_report import completion, tool_scope


def test_fixed_cli_has_no_arbitrary_command_or_override():
    for argv in (["shell"], ["execute", "--url", "https://example.invalid"], ["execute", "--calls", "1000"]):
        with pytest.raises(SystemExit):
            p.main(argv)


def test_allowance_counts_failures_and_preserves_arm_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "OUT", tmp_path)
    monkeypatch.setattr(p, "remaining", lambda: 100)
    monkeypatch.setattr(p, "save", lambda path, value: path.write_text(json.dumps(value)))
    a = p.Allowance("probe", 1)
    assert a.reserve("a" * 64) == 1
    with pytest.raises(RuntimeError, match="Arm allowance"):
        a.reserve("b" * 64)
    assert p.Allowance("product.baseline", 1).reserve("c" * 64) == 2
    assert len(p.ledger()["calls"]) == 2
    value = p.ledger()
    value["maximum"] = 999
    (tmp_path / "provider-allowance.json").write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Changed allowance"):
        a.reserve("d" * 64)


def test_reference_change_and_symlink_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "ROOT", tmp_path)
    f = tmp_path / "source"
    f.write_text("original")
    row = p.ref(f)
    p.check_ref(row)
    f.write_text("changed")
    with pytest.raises(ValueError, match="Changed program input"):
        p.check_ref(row)
    link = tmp_path / "link"
    link.symlink_to(f)
    with pytest.raises(ValueError, match="Unsafe program path"):
        p.safe(link)


def test_invalid_graph_cannot_discard_duplicates_or_unknown_endpoints():
    for case in ({"ids": ["a", "a"], "attacks": []},
                 {"ids": ["a"], "attacks": [["a", "unknown"]]},
                 {"ids": list(map(str, range(9))), "attacks": []}):
        with pytest.raises(ValueError):
            validate_graph(case)


def test_incomplete_product_or_missing_arm_blocks_completion():
    rows = [{"question": q, "arm": a, "repetition": r, "status": "STRUCTURE_VALIDATED"}
            for q in ("p10", "p14", "evidence", "gatecoin")
            for a in ("baseline", "retrieval", "structured", "combined") for r in (0, 1)]
    products = {a: {"execution_complete": True} for a in ("baseline", "combined")}
    review = {"all_required_integration_tests_passed": True, "all_live_answers_reviewed": True}
    assert completion(rows, products, review)
    assert not completion(rows[:-1], products, review)
    assert not completion(rows, {"baseline": {"execution_complete": True}}, review)
    products["combined"]["execution_complete"] = False
    assert not completion(rows, products, review)
    assert not completion(rows, products, {})


def test_missing_facts_are_not_relabelled_as_solver_tasks():
    roles = tool_scope(["factual input"], ["TP", "TE"])
    assert any(r["tool"] == "none supplies client facts" for r in roles)
    assert not any(r["tool"] == "graphs" for r in roles)


def test_direct_arms_preserve_source_and_candidate_parity():
    from scripts.legal_gap_live import direct_request
    corpus = {"units": [{"id": "u", "text": "Exact source"}]}
    candidate = {"rules": ["conditional hypothesis"]}
    q = {"id": "p10", "question": "Original fulfillment question"}
    tools = {"retrieval": {"rows": []}, "graphs": {"status": "PASS"}}
    rows = [direct_request(q, corpus, arm, tools, candidate)
            for arm in ("baseline", "retrieval", "structured", "combined")]
    assert all(r["corpus"] == corpus and r["candidate_material"] == candidate and r["question"] == q for r in rows)
    assert "external_tool_context" not in rows[0]


def test_dispatch_constructs_valid_settings_before_marking_sent(tmp_path, monkeypatch):
    from scripts import legal_gap_live as live
    from legalmath.interpretation.search.providers import Completion
    monkeypatch.setattr(live, "save", lambda path, value: path.write_text(json.dumps(value)))
    monkeypatch.setattr(live, "ref", lambda path: {"path": str(path), "sha256": "test"})
    monkeypatch.setattr(live, "ledger", lambda: {"calls": []})
    class FakeProvider:
        routing = {"model": "test"}
        def __init__(self, **kwargs):
            pass
        def complete(self, request, schema, settings):
            assert settings.max_input_bytes == 200000
            return Completion({"status": "ready"}, {"test": True})
    monkeypatch.setattr(live, "Provider", FakeProvider)
    row = live.dispatch(tmp_path, {}, {}, "probe", 1, 45)
    assert row["status"] == "RESPONSE"


def test_product_resume_cannot_overwrite_partial_stage(tmp_path):
    from scripts.legal_gap_live import ProductProvider
    from types import SimpleNamespace
    (tmp_path / "1").mkdir()
    (tmp_path / "1/response.json").write_text('{"retained": true}')
    base = SimpleNamespace(allowance=None, routing={}, executable="unused")
    with pytest.raises(RuntimeError, match="reviewed recovery"):
        ProductProvider(base, tmp_path, True)
    assert json.loads((tmp_path / "1/response.json").read_text()) == {"retained": True}


def test_normalized_long_source_gets_distinct_exact_windows():
    from scripts.legal_gap_worker import passages
    text = "responsibility and ownership records " * 130
    rows = passages([{"id": "appendix", "text": text}])
    assert len(rows) > 1
    assert rows[0]["start"] == 0 and rows[-1]["end"] == len(text)
    for row in rows:
        assert row["text"] == text[row["start"]:row["end"]]
        assert len(row["text"]) <= 1000
    assert all(a["start"] < b["start"] < a["end"] for a, b in zip(rows, rows[1:]))


def test_retrieval_arm_cannot_see_evaluation_labels_or_missed_gold_quotes():
    from scripts.legal_gap_live import direct_request
    tools = {"retrieval": {"rows": [{"mode": "passage_bm25", "question_id": "p10",
             "passages": [{"text": "actually retrieved"}], "targets_found": 0,
             "annotated_targets": 1, "missing": [{"quote": "hidden decisive quote"}]}]}}
    row = direct_request({"id": "p10"}, {}, "retrieval", tools, {})
    context = json.dumps(row["external_tool_context"])
    assert "actually retrieved" in context
    assert "hidden decisive quote" not in context and "targets_found" not in context


def test_retrieval_context_satisfies_actual_product_serializer():
    from scripts.legal_gap_live import model_passages
    from legalmath.canonical import canonical
    rows = [{"mode": "passage_bm25", "passages": [
        {"unit_id": "u", "text": "exact text", "start": 0, "end": 10, "score": 1.23},
        {"unit_id": "v", "text": "other", "start": 0, "end": 5, "score": .123}]}]
    result = model_passages(rows)
    assert canonical(result)
    assert [p["rank"] for p in result[0]["passages"]] == [1, 2]
    assert all("score" not in p for p in result[0]["passages"])
    assert rows[0]["passages"][0]["score"] == 1.23


def test_product_retrieval_uses_packet_question_not_stage_label():
    from scripts.legal_gap_live import product_query
    question = "Does the absence of a request discharge the confirmation duty?"
    assert product_query({"task": "SOURCE_INVENTORY", "source_packet": {"selected_slice": question}}) == question
    assert product_query({"task": "SOURCE_INVENTORY"}) is None
    assert product_query({"question": "A narrower question", "source_packet": {"selected_slice": question}}) == "A narrower question"


def test_product_grant_preserves_caps_and_rejects_changed_authorization(tmp_path, monkeypatch):
    from scripts import legal_gap_recovery as recovery
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    monkeypatch.setattr(p, "OUT", tmp_path)
    monkeypatch.setattr(p, "remaining", lambda: 100)
    monkeypatch.setattr(p, "save", lambda path, value: path.write_text(json.dumps(value)))
    auth = tmp_path / "authorization.json"
    auth.write_bytes((recovery.DOC / "authorization.json").read_bytes())
    grant = recovery.ProgramGrant("baseline", authorization=auth)
    assert isinstance(grant, GrantedAllowance)
    assert grant.verify()["arm_maximum"] == 24
    for _ in range(24):
        grant.reserve("a" * 64)
    with pytest.raises(RuntimeError, match="Arm allowance"):
        grant.reserve("b" * 64)
    assert grant.verify()["used"] == 24
    auth.write_text(auth.read_text() + " ")
    with pytest.raises(ValueError, match="authorization changed"):
        grant.reserve("c" * 64)


def test_product_provider_meets_actual_scoped_provider_interface(tmp_path):
    from scripts.legal_gap_live import ProductProvider
    from legalmath.interpretation.search.providers import CodexProvider
    from types import SimpleNamespace
    wrapper = ProductProvider(SimpleNamespace(allowance=None, routing={}, executable="unused"), tmp_path, False)
    assert isinstance(wrapper, CodexProvider)


def test_counted_exact_request_revision_is_reused_without_dispatch(tmp_path, monkeypatch):
    import hashlib
    from scripts import legal_gap_live as live
    class NoDispatch:
        routing = {"provider": "fixture"}
        def __init__(self, **kwargs):
            pass
        def complete(self, *args):
            pytest.fail("A retained counted revision must never dispatch")
    monkeypatch.setattr(live, "Provider", NoDispatch)
    monkeypatch.setattr(live, "ledger", lambda: {"calls": [{"arm": "a"}]})
    monkeypatch.setattr(live, "check_ref", lambda r: Path(r["path"]))
    (tmp_path / "binding.json").write_text(json.dumps({"request": "old"}))
    (tmp_path / "row.json").write_text(json.dumps({"status": "FAILED"}))
    binding = {"request": {"new": "exact"}, "schema": {}, "arm": "a", "route": NoDispatch.routing, "timeout": 180}
    ident = hashlib.sha256(json.dumps(binding, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    revised = tmp_path / "revisions" / ident
    revised.mkdir(parents=True)
    (revised / "binding.json").write_text(json.dumps(binding))
    cached = {"status": "RESPONSE", "response": {"path": str(revised / "response.json")}, "provider_reservations": 1}
    (revised / "row.json").write_text(json.dumps(cached))
    assert live.dispatch(tmp_path, binding["request"], {}, "a", 1) == cached
    with pytest.raises(ValueError, match="counted reservation"):
        live.dispatch(tmp_path, {"different": "request"}, {}, "a", 1)
