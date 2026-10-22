"""Bounded complete original Statements reading and agent answer supplement."""
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-05/attempt-015"
PRIOR = HERE.parent / "attempt-014"
SCOPE = HERE.parent / "attempt-007"
REVIEW = BASE / "reviews/h1-statements-171"
PLAN = "docs/plans/prospectus-h1-statements-2026-10-16.md"
STAGES = ("prepare", "render_statements", "render_auditor", "profile", "answer", "controls", "seal")
SELECTOR = {"version": "bes-h1-statements-agent-reading.v1", "stages": list(STAGES), "work_seconds": 110,
    "stage_seconds": 115, "execution_seconds": 600, "combined006_015_seconds": 1800,
    "combined006_015_bytes": 700*1024**2, "new_bytes": 50*1024**2,
    "render_children": 2, "rendered_pages": [56,57,58,172,173], "source_pages": [56,57,58,172,173], "child_seconds": 100,
    "extraction_ocr_network_model_gpu_install_production_edits": 0, "unchanged_retries": 0,
    "minimum_semantic_controls": 20}
LIMITS = {"financial_values_validated": False, "source_authenticity_established": False,
    "independent_statutory_interpretation": False, "independent_accounting_standards_interpretation": False,
    "actuarial_valuation_reproduced": False,
    "independent_legal_acceptance": False, "actual_incorporation_resolved": False,
    "production_integration_claimed": False, "automatic_extraction": False,
    "BES_Finance_standalone_accounts_supplied": False, "note_coupon_established": False}


def save(name, value):
    p = HERE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with p.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if p.suffix == ".gz" else raw+b"\n")


def storage():
    old = [HERE.parent / ("attempt-"+str(i).zfill(3)) for i in range(6,15)]
    envs = [Path(read(p / "workspace.json")["directory"]) for p in old if (p / "workspace.json").exists()]
    return {"previous_seconds": sum(read(p / "result.json")["cumulative_seconds"] for p in old),
        "combined_bytes": sum(f.stat().st_size for p in [*old,HERE,*envs] for f in p.rglob("*") if f.is_file()),
        "new_bytes": sum(f.stat().st_size for f in HERE.rglob("*") if f.is_file())}


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task, admitted = tasks["source-bes-dep-05"], read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and task.get("statements_reading") == SELECTOR and admitted["program_sha256"] == digest(program)
        and admitted["task_spec"] == task and admitted["binding"] == a.binding(task), "Current unchanged Statements admission required")
    require(not (HERE / "outputs.json").exists(), "Statements already sealed")
    history = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == h for p,h in history["protected"].items()), "Historical evidence changed")
    require(files(ROOT / "src/legalmath") == history["package"], "Production files changed")
    if (HERE / "reading-methods.json").exists():
        require(all(file_hash(ROOT / p) == h for p,h in read(HERE / "reading-methods.json").items()), "Frozen note method/source review changed")
    return admitted


def prepare():
    products = load(SCOPE / "products.json.gz")
    pages = SELECTOR["source_pages"]
    units = [u for u in products["P1"]["payload"]["graph"]["units"] if u["document"] == "bes-interim-h1-2010" and u["page"] in pages]
    require(len(units) == 533 and len({u["id"] for u in units}) == 533, "Complete533 original occurrences required")
    save("source-units.json", units)
    (HERE / "native-note.txt").write_text("\n".join(u["id"]+" "+u["raw"] for u in units)+"\n")
    source = read(SCOPE / "rendered-source.json")["report"]
    require(file_hash(ROOT / source["path"]) == source["sha256"], "Original PDF changed")
    renderer = Path(shutil.which("pdftoppm")).resolve(strict=True)
    for name, first, last in (("statements",56,58),("auditor",172,173)):
        save("render-"+name+"-spec.json", {"source":source,"renderer":str(renderer),"renderer_sha256":file_hash(renderer),
            "pages":list(range(first,last+1)),"argv":[str(renderer),"-f",str(first),"-l",str(last),"-scale-to","2600","-png",str(ROOT/source["path"]),str(HERE/("statements-"+name))]})
    return {"source_occurrences":533,"pages":pages}


