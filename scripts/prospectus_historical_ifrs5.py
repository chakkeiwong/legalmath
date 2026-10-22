"""One bounded historical-accounting source reading; no product acceptance."""
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import traceback
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-06/attempt-007"
PREVIOUS = tuple(HERE.parent / ("attempt-" + str(i).zfill(3)) for i in range(3, 7))
PRIOR = PREVIOUS[-1] / "answer-composition.json"
EPS = BASE / "attempts/source-bes-dep-07/attempt-007/answer-composition.json"
REVIEW = BASE / "reviews/historical-ifrs5-201"
DISCOVERY = BASE / "continuation-reviews/2026-10-17-after-compact200"
PLAN = "docs/plans/prospectus-historical-ifrs5-2026-10-17.md"
ROUTE = BASE / "closure-routes-2026-10-17-historical-ifrs5-201.json"
PROPOSAL = BASE / "proposals/historical-ifrs5-201.json"
REVIEW_JSON = BASE / "proposals/historical-ifrs5-201-review.json"
SUPPORT = (REVIEW, DISCOVERY, ROOT / PLAN, Path(__file__), ROUTE, PROPOSAL,
           REVIEW_JSON, BASE / "revisions/0201.json", BASE / "program.json")
STAGES = ("prepare", *("acquire" + str(i).zfill(2) for i in range(1, 13)),
          "sources", "profile", "answer", "controls", "seal")
KEY = "historical_ifrs5_agent_reading"
SELECTOR = {"version": "historical-ifrs5-source-reading.v1", "stages": list(STAGES),
            "maximum_requests": 12, "request_seconds": 15, "connect_seconds": 5,
            "maximum_redirects": 4, "raw_response_bytes": 8 * 1024**2,
            "minimum_semantic_controls": 16, "new_seconds": 300,
            "combined003_007_seconds": 1080, "new_bytes": 32 * 1024**2,
            "combined003_007_bytes": 160 * 1024**2, "new_reserve_bytes": 256 * 1024,
            "combined_reserve_bytes": 1024**2, "work_seconds": 45, "stage_seconds": 50,
            "OCR_model_GPU_install_production_edits_unchanged_retries": 0}
LIMITS = {"accounting_compliance_determined": False, "dated_Portuguese_law_checked": False,
          "source_authenticity_established": False, "independent_acceptance": False,
          "production_integration": False, "automatic_discovery": False,
          "controlling_edition_selected": False, "individual_asset_flows_established": False,
          "financial_values_validated": False, "BES_Finance_standalone_accounts_supplied": False}


def path_bytes(paths):
    found = {}
    for path in paths:
        for p in path.rglob("*") if path.is_dir() else (path,):
            if p.is_file() and "__pycache__" not in p.parts:
                found[str(p)] = p.stat().st_size
    return sum(found.values())


def storage():
    old = path_bytes(PREVIOUS)
    new = path_bytes((HERE, *SUPPORT))
    return {"previous_seconds": sum(read(p)["wall_seconds"] for d in PREVIOUS
                                     for p in (d / "stages").glob("*/result.json")),
            "previous_bytes": old, "new_inclusive_bytes": new, "combined_bytes": old + new}


def rawsave(name, raw):
    now = storage()
    require(now["new_inclusive_bytes"] + len(raw) < SELECTOR["new_bytes"] - SELECTOR["new_reserve_bytes"]
            and now["combined_bytes"] + len(raw) < SELECTOR["combined003_007_bytes"] - SELECTOR["combined_reserve_bytes"],
            "Inclusive historical-source storage exhausted")
    p = HERE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as stream:
        stream.write(raw)


