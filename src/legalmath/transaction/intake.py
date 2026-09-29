"""Retain public sources and create an explicitly incomplete investigation."""
from datetime import datetime, timezone
import json
from pathlib import Path

from ..canonical import canonical
from .catalog import PROFILE
from .evidence import Store, sha


def record(blob, kind, origin, recorded_at, *, media_type="text/plain", dependencies=(),
           provenance="official_retrieval", effective_from=None, effective_until=None, fresh_until=None):
    return {"blob": blob, "kind": kind, "origin": origin, "media_type": media_type,
            "recorded_at": recorded_at, "effective_from": effective_from,
            "effective_until": effective_until, "fresh_until": fresh_until,
            "dependencies": list(dependencies), "supersedes": [], "provenance": provenance}


def bootstrap(root, directory, *, at):
    root, directory = Path(root), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / "store")
    registry = {}
    archive = json.loads((root / "docs/compliance/sources/manifest.json").read_text())
    for row in archive["sources"]:
        if row["status"] != "RETAINED":
            continue
        key = row["key"]
        for path_key, digest_key, suffix, media in (("path", "sha256", ".original", "application/octet-stream"),
                                                    ("text_path", "text_sha256", "", "text/plain")):
            data = (root / row[path_key]).read_bytes()
            if sha(data) != row[digest_key]:
                raise ValueError("Retained source identity changed: " + key)
            registry[key + suffix] = record(store.put(data), "law", row["url"], row["retrieved_at"],
                media_type=media, dependencies=() if suffix else (key + ".original",))
    prospectus = json.loads((root / "docs/prospectus/manifest.json").read_text())["documents"]
    for key in ("sfc-spi-annex-1", "sfc-complex-products", "ubs-sgd-at1-2024-final-published",
                "jpm-series-pp-2026", "bofa-series-ss-2022-issuer"):
        row = prospectus[key]
        original = (root / "docs/prospectus" / row["file"]).read_bytes()
        if sha(original) != row["sha256"]:
            raise ValueError("Prospectus identity changed")
        registry[key + ".original"] = record(store.put(original), "law", row["url"], row["retrieved_at"],
                                              media_type="application/pdf")
        extracted = json.loads((root / "docs/prospectus/text" / (key + ".json")).read_text())
        if extracted["source_sha256"] != row["sha256"]:
            raise ValueError("Text references a different original")
        text = "\n\n".join(p["text"] for p in extracted["pages"]).encode()
        registry[key] = record(store.put(text), "law", row["url"], row["retrieved_at"],
                               dependencies=(key + ".original",))
    feed_manifest = json.loads((root / "docs/compliance/feeds/manifest.json").read_text())
    for row in feed_manifest["sources"]:
        data = (root / row["path"]).read_bytes()
        if sha(data) != row["sha256"]:
            raise ValueError("OFAC snapshot identity changed")
        registry[row["id"]] = record(store.put(data), "sanctions", row["url"], row["retrieved_at"],
                                     media_type="application/xml")
    request = {"profile": PROFILE, "capacity": "unresolved", "registry_sha256": store.put(registry),
        "context": {"instrument_id": "ubs-sgd-at1-2024-final-published", "instrument_kind": "at1_bond",
            "client_id": "not-supplied", "booking_entity_id": "not-established", "establishment_id": "hk-not-established",
            "service": "purchase-investigation", "action": "buy", "effective_at": at, "known_at": at,
            "facts_sha256": store.put({}), "route_sha256": store.put({"roles": [], "capacity": "unresolved", "currencies": []}),
            "policy_sha256": store.put({"source_ids": [], "mandate_source_ids": []})}}
    (directory / "request.json").write_bytes(canonical(request))
    return request, store


def hypothetical(request, store):
    """Explicit generated factual premises for integration checks, never a client."""
    from copy import deepcopy
    from datetime import timedelta
    from .catalog import declarations
    from .engine import DERIVED
    from .evidence import instant
    result = deepcopy(request)
    at = result["context"]["known_at"]
    values = {k: True if t == "bool" else 100000000 for k, t in declarations().items() if k not in DERIVED}
    values.update(portfolio=4000000000, net_assets=8000000000)
    registry = store.json(request["registry_sha256"])
    registry["hypothetical-account"] = record(store.put(values), "facts", "synthetic:complete-formal-premises", at,
        media_type="application/json", provenance="synthetic", effective_from=at,
        fresh_until=(instant(at) + timedelta(days=1)).isoformat())
    result.update(registry_sha256=store.put(registry), capacity="principal")
    result["context"].update(client_id="synthetic-client", instrument_id="synthetic-instrument",
        instrument_kind="synthetic-security", booking_entity_id="synthetic-bank", establishment_id="synthetic-hk",
        facts_sha256=store.put({k: [{"source": "hypothetical-account", "pointer": "/" + k}] for k in values}),
        route_sha256=store.put({"roles": [], "capacity": "principal", "currencies": ["USD"]}))
    return result