def render_part(name):
    spec=read(HERE/("render-"+name+"-spec.json"))
    require(file_hash(ROOT/spec["source"]["path"])==spec["source"]["sha256"] and file_hash(Path(spec["renderer"]))==spec["renderer_sha256"],"Pinned original PDF/renderer required")
    save("render-"+name+"-started.json",{"argv":spec["argv"],"timeout_seconds":100,"source_mutation":False})
    tick=time.monotonic()
    with (HERE/("render-"+name+".stdout")).open("xb") as out,(HERE/("render-"+name+".stderr")).open("xb") as err:
        completed=subprocess.run(spec["argv"],stdout=out,stderr=err,timeout=100,env=dict(os.environ))
    save("render-"+name+"-result.json",{"returncode":completed.returncode,"wall_seconds":time.monotonic()-tick})
    images=sorted(HERE.glob("statements-"+name+"-*.png"))
    require(completed.returncode==0 and [int(p.stem.split("-")[-1]) for p in images]==spec["pages"],"Exactly the admitted original pages required")
    save("images-"+name+".json",[{"page":int(p.stem.split("-")[-1]),"path":str(p.relative_to(ROOT)),"sha256":file_hash(p)} for p in images])
    return {"rendered_pages":len(images),"new_text_extractions":0}


def render_statements():
    return render_part("statements")


def render_auditor():
    result=render_part("auditor")
    images=read(HERE/"images-statements.json")+read(HERE/"images-auditor.json")
    save("images.json",sorted(images,key=lambda i:i["page"]))
    return result


