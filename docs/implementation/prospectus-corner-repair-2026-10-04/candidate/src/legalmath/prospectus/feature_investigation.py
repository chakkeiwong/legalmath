"""Connect verified feature findings to the actual bank investigator."""
from copy import deepcopy
from pathlib import Path

from .common import digest
from . import eligibility, source_obligations, instrument_sources, instrument_investigation
from .loss_absorption_reader import load_document, joined
from ..transaction.intake import record


def investigate(row, issue, documents, root, bank_request, store, *, product_assertions_sha256=None,
                issuer_basis_source_ids=(), instrument_request=None):
    current = source_obligations.replay(row, issue, documents, root)
    bank = deepcopy(bank_request)
    if bank["context"]["instrument_id"] != issue["id"]:
        raise ValueError("Bank request identifies a different instrument")
    registry = store.json(bank["registry_sha256"])
    ids = []
    for selected in issue["documents"]:
        key = selected["id"]
        meta = documents[key]
        doc = load_document(meta, root)
        raw = key + ".feature-original"
        # Retrieval time and force intervals are unknown unless separately evidenced.
        at = meta.get("retrieved_at")
        if meta.get("acquisition_receipt"):
            from .master_control import read, sha
            receipt_path = (Path(root) / meta["acquisition_receipt"]).resolve()
            if not receipt_path.is_relative_to(Path(root).resolve()):
                raise ValueError("Acquisition receipt escapes checkout")
            receipt = read(receipt_path)
            original = receipt.get("original", receipt.get("body"))
            if (receipt.get("sha256") != meta["sha256"] or original != meta["original"] or
                    sha(Path(root) / original) != meta["sha256"]):
                raise ValueError("Acquisition receipt belongs to different source bytes")
            observed = receipt.get("retrieved_at") or receipt.get("finished_at") or receipt.get("at")
            if at is not None and observed is not None and at != observed:
                raise ValueError("Conflicting observation times")
            at = observed if observed is not None else at
        registry[raw] = record(store.put((Path(root)/meta["original"]).read_bytes()),
            "law", meta["url"], at, media_type="application/octet-stream",
            provenance="supplied")
        registry[key] = record(store.put(joined(doc)[0].encode()), "law", meta["url"], at,
            dependencies=[raw], provenance="supplied")
        ids.append(key)
    bank["registry_sha256"] = store.put(registry)
    request = {"profile": eligibility.PROFILE, "bank_request": bank,
        "product_assertions_sha256": product_assertions_sha256 or store.put({}),
        "issuer_basis_source_ids": list(issuer_basis_source_ids),
        "prospectus_source_ids": ids, "contract_event_source_id": None}
    joined_receipt = eligibility.investigate(request, store)
    eligibility.revalidate(joined_receipt, request, store)
    mechanism = None
    if instrument_request is not None:
        from . import closure_mechanisms
        if instrument_request.get("profile") == closure_mechanisms.PROFILE:
            if set(instrument_request) != {"profile", "scenario"}:
                raise ValueError("Unexpected numerical adapter request")
            mechanism = closure_mechanisms.investigate(issue, documents, root, request, instrument_request["scenario"])
        else:
            if ids != [instrument_sources.KEY] or instrument_sources.ISIN not in issue["identifiers"]:
                raise ValueError("UBS mechanism profile cannot be transferred to another bond")
            specific = deepcopy(instrument_request)
            specific["joined_request"] = deepcopy(request)
            specific["joined_request"]["bank_request"]["context"]["instrument_id"] = instrument_sources.KEY
            mechanism = instrument_investigation.investigate(specific, store, root)
    packet = source_obligations.build(current, issue, documents, root, as_of=bank["context"]["effective_at"])
    result = {"profile": "feature-to-bank.v1", "issue_id": issue["id"],
        "feature": {"answer": current["answer"], "facts": current["facts"],
                    "derivation_sha256": current["derivation"]["sha256"], "report_sha256": digest(current)},
        "source_obligations": packet, "joined_request": request, "bank_investigation": joined_receipt,
        "instrument_investigation": mechanism,
        "required_product_evidence": [k for k, v in joined_receipt["observations"].items() if v["status"] != "KNOWN"],
        "feature_to_regulatory_scope": "NO_AUTOMATIC_IMPLICATION",
        "may_execute_transaction": False, "actual_event_or_settlement": "NOT_ESTABLISHED"}
    if len(joined_receipt["inventory"]) != 14 or joined_receipt["may_execute_transaction"]:
        raise ValueError("Bank obligations lost or unauthorized clearance")
    return {**result, "receipt_hash": digest(result)}
