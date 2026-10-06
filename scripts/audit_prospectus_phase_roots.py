"""Read-only adversarial diagnostics for the committed successor checkpoint."""
from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import ast
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-phase-roots-2026-10-06"
TIME = "2026-01-01T00:00:00Z"
PREFIX = "The Notes are unsecured obligations of the Issuer. The Notes will be redeemed at 100 per cent of their principal amount at maturity."
LOSS = "Upon a Trigger Event, the principal amount of the Notes shall be written down to zero."


def main():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    app = ROOT / ".venv/bin/python"
    if Path(sys.executable).absolute() != app.absolute():
        os.execv(str(app), [str(app), "-m", "scripts.audit_prospectus_phase_roots"])
    sys.path.insert(0, str(ROOT / "src"))
    from legalmath.prospectus.successor import source_graph, contract_assembly, clause_graph, law_facts, basf, jobs, controller
    from legalmath.prospectus.successor.service import assess
    from legalmath.prospectus.successor.contracts import VERSION, digest, read, write
    from legalmath.prospectus.successor.financial_profiles import assess as finance
    from legalmath.prospectus.legal_review import AUTHORITY_FACTS
    from legalmath.prospectus.closure_mechanisms import PROFILES, whole_shares
    from legalmath.prospectus.successor.evaluation import score
    from legalmath.prospectus.successor.release import assess as release

    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    def record(key, category, observed, expectation, explanation):
        rows.append(dict(id=key, category=category, observed=observed,
                         required_behavior=expectation, explanation=explanation))

    def req(directory, texts):
        directory.mkdir(parents=True, exist_ok=True)
        p = directory / "source.txt"
        p.write_text("\f".join(texts))
        b = {"instrument_id": "synthetic", "purpose": "review", "issue_date": TIME,
             "effective_at": TIME, "known_at": TIME, "documents": [
                 {"id": "d", "path": str(p), "sha256": digest(p.read_bytes()), "format": "text",
                  "language": "en", "authority": "synthetic", "document_date": TIME, "known_from": TIME}],
             "dependencies": []}
        g = source_graph.build(b, directory)
        ops = [{"unit": u["id"], "role": "OPERATIVE", "reason": "Synthetic test contract",
                "source_text_sha256": u["text_sha256"], "context": "whole"} for u in g["units"]]
        return {"version": VERSION, "bundle": b, "assembly": {"operations": ops},
                "scope": {q: {"complete": True, "reason": "Synthetic contract"} for q in ("Q1", "Q2")}}

    def material(r, directory):
        g = source_graph.build(r["bundle"], directory)
        a = contract_assembly.assemble(g, r["assembly"])
        return g, a, clause_graph.nominate(a)

    with tempfile.TemporaryDirectory(prefix="prospectus-phase-probes-") as temp:
        tmp = Path(temp)
        r = req(tmp, [PREFIX])
        control = assess(r, tmp)["questions"]["Q1"]["status"]
        record("control-repayment", "CONTROL", control, "NO", "Complete exact grammar fixture.")
        r = req(tmp, [PREFIX + " " + PREFIX])
        duplicate = assess(r, tmp)["questions"]["Q1"]
        assert duplicate["status"] == "UNKNOWN"
        record("P3-occurrences", "IMPLEMENTATION_DEFECT", duplicate["status"], "NO",
               "Repeated identical recognized clauses cover only their first text.find occurrence.")

        r = req(tmp, [PREFIX, "Section 14"])
        r["assembly"]["operations"][1]["role"] = "HEADER"
        q = assess(r, tmp)["questions"]["Q1"]
        assert q["status"] == "UNKNOWN"
        record("P1-excluded-reference", "IMPLEMENTATION_DEFECT",
               {"status": q["status"], "unresolved": q["unresolved"]}, "NO",
               "A header explicitly excluded from semantics still contributes a global Q1/Q2 dependency.")

        # The PDF extractor's unit is a printed line. The grammar requires a complete sentence.
        r = req(tmp, [PREFIX])
        _, a, _ = material(r, tmp)
        u = a["units"][0]
        a["units"] = [{**u, "unit": "line1", "text": "The Notes will be redeemed at 100 per cent"},
                      {**u, "unit": "line2", "text": "of their principal amount at maturity."}]
        cg = clause_graph.build(a)
        q = clause_graph.evaluate(cg, a, r["scope"], [])["Q1"]
        assert q["status"] == "UNKNOWN"
        record("P1-line-segmentation", "IMPLEMENTATION_DEFECT", q["status"], "NO after paragraph reconstruction",
               "Same repayment sentence split at a visual line break is unrecognized.")

        # A complete, exactly anchored assertion spanning two units cannot earn character coverage.
        joined = "The Notes will be redeemed at 100 per cent of their principal amount at maturity."
        node = clause_graph._node(u, joined, "repayment")
        node["units"] = ["line1", "line2"]
        cg = clause_graph.build(a, [node])
        assert set(cg["uncovered_units"]) == {"line1", "line2"}
        record("P3-multispan", "IMPLEMENTATION_DEFECT", cg["uncovered_units"],
               "Both spans covered by occurrence intervals",
               "The validator accepts the joined quotation but coverage handles only one-unit nodes.")

        r = req(tmp, [PREFIX])
        g, a, nodes = material(r, tmp)
        fake = deepcopy(g)
        fake["units"][0]["visible"] = False
        text = fake["units"][0]["raw"]
        construction = {"source_map": [{"unit": fake["units"][0]["id"], "start": 0, "end": len(text)}],
            "unit_accounting": [{"unit": fake["units"][0]["id"], "role": "BODY_CANDIDATE"}],
            "raw_body": text, "candidate_text": text, "operations": []}
        role = basf.as_assembly(fake, construction)["units"][0]["role"]
        assert role == "UNKNOWN"
        record("P2-visibility", "IMPLEMENTATION_DEFECT", role, "EXCLUDED",
               "BASF adapter ignores visible=False, unlike generic assembly. This does not prove a current false YES.")

        # A complete typed explicit negative has no executable negative branch.
        r = req(tmp, ["No principal loss is permitted."])
        g, a, nodes = material(r, tmp)
        node = nodes[0]
        node.update(effect="principal_loss", polarity=False)
        r["clauses"] = [node]
        q = assess(r, tmp)["questions"]["Q1"]
        assert q["status"] == "UNKNOWN"
        record("P3-explicit-negative", "IMPLEMENTATION_DEFECT", q["status"], "NO under supplied complete interpretation",
               "Negative nodes are collected but there is no status branch consuming them.")

        r = req(tmp, [PREFIX + " " + LOSS, "The Trigger Event can occur."])
        g, a, nodes = material(r, tmp)
        nodes[-1]["effect"] = "none"
        nodes[-2]["conditions"] = [nodes[-1]["id"]]
        r["clauses"] = nodes
        q = assess(r, tmp)["questions"]["Q1"]
        assert q["status"] == "UNKNOWN"
        record("P3-condition-execution", "MISSING_CAPABILITY", q["status"],
               "Feature decision conditional on an explicitly represented trigger predicate",
               "Every condition/exception list causes unconditional abstention, even when targets resolve; the automatic Trigger Event string is not in that list.")

        # Q2 represents mixed outcomes only as an appendix, not distinct queried predicates.
        r = req(tmp, [PREFIX, "The issuer may elect common or preferred shares."])
        g, a, nodes = material(r, tmp)
        nodes[-1].update(effect="conversion", election="issuer", assets=["common", "preferred"])
        r["clauses"] = nodes
        answer = assess(r, tmp)["questions"]
        assert answer["Q2"]["status"] == "NO"
        record("P3-question-collapse", "SCHEMA_GAP",
               {"Q2": answer["Q2"]["status"], "Q3_question_keys": sorted(answer["Q3"]["value"])},
               "Separate possible-common and common-only answers; Q3 coverage for every declared question",
               "One NO field conflates Q2 variants, while Q3 reports only Q1/Q2.")

        basis = {"id": "law", "authority": "synthetic", "jurisdiction": "X", "edition": "1", "source": "unresolved:law",
                 "valid_from": TIME, "known_from": TIME, "premises": list(AUTHORITY_FACTS) + ["court_order"]}
        facts = [{"name": n, "basis_id": "law", "instrument_id": "synthetic", "value": True,
                  "source": "unresolved:fact", "known_from": TIME, "observed_at": TIME} for n in AUTHORITY_FACTS]
        facts.append({**facts[0], "name": "court_order", "value": False})
        q = law_facts.assess(r["bundle"], [basis], facts)
        assert q["status"] == "YES"
        record("P4-ignored-premise", "IMPLEMENTATION_DEFECT", q["status"], "NO for declared conjunction",
               "basis.premises is checked for nonemptiness then ignored; false extra court-order premise is unused.")
        record("P4-unresolved-source", "VALIDATION_GAP", q["status"], "Reject or mark unverified source",
               "Neither legal-basis nor fact source strings resolve to a hash-bound source anchor.")

        basis["premises"] = list(AUTHORITY_FACTS)
        facts = facts[:-1]
        facts[0]["valid_from"] = "2027-01-01T00:00:00Z"
        q = law_facts.assess(r["bundle"], [basis], facts)
        assert q["status"] == "YES"
        record("P4-fact-valid-time", "SCHEMA_GAP", q["status"], "UNKNOWN or reject unsupported valid_from",
               "Observation time is used as validity start and an explicit later valid_from is silently ignored.")

        key = "bbva-at1-series15-2025"
        bundle = {"instrument_id": key, "documents": [{"sha256": PROFILES[key]["sha256"]}]}
        scenario = {"issue_id": key, "source_sha256": PROFILES[key]["sha256"], "premise_kind": "HYPOTHETICAL",
                    "currency": "EUR", "issuer_determined_cet1_ratio": "0.01", "capital_reduction": False,
                    "condition_7_7_redemption_override": False, "listed": True, "adjusted_floor_price": "1",
                    "nominal_share_value": "1", "five_eligible_closing_prices": None}
        try:
            finance(bundle, scenario)
        except Exception as exc:
            error = type(exc).__name__
        else:
            error = "NO_EXCEPTION"
        assert error == "TypeError"
        record("P5-invalid-shape", "IMPLEMENTATION_DEFECT", error, "Structured invalid-premise outcome",
               "Missing list shape escapes the KeyError/ValueError handler and aborts the service.")
        allocations = whole_shares([{"registration_name": "Alex Lee", "account": "A", "principal": "6"},
                                   {"registration_name": "Alex Lee", "account": "B", "principal": "6"}], "10", "principal")
        assert allocations[0]["shares"] == 1
        record("P5-group-identity", "CONDITIONAL_SCHEMA_GAP", allocations,
               "Two zero-share allocations when A/B are distinct registered holders",
               "The algorithm groups by a display string. Combining two separate holders changes floor rounding; correct legal aggregation key must be supplied.")

    # Actual phase/report configuration, inspected without executing expensive jobs.
    state = read(ROOT / controller.REL / "state.json")
    p1 = read(ROOT / state["P1"]["directory"] / "request.json")
    integrated = read(ROOT / state["P6"]["directory"] / "integrated-request.json")
    context = integrated["bank"]["request"]["bank_request"]["context"]
    record("P6-context-join", "IMPLEMENTATION_DEFECT",
           {"bundle_effective_at": p1["bundle"]["effective_at"], "bank_effective_at": context["effective_at"],
            "bundle_known_at": p1["bundle"]["known_at"], "bank_known_at": context["known_at"],
            "bank_instrument_kind": context["instrument_kind"], "instrument_id": context["instrument_id"]},
           "One explicitly mapped instrument/date/context identity",
           "P6 copies a UBS AT1 request and changes only instrument_id; BASF senior debt retains at1_bond and other dates.")

    trace = {}
    for phase in ("p0", "p1", "p2", "p3", "p4", "p5", "p6"):
        fn = getattr(jobs, phase)
        tree = ast.parse(inspect.getsource(fn))
        trace[phase] = {
            "line": inspect.getsourcelines(fn)[1],
            "calls": sorted({ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}),
            "saved_parent_reads": [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
                                   and isinstance(n.func, ast.Name) and n.func.id == "parent"]}
    record("P0-unwired-inputs", "MISSING_CAPABILITY", trace["p0"], "Consume admitted reviewer/cohort/label files",
           "P0 writes an empty hardcoded protocol; no read of reviewer/cohort inputs.")
    record("P3-P6-dataflow", "IMPLEMENTATION_DEFECT", {k: trace[k] for k in ("p3", "p4", "p5", "p6")},
           "P3 consumes P2; P6 consumes P3/P4/P5 receipts",
           "The DAG orders phase execution, but semantic results are recomputed from the original P1 request; P4/P5 products are never fed into P6.")
    inputs = controller.bindings(ROOT)
    bank_request_path = "docs/implementation/prospectus-evidence-closure/phases/S3/attempt-004/bank/request.json"
    assert bank_request_path not in inputs
    record("controller-missing-input", "IMPLEMENTATION_DEFECT", {"bank_request_bound": bank_request_path in inputs,
           "has_runtime_lock": True, "global_hash": True}, "Bind every actual input and tool/environment version per phase",
           "P6 reads the prior bank request/store and deeper rule modules outside the global bindings list. Editing them need not invalidate receipts.")

    # P0/P7 evidence identity and P8 scope mismatch; adjacent controls affect release.
    ids = {"readers": ["r1", "r2"], "adjudicator": "author", "implementer": "author"}
    cohort = [{"id": "a", "questions": ["Q1"]}, {"id": "b", "questions": ["Q1"]}]
    labels = [{"id": k, "question": "Q1", "value": v, "blinded": True,
               "readers": ["r1", "r2"], "evidence": ["s"]} for k,v in (("a","YES"),("b","NO"))]
    predictions = [{k: row[k] for k in ("id","question","value")} for row in labels]
    evaluation = score(predictions, labels, cohort, ids)
    released = release(evaluation, [{"question": "Q5"}], [{"reviewer": "author", "accepted": True},
                                                        {"reviewer": "r2", "accepted": True}])
    assert released["status"] == "FINITE_ASSISTED_CANDIDATE"
    record("P0-P7-P8-independence-scope", "VALIDATION_GAP", released["status"],
           "BLOCKED for implementer adjudication and unsupported Q5 scope",
           "Identity lists and booleans are not signed independent readings; P8 does not match support questions to evaluated questions. Automatic transaction clearance remains false.")

    # Bind the audit's actual saved-input reads separately from the incomplete
    # controller binding list being tested above.
    audit_bindings = dict(inputs)
    for path in (ROOT / controller.REL / "state.json",
                 ROOT / state["P1"]["directory"] / "request.json",
                 ROOT / state["P6"]["directory"] / "integrated-request.json",
                 ROOT / bank_request_path):
        audit_bindings[str(path.relative_to(ROOT))] = digest(path.read_bytes())

    write(OUT / "counterexamples.json", {"baseline_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "rows": rows})
    write(OUT / "code-trace.json", trace)
    write(OUT / "probe-manifest.json", {"command": ["python3", "-m", "scripts.audit_prospectus_phase_roots"],
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "environment": sys.executable, "cpu_gpu": "CPU; CUDA_VISIBLE_DEVICES=-1",
        "random_seeds": "N/A deterministic constructed probes", "wall_seconds": time.monotonic()-started,
        "data_version": digest(audit_bindings), "code_bindings": audit_bindings,
        "controller_bindings_count": len(inputs), "audit_extra_input_bindings": len(audit_bindings) - len(inputs),
        "plan": "docs/plans/prospectus-phase-roots-2026-10-06.md",
        "result_file": "docs/implementation/prospectus-phase-roots-2026-10-06/counterexamples.json",
        "script_sha256": digest(Path(__file__).read_bytes()),
        "output_bindings": {str((OUT / name).relative_to(ROOT)): digest((OUT / name).read_bytes())
                            for name in ("counterexamples.json", "code-trace.json")}})
    print(json.dumps({"probes": len(rows), "observations": [
        {"id": r["id"], "category": r["category"], "observed": r["observed"]}
        for r in rows if not r["id"].startswith(("P0-unwired","P3-P6"))]}, indent=2))


if __name__ == "__main__":
    main()
