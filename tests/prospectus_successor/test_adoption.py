"""Adversarial development checks; no independent legal labels are manufactured."""
from copy import deepcopy
from itertools import product
import pytest
from test_successor import request, TIME
from legalmath.prospectus.successor import source_graph
from legalmath.prospectus.successor.contracts import digest, write


def graph_anchors(tmp_path, texts):
    graph = source_graph.build(request(tmp_path, texts)["bundle"], tmp_path)
    anchors = [{"unit": u["id"], "document": u["document"], "source_sha256": u["source_sha256"],
                "start": 0, "end": len(u["raw"]), "quote": u["raw"]} for u in graph["units"]]
    return graph, anchors


def test_ast_shared_definition_and_inactive_nested_branch(tmp_path):
    from legalmath.prospectus.successor.construction_ast import render
    from legalmath.prospectus.successor.intervals import check
    graph, a = graph_anchors(tmp_path, ["Shared definition", "Chosen", "Other", "Selection"])
    spec = {"version": "contract-ast.v2", "root": "root", "nodes": [
        {"id": "shared", "kind": "Text", "source": a[0]}, {"id": "yes", "kind": "Text", "source": a[1]},
        {"id": "no", "kind": "Text", "source": a[2]},
        {"id": "nested", "kind": "Choice", "options": {"shared": "shared", "no": "no"}},
        {"id": "choice", "kind": "Choice", "options": {"yes": "yes", "other": "nested"}},
        {"id": "root", "kind": "Sequence", "children": ["shared", "choice"]}],
        "selections": {"choice": {"option": "yes", "source": a[3], "reason": "Reviewed selection"}}}
    out = render(graph, spec)
    assert out["text"] == "Shared definition Chosen"
    assert out["accounting"]["complete"] and not out["unresolved"]
    assert {r["disposition"] for r in out["dispositions"] if r["source"] == a[0]} == {"COPIED", "EXCLUDED_BY_CHOICE"}
    tampered = deepcopy(out["dispositions"])
    tampered = [r for r in tampered if r["source"] != a[2]]
    assert check(graph, tampered)["gaps"][0]["unit"] == a[2]["unit"]
    tampered[0]["source"]["quote"] += " changed"
    with pytest.raises(ValueError, match="quote"):
        check(graph, tampered)


def test_ast_unmentioned_instruction_is_not_erased(tmp_path):
    from legalmath.prospectus.successor.contract_assembly import assemble
    graph, a = graph_anchors(tmp_path, ["Selected text", "Except under the governing definition"])
    spec = {"ast": {"version": "contract-ast.v2", "root": "a", "nodes": [{"id": "a", "kind": "Text", "source": a[0]}]},
            "operations": [{"unit": a[1]["unit"], "role": "INSTRUCTION", "reason": "Legacy unreviewed margin",
                            "source_text_sha256": graph["units"][1]["text_sha256"]}]}
    out = assemble(graph, spec)
    assert out["status"] == "PARTIAL"
    assert any(u["text"] == a[1]["quote"] and u["role"] == "UNKNOWN" for u in out["units"])


def test_ast_conflicting_overrides_and_half_open_dates(tmp_path):
    from legalmath.prospectus.successor.construction_ast import render
    graph, a = graph_anchors(tmp_path, ["Old", "New", "Contradiction", "Authority"])
    nodes = [{"id": str(i), "kind": "Text", "source": a[i]} for i in range(3)]
    change = {"id": "amend", "kind": "Override", "target": "0", "replacement": "1", "source": a[3],
              "authority": a[3], "reason": "Admitted amendment", "valid_from": TIME, "known_from": TIME}
    spec = {"version": "contract-ast.v2", "root": "root", "nodes": nodes + [change,
            {**change, "id": "conflict", "replacement": "2"}, {"id": "root", "kind": "Sequence", "children": ["amend", "conflict"]}]}
    assert "Conflicting active overrides: 0" in render(graph, spec)["unresolved"]
    spec["nodes"][4]["valid_from"] = "2027-01-01T00:00:00Z"
    assert not render(graph, spec)["unresolved"]
    spec["nodes"][3]["valid_until"] = "2026-02-01T00:00:00Z"
    graph["context"]["effective_at"] = "2026-02-01T00:00:00Z"
    assert render(graph, spec)["text"] == "Old Old"
    del spec["nodes"][3]["authority"]
    with pytest.raises(ValueError):
        render(graph, spec)


