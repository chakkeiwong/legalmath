"""Current installed-target profile and native lifecycle; exact finite acceptance."""
import argparse
from contextlib import nullcontext, redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES="-1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
from legalmath.prospectus.execution_authority import Authority, digest as adigest, file_hash, read
from legalmath.prospectus import native_profile as product
from legalmath.prospectus.successor import process_ledger, service
from scripts import prospectus_native_product_delta as native
from scripts import prospectus_installed_profile_refresh as previous
from scripts.prospectus_profile_installed_worker import execution_guard

prior = native.prior
helper, common, require = prior.helper, prior.common, prior.require
BASE = native.BASE
REVIEW = BASE + "/reviews/profile-installed-196"
OLD = BASE + "/attempts/native-confinement/attempt-004"
RUNTIME = native.INSTALLED
INSTALLED = BASE + "/attempts/source-bes-dep-09/attempt-014"
SCRIPT = "scripts/prospectus_profile_installed.py"
WORKER = "scripts/prospectus_profile_installed_worker.py"
TEST = "tests/prospectus/test_profile_installed.py"
PLAN = "docs/plans/prospectus-current-installed-target-2026-10-17.md"
COMMANDS = ("capture", "check", *("replay-" + r for r in native.ROUTES), "profile-controls",
            *(s + "-" + m for m in ("fresh", "retained") for s in ("source", "construct", "finish", "verify")),
            "lifecycle-controls", "report-controls")
STAGES = ("tests", "prepare", *COMMANDS[:8], *COMMANDS[8:12], "compare-fresh",
          *COMMANDS[12:16], "compare-retained", *COMMANDS[16:], "validate", "seal")
SELECTOR = {"version": "current-annual-profile-installed.v1", "review": REVIEW, "stages": list(STAGES),
    "outer_commands": 18, "native_calls": 4, "historical_outer": 76, "historical_native": 12,
    "stage_seconds": 115, "execution_seconds": 1200, "validation_seconds": 210,
    "unique_evidence_bytes": 640 * 1024**2, "new_installations": 0}
PROFILE_ERRORS = {"wrong-pin": "Pinned profile", "blob-changed": "Snapshot blob", "blob-missing": "No such file",
    "method-changed": "Installed product methods", "runtime-changed": "Trusted runtime", "manifest-changed": "Snapshot manifest identity",
    "changed-source": "Source bytes changed", "duplicate-stage": "File exists", "rehashed-answer": "Complete installed object differs: answer",
    "extra-subprocess": "Native subprocess forbidden", "actual-old-profile": "Installed product methods changed; recapture profile"}
LIFECYCLE_ERRORS = {"failed-predecessor": "Predecessor stage did not pass", "rehashed-forged-answer": "Delivered answer differs from actual consumer",
                    "missing-stream": "No such file", "forbidden-subprocess": "Native subprocess forbidden"}


def selector(task):
    require(task.get("id") == "native-confinement" and task.get("validator") == prior.INSTALLED and
            task.get("annual_profile_compatibility") == SELECTOR and
            task.get("product_delta_acceptance") == previous.SELECTOR and
            "retained_profile_validation" not in task and task.get("native_call_allowance") == 4 and
            task.get("retained_acceptance_only") is False, "Unreviewed installed profile selector")


def methods(root):
    return {**prior.methods(root), **{p: file_hash(root / p) for p in
        (SCRIPT, WORKER, TEST, native.SCRIPT, previous.SCRIPT, previous.WORKER, previous.TEST)}}


