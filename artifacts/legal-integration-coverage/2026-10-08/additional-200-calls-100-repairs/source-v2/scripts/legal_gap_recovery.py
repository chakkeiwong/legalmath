"""Bounded recovery of the product's grant interface on retained stage inputs."""
import json
import re
from pathlib import Path
from scripts.legal_gap_program import (OUT, DOC, PREFIX, LIMITS, Allowance,
    read, save, ref, ledger, sha)
from legalmath.interpretation.assurance.grants import GrantedAllowance

APPROVED_AUTHORIZATION_SHA256 = "2bd211603685e68adb78fa0267c5a83af761bc7052d7540526642c1c142f8cd3"


class ProgramGrant(GrantedAllowance):
    """Explicit new-program grant sharing its already approved counted ledger.

    This authorization has no exhausted predecessor. It is independently
    recorded, not inferred from a retry or a model response.
    """
    def __init__(self, arm, authorization=None):
        self.counter = Allowance("product." + arm, 24)
        self.grant_path = Path(authorization) if authorization else DOC / "authorization.json"
        self.grant_bytes = self.grant_path.read_bytes()
        self.path = self.counter.path
        self.maximum = self.reservation_ceiling = LIMITS["provider_calls"]
        self.verify()

    def verify(self):
        if (self.grant_path.read_bytes() != self.grant_bytes
                or sha(self.grant_path) != APPROVED_AUTHORIZATION_SHA256):
            raise ValueError("Program authorization changed")
        grant = json.loads(self.grant_bytes)
        if (grant.get("limits") != LIMITS or grant.get("approved_prefix") != PREFIX
                or not grant.get("approval_evidence")):
            raise ValueError("Missing or changed recorded program grant")
        value = ledger()
        if value["maximum"] != self.maximum or len(value["calls"]) > self.maximum:
            raise ValueError("Invalid shared program allowance")
        for row in value["calls"]:
            if (set(row) != {"arm", "request_hash", "issued_at_ns"}
                    or not isinstance(row["arm"], str)
                    or not re.fullmatch("[0-9a-f]{64}", row["request_hash"])
                    or not isinstance(row["issued_at_ns"], str) or not row["issued_at_ns"].isdigit()):
                raise ValueError("Invalid retained program reservation")
        if sum(c["arm"] == self.counter.arm for c in value["calls"]) > self.counter.arm_maximum:
            raise ValueError("Product arm exceeded its unchanged cap")
        return {"grant_id": "legal-tool-gap-validation-2026-10-08", "maximum": self.maximum,
                "used": len(value["calls"]), "grant_hash": sha(self.grant_path),
                "arm": self.counter.arm, "arm_maximum": self.counter.arm_maximum,
                "authorization_kind": "explicit-independent-program-grant"}

    def reserve(self, request_hash):
        self.verify()
        if not isinstance(request_hash, str) or not re.fullmatch("[0-9a-f]{64}", request_hash):
            raise ValueError("Invalid provider reservation identity")
        return self.counter.reserve(request_hash)


def retained_inputs(arm):
    root = OUT / "live/products" / arm
    candidates = list(root.glob("revisions/*/core/actions/*/interpretation/candidates.json"))
    if len(candidates) != 1:
        raise ValueError("One retained product candidate inventory is required")
    location = candidates[0].parent
    assignments = []
    for path in root.glob("revisions/*/actions/*/result.json"):
        value = read(path)
        if value.get("status") == "VALIDATED" and "assignments" in value.get("value", {}):
            assignments.append((path, value["value"]))
    if len(assignments) != 1:
        raise ValueError("One validated product question assignment is required")
    question_path, assigned = assignments[0]
    inputs = {"packet": read(location / "packet.json"), "claims": read(location / "claims.json"),
              "candidates": read(candidates[0]),
              "questions": {r["candidate_id"]: r["question"] for r in assigned["assignments"]}}
    inputs["references"] = [ref(location / name) for name in ("packet.json", "claims.json", "candidates.json")] + [ref(question_path)]
    return inputs


