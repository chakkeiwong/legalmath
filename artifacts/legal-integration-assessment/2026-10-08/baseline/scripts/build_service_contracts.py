"""Generate the additional T00 record contracts deterministically, offline."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/v0.1"
STR = {"type": "string", "minLength": 1}
ID = {"type": "string", "pattern": "^[a-z][a-z0-9_.-]*$"}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
TIME = {"type": "string", "format": "date-time", "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$"}
TYPES = {"enum": ["bool", "integer", "money_hkd", "date"]}


def obj(props, optional=()):
    return {"type": "object", "properties": props, "required": [p for p in props if p not in optional], "additionalProperties": False}


def arr(item):
    return {"type": "array", "items": item}


def nullable(item):
    return {"anyOf": [item, {"type": "null"}]}


DIAG = obj({"code": STR, "pointer": {"type": "string"}, "message": STR})
contracts = {
    "boundary-error": obj({"error": {"const": "BOUNDARY_ERROR"}, "diagnostics": arr(DIAG)}),
    "fact-record": obj({"record_id": ID, "subject_id": ID, "fact_name": ID, "type": TYPES,
        "value": {"type": ["string", "boolean"]}, "evidence_ids": {**arr(ID), "minItems": 1},
        "valid_from": TIME, "valid_until": nullable(TIME), "recorded_at": TIME, "supersedes_record_ids": arr(ID)}),
    "stream-header": obj({"stream_id": ID, "profile": {"enum": ["consent", "achievement"]},
        "inception": TIME, "subject": ID, "category": ID, "actor": ID, "action": ID,
        "obligation_id": nullable(ID), "profile_version": {"const": "0.1"},
        "ordering_authority": nullable(ID), "initial_snapshot": nullable(obj({
            "as_of": TIME, "state": {"enum": ["ACTIVE", "WITHDRAWN", "NOT_ESTABLISHED"]},
            "generation": {"type": "integer", "minimum": 0}, "reviewer_id": ID,
            "evidence_id": ID, "recorded_at": TIME}))}),
    "completeness": obj({"complete_from": TIME, "complete_through": TIME,
        "recorded_at": TIME, "evidence_id": ID}),
    "event": obj({"id": ID, "stream_id": ID, "sequence": {"type": "integer", "minimum": 1},
        "kind": {"enum": ["consent.granted", "consent.withdrawn", "transaction.observed", "obligation.opened", "obligation.performed", "watermark"]},
        "occurred_at": TIME, "recorded_at": TIME, "actor": ID, "action": ID, "subject": ID,
        "category": ID, "evidence_id": ID, "obligation_id": nullable(ID),
        "activation": TIME, "deadline": nullable(TIME), "source_bundle_hash": HASH,
        "complete_from": TIME, "complete_through": TIME},
        optional=("activation", "deadline", "source_bundle_hash", "complete_from", "complete_through")),
    "java-build-manifest": obj({"record_type": {"const": "JavaBuildManifest"},
        "bundle_hash": HASH, "source_hashes": arr(HASH), "generated_sha256": HASH,
        "runtime_sha256": HASH, "jar_sha256": HASH, "java_target": {"const": 17},
        "compiler": STR, "command": arr(STR), "dependencies": arr(STR), "licenses": arr(STR),
        "decision_engine": STR, "event_engine": STR}),
    "verification-report": obj({"record_type": {"const": "VerificationReport"},
        "build_manifest_hash": HASH, "jar_sha256": HASH, "bundle_hash": HASH,
        "reference_engine": STR, "corpus_hash": HASH, "commands": arr(arr(STR)),
        "checks": arr(obj({"name": STR, "passed": {"type": "boolean"}, "evidence_hash": HASH})),
        "passed": {"type": "boolean"}}),
    "java-release-manifest": obj({"record_type": {"const": "JavaReleaseManifest"},
        "bundle_hash": HASH, "build_manifest_hash": HASH, "verification_report_hash": HASH,
        "profile": {"const": "RuleIR-0.1"}, "applicability_hash": HASH,
        "valid_from": TIME, "valid_until": nullable(TIME)}),
    "applicability": obj({"assessment_id": ID, "bundle_hash": HASH,
        **{x: STR for x in ("legal_entity", "regulated_role", "activity", "product_class", "client_class", "jurisdiction")},
        "valid_from": TIME, "valid_until": nullable(TIME),
        "conclusion": {"enum": ["in_scope", "out_of_scope", "unresolved"]},
        "reason": STR, "source_span_ids": arr(ID), "reviewer_id": ID}),
}


def main():
    for name, body in contracts.items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "$id": "https://legalmath.invalid/spec/0.1/" + name, **body}
        (SPEC / (name + ".schema.json")).write_text(json.dumps(schema, indent=2) + "\n")
    dest = ROOT / "src/legalmath/schemas"
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(SPEC.glob("*.schema.json")):
        (dest / path.name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