def test_solver_small_grammar_and_all_partial_assignments():
    from legalmath.prospectus.successor.predicates import decide, solve, evaluate
    leaves = [True, False, "a", "b"]
    grammar = leaves + [{"not": x} for x in leaves] + [{op: [a, b]} for op in ("all", "any") for a in leaves for b in leaves]
    for expr in grammar:
        for values in product((None, True, False, "conflict"), repeat=2):
            observations = dict(zip(("a", "b"), values))
            found = solve(expr, observations)
            assert found["status"] == decide(expr, observations)["status"]
            for outcome, witness in found["witnesses"].items():
                assert evaluate(expr, witness) == (outcome == "true")


def test_solver_declared_formulas_assignments_through_twelve_facts():
    from legalmath.prospectus.successor.predicates import evaluate, solve, _z3_expression
    # All assignments of these expressions, not all twelve-variable formulae.
    # Reuse one translated solver with assumption literals for this truth-table
    # check; the public entailment path is tested separately above and below.
    import z3
    for n in range(1, 13):
        facts = ["a" + str(i) for i in range(n)]
        expr = {"all": [{"any": [f, {"not": facts[(i+1) % n]}]} for i, f in enumerate(facts)]}
        result = solve(expr, {})
        outcomes = {evaluate(expr, dict(zip(facts, values))) for values in product((False, True), repeat=n)}
        assert result["status"] == ("YES" if outcomes == {True} else "NO" if outcomes == {False} else "UNKNOWN")
        variables = [z3.Bool(f) for f in facts]
        solver = z3.Solver()
        formula = _z3_expression(expr, dict(zip(facts, variables)))
        for values in product((False, True), repeat=n):
            expected = evaluate(expr, dict(zip(facts, values)))
            assert solver.check(*[v == x for v,x in zip(variables, values)], formula if not expected else z3.Not(formula)) == z3.unsat


def test_solver_constraints_conflict_timeout_and_large_case(tmp_path):
    from legalmath.prospectus.successor.predicates import solve
    graph, a = graph_anchors(tmp_path, ["A condition is required"])
    constraints = [{"id": "first", "expression": "a", "source": a[0], "reason": "Explicit premise"},
                   {"id": "second", "expression": {"not": "a"}, "source": a[0], "reason": "Contradictory admitted premise"}]
    answer = solve(True, {}, constraints, graph=graph)
    assert answer["status"] == "CONFLICT" and answer["reason"] == "INCONSISTENT_PREMISES"
    assert len(answer["unsat_core"]) == 2
    assert solve("a", {}, constraints[:1], graph=graph)["status"] == "YES"
    assert solve({"any": ["a", {"not": "a"}]}, {"a": "conflict"})["status"] == "CONFLICT"
    assert solve({"all": ["a"+str(i) for i in range(24)]}, {"a0": False})["status"] == "NO"
    import z3
    class Unknown:
        def set(self, **kwargs): pass
        def check(self): return z3.unknown
        def reason_unknown(self): return "injected resource exhaustion"
    assert solve(True, {}, solver_factory=Unknown)["reason"] == "SOLVER_UNKNOWN"
    constraints[0]["source"]["quote"] = "invented"
    with pytest.raises(ValueError):
        solve("a", {}, constraints[:1], graph=graph)


def test_reference_closure_remote_exception_and_cycle():
    from legalmath.prospectus.successor.reference_closure import close
    edges = [{"from": "main", "to": "definition", "kind": "definition", "resolved": True},
             {"from": "definition", "to": "exception", "kind": "exceptions", "resolved": True}]
    assert close(["main", "definition", "exception"], edges, ["main"])["reachable"] == ["definition", "exception", "main"]
    assert close(["main", "definition"], edges, ["main"])["unresolved"]
    edges.append({"from": "exception", "to": "main", "kind": "reference", "resolved": True})
    assert "cycle" in close(["main", "definition", "exception"], edges, ["main"])["unresolved"][0]
    assert not close(["main", "definition", "exception", "other"], edges, ["other"])["unresolved"]