def dispatch_candidate(before):
    marker = "def validate_submission(root, attempt, task):\n"
    require(before.count(marker) == 1, "Unexpected installed dispatcher baseline")
    return before.replace(marker, marker +
        '    if "annual_profile_compatibility" in task:\n'
        '        from scripts.prospectus_profile_installed import validate_submission as validate_current\n'
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
    parents.extend([ROOT / REVIEW, ROOT / (BASE + "/proposals/profile-installed-196.json"),
        ROOT / (BASE + "/proposals/profile-installed-196-review.json"),
        ROOT / (BASE + "/closure-routes-2026-10-17-profile-installed-196.json"),
        ROOT / (BASE + "/revisions/0196.json"), *(ROOT / p for p in (SCRIPT, WORKER, TEST, PLAN))])
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
    expected = read(installed / "final-package.json")
    require(helper.package_files(root / "src/legalmath") == expected ==
            helper.package_files(installed / "installed/legalmath"), "Current installed package differs")
    require(prior.preparation.tree(env, dependencies=True) == read(root / RUNTIME / "dependencies.json"), "Installed dependencies differ")
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
    save(folder, "baseline.json", {"attempt": native.NATIVE})
    process_ledger.create(folder / "outer-ledger.json", 18, 76, "Eighteen current target commands; prior76 retained; no build/install")
    process_ledger.create(folder / "native-ledger.json", 4, 12, "Four current target source reservations; prior twelve installed; native-binding lineage separate")
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
        req = helper.read(ROOT / native.NATIVE / "routes" / ("2010-" + mode) / "P1.json.gz")["payload"]["request"]
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
    base = root / native.NATIVE / "routes" / ("2010-" + mode)
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
                read(base / "native/1/receipt.json"), read(root / native.NATIVE / "snapshots/2010/manifest.json")))
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
    result = read(folder / "tests/result.json")
    require(result["status"] == "PASS" and result["exit_code"] == 0 and result["junit_sha256"] == file_hash(folder / "tests/results.xml"), "Installed current tests differ")
    tree = ET.parse(folder / "tests/results.xml").getroot()
    suites = list(tree.iter("testsuite"))
    require(suites and all(int(s.get(k, 0)) == 0 for s in suites for k in ("failures", "errors", "skipped")), "Installed tests failed/skipped")
    names = {r.get("name", "").split("[")[0] for r in tree.iter("testcase")}
    require({"test_installed_selector_refuses_changed_allowances", "test_control_denominator_and_specific_refusal",
             "test_current_target_execution_proof_refuses_other_package",
             "test_current_target_required_files_preserve_all_other_sources",
             "test_installed_target_dispatch_retains_strict_fallback",
             "test_current_target_package_checks_source_install_and_dependencies",
             "test_current_target_missing_lifecycle_cannot_validate",
             "test_current_target_selector_keeps_exact_call_and_scope_limits",
             "test_current_package_change_is_detected", "test_missing_current_lifecycle_is_not_acceptance",
             "test_process_guard_blocks_direct_bypasses", "test_process_guard_requires_exact_ordered_argv",
             "test_native_guard_checks_whole_namespace_command",
             "test_changed_profile_or_snapshot_refuses_before_launch", "test_stage_does_not_repeat_failed_work"} <= names,
            "Required installed adverse tests missing")
    return {"tests": sum(int(s.get("tests", 0)) for s in suites), "junit_sha256": result["junit_sha256"]}


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
    require(outer["limit"] == 18 and outer["historical_lower_bound"] == 76 and len(outer["reservations"]) == 18 and
            ledger["limit"] == 4 and ledger["historical_lower_bound"] == 12 and len(ledger["reservations"]) == 4 and
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
        expected = {p: helper.read(root / native.NATIVE / "routes" / route / (p + ".json.gz")) for p in ("P1", "P2", "P3", "P4", "P5", "answer")}
        helper.compare_objects(actual, expected)
    checked_controls(read(folder / "commands/profile-controls/installed-result.json")["details"]["cases"], PROFILE_ERRORS)
    checked_controls(read(folder / "commands/lifecycle-controls/installed-result.json")["details"]["cases"], LIFECYCLE_ERRORS)
    adverse = read(folder / "commands/report-controls/installed-result.json")["details"]["cases"]
    require({r["case"]: {k: v for k, v in r.items() if k != "case"} for r in adverse} == native.adverse(root), "Installed current report counterexamples differ")
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
        "new_outer_commands": 18, "new_native_reservations": 4, "cumulative_outer_commands": 94,
        "cumulative_native_reservations": 16, "whole_program_complete": False, "independent_legal_acceptance": False}


def validate_submission(root, attempt, task):
    if "retained_current_profile" in task:
        from scripts.prospectus_profile_retained import validate_submission as validate_retained
        return validate_retained(root, attempt, task)
    selector(task)
    root, attempt = Path(root).resolve(), Path(attempt).resolve()
    with prior.bounded_stage(210), prior.live.offline(), execution_guard():
        require({p.name for p in (attempt / "stages").iterdir()} == set(STAGES), "Installed current stages incomplete")
        rows = [read(attempt / "stages" / s / "result.json") for s in STAGES]
        require(all(r["status"] == "PASS" and r["stage"] == s and 0 <= r["wall_seconds"] < 115 for s, r in zip(STAGES, rows)) and
                sum(r["wall_seconds"] for r in rows) < 1200, "Installed current stage failed or exceeded bound")
        result = read(attempt / "result.json")
        require(result.get("status") == "PASS" and result.get("scope") == "CURRENT_INSTALLED_NATIVE_PROFILE" and
                result.get("whole_program_complete") is False, "Unsupported current installed result")
        require(read(attempt / "verification.json") == evidence(root, attempt), "Current installed evidence differs from independent check")
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


