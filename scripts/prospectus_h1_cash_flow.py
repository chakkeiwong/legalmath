"""Admitted source-complete H1 cash-flow reading, replay and offline installation."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1",
    PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from legalmath.prospectus.execution_acceptance import checked_tests
from legalmath.prospectus.successor import service, process_ledger
from legalmath.prospectus.successor.contracts import digest as product_digest
from scripts.prospectus_installed_profile_worker import execution_guard
from scripts.prospectus_basf_pension_source import files, load, require
from scripts.prospectus_basf_pension_install import dependencies

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
HERE = BASE / "attempts/source-bes-dep-05/attempt-005"
ORIGINAL = HERE.parent / "attempt-001"
PRIOR = HERE.parent / "attempt-004"
REVIEW = BASE / "reviews/h1-cash-flow-161"
PLAN = "docs/plans/prospectus-h1-cash-flow-2026-10-16.md"
RUNNER = ROOT / "scripts/prospectus_installed_h1_cash_flow.py"
TEST = "tests/prospectus/test_h1_cash_flow.py"
DOCUMENT = "bes-interim-h1-2010"
STAGES = ("prepare", "baseline", "profile", "compare", "controls-a", "controls-b", "tests",
    "install-prepare", "build", "install", "installed-positive", "installed-controls-a", "installed-controls-b", "verify", "seal")
SELECTOR = {"version": "bes-h1-cash-flow-supplied.v1", "stages": list(STAGES),
    "work_seconds": 110, "stage_seconds": 115, "child_seconds": 100,
    "execution_seconds": 1200, "storage_bytes": 500 * 1024**2,
    "outer_children": 5, "source_actions": 0, "network_calls": 0, "unchanged_retries": 0}
CASES = ("wrong-year", "wrong-unit", "cross-row", "cross-column", "omitted-cell", "lost-sign",
    "dash-as-zero", "wrong-note", "omitted-repeat", "wrong-shared-span", "invented-box", "omitted-separator",
    "omitted-occurrence", "omitted-qualification", "changed-source", "changed-image", "uncorrected-ocr",
    "wrong-correction-basis", "independent-review", "financial-validation", "legal-selection",
    "stale-prior", "stale-graph", "stale-pin")


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    with path.open("xb") as stream:
        stream.write(gzip.compress(raw, mtime=0) if path.suffix == ".gz" else raw + b"\n")


def workspace():
    return Path(read(HERE / "workspace.json")["directory"])


def storage():
    folders = [HERE]
    if (HERE / "workspace.json").is_file():
        folders.append(workspace())
    return sum(p.stat().st_size for folder in folders for p in folder.rglob("*") if p.is_file())


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-05"]
    require(task.get("cash_flow_reading") == SELECTOR, "Unreviewed H1 cash-flow scope")
    admitted = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT))
        and admitted["program_sha256"] == digest(program) and admitted["task_spec"] == task
        and admitted["binding"] == a.binding(task), "Current unchanged H1 admission required")
    require(not (HERE / "outputs.json").exists(), "H1 evidence already sealed")
    for name in ("protected-inputs.json", "methods.json"):
        if (HERE / name).is_file():
            require(all(file_hash(ROOT / p) == h for p, h in read(HERE / name).items()), "Frozen H1 evidence/method changed: " + name)
    return admitted


def prepare():
    history = read(REVIEW / "history.json")
    protected = history["protected"]
    require(all(file_hash(ROOT / p) == h for p, h in protected.items()), "Original H1 evidence changed")
    save("protected-inputs.json", protected)
    ref = load(PRIOR / "after-P1-reference.json.gz")
    require(file_hash(ROOT / ref["original_P1"]) == ref["original_P1_file_sha256"], "Original P1 file changed")
    graph = load(ROOT / ref["original_P1"])["payload"]["graph"]
    require(len(graph["units"]) == 33221 and product_digest(graph) == ref["graph_sha256"], "Original graph changed")
    p1 = service.seal("P1", ref["request"]["bundle"], {"request": product_digest(ref["request"])},
        {"request": ref["request"], "graph": graph})
    require(p1["sha256"] == ref["expected_P1_sha256"], "Reconstructed P1 changed")
    save("products.json.gz", {"P1": p1, **load(PRIOR / "after-P2-P5.json.gz")})
    units = [u for u in graph["units"] if u["document"] == DOCUMENT and u["page"] == 60]
    require(len(units) == 166 and all(u["visible"] for u in units), "Complete page60 inventory changed")
    save("source-units.json", units)
    doc = next(d for d in ref["request"]["bundle"]["documents"] if d["id"] == DOCUMENT)
    require(file_hash(ROOT / doc["path"]) == doc["sha256"] == "b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7", "Original H1 PDF changed")
    image = ORIGINAL / "extra-60.png"
    save("source.json", {"document": DOCUMENT, "page": 60, "path": doc["path"], "sha256": doc["sha256"],
        "image": {"path": str(image.relative_to(ROOT)), "sha256": file_hash(image)}})
    process_ledger.create(HERE / "command-ledger.json", 5, 0, "H1 offline build/install and three isolated replays; no new source action; pip internals excluded")
    return {"source_units": 33221, "page_occurrences": 166, "new_source_actions": 0}


def baseline():
    products = load(HERE / "products.json.gz")
    public = service.consume(products, ROOT)
    require(public == load(PRIOR / "after-answer.json.gz"), "Complete retained public answer differs")
    full = service.consume(products, ROOT, include_artifacts=True)
    require(product_digest(full) == read(PRIOR / "after-complete-answer-reference.json")["expected_complete_answer_sha256"],
        "Complete retained answer/artifacts differ")
    save("baseline-answer.json.gz", full)
    return {"complete_historical_public_answer_equal": True, "complete_artifact_answer_equal": True}


def methods():
    paths = [Path(__file__), RUNNER, ROOT / TEST, ROOT / PLAN, REVIEW / "REVIEW.md", REVIEW / "history.json",
        HERE / "IMAGE-REVIEW.md", HERE / "IMPLEMENTATION-REVIEW.md", ROOT / "pyproject.toml",
        ROOT / "scripts/prospectus_installed_profile_worker.py", ROOT / "scripts/prospectus_basf_pension_source.py",
        ROOT / "scripts/prospectus_basf_pension_install.py"]
    paths += [ROOT / "src/legalmath" / name for name in files(ROOT / "src/legalmath")]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def profile():
    from legalmath.prospectus import h1_cash_flow as note
    require((HERE / "IMAGE-REVIEW.md").is_file() and (HERE / "IMPLEMENTATION-REVIEW.md").is_file(), "Complete source/implementation review required")
    package, original = files(ROOT / "src/legalmath"), read(REVIEW / "history.json")["package"]
    require(all(package.get(k) == v for k, v in original.items()), "Existing436 package files changed")
    require(sorted(set(package) - set(original)) == ["prospectus/h1_cash_flow.py", "prospectus/h1_cash_flow_spec.py"], "Unexpected new source files")
    save("methods.json", methods())
    for name in read(HERE / "methods.json"):
        target = HERE / "methods" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    value = note.make_profile(load(HERE / "products.json.gz")["P1"]["payload"]["graph"],
        load(HERE / "baseline-answer.json.gz"), read(HERE / "source.json"))
    save("profile.json", value)
    save("profile-pin.json", {"sha256": product_digest(value)})
    save("control-partitions.json", {"controls-a": list(CASES[:12]), "controls-b": list(CASES[12:])})
    return {"rows": len(value["rows"]), "money_cells": len(value["rows"]) * 2, "source_files": len(package)}


def compare():
    from legalmath.prospectus import h1_cash_flow as note
    p = read(HERE / "profile.json")
    result = note.consume(load(HERE / "products.json.gz"), p, ROOT, expected_profile_sha256=product_digest(p))
    require(result["answer"] == load(HERE / "baseline-answer.json.gz"), "Protected complete answer changed")
    require(result["cash_flow_review"]["source_occurrences"] == 166, "Incomplete source coverage")
    save("cash-flow-consumer.json.gz", result)
    summary = {"status": "PASS", "source_occurrences": 166, "rows": len(result["cash_flow_review"]["rows"]),
        "money_cells": result["cash_flow_review"]["money_cells"], "complete_prior_answer_equal": True,
        "arithmetic": result["cash_flow_review"]["arithmetic"], "explanation": result["cash_flow_explanation"],
        "automatic_interpretation": False, "independent_legal_acceptance": False}
    save("comparison.json", summary)
    return {k: summary[k] for k in ("status", "source_occurrences", "rows", "money_cells", "complete_prior_answer_equal")}


def controls(mode):
    from legalmath.prospectus import h1_cash_flow as note
    p = read(HERE / "profile.json")
    graph = load(HERE / "products.json.gz")["P1"]["payload"]["graph"]
    prior = load(HERE / "baseline-answer.json.gz")
    results = []
    for name in read(HERE / "control-partitions.json")[mode]:
        value = deepcopy(p)
        rows = {r["id"]: r for r in value["rows"]}
        cell = rows["interest-received"]["cells"]["2010"]
        if name == "wrong-year": value["years"].reverse()
        elif name == "wrong-unit": value["unit"] = "million EUR"
        elif name == "cross-row": value["rows"][0]["cells"], value["rows"][1]["cells"] = value["rows"][1]["cells"], value["rows"][0]["cells"]
        elif name == "cross-column": rows["interest-received"]["cells"]["2010"], rows["interest-received"]["cells"]["2009"] = rows["interest-received"]["cells"]["2009"], cell
        elif name == "omitted-cell": del rows["interest-received"]["cells"]["2010"]
        elif name == "lost-sign": rows["interest-paid"]["cells"]["2010"]["printed"] = "1 316 102"
        elif name == "dash-as-zero": rows["subsidiaries-disposed"]["cells"]["2010"]["printed"] = "0"
        elif name == "wrong-note": rows["subsidiaries-acquired"]["notes"] = deepcopy(rows["cash"]["notes"])
        elif name == "omitted-repeat": value["rows"] = [r for r in value["rows"] if r["id"] != "net-change-repeat"]
        elif name == "wrong-shared-span": rows["financing-net"]["cells"]["2010"]["source"][0]["end"] += 1
        elif name == "invented-box": rows["financing-net"]["cells"]["2010"]["source"][0]["bbox"] = [370,575,424,588]
        elif name == "omitted-separator": value["separator"] = []
        elif name == "omitted-occurrence": value["context"]["decoration"].pop()
        elif name == "omitted-qualification": value["context"]["notes-integral"] = []
        elif name == "changed-source": value["source"]["sha256"] = "0" * 64
        elif name == "changed-image": value["source"]["image"]["sha256"] = "0" * 64
        elif name == "uncorrected-ocr": rows["risk-derivatives"]["cells"]["2010"]["printed"] = "(7? 424)"
        elif name == "wrong-correction-basis": rows["risk-derivatives"]["cells"]["2010"]["basis"] = "AUTOMATIC_OCR"
        elif name == "independent-review": value["reviewer"]["independent"] = True
        elif name == "financial-validation": value["financial_values_validated"] = True
        elif name == "legal-selection": value["selected_reading"] = "full-financial-statements"
        elif name == "stale-prior": value["prior_sha256"] = "0" * 64
        elif name == "stale-graph": value["graph_sha256"] = "0" * 64
        else: value["reviewer"]["identity"] += " changed"
        pin = product_digest(p) if name == "stale-pin" else product_digest(value)
        save("adverse-inputs/" + name + ".json.gz", {"profile": value, "expected_profile_sha256": pin})
        try:
            note.evaluate(graph, prior, value, ROOT, expected_profile_sha256=pin)
        except ValueError as exc:
            results.append({"case": name, "refused": True, "repinned": name != "stale-pin", "reason": str(exc)})
        else:
            raise ValueError("Altered cash-flow reading accepted: " + name)
    save(mode + ".json", results)
    return {"actual_refusals": len(results), "repinned": sum(r["repinned"] for r in results)}


def tests():
    with (HERE / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
        import pytest
        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "--junitxml=" + str(HERE / "tests.xml")]))
    require(code == 0, "Cash-flow tests failed")
    return {"tests": checked_tests(HERE / "tests.xml", 1), "exit_code": code}


def install_prepare():
    history = read(REVIEW / "history.json")
    env = Path(history["environment"])
    require(files(env / "lib/python3.11/site-packages/legalmath") == history["package"], "436-file installed comparator changed")
    needed = sum(p.stat().st_size for p in env.rglob("*") if p.is_file())
    needed += sum(p.stat().st_size for p in (ROOT / "src").rglob("*") if p.is_file())
    require(storage() + needed + 64 * 1024**2 < 498 * 1024**2, "Installation capacity with64MiB reserve exhausted")
    temp = Path(tempfile.mkdtemp(prefix="installed-h1-cash-flow-", dir=ROOT / ".localresources/prospectus"))
    save("workspace.json", {"directory": str(temp), "cloned_from": str(env), "measured_copy_bytes": needed})
    shutil.copytree(env, temp / "environment", symlinks=True)
    (temp / "source").mkdir()
    shutil.copyfile(ROOT / "pyproject.toml", temp / "source/pyproject.toml")
    shutil.copytree(ROOT / "src", temp / "source/src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    shutil.copyfile(RUNNER, temp / "runner.py")
    package = files(temp / "source/src/legalmath")
    require(package == files(ROOT / "src/legalmath") and len(package) == 438, "Copied package differs")
    save("source-package.json", package)
    save("dependency-files.json", dependencies(temp / "environment"))
    return {"source_files": len(package), "preserved_files": 436, "dependency_entries": len(read(HERE / "dependency-files.json"))}


def child(name, argv):
    folder = HERE / "commands" / name
    folder.mkdir(parents=True, exist_ok=False)
    save("commands/" + name + "/started.json", {"argv": argv, "timeout_seconds": 100})
    tick, result, error = time.monotonic(), None, None
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        with execution_guard([argv]) as guard, process_ledger.observe(HERE / "command-ledger.json"):
            try:
                result = subprocess.run(argv, stdout=out, stderr=err, timeout=100, env=dict(os.environ))
            except BaseException as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
            finally:
                save("commands/" + name + "/result.json", {"returncode": None if result is None else result.returncode,
                    "error": error, "wall_seconds": time.monotonic() - tick, "process_guard": guard.result()})
    require(error is None and result is not None and result.returncode == 0 and guard.result() == {"starts": 1, "blocked": 0}, "H1 child failed: " + name)


def build():
    (HERE / "wheel").mkdir()
    child("build", [str(workspace() / "environment/bin/python"), "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
        "--no-index", "--wheel-dir", str(HERE / "wheel"), str(workspace() / "source")])
    wheels = list((HERE / "wheel").glob("*.whl"))
    require(len(wheels) == 1, "Exactly one offline wheel required")
    result = {"path": str(wheels[0].relative_to(HERE)), "sha256": file_hash(wheels[0])}
    save("built-wheel.json", result)
    return result


def install():
    wheel = read(HERE / "built-wheel.json")
    require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Built wheel changed")
    child("install", [str(workspace() / "environment/bin/python"), "-m", "pip", "install", "--no-index", "--no-deps",
        "--force-reinstall", str(HERE / wheel["path"])])
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependencies changed")
    require(files(workspace() / "environment/lib/python3.11/site-packages/legalmath") == read(HERE / "source-package.json"), "Installed package differs")
    return {"installed": True, "dependencies_unchanged": True}


def installed(mode):
    require(file_hash(workspace() / "runner.py") == file_hash(RUNNER), "Installed runner changed")
    child(mode, [str(workspace() / "environment/bin/python"), "-I", str(workspace() / "runner.py"), str(HERE), str(ROOT), mode])
    result = read(HERE / "installed-results" / mode / "result.json")
    require(result["status"] == "PASS", "Installed H1 comparison failed")
    return result


def verify():
    package = workspace() / "environment/lib/python3.11/site-packages/legalmath"
    expected = read(HERE / "source-package.json")
    require(files(package) == expected == files(ROOT / "src/legalmath"), "Installed or current package changed")
    require(dependencies(workspace() / "environment") == read(HERE / "dependency-files.json"), "Dependency drift")
    for mode in ("positive", "controls-a", "controls-b"):
        folder = HERE / "installed-results" / mode
        result, proof = read(folder / "result.json"), read(folder / "import-proof.json")
        require(result["status"] == "PASS" and result["mode"] == mode and result["process_guard"] == {"starts": 0, "blocked": 0}, "Invalid isolated result")
        require(read(folder / "package-files.json") == expected and proof["isolated"] == 1
            and Path(proof["prefix"]).resolve() == (workspace() / "environment").resolve(), "Wrong installed identity")
        for item in proof["modules"].values():
            p = Path(item["path"]).resolve()
            require(p.is_relative_to(package) and file_hash(p) == item["sha256"] == expected[str(p.relative_to(package))], "Wrong installed module")
    require(load(HERE / "installed-results/positive/cash-flow-consumer.json.gz") == load(HERE / "cash-flow-consumer.json.gz"), "Full installed output differs")
    expected_controls = read(HERE / "controls-a.json") + read(HERE / "controls-b.json")
    actual_controls = sum([read(HERE / "installed-results" / mode / "controls.json") for mode in ("controls-a", "controls-b")], [])
    require(expected_controls == actual_controls and [r["case"] for r in actual_controls] == list(CASES), "Ordered installed refusals differ")
    require(len(process_ledger.checked(HERE / "command-ledger.json")["reservations"]) == 5, "Wrong outer process count")
    save("actual-controls.json", expected_controls)
    result = {**read(HERE / "comparison.json"), "installed_complete_output_equal": True, "actual_refusals": 24,
        "repinned": 23, "exact_package_files": 438, "preexisting_package_files_unchanged": 436,
        "unchanged_dependency_entries": len(read(HERE / "dependency-files.json")), "outer_children": 5,
        "new_source_actions": 0, "different_host_portability": False}
    save("verified-result.json", result)
    return {k: result[k] for k in ("status", "installed_complete_output_equal", "actual_refusals", "exact_package_files")}


def seal():
    require((HERE / "RESULT.md").is_file() and read(HERE / "verified-result.json")["status"] == "PASS", "Actual H1 result analysis required")
    return {"validated": True, "task_complete": False, "independent_legal_acceptance": False}


def run(stage):
    with Authority(ROOT).lock():
        admitted = bindings()
        index = STAGES.index(stage)
        started = {p.parent.name for p in (HERE / "stages").glob("*/started.json")}
        finished = {p.parent.name for p in (HERE / "stages").glob("*/result.json")}
        require(started == finished == set(STAGES[:index]), "Repeated, skipped or interrupted H1 stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < 115 for r in rows), "Failed H1 predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 1200 and storage() < 498 * 1024**2, "H1 cumulative allowance exhausted")
        save("stages/" + stage + "/started.json", {"command": ["timeout", "120", ".venv/bin/python", "-m", "scripts.prospectus_h1_cash_flow", stage],
            "at": datetime.now(timezone.utc).isoformat(), "git_commit": admitted["git_commit"], "python": sys.executable,
            "cpu_gpu": "CPU only; GPU devices intentionally hidden", "random_seeds": "N/A deterministic supplied source reading",
            "plan": PLAN, "data_version": str((PRIOR / "outputs.json").relative_to(ROOT)),
            "result": str((HERE / "RESULT.md").relative_to(ROOT)), "frozen_source_hashes": "methods.json after source review"})
        tick, details, error = time.monotonic(), None, None
        def expire(signum, frame):
            raise TimeoutError("H1 work limit; no unchanged retry")
        old_handler = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(110, 1200 - spent))
        try:
            if stage.startswith("installed-"):
                details = installed(stage.removeprefix("installed-"))
            elif stage in ("build", "install"):
                details = globals()[stage]()
            else:
                with execution_guard() as guard:
                    details = controls(stage) if stage in ("controls-a", "controls-b") else globals()[stage.replace("-", "_")]()
                    require(guard.result() == {"starts": 0, "blocked": 0}, "Unexpected H1 process action")
                details = {**details, "process_guard": guard.result()}
            bindings()
            require(storage() < 498 * 1024**2, "H1 storage bound")
            require(time.monotonic() - tick < 115 and spent + time.monotonic() - tick < 1200, "H1 recorded time bound")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()})
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        value = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic() - tick, "retained_bytes": storage()}
        value["cumulative_seconds"] = spent + value["wall_seconds"]
        save("stages/" + stage + "/result.json", value)
        if error or stage == "seal":
            save("result.json", {**value, "task": "source-bes-dep-05", "task_complete": False,
                "whole_program_complete": False, "independent_legal_acceptance": False})
            save("outputs.json", files(HERE))
        print(json.dumps({k: value[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    require(len(sys.argv) == 2 and sys.argv[1] in STAGES, "Choose admitted H1 cash-flow stage")
    raise SystemExit(run(sys.argv[1]))
