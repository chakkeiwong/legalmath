"""Verify records issued by a separately trusted review administrator.

The key authenticates that administrator's records, not a person's legal skill.
Real accounts, reader qualification and honest attestations remain prerequisites.
"""
import hashlib
import hmac
import json
from .anchors import bind
from .contracts import digest, timestamp
from .annotation_bridge import bound_evidence


def payload_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def verified(envelope, key):
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Independent administrator verification key required")
    if set(envelope) != {"payload", "signature"}:
        raise ValueError("Signed review envelope required")
    expected = hmac.new(key, payload_bytes(envelope["payload"]), hashlib.sha256).hexdigest()
    if not isinstance(envelope["signature"], str) or not hmac.compare_digest(expected, envelope["signature"]):
        raise ValueError("Review administrator signature invalid")
    return envelope["payload"]


def admit(packet, key, cohort, identities, labels, graphs):
    registry = verified(packet["registry"], key)
    if registry.get("version") != "independent-review-registry.v1" or registry.get("cohort_sha256") != digest(cohort):
        raise ValueError("Review registry cohort mismatch")
    if registry.get("identities") != identities or registry.get("qualification_attested") is not True:
        raise ValueError("Administrator identity/qualification attestation missing")
    exposure = set(registry["development_families"])
    family_map = registry["case_families"]
    for case in cohort:
        families = family_map.get(case["id"])
        if not families or exposure.intersection(families):
            raise ValueError("Missing family assignment or exposed development family")
    readings = {}
    expected = {(r["id"], r["question"]) for r in labels}
    for envelope in packet["first_readings"]:
        row = verified(envelope, key)
        identity = (row["case"], row["question"], row["reader"])
        if (identity in readings or identity[:2] not in expected or row["reader"] not in identities["readers"] or
                row.get("cohort_sha256") != digest(cohort) or row.get("blinded") is not True or
                row.get("authenticated_account") != row["reader"] or
                row.get("value") not in {"YES", "NO", "UNKNOWN", "CONFLICT"}):
            raise ValueError("Unassigned, duplicate or unblinded first reading")
        if timestamp(row["submitted_at"]) >= timestamp(registry["predictions_released_at"]):
            raise ValueError("First reading was not sealed before prediction exposure")
        if digest(row["export"]) != row["export_sha256"]:
            raise ValueError("Authored reading export changed")
        if row["evidence"] != bound_evidence(graphs[row["case"]], row["export"]):
            raise ValueError("First reading evidence differs from authored export")
        readings[identity] = row
    decisions = {}
    for envelope in packet["adjudications"]:
        row = verified(envelope, key)
        identity = (row["case"], row["question"])
        if (identity in decisions or row["adjudicator"] != identities["adjudicator"] or not row.get("reason") or
                row.get("authenticated_account") != row["adjudicator"] or row.get("cohort_sha256") != digest(cohort)):
            raise ValueError("Distinct assigned adjudication required")
        required = [readings.get((*identity, reader)) for reader in identities["readers"]]
        if any(r is None for r in required) or row["reading_sha256s"] != [digest(r) for r in required]:
            raise ValueError("Adjudication does not bind each first reading")
        if any(timestamp(r["submitted_at"]) > timestamp(row["adjudicated_at"]) for r in required):
            raise ValueError("Adjudication predates first readings")
        if timestamp(row["adjudicated_at"]) >= timestamp(registry["predictions_released_at"]):
            raise ValueError("Adjudication was not sealed before prediction exposure")
        for evidence in row["evidence"]:
            bind(graphs[row["case"]], evidence)
        decisions[identity] = row
    if set(decisions) != expected or set(readings) != {(*k, r) for k in expected for r in identities["readers"]}:
        raise ValueError("Review records differ from frozen evaluation denominator")
    for label in labels:
        row = decisions[(label["id"], label["question"])]
        if row["value"] != label["value"] or row["evidence"] != label["evidence"]:
            raise ValueError("Evaluation label differs from preserved adjudication")
    return {"status": "AUTHENTICATED_ASSIGNMENTS_AND_READINGS", "packet_sha256": digest(packet),
            "trust_boundary": "Supplied independent administrator key and attested real account/qualification mapping"}
