"""Evidence matrix and honest completion criteria for the gap-validation program."""
import time
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
    if "representation" in classes:
        present = {r["tool"] for r in rows}
        rows.extend({"tool": name, "role": "Check preservation of declared structure; source meaning requires a separate warrant"}
                    for name in ("legalruleml", "graphs", "logical-english") if name not in present)
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
    from scripts.legal_gap_coverage import run as original_coverage, case_boundaries
    coverage = original_coverage(folder / "original-coverage")
    cases = case_boundaries(folder / "case-controls")
    individual = read(check_ref(coverage["retrieval"]))["records"]
    matrix = []
    for row in obligations:
        tests = tool_scope(row["classes"], row["topics"])
        for test in tests:
            test["component_status"] = tools.get(test["tool"], {}).get("status", "PREREQUISITE_OR_BOUNDARY")
            test["individual_obligation_live_test"] = "NOT_ESTABLISHED_BY_FOUR_QUESTION_MATRIX"
        matrix.append({**row, "applicability_tests": tests, "status": "OPEN_QUALIFIED",
                       "individual_retrieval_checks": individual[row["obligation_id"]],
                       "retrieval_evidence": coverage["retrieval"], "closure_evidence": None})
    save(folder / "gap-tool-matrix.json", matrix)
    save(folder / "reading-coverage.json", [{**r, "retrieval_checks": individual[r["reading_id"]],
         "tool_benefit": "Source location and representation only; no legal closure"}
         for r in read(check_ref(coverage["readings"]))])
    usage = {"retrieval_calls": 0, "graph_checks": 0, "legalruleml_checks": 0, "unsupported_checks": 0}
    for path in (OUT / "live/products").rglob("checks.json"):
        for row in read(path):
            if row.get("status") == "UNSUPPORTED":
                usage["unsupported_checks"] += 1
            elif row.get("kind") == "graph":
                usage["graph_checks"] += 1
            elif row.get("kind") == "legalruleml":
                usage["legalruleml_checks"] += 1
    usage["retrieval_calls"] = len(list((OUT / "live/products").glob("**/tool-stages/*/retrieval/output.json")))
    complete = completion(direct, products, review)
    result = {"status": "COMPLETE" if complete else "INCOMPLETE_WITH_EVIDENCE",
        "obligations": len(matrix), "open_obligations": 46, "readings": len(readings),
        "unformalized_readings": 32, "substantive_closures": 0,
        "direct_validated": sum(r["status"] == "STRUCTURE_VALIDATED" for r in direct),
        "direct_planned": 32, "products": products, "transport": transport["status"],
        "provider_calls": len(ledger()["calls"]), "production_defaults_changed": False,
        "repair_attempts": len(read(OUT / "repairs.json")["repairs"]),
        "all_tools_integrated": False, "statistical_ranking": "NOT_SUPPORTED",
        "original_record_tests": coverage, "case_boundary_tests": cases,
        "actual_product_tool_usage": usage,
        "source_scope_repair": live.get("source_scope_repair"),
        "final_product_computations": live.get("final_product_computations"),
        "scoped_grant_repair": live.get("scoped_grant_repair"),
        "review": ref(DOC / "substantive-review.json"), "matrix": ref(folder / "gap-tool-matrix.json")}
    save(folder / "decision.json", result)
    frozen = accepted("G0")
    save(folder / "run-manifest.json", {
        "git_commit": frozen["git_commit"], "dirty_product_snapshot": frozen["result"]["product_method"],
        "command": [".venv/bin/python", "scripts/run_legal_gap_program.py", "execute"],
        "environment": "repository .venv; isolated pinned tool runtime where recorded in command receipts",
        "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPUs",
        "data_version": frozen["result"]["inputs"], "seeds": "Deterministic offline controls; provider seed unavailable",
        "wall_seconds_since_start": time.time() - read(OUT / "state.json")["started"],
        "plan": frozen["plan"], "result": ref(folder / "decision.json"),
        "output_directory": str(folder.relative_to(ROOT)), "provider_calls": result["provider_calls"],
        "repair_attempts": result["repair_attempts"]})
    lines = ["# Tool integration and gap-validation result", "",
        result["status"] + ". All 46 original obligations remain open; 32 readings remain unformalized.", "",
        "| Component | Actual result |", "|---|---|"]
    for name, value in tools.items():
        if isinstance(value, dict):
            lines.append("| " + name + " | " + value.get("status", "REVIEWED") + " |")
    lines += ["", f"Direct responses passing structure/source-span checks: {result['direct_validated']}/32. "
              f"Provider reservations: {result['provider_calls']}/96.", "",
        f"Individual retrieval probes: {coverage['obligation_queries']} original obligations and "
        f"{coverage['reading_queries']} retained readings. Original Boolean readings checked: "
        f"{coverage['original_boolean_readings']} ({coverage['boolean_status']}). "
        "The paragraph 14 examples are separate controls. Thirty-two original readings remain unformalized.", "",
        "Actual product tool calls/checks: " + str(usage) + ". These counts are engineering observations.", "",
        "Final normalized product computations are checked separately from raw model graph proposals. "
        "The exact results are in decision.json under final_product_computations; these offline checks "
        "did not influence the preceding live answers.", "",
        "| Decision | Primary criterion | Veto | Main uncertainty | Next action | Not concluded |",
        "|---|---|---|---|---|---|",
        "| Preserve component evidence | Actual controls retained | See each failed/unsupported control | Authored meaning can be wrong | Review source-to-rule warrant | Legal accuracy |",
        "| Keep obligations open | No complete closure evidence | Missing factual/applicability premises | Tool effect on original answer | Supply named evidence and complete product tests | Tool count closes gaps |",
        "", "| Inference status | Finding |", "|---|---|",
        "| Hard veto | Failed controls, unavailable transport or incomplete product execution remain explicit |",
        "| Statistically supported ranking | None |",
        "| Descriptive differences | Development retrieval coverage and engine/output checks only |",
        "| Default readiness | No default change justified |",
        "| Next evidence | Address the specific failed or unavailable checks and establish source-to-standard and factual premises |", ""]
    for arm, finding in review.get("product_findings", {}).items():
        lines += ["**Product " + arm + "**. " + finding, ""]
    if review.get("source_scope_finding"):
        lines += ["**Source identity diagnostic**. " + review["source_scope_finding"], ""]
    for qid, finding in review["questions"].items():
        lines += ["**" + qid + "**. " + finding, ""]
    lines += ["Strongest alternative explanation: the tools share the same wrong authored premises. "
              "Solver agreement and XML validity cannot rule that out. The weakest evidence is "
              "the missing individual source-to-standard/fact warrant, together with any incomplete live trials.", "",
              "See gap-tool-matrix.json for all original identities, missing premises and tool applicability. "
              "A failed candidate or unavailable provider does not reject tool reuse as a research direction."]
    (folder / "result.md").write_text("\n".join(lines) + "\n")
    return result
