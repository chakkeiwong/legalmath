"""Cursor progress is explicit; incomplete discovery is never an empty result."""
import json
from pathlib import Path
import re

from ..canonical import digest
from ..errors import LegalMathError
from .intake import import_source

PILOT = ("23EC35", "23EC46", "23EC53", "26EC22", "25EC48")


def refresh_official(db, category="products", *, page_size=100, max_pages=20, fetcher=None):
    from .fetch import fetch
    from ..canonical import loads
    fetcher = fetcher or fetch
    parameters = {"products": ("production-authorization", 100), "intermediaries": ("intermediaries-supervision", 110)}
    if category not in parameters or not 1 <= page_size <= 100 or not 1 <= max_pages <= 20:
        raise LegalMathError("E_SCHEMA")
    name, typ = parameters[category]
    url = "https://apps.sfc.hk/edistributionWeb/api/circular/search"
    captured = []

    def page(offset, count):
        request = {"lang": "EN", "category": name, "postDocType": typ, "year": "all", "pageNo": offset // count,
            "pageSize": count, "sort": {"field": "issueDate", "order": "desc"}}
        response = fetcher(url, json_body=request)
        if response["media_type"] != "application/json": raise LegalMathError("E_FETCH")
        payload = loads(response["data"])
        with db.transaction() as con:
            raw_hash = db.blobs.put(response["data"])
            captured.append(db.put(con, "discovery_page", {"url": url, "request": request, "raw_sha256": raw_hash, "response": payload}))
        return payload
    result = discover(page, page_size=page_size, max_pages=max_pages)
    result.update(category=category, captured_page_hashes=captured, perimeter_complete=False)
    with db.transaction() as con:
        rh = db.put(con, "discovery_result", result)
        db.audit(con, {"operation": "public_discovery", "result_hash": rh})
    return {**result, "result_hash": rh}


def discover(page_fetcher, *, start=0, page_size=100, max_pages=20):
    cursor, pages, items, seen_pages, total = start, [], {}, set(), None
    for _ in range(max_pages):
        try:
            page = page_fetcher(cursor, page_size)
        except Exception as exc:
            return {"status": "FETCH_ERROR", "next_cursor": cursor, "items": list(items.values()), "pages": pages}
        if not isinstance(page, dict) or not isinstance(page.get("items"), list) or type(page.get("total")) is not int or page["total"] < 0:
            raise LegalMathError("E_SCHEMA")
        h = digest(page)
        if h in seen_pages:
            return {"status": "INCOMPLETE_REPEATED_PAGE", "next_cursor": cursor, "items": list(items.values()), "pages": pages}
        seen_pages.add(h)
        if total is not None and total != page["total"]:
            return {"status": "INCOMPLETE_CHANGING_TOTAL", "next_cursor": cursor, "items": list(items.values()), "pages": pages}
        total = page["total"]
        for item in page["items"]:
            key = item["refNo"] + "/" + item["lang"]
            if key in items and items[key] != item:
                return {"status": "INCOMPLETE_CHANGED_ITEM", "next_cursor": cursor, "items": list(items.values()), "pages": pages}
            items[key] = item
        pages.append({"cursor": cursor, "hash": h, "count": len(page["items"])})
        cursor += len(page["items"])
        if cursor >= total:
            if start == 0 and len(items) != total:
                return {"status": "INCOMPLETE_DUPLICATES", "next_cursor": cursor, "items": list(items.values()), "pages": pages}
            return {"status": "COMPLETE" if start == 0 else "COMPLETE_REMAINDER", "next_cursor": None, "items": list(items.values()), "pages": pages}
        if not page["items"]:
            break
    return {"status": "INCOMPLETE_BUDGET", "next_cursor": cursor, "items": list(items.values()), "pages": pages}


def source_changes(old, new):
    old_attachments = {str(a["fileKeySeq"]): a for a in old.get("appendixDocList", [])}
    new_attachments = {str(a["fileKeySeq"]): a for a in new.get("appendixDocList", [])}
    return {"bytes_changed": digest(old) != digest(new), "removed_attachments": sorted(set(old_attachments) - set(new_attachments)),
        "added_attachments": sorted(set(new_attachments) - set(old_attachments)),
        "modified_attachments": sorted(k for k in set(old_attachments) & set(new_attachments) if old_attachments[k] != new_attachments[k])}


def import_pilot(db, repository):
    base = Path(repository) / ".localresources/sfc"
    imported, snapshots = {}, {}
    with db.transaction() as con:
        for ref in PILOT:
            raw = (base / (ref + ".json")).read_bytes()
            snapshots[ref] = json.loads(raw)
            imported[ref] = import_source(db, con, ref, raw, "application/json",
                "https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=" + ref,
                "2026-09-21T00:00:00.000000Z", authority="RETAINED_PUBLIC_SOURCE")
        old = snapshots["23EC53"]
        if "replaced" not in old["html"] or "26EC22" not in old["html"]:
            raise LegalMathError("E_DEPENDENCY")
        dep = {"from_revision_id": imported["26EC22"]["revision_id"], "target_revision_id": imported["23EC53"]["revision_id"],
            "locator": "replacement notice on retained 23EC53 page", "relation": "replaces", "resolution_status": "resolved",
            "resolution_note": "Source relationship only; scope and implementation changes need review."}
        ident = db.put(con, "dependency", dep)
        con.execute("INSERT OR IGNORE INTO dependencies VALUES(?,?,?,?,1)", (digest(dep), dep["from_revision_id"], dep["target_revision_id"], ident))
    return {"sources": imported, "announcement_only": ["25EC48"], "perimeter_complete": False, "basis": "retained public snapshots"}
