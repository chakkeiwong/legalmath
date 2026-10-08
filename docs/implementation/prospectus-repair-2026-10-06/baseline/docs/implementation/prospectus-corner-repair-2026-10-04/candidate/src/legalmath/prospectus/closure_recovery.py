"""Bounded local inspection of retained HTTP responses; never source admission."""
from html.parser import HTMLParser
from pathlib import Path
import os
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlparse

from . import master_control as c, evidence_closure as ec
from .closure_sources import require


class Navigation(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url, self.links, self.parts = url, [], []
        self.hidden = 0
        self.anchor = None

    def add(self, href, label):
        url = urljoin(self.url, href)
        parsed = urlparse(url)
        if parsed.scheme == "https" and not parsed.username and not parsed.password:
            self.links.append({"url": url, "label": " ".join(label.split())})

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "a" and attrs.get("href"):
            self.anchor = {"url": attrs["href"], "text": []}
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            found = re.search(r"(?i)url\s*=\s*(.+)", attrs.get("content", ""))
            if found:
                self.add(found.group(1).strip().strip("'\""), "HTTP-equivalent refresh; separate request required")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "a" and self.anchor:
            self.add(self.anchor["url"], " ".join(self.anchor["text"]))
            self.anchor = None

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())
            if self.anchor is not None:
                self.anchor["text"].append(data.strip())


def checked_path(name):
    path = (c.ROOT / name).resolve()
    require(path.is_relative_to(c.ROOT.resolve()) and path.is_file(), "Response evidence outside checkout or missing")
    return path


def prepare(receipt_path):
    receipt_path = checked_path(c.relative(receipt_path))
    receipt = c.read(receipt_path)
    body_name = receipt.get("original", receipt.get("body"))
    if body_name is None:
        return {"key": receipt["key"], "status": "NO_RESPONSE_BYTES", "files": {}}
    body = checked_path(body_name)
    require(c.sha(body) == receipt["sha256"], "Retained response changed")
    require(re.fullmatch(r"[a-z0-9-]{1,70}", receipt["key"]), "Invalid retained request key")
    target = ec.DATA / "recovered" / receipt["key"] / receipt["sha256"]
    manifest = target / "inspection.json"
    binding = {"receipt_sha256": c.sha(receipt_path), "source_sha256": receipt["sha256"], "version": "recovery-inspection.v1"}
    if manifest.exists():
        prior = c.read(manifest)
        require(prior["binding"] == binding, "Retained response review binding changed")
        for name, expected in prior["files"].items():
            require(c.sha(checked_path(name)) == expected, "Recovery derivative changed")
        return {**prior, "files": {**prior["files"], c.relative(manifest): c.sha(manifest)}}
    require(target.resolve().is_relative_to(c.ROOT.resolve()), "Recovery destination outside checkout")
    require(not target.exists(), "Incomplete recovery cache requires explicit repair")
    target.parent.mkdir(parents=True, exist_ok=True)
    derivatives = {}
    raw = body.read_bytes()
    kind = "pdf" if raw.lstrip().startswith(b"%PDF-") else (
        "html" if re.search(br"(?is)<(?:!doctype\s+html|html|head|body)\b", raw[:8192]) else "other")
    result = {"binding": binding, "key": receipt["key"], "kind": kind, "status": "UNAVAILABLE",
              "files": {}, "source_admitted": False, "observed_at": receipt["at"],
              "receipt": c.relative(receipt_path)}
    if receipt.get("status") == "RETAINED":
        pages, links = [], []
        if kind == "pdf":
            with tempfile.TemporaryDirectory(prefix="prospectus-recovery-", dir="/tmp") as scratch:
                out = Path(scratch) / "text.txt"
                try:
                    extraction = subprocess.run(["pdftotext", "-layout", str(body), str(out)],
                                                capture_output=True, timeout=60)
                    info = subprocess.run(["pdfinfo", str(body)], capture_output=True, text=True, timeout=20)
                    count = re.search(r"(?m)^Pages:\s+(\d+)", info.stdout)
                    require(extraction.returncode == info.returncode == 0 and count is not None,
                            "PDF parsing failed; original retained for repair")
                    chunks = out.read_text().split("\f")
                    if not chunks[-1].strip():
                        chunks.pop()
                    require(len(chunks) == int(count.group(1)) and chunks,
                            "PDF extraction page count differs from original")
                    pages = [{"page": i + 1, "text": part} for i, part in enumerate(chunks)]
                    result["status"] = "EXTRACTED_UNREVIEWED" if any(p["text"].strip() for p in pages) else "OCR_REQUIRED"
                    result["extractor"] = "pdftotext -layout; pdfinfo page count checked"
                except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
                    result.update(status="EXTRACTION_REPAIR_REQUIRED", error=str(exc))
        elif kind == "html":
            parser = Navigation(receipt["url"])
            parser.feed(raw.decode("utf-8", errors="replace"))
            require(len(parser.links) <= 5000, "HTML link limit exceeded")
            pages = [{"page": 1, "text": "\n".join(parser.parts)}]
            links = list({(v["url"], v["label"]): v for v in parser.links}.values())
            result.update(status="NAVIGATION_ONLY", links=len(links))
            derivatives["links.json"] = links
        else:
            result["status"] = "UNSUPPORTED_RESPONSE"
        if pages:
            path = target / "pages.json"
            derivatives["pages.json"] = {"id": receipt["key"], "source_sha256": receipt["sha256"], "pages": pages,
                                         "source_stage": "UNREVIEWED", "extraction_fidelity": "UNREVIEWED"}
            result["document"] = {"id": receipt["key"], "original": body_name, "sha256": receipt["sha256"],
                                  "text": c.relative(path), "pages": len(pages),
                                  "url": receipt["url"], "acquisition_receipt": c.relative(receipt_path),
                                  "stage": "UNREVIEWED", "media_type": kind}
    # Publish the complete cache together. A killed extraction never leaves a
    # visible partial cache that could be mistaken for a reviewed derivative.
    with tempfile.TemporaryDirectory(prefix=".recovery-", dir=target.parent) as staging:
        staging = Path(staging)
        for name, value in derivatives.items():
            c.write(staging / name, value, exclusive=True)
            result["files"][c.relative(target / name)] = c.sha(staging / name)
        if "document" in result:
            result["document"]["text_sha256"] = result["files"][result["document"]["text"]]
        c.write(staging / "inspection.json", result, exclusive=True)
        os.rename(staging, target)
    return {**result, "files": {**result["files"], c.relative(manifest): c.sha(manifest)}}
