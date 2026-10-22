"""One bounded, admitted capital-profile comparison per invocation."""
import ast
import base64
from contextlib import redirect_stderr, redirect_stdout
import csv
from datetime import datetime, timezone
import difflib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                  PYTHONNOUSERSITE="1", PYTHONPATH="", PYTHONDONTWRITEBYTECODE="1")
from legalmath.prospectus.execution_authority import Authority, digest, file_hash, read
from scripts import prospectus_2010_capital_resume_cases as cases
from scripts.prospectus_installed_profile_worker import execution_guard

BASE = ROOT / "docs/implementation/prospectus-execution-authority"
SOURCE = BASE / "attempts/source-bes-dep-09"
HERE = SOURCE / "attempt-012"
REVIEW = BASE / "reviews/2010-capital-repair-191"
SNAPSHOT = BASE / "reviews/2010-capital-product-190/baseline"
PLAN = "docs/plans/prospectus-2010-capital-repair-2026-10-17.md"
PRODUCTION = "src/legalmath/prospectus/successor/statement_cells.py"
DOCUMENTATION = "docs/prospectus/statement-cells.md"
INSTALLED = {"installed-" + key: key for key in (
    "candidate-products", "candidate-answer", *cases.INPUT_GROUPS, *cases.PHASE_GROUPS)}
STAGES = ("prepare", "focused", "baseline-products", "baseline-answer", "candidate-products",
          "candidate-answer", "composition", *cases.INPUT_GROUPS, *cases.PHASE_GROUPS,
          "prior-9m", "prior-q1", "prior-fy", "wheel-repack", "install", *INSTALLED, "seal")
CHILDREN = ("install", *INSTALLED)
SELECTOR = {"version": "bes-annual2010-capital-resume.v1", "stages": list(STAGES),
            "source_pages": list(cases.PAGES), "source_occurrences": 1817,
            "new_seconds": 720, "combined003_onward_seconds": 1960,
            "new_bytes": 16 * 1024**2, "combined003_onward_bytes": 200 * 1024**2,
            "reserve_bytes": 512 * 1024, "work_seconds": 45, "stage_seconds": 50,
            "children": list(CHILDREN), "child_seconds": 35,
            "production_edits": [], "wheel_validation": "verified009-wheel-repack; no fresh build",
            "extraction_OCR_render_network_model_GPU_retries": 0}
TESTS = ("tests/prospectus_successor/test_statement_cells.py",
         "tests/prospectus_successor/test_annual_statement_cells.py",
         "tests/prospectus_successor/test_annual_capital_statement_cells.py")
cases.configure(ROOT, HERE)
require = cases.require


def support():
    return {p for p in REVIEW.rglob("*") if p.is_file()} | {
        Path(__file__), Path(cases.__file__), ROOT / PLAN,
        BASE / "proposals/2010-capital-repair-191.json",
        BASE / "proposals/2010-capital-repair-191-review.json",
        BASE / "closure-routes-2026-10-17-2010-capital-repair-191.json"}


def storage():
    h = read(REVIEW / "history.json")
    paths = support() | {p for p in HERE.rglob("*") if p.is_file()}
    paths -= {ROOT / p for p in h["historical_storage"]}
    new = sum(p.stat().st_size for p in paths if p.is_file())
    return {"previous_seconds": h["previous_seconds"], "previous_bytes": h["previous_bytes"],
            "new_bytes": new, "combined_bytes": h["previous_bytes"] + new}


