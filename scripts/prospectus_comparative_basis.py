"""Bounded local IAS1/IAS8 and original Note45 continuation of source06."""
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from scripts import prospectus_historical_ifrs5 as w
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = w.BASE
PRIOR_FOLDER = w.HERE
HERE = BASE / "attempts/source-bes-dep-06/attempt-008"
REVIEW = BASE / "reviews/comparative-basis-202"
PLAN = "docs/plans/prospectus-comparative-accounting-basis-2026-10-17.md"
ROUTE = BASE / "closure-routes-2026-10-17-comparative-basis-202.json"
PROPOSAL = BASE / "proposals/comparative-basis-202.json"
REVIEW_JSON = BASE / "proposals/comparative-basis-202-review.json"
REPORT = BASE / "attempts/source-bes-dep-06/attempt-001/source-product.json.gz"
STAGES = ("prepare", "render", "profile", "answer", "controls", "seal")
PAGES = [85, 166, 167, 168, 169, 170]
PRIOR_SECONDS = 547.4019806189463
PRIOR_BYTES = 140306722
SELECTOR = {**w.SELECTOR, "version": "comparative-accounting-basis.v1", "stages": list(STAGES),
            "maximum_requests": 0, "render_children": 2, "child_seconds": 15, "render_scale": 1800,
            "report_context_occurrences": 346, "report_section_occurrences": 233,
            "new_bytes": 24 * 1024**2, "prior_inclusive_bytes": PRIOR_BYTES,
            "prior_recorded_and_preparation_seconds": PRIOR_SECONDS}
SUPPORT = (REVIEW, ROOT / PLAN, Path(__file__), ROUTE, PROPOSAL, REVIEW_JSON,
           BASE / "revisions/0202.json", BASE / "program.json")


def storage():
    new = w.path_bytes((HERE, *SUPPORT))
    return {"previous_seconds": PRIOR_SECONDS, "previous_bytes": PRIOR_BYTES,
            "new_inclusive_bytes": new, "combined_bytes": PRIOR_BYTES + new}


# Reuse immutable helpers through explicit per-package configuration, without
# modifying their file or any previous admission/result.
w.HERE, w.REVIEW, w.PLAN = HERE, REVIEW, PLAN
w.PRIOR = PRIOR_FOLDER / "answer-composition.json"
w.SELECTOR = SELECTOR
w.KEY = "comparative_accounting_basis_agent_reading"
w.STAGES = STAGES
w.storage = storage


def prepare():
    refs = w.prepare()
    manifest = w.read(PRIOR_FOLDER / "sources.json")
    selected = {k: manifest[k] for k in ("eu1126_original", "eu1126_20091227")}
    w.save("source-selections.json", {k: {"units_path": v["units_path"], "units_sha256": v["units_sha256"]} for k, v in selected.items()})
    w.save("sources.json", selected)
    product = w.load(REPORT)
    units = [u for u in product["payload"]["graph"]["units"] if u["document"] == "bes-report-2009" and u["page"] in PAGES]
    w.require(len(units) == 346, "Complete six-page report context required")
    w.save("report-units.json.gz", units)
    w.rawsave("report-native.txt", ("\n".join(u["id"] + " " + u["raw"] for u in units) + "\n").encode())
    source = next(d for d in product["payload"]["request"]["bundle"]["documents"] if d["id"] == "bes-report-2009")
    w.require(w.file_hash(ROOT / source["path"]) == source["sha256"], "Original2009 source PDF changed")
    renderer = w.read(REVIEW / "history.json")["renderer"]
    specs = []
    for first, last in ((85, 85), (166, 170)):
        prefix = "comparative-context-" + str(first)
        specs.append({"source": source, "renderer": renderer, "prefix": prefix, "pages": list(range(first, last + 1)),
                      "argv": [renderer["path"], "-f", str(first), "-l", str(last), "-scale-to", "1800", "-gray", "-png",
                               str(ROOT / source["path"]), str(HERE / prefix)]})
    w.save("render-spec.json", specs)
    return {**refs, "report_context_occurrences": len(units), "new_text_extractions": 0, "network_calls": 0}


def render():
    images = []
    for spec in w.read(HERE / "render-spec.json"):
        w.require(w.file_hash(ROOT / spec["source"]["path"]) == spec["source"]["sha256"]
                  and w.file_hash(Path(spec["renderer"]["path"])) == spec["renderer"]["sha256"], "Render inputs changed")
        with (HERE / (spec["prefix"] + ".stdout")).open("xb") as out, (HERE / (spec["prefix"] + ".stderr")).open("xb") as err:
            child = subprocess.run(spec["argv"], stdout=out, stderr=err, timeout=15, env=dict(os.environ))
        paths = sorted(HERE.glob(spec["prefix"] + "-*.png"))
        w.require(child.returncode == 0 and [int(p.stem.split("-")[-1]) for p in paths] == spec["pages"], "Complete expected report images required")
        images += [{"document": "bes-report-2009", "page": int(p.stem.split("-")[-1]),
                    "path": str(p.relative_to(ROOT)), "sha256": w.file_hash(p)} for p in paths]
    w.save("images.json", images)
    return {"images": len(images), "children": 2}


def run(stage):
    with w.Authority(ROOT).lock():
        admitted = w.bindings()
        index = STAGES.index(stage)
        w.require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                  {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                  "Repeated/skipped/interrupted comparative-basis stage")
        rows = [w.read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        w.require(all(r["status"] == "PASS" and r["wall_seconds"] < 50 for r in rows), "Failed comparative predecessor")
        spent = w.read(REVIEW / "history.json")["preparation_seconds"] + sum(r["wall_seconds"] for r in rows)
        def within(elapsed=0):
            now = storage()
            return spent + elapsed < 300 and PRIOR_SECONDS + spent + elapsed < 1080 and \
                now["new_inclusive_bytes"] < 24 * 1024**2 - 256 * 1024 and now["combined_bytes"] < 160 * 1024**2 - 1024**2
        w.require(within(), "Original cumulative comparative bounds exhausted")
        w.save("stages/" + stage + "/started.json", {"command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_comparative_basis", stage],
               "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
               "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic source reading",
               "plan": PLAN, "data_version": [str(REPORT.relative_to(ROOT)), str(PRIOR_FOLDER.relative_to(ROOT))],
               "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("Comparative-basis cumulative deadline; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(45, 300 - spent, 1080 - PRIOR_SECONDS - spent))
        try:
            commands = [s["argv"] for s in w.read(HERE / "render-spec.json")] if stage == "render" else []
            with execution_guard(commands) as guard:
                details = prepare() if stage == "prepare" else render() if stage == "render" else getattr(w, stage)()
            w.require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected comparative process/network action")
            details["process_guard"] = guard.result()
            w.bindings()
            w.require(time.monotonic() - tick < 50 and within(time.monotonic() - tick), "Comparative cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            w.save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
                  "wall_seconds": time.monotonic() - tick, "bounds": storage()}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        w.save("stages/" + stage + "/result.json", result)
        if error or stage == "seal":
            w.save("result.json", {**result, "task": "source-bes-dep-06", "task_complete": False,
                                  "whole_program_complete": False, "independent_legal_acceptance": False})
            w.save("outputs.json", w.files(HERE))
        print(w.json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
