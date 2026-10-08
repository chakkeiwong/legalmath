"""Independent result-shape, provenance and identity checks (no evaluation)."""
from ..canonical import digest
from ..domain import scalar
from ..domain import eligible
from ..errors import LegalMathError
from .graph import children, walk
from .load import schema_errors


def verify_result(bundle, snapshot, rule_id, result):
    if schema_errors("evaluation", result):
        raise LegalMathError("E_SCHEMA")
    if result["bundle_hash"] != digest(bundle) or result["snapshot_hash"] != digest(snapshot):
        raise LegalMathError("E_HASH_MISMATCH")
    request = {"bundle_hash": digest(bundle), "snapshot_hash": digest(snapshot), "rule_id": rule_id,
        "mode": result["mode"], "valid_at": result["valid_at"], "known_at": result["known_at"], "engine_version": result["engine_version"]}
    semantic = {k: result[k] for k in ("status", "type", "mode", "diagnostics", "reason_codes", "missing_inputs", "blocking_inputs", "trace")}
    if "value" in result:
        semantic["value"] = result["value"]
        if not scalar(result["type"], result["value"]):
            raise LegalMathError("E_TYPE")
    if digest({"request": request, "result": semantic}) != result["result_hash"]:
        raise LegalMathError("E_HASH_MISMATCH")
    for key in ("reason_codes", "missing_inputs", "blocking_inputs"):
        if result[key] != sorted(set(result[key])):
            raise LegalMathError("E_INTEGRITY")
    if result["status"] in ("TRUE", "FALSE", "VALUE", "OUT_OF_SCOPE") and result["blocking_inputs"]:
        raise LegalMathError("E_INTEGRITY")
    if schema_errors("rule-bundle", bundle) or schema_errors("fact-snapshot", snapshot):
        if result["status"] != "ERROR" or result["trace"] or result["reason_codes"] != ["E_SCHEMA"]:
            raise LegalMathError("E_INTEGRITY")
        return True
    rules = {r["id"]: r for r in bundle["rules"]}
    nodes, sources = {}, {}
    for r in bundle["rules"]:
        for field in ("scope", "body"):
            for n, _ in walk(r[field], ""):
                nodes[n["node_id"]] = n
                sources[n["node_id"]] = sorted(set(r["source_span_ids"]))
    visited, missing = {}, set()
    if not result["trace"] and result["status"] not in ("ERROR", "CONFLICT"):
        raise LegalMathError("E_INTEGRITY")
    for t in result["trace"]:
        ident = t["node_id"]
        if ident in visited or ident not in nodes:
            raise LegalMathError("E_INTEGRITY")
        n = nodes[ident]
        if t["op"] != n["op"] or t["source_span_ids"] != sources[ident] or any(c not in visited for c in t["children"]):
            raise LegalMathError("E_INTEGRITY")
        expected = [c["node_id"] for _, c in children(n)]
        if n["op"] == "rule":
            expected = [rules[n["name"]][f]["node_id"] for f in ("scope", "body")]
        if t["children"] != ([] if t["status"] == "SKIPPED" else expected):
            raise LegalMathError("E_INTEGRITY")
        if t["evidence_ids"] != sorted(set(t["evidence_ids"])):
            raise LegalMathError("E_INTEGRITY")
        if t["status"] in ("TRUE", "FALSE", "VALUE"):
            if "value" not in t or not scalar(t["type"], t["value"]):
                raise LegalMathError("E_TYPE")
            if t["status"] in ("TRUE", "FALSE") and (t["type"] != "bool" or t["value"] is not (t["status"] == "TRUE")):
                raise LegalMathError("E_INTEGRITY")
        elif "value" in t:
            raise LegalMathError("E_INTEGRITY")
        if n["op"] == "fact" and t["status"] == "UNKNOWN":
            missing.add(n["name"])
        if t["status"] != "SKIPPED":
            if n["op"] == "fact":
                fact = snapshot["facts"][n["name"]]
                admissible = fact["status"] == "known" and eligible(fact["valid_from"], fact["valid_until"], result["valid_at"]) and fact["recorded_at"] <= result["known_at"]
                evidence = set(fact["evidence_ids"]) if admissible else set()
                if admissible and (t.get("value") != fact["value"] or t["type"] != fact["type"] or t["status"] not in ("TRUE", "FALSE", "VALUE")):
                    raise LegalMathError("E_INTEGRITY")
                if not admissible and t["status"] != "UNKNOWN":
                    raise LegalMathError("E_INTEGRITY")
            else:
                evidence = {e for child in t["children"] for e in visited[child]["evidence_ids"]}
            if t["evidence_ids"] != sorted(evidence):
                raise LegalMathError("E_INTEGRITY")
        if n["op"] == "if" and t["status"] != "SKIPPED":
            guard = visited[n["condition"]["node_id"]]["status"]
            for field, selected in (("then", guard == "TRUE"), ("else", guard == "FALSE")):
                if (visited[n[field]["node_id"]]["status"] != "SKIPPED") != selected:
                    raise LegalMathError("E_INTEGRITY")
        visited[ident] = t
    if result["trace"] and missing != set(result["missing_inputs"]):
        raise LegalMathError("E_INTEGRITY")
    if result["trace"]:
        root = rules[rule_id]
        scope = visited.get(root["scope"]["node_id"])
        body = visited.get(root["body"]["node_id"])
        if not scope or not body:
            raise LegalMathError("E_INTEGRITY")
        expected = body["status"] if scope["status"] == "TRUE" else "OUT_OF_SCOPE" if scope["status"] == "FALSE" else "UNKNOWN" if scope["status"] == "UNKNOWN" else scope["status"]
        if result["status"] != expected or (scope["status"] == "TRUE" and result.get("value") != body.get("value")):
            raise LegalMathError("E_INTEGRITY")
    return True
