"""Execute an investigation's retrieved facts through either compiled target."""
from datetime import timezone
from pathlib import Path

from ..canonical import digest
from ..translation import pipeline
from .catalog import models
from .engine import conditional, revalidate, SUPPORTED_CMIC_ACTIONS
from .evidence import instant


def utc(value):
    return instant(value).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def execute(receipt, request, store, builds, target, jdk):
    if target not in {"ruleir", "catala"}:
        raise ValueError("Explicit native target required")
    revalidate(receipt, request, store)
    at, known = utc(request["context"]["effective_at"]), utc(request["context"]["known_at"])
    rows = {}
    for name, model in models().items():
        if name == "cmic" and (request["context"]["action"] not in SUPPORTED_CMIC_ACTIONS or request["capacity"] == "unresolved"):
            rows[name] = {"status": "UNSUPPORTED_ACTION_OR_CAPACITY"}
            continue
        path = Path(builds) / name / target
        built, _, manifest = pipeline.verify_build(path)
        if built != model or manifest["target"] != target:
            raise ValueError("Native build does not implement the current declared specification")
        snapshot = {"subject_id": request["context"]["instrument_id"], "facts": {}, "evidence": {}}
        complete = True
        for fact in model["facts"]:
            key, typ = fact["name"], fact["type"]
            observed = receipt["observations"][key]
            ids = observed["sources"] or ["derived:" + receipt["receipt_hash"] + ":" + key]
            if observed["status"] == "KNOWN":
                value = observed["value"] if typ == "bool" else str(observed["value"])
                snapshot["facts"][key] = {"type": typ, "status": "known", "value": value, "evidence_ids": ids,
                    "complete": True, "valid_from": at, "valid_until": None, "recorded_at": known}
                snapshot["evidence"]["/" + key] = ids
            else:
                complete = False
                snapshot["facts"][key] = ({"type": typ, "status": "conflict", "evidence_ids": ids}
                    if observed["status"] == "CONFLICT" else {"type": typ, "status": "unknown", "reason": "MISSING"})
        result = pipeline.execute_all(path, snapshot, at, known, jdk, expected_hash=digest(manifest))
        reference = conditional(model, receipt["observations"])
        if complete:
            for rule, calculated in result["results"].items():
                if (calculated["status"] not in {"TRUE", "FALSE", "VALUE"}
                        or calculated["value"] != reference[rule]["value"]):
                    raise ValueError("Native value disagrees with independent formal consequence")
        elif result["status"] != "ABSTAIN":
            raise ValueError("Complete-input native profile failed to abstain")
        rows[name] = result
    result = {"target": target, "investigation_receipt": receipt["receipt_hash"], "models": rows,
              "input_policy": "Complete factual inputs; unknown/conflicting facts cause abstention",
              "may_execute_transaction": False, "legal_correctness": "NOT_ESTABLISHED"}
    return {**result, "execution_hash": digest(result)}
