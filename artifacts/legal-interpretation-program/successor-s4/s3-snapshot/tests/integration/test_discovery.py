from copy import deepcopy
import json
from legalmath.sources.discovery import discover, source_changes, import_pilot


def test_captured_pagination_and_repeats(root):
    full = json.loads((root / ".localresources/sfc/product-index.json").read_text())
    items = full["items"]
    # Captured prefix, deliberately not represented as the complete live index.
    def page(start, limit): return {"items": items[start:start+limit], "total": len(items)}
    r = discover(page, page_size=17)
    assert r["status"] == "COMPLETE" and len(r["items"]) == 100
    assert discover(lambda start, limit: full)["status"] == "INCOMPLETE_REPEATED_PAGE"
    assert discover(lambda start, limit: {"items": [], "total": 0})["status"] == "COMPLETE"
    def failed(start, limit): raise OSError("upstream")
    assert discover(failed)["status"] == "FETCH_ERROR"


def test_attachment_deletion_and_real_replacement(db, root):
    old = json.loads((root / ".localresources/sfc/23EC35.json").read_text())
    new = deepcopy(old);new["appendixDocList"] = new["appendixDocList"][:1]
    assert source_changes(old, new)["removed_attachments"]
    result = import_pilot(db, root)
    assert len(result["sources"]) == 5 and result["announcement_only"] == ["25EC48"]
    with db.connect() as con:
        refs = [db.get(con, r[0]) for r in con.execute("SELECT payload_hash FROM dependencies")]
    assert any(r["relation"] == "replaces" and "26EC22" in r["from_revision_id"] and "23EC53" in r["target_revision_id"] for r in refs)


def test_captured_complete_live_pages_and_persisted_refresh(db, root):
    from legalmath.sources.discovery import refresh_official
    base = root / "artifacts/runs/sfc-live-refresh"
    calls = []
    def fetcher(url, json_body):
        calls.append(json_body["pageNo"])
        return {"media_type": "application/json", "data": (base / f'product-page{json_body["pageNo"]}.json').read_bytes()}
    report = refresh_official(db, fetcher=fetcher)
    assert calls == [0, 1] and report["status"] == "COMPLETE" and len(report["items"]) == 159
    assert len(report["captured_page_hashes"]) == 2 and db.verify()
