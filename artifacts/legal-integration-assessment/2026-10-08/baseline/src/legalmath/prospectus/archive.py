"""Preserve source bytes; extracted text is a separately versioned derivative."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import subprocess
from urllib.parse import urlparse

from .common import ARCHIVE, now, read, sha, write


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignored += 1
        elif tag in ("p", "div", "br", "tr", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.ignored:
            self.ignored -= 1
        elif tag in ("p", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def html_text(raw):
    parser = VisibleText()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return "\n".join(re.sub(r"\s+", " ", p).strip() for p in "".join(parser.parts).splitlines() if p.strip())


def extract(path, kind):
    raw = Path(path).read_bytes()
    extractor = "stdlib-html-json"
    if kind == "pdf":
        if b"%PDF-" not in raw[:1024]:
            raise ValueError("Response is not a PDF")
        from pypdf import PdfReader
        from pypdf.errors import DependencyError
        try:
            reader = PdfReader(path)
            pages = [{"page": i + 1, "text": p.extract_text() or ""} for i, p in enumerate(reader.pages)]
            extractor = "pypdf"
        except DependencyError:
            proc = subprocess.run(["/usr/bin/pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                                  capture_output=True, text=True, timeout=60)
            if proc.returncode:
                raise ValueError("PDF text extraction unavailable: " + proc.stderr)
            texts = proc.stdout.split("\f")
            if texts and not texts[-1].strip():
                texts.pop()
            pages = [{"page": i + 1, "text": text} for i, text in enumerate(texts)]
            extractor = "poppler-pdftotext-layout"
    else:
        if kind == "json":
            data = json.loads(raw)
            body = data.get("html", "")
            text = html_text(body.encode()) if body else json.dumps(data, ensure_ascii=False)
        else:
            text = html_text(raw)
        if len(text.strip()) < 100 or any(s in text[:1500].lower() for s in (
            "your request originates from an undeclared automated tool", "access denied", "request rate threshold exceeded"
        )):
            raise ValueError("Empty or denied source response")
        pages = [{"page": 1, "text": text}]
    if not pages or sum(len(p["text"].strip()) for p in pages) < 100:
        raise ValueError("No usable text; OCR remains required")
    # HTML filings may contain a whole appended base prospectus in one text unit.
    # References to a historical preliminary offering deep inside that document
    # must not label its current cover as preliminary.
    cover = re.sub(r"\s+", " ", pages[0]["text"])[:5000].lower()
    return {
        "extraction_schema": "prospectus-text.v2",
        "source_sha256": sha(raw), "extractor": extractor,
        "page_count": len(pages), "pages": pages,
        "preliminary_indicator": bool(re.search(r"preliminary\s+prospectus|subject\s+to\s+completion", cover)),
        "text_completeness": "NOT_ESTABLISHED", "rendered_equivalence": "NOT_ESTABLISHED",
    }


def catalog(root=ARCHIVE):
    rows = read(Path(root) / "catalog.json")
    if len(rows) > 32 or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Source budget or duplicate identity")
    for row in rows:
        if not re.fullmatch(r"[a-z0-9-]+", row["id"]):
            raise ValueError("Invalid source ID")
        if row["kind"] not in ("pdf", "html", "json") or urlparse(row["url"]).scheme != "https":
            raise ValueError("Only listed HTTPS PDF/HTML/JSON documents are accepted")
    return rows


def acquire(rows, directory, *, root=ARCHIVE):
    root = Path(root)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for sub in ("originals", "text"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest = read(manifest_path) if manifest_path.exists() else {"documents": {}, "history": []}
    results = []
    for row in rows:
        source = root / "originals" / (row["id"] + "." + row["kind"])
        previous = manifest["documents"].get(row["id"])
        if previous and any(previous[k] != row[k] for k in ("id", "url", "kind", "instrument", "role")):
            raise ValueError("Source identity changed; create a new catalog entry: " + row["id"])
        if previous and source.exists():
            if sha(source.read_bytes()) != previous["sha256"]:
                raise ValueError("Preserved source changed: " + row["id"])
            text_path = root / "text" / (row["id"] + ".json")
            if not text_path.exists() or read(text_path)["source_sha256"] != previous["sha256"]:
                write(text_path, extract(source, row["kind"]))
            results.append({"id": row["id"], "status": "PRESERVED", "cached": True})
            continue
        failures = [a for a in manifest["history"] if a["url"] == row["url"] and a["status"] == "FAILED"
                    and a.get("transport") == "curl-default-v3"]
        if len(failures) >= 2:
            results.append({"id": row["id"], "status": "FAILED", "cached": True,
                            "reason": "Two failed acquisition attempts retained; use a separately identified mirror"})
            continue
        temp = directory / (row["id"] + ".response")
        argv = ["curl", "--location", "--fail-with-body", "--silent", "--show-error",
                "--connect-timeout", "15", "--max-time", "60", "--max-filesize", "52428800",
                "--proto", "=https", "--proto-redir", "=https",
                "--output", str(temp), "--write-out", "%{json}", row["url"]]
        attempt = {"id": row["id"], "url": row["url"], "retrieved_at": now(), "argv": argv, "transport": "curl-default-v3"}
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=70)
            info = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
            attempt.update(http_status=info.get("http_code"), effective_url=info.get("url_effective"),
                           exit_code=proc.returncode, error=proc.stderr[-1500:])
            if proc.returncode:
                raise ValueError("Download failed: " + str(proc.returncode))
            parsed = extract(temp, row["kind"])
            raw = temp.read_bytes()
            if source.exists() and source.read_bytes() != raw:
                raise ValueError("Refusing to overwrite preserved original")
            source.write_bytes(raw)
            write(root / "text" / (row["id"] + ".json"), parsed)
            entry = {**row, "sha256": sha(raw), "bytes": len(raw), "retrieved_at": attempt["retrieved_at"],
                     "effective_url": attempt["effective_url"], "page_count": parsed["page_count"],
                     "preliminary_indicator": parsed["preliminary_indicator"],
                     "file": str(source.relative_to(root)), "authenticity": "HTTPS_LOCATION_ONLY"}
            manifest["documents"][row["id"]] = entry
            attempt["status"] = "PRESERVED"
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            attempt.update(status="FAILED", error=str(exc))
        write(directory / (row["id"] + ".acquisition.json"), attempt)
        manifest["history"].append(attempt)
        write(manifest_path, manifest)
        results.append({"id": row["id"], "status": attempt["status"], "cached": False})
        print(json.dumps(results[-1]), flush=True)
    write(directory / "acquisition.json", results)
    write_index(root, manifest)
    return results


def write_index(root, manifest):
    lines = ["# Preserved prospectuses and related sources", "",
             "Original bytes are retained in `originals/`; page text in `text/` is a derivative.",
             "`catalog.json` records every requested source, including unsuccessful downloads.",
             "`manifest.json` records URLs, acquisition attempts, versions and SHA-256 checksums.",
             "These are development sources. Document preservation does not verify a legal interpretation.", "",
             "| Document | Role | Preserved file | Pages |", "| --- | --- | --- | --- |"]
    for row in catalog(root):
        item = manifest["documents"].get(row["id"])
        location = "DOWNLOAD PENDING" if item is None else f"[{row['id']}]({item['file']})"
        lines.append(f"| [{row['title']}]({row['url']}) | {row['role']} | {location} | {item['page_count'] if item else '—'} |")
    (Path(root) / "README.md").write_text("\n".join(lines) + "\n")


def verify(root=ARCHIVE):
    manifest = read(Path(root) / "manifest.json")
    rows = {r["id"]: r for r in catalog(root)}
    for key, item in manifest["documents"].items():
        if key not in rows or any(item[k] != rows[key][k] for k in ("id", "url", "kind", "instrument", "role")):
            raise ValueError("Source provenance differs from catalog: " + key)
        path = Path(root) / item["file"]
        if sha(path.read_bytes()) != item["sha256"]:
            raise ValueError("Original byte mismatch: " + key)
        parsed = read(Path(root) / "text" / (key + ".json"))
        if parsed != extract(path, item["kind"]):
            raise ValueError("Source text changed: " + key)
    return {"preserved": len(manifest["documents"]), "requested": len(catalog(root)),
            "original_integrity": "CHECKED", "legal_meaning": "NOT_ESTABLISHED"}


def derivative_repairs(*, root=ARCHIVE, execute=False):
    """Rebuild derivatives only. Changed preserved originals are a hard failure."""
    root = Path(root)
    manifest = read(root / "manifest.json")
    changes = []
    for key, item in manifest["documents"].items():
        source = root / item["file"]
        if sha(source.read_bytes()) != item["sha256"]:
            raise ValueError("Preserved original changed: " + key)
        target = root / "text" / (key + ".json")
        derived = extract(source, item["kind"])
        try:
            prior = read(target)
        except (OSError, ValueError):
            prior = None
        if prior != derived:
            changes.append({"document": key, "repair": "REEXTRACT_FROM_UNCHANGED_ORIGINAL", "executed": execute})
            if execute:
                write(target, derived)
                item["preliminary_indicator"] = derived["preliminary_indicator"]
                item["page_count"] = derived["page_count"]
    if execute and changes:
        write(root / "manifest.json", manifest)
    return changes
