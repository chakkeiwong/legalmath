"""Post-observation diagnostic of explicitly typed source identity evidence."""
from copy import deepcopy
from scripts.legal_gap_program import OUT, read, save, ref, check_ref, accepted


def run(folder, direct):
    from legalmath.canonical import digest
    from scripts.legal_gap_live import dispatch
    from scripts.legal_tool_live import Answer, inspect_answer
    from scripts.legal_gap_program import OLD
    selected = next(r for r in direct if r["question"] == "gatecoin" and
                    r["arm"] == "combined" and r["repetition"] == 0)
    if selected["status"] != "STRUCTURE_VALIDATED":
        result = {"status": "UNTESTED_PREREQUISITE", "reason": "A valid combined comparator is required"}
        save(folder / "source-scope-diagnostic.json", result)
        return result
    binding_path = check_ref(selected["response"]).parent / "binding.json"
    binding = read(binding_path)
    request = deepcopy(binding["request"])
    g1 = check_ref(accepted("G1")["result"]["tools"]).parent
    records_path = g1 / "case-factors/case-records.json"
    records = read(records_path)
    packet_hash = digest(records["packet"])
    files = []
    for case in records["cases"]:
        if case["manifest"]["source_hash"] != packet_hash:
            raise ValueError("Case packet identity does not verify")
        raw = case["raw_source"]
        checked = check_ref({"path": raw["path"], "sha256": raw["sha256"]})
        files.append({"judgment_id": case["manifest"]["judgment_id"],
                      "object_kind": "individual_original_DOCX_bytes", "identity": ref(checked)})
    evidence = {"combined_packet": {"object_kind": "combined_normalized_source_packet",
        "sha256": packet_hash, "member_unit_ids": [u["unit_id"] for u in records["packet"]["units"]]},
        "case_manifest_source_hash_field": "Hash of the combined source packet, checked against the actual packet",
        "raw_sources": files, "legal_force": "Not assessed by source identity checking"}
    request["external_tool_context"]["verified_source_identity_scopes"] = evidence
    from legalmath.canonical import canonical
    if len(canonical(request)) > 200000:
        raise ValueError("Source-scope diagnostic exceeds provider input limit")
    save(folder / "source-scope-evidence.json", {"input": ref(records_path), "computed": evidence})
    rows = []
    corpus = read(OLD / "T0/attempt-1/corpus.json")
    for repetition in range(2):
        print("REPAIR SOURCE SCOPE " + str(repetition), flush=True)
        trial = OUT / "live/source-scope-repair" / str(repetition)
        row = dispatch(trial, request, Answer.model_json_schema(), "repair.source-scope", 2)
        if row["status"] == "RESPONSE":
            try:
                checked = inspect_answer(read(check_ref(row["response"])), corpus, "gatecoin")
            except ValueError as exc:
                checked = {"valid_structure_and_quotes": False, "failures": ["response-schema"], "error": str(exc)}
            save(trial / "check.json", checked)
            row = {**row, "check": ref(trial / "check.json"),
                   "status": "STRUCTURE_VALIDATED" if checked["valid_structure_and_quotes"] else "REJECTED"}
        rows.append(row)
    result = {"status": "DIAGNOSTIC_RECORDED", "comparator": selected["response"],
              "trials": rows, "source_evidence": ref(folder / "source-scope-evidence.json"),
              "interpretation": "Substantive review required; post-observation diagnostic, no statistical ranking"}
    save(folder / "source-scope-diagnostic.json", result)
    return result