def select_pairs(inputs):
    candidates, questions = inputs["candidates"], inputs["questions"]
    ids = sorted(cid for cid, q in questions.items() if q["result_kind"] == "DUTY_TRIGGER"
        and candidates[cid].get("formalization")
        and candidates[cid]["formalization"]["result"] not in ("true", "false"))
    if not ids:
        raise ValueError("No retained request-trigger candidate")
    responsibilities = [c for c in inputs["claims"] if "ultimately responsible" in c["statement"].lower()
                        and "operational soundness" in c["statement"].lower()]
    demonstrations = [c for c in inputs["claims"] if "demonstrate" in c["action"].lower()
                      and "request" in " ".join(c["conditions"]).lower()
                      and c["kind"] == "OBLIGATION"]
    if not responsibilities or not demonstrations:
        raise ValueError("Required responsibility and requested-demonstration claims not identified")
    selected = [sorted(group, key=lambda c: c["claim_id"])[0] for group in (responsibilities, demonstrations)]
    if selected[0]["claim_id"] == selected[1]["claim_id"]:
        raise ValueError("Diagnostic requires distinct source duties")
    return [(c["claim_id"], ids[0]) for c in selected]


def run(folder):
    from scripts.legal_gap_live import Provider, ProductProvider
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
    from legalmath.interpretation.search.models import Settings
    results = {}
    for arm in ("baseline", "combined"):
        target = folder / arm
        target.mkdir(parents=True, exist_ok=True)
        try:
            inputs = retained_inputs("baseline")
            pairs = select_pairs(inputs)
            save(target / "selected-inputs.json", {**inputs, "selected_pairs": pairs,
                "input_arm": "baseline", "diagnostic_arm": arm,
                "primary_combined_generation": "No candidates after timeout; unchanged primary failure retained",
                "full_pair_denominator": len(inputs["claims"]) * len(inputs["candidates"]),
                "selection": "First stable-ID request-trigger candidate; responsibility and requested-demonstration claims"})
        except ValueError as exc:
            results[arm] = {"status": "UNTESTED_MISSING_RETAINED_PREREQUISITE", "reason": str(exc)}
            continue
        stages = OUT / "live/scoped-grant-repair" / arm
        if (stages / "result.json").exists():
            results[arm] = read(stages / "result.json")
            continue
        stages.mkdir(parents=True, exist_ok=True)
        grant = ProgramGrant(arm)
        before = len(ledger()["calls"])
        provider = ProductProvider(Provider(allowance=grant), stages / "tool-stages", arm == "combined")
        print("SCOPED GRANT REPAIR " + arm, flush=True)
        try:
            result = investigate(inputs["packet"], inputs["claims"], inputs["candidates"],
                inputs["questions"], provider, stages / "scoped", required_pairs=pairs,
                batch_size=2, maximum_rounds=1, maximum_actions=2, deadline_seconds=600,
                settings=Settings(timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000),
                schedule="round-first", reference_protocol=PROTOCOL, input_profile="readable-tables.v1")
            save(stages / "scoped-result.json", result)
            row = {"status": "SCOPED_STAGE_VALIDATED" if not result["stopped"] and
                   result["pairs_with_two_validated_proposals"] == len(pairs) else "SCOPED_STAGE_INCOMPLETE",
                   "result": ref(stages / "scoped-result.json"), "selected_pairs": pairs,
                   "full_product_completion": False, "internal_reported_live_calls": result["live_calls"]}
        except Exception as exc:
            save(stages / "failure.json", {"type": type(exc).__name__, "error": str(exc),
                                           "details": str(getattr(exc, "details", ""))[:5000]})
            row = {"status": "FAILED", "failure": ref(stages / "failure.json"), "full_product_completion": False}
        row["provider_reservations"] = len(ledger()["calls"]) - before
        row["call_accounting"] = "Actual shared-ledger change; internal request-hash matching may omit tool-augmented requests"
        save(stages / "result.json", row)
        results[arm] = row
    save(folder / "result.json", results)
    return {"status": "BOUNDED_SCOPED_GRANT_REPAIR_RECORDED", "results": ref(folder / "result.json")}
