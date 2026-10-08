"""Individual original-gap coverage and precedent boundary diagnostics."""
from dataclasses import replace
from scripts.legal_gap_program import ROOT, OLD, OUT, read, save, ref, check_ref, accepted, worker


def run(folder):
    g0 = check_ref(read(OUT / "state.json")["completed"]["G0"]).parent
    obligations, readings = read(g0 / "obligations.json"), read(g0 / "readings.json")
    trace_path = ROOT / "artifacts/legal-interpretation-program/problem-led-follow-up/obligation-traces.json"
    traces = read(trace_path)
    corpus = read(OLD / "T0/attempt-1/corpus.json")
    units = {u["id"]: u["text"] for u in corpus["units"]}
    questions, targets, unavailable = [], {}, []
    for gap, trace in zip(obligations, traces, strict=True):
        identity = gap["obligation_id"]
        if identity != trace["original_record"]["obligation_id"]:
            raise ValueError("Original obligation order or identity changed")
        questions.append({"id": identity, "question": gap["first_unresolved_step"] + " " +
            " ".join(p["statement"] for p in gap["missing_premises"])})
        labels = set()
        for role in trace["original_record"]["role_responses"]:
            for cited in role["response"].get("evidence", []):
                key, quote = cited["unit_id"], cited["quote"]
                if key in units and quote and quote in units[key]:
                    labels.add((key, quote))
                else:
                    unavailable.append({"obligation_id": identity, "citation": cited,
                                        "reason": "Prior citation unavailable in frozen corpus"})
        targets[identity] = [{"unit_id": key, "quote": quote} for key, quote in sorted(labels)]
    questions += [{"id": r["reading_id"], "question": r["retained_statement"]} for r in readings]
    result = worker("retrieval", {"corpus": corpus, "questions": questions, "targets": targets}, folder / "retrieval")
    summaries = {}
    for row in result["rows"]:
        for passage in row["passages"]:
            if units[passage["unit_id"]][passage["start"]:passage["end"]] != passage["text"]:
                raise ValueError("Individual retrieval changed source text")
        summaries.setdefault(row["question_id"], []).append({
            "mode": row["mode"], "targets_found": row["targets_found"],
            "annotated_targets": row["annotated_targets"], "missing": row["missing"],
            "retrieved_characters": sum(len(p["text"]) for p in row["passages"]),
            "source_identity": "CHECKED", "legal_resolution": "NOT_ESTABLISHED"})
    save(folder / "retrieval-coverage.json", {"records": summaries, "unavailable_labels": unavailable,
        "raw": ref(folder / "retrieval/output.json"),
        "interpretation": "Missing-premise/reading location queries; inherited citation targets, not independent legal labels"})

    overlay_path = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2/overlay.json"
    originals = {}
    for row in read(overlay_path)["records"]:
        identity, original = row["reading_id"], row["operative"]["original_reading"]
        if identity in originals and originals[identity] != original:
            raise ValueError("Conflicting copies of an original reading")
        originals[identity] = original
    if set(originals) != {r["reading_id"] for r in readings}:
        raise ValueError("Original reading inventory changed")
    from legalmath.translation.expressions import expression
    encoded, coverage = [], []
    for retained in readings:
        identity = retained["reading_id"]
        original = originals[identity]
        formal = original.get("formalization")
        row = {"reading_id": identity, "retained_statement": retained["retained_statement"],
               "source_equivalence": "NOT_ESTABLISHED", "formalization": formal,
               "citations": original["citations"]}
        if formal is None:
            row["status"] = "UNFORMALIZED"
        elif formal["result_type"] != "bool" or any(f["type"] != "bool" for f in formal["facts"]):
            row["status"] = "UNSUPPORTED_PROFILE"
        else:
            encoded.append({"id": identity, "scope": expression(formal["scope"], "scope"),
                            "result": expression(formal["result"], "result")})
            row["status"] = "PENDING_XML"
        coverage.append(row)
    boolean = worker("boolean", {"readings": encoded}, folder / "original-readings")
    by_id = {r["id"]: r for r in boolean["readings"]}
    for row in coverage:
        if row["status"] == "PENDING_XML":
            row["status"] = by_id[row["reading_id"]]["status"]
            row["xml_evidence"] = ref(folder / "original-readings/output.json")
    save(folder / "reading-coverage.json", coverage)
    save(folder / "inputs.json", [ref(trace_path), ref(overlay_path)])
    return {"status": "ORIGINAL_RECORDS_TESTED", "obligation_queries": len(obligations),
            "reading_queries": len(readings), "original_boolean_readings": len(encoded),
            "boolean_status": boolean["status"], "retrieval": ref(folder / "retrieval-coverage.json"),
            "readings": ref(folder / "reading-coverage.json"), "inputs": ref(folder / "inputs.json"),
            "legal_closures": 0}


