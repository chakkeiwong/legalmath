"""Read-only, exact-data capacity diagnostic for the terminal Sol inventory.

No provider, allowance, product policy, or historical result is changed. The
diagnostic writes one new result below the live pilot's capacity-audit directory.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from legalmath.canonical import canonical, digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import readable_tables, source_references
from legalmath.interpretation.assurance.decomposition import (
    CrossPieceCheck,
    compact_request,
    cross_request,
    merge_pieces,
)
from legalmath.interpretation.assurance.semantics import (
    Inventory,
    merge_inventories,
    validate_inventory,
)
from legalmath.interpretation.assurance.source_context import augment


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "artifacts/legal-mission-control/2026-10-10/live-pilot-400"
RUN = PILOT / "sol-inventory-window"
OUTPUT = PILOT / "capacity-audit/diagnostic.json"


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def partial_merge(values):
    """Build exact `merge_pieces` rows without accepting an over-cap Inventory."""
    out = {"claims": [], "units": [], "authorities": [], "uncertainties": []}
    for index, value in enumerate(values):
        ids = {c["claim_id"]: f"c{index}." + digest(c["claim_id"])[:24]
               for c in value["claims"]}
        out["claims"].extend({**c, "claim_id": ids[c["claim_id"]]}
                             for c in value["claims"])
        out["units"].extend({**u, "claim_ids": [ids[c] for c in u["claim_ids"]]}
                            for u in value["units"])
        out["authorities"].extend({**a, "dependency_id": f"d{index}." + digest(a["dependency_id"])[:24]}
                                  for a in value["authorities"])
        out["uncertainties"].extend(value["uncertainties"])
    return out


def quote_coordinates(value, full_packet):
    source = [u["text"] for u in full_packet["units"]]
    ids = {u["unit_id"]: index for index, u in enumerate(full_packet["units"])}
    count = 0

    def encode(item):
        nonlocal count
        if isinstance(item, dict):
            if set(item) == {"unit_id", "quote"}:
                index = ids[item["unit_id"]]
                quote = item["quote"]
                assert source[index].count(quote) == 1
                start = source[index].index(quote)
                count += 1
                return {"$quote": [index, start, start + len(quote)]}
            return {key: encode(child) for key, child in item.items()}
        if isinstance(item, list):
            return [encode(child) for child in item]
        return item

    def decode(item):
        if isinstance(item, dict):
            if set(item) == {"$quote"}:
                index, start, end = item["$quote"]
                assert 0 <= index < len(source) and 0 <= start < end <= len(source[index])
                quote = source[index][start:end]
                assert source[index].count(quote) == 1
                return {"unit_id": full_packet["units"][index]["unit_id"], "quote": quote}
            return {key: decode(child) for key, child in item.items()}
        if isinstance(item, list):
            return [decode(child) for child in item]
        return item

    compact = encode(value)
    assert canonical(decode(compact)) == canonical(value)
    return compact, count


def wire_sizes(packet, inventory, context):
    request = cross_request(packet, "atomic-reader", inventory)
    qualified = augment(request, context)
    compact = compact_request(qualified, profile="v2")
    wire, schema, _ = source_references.prepare(
        compact, CrossPieceCheck.model_json_schema())
    readable = readable_tables.encode(wire)
    return {
        "unqualified_request": len(canonical(request)),
        "qualified_request": len(canonical(qualified)),
        "compact_request": len(canonical(compact)),
        "source_span_wire": len(canonical(wire)),
        "readable_wire": len(canonical(readable)),
        "schema": len(canonical(schema)),
    }


def main():
    outer = read(RUN / "result.json")
    baseline = read(RUN / "baseline/result.json")
    assert outer["status"] == "PAIR_UNAVAILABLE" and baseline["error"] == "E_REFERENCE"
    directory = Path(baseline["details"]["interpretation_directory"]).resolve()
    assert directory.is_relative_to(RUN.resolve())
    plan = read(directory / "inventory-pieces/round-000/plan.json")
    packet = read(directory / "packet.json")
    context = read(RUN / "qualified-source-context.json")
    assert digest(packet) == plan["packet_hash"] and len(packet["units"]) == 55
    pieces, values, statuses = [], [], []
    for index in range(4):
        call = directory / "calls" / f"call-{index:03}"
        status = read(call / "status.json")
        piece = read(call / "request.json")["source_packet"]
        value = (read(directory / "inventory-pieces/round-000/atomic-reader" /
                      f"piece-{index:03}.json")["inventory"] if index < 3 else
                 read(directory.parent / "transport/call-003/source-references/resolved-response.json"))
        assert digest(piece) == plan["pieces"][index]["packet_hash"]
        validate_inventory(value, piece)
        pieces.append(piece)
        values.append(value)
        statuses.append({"index": index, "status": status["status"],
                         "error": status.get("error"),
                         "counts": {name: len(value[name]) for name in value}})
    assert all(row["status"] == "RETURNED_UNVALIDATED" for row in statuses[:3])
    assert statuses[3]["status"] == "FAILED" and statuses[3]["error"] == "E_RESOURCE_LIMIT"
    reference_validation = read(directory.parent / "transport/call-003/source-references/validation.json")
    assert reference_validation["status"] == "REFERENCE_INTEGRITY_CHECKED"
    settings = read(RUN / "effective-settings/0013.json")["effective_settings"]
    raw = read(directory.parent / "transport/call-003/source-references/raw-response.json")["value"]
    resolved = values[3]

    merged = partial_merge(values)
    partial_packet = {**pieces[0], "units": [unit for piece in pieces for unit in piece["units"]]}
    try:
        merge_pieces(partial_packet, list(zip(pieces, values)))
        aggregate_failure = None
    except LegalMathError as exc:
        aggregate_failure = {"error": exc.code, "details": exc.details}

    compact, quote_count = quote_coordinates(merged, packet)
    claims = merge_inventories({"atomic-reader": merged})
    report = {
        "status": "CURRENT_ROUTE_BLOCKED",
        "source_packet_hash": digest(packet),
        "full_source_units": len(packet["units"]),
        "retained_piece_statuses": statuses,
        "partial_unit_accounts": len(merged["units"]),
        "merged_counts": {name: len(merged[name]) for name in merged},
        "inventory_schema_limits": {
            "claims": Inventory.model_json_schema()["properties"]["claims"]["maxItems"],
            "uncertainties": Inventory.model_json_schema()["properties"]["uncertainties"]["maxItems"],
        },
        "merge_failure": aggregate_failure,
        "fourth_response": {
            "wire_canonical_bytes": len(canonical(raw)),
            "resolved_canonical_bytes": len(canonical(resolved)),
            "journal_output_cap": settings["max_output_bytes"],
            "source_reference_status": reference_validation["status"],
            "offline_inventory_valid": True,
        },
        "cross_check_current_sizes": wire_sizes(packet, merged, context),
        "coordinate_candidate": {
            "exact_roundtrip": True,
            "quote_occurrences": quote_count,
            "expanded_inventory_bytes": len(canonical(merged)),
            "coordinate_inventory_bytes": len(canonical(compact)),
            "cross_check_sizes": wire_sizes(packet, compact, context),
            "candidate_status": "OFFLINE_HYPOTHESIS_NOT_ADMITTED",
        },
        "cross_check_input_cap": settings["max_input_bytes"],
        "atomic_claims_only": {"count": len(claims), "canonical_bytes": len(canonical(claims))},
        "limits": [
            "Four-piece evidence omits the fifth source piece and independent reader.",
            "Reference integrity and schema validity do not establish source entailment.",
            "Coordinate compression is reversible here but does not fit the complete target or qualify later consumers.",
            "No provider, tool, model, source acquisition or legal answer was run.",
        ],
        "method_sha256": {name: sha(ROOT / name) for name in (
            "src/legalmath/interpretation/assurance/decomposition.py",
            "src/legalmath/interpretation/assurance/semantics.py",
            "src/legalmath/interpretation/assurance/source_references.py",
            "src/legalmath/interpretation/assurance/readable_tables.py",
            "src/legalmath/interpretation/assurance/transport.py",
        )},
        "input_sha256": {name: sha(RUN / name) for name in (
            "baseline/result.json", "result.json", "qualified-source-context.json")},
    }
    assert aggregate_failure and aggregate_failure["error"] == "E_SCHEMA"
    assert report["fourth_response"]["resolved_canonical_bytes"] > settings["max_output_bytes"]
    assert report["cross_check_current_sizes"]["readable_wire"] > settings["max_input_bytes"]
    assert report["coordinate_candidate"]["cross_check_sizes"]["readable_wire"] > settings["max_input_bytes"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != data:
        raise LegalMathError("E_INTEGRITY", details="Capacity diagnostic already exists with different bytes")
    OUTPUT.write_text(data)
    print(json.dumps({"status": report["status"],
                      "source_units": report["full_source_units"],
                      "partial_units": report["partial_unit_accounts"],
                      "merged_uncertainties": report["merged_counts"]["uncertainties"],
                      "fourth_resolved_bytes": report["fourth_response"]["resolved_canonical_bytes"],
                      "current_cross_wire_bytes": report["cross_check_current_sizes"]["readable_wire"],
                      "coordinate_cross_wire_bytes": report["coordinate_candidate"]["cross_check_sizes"]["readable_wire"],
                      "output": str(OUTPUT.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
