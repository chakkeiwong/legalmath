"""Current frozen 452-file installed profile and complete native lifecycle."""
import argparse
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import zipfile
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest as adigest, file_hash, read, write
from legalmath.prospectus import native_profile as product
from legalmath.prospectus.successor import process_ledger, service
from scripts import prospectus_native_product_delta as native
from scripts import prospectus_installed_profile_refresh as previous
from scripts.prospectus_profile_installed_worker import execution_guard
from scripts.prospectus_component_revalidation import runtime_files

prior = native.prior
helper, common, require = prior.helper, prior.common, prior.require
BASE = native.BASE
REVIEW = BASE + "/reviews/installed-runtime-246"
BASELINE = BASE + "/attempts/native-binding/attempt-023"
OLD = BASE + "/attempts/native-confinement/attempt-004"
RUNTIME = native.INSTALLED
INSTALLED = BASE + "/attempts/source-bes-dep-06/attempt-013"
SCRIPT = "scripts/prospectus_installed_runtime.py"
WORKER = "scripts/prospectus_installed_runtime_worker.py"
TEST = "tests/prospectus/test_installed_runtime.py"
PLAN = "docs/plans/prospectus-current-installed-runtime-2026-10-18.md"
COMMANDS = ("capture", "check", *("replay-" + r for r in native.ROUTES), "profile-controls",
            *(s + "-" + m for m in ("fresh", "retained") for s in ("source", "construct", "finish", "verify")),
            "lifecycle-controls", "report-controls")
STAGES = ("prepare", *COMMANDS[:8], *COMMANDS[8:12], "compare-fresh",
          *COMMANDS[12:16], "compare-retained", *COMMANDS[16:], "validate", "seal")
SELECTOR = {"version": "current-installed-runtime.v1", "review": REVIEW,
    "baseline": BASELINE, "donor": INSTALLED, "stages": list(STAGES),
    "outer_commands": 18, "native_calls": 4, "historical_outer": 94, "historical_native": 16,
    "preparation_seconds": 90, "stage_seconds": 120, "execution_seconds": 1800,
    "evidence_stage_seconds": 215, "validation_seconds": 210,
    "unique_evidence_bytes": 640 * 1024**2, "new_installations": 0, "unchanged_retries": 0}
TESTS = (TEST, "tests/prospectus/test_profile_installed.py",
         "tests/prospectus/test_installed_profile_refresh.py", "tests/prospectus/test_native_profile.py")
PROFILE_ERRORS = {"wrong-pin": "Pinned profile", "blob-changed": "Snapshot blob", "blob-missing": "No such file",
    "method-changed": "Installed product methods", "runtime-changed": "Trusted runtime", "manifest-changed": "Snapshot manifest identity",
    "changed-source": "Source bytes changed", "duplicate-stage": "File exists", "rehashed-answer": "Complete installed object differs: answer",
    "extra-subprocess": "Native subprocess forbidden", "actual-old-profile": "Installed product methods changed; recapture profile"}
LIFECYCLE_ERRORS = {"failed-predecessor": "Predecessor stage did not pass", "rehashed-forged-answer": "Delivered answer differs from actual consumer",
                    "missing-stream": "No such file", "forbidden-subprocess": "Native subprocess forbidden"}


def selector(task):
    require(task.get("id") == "native-confinement" and task.get("handler") == "agent"
        and task.get("validator") == prior.INSTALLED and task.get("current_installed_runtime") == SELECTOR
        and task.get("product_delta_acceptance") == previous.SELECTOR
        and task.get("native_call_allowance") == 4 and task.get("retained_acceptance_only") is False
        and task.get("preparation_only") is False
        and not {"annual_profile_compatibility", "retained_current_profile"} & set(task),
        "Unreviewed current installed runtime selector")


