from pathlib import Path
from ..canonical import loads, raw_digest
from ..errors import LegalMathError
from .intake import import_source
from .dependencies import record_dependency


def import_manifest(db, manifest_path):
    path = Path(manifest_path).resolve()
    manifest = loads(path.read_bytes())
    repository = path.parent.parent.parent
    result = []
    with db.transaction() as con:
        for item in manifest["sources"]:
            raw = (repository / item["raw_path"]).read_bytes()
            if raw_digest(raw) != item["raw_sha256"]:
                raise LegalMathError("E_HASH_MISMATCH")
            text = (repository / item["text_path"]).read_text() if item.get("text_path") else None
            if text is not None and raw_digest(text.encode()) != item["text_sha256"]:
                raise LegalMathError("E_HASH_MISMATCH")
            result.append(import_source(db, con, item["source_id"], raw, item["media_type"], item["official_url"], manifest["retrieved_at"],
                retained_text=text, extractor=item.get("extractor"), source_kind=item["source_kind"], authority="RETAINED_PUBLIC_SOURCE"))
        by_source = {item["source_id"]: response["revision_id"] for item, response in zip(manifest["sources"], result)}
        for dependency in manifest["dependencies"]:
            record_dependency(db, con, {"from_revision_id": by_source[dependency["from"]], "target_revision_id": by_source.get(dependency["target"]),
                "locator": dependency["locator"], "relation": dependency["relation"], "resolution_status": "resolved" if dependency["target"] in by_source else "unresolved", "resolution_note": dependency["note"]})
    return {"sources": result, "perimeter_complete": False}