def test_read_context_missing_changes_snapshot_and_tool(tmp_path):
    from legalmath.prospectus.successor.read_context import ReadContext, current
    ctx = ReadContext(tmp_path, tmp_path / "snapshots", clock=TIME)
    assert ctx.read_bytes("optional", optional=True) is None
    assert current(tmp_path, ctx.manifest())
    (tmp_path / "optional").write_text("new")
    assert not current(tmp_path, ctx.manifest())
    with pytest.raises(ValueError, match="changed"):
        ctx.read_bytes("optional")
    ctx = ReadContext(tmp_path, tmp_path / "snapshots", clock=TIME)
    ctx.read_bytes("optional", expected=digest(b"new"))
    assert ctx.clock() == TIME
    snapshot = tmp_path / ctx.records[0]["snapshot"]
    snapshot.write_text("corruption")
    assert not current(tmp_path, ctx.manifest())
    with pytest.raises(ValueError, match="Corrupt"):
        ctx.read_bytes("optional")


def test_read_context_directory_new_file_and_environment(tmp_path, monkeypatch):
    from legalmath.prospectus.successor.read_context import ReadContext, current
    (tmp_path / "inputs").mkdir()
    ctx = ReadContext(tmp_path, tmp_path / "snapshots")
    assert ctx.entries("inputs") == []
    ctx.environment("LANG")
    assert current(tmp_path, ctx.manifest())
    (tmp_path / "inputs/new").write_text("now exists")
    assert not current(tmp_path, ctx.manifest())
    with pytest.raises(ValueError): ctx.environment("SECRET_TOKEN")


from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize


class DependencyMachine(RuleBasedStateMachine):
    """Memoized capability result versus an independent fresh file read."""
    @initialize()
    def setup(self):
        import tempfile
        from pathlib import Path
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = None
        self.cached = None

    @rule(value=st.one_of(st.none(), st.binary(max_size=30)))
    def relevant_change(self, value):
        path = self.root / "input"
        if value is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(value)

    @rule(value=st.binary(max_size=20))
    def irrelevant_change(self, value):
        (self.root / "irrelevant").write_bytes(value)

    @rule()
    def corrupt_product(self):
        self.cached = "CORRUPTED"

    @rule()
    def interrupted_publication(self):
        # An uncommitted temporary output cannot replace the receipt.
        (self.root / "unpublished.tmp").write_bytes(b"incomplete")

    @invariant()
    def incremental_equals_fresh(self):
        from legalmath.prospectus.successor.read_context import ReadContext, current
        fresh_bytes = (self.root / "input").read_bytes() if (self.root / "input").exists() else None
        fresh = digest(fresh_bytes) if fresh_bytes is not None else "MISSING"
        if self.manifest is None or not current(self.root, self.manifest) or digest(self.cached) != getattr(self, "output_hash", None):
            context = ReadContext(self.root, self.root / "snapshots")
            raw = context.read_bytes("input", optional=True)
            self.cached = digest(raw) if raw is not None else "MISSING"
            self.manifest = context.manifest()
            self.output_hash = digest(self.cached)
        assert self.cached == fresh

    def teardown(self):
        self.temp.cleanup()


TestDependencyMachine = DependencyMachine.TestCase
TestDependencyMachine.settings = settings(max_examples=30, stateful_step_count=25, derandomize=True, deadline=None)


def test_annotation_utf16_discontinuous_repeat_edit_and_reimport():
    from legalmath.prospectus.successor.annotation_bridge import export, reimport, from_utf16, to_utf16
    text = "😀 e\u0301. Same. Same.\nNo loss except\namend-\nment."
    source = {"document": "fixture", "source_sha256": digest(b"PDF"), "text_sha256": digest(text.encode())}
    spans = [{"start": 0, "end": 5, "quote": text[:5]},
             {"start": text.index("amend-"), "end": len(text), "quote": text[text.index("amend-"):]}]
    repeated = text.index("Same.", text.index("Same.")+1)
    groups = [{"id": "g1", "label": "condition", "spans": spans},
              {"id": "g2", "label": "exception", "spans": [{"start": repeated, "end": repeated+5, "quote": "Same."}]}]
    relations = [{"id": "r1", "from": "g1", "to": "g2", "kind": "exception"}]
    packet = export(text, source, groups, relations)
    assert packet["groups"][0]["spans"][0]["end"] == 6
    assert reimport(packet, text, source)["groups"] == groups
    for i in range(len(text)+1):
        assert from_utf16(text, to_utf16(text, i)) == i
    with pytest.raises(ValueError, match="surrogate"):
        from_utf16(text, 1)
    edited = deepcopy(packet)
    edited["groups"][1]["label"] = "definition"
    assert reimport(edited, text, source)["groups"][1]["label"] == "definition"
    with pytest.raises(ValueError, match="changed"):
        reimport(packet, text.replace("amend-\nment", "amendment"), source)
    packet["relations"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="relation"):
        reimport(packet, text, source)


