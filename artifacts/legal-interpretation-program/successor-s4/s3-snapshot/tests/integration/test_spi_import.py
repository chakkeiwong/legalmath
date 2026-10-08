from copy import deepcopy
import json
import pytest
from legalmath.sources.intake import import_spi, resolve_span, import_source
from legalmath.errors import LegalMathError


def test_retained_pilot_manifest_and_hash_failure(db, root, tmp_path):
    from legalmath.sources.manifest import import_manifest
    from legalmath.canonical import loads
    result = import_manifest(db, root / "corpus/sources/pilot.json")
    assert len(result["sources"]) == 7 and result["perimeter_complete"] is False
    db.verify()
    manifest = loads((root / "corpus/sources/pilot.json").read_bytes())
    for item in manifest["sources"]:
        item["raw_path"] = str(root / item["raw_path"])
        if "text_path" in item: item["text_path"] = str(root / item["text_path"])
    manifest["sources"][0]["raw_sha256"] = "0" * 64
    import json
    path = tmp_path / "bad-manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(LegalMathError, match="digest"):
        import_manifest(db, path)


def test_unverified_uploaded_annex_cannot_enter_review(db, root, case):
    from legalmath.review.lifecycle import Lifecycle
    from tests.helpers import IDENTITIES
    lc = Lifecycle(db)
    lc.register(IDENTITIES)
    with db.transaction() as con:
        import_source(db, con, "23EC35/annex1", (root / ".localresources/sfc/23EC35-annex1.pdf").read_bytes(), "application/pdf",
            "https://apps.sfc.hk/claimed", "2026-09-21T00:00:00.000000Z",
            retained_text=(root / ".localresources/sfc/23EC35-annex1.txt").read_text(),
            extractor={"name": "retained-pdftotext", "version": "test", "configuration": {}})
    bundle = lc.create("author", "draft", case["bundle"])
    with pytest.raises(LegalMathError) as error:
        lc.transition("author", "submit", bundle["bundle_hash"], "submit", 1)
    assert error.value.code == "E_RELEASE_BLOCKED"


def test_real_annex_roundtrip_and_drift(db, root):
    assert len(import_spi(db, root)) == 3
    span = json.loads((root / "docs/specs/v0.1/fixtures/source-anchor.json").read_text())["span"]
    with db.connect() as con:
        assert "40 million" in resolve_span(db, con, span)
        for field in ("raw_sha256", "text_sha256", "quote_sha256", "page", "start"):
            bad = deepcopy(span)
            bad[field] = "0" * 64 if field.endswith("sha256") else bad[field] + 1
            with pytest.raises(LegalMathError): resolve_span(db, con, bad)
    assert db.verify()


def test_html_cannot_impersonate_pdf(db):
    with db.transaction() as con, pytest.raises(LegalMathError):
        import_source(db, con, "fake", b"<html>error</html>", "application/pdf", "https://apps.sfc.hk", "2026-09-01T00:00:00.000000Z")


def test_missing_annex_rolls_back_import(db, root, tmp_path):
    fake = tmp_path / "incomplete-repository/.localresources/sfc"
    fake.mkdir(parents=True)
    (fake / "23EC35.json").write_bytes((root / ".localresources/sfc/23EC35.json").read_bytes())
    with pytest.raises(LegalMathError) as e: import_spi(db, fake.parent.parent)
    assert e.value.code == "E_DEPENDENCY"
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM sources").fetchone()[0] == 0
