import json
import shutil

import pytest

from legalmath.prospectus import closure_recovery as r

AT = "2026-10-04T01:00:00+00:00"


def retained(tmp_path, monkeypatch, body, status="RETAINED"):
    monkeypatch.setattr(r.c, "ROOT", tmp_path)
    monkeypatch.setattr(r.ec, "DATA", tmp_path / "data")
    path = tmp_path / "response.bin"
    path.write_bytes(body)
    receipt = tmp_path / "receipt.json"
    r.c.write(receipt, {"key": "test-source", "url": "https://example.org/path/file.pdf",
                       "status": status, "at": AT, "original": "response.bin",
                       "sha256": r.c.sha(path), "content_type": "application/pdf"})
    return receipt


def minimal_pdf(text="Synthetic review fixture"):
    stream = ("BT /F1 12 Tf 20 100 Td (" + text + ") Tj ET").encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(("%010d 00000 n \n" % n).encode() for n in offsets)
    return data + b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"


def test_html_mislabeled_pdf_only_supplies_navigation(tmp_path, monkeypatch):
    receipt = retained(tmp_path, monkeypatch, b"""<!doctype html><html><head>
    <meta http-equiv="refresh" content="0; url='../actual.pdf'"></head><body>
    <script>secret script</script><a href="/docs/base.pdf">Base <b>programme</b></a>
    <a href="https://user:password@example.org/private">Excluded</a></body></html>""")
    def no_dispatch(*args, **kwargs):
        raise AssertionError("HTML inspection must not invoke network or executable content")
    monkeypatch.setattr(r.subprocess, "run", no_dispatch)
    result = r.prepare(receipt)
    assert result["kind"] == "html" and result["status"] == "NAVIGATION_ONLY"
    assert not result["source_admitted"] and result["observed_at"] == AT
    links = r.c.read(tmp_path / next(k for k in result["files"] if k.endswith("links.json")))
    assert {v["url"] for v in links} == {"https://example.org/actual.pdf", "https://example.org/docs/base.pdf"}
    text = r.c.read(tmp_path / result["document"]["text"])["pages"][0]["text"]
    assert "secret script" not in text
    assert r.prepare(receipt) == result


@pytest.mark.skipif(not shutil.which("pdftotext") or not shutil.which("pdfinfo"), reason="Poppler required")
def test_real_pdf_extraction_preserves_page_and_provenance(tmp_path, monkeypatch):
    receipt = retained(tmp_path, monkeypatch, minimal_pdf())
    result = r.prepare(receipt)
    assert result["status"] == "EXTRACTED_UNREVIEWED" and result["document"]["pages"] == 1
    pages = r.c.read(tmp_path / result["document"]["text"])["pages"]
    assert pages[0]["page"] == 1 and "Synthetic review fixture" in pages[0]["text"]
    assert not result["source_admitted"] and result["document"]["stage"] == "UNREVIEWED"
    assert result["document"]["acquisition_receipt"] == "receipt.json"


def test_malformed_pdf_never_becomes_candidate(tmp_path, monkeypatch):
    receipt = retained(tmp_path, monkeypatch, b"%PDF-1.4\nnot a PDF")
    result = r.prepare(receipt)
    assert result["status"] == "EXTRACTION_REPAIR_REQUIRED"
    assert "document" not in result and not result["source_admitted"]


@pytest.mark.parametrize("mutation", ["response", "derivative", "receipt"])
def test_changed_evidence_rejected(tmp_path, monkeypatch, mutation):
    receipt = retained(tmp_path, monkeypatch, b"<html><body>source</body></html>")
    result = r.prepare(receipt)
    if mutation == "response":
        (tmp_path / "response.bin").write_bytes(b"changed")
    elif mutation == "derivative":
        (tmp_path / result["document"]["text"]).write_text("{}")
    else:
        value = r.c.read(receipt)
        value["at"] = "2026-10-05T00:00:00Z"
        r.c.write(receipt, value)
    with pytest.raises(ValueError, match="changed"):
        r.prepare(receipt)


def test_unavailable_body_cannot_supply_document(tmp_path, monkeypatch):
    receipt = retained(tmp_path, monkeypatch, minimal_pdf(), status="UNAVAILABLE")
    result = r.prepare(receipt)
    assert result["status"] == "UNAVAILABLE" and "document" not in result


def test_interrupted_cache_publication_can_resume(tmp_path, monkeypatch):
    receipt = retained(tmp_path, monkeypatch, b"<html><body>source</body></html>")
    original = r.os.rename
    def crash(*args):
        raise OSError("simulated interruption before publication")
    monkeypatch.setattr(r.os, "rename", crash)
    with pytest.raises(OSError, match="interruption"):
        r.prepare(receipt)
    monkeypatch.setattr(r.os, "rename", original)
    assert r.prepare(receipt)["status"] == "NAVIGATION_ONLY"


@pytest.mark.parametrize("host", ["graphqlaz.luxse.com", "example.org"])
def test_public_api_preflight_header_is_fixed_and_host_specific(tmp_path, monkeypatch, host):
    from types import SimpleNamespace
    from legalmath.prospectus import closure_phases as p
    monkeypatch.setattr(r.c, "ROOT", tmp_path)
    monkeypatch.setattr(r.ec, "DATA", tmp_path / "data")
    monkeypatch.setattr(r.ec, "policy", lambda: {
        "public_hosts": [host], "max_http_requests_including_continuation": 112,
        "max_requests_per_url": 2, "max_http_seconds": 45, "max_response_bytes": 33554432})
    monkeypatch.setattr(p, "all_requests", lambda: [])
    commands = []
    def run(argv, **kwargs):
        commands.append(argv)
        return SimpleNamespace(stdout="200", stderr="", returncode=0)
    monkeypatch.setattr(p.subprocess, "run", run)
    receipt = p.acquire({"key": "public-query", "url": "https://" + host + "/?query=query%20%7Btest%7D",
                         "gap": "synthetic", "review": "synthetic public query"})
    assert ("Apollo-Require-Preflight: true" in commands[0]) == (host == "graphqlaz.luxse.com")
    assert "--location" not in commands[0]
    assert r.c.read(receipt)["sequence"] == 1