def save(name, value, failure=False):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    data = gzip.compress(raw, mtime=0) if name.endswith(".gz") else raw + b"\n"
    state, reserve = storage(), 0 if failure else SELECTOR["reserve_bytes"]
    require(state["new_bytes"] + len(data) < SELECTOR["new_bytes"] - reserve and
            state["combined_bytes"] + len(data) < SELECTOR["combined003_onward_bytes"] - reserve,
            "Capital repair storage ceiling/reserve exhausted")
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def source_contract():
    """Read-only structural and source checks, usable before admission."""
    old = ast.parse((SNAPSHOT / "statement_cells.py").read_text())
    new = ast.parse((ROOT / PRODUCTION).read_text())
    for tree in (old, new):
        require(isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant),
                "Expected module docstring")
        tree.body.pop(0)
    profiles = next(n.value for n in new.body if isinstance(n, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == "PROFILES" for t in n.targets))
    index, = [i for i, k in enumerate(profiles.keys) if isinstance(k, ast.Constant) and k.value == cases.PROFILE]
    profiles.keys.pop(index)
    profiles.values.pop(index)
    require(ast.dump(old) == ast.dump(new), "Adapter changed beyond the optional v2 entry/docstring")
    from legalmath.prospectus.successor import statement_cells
    fixture = cases.read(ROOT / cases.FIXTURE)
    actual = sorted(fixture["graph"]["units"], key=lambda u: (u["page"], u["order"], u["id"]))
    graph = cases.legacy.original()["P1"]["payload"]["graph"]
    selected = sorted((u for u in graph["units"] if u["document"] == "bes-2010-en" and u["page"] in cases.PAGES),
                      key=lambda u: (u["page"], u["order"], u["id"]))
    require(actual == selected and len(actual) == 1817 and len({u["id"] for u in actual}) == 1817,
            "Combined fixture differs from complete original occurrences")
    profile = statement_cells.PROFILES[cases.PROFILE]
    require(cases.evidence_digest(selected) == profile["pages_digest"] and
            cases.evidence_digest(fixture["reading"]) == profile["reading"] and
            {u["page"] for u in actual} == set(cases.PAGES), "Combined fixture pins differ")
    capital = fixture["reading"]["capital_notes"]
    require(capital == {"profile": read(SOURCE / "attempt-010/profile.json"),
                        "analysis": read(SOURCE / "attempt-010/analysis.json")}, "010 reading changed")
    return {"only_optional_profile_and_docstring_changed": True, "original_source_units_exact": True,
            "source_occurrences": len(actual), "reading_sha256": profile["reading"],
            "selected_units_sha256": profile["pages_digest"]}


def bindings():
    a = Authority(ROOT)
    program, tasks, _ = a.spec()
    task = tasks["source-bes-dep-09"]
    admission = read(HERE / "admission.json")
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == str(HERE.relative_to(ROOT)) and
            admission["task_spec"] == task and admission["program_sha256"] == digest(program) and
            task.get("capital_resume") == SELECTOR and admission["binding"] == a.binding(task),
            "Current unchanged capital-repair admission required")
    require(not (HERE / "outputs.json").exists(), "Sealed capital repair")
    h = read(REVIEW / "history.json")
    require(all(file_hash(ROOT / p) == v for p, v in h["protected"].items()), "Historical/support bytes changed")
    require(cases.legacy.package_files(ROOT / "src/legalmath") == h["package"], "Candidate package drift")
    require(all((ROOT / p).stat().st_size == size for p, size in h["historical_storage"].items()),
            "Historical storage identity changed")
    env_ref = h["build_environment"]
    require(file_hash(ROOT / env_ref["manifest_path"]) == env_ref["manifest_sha256"], "Environment manifest changed")
    env = read(ROOT / env_ref["manifest_path"])["build_environment"]
    require(env["path"] == env_ref["path"], "Environment path differs")
    require(cases.legacy.environment_files(Path(env["path"])) == env["files"], "Read-only build environment changed")
    if (HERE / "final-methods.json").exists():
        require(all(file_hash(ROOT / p) == v for p, v in read(HERE / "final-methods.json").items()),
                "Frozen capital-repair methods changed")
    return admission