def test_layout_never_normalizes_away_negation_or_hyphen():
    from legalmath.prospectus.successor.layout_adapter import map_layout
    raw = [{"id": "u", "source_sha256": "a"*64, "page": 1, "bbox": [0,0,10,3], "words": [
        {"text": "Not", "start": 0, "end": 3, "bbox": [0,0,3,1]},
        {"text": "amend-", "start": 4, "end": 10, "bbox": [4,0,10,1]},
        {"text": "ment", "start": 11, "end": 15, "bbox": [0,2,4,3]}]}]
    item = {"self_ref": "#/texts/0", "text": "Not amend-\nment", "label": "footnote",
            "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 0, "r": 10, "b": 3, "coord_origin": "TOPLEFT"}}]}
    doc = {"texts": [item]}
    assert not map_layout(raw, doc, source_sha256="a"*64)["failures"]
    item["text"] = "Not amendment"
    assert map_layout(raw, doc, source_sha256="a"*64)["failures"]
    item["text"] = "amend-ment"
    assert map_layout(raw, doc, source_sha256="a"*64)["failures"]


def test_layout_preserves_mixed_font_order_and_structural_numbers():
    from legalmath.prospectus.successor.layout_adapter import map_layout
    raw = [{"id": "line", "source_sha256": "a"*64, "page": 1, "bbox": [0,0,10,2], "words": [
        {"text": "(4)", "start": 0, "end": 3, "bbox": [0,0.2,2,1]},
        {"text": "Definition", "start": 4, "end": 14, "bbox": [3,0.3,7,1]},
        {"text": "applies", "start": 15, "end": 22, "bbox": [8,0,10,1]}]}]
    item = {"self_ref": "i", "label": "list_item", "text": "Definition applies", "marker": "(4)", "enumerated": True,
            "prov": [{"page_no": 1, "bbox": {"l": 0, "t": 0, "r": 10, "b": 2, "coord_origin": "TOPLEFT"}}]}
    out = map_layout(raw, {"texts": [item]}, source_sha256="a"*64)
    assert not out["failures"]
    assert out["mappings"][0]["text"] == "(4) Definition applies"


def test_coupon_independent_fractions_and_missing_reference():
    from legalmath.prospectus.successor.fixed_coupon import year_fraction
    from legalmath.prospectus.successor.adoption_trials import coupon_cases
    from fractions import Fraction
    for case in coupon_cases():
        assert year_fraction(case["start"], case["end"], case["convention"], references=case["references"],
                             frequency=case["frequency"], eom=case["eom"]) == Fraction(case["expected_exact"])
    with pytest.raises(ValueError, match="guessing"):
        year_fraction("2024-01-01", "2024-02-01", "ACT_ACT_ICMA", references=[], frequency=2, eom=False)
    with pytest.raises(ValueError, match="contiguous"):
        year_fraction("2024-01-01", "2024-08-01", "ACT_ACT_ICMA",
                      references=[{"start": "2024-01-01", "end": "2024-07-01"}, {"start": "2024-07-02", "end": "2025-01-02"}],
                      frequency=2, eom=False)


def test_coupon_calendar_holidays_and_coverage():
    from legalmath.prospectus.successor.fixed_coupon import adjusted
    calendar = {"edition": "TARGET-2024 explicit test", "valid_from": "2024-01-01", "valid_until": "2025-01-01",
                "weekend": [5,6], "holidays": ["2024-03-29", "2024-04-01"], "coverage": "COMPLETE_DECLARED_INTERVAL"}
    assert adjusted("2024-03-29", "FOLLOWING", calendar) == "2024-04-02"
    assert adjusted("2024-03-29", "MODIFIED_FOLLOWING", calendar) == "2024-03-28"
    assert adjusted("2024-03-29", "UNADJUSTED", calendar) == "2024-03-29"
    calendar["valid_until"] = "2024-04-01"
    with pytest.raises(ValueError, match="coverage"):
        adjusted("2024-03-29", "FOLLOWING", calendar)


def coupon_scenario(tmp_path):
    graph, a = graph_anchors(tmp_path, ["Explicit hypothetical coupon conventions and entitlement for a development test"])
    s = {"profile": "fixed-coupon.v1", "issue_id": graph["instrument_id"], "source_sha256": graph["documents"][0]["sha256"],
         "premise_kind": "HYPOTHETICAL", "currency": "EUR", "annual_rate": "0.05", "accrual_start": "2024-01-01",
         "accrual_end": "2025-01-01", "due_date": "2025-01-01", "payment_date": "2025-01-02",
         "day_count": "ACT_ACT_ICMA", "references": [{"start": "2024-01-01", "end": "2025-01-01"}],
         "frequency": 1, "eom": False, "stub": "REGULAR", "adjustment": "FOLLOWING",
         "calendar": {"edition": "Explicit test calendar", "valid_from": "2024-01-01", "valid_until": "2026-01-01",
                      "holidays": ["2025-01-01"], "weekend": [5,6], "coverage": "COMPLETE_DECLARED_INTERVAL"},
         "rounding": {"quantum": "0.01", "rule": "HALF_UP", "aggregation": "PER_LEGAL_HOLDER"},
         "holdings": [{"legal_holder_id": "a", "account_id": "a1", "principal": "100.1", "entitled": True},
                      {"legal_holder_id": "a", "account_id": "a2", "principal": "100.1", "entitled": True},
                      {"legal_holder_id": "b", "account_id": "b1", "principal": "100.1", "entitled": True}],
         "event_scope": {k: "REQUIRED" if k in {"accrual_start", "accrual_end", "determination", "record", "payment"} else "NOT_APPLICABLE"
                         for k in ("accrual_start", "accrual_end", "notice", "observation", "determination", "record", "ex_coupon", "payment")},
         "events": [{"id": "start", "kind": "accrual_start", "at": "2024-01-01T00:00:00Z", "order": 0},
                    {"id": "record", "kind": "record", "at": "2024-12-30T00:00:00Z", "order": 0},
                    {"id": "end", "kind": "accrual_end", "at": "2025-01-01T00:00:00Z", "order": 0},
                    {"id": "det", "kind": "determination", "at": "2025-01-01T00:00:00Z", "order": 1},
                    {"id": "pay", "kind": "payment", "at": "2025-01-02T00:00:00Z", "order": 0}]}
    s["evidence"] = {k: {"source": deepcopy(a[0]), "reason": "Explicit development assumption; not issuer facts"}
                     for k in set(s) - {"profile", "issue_id", "source_sha256", "premise_kind"}}
    return graph, s


def test_coupon_holder_aggregation_events_and_source_admission(tmp_path):
    from legalmath.prospectus.successor.fixed_coupon import calculate
    graph, s = coupon_scenario(tmp_path)
    result = calculate(s, graph)
    assert result["day_fraction"] == "1"
    assert [t["amount"] for t in result["transfers"]] == ["1001/100", "501/100"]
    assert result["actual_event"] == "NOT_ESTABLISHED" and len(result["events"]) == 5
    s["events"][3]["order"] = 0
    with pytest.raises(ValueError, match="equal-time"):
        calculate(s, graph)
    s["events"][3]["order"] = -1
    with pytest.raises(ValueError, match="order"):
        calculate(s, graph)
    s["events"][3]["order"] = 1
    del s["evidence"]["calendar"]
    with pytest.raises(ValueError):
        calculate(s, graph)


def test_coupon_service_preserves_missing_calendar_as_unsupported(tmp_path):
    from legalmath.prospectus.successor.financial_profiles import assess
    graph, s = coupon_scenario(tmp_path)
    bundle = {"instrument_id": graph["instrument_id"]}
    assert assess(bundle, s, graph)["status"] == "CONDITIONAL"
    del s["calendar"]["edition"]
    assert assess(bundle, s, graph)["status"] == "UNSUPPORTED"


def test_solver_optional_engine_is_consumed_by_service(tmp_path):
    from test_successor import PREFIX
    from legalmath.prospectus.successor import service, clause_graph, contract_assembly
    r = request(tmp_path, [PREFIX + "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."])
    graph = source_graph.build(r["bundle"], tmp_path)
    clauses = clause_graph.build(contract_assembly.assemble(graph, r["assembly"]))["nodes"]
    loss = next(n for n in clauses if n["effect"] == "principal_loss")
    loss["conditions"] = {"all": ["fact" + str(i) for i in range(24)]}
    r.update(clauses=clauses, predicate_engine="z3", observations={"fact" + str(i): True for i in range(24)})
    p1 = service.source_product(r, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    assert service.interpretation_product(p1, p2)["payload"]["questions"]["Q1"]["status"] == "YES"
    changed = service.interpretation_product(p1, p2, {"observations": {"fact0": False}})
    assert changed["payload"]["questions"]["Q1"]["status"] == "NO"
    missing = service.interpretation_product(p1, p2, {"observations": {}})
    assert missing["payload"]["questions"]["Q1"]["status"] == "UNKNOWN"


def test_read_context_tool_identity_changes(tmp_path):
    from legalmath.prospectus.successor.read_context import ReadContext, current
    tool = tmp_path / "tool"
    tool.write_text("#!/bin/sh\nexit 0\n")
    tool.chmod(0o755)
    ctx = ReadContext(tmp_path, tmp_path / "snapshots")
    assert ctx.tool([str(tool)], timeout=5).returncode == 0
    assert current(tmp_path, ctx.manifest())
    tool.write_text("#!/bin/sh\nexit 1\n")
    assert not current(tmp_path, ctx.manifest())


def test_read_context_stale_claimed_hash_and_escape(tmp_path):
    from legalmath.prospectus.successor.read_context import ReadContext
    (tmp_path / "input").write_bytes(b"changed bytes")
    ctx = ReadContext(tmp_path, tmp_path / "snapshots")
    with pytest.raises(ValueError, match="hash mismatch"):
        ctx.read_bytes("input", expected=digest(b"old bytes"))
    with pytest.raises(ValueError, match="escapes"):
        ctx.read_bytes("../not-allowed")
    with pytest.raises(ValueError, match="sidecar"):
        ctx.external_bytes("/etc/passwd")


def test_read_context_absent_file_replaced_by_directory(tmp_path):
    from legalmath.prospectus.successor.read_context import ReadContext, current
    ctx = ReadContext(tmp_path, tmp_path/"snapshots")
    ctx.read_bytes("input", optional=True)
    (tmp_path/"input").mkdir()
    assert not current(tmp_path, ctx.manifest())


def test_ast_field_value_must_recover_its_quote(tmp_path):
    from legalmath.prospectus.successor.construction_ast import render
    graph, a = graph_anchors(tmp_path, ["[amount]", "100"])
    spec = {"version": "contract-ast.v2", "root": "f", "nodes": [{"id": "f", "kind": "Field", "template": a[0],
             "source": a[1], "value": "999", "reason": "A reason alone cannot justify a different quantity"}]}
    assert "transformation unadmitted" in render(graph, spec)["unresolved"][0]


def test_coupon_cannot_switch_bundle_instrument(tmp_path):
    from legalmath.prospectus.successor.financial_profiles import assess
    graph, s = coupon_scenario(tmp_path)
    assert assess({"instrument_id": "another-bond"}, s, graph)["status"] == "UNSUPPORTED"


def test_read_context_distribution_bytes_change_under_same_version(tmp_path, monkeypatch):
    from pathlib import Path
    from legalmath.prospectus.successor import read_context
    site = tmp_path / "site-packages"
    site.mkdir()
    (site / "VERSION").write_text("1.0")
    (site / "library.py").write_text("answer = 1\n")
    # Substitute only the external-root boundary for this isolated fixture.
    def fixture_path(name):
        path = Path(name).resolve()
        if not path.is_relative_to(site):
            raise ValueError("Outside fixture distribution")
        return path
    monkeypatch.setattr(read_context, "external_path", fixture_path)
    ctx = read_context.ReadContext(tmp_path, tmp_path / "snapshots")
    ctx.external_tree(site)
    (site / "__pycache__").mkdir()
    (site / "__pycache__/library.pyc").write_bytes(b"ignored interpreter cache")
    assert read_context.current(tmp_path, ctx.manifest())
    (site / "library.py").write_text("answer = 2\n")
    assert not read_context.current(tmp_path, ctx.manifest())
    with pytest.raises(ValueError, match="changed"):
        ctx.external_tree(site)


def test_read_context_interrupted_snapshot_is_never_published(tmp_path, monkeypatch):
    from legalmath.prospectus.successor import read_context
    (tmp_path / "input").write_bytes(b"complete input")
    ctx = read_context.ReadContext(tmp_path, tmp_path / "snapshots")
    link = read_context.os.link
    def interrupted(*args, **kwargs):
        raise OSError("Injected interruption before publication")
    monkeypatch.setattr(read_context.os, "link", interrupted)
    with pytest.raises(OSError, match="Injected"):
        ctx.read_bytes("input")
    assert list((tmp_path / "snapshots").iterdir()) == []
    assert ctx.records == []
    monkeypatch.setattr(read_context.os, "link", link)
    assert ctx.read_bytes("input") == b"complete input"
    assert read_context.current(tmp_path, ctx.manifest())
