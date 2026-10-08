"""Freeze the method before new evidence; preserve every qualified observation."""
from ..canonical import digest
from .catalog import PROFILE, inventory
from .engine import investigate, method_identity
from .evidence import fields, instant


def freeze(*, at, known_source_hashes):
    instant(at)
    if not isinstance(known_source_hashes, list) or any(not isinstance(x, str) or len(x) != 64 for x in known_source_hashes):
        raise ValueError("Explicit prior source identities required")
    result = {"at": at, "method_hash": method_identity(), "profile": PROFILE,
              "inventory_hash": digest(inventory(PROFILE)), "known_source_hashes": sorted(set(known_source_hashes)),
              "scoring": "Formal obligations, counterexamples and preserved qualifications; no human labels"}
    return {**result, "freeze_hash": digest(result)}


def observe(frozen, request, store):
    fields(frozen, {"at", "method_hash", "profile", "inventory_hash", "known_source_hashes", "scoring", "freeze_hash"})
    if frozen != freeze(at=frozen["at"], known_source_hashes=frozen["known_source_hashes"]):
        raise ValueError("Method, inventory or freeze changed; start a new prospective series")
    if request["profile"] != frozen["profile"] or instant(request["context"]["known_at"]) <= instant(frozen["at"]):
        raise ValueError("Observation must follow the frozen method")
    registry = store.json(request["registry_sha256"])
    new = {r["blob"] for r in registry.values()} - set(frozen["known_source_hashes"])
    if not new:
        raise ValueError("No previously unseen source content")
    result = investigate(request, store)
    return {"freeze_hash": frozen["freeze_hash"], "new_source_hashes": sorted(new), "investigation": result,
            "novelty": "NEW_TO_DECLARED_SOURCE_INVENTORY", "chronology": "DECLARED_TIMES_NOT_EXTERNALLY_ATTESTED",
            "prospective_legal_accuracy": "NOT_ESTABLISHED", "human_quality_evidence": False}


def observe_sources(frozen, request, store, *, chronology_sha256):
    """Distinguish newly supplied facts, old documents and later publications.

    Publication dates remain source assertions. Even consistent dates do not
    supply an external attestation or a score of legal correctness.
    """
    result = observe(frozen, request, store)
    rows = store.json(chronology_sha256)
    if not isinstance(rows, dict) or set(rows) - set(result["new_source_hashes"]):
        raise ValueError("Chronology must address only newly observed content")
    registry = store.json(request["registry_sha256"])
    entries = []
    for blob in result["new_source_hashes"]:
        kinds = {r["kind"] for r in registry.values() if r["blob"] == blob}
        if blob not in rows:
            entries.append({"blob": blob, "classification": "CHRONOLOGY_MISSING"})
            continue
        row = rows[blob]
        fields(row, {"published_at", "retrieved_at", "origin", "date_evidence_sha256"})
        if not row["origin"] or row["origin"] not in {r["origin"] for r in registry.values() if r["blob"] == blob}:
            raise ValueError("Chronology origin does not match the source registry")
        store.get(row["date_evidence_sha256"])
        retrieved = instant(row["retrieved_at"])
        if retrieved > instant(request["context"]["known_at"]) or retrieved <= instant(frozen["at"]):
            raise ValueError("New retrieval must lie after freeze and before knowledge cutoff")
        published = instant(row["published_at"]) if row["published_at"] else None
        if published and published > retrieved:
            raise ValueError("Publication cannot follow its retrieval")
        if not kinds <= {"law", "sanctions", "specification"}:
            classification = "NEW_FACT_OR_MIXED_KIND_NOT_NEW_LAW"
        elif published is None:
            classification = "PUBLICATION_DATE_UNKNOWN"
        elif published <= instant(frozen["at"]):
            classification = "PREEXISTING_DOCUMENT_NEW_TO_INVENTORY"
        else:
            classification = "POST_FREEZE_PUBLICATION_UNATTESTED"
        entries.append({"blob": blob, "classification": classification, "kinds": sorted(kinds), **row})
    return {**result, "chronology_sha256": chronology_sha256, "source_observations": entries,
            "future_legal_accuracy": "NOT_ESTABLISHED", "external_time_attestation": "NOT_SUPPLIED"}