def prepare():
    h = read(REVIEW / "history.json")
    details = source_contract()
    _, _, refs = cases.complete010()
    save("final-package.json", cases.legacy.package_files(ROOT / "src/legalmath"))
    methods = support() | {ROOT / p for p in (*TESTS, cases.FIXTURE, DOCUMENTATION, PRODUCTION)}
    save("final-methods.json", {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(methods)})
    before, after = (SNAPSHOT / "statement-cells.md").read_text(), (ROOT / DOCUMENTATION).read_text()
    save("documentation-diff.json", {"patch": "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))})
    support_bytes = sum(p.stat().st_size for p in support())
    available = min(SELECTOR["new_bytes"] - support_bytes,
                    SELECTOR["combined003_onward_bytes"] - h["previous_bytes"] - support_bytes)
    save("resource-contract.json", {"attempt_available_bytes": available, "reserve_bytes": SELECTOR["reserve_bytes"],
        "support_bytes": support_bytes, "previous_bytes": h["previous_bytes"]})
    return {**details, "complete010_sha256": refs["complete_composed_answer_sha256"],
            "prior_admissions": len(h["admissions"]), "package_files": len(h["package"]),
            "read_only_environment": True, "attempt_available_bytes": available}


def focused():
    import pytest
    path = HERE / "focused.log"
    with path.open("x", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        code = pytest.main(["-q", "-p", "no:cacheprovider", *TESTS,
                            "--junitxml=" + str(HERE / "focused.xml")])
    require(code == 0, "Focused tests failed; inspect focused.log")
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / "focused.xml").getroot()
    tests = sum(int(s.attrib.get("tests", 0)) for s in suites.iter("testsuite"))
    result = {"status": "PASS", "tests": tests, "log_sha256": file_hash(path)}
    save("checks/focused.json", result)
    return result


def validate_record(archive):
    names = archive.namelist()
    require(len(set(names)) == len(names) and all(not n.endswith("/") for n in names), "Unexpected wheel entries")
    record, = [n for n in names if n.endswith(".dist-info/RECORD")]
    rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
    require(len(rows) == len(names) and {r[0] for r in rows} == set(names), "Incomplete wheel RECORD")
    for name, checksum, size in rows:
        if name == record:
            require(checksum == size == "", "RECORD self-row differs")
        else:
            data = archive.read(name)
            expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
            require(checksum == expected and size == str(len(data)), "Invalid wheel RECORD: " + name)
    return record


def wheel_repack():
    ref = read(SOURCE / "attempt-009/built-wheel.json")
    original = SOURCE / "attempt-009" / ref["path"]
    require(file_hash(original) == ref["sha256"], "Verified009 wheel changed")
    target = HERE / "wheel" / original.name
    target.parent.mkdir()
    changed = "legalmath/" + PRODUCTION.removeprefix("src/legalmath/")
    with zipfile.ZipFile(original) as before:
        record = validate_record(before)
        old_package = {n.removeprefix("legalmath/"): hashlib.sha256(before.read(n)).hexdigest()
                       for n in before.namelist() if n.startswith("legalmath/")}
        require(old_package == read(REVIEW / "history.json")["baseline_package"], "009 wheel baseline package differs")
        data = {n: before.read(n) for n in before.namelist() if n != record}
        data[changed] = (ROOT / PRODUCTION).read_bytes()
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        for name, value in data.items():
            writer.writerow([name, "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode(), len(value)])
        writer.writerow([record, "", ""])
        data[record] = output.getvalue().encode()
        with zipfile.ZipFile(target, "x") as after:
            for entry in before.infolist():
                after.writestr(entry, data[entry.filename])
        with zipfile.ZipFile(target) as after:
            require(validate_record(after) == record, "Changed RECORD path")
            names = [n for n in before.namelist() if before.read(n) != after.read(n)]
            require(set(names) == {changed, record}, "Repack changed undeclared wheel entries")
            package = {n.removeprefix("legalmath/"): hashlib.sha256(after.read(n)).hexdigest()
                       for n in after.namelist() if n.startswith("legalmath/")}
            require(package == read(HERE / "final-package.json"), "Repacked package differs")
    result = {"path": str(target.relative_to(HERE)), "sha256": file_hash(target),
              "baseline_path": str(original.relative_to(ROOT)), "baseline_sha256": ref["sha256"],
              "changed_entries": names, "all_RECORD_rows_valid": True, "package_files": len(package),
              "fresh_normal_build": False, "validation": SELECTOR["wheel_validation"]}
    save("built-wheel.json", result)
    return result


def command(stage):
    python = str(Path(read(REVIEW / "history.json")["build_environment"]["path"]) / "bin/python")
    if stage == "install":
        wheel = read(HERE / "built-wheel.json")
        require(file_hash(HERE / wheel["path"]) == wheel["sha256"], "Candidate wheel changed")
        return [python, "-I", "-B", "-m", "pip", "install", "--no-deps", "--no-index", "--no-compile",
                "--target", str(HERE / "installed"), str(HERE / wheel["path"])]
    return [python, "-I", "-B", str(Path(cases.__file__)), str(ROOT), str(HERE), INSTALLED[stage]]


def child(stage):
    if stage == "install":
        require(not (HERE / "installed").exists(), "Existing installation target refused")
    argv = command(stage)
    env = {"CUDA_VISIBLE_DEVICES": "-1", "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": "/dev/null"}
    save("commands/" + stage + "/command.json", {"argv": argv, "cwd": str(HERE), "environment": env,
        "timeout": SELECTOR["child_seconds"], "reservation": CHILDREN.index(stage) + 1})
    folder, tick = HERE / "commands" / stage, time.monotonic()
    with (folder / "stdout").open("xb") as out, (folder / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=HERE, env={**os.environ, **env}, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err, timeout=SELECTOR["child_seconds"])
    save("commands/" + stage + "/result.json", {"returncode": result.returncode, "wall_seconds": time.monotonic() - tick})
    require(result.returncode == 0, "Capital-repair child failed: " + stage)
    require(cases.legacy.package_files(HERE / "installed/legalmath") == read(HERE / "final-package.json"),
            "Installed package differs")
    if stage != "install":
        require(read(HERE / "installed-checks" / (INSTALLED[stage] + ".json"))["status"] == "PASS", "Installed result missing")
    return {"command": stage, "returncode": result.returncode}


def seal():
    require((HERE / "RESULT.md").is_file(), "Actual result review required")
    for groups in (cases.INPUT_GROUPS, cases.PHASE_GROUPS):
        for name, expected in groups.items():
            controls = read(HERE / "checks" / (name + ".json"))
            require(set(controls) == set(expected) and all(v["refused"] for v in controls.values()), "Missing actual controls")
            require(all(cases.sha(HERE / v["adverse"]["path"]) == v["adverse"]["file_sha256"] for v in controls.values()),
                    "Retained adverse inputs changed")
    for action in INSTALLED.values():
        require(read(HERE / "installed-checks" / (action + ".json"))["status"] == "PASS", "Missing installed comparison")
    require(read(HERE / "checks/composition.json")["complete010_protected_equal"], "Missing complete010 comparison")
    require(all(read(HERE / "checks" / (n + ".json"))["complete_answer_equal"]
                for n in ("prior-9m", "prior-q1", "prior-fy")), "Missing older profile comparison")
    save("verified-result.json", {"actual_product_consumption": True, "offline_installed_consumption": True,
        "fresh_normal_build": False, "package_files": len(read(HERE / "final-package.json")),
        "actual_public_refusals": 14, "actual_installed_refusals": 14, "fresh_extractions": 0,
        "candidate": read(HERE / "checks/candidate-answer.json"), "composition": read(HERE / "checks/composition.json"),
        "result_note_sha256": file_hash(HERE / "RESULT.md"), "independent_acceptance": False, "task_complete": False})
    return {"actual_product_consumption": True, "offline_installed_consumption": True, "task_complete": False}


def finish(result):
    save("result.json", {**result, "task": "source-bes-dep-09", "task_complete": False,
        "whole_program_complete": False, "independent_acceptance": False}, failure=result["status"] == "FAIL")
    save("outputs.json", cases.legacy.package_files(HERE), failure=result["status"] == "FAIL")


def run(stage):
    require(stage in STAGES, "Unknown capital-repair stage")
    with Authority(ROOT).lock():
        require((HERE / "admission.json").is_file() and not (HERE / "outputs.json").exists(), "Unadmitted/sealed attempt")
        try:
            admission = bindings()
        except Exception as exc:
            result = {"stage": stage, "status": "FAIL", "error": {"type": type(exc).__name__, "message": str(exc)},
                      "wall_seconds": 0, "timing_scope": "Preflight failed before stage body"}
            save("preflight-failure.json", {"traceback": traceback.format_exc()}, failure=True)
            finish(result)
            print(json.dumps(result))
            return 1
        index = STAGES.index(stage)
        require({p.parent.name for p in (HERE / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (HERE / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Repeated/skipped/interrupted capital-repair stage")
        rows = [read(HERE / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" and r["wall_seconds"] < SELECTOR["stage_seconds"] for r in rows), "Failed predecessor")
        spent, before = sum(r["wall_seconds"] for r in rows), storage()
        def within(state, elapsed=0):
            return spent + elapsed < SELECTOR["new_seconds"] and \
                state["previous_seconds"] + spent + elapsed < SELECTOR["combined003_onward_seconds"] and \
                state["new_bytes"] < SELECTOR["new_bytes"] - SELECTOR["reserve_bytes"] and \
                state["combined_bytes"] < SELECTOR["combined003_onward_bytes"] - SELECTOR["reserve_bytes"]
        require(within(before), "Cumulative repair bounds exhausted")
        save("stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "55", ".venv/bin/python", "-m", "scripts.prospectus_2010_capital_resume", stage],
            "git_commit": admission["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic", "data_version": "original P1; sealed009/006/007/010; optional frozen v2",
            "plan": PLAN, "result": str((HERE / "RESULT.md").relative_to(ROOT))})
        tick, details, error = time.monotonic(), None, None
        def expire(*_):
            raise TimeoutError("Capital repair stage/cumulative bound; no unchanged retry")
        old = signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, min(SELECTOR["work_seconds"], SELECTOR["new_seconds"] - spent,
                                             SELECTOR["combined003_onward_seconds"] - before["previous_seconds"] - spent))
        try:
            commands = [command(stage)] if stage in CHILDREN else []
            with execution_guard(commands) as guard:
                if stage in CHILDREN: details = child(stage)
                elif stage == "prepare": details = prepare()
                elif stage == "focused": details = focused()
                elif stage == "wheel-repack": details = wheel_repack()
                elif stage == "seal": details = seal()
                else:
                    details = cases.dispatch(stage)
                    save("checks/" + stage + ".json", details)
            require(guard.result() == {"starts": len(commands), "blocked": 0}, "Unexpected process/network action")
            bindings()
            require(time.monotonic() - tick < SELECTOR["stage_seconds"] and within(storage(), time.monotonic() - tick),
                    "Capital repair bounds exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save("stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, failure=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
        result = {"stage": stage, "status": "FAIL" if error else "PASS", "error": error, "details": details,
            "wall_seconds": time.monotonic() - tick, "bounds": storage(),
            "timing_scope": "Stage body and final identities; excludes startup/final receipt writing"}
        result["cumulative_seconds"] = spent + result["wall_seconds"]
        save("stages/" + stage + "/result.json", result, failure=bool(error))
        if error or stage == "seal": finish(result)
        print(json.dumps({k: result[k] for k in ("stage", "status", "error", "wall_seconds", "cumulative_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1]))