def case_boundaries(folder):
    from legalmath.canonical import digest
    from legalmath.interpretation.semantics.records import SourceSpan, Interval
    from legalmath.interpretation.semantics.precedent import (
        JudgmentManifest, Passage, Proposition, Factor, Move, Authority,
        validate_case, assess_authority)
    g1 = check_ref(accepted("G1")["result"]["tools"]).parent
    value = read(g1 / "case-factors/case-records.json")
    results = []
    for case in value["cases"]:
        manifest = JudgmentManifest(**case["manifest"])
        passages = [Passage(**{**p, "span": SourceSpan(**p["span"])}) for p in case["passages"]]
        propositions = [Proposition(**p) for p in case["propositions"]]
        factors = [Factor(**f) for f in case["factors"]]
        moves = [Move(**m) for m in case["moves"]]
        authority = Authority(propositions[0].proposition_id, "HK", "Court of First Instance", None, None,
                              Interval(start=None, end=None), ("target-applicability",), "unknown")
        for name, proposed in (
            ("absent-consent", "Hypothetical target: no acceptance of the 2018 terms is established."),
            ("changed-terms", "Hypothetical target: a different custody contract governs."),
            ("different-relationship", "Hypothetical target: Product Provider, custodian and investor roles differ from the exchange-customer relationship.")):
            changed = [replace(factors[0], value=proposed, status="proposed"), *factors[1:]]
            checked = validate_case(value["packet"], digest(value["question"]), manifest, passages, propositions, changed, moves)
            force = assess_authority(manifest, propositions[0], authority, [], "2026-10-08")
            if force["binding_established"] or force["status"] != "UNRESOLVED":
                raise ValueError("Unsupported target transfer promoted")
            results.append({"case": manifest.judgment_id, "control": name, "input": proposed,
                "reference_check": checked, "authority": force, "target_classification": "NOT_IMPLEMENTED",
                "meaning": "Reference integrity accepts proposed factors; no target fact or analogy is established"})
        for name in ("unknown-factor-source", "submission-as-holding"):
            changed_factors, changed_passages, changed_props = factors, passages, propositions
            if name == "unknown-factor-source":
                changed_factors = [replace(factors[0], source_proposition_ids=("absent",)), *factors[1:]]
            else:
                changed_passages = [replace(passages[0], role="submission", span=passages[0].span.model_copy(update={"role": "submission"})), *passages[1:]]
                changed_props = [replace(propositions[0], role="holding", role_status="source-backed"), *propositions[1:]]
            try:
                validate_case(value["packet"], digest(value["question"]), manifest, changed_passages, changed_props, changed_factors, moves)
                rejected, reason = False, "Incorrectly accepted"
            except ValueError as exc:
                rejected, reason = True, str(exc)
            results.append({"case": manifest.judgment_id, "control": name, "rejected": rejected, "reason": reason})
    save(folder / "target-case-controls.json", results)
    return {"status": "PASS" if all(r.get("rejected", True) for r in results) else "FAILED",
            "controls": ref(folder / "target-case-controls.json"), "automatic_analogy": "NOT_IMPLEMENTED"}