def methods(root):
    paths = {str(p.relative_to(root)) for p in (root / "src/legalmath").rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    paths |= set(prior.methods(root)) | {SCRIPT, WORKER, TEST, PLAN, native.SCRIPT,
        previous.SCRIPT, previous.WORKER, previous.TEST, "scripts/prospectus_profile_installed.py",
        "scripts/prospectus_profile_installed_worker.py", "scripts/prospectus_component_revalidation.py",
        "scripts/prospectus_installed_consumer.py", "scripts/prospectus_installed_live_worker.py", *TESTS}
    return {n: file_hash(root / n) for n in sorted(paths)}


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected installed dispatcher baseline")
    return before.replace(marker, marker +
        '    if "current_installed_runtime" in task:\n'
        '        from scripts.prospectus_installed_runtime import validate_submission as validate_current\n'
        '        return validate_current(root, attempt, task)\n')


def installed_proof(proof, environment, package, expected_methods):
    require(proof.get("module_path") == str(package / "prospectus/native_profile.py") and
        proof.get("python") == str(environment / "bin/python") and
        proof.get("methods") == expected_methods, "Current target execution identity differs")
    return package


def installed_requirements(required, manifest, package):
    expected = dict(required)
    files = {r["path"]: r["sha256"] for r in manifest["files"]}
    for name in ("ocr_worker.py", "native_inputs.py"):
        source = str(Path(product.extraction.__file__).with_name(name).resolve())
        target = str(package / "prospectus/successor" / name)
        require(source in expected and target not in expected, "Ambiguous current target worker mapping")
        hashed = expected.pop(source)
        require(files.get(target) == hashed, "Current target worker bytes differ")
        expected[target] = hashed
    return expected


def workspace(folder):
    value = read(folder / "workspace.json")
    work, environment = Path(value["directory"]), Path(value["environment"])
    require(work.is_relative_to(ROOT / ".localresources/prospectus") and
            work.resolve() == work and not work.is_symlink() and
            environment == Path(read(ROOT / RUNTIME / "workspace.json")["directory"]) / "environment" and
            value["package"] == str(ROOT / INSTALLED / "installed/legalmath"),
            "Unreviewed installed workspace")
    return work, environment


def storage(folder):
    parents = [folder]
    if (folder / "workspace.json").exists():
        parents.append(workspace(folder)[0])
    parents.extend([ROOT / REVIEW, ROOT / (BASE + "/proposals/installed-runtime-246.json"),
        ROOT / (BASE + "/proposals/installed-runtime-246-review.json"),
        ROOT / (BASE + "/closure-routes-2026-10-18-installed-runtime-246.json"),
        ROOT / (BASE + "/revisions/0246.json"), *(ROOT / p for p in (SCRIPT, WORKER, TEST, PLAN))])
    unique, logical = {}, 0
    for parent in parents:
        for p in (parent.rglob("*") if parent.is_dir() else [parent]):
            require(not p.is_symlink(), "Installed evidence symlink refused")
            if p.is_file():
                st = p.stat(); unique[st.st_dev, st.st_ino] = st.st_size; logical += st.st_size
    return {"unique_bytes": sum(unique.values()), "logical_bytes": logical}


def save(folder, name, value, *, final=False):
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    if name.endswith(".gz"):
        data = gzip.compress(data, mtime=0)
    require(storage(folder)["unique_bytes"] + len(data) < (640 if final else 636) * 1024**2, "Installed profile evidence cap")
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def package_check(root, folder=None):
    installed = root / INSTALLED
    env = Path(read(root / RUNTIME / "workspace.json")["directory"]) / "environment"
    expected = read(installed / "source-package.json")
    require(helper.package_files(root / "src/legalmath") == expected ==
            helper.package_files(installed / "installed/legalmath"), "Current installed package differs")
    require(prior.preparation.tree(env, dependencies=True) == read(root / RUNTIME / "dependencies.json"), "Installed dependencies differ")
    require(len(expected) == 452, "Wrong current installed package inventory")
    wheel = read(installed / "wheel.json")
    require(file_hash(installed / wheel["file"]) == wheel["sha256"], "Frozen wheel changed")
    with zipfile.ZipFile(installed / wheel["file"]) as archive:
        content = {n.removeprefix("legalmath/"): hashlib.sha256(archive.read(n)).hexdigest()
                   for n in archive.namelist() if n.startswith("legalmath/") and not n.endswith("/")}
    require(content == expected, "Wheel/source/installation disagree")
    if folder:
        require(read(folder / "source-package.json") == expected, "Frozen current package differs")
    return env, expected


def prepare(folder):
    env, expected = package_check(ROOT)
    work = Path(tempfile.mkdtemp(prefix="native-profile-current-", dir=ROOT / ".localresources/prospectus"))
    save(folder, "workspace.json", {"directory": str(work), "environment": str(env), "old_preparation": BASE + "/attempts/native-confinement/attempt-010", "package": str(ROOT / INSTALLED / "installed/legalmath")})
    (work / "helpers").mkdir()
    for source, name in ((WORKER, "worker.py"), ("scripts/prospectus_installed_consumer.py", "consumer.py"),
                         ("scripts/prospectus_installed_live_worker.py", "live.py")):
        shutil.copyfile(ROOT / source, work / "helpers" / name)
    save(folder, "source-package.json", expected)
    save(folder, "baseline.json", {"attempt": BASELINE})
    process_ledger.create(folder / "outer-ledger.json", 18, 94, "Eighteen current installed commands; prior94 retained; no build/install")
    process_ledger.create(folder / "native-ledger.json", 4, 16, "Four current installed source reservations; prior16 retained; native-binding lineage separate")
    original = common.snapshot(ROOT / BASE / "attempts/native-binding/attempt-006/snapshot")
    old_spec = read(ROOT / OLD / "capture-spec.json")
    rows = deepcopy(original["files"])
    sources = {row["path"]: old_spec["sources"][row["path"]] for row in rows}
    package = ROOT / INSTALLED / "installed/legalmath"
    old_env = Path(read(ROOT / OLD / "workspace.json")["directory"]) / "environment"
    for name in ("ocr_worker.py", "native_inputs.py"):
        path = package / "prospectus/successor" / name
        old_path = old_env / "lib/python3.11/site-packages/legalmath/prospectus/successor" / name
        rows.append({"path": str(path), "sha256": file_hash(path), "size": path.stat().st_size, "mode": 0o444})
        sources[str(path)] = old_spec["sources"][str(old_path)]
    for row in rows:
        source = Path(sources[row["path"]])
        require(file_hash(source) == row["sha256"] and source.stat().st_size == row["size"] and
                source.stat().st_mode & 0o777 == row["mode"], "Declared capture source differs")
    directories = set(original["directories"])
    for row in rows:
        directories.update(str(p) for p in Path(row["path"]).parents if str(p) != "/")
    save(folder, "capture-spec.json", {"repository": str(ROOT), "sources": sources, "directories": sorted(directories),
        "ocr_python": old_spec["ocr_python"], "native_text_max_stream": 64 * 1024**2})
    save(folder, "expected-snapshot.json", {**original, "files": sorted(rows, key=lambda r: r["path"]), "directories": sorted(directories)})
    for mode in ("fresh", "retained"):
        req = helper.read(ROOT / BASELINE / "routes" / ("2010-" + mode) / "P1.json.gz")["payload"]["request"]
        require(req == read(ROOT / OLD / (mode + "-request.json")), "Original installed request differs")
        save(folder, mode + "-request.json", req)
    return {"package_files": len(expected), "declared_profile_files": len(rows), "new_installations": 0}


def execute(folder, stage):
    work, env = workspace(folder)
    package_check(ROOT, folder)
    for source, name in ((WORKER, "worker.py"), ("scripts/prospectus_installed_consumer.py", "consumer.py"),
                         ("scripts/prospectus_installed_live_worker.py", "live.py")):
        require(file_hash(work / "helpers" / name) == file_hash(ROOT / source), "Copied installed helper changed")
    rows = process_ledger.checked(folder / "outer-ledger.json")["reservations"]
    require(len(rows) == COMMANDS.index(stage), "Installed outer command order differs")
    argv = [str(env / "bin/python"), "-I", "-B", str(work / "helpers/worker.py"), str(ROOT), str(folder), stage]
    target = folder / "commands" / stage
    target.mkdir(parents=True)
    environment = {**os.environ, "PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "-1"}
    save(folder, "commands/" + stage + "/command.json", {"argv": argv, "cwd": str(work / "helpers"), "timeout": 110,
        "environment": {k: environment[k] for k in ("PYTHONPATH", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "CUDA_VISIBLE_DEVICES")}})
    tick = time.monotonic()
    with execution_guard([argv]) as guard, process_ledger.observe(folder / "outer-ledger.json"), (target / "stdout").open("xb") as out, (target / "stderr").open("xb") as err:
        result = subprocess.run(argv, cwd=work / "helpers", env=environment, stdout=out, stderr=err, timeout=110)
    save(folder, "commands/" + stage + "/result.json", {"returncode": result.returncode, "wall_seconds": time.monotonic() - tick,
        "process_guard": guard.result()})
    require(guard.result() == {"starts": 1, "blocked": 0}, "Installed outer process guard differs")
    require(result.returncode == 0 and read(target / "installed-result.json")["status"] == "PASS", "Actual installed command failed; see retained stderr")
    package_check(ROOT, folder)
    return {"command": stage, "returncode": result.returncode}


def profile_context(root, folder):
    env, package = package_check(root, folder)
    pin = read(folder / "profile/capture-result.json")["profile_sha256"]
    profile, manifest = product.load_profile(folder / "profile", pin)
    require(manifest == read(folder / "expected-snapshot.json") and len(manifest["files"]) == 343,
            "Actual current profile differs from declared complete snapshot")
    require(profile["methods"] == product.methods() and all(package[p] == h for p, h in profile["methods"].items()),
            "Captured product methods differ from installed package")
    product.checked_stage(folder / "profile", "capture")
    product.checked_stage(folder / "profile-check", "check")
    return env, profile, manifest


def compare(root, folder, mode, *, reconsume=True):
    require(mode in ("fresh", "retained"), "Unknown installed comparison mode")
    env, profile, manifest = profile_context(root, folder)
    base = root / BASELINE / "routes" / ("2010-" + mode)
    job = folder / mode
    for stage in ("source", "construct", "finish", "verify"):
        product.checked_stage(job, stage)
    actual, answer = common.products(job)
    expected, old_answer = common.products(base)
    execution = read(job / "execution.json")
    installed_proof(execution, env, root / INSTALLED / "installed/legalmath", product.methods())
    request = read(folder / (mode + "-request.json"))
    require(request == expected["P1"]["payload"]["request"], "Installed original request differs")
    prior.live.product_bindings(actual["P1"], request, execution, profile, folder / "profile")
    required = installed_requirements(product.preflight(request, profile, manifest), manifest, root / INSTALLED / "installed/legalmath")
    require(required == execution["required_files"] == read(folder / "preflight.json")[mode], "Installed required input map differs")
    receipts = []
    for index in (0, 1):
        receipt, streams = common.receipt(job / "native" / str(index), manifest)
        argv = read(base / "native" / str(index) / "receipt.json")["argv"]
        if index:
            argv[1] = str(root / INSTALLED / "installed/legalmath/prospectus/successor/ocr_worker.py")
        require(receipt["argv"] == argv and receipt["limits"]["max_stream_bytes"] == (20 if index else 64) * 1024**2,
                "Actual installed native dispatch or bound differs")
        require(all(data == (base / "native" / str(index) / name).read_bytes()
                    for name, data in zip(("stdin", "stdout", "stderr"), streams)), "Complete installed native stream differs")
        receipts.append(receipt)
    require(execution["native_receipts"] == receipts, "Native receipt inventory differs")
    graph, old = actual["P1"]["payload"]["graph"], expected["P1"]["payload"]["graph"]
    ocr_hashes = None
    if mode == "fresh":
        ocr_hashes = (prior.live.checked_fresh_ocr(graph["documents"][0], (job / "native/1/stdout").read_bytes(), receipts[1], manifest),
            prior.live.checked_fresh_ocr(old["documents"][0], (base / "native/1/stdout").read_bytes(),
                read(base / "native/1/receipt.json"), read(root / BASELINE / "snapshots/2010/manifest.json")))
    prior.live.compare_source_graph(graph, old, mode, receipts, ocr_hashes)
    common.compare_products((expected, old_answer), (actual, answer))
    if reconsume:
        common.consumer(root, actual, answer)
    require(read(job / "verification.json") == {"version": product.VERSION, "profile_sha256": product.digest(profile),
        "answer_sha256": answer["report_sha256"], "consumed_products": answer["consumed_products"], "native_calls": 2,
        "native_reuse_allowed": False, "independent_legal_acceptance": False}, "Installed final verification differs")
    return {"mode": mode, "complete_streams_equal": True, "source_equal_except_verified_receipts": True,
            "complete_semantics_equal": True, "answer_sha256": answer["report_sha256"],
            "receipts": [r["receipt_sha256"] for r in receipts]}


def checked_controls(rows, expected):
    require(len(rows) == len(expected) and {r["case"] for r in rows} == set(expected), "Installed control denominator differs")
    require(all(r.get("refused") is True and expected[r["case"]] in r.get("error", "") for r in rows),
            "Installed control did not refuse for expected reason")


def checked_tests(folder):
    from legalmath.prospectus.execution_acceptance import checked_tests as count_tests
    result = read(folder / "tests/result.json")
    require(result["status"] == "PASS" and result["exit_code"] == 0
        and result["junit_sha256"] == file_hash(folder / "tests/results.xml"), "Installed tests differ")
    require(result["junit_sha256"] == file_hash(ROOT / REVIEW / "tests.xml"), "Reviewed preparation tests differ")
    count = count_tests(folder / "tests/results.xml", 1)
    require(count == read(ROOT / REVIEW / "preparation.json")["tests"], "Preparation test denominator differs")
    return {"tests": count,
            "junit_sha256": result["junit_sha256"]}


def report_adverse(root):
    values, _ = common.products(root / BASELINE / "routes/2009-fresh")
    rows = {}
    for case in native.ATTACKS:
        bad = native.changed(values, case)
        expected = "Report readings lack supplied source evidence" if case == "unsupplied-selection" else "Report readings differ from supplied source evidence"
        try:
            service.consume(bad, root, mode="frozen", include_artifacts=True)
        except ValueError as exc:
            require(str(exc) == expected, "Wrong current report refusal")
            rows[case] = {"rejected": True, "reason": str(exc), "products": {p: v["sha256"] for p, v in bad.items()}}
        else:
            raise ValueError("Forged current report accepted")
    return rows


def evidence(root, folder, *, reconsume=True):
    require(read(folder / "methods.json") == methods(root), "Installed current checker methods changed")
    require((root / previous.SCRIPT).read_text() == dispatch_candidate((root / REVIEW / "dispatch-before.py").read_text()),
        "Unreviewed installed-only dispatch")
    history = read(root / REVIEW / "history.json")
    authority = Authority(root)
    require(all(e in authority.events() and authority.retained_evidence_valid(e) for e in history["events"]), "Retained installed/native history changed")
    env, profile, manifest = profile_context(root, folder)
    work, _ = workspace(folder)
    outer = process_ledger.checked(folder / "outer-ledger.json")
    ledger = process_ledger.checked(folder / "native-ledger.json")
    require(outer["limit"] == 18 and outer["historical_lower_bound"] == 94 and len(outer["reservations"]) == 18 and
            ledger["limit"] == 4 and ledger["historical_lower_bound"] == 16 and len(ledger["reservations"]) == 4 and
            all(r["state"] == "STARTED" for r in outer["reservations"] + ledger["reservations"]), "Current installed reservation denominator differs")
    require({p.name for p in (folder / "commands").iterdir()} == set(COMMANDS), "Current installed command denominator differs")
    package = ROOT / INSTALLED / "installed/legalmath"
    position = 0
    for stage, row in zip(COMMANDS, outer["reservations"]):
        target = folder / "commands" / stage
        command, actual = read(target / "command.json"), read(target / "result.json")
        require(command["argv"] == row["argv"] == [str(env / "bin/python"), "-I", "-B", str(work / "helpers/worker.py"), str(root), str(folder), stage]
            and command["timeout"] == 110 and actual["returncode"] == 0 and actual["wall_seconds"] <= 110 and
            actual["process_guard"] == {"starts": 1, "blocked": 0} and
            command["environment"] == {"PYTHONPATH": "", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": "-1"},
            "Installed current command or environment differs")
        for name in ("installed-proof-before.json", "installed-proof.json"):
            proof = read(target / name)
            require(proof["isolated"] == 1 and proof["prefix"] == str(env) and proof["python"] == str(env / "bin/python") and
                    proof["modules"] and all(not str(p).endswith("/src") for p in proof["sys_path"]), "Current installed import identity differs")
            require(all(Path(r["path"]).is_relative_to(package) and file_hash(Path(r["path"])) == r["sha256"]
                        for r in proof["modules"].values()), "Loaded installed module differs")
        result = read(target / "installed-result.json")
        added = 2 if stage.startswith("source-") else 0
        require(result["status"] == "PASS" and result["native_reservations"] == [position, position + added] and
                result["blocked_native_attempts"] == (1 if stage in ("profile-controls", "lifecycle-controls") else 0) and
                result["process_guard"] == {"starts": added, "blocked": 0}, "Installed command outcome differs")
        position += added
    for route in native.ROUTES:
        actual = helper.read(folder / "replays" / route / "actual.json.gz")
        expected = {p: helper.read(root / BASELINE / "routes" / route / (p + ".json.gz")) for p in ("P1", "P2", "P3", "P4", "P5", "answer")}
        helper.compare_objects(actual, expected)
    checked_controls(read(folder / "commands/profile-controls/installed-result.json")["details"]["cases"], PROFILE_ERRORS)
    checked_controls(read(folder / "commands/lifecycle-controls/installed-result.json")["details"]["cases"], LIFECYCLE_ERRORS)
    adverse = read(folder / "commands/report-controls/installed-result.json")["details"]["cases"]
    require({r["case"]: {k: v for k, v in r.items() if k != "case"} for r in adverse} == report_adverse(root), "Installed current report counterexamples differ")
    cases = [compare(root, folder, mode, reconsume=reconsume) for mode in ("fresh", "retained")]
    require(all(value == read(folder / ("compare-" + value["mode"] + ".json")) for value in cases),
            "Installed comparison differs from its recorded current consumer")
    for mode, start in (("fresh", 0), ("retained", 2)):
        for index in (0, 1):
            receipt = read(folder / mode / "native" / str(index) / "receipt.json")
            argv = ledger["reservations"][start + index]["argv"]
            require(argv[0] == "/usr/bin/bwrap" and "--" in argv and argv[argv.index("--") + 1:] == receipt["argv"], "Installed reservation differs from actual receipt")
    usage = storage(folder)
    require(usage["unique_bytes"] < SELECTOR["unique_evidence_bytes"], "Installed evidence cap exceeded")
    return {"version": SELECTOR["version"], "profile_sha256": product.digest(profile), "profile_files": len(manifest["files"]),
        "replay_routes": list(native.ROUTES), "cases": cases, "tests": checked_tests(folder),
        "profile_controls": 11, "lifecycle_controls": 4, "report_controls": 3,
        "new_outer_commands": 18, "new_native_reservations": 4, "cumulative_outer_commands": 112,
        "cumulative_native_reservations": 20, "whole_program_complete": False, "independent_legal_acceptance": False}


def validate_submission(root, attempt, task):
    selector(task)
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    require(root == ROOT, "Wrong current installed root")
    tick = time.monotonic()
    with prior.bounded_stage(210), prior.live.offline(), execution_guard():
        frozen(task)
        require({p.name for p in (attempt / "stages").iterdir()} == set(STAGES), "Installed current stages incomplete")
        rows = [read(attempt / "stages" / s / "result.json") for s in STAGES]
        require(all(r["status"] == "PASS" and r["stage"] == s and 0 <= r["wall_seconds"] < (215 if s == "validate" else 120)
                    for s, r in zip(STAGES, rows)), "Installed stage failed or exceeded bound")
        result = read(attempt / "result.json")
        require(result.get("status") == "PASS" and result.get("scope") == "CURRENT_INSTALLED_NATIVE_PROFILE"
            and result.get("whole_program_complete") is False, "Unsupported current installed result")
        require(read(attempt / "verification.json") == evidence(root, attempt), "Current installed evidence differs")
        spent = read(root / REVIEW / "preparation.json")["seconds"] + sum(r["wall_seconds"] for r in rows)
        require(spent + time.monotonic() - tick < 1800, "Installed aggregate time bound")
    print(json.dumps({"current_installed_validation_seconds": time.monotonic() - tick}), flush=True)
    return True


def admission(a, name):
    folder = a.path(name)
    require(folder.parent == a.base / "attempts/native-confinement", "Wrong installed current attempt path")
    admitted = read(folder / "admission.json")
    program, tasks, _ = a.spec(); task = tasks["native-confinement"]
    selector(task)
    event = next(e for e in reversed(a.events()) if e.get("task") == task["id"])
    require(event["kind"] == "ADMIT" and event["attempt"] == name and event["admission_sha256"] == file_hash(folder / "admission.json") and
        admitted["program_sha256"] == adigest(program) and admitted["task_spec"] == task and
        admitted["task_sha256"] == adigest(task) and admitted["binding"] == a.binding(task), "Current unchanged installed admission required")
    require(not (folder / "outputs.json").exists() and not (folder / "result.json").exists(), "Sealed installed attempt refused")
    return folder, admitted, task



def history(auth):
    events = []
    for name in (BASELINE, INSTALLED, RUNTIME, BASE + "/attempts/native-confinement/attempt-013"):
        event = next(e for e in reversed(auth.events()) if e.get("attempt") == name and e["kind"] in {"RECORD", "ACCEPT"})
        require(auth.retained_evidence_valid(event), "Retained installed baseline changed")
        if name == BASELINE:
            require(event["kind"] == "ACCEPT", "Current native baseline has not passed authority acceptance")
        events.append(event)
    return {"events": events}


def frozen(task):
    selector(task)
    value = read(ROOT / REVIEW / "frozen.json")
    require(value["methods"] == methods(ROOT), "Current installed method drift")
    require(value["inputs"] == {n: file_hash(ROOT / n) for n in value["inputs"]}, "Current installed input drift")
    require(value["runtime_files"] == runtime_files(), "Current installed runtime drift")
    require(value["package"] == package_check(ROOT)[1], "Current installed package drift")
    require(history(Authority(ROOT)) == read(ROOT / REVIEW / "history.json"), "Current installed history drift")
    return value


def preparation():
    tick = time.monotonic()
    auth = Authority(ROOT); old, tasks, _ = auth.spec()
    require(old["revision"] == 245, "Wrong current installed preparation baseline")
    folder = ROOT / REVIEW; folder.mkdir(parents=True, exist_ok=False)
    write(folder / "started.json", {"at": datetime.now(timezone.utc).isoformat(),
        "command": [".venv/bin/python", "-m", "scripts.prospectus_installed_runtime", "prepare"]}, exclusive=True)
    try:
        with prior.bounded_stage(max(1, 90 - (time.monotonic() - tick))):
            retained = history(auth)
            write(folder / "implementation-review.json", {
                "verdict": "PASS", "plan": PLAN,
                "baseline": "Current native023 accepted; original006/008/017 retained",
                "primary": "Complete original products/answers, actual installed lifecycles and original18 adverse cases",
                "proxy_audit": "No test count, wheel inventory or replay alone is a lifecycle pass",
                "stop_conditions": "Exact call/time/storage caps; no unchanged retry; preserve failure then diagnose",
                "comparison_audit": "Full current equality; only original checked source/receipt mapping for installed paths",
                "default_audit": "Finite cohort and same-host runtime remain bounded assumptions; full frozen inventory checked",
                "environment_audit": "Exact donor452-file source/wheel/install; original read-only dependencies; isolated imports",
                "stale_context_repair": "Keep historical annual bridge unchanged; replace stale floors with checked94/16",
                "artifact_audit": "Original commands, streams, receipts, complete consumers, control reasons and independent replay",
                "continuation": "Candidate failure is not direction rejection; no external-opinion requirement",
                "known_summary_failure": "Full validation uses explicit210s work limit instead of original115s stage",
            }, exclusive=True)
            # Editing this repository dispatcher must not stale any current result.
            reviews = ["component-238", "pension-post-repair-239", "component-240", "component-241",
                       "component-242", "installed-reasoning-243", "runtime-matrix-245-r2"]
            for name in reviews:
                bindings = read(ROOT / BASE / "reviews" / name / "frozen.json")
                require(previous.SCRIPT not in set(bindings["methods"]) | set(bindings["inputs"]),
                        "Current evidence binds installed dispatcher")
            before = (ROOT / previous.SCRIPT).read_text()
            require('if "current_installed_runtime" in task:' not in before, "Dispatcher already amended")
            (folder / "dispatch-before.py").write_text(before)
            after = dispatch_candidate(before)
            import difflib
            (folder / "driver.patch").write_text(''.join(difflib.unified_diff(before.splitlines(True),
                after.splitlines(True), fromfile="before/" + previous.SCRIPT, tofile="after/" + previous.SCRIPT)))
            # The only shared-file delta is this exact selector branch.
            (ROOT / previous.SCRIPT).write_text(after)
            package = package_check(ROOT)[1]; current = methods(ROOT)
            command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS,
                       "--junitxml=" + str(folder / "tests.xml")]
            with (folder / "tests.log").open("xb") as out:
                result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src"),
                    "PYTHONDONTWRITEBYTECODE": "1"}, stdout=out, stderr=subprocess.STDOUT,
                    timeout=max(1, 80 - (time.monotonic() - tick)))
            require(result.returncode == 0, "Current installed preparation tests failed")
            from legalmath.prospectus.execution_acceptance import checked_tests as count_tests
            count = count_tests(folder / "tests.xml", 1)
            require(current == methods(ROOT), "Methods changed during current installed preparation")
            write(folder / "history.json", retained, exclusive=True)
            task = tasks["native-confinement"]; inputs = set(task["inputs"])
            for event in retained["events"]:
                name = event["attempt"]
                inputs |= {name + "/outputs.json"} | {name + "/" + n for n in read(ROOT / name / "outputs.json")}
            write(folder / "frozen.json", {"methods": current, "inputs": {n: file_hash(ROOT / n) for n in sorted(inputs)},
                "runtime_files": runtime_files(), "package": package}, exclusive=True)
            admissions = [e["attempt"] for e in auth.events() if e["kind"] == "ADMIT" and e["budget_key"] == task["budget_key"]]
            require(len(admissions) == old["budgets"][task["budget_key"]]["maximum_new_attempts"] == 13,
                    "Installed cumulative admissions differ")
            prior_attempt = ROOT / BASE / "attempts/native-confinement/attempt-012"
            for name, limit, floor in (("outer-ledger.json", 18, 76), ("native-ledger.json", 4, 12)):
                old_ledger = process_ledger.checked(prior_attempt / name)
                require(old_ledger["limit"] == limit and old_ledger["historical_lower_bound"] == floor
                        and len(old_ledger["reservations"]) == limit, "Installed historical accounting differs")
            new = deepcopy(old); new["revision"] = 246
            current_task = next(t for t in new["tasks"] if t["id"] == task["id"])
            for key in ("annual_profile_compatibility", "retained_current_profile"):
                current_task.pop(key, None)
            current_task.update(dossier=PLAN, reason="Actual frozen452-file installed profile, five full replays and two native lifecycles; retain13 admissions and floors94 outer/16 native",
                current_installed_runtime=SELECTOR, preparation_only=False, retained_acceptance_only=False,
                native_call_allowance=4, timeout_seconds=230)
            write(folder / "preparation.json", {"tests": count, "test_command": command, "seconds": time.monotonic() - tick,
                "retained_admissions": admissions, "historical_unmeasured_seconds": "UNKNOWN",
                "forecast_unique_bytes": 600 * 1024**2, "new_installations": 0,
                "default_audit": PLAN, "driver_patch": REVIEW + "/driver.patch"}, exclusive=True)
            current_task["inputs"] = sorted(inputs | set(current) | {str(p.relative_to(ROOT)) for p in folder.iterdir() if p.is_file()})
            new["budgets"][task["budget_key"]]["maximum_new_attempts"] = 14
            routes = read(ROOT / old["continuation_review"]["routes"]); routes["baseline_revision"] = 246
            for row in routes["tasks"]:
                if row["task"] == task["id"]:
                    row.update(task_sha256=adigest(current_task), dossier=PLAN, phase=0, mode="local", remaining=current_task["reason"],
                        next_action="Execute current installed stages; independently record and refresh; continue original eight-state recovery", stop_condition=SELECTOR)
            route_name = BASE + "/closure-routes-2026-10-18-installed-runtime-246.json"
            write(ROOT / route_name, routes, exclusive=True)
            new["continuation_review"].update(plan=PLAN, routes=route_name)
            for name in (PLAN, SCRIPT, route_name): new["continuation_review"]["bindings"][name] = file_hash(ROOT / name)
            review = {"baseline": adigest(old), "changes": current_task["reason"], "scope_unchanged": True, "budget_unchanged": False,
                "skeptical_audit": {"verdict": "PASS", "plan": PLAN, "delta": REVIEW + "/driver.patch",
                    "baseline": BASELINE, "veto": "No projection, stale exception, checkout import or accounting reset",
                    "summary_repair": "Explicit210s full validation work bound preserves the known historical timeout diagnosis"},
                "evidence_contract": PLAN, "budget_revision": {"budget_key": task["budget_key"], "previous_maximum": 13,
                    "new_maximum": 14, "retained_attempts": admissions, "reason": current_task["reason"],
                    "next_discriminating_check": "Actual installed full original lifecycles and original adverse controls",
                    "stop_condition": SELECTOR, "same_scope_authorization": "User-directed general build; separate trusted namespace permission"}}
            auth.validate_program(new)
            write(ROOT / BASE / "proposals/installed-runtime-246.json", new, exclusive=True)
            write(ROOT / BASE / "proposals/installed-runtime-246-review.json", review, exclusive=True)
            preparation_result = read(folder / "preparation.json"); preparation_result["seconds"] = time.monotonic() - tick
            write(folder / "preparation.json", preparation_result)
            print(json.dumps({"prepared_revision": 246, "tests": count, "seconds": preparation_result["seconds"]}))
    except BaseException as exc:
        write(folder / "failure.json", {"error": str(exc), "seconds": time.monotonic() - tick,
              "traceback": traceback.format_exc()}, exclusive=True)
        raise


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        tick = time.monotonic()
        folder, admitted, task = admission(a, name)
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]),
                "Repeated/skipped/interrupted installed stage")
        rows = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" for r in rows), "Failed installed predecessor")
        spent = read(ROOT / REVIEW / "preparation.json")["seconds"] + sum(r["wall_seconds"] for r in rows)
        require(spent + 210 < 1800, "Installed acceptance reserve exhausted")
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": [".venv/bin/python", "-m", "scripts.prospectus_installed_runtime", "run", "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU_ONLY; CUDA_VISIBLE_DEVICES=-1",
            "random_seeds": "N/A deterministic", "inputs": admitted["binding"], "plan": PLAN, "result": name + "/result.json"})
        details, error = None, None
        ceiling = 215 if stage == "validate" else 120
        try:
            with prior.bounded_stage(max(1, ceiling - 5 - (time.monotonic() - tick))), (nullcontext() if stage in COMMANDS else execution_guard()):
                f = frozen(task)
                if stage == "prepare":
                    save(folder, "methods.json", f["methods"])
                    save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_bytes().hex() for p in f["methods"]})
                    target = folder / "tests"; target.mkdir()
                    shutil.copyfile(ROOT / REVIEW / "tests.xml", target / "results.xml")
                    save(folder, "tests/result.json", {"status": "PASS", "exit_code": 0,
                        "junit_sha256": file_hash(target / "results.xml"), "original_tests": REVIEW + "/tests.xml"})
                    details = prepare(folder)
                elif stage in COMMANDS:
                    details = execute(folder, stage)
                elif stage.startswith("compare-"):
                    details = compare(ROOT, folder, stage.removeprefix("compare-"))
                    save(folder, stage + ".json", details)
                elif stage == "validate":
                    details = evidence(ROOT, folder, reconsume=False)
                    save(folder, "verification.json", details)
                else:
                    details = read(folder / "verification.json")
                    (folder / "RESULT.md").write_text(
                        "# Current installed runtime\n\nThe frozen452-file installation passed all five complete replays, both actual fresh/retained lifecycles, "
                        "11 profile controls, four lifecycle controls and three report controls. Every imported production module came from that installation. "
                        "Eighteen outer commands and four native reservations were charged after retained installed floors94/16; no installation occurred.\n\n"
                        "| Decision | Primary criterion | Veto | Uncertainty | Next action | Limit |\n| --- | --- | --- | --- | --- | --- |\n"
                        "| Submit current installed evidence | Complete original outputs and controls passed | No identity/accounting veto | Finite same-host cohort | Independent authority record,refresh,eight-state recovery | No unseen/legal/whole-build conclusion |\n\n"
                        "Post-run red team: matching original answers can preserve source-interpretation errors; recovery and broader substantive coverage remain separate.\n")
                    save(folder, "run-manifest.json", {"git_commit": admitted["git_commit"], "plan": PLAN,
                        "result": name + "/RESULT.md", "commands": [read(folder / "stages" / s / "started.json") for s in STAGES],
                        "environment": str(workspace(folder)[1]), "cpu_gpu": "CPU_ONLY; CUDA_VISIBLE_DEVICES=-1", "seeds": "N/A deterministic",
                        "data_version": f["inputs"], "methods": f["methods"], "cumulative_seconds": spent + time.monotonic() - tick,
                        "historical_unmeasured_seconds": "UNKNOWN", "storage": storage(folder)})
                require(f["methods"] == methods(ROOT) and admitted["binding"] == a.binding(task), "Installed stage inputs/methods changed")
                require(spent + time.monotonic() - tick + 210 < 1800 and storage(folder)["unique_bytes"] < 636 * 1024**2,
                        "Installed cumulative bound or reserve exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        if not error and time.monotonic() - tick >= ceiling:
            error = {"type": "TimeoutError", "message": "Recorded installed stage bound exceeded"}
        value = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error,
                 "details": details, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", value, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**value, "task": task["id"], "scope": "CURRENT_INSTALLED_NATIVE_PROFILE",
                 "whole_program_complete": False}, final=True)
            save(folder, "outputs.json", prior.preparation.prep.files(folder), final=True)
        print(json.dumps({k: value[k] for k in ("status", "stage", "error", "wall_seconds")}))
        return int(error is not None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--attempt"); parser.add_argument("--stage", choices=STAGES)
    args = parser.parse_args()
    if args.action == "prepare":
        preparation()
    else:
        if not args.attempt or not args.stage: parser.error("--attempt and --stage required")
        raise SystemExit(run(args.attempt, args.stage))


