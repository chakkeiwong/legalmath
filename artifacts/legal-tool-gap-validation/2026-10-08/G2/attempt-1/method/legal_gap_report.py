"""Evidence matrix and honest completion criteria for the gap-validation program."""
from scripts.legal_gap_program import ROOT, OUT, DOC, read, save, ref, check_ref, accepted, ledger


def completion(direct, products, review):
    expected = {(q, arm, rep) for q in ("p10", "p14", "evidence", "gatecoin")
                for arm in ("baseline", "retrieval", "structured", "combined") for rep in (0, 1)}
    actual = {(r["question"], r["arm"], r["repetition"]) for r in direct}
    return (len(direct) == 32 and actual == expected
            and all(r["status"] == "STRUCTURE_VALIDATED" for r in direct)
            and set(products) == {"baseline", "combined"}
            and all(r.get("execution_complete") for r in products.values())
            and review.get("all_required_integration_tests_passed") is True
            and review.get("all_live_answers_reviewed") is True)


def tool_scope(classes, topics):
    rows = [{"tool": "retrieval", "role": "Locate source passages; cannot establish missing facts or the sufficiency of a standard"}]
    if set(classes) & {"source interpretation", "normative standard"}:
        rows += [{"tool": name, "role": "Check an explicitly declared interpretation; cannot supply its legal warrant"}
                 for name in ("graphs", "legalruleml", "logical-english")]
    if set(classes) & {"authority/applicability"} or set(topics) & {"OL", "OF"}:
        rows += [{"tool": name, "role": "Organize citation/factor provenance; target transfer and later treatment require evidence"}
                 for name in ("eyecite", "case-factors")]
    if "factual input" in classes:
        rows.append({"tool": "none supplies client facts", "role": "Actual dated records are a prerequisite, not model output"})
    if "question mismatch" in classes:
        rows.append({"tool": "question preservation", "role": "Keep the original requested consequence; do not replace it with a duty trigger"})
    return rows


def run(folder):
    g0 = check_ref(read(OUT / "state.json")["completed"]["G0"]).parent
    obligations = read(g0 / "obligations.json")
    readings = read(g0 / "readings.json")
    tools = read(check_ref(accepted("G1")["result"]["tools"]))
    transport = accepted("G2")["result"]
    live = accepted("G3")["result"]
    direct, products = read(check_ref(live["direct"])), read(check_ref(live["products"]))
    review = read(DOC / "substantive-review.json")
    if review.get("direct") != live["direct"] or review.get("products") != live["products"]:
        raise ValueError("Review is not bound to current comparison")
    if set(review.get("questions", {})) != {"p10", "p14", "evidence", "gatecoin"}:
        raise ValueError("Every original question requires a review")
    # This run has no client facts or newly established legal standards. Any
    # proposed closure must receive a separate, explicit evidentiary contract.
    if review.get("original_obligations_closed") != 0:
        raise ValueError("Unsupported automatic closure")
    matrix = []
    for row in obligations:
        tests = tool_scope(row["classes"], row["topics"])
        for test in tests:
            test["component_status"] = tools.get(test["tool"], {}).get("status", "PREREQUISITE_OR_BOUNDARY")
            test["individual_obligation_live_test"] = "NOT_ESTABLISHED_BY_FOUR_QUESTION_MATRIX"
        matrix.append({**row, "applicability_tests": tests, "status": "OPEN_QUALIFIED",
                       "closure_evidence": None})
    save(folder / "gap-tool-matrix.json", matrix)
    save(folder / "reading-coverage.json", [{"reading_id": r["reading_id"],
         "statement": r["retained_statement"], "formalization_status": "UNCHANGED_FROM_FROZEN_BASELINE",
         "tool_benefit": "NOT_ESTABLISHED_INDIVIDUALLY", "source_equivalence": "REQUIRES_REVIEW"} for r in readings])
    complete = completion(direct, products, review)
    result = {"status": "COMPLETE" if complete else "INCOMPLETE_WITH_EVIDENCE",
        "obligations": len(matrix), "open_obligations": 46, "readings": len(readings),
        "unformalized_readings": 32, "substantive_closures": 0,
        "direct_validated": sum(r["status"] == "STRUCTURE_VALIDATED" for r in direct),
        "direct_planned": 32, "products": products, "transport": transport["status"],
        "provider_calls": len(ledger()["calls"]), "production_defaults_changed": False,
        "all_tools_integrated": False, "statistical_ranking": "NOT_SUPPORTED",
        "review": ref(DOC / "substantive-review.json"), "matrix": ref(folder / "gap-tool-matrix.json")}
    save(folder / "decision.json", result)
    lines = ["# Tool integration and gap-validation result", "",
        result["status"] + ". All 46 original obligations remain open; 32 readings remain unformalized.", "",
        "| Component | Actual result |", "|---|---|"]
    for name, value in tools.items():
        if isinstance(value, dict):
            lines.append("| " + name + " | " + value.get("status", "REVIEWED") + " |")
    lines += ["", f"Direct responses passing structure/source-span checks: {result['direct_validated']}/32. "
              f"Provider reservations: {result['provider_calls']}/96.", "",
        "| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |",
        "|---|---|---|---|---|---|",
        "| Preserve component evidence | Actual controls retained | See each failed/unsupported control | Authored meaning can be wrong | Review source-to-rule warrant | Legal accuracy |",
        "| Keep obligations open | No complete closure evidence | Missing factual/applicability premises | Tool effect on original answer | Supply named evidence and complete product tests | Tool count closes gaps |",
        "", "| Inference status | Finding |", "|---|---|",
        "| Hard veto | Failed controls, unavailable transport or incomplete product execution remain explicit |",
        "| Statistically supported ranking | None |",
        "| Descriptive differences | Development retrieval coverage and engine/output checks only |",
        "| Default readiness | No default change justified |",
        "| Next evidence | Complete actual product trials and substantive review against original questions |", ""]
    for qid, finding in review["questions"].items():
        lines += ["**" + qid + "**. " + finding, ""]
    lines += ["Strongest alternative explanation: the tools share the same wrong authored premises. "
              "Solver agreement and XML validity cannot rule that out. The weakest evidence is "
              "the missing individual source-to-standard/fact warrant, together with any incomplete live trials.", "",
              "See gap-tool-matrix.json for all original identities, missing premises and tool applicability. "
              "A failed candidate or unavailable provider does not reject tool reuse as a research direction."]
    (folder / "result.md").write_text("\n".join(lines) + "\n")
    return result