def run(name, stage):
    a = Authority(ROOT)
    with a.lock():
        folder, admitted, task = admission(a, name)
        index = STAGES.index(stage)
        require({p.parent.name for p in (folder / "stages").glob("*/started.json")} ==
                {p.parent.name for p in (folder / "stages").glob("*/result.json")} == set(STAGES[:index]), "Repeated/skipped/interrupted installed stage")
        rows = [read(folder / "stages" / s / "result.json") for s in STAGES[:index]]
        require(all(r["status"] == "PASS" for r in rows), "Failed installed predecessor")
        spent = sum(r["wall_seconds"] for r in rows)
        require(spent < 1200, "Installed current execution budget exhausted")
        current = methods(ROOT)
        if index:
            require(current == read(folder / "methods.json"), "Installed current methods changed")
        else:
            save(folder, "methods.json", current)
            save(folder, "method-snapshots.json.gz", {p: (ROOT / p).read_bytes().hex() for p in current})
        save(folder, "stages/" + stage + "/started.json", {"at": datetime.now(timezone.utc).isoformat(),
            "command": ["timeout", "120", ".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "--attempt", name, "--stage", stage],
            "git_commit": admitted["git_commit"], "python": sys.executable, "cpu_gpu": "CPU only; GPUs intentionally hidden",
            "random_seeds": "N/A deterministic comparison", "inputs": admitted["binding"], "plan": task["dossier"], "result": name + "/result.json"})
        tick, details, error = time.monotonic(), None, None
        try:
            # Command stages guard one exact outer argv; their installed workers
            # constrain both native argv. Tests exercise their own guard contexts.
            with prior.bounded_stage(min(110, 1200 - spent)), (nullcontext() if stage in COMMANDS or stage == "tests" else execution_guard()):
                if stage == "tests":
                    target = folder / "tests"; target.mkdir()
                    with (target / "tests.log").open("x") as log, redirect_stdout(log), redirect_stderr(log):
                        import pytest
                        code = int(pytest.main(["-q", "-p", "no:cacheprovider", TEST, "tests/prospectus/test_installed_profile_refresh.py", "tests/prospectus/test_native_profile.py", "--junitxml=" + str(target / "results.xml")]))
                    save(folder, "tests/result.json", {"status": "PASS" if code == 0 else "FAIL", "exit_code": code,
                        "junit_sha256": file_hash(target / "results.xml") if (target / "results.xml").exists() else None})
                    require(code == 0, "Installed current focused tests failed")
                    details = checked_tests(folder)
                elif stage == "prepare":
                    details = prepare(folder)
                elif stage in COMMANDS:
                    details = execute(folder, stage)
                elif stage.startswith("compare-"):
                    details = compare(ROOT, folder, stage.removeprefix("compare-"))
                    save(folder, stage + ".json", details)
                elif stage == "validate":
                    # Actual consumer checks ran in both compare stages; final
                    # authority recording independently repeats them. Do not
                    # duplicate those long checks inside this115s summary stage.
                    details = evidence(ROOT, folder, reconsume=False)
                    save(folder, "verification.json", details)
                else:
                    require((folder / "RESULT.md").is_file(), "Actual installed result review required")
                    details = read(folder / "verification.json")
                require(current == methods(ROOT) and admitted["binding"] == a.binding(task), "Installed methods or inputs changed during stage")
                require(spent + time.monotonic() - tick < 1200 and storage(folder)["unique_bytes"] < 636 * 1024**2, "Installed cumulative bound exceeded")
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            save(folder, "stages/" + stage + "/error.json", {"traceback": traceback.format_exc()}, final=True)
        if not error and time.monotonic() - tick >= 115:
            error = {"type": "TimeoutError", "message": "Recorded installed stage bound exceeded"}
        value = {"status": "FAIL" if error else "PASS", "stage": stage, "error": error, "details": details, "wall_seconds": time.monotonic() - tick}
        save(folder, "stages/" + stage + "/result.json", value, final=True)
        if error or stage == "seal":
            save(folder, "result.json", {**value, "task": task["id"], "scope": "CURRENT_INSTALLED_NATIVE_PROFILE", "whole_program_complete": False}, final=True)
            save(folder, "outputs.json", prior.preparation.prep.files(folder), final=True)
        print(json.dumps({k: value[k] for k in ("status", "stage", "error", "wall_seconds")}))
        return int(error is not None)


def record(name):
    a = Authority(ROOT)
    tick = time.monotonic()
    a.record(name)
    event = next(e for e in reversed(a.events()) if e.get("attempt") == name)
    value = {"attempt": name, "authority_event": event, "wall_seconds": time.monotonic() - tick,
        "command": ["timeout", "240", ".venv/bin/python", "-m", SCRIPT.removesuffix(".py").replace("/", "."), "--attempt", name, "--stage", "record"]}
    save(ROOT / REVIEW, "actual-record.json", value)
    print(json.dumps({"kind": event["kind"], "reason": event.get("reason"), "seq": event["seq"], "wall_seconds": value["wall_seconds"]}))
    return int(event["kind"] != "ACCEPT")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--attempt", required=True); p.add_argument("--stage", choices=(*STAGES, "record"), required=True)
    args = p.parse_args()
    return record(args.attempt) if args.stage == "record" else run(args.attempt, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
