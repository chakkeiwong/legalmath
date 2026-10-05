"""Resumable local BASF continuation; derives next phase from verified receipts."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, base64, fcntl, hashlib, json, os, shutil, subprocess, sys, time
from scripts import prospectus_refresh as prior
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/implementation/prospectus-basf-continuation-2026-10-05"
PLAN = ROOT / "docs/plans/prospectus-basf-continuation-2026-10-05.md"
PHASES = ("baseline", "prepare", "checks", "construct", "document", "verify")
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["OMP_THREAD_LIMIT"] = "1"
read, sha, write, require, relative = prior.read, prior.sha, prior.write, prior.require, prior.relative

def method():
    files = list((ROOT / "scripts").glob("prospectus_basf*"))
    files += list((ROOT / "tests/closure_basf").glob("test_*.py"))
    files += [PLAN, ROOT / "scripts/prospectus_refresh.py", ROOT / "scripts/prospectus_refresh_sources.py",
              ROOT / "scripts/prospectus_refresh_work.py", ROOT / "scripts/prospectus_refresh_admission.py"]
    return {relative(p): sha(p) for p in sorted(files) if p.is_file()}

def inputs(phase):
    from scripts.prospectus_basf_admission import OLD_PACKET
    from scripts.prospectus_refresh_work import sources
    files = [OLD_PACKET, prior.OUT / "run-manifest.json"]
    for key, row in sources().items():
        if key != "deutsche-at1-2025":
            files += [ROOT / row[k] for k in ("original", "text", "acquisition_receipt")]
    if phase in ("checks", "construct", "document", "verify"):
        files.append(OUT / "source-review.json")
    if phase == "verify":
        files.append(OUT / "rendered-review.json")
    return {relative(p): sha(p) for p in files}

def receipts():
    return sorted((OUT / "phases").glob("*/receipt.json"))

def latest(phase):
    matches = [p for p in receipts() if read(p)["phase"] == phase]
    return matches[-1] if matches else None

def history():
    for path in receipts():
        r = read(path)
        prior.verify_bindings(r["outputs"])
        prior.verify_bindings(r["previous_receipts"])
        prior.verify_bindings({r["snapshots"].get(p, p): h for p,h in r["inputs"].items()})
        for name, digest in r["method"].items():
            require(sha(path.parent / "method" / name) == digest, "Method snapshot changed")
    base = latest("baseline")
    if base:
        require(read(base)["status"] == "PASS", "Baseline invalid")
        prior.verify_bindings(read(base.parent / "baseline.json")["files"])

def phase_current(record, phase, methods, bound_inputs, prerequisite):
    if record["status"] != "PASS":
        return False
    if phase == "prepare":
        names = ["scripts/prospectus_basf.py", "scripts/prospectus_basf_images.py", relative(PLAN)]
        if any(record["method"].get(name) != methods.get(name) for name in names):
            return False
    elif phase != "baseline" and record["method"] != methods:
        return False
    return record["inputs"] == bound_inputs and record["prerequisite"] == prerequisite

def state():
    previous = None
    for phase in PHASES:
        path = latest(phase)
        needed_review = "source-review.json" if phase == "checks" else "rendered-review.json" if phase == "verify" else None
        if needed_review and not (OUT / needed_review).exists():
            return {"next_phase": phase, "status": "REVIEW_REQUIRED", "action": "Inspect prepared pages and record " + needed_review,
                    "command": "python3 -m scripts.prospectus_basf " + phase, "production_promotion": False}
        try:
            current_inputs = inputs(phase)
            prerequisite = {relative(previous): sha(previous)} if previous else {}
            current = path is not None and phase_current(read(path), phase, method(), current_inputs, prerequisite)
        except (ValueError, OSError):
            current = False
        if not current:
            return {"next_phase": phase, "status": "READY" if path is None else "REPAIR_OR_REFRESH_REQUIRED",
                    "command": "python3 -m scripts.prospectus_basf " + phase,
                    "action": "Execute phase; inspect latest failure before retrying." if path else "Execute phase.",
                    "production_promotion": False}
        previous = path
    return {"next_phase": None, "status": "BOUNDED_PHASES_VERIFIED", "command": None,
            "next_work_orders": relative(OUT / "remaining-gaps.json"),
            "action": "Explicit BASF selection/scope work completed; further contract construction and programme gaps remain.",
            "production_promotion": False}

def refresh():
    current = state()
    write(OUT / "next-phase.json", current)
    (OUT / "NEXT-PHASE.md").write_text("# BASF continuation: next phase\n\n" + json.dumps(current, indent=2) + "\n")
    return current

def command(argv, folder, label, timeout=180):
    start = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        log = result.stdout + result.stderr
        code = result.returncode
    except subprocess.TimeoutExpired as exc:
        log, code = str(exc), -1
    (folder / (label + ".log")).write_text(log)
    write(folder / (label + ".json"), {"command": argv, "exit_code": code,
          "wall_seconds": time.monotonic()-start, "log": relative(folder/(label+".log"))})
    require(code == 0, label + " failed; inspect preserved log")
    return log

def baseline(folder):
    prior.history()
    files = dict(read(prior.latest("baseline") / "baseline.json")["files"])
    for p in prior.OUT.rglob("*"):
        if p.is_file() and p.name != ".lock":
            files[relative(p)] = sha(p)
    prior.verify_bindings(files)
    environment = {name: subprocess.run([name, "-v"], capture_output=True, text=True).stderr.strip()
                   for name in ("pdftoppm", "pdftotext", "pdfinfo")}
    write(folder / "baseline.json", {"files": files, "count": len(files), "environment": environment,
        "requests": {"used": 188, "limit": 212, "remaining": 24}, "new_http_requests": 0})

def prepare(folder):
    from scripts.prospectus_refresh_work import sources, BASF, SUPPLEMENT, ANNUAL
    rows = sources()
    pages = {"basf-2032-final": [3,4,5,6,7],
             BASF: [108,109,110,111,112,113,114,115,118,119,120,121,122,123,124,128,129,130,131,132,133,134],
             SUPPLEMENT: [12], ANNUAL: [195,197,202,203,205,206,207,209,290]}
    records = []
    for key, numbers in pages.items():
        row = rows[key]
        for page in numbers:
            stem = folder / (key + "-" + str(page))
            command(["pdftoppm","-f",str(page),"-l",str(page),"-singlefile","-scale-to","1450","-png",
                     str(ROOT/row["original"]),str(stem)], folder, stem.name + "-render", timeout=45)
            image = stem.with_suffix(".png")
            records.append({"document": key, "page": page, "source_sha256": row["sha256"],
                            "image": relative(image), "image_sha256": sha(image)})
    write(folder / "prepared.json", records)
    # Contact sheets assist navigation; exact single pages remain available for reading.
    helper = ROOT / "scripts/prospectus_basf_images.py"
    command(["/home/chakwong/miniconda3/envs/tfgpu/bin/python", str(helper), str(folder)], folder, "contact-sheets")
    write(folder / "review-template.json", {"prepared": relative(folder/"prepared.json"),
        "prepared_sha256": sha(folder/"prepared.json"), "review_role": "development_source_review",
        "independent_legal_adjudication": False, "reviewed_pages": [], "observations": []})

def check_review():
    prepared = latest("prepare").parent / "prepared.json"
    review = read(OUT/"source-review.json")
    require(review["prepared"] == relative(prepared) and review["prepared_sha256"] == sha(prepared),
            "Stale source review")
    require(review["review_role"] == "development_source_review" and review["independent_legal_adjudication"] is False,
            "Review authority overstated")
    rows = read(prepared)
    require(sorted(review["reviewed_pages"]) == sorted([[r["document"],r["page"]] for r in rows]),
            "Source review incomplete")
    prior.verify_bindings({r["image"]:r["image_sha256"] for r in rows})
    return review

def checks(folder):
    check_review()
    command([str(ROOT/".venv/bin/python"),"-m","pytest","-q","tests/closure_basf","tests/closure_refresh",
             "tests/closure_next","--junitxml="+str(folder/"tests.xml")], folder, "tests", timeout=240)

def construct(folder):
    from scripts.prospectus_basf_admission import build_packet, consume, verify_anchors
    check_review()
    packet = build_packet()
    verify_anchors(packet)
    consumer = consume(packet)
    write(folder/"basf-selection-admission.json", packet)
    write(folder/"successor-selection-view.json", consumer)
    write(folder/"comparison.json", {"prior_selections": 21, "checkboxes": 55, "bilingual_responses": 8,
        "current_selections": len(packet["decisions"]), "report_pages": len(consumer["annual_source_pages"]),
        "full_dossier_before": "UNRESOLVED", "full_dossier_after": "UNRESOLVED",
        "comparison_role": "Coverage only; no accuracy or legal-outcome improvement inferred."})

def document(folder):
    from scripts.prospectus_basf_document import run
    run(folder)

def verify(folder):
    from scripts.prospectus_basf_document import verify as verify_document
    verify_document(folder)
    history()
    from scripts.prospectus_basf_admission import load_packet
    load_packet(read(latest("construct").parent/"basf-selection-admission.json"))
    write(folder/"verification.json", {"status":"PASS","production_promotion":False,
        "source_review":"development only","new_http_requests":0})
    write(folder/"run-manifest.json", {"git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "command":"python3 -m scripts.prospectus_basf run","python":sys.executable,"python_version":sys.version,
        "compute":"CPU; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden","seeds":"N/A deterministic",
        "plan":relative(PLAN),"plan_sha256":sha(PLAN),"result":relative(latest("document").parent/"REPORT.md"),
        "method":method(),"inputs":inputs("verify"),
        "phase_receipts":{relative(p):sha(p) for p in receipts()},
        "wall_seconds_by_phase":{p.parent.name:read(p)["wall_seconds"] for p in receipts()},
        "independent_legal_adjudication":False,"production_promotion":False})

def execute(phase):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/".lock").open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        history()
        current = state()
        require(current["next_phase"] == phase, "Execute current next phase: " + str(current))
        require(current["status"] != "REVIEW_REQUIRED", current["action"])
        previous = latest(PHASES[PHASES.index(phase)-1]) if phase != "baseline" else None
        number = len(list((OUT/"phases").glob("*"))) + 1
        folder = OUT/"phases"/f"{number:03d}-{phase}"
        folder.mkdir(parents=True)
        start = time.monotonic()
        record = {"phase":phase,"started":datetime.now(timezone.utc).isoformat(),
            "command":[sys.executable,"-m","scripts.prospectus_basf",phase],
            "git_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "python":sys.executable,"python_version":sys.version,"compute":"CPU; GPU intentionally hidden",
            "seeds":"N/A deterministic","plan":relative(PLAN),"method":method(),"inputs":inputs(phase),
            "prerequisite":{relative(previous):sha(previous)} if previous else {},
            "previous_receipts":{relative(p):sha(p) for p in receipts()},"snapshots":{},
            "result_directory":relative(folder),"new_http_requests":0}
        for name in record["method"]:
            dest = folder/"method"/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,dest)
        for name in record["inputs"]:
            if (ROOT/name).is_relative_to(OUT):
                dest = folder/"inputs"/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,dest)
                record["snapshots"][name] = relative(dest)
        try:
            globals()[phase](folder)
            record["status"] = "PASS"
        except Exception as exc:
            record.update(status="FAIL",error=type(exc).__name__ + ": " + str(exc))
            raise
        finally:
            record["wall_seconds"] = time.monotonic()-start
            record["outputs"] = {relative(p):sha(p) for p in folder.rglob("*") if p.is_file() and
                "method" not in p.relative_to(folder).parts and p.name != "receipt.json"}
            write(folder/"receipt.json",record)
            print(json.dumps(refresh(),indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=(*PHASES,"status","run","image","diagnose"))
    parser.add_argument("path",nargs="?")
    args = parser.parse_args()
    if args.phase == "image":
        path = (ROOT/args.path).resolve()
        require(path.is_relative_to(OUT) and path.suffix == ".png","Image outside continuation output")
        print(base64.b64encode(path.read_bytes()).decode())
    elif args.phase == "diagnose":
        from scripts.prospectus_basf_admission import build_packet
        p = build_packet()
        print(json.dumps({"decisions":len(p["decisions"]),"report_pages":len(p["annual_2022"]["pages"])}))
    elif args.phase == "status":
        history()
        print(json.dumps(state(),indent=2))
    elif args.phase == "run":
        while True:
            history()
            current = state()
            if current["next_phase"] is None or current["status"] == "REVIEW_REQUIRED":
                print(json.dumps(current,indent=2))
                break
            execute(current["next_phase"])
    else:
        execute(args.phase)
if __name__ == "__main__":
    main()
