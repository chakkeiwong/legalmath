"""Bounded source acquisition and local reading support for the adoption survey."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/prospectus-adoption-2026-10-07"
RA = Path("/home/chakwong/python/ResearchAssistant")


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def fetch(ident, url, suffix):
    if not ident.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Use a simple source identifier")
    if not url.startswith("https://") or suffix not in {"pdf", "html", "json", "md", "py", "cpp", "hpp", "zip", "txt"}:
        raise ValueError("Public HTTPS and declared source formats only")
    folder = OUT / "sources" / ident
    folder.mkdir(parents=True, exist_ok=True)
    if (folder / "receipt.json").exists():
        raise ValueError("Preserve existing retrieval; use a new identifier")
    attempts = list((OUT / "sources").glob("*/receipt.json"))
    if len(attempts) >= 65:
        raise ValueError("Direct retrieval budget reached; reserve discovery requests")
    target = folder / ("source." + suffix)
    cmd = ["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
           "--max-redirs", "3", "--connect-timeout", "12", "--max-time", "50",
           "--max-filesize", "25000000", "--silent", "--show-error",
           "--output", str(target), "--write-out", "%{json}", url]
    started = time.monotonic()
    run = subprocess.run(cmd, capture_output=True, text=True)
    try:
        transport = json.loads(run.stdout)
    except json.JSONDecodeError:
        transport = {"output": run.stdout}
    valid = run.returncode == 0 and target.is_file()
    if valid and suffix == "pdf":
        valid = target.read_bytes().startswith(b"%PDF-")
    if valid and suffix == "json":
        try:
            json.loads(target.read_text())
        except (UnicodeError, json.JSONDecodeError):
            valid = False
    receipt = {"id": ident, "url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
               "command": cmd, "returncode": run.returncode, "format_valid": valid,
               "transport": transport, "stderr": run.stderr, "wall_seconds": time.monotonic()-started,
               "path": str(target.relative_to(ROOT)) if target.exists() else None,
               "bytes": target.stat().st_size if target.exists() else 0,
               "sha256": hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None}
    write(folder / "receipt.json", receipt)
    print(json.dumps({k:receipt[k] for k in ("id", "returncode", "format_valid", "bytes", "stderr")}))
    if not valid:
        raise SystemExit(1)


def parse():
    sys.path.insert(0, str(RA / "src"))
    from research_assistant.ingest.parser_pdftotext import PdftotextParser
    parser = PdftotextParser()
    for path in sorted((OUT / "sources").glob("*/source.pdf")):
        target = path.parent / "parsed.json"
        if target.exists():
            continue
        doc = parser.parse(path)
        write(target, doc.to_dict())
        (path.parent / "text.txt").write_text(doc.body_text)
        print(json.dumps({"id":path.parent.name, "status":doc.parse_status, "characters":len(doc.body_text)}))
    from lxml import html
    for path in sorted((OUT / "sources").glob("*/source.html")):
        target = path.with_name("text.txt")
        if target.exists():
            continue
        tree = html.fromstring(path.read_bytes())
        for element in tree.xpath("//script|//style|//nav"):
            element.drop_tree()
        target.write_text("\n".join(t.strip() for t in tree.itertext() if t.strip()) + "\n")


def inventory():
    """Inspect metadata and retained receipts; do not initialize any accelerator."""
    started = time.monotonic()
    probe = '''import importlib.metadata as m, importlib.util as u, json, sys
from pathlib import Path
packages = {}
for name in ["hypothesis", "z3-solver", "pypdf", "pydantic", "jsonschema", "PyMuPDF", "docling", "QuantLib", "research-assistant"]:
    try: packages[name] = m.version(name)
    except m.PackageNotFoundError: packages[name] = None
modules = {}
for name in ["hypothesis", "z3", "fitz", "docling", "QuantLib", "research_assistant"]:
    spec = u.find_spec(name)
    modules[name] = spec.origin if spec else None
print(json.dumps({"executable":sys.executable,"resolved_executable":str(Path(sys.executable).resolve()),"python":sys.version,"packages":packages,"modules":modules}))
'''
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1"}
    records = []
    for python in [ROOT / ".venv/bin/python", Path(sys.executable)]:
        command = [str(python), "-c", probe]
        run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=30)
        records.append({"command": command, "returncode": run.returncode, "stderr": run.stderr,
                        "result": json.loads(run.stdout) if run.returncode == 0 else run.stdout})
    tools = {}
    for name in ["pdftotext", "pdftoppm", "tesseract", "ocrmypdf", "java", "lean", "pandoc",
                 "marker_single", "magic-pdf", "mineru", "clingo", "opa", "ra"]:
        tools[name] = {"path": shutil.which(name)}
    # The elan shim may resolve or fetch a worktree-specific toolchain. A survey
    # inventory only records its location; it must not implicitly install one.
    tools["lean"]["version_status"] = "Not probed: elan shim can resolve/download a toolchain"
    for name, flag in [("pdftotext", "-v"), ("java", "-version"), ("pandoc", "--version")]:
        if tools[name]["path"]:
            command = [tools[name]["path"], flag]
            try:
                run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=15)
                tools[name].update(command=command, returncode=run.returncode, output=run.stdout + run.stderr)
            except subprocess.TimeoutExpired:
                tools[name].update(command=command, status="TIMEOUT", seconds=15)
    retained = []
    admitted = json.loads((ROOT / "docs/prospectus/closure-2026-10-05/reviewed-extractions.json").read_text())
    for ident, row in admitted.items():
        path = ROOT / row["raw"]
        data = json.loads(path.read_text())
        retained.append({"id": ident, "path": row["raw"], "runtime": data["runtime"],
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "admitted_sha256_matches": hashlib.sha256(path.read_bytes()).hexdigest() == row["raw_sha256"],
                         "language_model": row["language_model"],
                         "language_model_sha256": hashlib.sha256((ROOT / row["language_model"]).read_bytes()).hexdigest()})
    local = []
    app = records[0]["result"]
    for name, suffix in [("hypothesis", "stateful.py"), ("z3", "z3.py")]:
        origin = app.get("modules", {}).get(name) if isinstance(app, dict) else None
        if origin:
            path = Path(origin).parent / suffix
            target = OUT / "local-code" / (name + "-" + suffix)
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(path.read_bytes())
            local.append({"source_path": str(path), "path": str(target.relative_to(ROOT)),
                          "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    ra_commit = subprocess.run(["git", "-C", str(RA), "rev-parse", "HEAD"],
                               capture_output=True, text=True, timeout=15)
    result = {"recorded_utc": datetime.now(timezone.utc).isoformat(), "interpreters": records,
              "tools": tools, "retained_ocr": retained, "local_code": local,
              "research_assistant": {"path": str(RA), "commit": ra_commit.stdout.strip(),
                                     "returncode": ra_commit.returncode,
                                     "usage": "Source import for PDF parsing and metadata discovery; no model call"},
              "gpu": "Intentionally hidden with CUDA_VISIBLE_DEVICES=-1; no GPU availability check",
              "wall_seconds": time.monotonic() - started}
    write(OUT / "environment.json", result)
    print(json.dumps({"interpreters": [r["result"] for r in records],
                      "retained_ocr_receipts_match": all(r["admitted_sha256_matches"] for r in retained)}, indent=2))


def manifest():
    """Bind acquisition, reading and environment records without claiming execution."""
    receipts = [json.loads(p.read_text()) for p in sorted((OUT / "sources").glob("*/receipt.json"))]
    ledger = json.loads((OUT / "reading-ledger.json").read_text())
    for receipt in receipts:
        receipt["reading_ids"] = [e["id"] for e in ledger["entries"]
                                  if receipt["id"] in e.get("source_ids", [])]
        receipt["disposition"] = ("FAILED_RETRIEVAL" if not receipt["format_valid"]
                                  else "See reading ledger for inspected scope" if receipt["reading_ids"]
                                  else "Navigation/discovery resource; no technical adoption claim")
    bound = []
    for item in ledger["entries"]:
        for rel in item.get("local_paths", []):
            path = ROOT / rel
            if not path.is_file():
                raise ValueError("Missing reading source: " + rel)
            bound.append({"reading_id": item["id"], "path": rel,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    resources = []
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path.name in {"source-manifest.json", "validation.json", "run-manifest.json"}:
            continue
        resources.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for rel in ["scripts/prospectus_adoption_survey.py",
                "docs/plans/prospectus-tools-survey-2026-10-07.md",
                "docs/plans/prospectus-adoption-program-2026-10-07.md"]:
        path = ROOT / rel
        resources.append({"path": rel, "bytes": path.stat().st_size,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {"schema_version": "prospectus-adoption-sources.v1", "baseline_commit": "a05e18bbd",
              "request_budget": {"ceiling": 120, "initial_discovery_charged_upper_bound": 33,
                                 "repaired_discovery_requests": 18, "initial_github_probe": 1,
                                 "direct_fetches": len(receipts), "charged_total": 52 + len(receipts),
                                 "caveat": "Logical provider/fetch attempts; HTTPS redirects may involve additional wire requests. Initial discovery's exact count unavailable."},
              "receipts": receipts, "reading_sources": bound, "resources": resources}
    write(OUT / "source-manifest.json", result)
    print(json.dumps({"direct_attempts": len(receipts), "valid_sources": sum(r["format_valid"] for r in receipts),
                      "charged_requests": result["request_budget"]["charged_total"], "bound_reading_sources": len(bound)}))


def render():
    """Render the report with explicit widths for Pandoc 2.9's pipe tables."""
    started = time.monotonic()
    command = ["pandoc", str(OUT / "SURVEY.md"), "--from=gfm", "--to=json"]
    run = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    document = json.loads(run.stdout)
    if document["pandoc-api-version"] != [1, 20]:
        raise ValueError("Review table conversion for this Pandoc API before rendering")
    for block in document["blocks"]:
        if block["t"] == "Table":
            columns = len(block["c"][2])
            block["c"][2] = {4: [0.15, 0.25, 0.25, 0.35],
                              5: [0.16, 0.23, 0.22, 0.22, 0.17]}[columns]
    pdf_command = ["pandoc", "--from=json", "--pdf-engine=xelatex", "-V", "geometry:margin=22mm",
                   "-V", "fontsize=10pt", "-V", "mainfont=DejaVu Serif", "-V", "monofont=DejaVu Sans Mono",
                   "-V", "colorlinks=true", "-o", str(OUT / "SURVEY.pdf")]
    rendered = subprocess.run(pdf_command, input=json.dumps(document), capture_output=True,
                              text=True, check=True, timeout=90)
    write(OUT / "render.json", {"commands": [command, pdf_command],
                               "pandoc_api_version": document["pandoc-api-version"],
                               "source_sha256": hashlib.sha256((OUT / "SURVEY.md").read_bytes()).hexdigest(),
                               "pdf_sha256": hashlib.sha256((OUT / "SURVEY.pdf").read_bytes()).hexdigest(),
                               "stderr": rendered.stderr, "wall_seconds": time.monotonic() - started,
                               "layout_change": "Explicit column widths; report text unchanged"})
    print(json.dumps({"status": "rendered", "path": str(OUT / "SURVEY.pdf")}))


