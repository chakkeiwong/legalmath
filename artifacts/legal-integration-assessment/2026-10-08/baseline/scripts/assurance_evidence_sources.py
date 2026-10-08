"""Fixed-scope official retrieval; source bytes never become executable commands."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import re
import time
import subprocess
import xml.etree.ElementTree as ET

import httpx
import assurance_evidence_core as c
from assurance_gap_authorities import html_text, normalize, operative_part_four
from legalmath.canonical import digest, raw_digest

HOSTS = {"www.sfc.hk", "apps.sfc.hk", "www.jfiu.gov.hk", "www.elegislation.gov.hk",
         "resource.data.one.gov.hk"}
MAX_BYTES = 12_000_000
MAX_REQUESTS = 24
QUOTES = [
    "(ii) unlisted securities (excluding unlisted securities that are structured products);",
    "(ii) a regulated investment agreement or an agreement to acquire, dispose of, subscribe for or underwrite any other structured product;",
]

def allowed_url(url):
    u = urlsplit(url)
    return (u.scheme == "https" and u.hostname in HOSTS and u.port in (None, 443)
            and u.username is None and u.password is None)

def seeds(authority):
    rows = [
        ("codes-index", "current", "Find current and previous UT Code and Code of Conduct edition notices.",
         "https://www.sfc.hk/en/Rules-and-standards/Codes-and-guidelines/Codes"),
        ("current-tokenisation", "2026-04-20", "Exact active paragraph 10 source and replacement notice.",
         "https://apps.sfc.hk/edistributionWeb/api/circular/list-content?lang=EN&refNo=26EC22"),
        ("tokenised-securities", "2023-11-02", "Full incorporated 23EC52 guidance and publication date.",
         "https://apps.sfc.hk/edistributionWeb/api/circular/list-content?lang=EN&refNo=23EC52"),
        ("appendix", "2023-11-02", "All three pages of the incorporated Appendix including Part A.",
         "https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?appendix=0&lang=EN&refNo=23EC52"),
        ("statute-historical", "2023-11-02", "Point-in-time Part IV/Schedule 1, amendments and commencement.",
         "https://www.elegislation.gov.hk/hk/cap571!en@2023-11-02"),
        ("statute-current", "2026-04-20", "Point-in-time Part IV/Schedule 1 and change chain through 20 April 2026.",
         "https://www.elegislation.gov.hk/hk/cap571!en@2026-04-20"),
        ("enforcement-index", "2026-04-20", "Official decisions/guidance addressing responsibility despite delegation.",
         "https://www.sfc.hk/en/Regulatory-functions/Enforcement/Enforcement-news"),
    ]
    for u in authority["units"]:
        ref = u.get("metadata", {}).get("acquisition")
        if ref and u["unit_id"] in ("historical.jfiu-home", "historical.jfiu-login", "historical.gifts-faq",
                                    "historical.gifts-faq-original"):
            rows.append((u["unit_id"], "historical date NOT ESTABLISHED",
                         "Seek schema/signature/resubmission instructions or mixed-package interpretation.",
                         ref["url"]))
    return [{"id": x, "question_date": date, "question": question, "url": url} for x, date, question, url in rows]

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = {"url": dict(attrs).get("href", ""), "text": ""}
    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data
    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.rows.append(self.current)
            self.current = None

def fetch(spec, directory):
    directory.mkdir(parents=True, exist_ok=True)
    result = directory/"result.json"
    if result.exists():
        row = c.read(result)
        for ref in row.get("files", []):
            c.checked(ref, directory)
        return row
    # An interrupted request is recorded, never invisibly retried.
    if (directory/"started.json").exists():
        row = {**spec, "status": "INTERRUPTED", "needed": spec["question"], "files": []}
        c.save(result, row)
        return row
    c.save(directory/"started.json", {**spec, "started_at": c.now()})
    began = time.monotonic()
    row = {**spec, "files": [], "redirects": [], "temporal_applicability": "NOT_ESTABLISHED"}
    try:
        current = spec["url"]
        with httpx.Client(timeout=30, follow_redirects=False, trust_env=True) as client:
            for _ in range(4):
                if not allowed_url(current):
                    c.fail("E_AUTHORITY", "URL outside official-host allowlist")
                with client.stream("GET", current, headers={"User-Agent": "LegalMath-evidence-review/1.0"}) as response:
                    row["http_status"] = response.status_code
                    row["content_type"] = response.headers.get("content-type", "")
                    row["etag"] = response.headers.get("etag")
                    row["last_modified"] = response.headers.get("last-modified")
                    if response.is_redirect:
                        target = urljoin(current, response.headers["location"])
                        row["redirects"].append({"from": current, "to": target})
                        current = target
                        continue
                    response.raise_for_status()
                    data = bytearray()
                    for chunk in response.iter_bytes(65536):
                        data.extend(chunk)
                        if len(data) > MAX_BYTES or time.monotonic()-began > 90:
                            c.fail("E_RESOURCE_LIMIT", "Public-source byte/time bound")
                    (directory/"source.bin").write_bytes(data)
                    row.update(status="RETRIEVED", final_url=current, bytes=len(data),
                               files=[c.receipt(directory/"source.bin", directory)])
                    break
            else:
                c.fail("E_RESOURCE_LIMIT", "Redirect bound exceeded")
        data = bytes(data)
        if data.startswith(b"%PDF"):
            completed = subprocess.run(["pdftotext", "-layout", str(directory/"source.bin"), "-"],
                capture_output=True, text=True, timeout=60)
            if completed.returncode:
                c.fail("E_DEPENDENCY", "Installed Poppler PDF extraction failed")
            text = completed.stdout
            pages = text.split("\f")
            if pages and not pages[-1].strip():
                pages.pop()
            row["pdf_pages"] = len(pages)
            c.save(directory/"pdf-pages.json", [{"page": i+1, "text": t} for i, t in enumerate(pages)])
            row["files"].append(c.receipt(directory/"pdf-pages.json", directory))
            row["extraction_scope"] = "Complete PDF text; rendered inspection tracked separately."
        else:
            raw = data.decode("utf-8", errors="replace")
            text = html_text(raw)
            if "json" in row["content_type"]:
                import json
                obj = json.loads(raw)
                if isinstance(obj, dict) and isinstance(obj.get("html"), str):
                    text = html_text(obj["html"])
                    row["publication_metadata"] = {k: obj.get(k) for k in ("releasedDate", "title", "publicUrl")}
                elif isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict) and "html" in obj[0]:
                    text = html_text(obj[0]["html"])
                    row["publication_metadata"] = {k: obj[0].get(k) for k in ("releasedDate", "title")}
                else:
                    row["extraction_scope"] = "JSON/index not recognized as a complete operative document."
            parser = Links()
            parser.feed(raw)
            links = []
            for link in parser.rows:
                url = urljoin(current, link["url"])
                if allowed_url(url):
                    links.append({"url": url, "text": normalize(link["text"])})
            c.save(directory/"links.json", links)
            row["files"].append(c.receipt(directory/"links.json", directory))
        c.write_text(directory/"text.txt", text)
        row["files"].append(c.receipt(directory/"text.txt", directory))
        row["text_characters"] = len(text)
        row["retrieved_at"] = c.now()
    except Exception as exc:
        row.update(status="RETRIEVED_EXTRACTION_FAILED" if row.get("files") else "UNAVAILABLE", error=type(exc).__name__, details=str(exc)[:1200],
                   needed=spec["question"])
    row["elapsed_seconds"] = str(round(time.monotonic()-began, 3))
    c.save(result, row)
    return row

def acquire(root, work, authority):
    initial = seeds(authority)
    c.save(work/"acquisition-contract.json", {
        "queries": initial, "maximum_requests": MAX_REQUESTS, "maximum_bytes_per_document": MAX_BYTES,
        "method": "Exact official source/index, then at most two relevant public links per family; no login.",
        "pass": "Retained complete response bytes and explicit edition/date evidence.",
        "nonclaim": "A successful download or failed index search does not establish applicability or absence of authority."})
    results = []
    for spec in initial:
        results.append(fetch(spec, work/"downloads"/spec["id"]))
    # Deterministic official-link follow-up; no model-generated URLs or arbitrary commands.
    seen = {r["url"] for r in results}
    targets = ("codes-index", "historical.jfiu-home", "historical.jfiu-login",
               "historical.gifts-faq", "enforcement-index")
    pattern = re.compile(r"unit trusts|previous|code of conduct|schema|xml|certificate|str |reporting|outsourc|delegat|mixed|gift", re.I)
    for parent in list(results):
        if parent["id"] not in targets:
            continue
        path = work/"downloads"/parent["id"]/"links.json"
        if not path.exists():
            continue
        count = 0
        for link in c.read(path):
            if link["url"] in seen or not pattern.search(link["text"]+" "+link["url"]):
                continue
            spec = {"id": parent["id"]+f".followup.{count+1}", "question_date": parent["question_date"],
                    "question": parent["question"], "url": link["url"], "discovered_on": parent["url"],
                    "link_text": link["text"]}
            results.append(fetch(spec, work/"downloads"/spec["id"]))
            seen.add(spec["url"])
            count += 1
            if count == 2 or len(results) == MAX_REQUESTS:
                break
    # Alternate official open-data path; existing downloader is edition/range/CRC bound.
    archive = work/"chapter571"
    c.save(archive/"intent.json", {
        "url": "https://resource.data.one.gov.hk/doj/data/hkel_c_leg_cap_301_cap_600_en.zip",
        "question": "Does the current official archive extend the retained 2025 consolidation or establish either question date?",
        "question_dates": ["2023-11-02", "2026-04-20"], "range_budget": 32_000_000})
    if not (archive/"acquisition.json").exists():
        try:
            from legalmath.interpretation.assurance.official_archive import chapter
            value = chapter("https://resource.data.one.gov.hk/doj/data/hkel_c_leg_cap_301_cap_600_en.zip", archive)
            c.save(archive/"acquisition.json", {"status": "RETRIEVED", "result": value})
        except Exception as exc:
            c.save(archive/"acquisition.json", {"status": "UNAVAILABLE", "error": type(exc).__name__,
                                               "details": str(exc)[:1200]})
    archive_result = c.read(archive/"acquisition.json")
    c.save(work/"source-acquisition.json", {"public_requests": results, "official_archive": archive_result,
        "private_requirements": ["JFIU versioned schema package and submission instructions if confined to registered operators",
                                 "Actual provider appointment/termination, ownership and control records",
                                 "Applicable SFC scheme conditions or authoritative resolution of disputed interpretation"],
        "legal_correctness": "NOT_ESTABLISHED"})
    return results, archive_result

def repaired_authority(root, out):
    authority = deepcopy(c.read(root/c.OLD/"authority-context.json"))
    xml = root/"artifacts/assurance-gap-closure/2026-09-30/G5r/attempt-01/chapter571/chapter-00.xml"
    tree = ET.parse(xml).getroot()
    part = operative_part_four(tree)
    parents = {child: node for node in tree.iter() for child in node}
    parent = next(u for u in authority["units"] if u["unit_id"] == "cap571.part4")
    if normalize(" ".join(part.itertext())) != parent["text"]:
        c.fail("E_INTEGRITY", "Statutory parent differs from retained XML")
    locators = c.locate_repeated_quotes(parent, QUOTES)
    ns = "{http://www.xml.gov.hk/schemas/hklm/1.0}"
    for node in part.iter(ns+"section"):
        text = normalize(" ".join(node.itertext()))
        if not any(q in text for q in QUOTES):
            continue
        start = parent["text"].find(text)
        if start < 0 or parent["text"].count(text) != 1:
            c.fail("E_REFERENCE", "Statutory section not unique in complete parent")
        ancestry, current = [], node
        while current is not None:
            ancestry.append({"tag": current.tag, "attributes": dict(current.attrib)})
            current = parents.get(current)
        locators.append({"unit_id": "cap571."+node.get("temporalId")+".edition20250824",
            "text": text, "parent_unit_id": parent["unit_id"], "parent_text_hash": digest(parent["text"]),
            "start": start, "end": start+len(text), "xml_ancestry": list(reversed(ancestry)),
            "xml_receipt": c.receipt(xml, root), "qualification": "Complete section in retained 2025 consolidation; no historical/current applicability inferred."})
    authority["units"].extend(locators)
    for group in authority["groups"]:
        if any(u["unit_id"] == parent["unit_id"] for u in group["packet"]["units"]):
            group["packet"]["units"].extend(locators)
        c.verify_packet(group["packet"])
    c.verify_packet({"units": authority["units"]})
    c.save(out/"authority-context.json", authority)
    c.save(out/"quote-locator-repair.json", {"parent": parent["unit_id"], "locators": locators,
        "original_occurrences": {q: parent["text"].count(q) for q in QUOTES},
        "repair": "Unique span IDs and complete section ancestry, with full parent retained.",
        "legal_correctness": "NOT_ESTABLISHED"})
    return authority

def current_packet(root, authority):
    original = deepcopy(c.read(root/c.OLD/"context.json")["packet"])
    ids = {"ut-current.parent", "ut-current.intro", "tokenised-securities.circular",
           "tokenised-securities.appendix"}
    original["units"] += [u for u in authority["units"] if u["unit_id"] in ids]
    return c.verify_packet(original)