def evaluator():
    path = HERE / "reading.py"
    spec = importlib.util.spec_from_file_location("statements_finite_reading", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(value, pin):
    units = read(HERE / "source-units.json")
    require(digest(value) == pin, "Statements profile pin changed")
    require(value["version"] == SELECTOR["version"] and value["limits"] == LIMITS, "Statements cannot establish unsupported authority or integration")
    require(value["source_units"] == [{"id": u["id"], "quote": u["raw"]} for u in units], "Complete original533 quotes required")
    require(value["images"] == read(HERE / "images.json") and all(file_hash(ROOT / i["path"]) == i["sha256"] for i in value["images"]), "Original note images changed")
    require(value["prior_sha256"] == file_hash(PRIOR / "answer-supplement.json.gz"), "Complete previous answer changed")
    return evaluator().evaluate(units, value["reading"])


def profile():
    for name in ("SOURCE-REVIEW.md", "IMPLEMENTATION-REVIEW.md", "draft-profile.json", "reading.py"):
        require((HERE / name).is_file(), "Complete source-specific reading and review required")
    methods = [Path(__file__), ROOT / PLAN, REVIEW / "REVIEW.md", HERE / "SOURCE-REVIEW.md",
        HERE / "IMPLEMENTATION-REVIEW.md", HERE / "reading.py", HERE / "draft-profile.json", HERE / "source-units.json", HERE / "images.json"]
    save("reading-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in methods})
    value = read(HERE / "draft-profile.json")
    validate(value, digest(value))
    controls = evaluator().CASES
    require(isinstance(controls, dict) and len(controls) >= 20, "At least twenty predeclared semantic controls required")
    save("profile.json", value)
    save("profile-pin.json", {"sha256": digest(value)})
    save("intended-refusals.json", controls)
    return {"reading_frozen": True, "controls": len(controls)}


def answer():
    value = read(HERE / "profile.json")
    result = validate(value, read(HERE / "profile-pin.json")["sha256"])
    prior = load(PRIOR / "answer-supplement.json.gz")
    original = {"BES-DEP-"+str(i).zfill(2) for i in range(1,12)} | {"BES-DEP-AGENCY-"+str(i).zfill(2) for i in range(1,4)}
    deps = prior["answer"]["dependencies"]
    require(len(deps) == 432 and len([d for d in deps if d["id"] in original and d["status"] == "UNRESOLVED"]) == 14
        and prior["answer"]["questions"]["Q3"]["status"] == "PARTIAL", "Original unresolved answer required")
    result["conditional_scope"] = [{"construction": c["id"], "consolidated_statements_and_limited_review_included": set(SELECTOR["source_pages"]) <= set(c["pages"])} for c in prior["h1_scope_review"]["candidates"]]
    result["limits"] = LIMITS
    result["statement_readings"] = {"56": "CURRENT_SUPPLIED_READING", "57": "CURRENT_SUPPLIED_READING", "58": "CURRENT_SUPPLIED_READING", "172-173": "CURRENT_SUPPLIED_LIMITED_REVIEW_READING", "59": "PRIOR_TRUNCATION_LIMITS_RETAINED"}
    supplement = {**prior, "h1_statements_agent_reading": {"source_units": read(HERE / "source-units.json"), "profile": value, "analysis": result}}
    require({k:supplement[k] for k in prior} == prior, "Complete old answer changed")
    save("answer-supplement.json.gz", supplement)
    save("analysis.json", result)
    save("comparison.json", {"complete_prior_consumer_equal": True, "source_occurrences": 533,
        "original_BES_dependencies_unresolved": 14, "Q3": "PARTIAL", "supplement_sha256": digest(supplement)})
    return {"complete_prior_consumer_equal": True, "statements_source_reading_added": True}


def controls():
    good = read(HERE / "profile.json")
    module, results = evaluator(), []
    for name, reason in read(HERE / "intended-refusals.json").items():
        altered = module.altered(good, name)
        pin = digest(altered)
        save("adverse-inputs/"+name+".json", {"profile": altered, "expected_pin": pin})
        try:
            validate(altered, pin)
        except ValueError as exc:
            row = {"case": name, "refused": True, "repinned": True, "reason": str(exc)}
            save("adverse-results/"+name+".json", row)
            require(str(exc) == reason, "Unintended Statements refusal: "+name+": "+str(exc))
            results.append(row)
        else:
            raise ValueError("Changed Statements reading accepted: "+name)
    save("actual-controls.json", results)
    return {"actual_refusals": len(results), "repinned": len(results)}


def seal():
    require((HERE / "RESULT.md").exists(), "Actual Statements result analysis required")
    controls = read(HERE / "actual-controls.json")
    require(len(controls) >= 20 and all(r["reason"] == read(HERE / "intended-refusals.json")[r["case"]] for r in controls), "Complete intended refusals required")
    save("verified-result.json", {**read(HERE / "comparison.json"), "actual_refusals": len(controls),
        "task_complete": False, "result_sha256": file_hash(HERE / "RESULT.md")})
    return {"statements_reading_retained": True, "task_complete": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
            {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted note stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed note predecessor")
        spent, limits = sum(r["wall_seconds"] for r in rows), storage()
        require(spent < 600 and limits["previous_seconds"]+spent < 1800 and limits["new_bytes"] < 49*1024**2
            and limits["combined_bytes"] < 698*1024**2, "Cumulative note bounds exhausted")
        save("stages/"+stage+"/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m", "scripts.prospectus_h1_statements", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic supplied note reading",
            "plan": PLAN, "data_version": str((PRIOR / "outputs.json").relative_to(ROOT)), "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame): raise TimeoutError("Statements time bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110,600-spent,1800-limits["previous_seconds"]-spent))
        try:
            commands = [read(HERE / ("render-"+stage.removeprefix("render_")+"-spec.json"))["argv"]] if stage.startswith("render_") else []
            with execution_guard(commands) as guard:
                details = globals()[stage]()
                require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            details["process_guard"] = guard.result()
            bindings()
            elapsed, current = time.monotonic()-tick, storage()
            require(elapsed < 115 and spent+elapsed < 600 and limits["previous_seconds"]+spent+elapsed < 1800
                and current["new_bytes"] < 49*1024**2 and current["combined_bytes"] < 698*1024**2, "Note bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/"+stage+"/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic()-tick, "bounds": storage()}
        result["cumulative_seconds"] = spent+result["wall_seconds"]
        save("stages/"+stage+"/result.json", result)
        if error or stage == "seal":
            save("result.json", {**result, "task": "source-bes-dep-05", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k:result[k] for k in ("stage","status","error","wall_seconds","cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "Choose Statements prepare/render_statements/render_auditor/profile/answer/controls/seal")
    raise SystemExit(run(sys.argv[1]))