def validate():
    started = time.monotonic()
    data = json.loads((OUT / "source-manifest.json").read_text())
    failures = []
    checks = 0
    for row in data["resources"] + data["reading_sources"]:
        path = ROOT / row["path"]
        checks += 1
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            failures.append("Source hash mismatch: " + row["path"])
    for row in data["receipts"]:
        if row["path"]:
            checks += 1
            path = ROOT / row["path"]
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                failures.append("Receipt hash mismatch: " + row["id"])
    if data["request_budget"]["charged_total"] > data["request_budget"]["ceiling"]:
        failures.append("Survey request ceiling exceeded")
    documents = list(OUT.glob("*.md")) + [ROOT / "docs/plans/prospectus-tools-survey-2026-10-07.md",
                                             ROOT / "docs/plans/prospectus-adoption-program-2026-10-07.md"]
    for path in documents:
        if not path.is_file():
            failures.append("Missing document: " + str(path))
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("https://", "http://", "#")):
                continue
            from urllib.parse import unquote
            destination = unquote(target.strip("<>").split("#", 1)[0])
            destination = re.sub(r":\d+$", "", destination)
            checks += 1
            if not (path.parent / destination).exists():
                failures.append(f"Broken local link in {path.name}: {target}")
    compile(Path(__file__).read_text(), str(Path(__file__)), "exec")
    result = {"status": "PASS" if not failures else "FAIL", "checks": checks,
              "failures": failures, "wall_seconds": time.monotonic() - started,
              "scope": "Retained hashes, local links, budget and helper syntax only; no prospectus candidate evaluation"}
    write(OUT / "validation.json", result)
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


