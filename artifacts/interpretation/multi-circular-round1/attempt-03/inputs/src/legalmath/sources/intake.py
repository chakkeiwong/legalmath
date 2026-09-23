from pathlib import Path

from ..canonical import digest, raw_digest, loads
from ..domain import timestamp
from ..errors import LegalMathError
from .extract import extract, normalize_text
from .anchors import verify_span


def import_source(db, con, source_id, raw, media_type, official_url, retrieved_at,
                  *, retained_text=None, extractor=None, source_kind="circular", authority="UPLOADED_UNVERIFIED"):
    timestamp(retrieved_at)
    if len(raw) > 20 * 1024 * 1024:
        raise LegalMathError("E_RESOURCE_LIMIT")
    fresh_text, fresh_extractor = extract(raw, media_type)
    text = fresh_text if retained_text is None else normalize_text(retained_text)
    if retained_text is not None and not extractor:
        raise LegalMathError("E_REFERENCE")
    rh, th = db.blobs.put(raw), db.blobs.put(text.encode())
    revision_id = source_id + "/" + rh
    pages = [0] + [i + 1 for i, c in enumerate(text) if c == "\f"] + [len(text)]
    derivative = {"raw_sha256": rh, "text_sha256": th, "extractor": extractor or fresh_extractor, "page_boundaries": pages}
    dh = db.put(con, "derivative", derivative)
    publication = None
    if media_type == "application/json":
        decoded = loads(raw)
        if not isinstance(decoded, dict) or not isinstance(decoded.get("releasedDate", ""), str):
            raise LegalMathError("E_SCHEMA")
        publication = decoded.get("releasedDate", "")[:10] or None
    revision = {"source_id": source_id, "revision_id": revision_id, "raw_sha256": rh,
        "media_type": media_type, "official_url": official_url, "retrieved_at": retrieved_at,
        "published_date": publication, "effective_from": None, "effective_until": None,
        "language": "EN", "authority": authority, "source_kind": source_kind,
        "supersedes_revision_ids": [], "derivative_ids": [dh]}
    ident = db.put(con, "source", revision)
    old = con.execute("SELECT payload_hash FROM sources WHERE revision_id=?", (revision_id,)).fetchone()
    if old:
        original = db.get(con, old[0])
        if dh not in original["derivative_ids"]:
            # Derivatives may evolve without overwriting a source revision.
            con.execute("INSERT OR IGNORE INTO derivatives VALUES(?,?)", (dh, revision_id))
        return {"revision_id": revision_id, "source_hash": old[0], "derivative_hash": dh}
    con.execute("INSERT INTO sources VALUES(?,?,?)", (revision_id, source_id, ident))
    con.execute("INSERT INTO derivatives VALUES(?,?)", (dh, revision_id))
    return {"revision_id": revision_id, "source_hash": ident, "derivative_hash": dh}


def resolve_span(db, con, span):
    rows = con.execute("SELECT s.payload_hash,d.hash FROM sources s JOIN derivatives d ON d.revision_id=s.revision_id WHERE s.source_id=?", (span["source_id"],)).fetchall()
    for row in rows:
        src, derivative = db.get(con, row[0]), db.get(con, row[1])
        if src["raw_sha256"] == span["raw_sha256"] and derivative["text_sha256"] == span["text_sha256"]:
            raw = db.blobs.get(src["raw_sha256"])
            text = db.blobs.get(derivative["text_sha256"]).decode()
            return verify_span(span, raw, text)
    raise LegalMathError("E_REFERENCE")


def import_spi(db, repository):
    root = Path(repository)
    base = root / ".localresources/sfc"
    result = []
    with db.transaction() as con:
        for suffix, media in (("", "application/json"), ("-annex1", "application/pdf"), ("-annex2", "application/pdf")):
            path = base / ("23EC35" + suffix + (".pdf" if suffix else ".json"))
            if not path.exists():
                raise LegalMathError("E_DEPENDENCY")
            source_id = "23EC35" + ("/" + suffix[1:] if suffix else "")
            retained = path.with_suffix(".txt")
            url = ("https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?lang=EN&refNo=23EC35&appendix=" + ("0" if suffix == "-annex1" else "1")) if suffix else "https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC35"
            result.append(import_source(db, con, source_id, path.read_bytes(), media,
                url,
                "2026-09-21T00:00:00.000000Z", retained_text=retained.read_text() if suffix else None,
                extractor={"name": "retained-pdftotext", "version": "proposal-v0.3", "configuration": {"source_snapshot": "2026-09-21"}} if suffix else None,
                source_kind="annex" if suffix else "circular", authority="RETAINED_PUBLIC_SOURCE"))
        for annex in result[1:]:
            dep = {"from_revision_id": result[0]["revision_id"], "locator": annex["revision_id"].split("/")[1],
                "target_revision_id": annex["revision_id"], "relation": "incorporates", "resolution_status": "resolved", "resolution_note": "Retained public annex"}
            dh = db.put(con, "dependency", dep)
            con.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?,1)", (digest(dep), dep["from_revision_id"], dep["target_revision_id"], dh))
    return result