def save(name, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    rawsave(name, gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw + b"\n")


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-06"]
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
            and task.get("historical_ifrs5_reading") == SELECTOR and admitted["task_spec"] == task
            and admitted["program_sha256"] == digest(program) and admitted["binding"] == a.binding(task),
            "Current unchanged historical IFRS5 admission required")
    require(not (HERE / "outputs.json").exists(), "Historical IFRS5 attempt already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p, h in history["protected"].items()), "Retained source evidence changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Current production changed")
    if (HERE / "reading-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p, h in read(HERE / "reading-methods.json").items()),
                "Frozen historical IFRS5 reading changed")
    return admitted


def published_links(raw):
    try:
        doc = ET.fromstring(raw)
    except ET.ParseError:
        parser = TextBlocks()
        parser.feed(raw.decode("utf-8-sig"))
        return set(parser.links)
    return {v for el in doc.iter() for k, v in el.attrib.items()
            if k.rsplit("}", 1)[-1] in {"resource", "about", "href"} and v.startswith(("https://", "http://"))}


def response_raw(path):
    raw = path.read_bytes()
    return gzip.decompress(raw) if path.suffix == ".gz" else raw


def request_spec(stage):
    spec = read(HERE / ("requests/" + stage + ".json"))
    if spec.get("unused"):
        require(set(spec) == {"unused", "reason"} and spec["reason"], "Unused request needs an actual reason")
        return spec, None
    require(set(spec) == {"parent", "parent_sha256", "published_url", "url", "accept"}, "Unexpected source request fields")
    parent = ROOT / spec["parent"]
    eligible = {str((DISCOVERY / ("discovery-official-" + n)).relative_to(ROOT)) for n in ("06.html", "08.rdf")}
    eligible.update(str(p.relative_to(ROOT)) for p in (HERE / "responses").glob("*/body.gz"))
    require(spec["parent"] in eligible and file_hash(parent) == spec["parent_sha256"], "Request parent missing or changed")
    require(spec["published_url"] in published_links(response_raw(parent)), "Request is not a published resource link")
    require(spec["url"] == spec["published_url"].replace("http://", "https://", 1), "Unreviewed URL transformation")
    parsed = urlparse(spec["url"])
    require(parsed.scheme == "https" and parsed.hostname == "publications.europa.eu"
            and parsed.path.startswith("/resource/") and not parsed.username and not parsed.password
            and spec["accept"] in {"application/rdf+xml", "application/xhtml+xml", "text/html", "application/pdf"},
            "Request outside the reviewed official-public-resource scope")
    previous = [read(p) for p in (HERE / "responses").glob("*/receipt.json")]
    require(len(previous) < 12 and spec["url"] not in {p["requested_url"] for p in previous}, "Request allowance or unchanged retry refused")
    argv = ["/usr/bin/curl", "--silent", "--show-error", "--location", "--connect-timeout", "5",
            "--max-time", "15", "--max-redirs", "4", "--proto", "=http,https", "--proto-redir", "=http,https",
            "--header", "Accept: " + spec["accept"], "--dump-header", str(HERE / ("responses/" + stage + "/headers.txt")),
            "--write-out", "%{stderr}\n%{json}\n", spec["url"]]
    return spec, argv


def prepare():
    for name, path in (("baseline-composition-reference.json", PRIOR), ("EPS-composition-reference.json", EPS)):
        save(name, {"path": str(path.relative_to(ROOT)), "sha256": file_hash(path),
                    "complete_composed_answer_sha256": read(path)["complete_composed_answer_sha256"]})
    return {"baseline": "source06/006 full composition", "EPS": "source07/007 full composition",
            "maximum_new_requests": 12, "large_answer_copies": 0}


def acquire(stage, spec, argv):
    save("requests/" + stage + "-frozen.json", {"spec": spec, "sha256": digest(spec), "argv": argv})
    if argv is None:
        return {"request_sent": False, "reason": spec["reason"]}
    dest = HERE / "responses" / stage
    dest.mkdir(parents=True, exist_ok=True)
    body = bytearray()
    capped = False
    tick = time.monotonic()
    with (dest / "stderr.txt").open("xb") as err:
        child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=err)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                while True:
                    if time.monotonic() - tick > 18:
                        raise TimeoutError("Official request exceeded bounded curl lifetime")
                    if not selector.select(0.2):
                        continue
                    chunk = os.read(child.stdout.fileno(), min(65536, SELECTOR["raw_response_bytes"] + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > SELECTOR["raw_response_bytes"]:
                        capped = True
                        child.kill()
                        break
            code = child.wait(timeout=3)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=3)
            child.stdout.close()
    require((dest / "headers.txt").stat().st_size < 65536 and (dest / "stderr.txt").stat().st_size < 65536,
            "Unexpected oversized request diagnostics")
    rawsave("responses/" + stage + "/body.gz", gzip.compress(bytes(body), mtime=0))
    diagnostics = (dest / "stderr.txt").read_text(errors="replace").splitlines()
    info = next((json.loads(line) for line in reversed(diagnostics) if line.startswith("{") and line.endswith("}")), {})
    receipt = {"requested_url": spec["url"], "published_url": spec["published_url"], "accept": spec["accept"],
               "parent": spec["parent"], "parent_sha256": spec["parent_sha256"], "curl_exit": code,
               "http_status": info.get("http_code"), "effective_url": info.get("url_effective"),
               "redirects": info.get("num_redirects"), "actual_raw_bytes_retained": len(body),
               "raw_sha256": hashlib.sha256(body).hexdigest(), "complete_transport": code == 0 and not capped,
               "raw_cap_exceeded": capped, "request_seconds": time.monotonic() - tick,
               "substantive_authority_verified": False}
    save("responses/" + stage + "/receipt.json", receipt)
    return receipt


class TextBlocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.units, self.links = [], [], []
        self.anchor, self.ignore = None, 0

    def flush(self):
        text = " ".join("".join(self.parts).split())
        if text:
            self.units.append({"order": len(self.units), "anchor": self.anchor, "text": text})
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.ignore += 1
        if tag in {"p", "div", "tr", "td", "th", "h1", "h2", "h3", "h4", "li", "br"}:
            self.flush()
        if "id" in attrs:
            self.anchor = attrs["id"]
        if "href" in attrs:
            self.links.append(attrs["href"])

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignore = max(0, self.ignore - 1)
        if tag in {"p", "div", "tr", "td", "th", "h1", "h2", "h3", "h4", "li"}:
            self.flush()

    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def sources():
    selected = read(HERE / "source-selections.json")
    require(selected and isinstance(selected, dict), "Actual acquired source selections required")
    manifest = {}
    for name, stage in selected.items():
        receipt = read(HERE / ("responses/" + stage + "/receipt.json"))
        require(receipt["complete_transport"] and receipt["http_status"] == 200, "Incomplete transport cannot be source text")
        raw = response_raw(HERE / ("responses/" + stage + "/body.gz"))
        require(hashlib.sha256(raw).hexdigest() == receipt["raw_sha256"], "Source response changed")
        try:
            xml = ET.fromstring(raw)
        except ET.ParseError:
            xml = None
        require(xml is None or xml.tag.rsplit("}", 1)[-1] != "RDF", "Metadata is not accounting text")
        parser = TextBlocks()
        parser.feed(raw.decode("utf-8-sig"))
        parser.flush()
        require(len(parser.units) > 100 and any("IFRS 5" in u["text"] for u in parser.units), "Full accounting text not established")
        for unit in parser.units:
            unit["id"] = name + ":u" + str(unit["order"]).zfill(5)
        save("sources/" + name + "-units.json.gz", parser.units)
        manifest[name] = {"request": stage, "receipt": receipt, "units": len(parser.units),
                          "units_path": str((HERE / ("sources/" + name + "-units.json.gz")).relative_to(ROOT)),
                          "units_sha256": file_hash(HERE / ("sources/" + name + "-units.json.gz"))}
    save("sources.json", manifest)
    return {"acquired_texts": len(manifest), "parsed_units": {k: v["units"] for k, v in manifest.items()}}


def evaluator():
    spec = importlib.util.spec_from_file_location("historical_ifrs5_reading", HERE / "reading.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value, pin):
    require(digest(value) == pin, "Historical IFRS5 profile pin changed")
    require(value["version"] == SELECTOR["version"] and value["limits"] == LIMITS, "Historical IFRS5 conclusion limits required")
    require(value["baseline"] == read(HERE / "baseline-composition-reference.json")
            and value["EPS"] == read(HERE / "EPS-composition-reference.json"), "Both complete answer references required")
    manifest = read(HERE / "sources.json")
    require(all(file_hash(ROOT / v["units_path"]) == v["units_sha256"] for v in manifest.values()), "Parsed source changed")
    return evaluator().evaluate({k: load(ROOT / v["units_path"]) for k, v in manifest.items()}, value["reading"])


def profile():
    names = ("reading.py", "prepare-reading.py", "SOURCE-REVIEW.md", "IMPLEMENTATION-REVIEW.md", "draft-profile.json")
    require(all((HERE / n).is_file() for n in names), "Actual complete-source and implementation readings required")
    paths = [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md", HERE / "source-selections.json", HERE / "sources.json"]
    paths += [HERE / name for name in names]
    paths += list((HERE / "requests").glob("*.json")) + list((HERE / "responses").glob("*/*"))
    save("reading-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in paths})
    value = read(HERE / "draft-profile.json")
    analysis = validate(value, digest(value))
    require(len(evaluator().CASES) >= 16, "At least sixteen semantic controls required")
    save("profile.json", value)
    save("profile-pin.json", {"sha256": digest(value)})
    save("intended-refusals.json", evaluator().CASES)
    return {"frozen": True, "semantic_controls": len(evaluator().CASES), "analysis": analysis}


def compose(path):
    meta = read(path)
    if "baseline_composition" in meta:
        ref = meta["baseline_composition"]
        require(file_hash(ROOT / ref["path"]) == ref["sha256"], "Baseline composition changed")
        baseline = compose(ROOT / ref["path"])
        require(digest(baseline) == ref["complete_composed_answer_sha256"], "Baseline composed content changed")
    else:
        ref = meta["baseline"]
        require(file_hash(ROOT / ref["path"]) == ref["file_sha256"], "Baseline answer changed")
        baseline = load(ROOT / ref["path"])
        require(digest(baseline) == ref["content_sha256"], "Baseline answer content changed")
    overlay = meta["overlay"]
    require(file_hash(ROOT / overlay["path"]) == overlay["file_sha256"], "Answer overlay changed")
    addition = load(ROOT / overlay["path"])
    require(digest(addition) == overlay["content_sha256"] and not (set(baseline) & set(addition)), "Invalid answer overlay")
    result = {**baseline, **addition}
    require(digest(result) == meta["complete_composed_answer_sha256"], "Complete answer changed")
    return result


def answer():
    value = read(HERE / "profile.json")
    analysis = validate(value, read(HERE / "profile-pin.json")["sha256"])
    baseline = compose(PRIOR)
    eps = compose(EPS)
    unresolved = {"BES-DEP-" + str(i).zfill(2) for i in range(1, 12)} | {"BES-DEP-AGENCY-" + str(i).zfill(2) for i in range(1, 4)}
    require({d["id"] for d in baseline["dependencies"] if d["id"] in unresolved and d["status"] == "UNRESOLVED"} == unresolved
            and baseline["questions"]["Q3"]["status"] == "PARTIAL", "Original BES dependency and question limits required")
    require(KEY not in baseline, "Historical IFRS5 field already present")
    overlay = {KEY: {"profile": value, "analysis": analysis, "sources": read(HERE / "sources.json"), "limits": LIMITS}}
    save("answer-overlay.json.gz", overlay)
    save("analysis.json", analysis)
    combined = {**baseline, **overlay}
    require(all(combined[k] == baseline[k] for k in baseline), "Complete previous answer changed")
    save("answer-composition.json", {"baseline_composition": read(HERE / "baseline-composition-reference.json"),
         "overlay": {"path": str((HERE / "answer-overlay.json.gz").relative_to(ROOT)),
                     "file_sha256": file_hash(HERE / "answer-overlay.json.gz"), "content_sha256": digest(overlay)},
         "complete_composed_answer_sha256": digest(combined), "EPS_full_composed_sha256": digest(eps),
         "complete_prior_answer_preserved": True, "EPS_full_composition_verified": True,
         "large_answer_copies": 0, "original_BES_dependencies_unresolved": 14, "Q3": "PARTIAL"})
    return {"full_prior_answer_preserved": True, "full_EPS_answer_preserved": True, "large_answer_copies": 0}


def controls():
    value, method = read(HERE / "profile.json"), evaluator()
    results = []
    for name, expected in read(HERE / "intended-refusals.json").items():
        bad = method.altered(value, name)
        pin = digest(bad)
        save("adverse-inputs/" + name + ".json.gz", {"profile": bad, "expected_pin": pin})
        try:
            validate(bad, pin)
        except ValueError as exc:
            require(str(exc) == expected, "Wrong historical IFRS5 semantic refusal: " + name + ": " + str(exc))
            row = {"case": name, "refused": True, "repinned": True, "reason": str(exc)}
            save("adverse-results/" + name + ".json", row)
            results.append(row)
        else:
            raise ValueError("Changed historical IFRS5 reading accepted: " + name)
    save("actual-controls.json", results)
    return {"actual_semantic_refusals": len(results), "freshly_repinned": len(results)}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual historical IFRS5 result required")
    controls = read(HERE / "actual-controls.json")
    expected = read(HERE / "intended-refusals.json")
    require(len(controls) == len(expected) >= 16 and {r["case"] for r in controls} == set(expected)
            and all(r["refused"] and r["repinned"] and r["reason"] == expected[r["case"]] for r in controls),
            "Complete actual semantic refusal evidence required")
    save("verified-result.json", {**read(HERE / "answer-composition.json"), "actual_refusals": len(controls),
                                 "task_complete": False, "result_sha256": file_hash(HERE / "RESULT.md")})
    return {"conditional_accounting_source_reading_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Repeated/skipped/interrupted historical IFRS5 stage")
        previous = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in previous), "Failed predecessor")
        preflight = read(REVIEW / "history.json")["preparation_seconds"]
        spent = preflight + sum(r["wall_seconds"] for r in previous)
        before = storage()
        def within(now, elapsed=0):
            return spent + elapsed < 300 and now["previous_seconds"] + spent + elapsed < 1080 and \
                now["new_inclusive_bytes"] < SELECTOR["new_bytes"] - SELECTOR["new_reserve_bytes"] and \
                now["combined_bytes"] < SELECTOR["combined003_007_bytes"] - SELECTOR["combined_reserve_bytes"]
        require(within(before), "Cumulative historical IFRS5 bounds exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_historical_ifrs5", stage],
             "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
             "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic source reading",
             "plan": PLAN, "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Historical IFRS5 cumulative bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 300 - spent, 1080 - before["previous_seconds"] - spent))
        try:
            spec, argv = request_spec(stage) if stage.startswith("acquire") else (None, None)
            with execution_guard([argv] if argv else []) as guard:
                details = acquire(stage, spec, argv) if stage.startswith("acquire") else globals()[stage]()
            require(guard.result() == {"starts": 1 if argv else 0, "blocked": 0}, "Unexpected historical IFRS5 process/network action")
            details["process_guard"] = guard.result()
            bindings()
            require(time.monotonic() - tick < 50 and within(storage(), time.monotonic() - tick), "Historical IFRS5 cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
                  "wall_seconds": time.monotonic() - tick, "bounds": storage()}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result)
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-06", "task_complete": False,
                                 "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