def discover():
    sys.path.insert(0, str(RA / "src"))
    from research_assistant.survey.seed_papers import run_seed_paper_campaign
    from research_assistant.survey.seed_paper_providers import collect_live_provider_bundle
    from research_assistant.survey.topic_contract import build_topic_contract
    topic = "prospectus contract analysis"
    scope = "Focused metadata expansion; document/financial standards are searched separately. Metadata does not justify adoption."
    contract = build_topic_contract(topic, scope_note=scope)
    bundle = collect_live_provider_bundle(contract, max_requests=18,
        max_records_per_response=8, max_total_records=144)
    raw = OUT / "discovery-focused-provider-bundle.json"
    write(raw, bundle)
    result = run_seed_paper_campaign(
        topic=topic, output_dir=OUT / "discovery-focused",
        observation_bundle=raw, max_selected=16, scope_note=scope)
    print(json.dumps({k:result.get(k) for k in ("status", "budget_consumption", "limitations", "selected_count")}, indent=2))


def main():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("fetch")
    command.add_argument("id")
    command.add_argument("url")
    command.add_argument("suffix")
    sub.add_parser("parse")
    sub.add_parser("discover")
    sub.add_parser("inventory")
    sub.add_parser("manifest")
    sub.add_parser("validate")
    sub.add_parser("render")
    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.id, args.url, args.suffix)
    elif args.command == "parse":
        parse()
    elif args.command == "discover":
        discover()
    else:
        {"inventory": inventory, "manifest": manifest, "validate": validate, "render": render}[args.command]()


if __name__ == "__main__":
    main()
